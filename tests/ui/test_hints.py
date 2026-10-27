import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from ebbin.data import queries as q
from ebbin.data.store import State
from ebbin.ui import hints
from ebbin.ui.hints import build_hints
from tests.conftest import seed_revlog

CFG = json.loads((Path(__file__).parents[2] / "ebbin" / "config.json").read_text())
SUNDAY = date(2026, 11, 1)  # a Sunday
assert SUNDAY.weekday() == 6


def _notes(col, n, due_offset=None):
    t = col.sched.today
    cids = []
    for i in range(n):
        note = col.new_note(col.models.by_name("Basic"))
        note["Front"], note["Back"] = f"q{i}", "a"
        col.add_note(note, col.decks.id("Default"))
        cid = note.cards()[0].id
        cids.append(cid)
        if due_offset is not None:
            col.db.execute("update cards set queue=2, type=2, due=?, ivl=5 where id=?",
                           t + due_offset, cid)
    return cids


def _ids(col, st, view=None):
    return {h["id"].split(":")[0]: h for h in build_hints(col, st, CFG, view or {})}


def _at(monkeypatch, d):
    monkeypatch.setattr(hints, "_anki_date", lambda col: d)


def test_nothing_on_empty_collection(col, monkeypatch):
    _at(monkeypatch, date(2026, 10, 28))  # Wednesday
    st = State(last_weekly_summary_day=10**6)
    assert build_hints(col, st, CFG, {}) == []


def test_load_warning_with_date(col, monkeypatch):
    _at(monkeypatch, date(2026, 10, 28))
    _notes(col, 50, due_offset=3)  # 50 * 30 s > 20 min
    h = _ids(col, State(last_weekly_summary_day=10**6))["load"]
    assert h["text"] == "No ritmo atual você passa dos 20 min em 31/10"
    assert h["id"] == f"load:{q.today(col)}" and h["kind"] == "warn"


def test_load_warning_absent_when_under_budget(col, monkeypatch):
    _at(monkeypatch, date(2026, 10, 28))
    _notes(col, 5, due_offset=3)
    assert "load" not in _ids(col, State(last_weekly_summary_day=10**6))


def test_suggestion_needs_new_cards_and_room(col, monkeypatch):
    _at(monkeypatch, date(2026, 10, 28))
    st = State(last_weekly_summary_day=10**6)
    assert "suggest" not in _ids(col, st)  # no new cards
    _notes(col, 3)
    assert _ids(col, st)["suggest"]["text"] == "sugestão: 13 novos hoje"  # (40 - 0) // 3
    _notes(col, 40, due_offset=-1)  # due 40 -> capacity used up
    assert "suggest" not in _ids(col, st)


def test_weekly_summary_once(col, monkeypatch):
    _at(monkeypatch, SUNDAY)
    start = q.day_start_ms(col)
    cid = _notes(col, 1, due_offset=9)[0]
    seed_revlog(col, [{"id": start + 1000 * i, "cid": cid, "ease": 3} for i in range(1, 4)])
    st = State()
    t = q.today(col)
    h = _ids(col, st)["weekly"]
    assert h["id"] == f"weekly:{t}"
    assert "sem estudo" in h["text"] and " · " not in h["text"]
    assert st.last_weekly_summary_day == t and st.weekly_shown_day == t
    again = _ids(col, st)["weekly"]  # re-render the same day: still visible
    assert again == h
    st.dismissed_hints[h["id"]] = t
    assert "weekly" not in _ids(col, st)  # dismissed


def test_weekly_summary_hidden_next_day(col, monkeypatch):
    _at(monkeypatch, SUNDAY)
    start = q.day_start_ms(col)
    cid = _notes(col, 1, due_offset=9)[0]
    seed_revlog(col, [{"id": start + 1000, "cid": cid, "ease": 3}])
    st = State()
    assert "weekly" in _ids(col, st)
    st.weekly_shown_day -= 1  # pretend it was first shown yesterday
    assert "weekly" not in _ids(col, st)


def test_weekly_summary_not_before_sunday_marker_or_install(col, monkeypatch):
    _at(monkeypatch, SUNDAY)
    start = q.day_start_ms(col)
    cid = _notes(col, 1, due_offset=9)[0]
    seed_revlog(col, [{"id": start + 1000, "cid": cid, "ease": 3}])
    t = q.today(col)
    assert "weekly" not in _ids(col, State(last_weekly_summary_day=t))
    assert "weekly" not in _ids(col, State(installed_day=t + 1))
    # no reviews this week -> nothing to say, but still marked
    col.db.execute("delete from revlog")
    st = State()
    assert "weekly" not in _ids(col, st)
    assert st.last_weekly_summary_day == t


def test_weekly_summary_after_sunday_uses_that_sunday(col, monkeypatch):
    _at(monkeypatch, SUNDAY + timedelta(days=3))  # Wednesday
    start = q.day_start_ms(col)
    cid = _notes(col, 1, due_offset=9)[0]
    seed_revlog(col, [{"id": start - 3 * 86_400_000 + 1000, "cid": cid, "ease": 3}])  # on Sunday
    t = q.today(col)
    st = State(installed_day=t - 30, last_weekly_summary_day=t - 30)
    assert _ids(col, st)["weekly"]["id"] == f"weekly:{t - 3}"
    assert st.last_weekly_summary_day == t - 3


def test_comeback_hint(col, monkeypatch):
    _at(monkeypatch, date(2026, 10, 28))
    t = q.today(col)
    base = dict(last_weekly_summary_day=10**6)
    assert "comeback" not in _ids(col, State(**base))
    assert _ids(col, State(comeback_days_left=2, **base))["comeback"]["text"] == "bem-vindo de volta"
    last = State(m=1.0, missions_by_day={t: {"m_used": 0.6}}, **base)  # third day: left == 0
    assert "comeback" in _ids(col, last)
    adaptive = State(m=0.8, missions_by_day={t: {"m_used": 0.8}}, **base)
    assert "comeback" not in _ids(col, adaptive)


def test_dismissed_hidden(col, monkeypatch):
    _at(monkeypatch, date(2026, 10, 28))
    t = q.today(col)
    st = State(last_weekly_summary_day=10**6, comeback_days_left=1)
    assert "comeback" in _ids(col, st)
    st.dismissed_hints[f"comeback:{t}"] = t
    assert "comeback" not in _ids(col, st)


def test_fsrs_reminder_hint(col, monkeypatch):
    _at(monkeypatch, date(2026, 10, 28))
    cid = _notes(col, 1, due_offset=9)[0]
    st = State(last_weekly_summary_day=10**6)
    seed_revlog(col, [{"id": 1_000_000 + i, "cid": cid, "ease": 3} for i in range(299)])
    assert "fsrs" not in _ids(col, st)
    seed_revlog(col, [{"id": 9_000_000, "cid": cid, "ease": 3}])
    h = _ids(col, st)["fsrs"]
    assert h["id"] == f"fsrs:{q.today(col)}" and h["kind"] == "fsrs"
    assert h["text"] == "Hora de otimizar o FSRS: abra as opções do deck e clique em Otimizar"


def _obj_state(col, root="Prova"):
    from ebbin.core.objectives import Objective
    st = State(last_weekly_summary_day=10**6)
    st.objectives = [Objective(id="o", name="P", exam_date=None, deck_roots=[root]).to_dict()]
    st.active_objective = "o"
    return st


def test_auto_new_hint_shared_preset_once_per_day_and_sticks(col):
    col.decks.id("Prova")  # shares preset 1 with Default
    st = _obj_state(col)
    cfg = {**CFG, "auto_new_per_day": True}
    h = hints.auto_new_hint(col, st, cfg)
    t = col.sched.today
    assert h == {"id": f"autonew:{t}", "kind": "warn", "text":
                 "Novos automáticos: o preset 'Default' é compartilhado com outros decks — "
                 "crie um preset só para o objetivo"}
    assert hints.auto_new_hint(col, st, cfg) == h  # rebuild same day keeps it
    assert [x["id"] for x in build_hints(col, st, cfg, {}) if x["id"].startswith("autonew")] == [h["id"]]
    st.dismissed_hints[h["id"]] = t
    assert not [x for x in build_hints(col, st, cfg, {}) if x["id"].startswith("autonew")]


def test_auto_new_hint_off_or_dedicated(col):
    st = _obj_state(col)
    assert hints.auto_new_hint(col, st, {**CFG, "auto_new_per_day": False}) is None
    assert st.day_stats == {}
    assert hints.auto_new_hint(col, State(), {**CFG, "auto_new_per_day": True}) is None
