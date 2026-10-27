"""Study sessions, diminishing returns, badges and records (pure)."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace

GAP_MS = 300_000


@dataclass(frozen=True)
class SessionRecord:
    start_ms: int
    end_ms: int
    answers: int
    correct: int
    xp: int
    avg_s: float
    rescued: int
    mastered: int
    max_combo: int
    pomodoro: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "SessionRecord":
        return cls(**d)


class SessionTracker:
    def __init__(self) -> None:
        self._cur: SessionRecord | None = None
        self._total_ms = 0

    @property
    def current(self) -> SessionRecord | None:
        return self._cur

    def on_answer(self, at_ms: int, ease: int, xp: int, time_ms: int,
                  rescued: bool, mastered: bool, combo: int) -> SessionRecord | None:
        closed = None
        if self._cur is not None and at_ms - self._cur.end_ms > GAP_MS:
            closed = self.close(at_ms)
        c = self._cur
        if c is None:
            c = SessionRecord(at_ms, at_ms, 0, 0, 0, 0.0, 0, 0, 0, False)
            self._total_ms = 0
        self._total_ms += time_ms
        n = c.answers + 1
        self._cur = replace(
            c, end_ms=at_ms, answers=n, correct=c.correct + (1 if ease > 1 else 0),
            xp=c.xp + xp, avg_s=self._total_ms / 1000 / n,
            rescued=c.rescued + (1 if rescued else 0),
            mastered=c.mastered + (1 if mastered else 0),
            max_combo=max(c.max_combo, combo))
        return closed

    def close(self, at_ms: int) -> SessionRecord | None:
        c, self._cur, self._total_ms = self._cur, None, 0
        return c

    def mark_pomodoro(self) -> None:
        if self._cur is not None:
            self._cur = replace(self._cur, pomodoro=True)


def should_popup(rec: SessionRecord, reason: str) -> bool:
    return True if reason == "pomodoro" else rec.answers >= 10


def is_diminished(main_done: bool, pomodoro_done_today: bool,
                  review_seconds_today: int, budget_min: int) -> bool:
    return main_done and (pomodoro_done_today or review_seconds_today > budget_min * 60)


def _acc(rec: SessionRecord) -> float:
    return rec.correct / rec.answers if rec.answers else 0.0


def badge_for(rec: SessionRecord, median14: float | None, capacity: int) -> str | None:
    if rec.answers < 10:
        return None
    if _acc(rec) >= 0.90:
        return "Preciso"
    if median14 and rec.avg_s <= 0.8 * median14:
        return "Relâmpago"
    if rec.rescued >= 10:
        return "Resgatador"
    if rec.answers >= capacity:
        return "Persistente"
    return None


@dataclass(frozen=True)
class Records:
    most_cards_pomodoro: int = 0
    best_week_accuracy: dict = field(default_factory=dict)
    max_combo: int = 0

    def to_dict(self) -> dict:
        return {"most_cards_pomodoro": self.most_cards_pomodoro,
                "best_week_accuracy": dict(self.best_week_accuracy),
                "max_combo": self.max_combo}

    @classmethod
    def from_dict(cls, d: dict) -> "Records":
        return cls(int(d.get("most_cards_pomodoro", 0)),
                   dict(d.get("best_week_accuracy", {})),
                   int(d.get("max_combo", 0)))


def update_records(r: Records, rec: SessionRecord, iso_week: str) -> tuple[Records, list[str]]:
    events: list[str] = []
    mcp, week, mc = r.most_cards_pomodoro, dict(r.best_week_accuracy), r.max_combo
    if rec.pomodoro and rec.answers > mcp:
        if mcp > 0:
            events.append("Mais cards num pomodoro")
        mcp = rec.answers
    if rec.answers >= 20:
        acc = _acc(rec)
        prev = week.get(iso_week)
        if prev is None or acc > prev:
            if prev is not None:
                events.append("Melhor acerto da semana")
            week[iso_week] = acc
    if rec.max_combo > mc:
        if mc > 0:
            events.append("Maior combo")
        mc = rec.max_combo
    return Records(mcp, week, mc), events
