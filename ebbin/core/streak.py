"""Streak and freeze computation (pure)."""
from __future__ import annotations

from dataclasses import dataclass, field

from .models import ReviewRow

FREEZE_EVERY = 7
MAX_FREEZES = 2


@dataclass(frozen=True)
class StreakResult:
    current: int
    best: int
    freezes: int
    freeze_used_days: list[int] = field(default_factory=list)


def qualified_days_from_history(rows: list[ReviewRow]) -> set[int]:
    return {r.day for r in rows}


def compute(qualified_days: set[int], today: int, freezes_start: int = 0) -> StreakResult:
    days = {d for d in qualified_days if d <= today}
    if not days:
        return StreakResult(0, 0, freezes_start, [])
    current = best = 0
    freezes = freezes_start
    used: list[int] = []
    for d in range(min(days), today + 1):
        if d in days:
            current += 1
            best = max(best, current)
            if current % FREEZE_EVERY == 0:
                freezes = min(MAX_FREEZES, freezes + 1)
        elif d == today or current == 0:
            continue
        elif freezes > 0:
            freezes -= 1
            used.append(d)
        else:
            current = 0
    return StreakResult(current, best, freezes, used)
