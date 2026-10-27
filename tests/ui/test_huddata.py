import json
from pathlib import Path

import pytest

from ebbin.data import queries as q
from ebbin.ui.engine import Engine
from ebbin.ui.huddata import hud_view, progress
from tests.data.test_engine import _add_due, _study

CFG = json.loads((Path(__file__).parents[2] / "ebbin" / "config.json").read_text())


@pytest.mark.parametrize("done, target, met, exp", [
    (21, 37, False, {"done": 21, "target": 37, "left": 16, "met": False, "pct": 56.8}),
    (0, 37, False, {"done": 0, "target": 37, "left": 37, "met": False, "pct": 0.0}),
    (37, 37, True, {"done": 37, "target": 37, "left": 0, "met": True, "pct": 100.0}),
    (0, 0, False, {"done": 0, "target": 0, "left": 0, "met": False, "pct": 100.0}),
    (3, 5, True, {"done": 3, "target": 5, "left": 2, "met": True, "pct": 100.0}),
    (-2, -1, False, {"done": 0, "target": 0, "left": 0, "met": False, "pct": 100.0}),
])
def test_progress(done, target, met, exp):
    assert progress(done, target, met) == exp


def test_hud_view_follows_the_main_mission():
    view = {"missions": [{"type": "main", "progress": 21, "target": 37, "done": False},
                         {"type": "combo", "progress": 9, "target": 10, "done": False}]}
    assert hud_view(view) == progress(21, 37, False)
    assert hud_view({"missions": []}) == progress(0, 0, False)


def _set_main(eng, main: dict, done: bool = False) -> None:
    eng.ensure_day()
    t = q.today(eng.col)
    eng.state.missions_by_day[t]["main"] = main
    eng.state.missions_by_day[t]["main_done"] = done


def test_hud_view_clear_and_new_uses_mission_progress_not_answer_count(col, tmp_path):
    _add_due(col, 3)
    eng = Engine(col, CFG, tmp_path / "p.json")
    _set_main(eng, {"kind": "clear_and_new", "target_reviews": 3, "target_new": 2})
    _study(col, eng, 1)  # an "Errei" leaves the card due: mission progress stays 0
    _study(col, eng, 1)
    view = eng.today_view()
    main = view["missions"][0]
    h = hud_view(view)
    assert (h["done"], h["target"], h["met"]) == (main["progress"], main["target"], False)
    assert h["target"] == 5 and h["done"] < 2  # 2 answers given, mission barely moved
    json.dumps(h)


def test_hud_view_met_iff_main_mission_done(col, tmp_path):
    _add_due(col, 3)
    eng = Engine(col, CFG, tmp_path / "p.json")
    _set_main(eng, {"kind": "clear_and_new", "target_reviews": 3, "target_new": 2}, done=True)
    h = hud_view(eng.today_view())
    assert h["met"] is True and h["done"] == h["target"] == 5 and h["pct"] == 100.0
