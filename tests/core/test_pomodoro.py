from ebbin.core.pomodoro import resume, start, stop, tick

CFG = {"focus": 20, "short": 5, "long": 15, "cycles": 4, "idle_pause_s": 120}


def test_focus_to_short_to_idle():
    p = start(CFG)
    assert (p.phase, p.remaining_s, p.cycle) == ("focus", 1200, 0)
    p, ev = tick(p, 600, 0, CFG)
    assert ev == [] and p.remaining_s == 600
    p, ev = tick(p, 600, 0, CFG)
    assert ev == ["focus_done"] and p.phase == "short" and p.remaining_s == 300 and p.cycle == 1
    p, ev = tick(p, 300, 0, CFG)
    assert ev == ["break_done"] and p.phase == "idle" and p.cycle == 1
    assert tick(p, 50, 0, CFG) == (p, [])


def test_long_break_on_4th():
    p = start(CFG, cycle=3)
    p, ev = tick(p, 1200, 0, CFG)
    assert p.phase == "long" and p.remaining_s == 900 and p.cycle == 4


def test_idle_autopause_and_resume():
    p = start(CFG)
    p, _ = tick(p, 100, 0, CFG)
    p, ev = tick(p, 10, 120, CFG)
    assert ev == ["auto_paused"] and p.phase == "paused" and p.paused_from == "focus"
    assert p.remaining_s == 1100
    assert tick(p, 10, 0, CFG) == (p, [])
    q = resume(p)
    assert q.phase == "focus" and q.remaining_s == 1100


def test_stop():
    p, _ = tick(start(CFG, cycle=2), 5, 0, CFG)
    q = stop(p)
    assert q.phase == "idle" and q.cycle == 0
