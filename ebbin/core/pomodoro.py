"""Pomodoro state machine (pure)."""
from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Pomo:
    phase: str = "idle"  # idle | focus | short | long | paused
    remaining_s: int = 0
    cycle: int = 0
    paused_from: str | None = None


def start(cfg: dict, cycle: int = 0) -> Pomo:
    return Pomo("focus", cfg["focus"] * 60, cycle, None)


def tick(p: Pomo, dt_s: int, idle_s: int, cfg: dict) -> tuple[Pomo, list[str]]:
    if p.phase == "focus":
        if idle_s >= cfg["idle_pause_s"]:
            return replace(p, phase="paused", paused_from="focus"), ["auto_paused"]
        rem = p.remaining_s - dt_s
        if rem > 0:
            return replace(p, remaining_s=rem), []
        cycle = p.cycle + 1
        if cycle % cfg["cycles"] == 0:
            return Pomo("long", cfg["long"] * 60, cycle, None), ["focus_done"]
        return Pomo("short", cfg["short"] * 60, cycle, None), ["focus_done"]
    if p.phase in ("short", "long"):
        rem = p.remaining_s - dt_s
        if rem > 0:
            return replace(p, remaining_s=rem), []
        return Pomo("idle", 0, p.cycle, None), ["break_done"]
    return p, []


def resume(p: Pomo) -> Pomo:
    if p.phase != "paused" or p.paused_from is None:
        return p
    return replace(p, phase=p.paused_from, paused_from=None)


def stop(p: Pomo) -> Pomo:
    return Pomo("idle", 0, 0, None)
