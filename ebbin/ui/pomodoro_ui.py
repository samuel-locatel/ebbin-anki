"""Pomodoro driver: a 1 s QTimer feeding Engine.pomo_tick and forwarding its events."""
from __future__ import annotations

import json
import time

from aqt import mw
from aqt.qt import QTimer

from ebbin.ui import deckbrowser, pomo_flow, popup, reviewer


class PomodoroDriver:
    def __init__(self, engine):
        self.engine = engine
        self._last_answer = time.time()
        pomo_flow.deferral.clear()
        pomo_flow.auto_resume.clear()
        self._clock = pomo_flow.TickClock(time.monotonic())
        self.timer = QTimer(mw)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.tick)

    def start(self) -> None:
        self.timer.start()

    def stop(self) -> None:
        self.timer.stop()
        self.timer.deleteLater()
        pomo_flow.deferral.clear()
        pomo_flow.auto_resume.clear()

    # ---- helpers -------------------------------------------------------------------

    def _idle_s(self) -> int:
        """Seconds since the last answer, only while reviewing (never on the deck screen)."""
        if mw.state != "review":
            return 0
        return max(0, int(time.time() - self._last_answer))

    def _web(self):
        if mw.state == "review" and mw.reviewer is not None:
            return mw.reviewer.web
        return mw.web

    def _play(self, keys: list[str]) -> None:
        sounds = self.engine.cfg["sounds"]
        if not keys or not sounds["enabled"]:
            return
        self._web().eval(
            f"window.ebbinPlaySeq && ebbinPlaySeq({keys!r}, {float(sounds['volume'])});")

    def _push_pomo(self) -> None:
        pomo = reviewer.pomo_view(self.engine)
        if mw.state == "review" and mw.reviewer is not None:
            mw.reviewer.web.eval(f"window.ebbin && ebbin.updatePomo({json.dumps(pomo)});")
        else:
            deckbrowser.push_update({"pomodoro": pomo})

    def _end_session(self, reason: str = "pomodoro") -> None:
        payload = self.engine.end_session(reason)
        if payload is not None:
            popup.show_later(payload)

    # ---- hooks ---------------------------------------------------------------------

    def tick(self) -> None:
        try:
            dt = self._clock.delta(time.monotonic())
            events = self.engine.pomo_tick(dt, self._idle_s())
            pomo_flow.auto_resume.on_events(events)
            pomo_flow.auto_resume.sync(self.engine.pomo.phase)
            if events:
                self._on_events(events)
            if self.engine.pomo.phase != "idle" or events:
                self._push_pomo()
        except Exception as e:  # keep the timer alive
            print(f"[ebbin] pomodoro tick failed: {e!r}")

    def _on_events(self, events: list[str]) -> None:
        keys = []
        if "focus_done" in events:
            keys.append("pomo")
        keys += ["good" for e in events if e.startswith("mission:")]
        if "level" in events:
            keys.append("level")
        self._play(keys)
        if "focus_done" in events:
            try:
                pomo_flow.deferral.on_focus_done(mw.state == "review", self._end_session)
            except Exception as e:
                print(f"[ebbin] pomodoro end_session failed: {e!r}")
        deckbrowser.refresh()

    def on_answer(self, reviewer_, card, ease) -> None:
        self._last_answer = time.time()
        try:
            pomo_flow.deferral.on_answer(self._end_session)
        except Exception as e:
            print(f"[ebbin] pomodoro end_session failed: {e!r}")
        try:
            if pomo_flow.auto_resume.on_answer(self.engine.pomo.phase, self.engine.pomo_resume):
                self._push_pomo()
        except Exception as e:
            print(f"[ebbin] pomodoro auto-resume failed: {e!r}")

    def on_state_change(self, new_state, old_state) -> None:
        if new_state != "review":
            pomo_flow.deferral.clear()  # reviewer_will_end already closed the session
            return
        self._last_answer = time.time()
        if self.engine.cfg["pomodoro"]["autostart"] and self.engine.pomo.phase == "idle":
            self.engine.pomo_start()
            self._push_pomo()


_driver: PomodoroDriver | None = None


def start(engine) -> None:
    global _driver
    stop()
    _driver = PomodoroDriver(engine)
    _driver.start()


def stop() -> None:
    global _driver
    if _driver is not None:
        _driver.stop()
        _driver = None


def on_answer(reviewer_, card, ease) -> None:
    if _driver is not None:
        _driver.on_answer(reviewer_, card, ease)


def on_state_change(new_state, old_state) -> None:
    if _driver is not None:
        try:
            _driver.on_state_change(new_state, old_state)
        except Exception as e:
            print(f"[ebbin] pomodoro state change failed: {e!r}")
