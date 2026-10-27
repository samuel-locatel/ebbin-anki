import json

from ebbin.core.rules import Combo, XpLedger
from ebbin.data import store
from ebbin.data.store import State


def _populated() -> State:
    return State(
        bootstrap_xp=120,
        ledger=XpLedger({1001: 10, 1002: 15}, {"mission:5": 40}),
        combo=Combo(7),
        combo_day=5,
        freezes=2,
        freeze_used_days=[3, 4],
        m=1.2,
        met_streak=3,
        miss_streak=1,
        missions_by_day={5: {"a": 1}, 6: {"b": [1, 2]}},
        comeback_days_left=2,
        sessions=[{"start": 1, "end": 2}],
        rescued={111: 1, 112: 2},
        mastered={211: 3},
        records={"best": 9},
        badges_by_day={5: "gold", 6: "silver"},
        objectives=[{"id": "o1"}],
        active_objective="o1",
        fsrs_reminder={"params_hash": "abc", "revlog_count": 42},
        last_weekly_summary_day=4,
        imported_hashes=["h1", "h2"],
        day_stats={5: {"qualified": True, "pomodoros": 2}},
        installed_day=4,
        weekly_shown_day=6,
        dismissed_hints={"load:5": 5, "weekly:3": 6},
    )


def test_round_trip(tmp_path):
    p = tmp_path / "p.json"
    s = _populated()
    store.save(s, p)
    assert store.load(p) == s


def test_missing_returns_default(tmp_path):
    s = store.load(tmp_path / "nope.json")
    assert s == State()
    assert s.fsrs_reminder == {"params_hash": "", "revlog_count": 0}


def test_corrupt_renamed(tmp_path):
    p = tmp_path / "p.json"
    p.write_text("{")
    assert store.load(p) == State()
    assert not p.exists()
    assert len(list(tmp_path.glob("p.corrupt-*.json"))) == 1


def test_int_keys_stored_as_str_restored_as_int(tmp_path):
    p = tmp_path / "p.json"
    store.save(_populated(), p)
    raw = json.loads(p.read_text())
    assert "5" in raw["missions_by_day"]
    assert "1001" in raw["ledger"]["answers"]
    loaded = store.load(p)
    for d in (loaded.missions_by_day, loaded.rescued, loaded.mastered,
              loaded.badges_by_day, loaded.day_stats, loaded.ledger.answers):
        assert all(isinstance(k, int) for k in d)


def test_path_for(tmp_path):
    assert store.path_for(tmp_path, "Ana") == tmp_path / "user_files" / "Ana.json"


def test_save_creates_parent_dir(tmp_path):
    p = tmp_path / "user_files" / "x.json"
    store.save(State(), p)
    assert store.load(p) == State()


def test_installed_day_round_trips_and_defaults_for_old_files(tmp_path):
    p = tmp_path / "p.json"
    store.save(State(installed_day=17), p)
    assert store.load(p).installed_day == 17
    raw = json.loads(p.read_text())
    del raw["installed_day"]
    p.write_text(json.dumps(raw))
    assert store.load(p).installed_day == -1
