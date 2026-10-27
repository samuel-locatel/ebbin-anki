from ebbin.ui.pomo_flow import EndDeferral


def test_focus_done_outside_review_ends_now():
    d, got = EndDeferral(), []
    d.on_focus_done(False, got.append)
    assert got == ["pomodoro"] and not d.pending


def test_focus_done_in_review_waits_for_answer_once():
    d, got = EndDeferral(), []
    d.on_focus_done(True, got.append)
    assert got == []
    d.on_answer(got.append)
    d.on_answer(got.append)
    assert got == ["pomodoro"]


def test_leaving_review_uses_pomodoro_reason_and_clears_flag():
    d, got = EndDeferral(), []
    d.on_focus_done(True, got.append)
    assert d.on_reviewer_end() == "pomodoro"
    d.on_answer(got.append)  # later unrelated session: no stale end
    assert got == []
    assert d.on_reviewer_end() == "left_reviewer"


def test_clear():
    d = EndDeferral()
    d.on_focus_done(True, lambda r: None)
    d.clear()
    assert not d.pending


from ebbin.ui.pomo_flow import AutoResume, TickClock


def test_auto_paused_resumes_on_answer_once():
    a, calls = AutoResume(), []
    a.on_events(["auto_paused"])
    assert a.on_answer("paused", lambda: calls.append(1)) is True
    assert a.on_answer("paused", lambda: calls.append(1)) is False
    assert calls == [1]


def test_manual_pause_never_auto_resumes():
    a, calls = AutoResume(), []
    a.on_events([])
    assert a.on_answer("paused", lambda: calls.append(1)) is False
    assert calls == []


def test_auto_flag_dropped_when_user_resumed_then_paused_manually():
    a, calls = AutoResume(), []
    a.on_events(["auto_paused"])
    a.sync("focus")  # user resumed
    assert a.on_answer("paused", lambda: calls.append(1)) is False
    assert calls == []


def test_tick_clock_whole_seconds_with_carry():
    c = TickClock(100.0)
    assert c.delta(100.6) == 0
    assert c.delta(101.3) == 1  # 1.3 total, 0.3 carried
    assert c.delta(103.5) == 2  # 0.3 + 2.2 = 2.5
    assert c.delta(104.0) == 1  # 0.5 + 0.5 = 1.0
    assert c.delta(103.0) == 0  # clock never goes backwards
