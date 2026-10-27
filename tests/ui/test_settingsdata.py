import json
from copy import deepcopy

import pytest

from ebbin.ui import settingsdata as sd
from tests.ui.test_hints import CFG


def test_roundtrip_and_overlay():
    assert sd.validate_config(deepcopy(CFG), CFG) == CFG
    out = sd.validate_config({"easy_cap": {"ratio": 2}, "budget_min": 30}, CFG)
    assert out["easy_cap"] == {**CFG["easy_cap"], "ratio": 2.0} and out["budget_min"] == 30
    assert CFG["easy_cap"]["ratio"] == 1.5  # base untouched


@pytest.mark.parametrize("patch", [
    {"easy_cap": {"ratio": 1.1}}, {"easy_cap": {"ratio": 3.1}}, {"easy_cap": {"ratio": "x"}},
    {"sounds": {"volume": 1.5}}, {"sounds": {"volume": True}},
    {"pomodoro": {"focus": 0}}, {"pomodoro": {"cycles": 2.5}}, {"pomodoro": {"idle_pause_s": 5}},
    {"budget_min": 0}, {"budget_min": None}, {"mastered_days": 0}, {"rescued_r": 1.0},
    {"dark_theme": "neon"}, {"import": {"dupe": "x"}}, {"import": {"dest": "  "}},
    {"auto_new_per_day": "yes"}, {"pomodoro": "x"}, {"skin": "yes"}, {"skin": 1}, {"skin": None},
])
def test_invalid_rejected(patch):
    with pytest.raises(ValueError):
        sd.validate_config(patch, CFG)


def test_skin_is_a_bool_defaulting_to_true():
    assert CFG["skin"] is True
    assert sd.validate_config({"skin": False}, CFG)["skin"] is False
    old = {k: v for k, v in CFG.items() if k != "skin"}  # config saved before the skin existed
    assert sd.sanitize_config(old, CFG) == (CFG, [])
    out, bad = sd.sanitize_config({**CFG, "skin": "on"}, CFG)
    assert out["skin"] is True and bad == ["skin"]


def test_non_dict_and_webview_config():
    with pytest.raises(ValueError):
        sd.validate_config([], CFG)
    assert sd.webview_config(CFG) == {"sounds_enabled": True, "volume": 0.8, "dark_theme": "night"}


def test_export_json(tmp_path):
    p = tmp_path / "s.json"
    p.write_text('{"a": "ç"}', encoding="utf-8")
    assert json.loads(sd.export_json(p)) == {"a": "ç"}


def test_sanitize_config_falls_back_per_invalid_key():
    import json
    from pathlib import Path
    from ebbin.ui.settingsdata import sanitize_config
    d = json.loads((Path(__file__).parents[2] / "ebbin" / "config.json").read_text())
    ok, bad = sanitize_config(d, d)
    assert ok == d and bad == []
    mine = json.loads(json.dumps(d))
    mine["pomodoro"]["focus"] = 9999
    mine["pomodoro"]["short"] = 7
    mine["dark_theme"] = "neon"
    mine["budget_min"] = 45
    out, bad = sanitize_config(mine, d)
    assert sorted(bad) == ["dark_theme", "pomodoro.focus"]
    assert out["pomodoro"]["focus"] == d["pomodoro"]["focus"] and out["pomodoro"]["short"] == 7
    assert out["dark_theme"] == d["dark_theme"] and out["budget_min"] == 45
    assert sanitize_config("junk", d) == (d, ["*"])
