"""Payload -> view-model for the end-of-session pop-up (no aqt imports)."""
from __future__ import annotations


def format_duration(seconds: int) -> str:
    s = max(0, int(seconds))
    return f"{s // 60}m{s % 60:02d}s"


def _pct(part: float, whole: float) -> float:
    return max(0.0, min(100.0, part / whole * 100)) if whole > 0 else 0.0


def build_view(payload: dict, budget_min: int) -> dict:
    before, after = payload["level_before"], payload["level_after"]
    level_up = after["level"] > before["level"]
    needed = after["needed"]
    # On level-up the bar shows the new level: nothing "before", everything gained.
    a_pct = 0.0 if level_up else _pct(before["into"], needed)
    total_pct = _pct(after["into"], needed)
    b_pct = max(0.0, total_pct - a_pct)

    rows = []
    if payload.get("main_bonus", 0) > 0:
        rows.append({"mark": "✓", "text": "Desafio cumprido", "delta": f"+{payload['main_bonus']}"})
    if payload.get("streak_bonus", 0) > 0:
        rows.append({"mark": str(payload["streak"]), "text": "dias seguidos",
                     "delta": f"+{payload['streak_bonus']}"})
    if payload.get("rescued", 0) > 0:
        rows.append({"mark": "↺", "text": f"{payload['rescued']} memórias resgatadas", "delta": ""})
    if payload.get("mastered_new", 0) > 0:
        rows.append({"mark": "★", "text": f"{payload['mastered_new']} novos dominados", "delta": ""})

    due = payload["tomorrow_due"]
    tail = f"cabe nos {budget_min} min" if payload["fits_budget"] else f"passa dos {budget_min} min"
    return {
        "xp": payload["session_xp"],
        "summary": (f"{payload['answers']} revisões · {int(payload['acc'] + 0.5)}% de acerto · "
                    f"{format_duration(payload['duration_s'])}"),
        "level": after["level"],
        "level_up": level_up,
        "level_up_text": f"nível {after['level']}!" if level_up else "",
        "level_text": f"nível {after['level']}",
        "remaining_text": f"faltam {max(0, needed - after['into'])} XP p/ o nível {after['level'] + 1}",
        "a_pct": a_pct,
        "b_pct": b_pct,
        "rows": rows,
        "badge": payload.get("badge") or None,
        "records": [f"novo recorde: {r}" for r in payload.get("records") or []],
        "footer": f"Amanhã: ~{due} revisões previstas · {tail}",
    }


def theme_class(night_mode: bool, dark_theme: str) -> str:
    """Same rule as ebbinSketch.themeClass, for the popup's initial HTML (no light flash)."""
    if not night_mode:
        return ""
    return "slate" if dark_theme == "slate" else "night"
