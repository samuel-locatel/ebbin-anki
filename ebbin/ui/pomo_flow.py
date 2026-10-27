"""Deferral of the pomodoro-end session close until the current answer (no aqt imports)."""
from __future__ import annotations

from typing import Callable


class EndDeferral:
    def __init__(self):
        self.pending = False

    def on_focus_done(self, in_review: bool, end: Callable[[str], None]) -> None:
        if in_review:
            self.pending = True  # wait for the current answer
        else:
            end("pomodoro")

    def on_answer(self, end: Callable[[str], None]) -> None:
        if self.pending:
            self.pending = False
            end("pomodoro")

    def on_reviewer_end(self) -> str:
        """Reason for closing the session when the reviewer is left."""
        reason = "pomodoro" if self.pending else "left_reviewer"
        self.pending = False
        return reason

    def clear(self) -> None:
        self.pending = False


class AutoResume:
    """Resume a pomodoro that was paused by inactivity (never one the user paused) on the next answer."""

    def __init__(self):
        self.auto_paused = False

    def on_events(self, events: list[str]) -> None:
        if "auto_paused" in events:
            self.auto_paused = True

    def sync(self, phase: str) -> None:
        """Any phase other than paused means the auto pause is over (user resumed/stopped)."""
        if phase != "paused":
            self.auto_paused = False

    def on_answer(self, phase: str, resume: Callable[[], None]) -> bool:
        """Call `resume` and return True when this answer should end an automatic pause."""
        should = self.auto_paused and phase == "paused"
        self.auto_paused = False
        if should:
            resume()
        return should

    def clear(self) -> None:
        self.auto_paused = False


class TickClock:
    """Whole seconds elapsed between ticks from a monotonic clock, carrying the remainder."""

    def __init__(self, now: float):
        self._last = now
        self._acc = 0.0

    def delta(self, now: float) -> int:
        self._acc += max(0.0, now - self._last)
        self._last = now
        secs = int(self._acc)
        self._acc -= secs
        return secs


deferral = EndDeferral()
auto_resume = AutoResume()
