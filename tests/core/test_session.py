from ebbin.core.session import (
    Records, SessionRecord, SessionTracker, badge_for, is_diminished,
    should_popup, update_records,
)


def _rec(**kw):
    d = dict(start_ms=0, end_ms=1, answers=10, correct=5, xp=0, avg_s=10.0,
             rescued=0, mastered=0, max_combo=0, pomodoro=False)
    d.update(kw)
    return SessionRecord(**d)


def _ans(t, at, ease=3, **kw):
    args = dict(xp=10, time_ms=4000, rescued=False, mastered=False, combo=1)
    args.update(kw)
    return t.on_answer(at, ease, **args)


def test_gap_under_5min_same_session():
    t = SessionTracker()
    assert _ans(t, 0) is None
    assert _ans(t, 240_000) is None
    assert t.current.answers == 2


def test_gap_over_5min_splits():
    t = SessionTracker()
    _ans(t, 0)
    _ans(t, 1000, ease=1, rescued=True, mastered=True, combo=7)
    closed = _ans(t, 1000 + 300_001)
    assert closed is not None
    assert (closed.start_ms, closed.end_ms) == (0, 1000)
    assert closed.answers == 2 and closed.correct == 1 and closed.xp == 20
    assert closed.avg_s == 4.0 and closed.rescued == 1 and closed.mastered == 1
    assert closed.max_combo == 7
    assert t.current.start_ms == 301_001 and t.current.answers == 1


def test_close_and_pomodoro_mark():
    t = SessionTracker()
    assert t.close(5) is None
    _ans(t, 100)
    t.mark_pomodoro()
    r = t.close(9999)
    assert r.end_ms == 100 and r.pomodoro
    assert t.current is None


def test_should_popup():
    assert not should_popup(_rec(answers=9), "left_reviewer")
    assert should_popup(_rec(answers=10), "left_reviewer")
    assert should_popup(_rec(answers=3), "pomodoro")


def test_is_diminished():
    assert is_diminished(True, False, 1300, 20)
    assert not is_diminished(False, True, 9999, 20)
    assert is_diminished(True, True, 0, 20)
    assert not is_diminished(True, False, 1200, 20)


def test_badges():
    assert badge_for(_rec(correct=10, rescued=12), None, 50) == "Preciso"
    assert badge_for(_rec(avg_s=3.0), 5.0, 50) == "Relâmpago"
    assert badge_for(_rec(rescued=10), 5.0, 50) == "Resgatador"
    assert badge_for(_rec(answers=50), None, 50) == "Persistente"
    assert badge_for(_rec(answers=9, correct=9), None, 5) is None
    assert badge_for(_rec(), None, 50) is None


def test_records():
    r, ev = update_records(Records(), _rec(max_combo=5), "2026-W44")
    assert ev == [] and r.max_combo == 5
    r, ev = update_records(r, _rec(max_combo=5), "2026-W44")
    assert ev == []
    r, ev = update_records(r, _rec(max_combo=6), "2026-W44")
    assert ev == ["Maior combo"] and r.max_combo == 6


def test_records_pomodoro_and_week():
    r, ev = update_records(Records(), _rec(answers=20, correct=10, pomodoro=True), "w1")
    assert ev == [] and r.most_cards_pomodoro == 20 and r.best_week_accuracy == {"w1": 0.5}
    r, ev = update_records(r, _rec(answers=25, correct=20, pomodoro=True), "w1")
    assert set(ev) == {"Mais cards num pomodoro", "Melhor acerto da semana"}
    r, ev = update_records(r, _rec(answers=19, correct=19), "w1")
    assert ev == [] and r.best_week_accuracy["w1"] == 0.8
    r, ev = update_records(r, _rec(answers=30), "w1")
    assert r.most_cards_pomodoro == 25  # non-pomodoro ignored


def test_dict_roundtrip():
    s = _rec(pomodoro=True)
    assert SessionRecord.from_dict(s.to_dict()) == s
    r = Records(3, {"w": 0.5}, 4)
    assert Records.from_dict(r.to_dict()) == r
