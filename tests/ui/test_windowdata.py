import json
from datetime import date

import pytest

from ebbin.data import queries as q
from ebbin.data.store import State
from ebbin.ui import windowdata as wd
from tests.conftest import seed_revlog
from tests.ui.test_hints import CFG

TODAY = date(2026, 10, 28)
SECTIONS = {"consistency", "improve", "efficiency", "curve", "empty"}


def _cards(col, deck, n, **upd):
    did = col.decks.id(deck)
    cids = []
    for i in range(n):
        note = col.new_note(col.models.by_name("Basic"))
        note["Front"], note["Back"] = f"{deck}{i}", "a"
        col.add_note(note, did)
        cids.append(note.cards()[0].id)
    return cids


def _seed(col, cids, day_off, eases, base=0):
    start = q.day_start_ms(col)
    seed_revlog(col, [
        {"id": start - day_off * 86_400_000 + 1000 + base + i, "cid": cids[i % len(cids)], "ease": e}
        for i, e in enumerate(eases)])


def test_empty_collection(col):
    p = wd.metrics_payload(col, State(), CFG, "all", "30d", TODAY)
    assert SECTIONS <= set(p) and p["empty"] is True
    assert len(p["consistency"]["calendar"]) == 84
    assert p["consistency"]["streak"] == {"current": 0, "best": 0}
    assert len(p["curve"]["retention_series"]) == 12
    assert p["efficiency"]["load"]["first_over"] is None
    json.dumps(p)


def test_deck_accuracy_and_scope(col):
    a, b = _cards(col, "A", 3), _cards(col, "B", 3)
    _seed(col, a, 0, [3] * 30)
    _seed(col, b, 0, [1] * 15 + [3] * 15, base=100)
    st = State()
    p = wd.metrics_payload(col, st, CFG, "all", "30d", TODAY)
    assert not p["empty"]
    decks = p["improve"]["by_deck_accuracy"]
    assert [d["deck"] for d in decks] == ["B", "A"]
    assert p["improve"]["problem_cards"] and "cid" in p["improve"]["problem_cards"][0]
    assert p["improve"]["true_retention"] == pytest.approx(45 / 60)
    assert p["curve"]["retention_series"][-1] == pytest.approx(0.75)
    st.objectives = [{"id": "o", "name": "X", "exam_date": None, "deck_roots": ["A"]}]
    st.active_objective = "o"
    act = wd.metrics_payload(col, st, CFG, "active", "30d", TODAY)
    assert [d["deck"] for d in act["improve"]["by_deck_accuracy"]] == ["A"]
    assert p["improve"]["desired_retention"] == pytest.approx(0.90) and p["scope_fallback"] is False
    cal = p["consistency"]["calendar"]
    assert cal[-1]["weekday"] == TODAY.weekday() == 2 and cal[-2]["weekday"] == 1 and cal[0]["weekday"] == (2 - 83) % 7
    assert act["scope_fallback"] is False
    st.active_objective = None  # no active objective -> all
    assert wd.metrics_payload(col, st, CFG, "active", "30d", TODAY)["scope_fallback"] is True
    assert len(wd.metrics_payload(col, st, CFG, "active", "30d", TODAY)["improve"]["by_deck_accuracy"]) == 2
    json.dumps(act)


def test_period_and_mastered_rescued(col):
    a = _cards(col, "A", 2)
    _seed(col, a, 40, [3] * 20)
    _seed(col, a, 0, [3] * 12, base=500)
    st = State()
    assert wd.metrics_payload(col, st, CFG, "all", "30d", TODAY)["empty"] is False
    p30 = wd.metrics_payload(col, st, CFG, "all", "30d", TODAY)
    pall = wd.metrics_payload(col, st, CFG, "all", "all", TODAY)
    assert p30["improve"]["true_retention"] is None  # 12 type-1 rows < 30
    assert pall["improve"]["true_retention"] == 1.0
    rid = q.day_start_ms(col) + 2000
    st.mastered[rid] = a[0]
    st.rescued[rid] = a[0]
    p = wd.metrics_payload(col, st, CFG, "all", "30d", TODAY)
    assert p["efficiency"]["mastered_per_hour"] > 0
    assert p["curve"]["rescued_by_week"][-1] == 1


def test_objective_crud(col):
    st = State()
    with pytest.raises(ValueError):
        wd.objective_upsert(st, {"name": " "})
    with pytest.raises(ValueError):
        wd.objective_upsert(st, {"name": "x", "exam_date": "31/12"})
    with pytest.raises(ValueError):
        wd.objective_upsert(st, {"name": "x", "deck_roots": "A"})
    oid = wd.objective_upsert(st, {"name": "OAB", "exam_date": "2026-11-27", "deck_roots": ["A"]})
    assert wd.objective_upsert(st, {"id": oid, "name": "OAB 2", "exam_date": None, "deck_roots": []}) == oid
    assert len(st.objectives) == 1 and st.objectives[0]["name"] == "OAB 2"
    wd.objective_activate(st, oid)
    assert st.active_objective == oid
    wd.objective_delete(st, oid)
    assert st.objectives == [] and st.active_objective is None


def test_objectives_payload_stars_fallback_and_archive(col):
    cids = _cards(col, "Prova::Dir", 4)
    _cards(col, "Outro", 1)
    col.db.execute("update cards set type=2, queue=2, due=?, ivl=30 where id in (?,?)", col.sched.today + 5, cids[0], cids[1])
    col.db.execute("update cards set type=2, queue=2, due=?, ivl=3, data=? where id=?",
                   col.sched.today + 5, '{"s": 30.0}', cids[2])
    st = State()
    oid = wd.objective_upsert(st, {"name": "P", "exam_date": "2026-11-27", "deck_roots": ["Prova"]})
    wd.objective_activate(st, oid)
    p = wd.objectives_payload(col, st, TODAY)
    assert p["active_id"] == oid and "Outro" in p["decks"] and "Prova::Dir" in p["decks"]
    it = p["items"][0]
    assert it["new_remaining"] == 1 and it["stars"] == 2  # 3/4 mastered = 75%
    assert it["days_left"] == 30 and it["pace"] == 1 and it["countdown"] == "P · 30 dias"
    json.dumps(p)
    _seed(col, cids, 0, [3, 1, 3, 3])
    s = wd.objective_archive(col, st, oid, TODAY)
    assert s == {"mastered": 3, "study_days": 1, "accuracy": 0.75}
    assert st.active_objective is None and st.objectives[0]["archived"] is True
    assert st.objectives[0]["archived_summary"] == s
