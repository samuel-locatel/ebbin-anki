import json
from pathlib import Path

from ebbin.ui.engine import Engine
from ebbin.ui.stripdata import STAMP_WINDOW_MS, strip_payload

CFG = json.loads((Path(__file__).parents[2] / "ebbin" / "config.json").read_text())


def test_payload_is_json_with_stamp_and_hints(col, tmp_path):
    eng = Engine(col, CFG, tmp_path / "p.json")
    now = 1_800_000_000_000
    assert strip_payload(eng, now)["view"]["stamp_xp"] == 0
    eng.state.sessions.append({"end_ms": now - 1000, "xp": 412})
    p = strip_payload(eng, now)
    assert p["view"]["stamp_xp"] == 412 and p["focus_s"] == 1200
    assert isinstance(p["view"]["hints"], list)
    json.dumps(p)
    assert strip_payload(eng, now + STAMP_WINDOW_MS + 5000)["view"]["stamp_xp"] == 0


def test_strip_payload_saves_state_when_hints_mutate_it(col, tmp_path):
    eng = Engine(col, {**CFG, "auto_new_per_day": True}, tmp_path / "p.json")
    col.decks.id("Prova")
    from ebbin.core.objectives import Objective
    eng.state.objectives = [Objective(id="o", name="P", exam_date=None, deck_roots=["Prova"]).to_dict()]
    eng.state.active_objective = "o"
    eng.state.last_weekly_summary_day = 10**6
    hints_ = strip_payload(eng, 1)["view"]["hints"]
    assert any(h["id"].startswith("autonew:") for h in hints_)
    from ebbin.data import store
    assert store.load(eng.path).day_stats[col.sched.today]["auto_new"] is True
