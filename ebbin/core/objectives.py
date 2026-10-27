"""Study objectives (pure; no anki imports)."""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field, replace
from datetime import date


@dataclass
class Objective:
    id: str
    name: str
    exam_date: str | None
    deck_roots: list[str] = field(default_factory=list)
    archived: bool = False
    archived_summary: dict | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Objective":
        return cls(
            id=d["id"],
            name=d["name"],
            exam_date=d.get("exam_date"),
            deck_roots=list(d.get("deck_roots", [])),
            archived=bool(d.get("archived", False)),
            archived_summary=d.get("archived_summary"),
        )


def days_left(o: Objective, today_date: date) -> int | None:
    if not o.exam_date:
        return None
    return (date.fromisoformat(o.exam_date) - today_date).days


def new_pace(new_remaining: int, days_left: int | None) -> int | None:
    if days_left is None:
        return None
    return math.ceil(new_remaining / max(1, days_left - 7))


def suggest_new_today(capacity: int, due_today: int) -> int:
    return max(0, (capacity - due_today) // 3)


def _update(objs: list[Objective], oid: str, **changes) -> list[Objective]:
    if not any(o.id == oid for o in objs):
        raise KeyError(oid)
    return [replace(o, **changes) if o.id == oid else o for o in objs]


def activate(objs: list[Objective], oid: str) -> list[Objective]:
    return _update(objs, oid, archived=False)


def archive(objs: list[Objective], oid: str, summary: dict) -> list[Objective]:
    return _update(objs, oid, archived=True, archived_summary=summary)


def countdown_text(o: Objective, today_date: date) -> str | None:
    n = days_left(o, today_date)
    if n is None:
        return None
    if n == 0:
        return f"{o.name} · é hoje"
    if n < 0:
        return f"{o.name} · prova passou"
    return f"{o.name} · {n} dias"
