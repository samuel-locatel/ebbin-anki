"""Payload for the deck-browser strip (no aqt imports)."""
from __future__ import annotations

import copy
from dataclasses import asdict

from ebbin.ui.hints import build_hints

STAMP_WINDOW_MS = 600_000  # "+N XP" stamp stays for 10 minutes after a session


def stamp_xp(engine, now_ms: int) -> int:
    sessions = engine.state.sessions
    if not sessions:
        return 0
    last = sessions[-1]
    if now_ms - last.get("end_ms", 0) <= STAMP_WINDOW_MS:
        return int(last.get("xp", 0))
    return 0


def strip_payload(engine, now_ms: int, with_hints: bool = True) -> dict:
    view = engine.today_view()
    view["stamp_xp"] = stamp_xp(engine, now_ms)
    if with_hints:
        before = copy.deepcopy(asdict(engine.state))
        view["hints"] = build_hints(engine.col, engine.state, engine.cfg, view)
        if asdict(engine.state) != before:  # weekly day, fsrs_reminder, auto_new may have changed
            engine.save()
    return {"view": view, "focus_s": engine.cfg["pomodoro"]["focus"] * 60,
            "dark_theme": engine.cfg["dark_theme"]}
