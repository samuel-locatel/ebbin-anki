"""Reviewer HUD progress bar: the main mission's own progress (no aqt imports)."""
from __future__ import annotations


def progress(done: int, target: int, met: bool) -> dict:
    """Numbers for the bar and its label ("21 de 37 · faltam 16" / "meta batida")."""
    done, target = max(0, int(done)), max(0, int(target))
    pct = 100.0 if met or target == 0 else round(min(1.0, done / target) * 100, 1)
    return {"done": done, "target": target, "left": max(0, target - done), "met": bool(met),
            "pct": pct}


def hud_view(view: dict) -> dict:
    """From today_view: missions[0] is the main mission, already consistent with its completion
    (clear_and_new counts due cleared + new learned, not raw answers)."""
    missions = view.get("missions") or []
    if not missions:
        return progress(0, 0, False)
    main = missions[0]
    return progress(main["progress"], main["target"], main["done"])
