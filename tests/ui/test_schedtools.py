import json
from pathlib import Path

from ebbin.core.objectives import Objective
from ebbin.data.store import State
from ebbin.ui import schedtools
from tests.conftest import seed_revlog

CFG = json.loads((Path(__file__).parents[2] / "ebbin" / "config.json").read_text())


def _revlog(col, n, base=1_000_000):
    seed_revlog(col, [{"id": base + i, "cid": 1, "ease": 3} for i in range(n)])


def _set_params(col, params):
    conf = col.decks.config_dict_for_deck_id(1)
    conf["fsrsParams6"] = params
    col.decks.update_config(conf)


def test_reminder_threshold_with_empty_params(col):
    st = State()
    _revlog(col, 299)
    assert schedtools.fsrs_reminder_due(col, st) is False
    _revlog(col, 1, base=9_000_000)
    assert schedtools.fsrs_reminder_due(col, st) is True


def test_reminder_hash_change_resets_then_counts_new_reviews(col):
    st = State()
    _revlog(col, 500)
    _set_params(col, [0.1] * 21)
    assert schedtools.fsrs_reminder_due(col, st) is False  # new hash stored
    assert st.fsrs_reminder["revlog_count"] == 500 and st.fsrs_reminder["params_hash"]
    assert schedtools.fsrs_reminder_due(col, st) is False
    _revlog(col, 299, base=9_000_000)
    assert schedtools.fsrs_reminder_due(col, st) is False
    _revlog(col, 1, base=19_000_000)
    assert schedtools.fsrs_reminder_due(col, st) is True
    _set_params(col, [0.2] * 21)  # re-optimized: reset
    assert schedtools.fsrs_reminder_due(col, st) is False
    assert st.fsrs_reminder["revlog_count"] == 800


def _dedicated(col, name):
    did = col.decks.id(name)
    conf = col.decks.add_config_returning_id(f"preset-{name}")
    col.decks.set_config_id_for_deck_dict(col.decks.get(did), conf)
    col.decks.save(col.decks.get(did))
    return did


def test_apply_auto_new_dedicated_preset(col):
    did = _dedicated(col, "Prova")
    obj = Objective(id="o", name="P", exam_date=None, deck_roots=["Prova"])
    st = State()
    on = {**CFG, "auto_new_per_day": True}
    assert schedtools.apply_auto_new(col, st, {**CFG, "auto_new_per_day": False}, obj, 40, 4) is None
    assert schedtools.apply_auto_new(col, st, on, None, 40, 4) is None
    before = col.decks.config_dict_for_deck_id(did)
    r = schedtools.apply_auto_new(col, st, on, obj, 40, 4)
    assert r == {"applied": 12, "skipped_shared": []}
    after = col.decks.config_dict_for_deck_id(did)
    assert after["new"]["perDay"] == 12
    before["new"]["perDay"] = 12
    before["mod"] = after["mod"] = before["usn"] = after["usn"] = 0
    assert before == after
    assert schedtools.apply_auto_new(col, st, on, obj, 90, 0) is None  # once per day
    assert col.decks.config_dict_for_deck_id(did)["new"]["perDay"] == 12


def test_apply_auto_new_shared_preset_untouched(col):
    did = col.decks.id("Prova")  # shares preset 1 with Default
    obj = Objective(id="o", name="P", exam_date=None, deck_roots=["Prova"])
    st = State()
    r = schedtools.apply_auto_new(col, st, {**CFG, "auto_new_per_day": True}, obj, 40, 4)
    assert r == {"applied": None, "skipped_shared": ["Default"]}
    assert col.decks.config_dict_for_deck_id(did)["new"]["perDay"] == 20
    assert st.day_stats[col.sched.today]["auto_new"] is True


def test_apply_auto_new_no_decks_does_not_mark_day(col):
    obj = Objective(id="o", name="P", exam_date=None, deck_roots=["Nada"])
    st = State()
    r = schedtools.apply_auto_new(col, st, {**CFG, "auto_new_per_day": True}, obj, 40, 4)
    assert r == {"applied": None, "skipped_shared": []}
    assert not st.day_stats.get(col.sched.today, {}).get("auto_new")
