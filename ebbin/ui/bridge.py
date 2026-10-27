"""pycmd("ebbin:<cmd>:<arg>") dispatcher. No aqt imports, so it is testable without Qt.

<arg> is JSON when it parses, otherwise the raw string (e.g. `ebbin:open_window:metrics`)."""
from __future__ import annotations

import json
from typing import Any, Callable

from ebbin.data import queries as q
from ebbin.ui import state

PREFIX = "ebbin:"
_handlers: dict[str, Callable[[Any], Any]] = {}


def register(cmd: str, fn: Callable[[Any], Any]) -> None:
    _handlers[cmd] = fn


def parse(message: str) -> tuple[str, Any] | None:
    if not isinstance(message, str) or not message.startswith(PREFIX):
        return None
    cmd, _, raw = message[len(PREFIX):].partition(":")
    if not cmd:
        return None
    if raw == "":
        return cmd, None
    try:
        return cmd, json.loads(raw)
    except ValueError:
        return cmd, raw


def handle(handled: tuple[bool, Any], message: str, context: Any) -> tuple[bool, Any]:
    parsed = parse(message)
    if parsed is None:
        return handled
    cmd, arg = parsed
    fn = _handlers.get(cmd)
    if fn is None:
        print(f"[ebbin] unknown bridge command: {cmd}")
        return (True, None)
    try:
        return (True, fn(arg))
    except Exception as e:  # never break Anki's webview
        print(f"[ebbin] bridge command {cmd} failed: {e!r}")
        return (True, None)


def _engine_call(name: str) -> Callable[[Any], Any]:
    def run(_arg):
        eng = state.get_engine()
        return getattr(eng, name)() if eng else None
    return run


def _stub(name: str) -> Callable[[Any], Any]:
    def run(arg):
        print(f"[ebbin] bridge '{name}' not implemented yet: {arg!r}")
        return None
    return run


for _cmd in ("pomo_start", "pomo_pause", "pomo_resume", "pomo_stop"):
    register(_cmd, _engine_call(_cmd))
def _dismiss(arg):
    eng = state.get_engine()
    if eng is None or arg is None:
        return None
    today = q.today(eng.col)
    hidden = eng.state.dismissed_hints
    hidden[str(arg)] = today
    for k in [k for k, d in hidden.items() if d < today - 60]:  # forget old dismissals
        del hidden[k]
    eng.save()
    return None


register("dismiss", _dismiss)
for _cmd in ("open_window", "open_import"):
    register(_cmd, _stub(_cmd))
