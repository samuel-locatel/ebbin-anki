"""Mastery state, stars and rescued memories (pure; no anki imports)."""
from __future__ import annotations


def card_state(ctype: int, queue: int, stability: float | None, mastered_days: float = 21) -> str:
    if ctype == 0:
        return "novo"
    if ctype in (1, 3):
        return "aprendendo"
    if stability is not None and stability >= mastered_days:
        return "dominado"
    return "firme"


def became_mastered(before: float | None, after: float | None, mastered_days: float = 21) -> bool:
    return (before is None or before < mastered_days) and after is not None and after >= mastered_days


def is_rescued(r_before: float | None, ease: int, threshold: float = 0.85) -> bool:
    return r_before is not None and r_before < threshold and ease > 1


def stars(mastered: int, total: int) -> int:
    if total <= 0:
        return 0
    pct = mastered / total
    if pct >= 0.8:
        return 3
    if pct >= 0.5:
        return 2
    if pct >= 0.25:
        return 1
    return 0
