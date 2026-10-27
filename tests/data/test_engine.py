import json
from pathlib import Path

import pytest

from ebbin.core.models import CardSnap
from ebbin.core.rules import level_from_total, main_mission_bonus
from ebbin.data import queries as q
from ebbin.data import store
from ebbin.ui.engine import Engine
from tests.conftest import seed_revlog

DAY = 86_400_000
_CFG = json.loads((Path(__file__).parents[2] / "ebbin" / "config.json").read_text())


class FakeClock:
    def __init__(self, t: float = 1_800_000_000.0):
        self.t = t

    def __call__(self) -> float:
        return self.t


def _cfg(**over):
    return {**json.loads(json.dumps(_CFG)), **over}


def _add_due(col, n: int) -> list[int]:
    t = col.sched.today
    ids = []
    for i in range(n):
        note = col.new_note(col.models.by_name("Basic"))
        note["Front"], note["Back"] = f"q{i}", "a"
        col.add_note(note, col.decks.id("Default"))
        cid = note.cards()[0].id
        col.db.execute("update cards set queue=2, type=2, due=?, ivl=5, factor=2500 where id=?", t - 1, cid)
        ids.append(cid)
    return ids


def _study(col, eng: Engine, ease: int):
    card = col.sched.getCard()
    eng.before_show(card.id)
    states = col._backend.get_scheduling_states(card.id)
    col.sched.answer_card(col.sched.build_answer(card=card, states=states, rating=ease - 1))
    return eng.on_answer(card.id, ease)


@pytest.fixture
def path(tmp_path):
    return tmp_path / "user_files" / "p.json"


def test_first_install_bootstraps_from_history(col, path):
    cid = _add_due(col, 1)[0]
    past = q.day_start_ms(col) - 2 * DAY
    seed_revlog(col, [{"id": past, "cid": cid, "ease": 3}, {"id": past + 1, "cid": cid, "ease": 1}])
    eng = Engine(col, _cfg(), path, clock=FakeClock())
    assert eng.state.bootstrap_xp == 12
    assert eng.state.installed_day == col.sched.today
    assert path.exists()
    seed_revlog(col, [{"id": past + 2, "cid": cid, "ease": 3}])
    again = Engine(col, _cfg(), path, clock=FakeClock())
    assert again.state.bootstrap_xp == 12


def test_good_x3_builds_combo(col, path):
    _add_due(col, 5)
    eng = Engine(col, _cfg(), path, clock=FakeClock())
    evs = [_study(col, eng, 3) for _ in range(3)]
    assert [e.xp for e in evs] == [11, 11, 12]
    assert [e.sounds for e in evs] == [["good"], ["combo:2"], ["combo:3"]]
    assert [e.combo for e in evs] == [1, 2, 3]
    assert eng.state.day_stats[col.sched.today]["max_combo"] == 3
    assert len(eng.state.ledger.answers) == 3


def test_again_resets_combo(col, path):
    _add_due(col, 5)
    eng = Engine(col, _cfg(), path, clock=FakeClock())
    _study(col, eng, 3)
    _study(col, eng, 3)
    ev = _study(col, eng, 1)
    assert ev.sounds == ["again"]
    assert ev.combo == 0 and ev.xp == 2
    assert eng.state.combo.count == 0


def test_undo_drops_last_answer_xp_and_combo(col, path):
    _add_due(col, 5)
    eng = Engine(col, _cfg(), path, clock=FakeClock())
    _study(col, eng, 3)
    before = eng.state.ledger.total(eng.state.bootstrap_xp)
    last = _study(col, eng, 3)
    assert eng.state.combo.count == 2
    col.undo()
    eng.on_undo()
    assert eng.state.ledger.total(eng.state.bootstrap_xp) == before
    assert last.xp == 11
    assert eng.state.combo.count == 1  # replay of the remaining answer, not 0
    assert eng.tracker.current.answers == 1
    assert eng.tracker.current.xp == 11
    assert store.load(path).combo.count == 1


def test_main_mission_done_exactly_once_and_undo_removes_bonus(col, path):
    _add_due(col, 5)
    eng = Engine(col, _cfg(budget_min=1.5), path, clock=FakeClock())
    eng.today_view()  # fixes the day's mission: capacity floor(90 / 30) = 3, due 5 -> "Revisar 3"
    t = col.sched.today
    main = eng.state.missions_by_day[t]["main"]
    assert main == {"kind": "reviews", "target_reviews": 3, "target_new": 0}
    e1, e2 = _study(col, eng, 3), _study(col, eng, 3)
    assert "main" not in e1.mission_done + e2.mission_done
    total_before = eng.state.ledger.total(eng.state.bootstrap_xp)
    e3 = _study(col, eng, 3)
    assert "main" in e3.mission_done
    assert "done" in e3.sounds
    level = level_from_total(total_before + e3.xp).level
    assert eng.state.ledger.bonuses[f"main:{t}"] == main_mission_bonus(level)
    assert eng.state.day_stats[t]["qualified"] is True
    assert eng.state.ledger.bonuses[f"streak:{t}"] == 20
    e4 = _study(col, eng, 3)
    assert "main" not in e4.mission_done and "done" not in e4.sounds
    assert [k for k in eng.state.ledger.bonuses if k.startswith("main:")] == [f"main:{t}"]
    col.undo()
    eng.on_undo()  # back to 3 reviews: still done
    assert f"main:{t}" in eng.state.ledger.bonuses
    col.undo()
    eng.on_undo()  # the answer that reached the target is gone
    assert f"main:{t}" not in eng.state.ledger.bonuses
    assert f"streak:{t}" not in eng.state.ledger.bonuses
    assert eng.state.missions_by_day[t]["main_done"] is False
    assert eng.state.day_stats[t]["qualified"] is False
    e5 = _study(col, eng, 3)
    assert "main" in e5.mission_done


def test_rescued_from_low_retrievability(col, path, monkeypatch):
    _add_due(col, 2)
    monkeypatch.setattr(q, "card_snapshot", lambda col, cid: CardSnap(None, 0.8, 2))
    eng = Engine(col, _cfg(), path, clock=FakeClock())
    ev = _study(col, eng, 3)
    assert ev.rescued is True and ev.mastered is False
    rid = max(eng.state.ledger.answers)
    assert rid in eng.state.rescued
    assert eng.tracker.current.rescued == 1


def test_no_snapshot_means_not_rescued(col, path, monkeypatch):
    _add_due(col, 1)
    monkeypatch.setattr(q, "card_snapshot", lambda col, cid: CardSnap(None, 0.5, 2))
    eng = Engine(col, _cfg(), path, clock=FakeClock())
    card = col.sched.getCard()
    states = col._backend.get_scheduling_states(card.id)
    col.sched.answer_card(col.sched.build_answer(card=card, states=states, rating=2))
    ev = eng.on_answer(card.id, 3)
    assert ev.rescued is False and eng.state.rescued == {}


def test_mastered_when_stability_crosses_threshold(col, path, monkeypatch):
    _add_due(col, 3)
    snaps = iter([CardSnap(10.0, 0.95, 2), CardSnap(30.0, 1.0, 2)])
    monkeypatch.setattr(q, "card_snapshot", lambda col, cid: next(snaps))
    eng = Engine(col, _cfg(), path, clock=FakeClock())
    ev = _study(col, eng, 3)
    assert ev.mastered is True and ev.rescued is False
    assert ev.sounds == ["good", "mastered"]
    assert list(eng.state.mastered.values()) == [col.db.scalar("select cid from revlog")]


_VIEW_KEYS = {"level", "rank", "into", "needed", "total_xp", "xp_today", "xp_before_today",
              "streak", "week", "missions", "objective", "pomodoro", "session_xp",
              "diminished", "hints"}


def test_today_view_keys_and_json(col, path):
    _add_due(col, 3)
    eng = Engine(col, _cfg(), path, clock=FakeClock())
    _study(col, eng, 3)
    v = eng.today_view()
    assert set(v) == _VIEW_KEYS
    json.dumps(v)
    assert v["xp_today"] >= 11 and v["session_xp"] == 11
    assert set(v["streak"]) == {"current", "best", "freezes"}
    assert len(v["week"]) == 7 and v["week"][-1]["state"] in ("today", "done")
    assert all(w["label"] in "stqd" for w in v["week"])
    assert v["missions"][0]["type"] == "main"
    assert all(set(m) == {"type", "text", "progress", "target", "done"} for m in v["missions"])
    assert len(v["missions"]) == 3
    assert v["pomodoro"] == {"phase": "idle", "remaining_s": 0, "cycle": 0}
    assert v["objective"] is None and v["hints"] == []


def test_today_view_objective_countdown(col, path):
    eng = Engine(col, _cfg(), path, clock=FakeClock())
    eng.state.objectives = [{"id": "o1", "name": "CGU", "exam_date": "2099-01-01"}]
    eng.state.active_objective = "o1"
    assert eng.today_view()["objective"].startswith("CGU · ")


_PAYLOAD_KEYS = {"session_xp", "answers", "acc", "duration_s", "level_before", "level_after",
                 "main_bonus", "streak", "streak_bonus", "rescued", "mastered_new", "badge",
                 "records", "tomorrow_due", "fits_budget"}


def test_end_session_popup_threshold(col, path):
    _add_due(col, 25)
    clock = FakeClock()
    eng = Engine(col, _cfg(), path, clock=clock)
    for _ in range(9):
        _study(col, eng, 3)
    assert eng.end_session("left_reviewer") is None
    assert len(eng.state.sessions) == 1
    assert store.load(path).sessions[0]["answers"] == 9
    evs = [_study(col, eng, 3) for _ in range(10)]
    p = eng.end_session("left_reviewer")
    assert set(p) == _PAYLOAD_KEYS
    json.dumps(p)
    assert p["answers"] == 10 and p["acc"] == 100
    assert p["session_xp"] == sum(e.xp for e in evs)
    assert p["badge"] == "Preciso"
    assert eng.state.badges_by_day[col.sched.today] == "Preciso"
    assert set(p["level_before"]) == {"level", "into", "needed"}
    total = eng.state.ledger.total(eng.state.bootstrap_xp)
    after = level_from_total(total)
    assert p["level_after"] == {"level": after.level, "into": after.into, "needed": after.needed}
    assert p["tomorrow_due"] == 0 and p["fits_budget"] is True
    assert len(eng.state.sessions) == 2
    assert eng.end_session("left_reviewer") is None


@pytest.mark.parametrize("back, m_used, left", [(3, 1.0, 0), (4, 0.6, 2), (5, 0.6, 2)])
def test_comeback_needs_three_missed_days(col, path, back, m_used, left):
    # last review at t-3 leaves 2 missed days (no comeback); t-4 leaves 3 (comeback)
    cid = _add_due(col, 3)[0]
    seed_revlog(col, [{"id": q.day_start_ms(col) - back * DAY + 1000, "cid": cid, "ease": 3}])
    eng = Engine(col, _cfg(), path, clock=FakeClock())
    eng.today_view()
    t = col.sched.today
    assert eng.state.missions_by_day[t]["m_used"] == m_used
    assert eng.state.comeback_days_left == left


def _answer_cid(col, eng: Engine, cid: int, ease: int):
    card = col.get_card(cid)
    card.start_timer()
    eng.before_show(cid)
    states = col._backend.get_scheduling_states(cid)
    col.sched.answer_card(col.sched.build_answer(card=card, states=states, rating=ease - 1))
    return eng.on_answer(cid, ease)


def _add_new(col, n: int) -> list[int]:
    ids = []
    for i in range(n):
        note = col.new_note(col.models.by_name("Basic"))
        note["Front"], note["Back"] = f"n{i}", "a"
        col.add_note(note, col.decks.id("Default"))
        ids.append(note.cards()[0].id)
    return ids


def test_undo_keeps_due_zero_qualification_from_earlier_answer(col, path):
    rev, new = _add_due(col, 2), _add_new(col, 2)
    eng = Engine(col, _cfg(), path, clock=FakeClock())
    eng.today_view()
    t = col.sched.today
    for cid in rev:
        _answer_cid(col, eng, cid, 3)
    assert q.due_today(col) == 0
    assert eng.state.day_stats[t]["qualified"] is True
    assert f"streak:{t}" in eng.state.ledger.bonuses
    _answer_cid(col, eng, new[0], 1)
    _answer_cid(col, eng, new[1], 3)
    assert q.due_today(col) > 0
    col.undo()
    eng.on_undo()
    assert len(eng.state.ledger.answers) == 3
    assert eng.state.day_stats[t]["qualified"] is True
    assert eng.state.day_stats[t]["due_zero"] is True
    assert f"streak:{t}" in eng.state.ledger.bonuses


def test_undo_without_removed_answer_changes_nothing(col, path):
    _add_due(col, 5)
    eng = Engine(col, _cfg(budget_min=1.5), path, clock=FakeClock())
    for _ in range(3):
        _study(col, eng, 3)
    t = col.sched.today
    bonuses = dict(eng.state.ledger.bonuses)
    assert f"main:{t}" in bonuses
    eng.on_undo()  # e.g. state_did_undo after a note edit: revlog untouched
    assert eng.state.combo.count == 3
    assert eng.state.ledger.bonuses == bonuses
    assert eng.state.missions_by_day[t]["main_done"] is True
    assert eng.state.day_stats[t]["qualified"] is True


def test_pomodoro_focus_done_counts(col, path):
    _add_due(col, 3)  # keeps the "zerar" main mission open
    eng = Engine(col, _cfg(), path, clock=FakeClock())
    assert eng.pomo_start() == {"phase": "focus", "remaining_s": 1200, "cycle": 0}
    assert eng.pomo_pause()["phase"] == "paused"
    assert eng.pomo_resume()["phase"] == "focus"
    assert eng.pomo_tick(600, 0) == []
    assert eng.pomo_tick(600, 0) == ["focus_done", "mission:focus"]
    t = col.sched.today
    assert eng.state.ledger.bonuses[f"side:{t}:focus"] == 30
    assert eng.state.day_stats[t]["pomodoros"] == 1
    assert store.load(path).day_stats[t]["pomodoros"] == 1
    assert eng.pomo_stop() == {"phase": "idle", "remaining_s": 0, "cycle": 0}


def test_pomodoro_focus_bonus_can_level_up(col, path):
    _add_due(col, 3)
    eng = Engine(col, _cfg(), path, clock=FakeClock())
    eng.today_view()
    eng.state.bootstrap_xp = 390
    eng.pomo_start()
    assert eng.pomo_tick(1200, 0) == ["focus_done", "mission:focus", "level"]


def test_end_session_clears_snapshots(col, path):
    _add_due(col, 3)
    eng = Engine(col, _cfg(), path, clock=FakeClock())
    _study(col, eng, 3)
    eng.before_show(col.sched.getCard().id)
    eng.end_session("left_reviewer")
    assert eng._snaps == {}
