from ebbin.core.challenge import (
    DayMissions, MainMission, SideMission, adapt, capacity, comeback_m, evaluate,
    main_text, make_main, make_sides,
)
from ebbin.core.models import ReviewRow


def row(i, ease=3, time_ms=10000, type=1, day=100, deck="A::B", cid=None):
    return ReviewRow(i, cid or i, 1, deck, "nt", "", ease, time_ms, type, day, 10, 1)


def test_capacity():
    assert capacity(20, 32.3) == 37
    assert capacity(20, 30.0) == 40


def test_make_main():
    assert make_main(37, 1.0, 60, 325) == MainMission("reviews", 37, 0)
    assert make_main(37, 1.0, 10, 325) == MainMission("clear_and_new", 10, 9)
    assert make_main(37, 1.0, 10, 3).target_new == 3
    assert main_text(MainMission("reviews", 37)) == "Revisar 37 cards"
    assert main_text(MainMission("clear_and_new", 10, 9)) == \
        "Zerar as revisões (10) e aprender 9 novos"


def test_adapt():
    assert adapt(1.0, 0, 0, True) == (1.0, 1, 0)
    assert adapt(1.0, 2, 0, True) == (1.1, 0, 0)
    assert adapt(1.3, 2, 0, True) == (1.3, 0, 0)
    assert adapt(1.0, 0, 1, False) == (0.9, 0, 0)
    assert adapt(0.7, 0, 1, False) == (0.7, 0, 0)
    assert adapt(1.0, 2, 0, False) == (1.0, 0, 1)


def test_comeback():
    assert comeback_m(3, 0) == 0.6 and comeback_m(5, 2) == 1.0
    assert comeback_m(2, 0) is None and comeback_m(3, 3) is None


def test_sides_empty_history():
    s = make_sides(5, [], set(), [])
    assert sorted(x.type for x in s) == ["combo", "focus"]
    combo = next(x for x in s if x.type == "combo")
    assert combo.target == 5 and combo.text == "5 acertos seguidos"


def test_sides_deterministic_no_repeat():
    rows = [row(i, ease=3 if i % 5 else 1, time_ms=10000, day=90 + i % 14) for i in range(60)]
    weak = ["X::Anat", "Y::Z::Fisio"]
    for d in range(200, 230):
        a = make_sides(d, rows, {"combo", "focus"}, weak)
        assert a == make_sides(d, rows, {"combo", "focus"}, weak)
        types = [x.type for x in a]
        assert len(set(types)) == 2 and not set(types) & {"combo", "focus"}
    # forced fill from yesterday's
    b = make_sides(1, [], {"combo"}, [])
    assert sorted(x.type for x in b) == ["combo", "focus"]


def test_sides_targets_and_text():
    rows = [row(i, ease=3, time_ms=10000) for i in range(20)]
    rows[3] = row(3, ease=1)
    # sample picks 2 of 5 per day; collect all types over many days
    seen = {}
    for d in range(50):
        for x in make_sides(d, rows, set(), ["X::Anat", "Y::Fisio"]):
            seen[x.type] = x
    assert seen["accuracy"].text == "Acerto ≥ 95%"
    assert seen["pace"].text == "Ritmo ≤ 9s por card"
    assert seen["weak"].text == "10 cards de Anat e Fisio"
    assert seen["weak"].decks == ("X::Anat", "Y::Fisio")
    assert seen["focus"].text == "Termine 1 pomodoro"


def test_evaluate_main_and_roundtrip():
    dm = DayMissions(100, MainMission("reviews", 37), [], m_used=1.0)
    assert not evaluate(dm, [row(i) for i in range(36)], 5, 0, 0).main_done
    out = evaluate(dm, [row(i) for i in range(37)], 5, 0, 0)
    assert out.main_done and not dm.main_done
    assert DayMissions.from_dict(out.to_dict()) == out


def test_evaluate_clear_and_sides():
    sides = [SideMission("weak", 10, "t", ("X::Anat", "Y")), SideMission("combo", 5, "t"),
             SideMission("focus", 1, "t"), SideMission("accuracy", 0.9, "t"),
             SideMission("pace", 12, "t")]
    dm = DayMissions(100, MainMission("clear_and_new", 3, 2), sides)
    rows = [row(i, type=0, deck="X::Anat::Sub") for i in range(10)] + \
           [row(20 + i, ease=1, deck="Other") for i in range(5)]
    out = evaluate(dm, rows, 0, 5, 1)
    assert out.main_done
    assert set(out.sides_done) == {"weak", "combo", "focus", "pace"}
    assert not evaluate(dm, rows, 1, 4, 0).main_done


def test_main_text_zero_new():
    assert main_text(MainMission("clear_and_new", 12, 0)) == "Zerar as revisões (12)"


def _sides_by_type(rows):
    seen = {}
    for d in range(60):
        for x in make_sides(d, rows, set(), ["X::A", "Y::B"]):
            seen[x.type] = x
    return seen


def test_pace_target_is_rounded_half_up_and_checked_rounded():
    rows = [row(i, time_ms=31000) for i in range(20)]  # 0.9 * 31 = 27.9
    pace = _sides_by_type(rows)["pace"]
    assert pace.target == 28 and isinstance(pace.target, int)
    assert pace.text == "Ritmo ≤ 28s por card"
    half = [row(i, time_ms=15000) for i in range(20)]  # 13.5 -> 14 (half-up)
    assert _sides_by_type(half)["pace"].target == 14
    dm = DayMissions(100, MainMission("reviews", 999), [pace])
    avg_ok = [row(i, time_ms=27900) for i in range(15)]  # 27.9 s average
    assert "pace" in evaluate(dm, avg_ok, 0, 0, 0).sides_done
    avg_bad = [row(i, time_ms=28100) for i in range(15)]
    assert "pace" not in evaluate(dm, avg_bad, 0, 0, 0).sides_done


def test_accuracy_target_is_the_shown_percent():
    rows = [row(i, ease=3) for i in range(20)]
    rows[0] = row(0, ease=1)  # 95% -> min(.95, .98)
    rows[1] = row(1, ease=1)  # 90% -> .93
    acc = _sides_by_type(rows)["accuracy"]
    assert acc.target == 0.93 and acc.text == "Acerto ≥ 93%"
    dm = DayMissions(100, MainMission("reviews", 999), [acc])
    ok = [row(i, ease=3) for i in range(14)] + [row(99, ease=1)]  # 14/15 = 93.33%
    assert "accuracy" in evaluate(dm, ok, 0, 0, 0).sides_done
