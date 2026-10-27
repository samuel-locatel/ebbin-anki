"""JSON persistence of add-on state, one file per profile."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field, fields
from pathlib import Path

from ebbin.core.rules import Combo, XpLedger

_INT_KEYED = ("missions_by_day", "rescued", "mastered", "badges_by_day", "day_stats")


def _fsrs_default() -> dict:
    return {"params_hash": "", "revlog_count": 0}


@dataclass
class State:
    schema: int = 1
    bootstrap_xp: int = 0
    ledger: XpLedger = field(default_factory=XpLedger)
    combo: Combo = field(default_factory=Combo)
    combo_day: int = -1
    freezes: int = 0
    freeze_used_days: list[int] = field(default_factory=list)
    m: float = 1.0
    met_streak: int = 0
    miss_streak: int = 0
    missions_by_day: dict[int, dict] = field(default_factory=dict)
    comeback_days_left: int = 0
    sessions: list[dict] = field(default_factory=list)
    rescued: dict[int, int] = field(default_factory=dict)
    mastered: dict[int, int] = field(default_factory=dict)
    records: dict = field(default_factory=dict)
    badges_by_day: dict[int, str] = field(default_factory=dict)
    objectives: list[dict] = field(default_factory=list)
    active_objective: str | None = None
    fsrs_reminder: dict = field(default_factory=_fsrs_default)
    last_weekly_summary_day: int = -1
    imported_hashes: list[str] = field(default_factory=list)
    day_stats: dict[int, dict] = field(default_factory=dict)
    installed_day: int = -1
    dismissed_hints: dict[str, int] = field(default_factory=dict)
    weekly_shown_day: int = -1  # Anki day the weekly summary was first shown


def _to_dict(state: State) -> dict:
    d = {f.name: getattr(state, f.name) for f in fields(State)}
    d["ledger"] = state.ledger.to_dict()
    d["combo"] = state.combo.to_dict()
    return d


def _from_dict(d: dict) -> State:
    known = {f.name for f in fields(State)}
    kw = {k: v for k, v in d.items() if k in known}
    if "ledger" in kw:
        kw["ledger"] = XpLedger.from_dict(kw["ledger"])
    if "combo" in kw:
        kw["combo"] = Combo.from_dict(kw["combo"])
    for name in _INT_KEYED:
        if name in kw:
            kw[name] = {int(k): v for k, v in kw[name].items()}
    if "fsrs_reminder" in kw:
        kw["fsrs_reminder"] = {**_fsrs_default(), **kw["fsrs_reminder"]}
    return State(**kw)


def path_for(addon_dir: Path, profile: str) -> Path:
    return Path(addon_dir) / "user_files" / f"{profile}.json"


def load(path: Path) -> State:
    path = Path(path)
    if not path.exists():
        return State()
    try:
        return _from_dict(json.loads(path.read_text(encoding="utf-8")))
    except (ValueError, TypeError, AttributeError, OSError):
        try:
            os.replace(path, path.with_name(f"{path.stem}.corrupt-{int(time.time())}.json"))
        except OSError:
            pass
        return State()


def save(state: State, path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(_to_dict(state), ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)
