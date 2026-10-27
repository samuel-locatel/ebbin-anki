from ebbin.core.models import ReviewRow
from ebbin.core.streak import compute, qualified_days_from_history


def days(a, b):
    return set(range(a, b + 1))


def test_six_days():
    r = compute(days(1, 6), today=6)
    assert (r.current, r.best, r.freezes, r.freeze_used_days) == (6, 6, 0, [])


def test_seven_earns_freeze():
    assert compute(days(1, 7), today=7).freezes == 1


def test_fourteen_earns_two():
    assert compute(days(1, 14), today=14).freezes == 2


def test_twenty_one_capped_at_two():
    r = compute(days(1, 21), today=21)
    assert r.freezes == 2 and r.current == 21


def test_gap_of_one_uses_freeze():
    r = compute(days(1, 7) | {9}, today=9)
    assert r.current == 8
    assert r.freeze_used_days == [8]
    assert r.freezes == 0


def test_gap_of_two_after_seven_resets():
    r = compute(days(1, 7) | {10}, today=10)
    assert r.freeze_used_days == [8]
    assert r.current == 1
    assert r.best == 7
    assert r.freezes == 0


def test_fourteen_then_two_day_gap_continues():
    r = compute(days(1, 14) | {17}, today=17)
    assert r.freeze_used_days == [15, 16]
    assert r.current == 15
    assert r.freezes == 0


def test_today_unqualified_does_not_break():
    r = compute(days(1, 5), today=6)
    assert r.current == 5 and r.freeze_used_days == []


def test_missed_yesterday_resets_without_freeze():
    r = compute(days(1, 5), today=7)
    assert r.current == 0 and r.best == 5


def test_missed_yesterday_consumes_freeze():
    r = compute(days(1, 7), today=9)
    assert r.current == 7 and r.freeze_used_days == [8] and r.freezes == 0


def test_freezes_start():
    r = compute({1, 3}, today=3, freezes_start=1)
    assert r.current == 2 and r.freeze_used_days == [2]


def test_empty():
    r = compute(set(), today=5)
    assert (r.current, r.best, r.freezes, r.freeze_used_days) == (0, 0, 0, [])


def test_qualified_days_from_history():
    def row(day):
        return ReviewRow(id=day, cid=1, did=1, deck="d", notetype="n", tags="", ease=3,
                         time_ms=1000, type=1, day=day, hour=10, n_items=1)
    assert qualified_days_from_history([row(3), row(3), row(5)]) == {3, 5}
