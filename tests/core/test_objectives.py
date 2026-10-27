from datetime import date

import pytest

from ebbin.core.objectives import (
    Objective, activate, archive, countdown_text, days_left, new_pace, suggest_new_today,
)

TODAY = date(2026, 10, 26)


def obj(i="a", name="Prova", exam="2026-12-06", archived=False):
    return Objective(id=i, name=name, exam_date=exam, deck_roots=["X"], archived=archived)


def test_days_left():
    assert days_left(obj(), TODAY) == 41
    assert days_left(obj(exam=None), TODAY) is None
    assert days_left(obj(exam="2026-10-20"), TODAY) == -6


def test_new_pace():
    assert new_pace(325, 41) == 10
    assert new_pace(10, None) is None
    assert new_pace(10, 3) == 10


def test_suggest_new_today():
    assert suggest_new_today(37, 22) == 5
    assert suggest_new_today(10, 20) == 0


def test_countdown_text():
    assert countdown_text(obj(), TODAY) == "Prova · 41 dias"
    assert countdown_text(obj(exam="2026-10-26"), TODAY) == "Prova · é hoje"
    assert countdown_text(obj(exam="2026-10-01"), TODAY) == "Prova · prova passou"
    assert countdown_text(obj(exam=None), TODAY) is None


def test_activate_unarchives_target_only():
    objs = [obj("a", archived=True), obj("b")]
    out = activate(objs, "a")
    assert not out[0].archived and out[1] == objs[1]
    assert objs[0].archived
    with pytest.raises(KeyError):
        activate(objs, "zz")


def test_archive():
    objs = [obj("a"), obj("b")]
    out = archive(objs, "a", {"x": 1})
    assert out[0].archived and out[0].archived_summary == {"x": 1}
    assert not out[1].archived
    with pytest.raises(KeyError):
        archive(objs, "zz", {})


def test_roundtrip():
    o = Objective("a", "n", None, ["r"], True, {"k": 1})
    assert Objective.from_dict(o.to_dict()) == o
