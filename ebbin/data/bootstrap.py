"""First-install XP bootstrap from historical revlog."""
from __future__ import annotations

from ..core.rules import BASE_XP
from . import queries


def initial_xp(col) -> int:
    return sum(BASE_XP[r.ease] for r in queries.reviews_since(col, 0))
