"""Deck-browser strip (design B): asset injection, server-side payload, live updates."""
from __future__ import annotations

import functools
import json
import time

from aqt import mw
from aqt.deckbrowser import DeckBrowser

from ebbin.ui import state
from ebbin.ui.stripdata import strip_payload

_ASSETS_JS = ("sketch.js", "sounds.js", "strip.js")


def _safe(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:  # never break Anki's deck browser
            print(f"[ebbin] {fn.__name__} failed: {e!r}")
    return wrapper


def _addon() -> str:
    return mw.addonManager.addonFromModule(__name__)


def _js(obj) -> str:
    """JSON safe to embed in an inline <script> (no raw '<' so '</script>' cannot appear)."""
    return json.dumps(obj, ensure_ascii=False).replace("<", "\\u003c")


@_safe
def inject(web_content, context) -> None:
    if not isinstance(context, DeckBrowser):
        return
    base = f"/_addons/{_addon()}/web"
    web_content.css.append(f"{base}/theme.css")
    web_content.js.extend(f"{base}/{name}" for name in _ASSETS_JS)


@_safe
def on_render(deck_browser, content) -> None:
    engine = state.get_engine()
    if engine is None:
        return
    payload = strip_payload(engine, int(time.time() * 1000))
    content.tree = (
        '<div id="ebbin-strip" class="ebbin"></div>'
        f"<script>window.ebbinStrip && ebbinStrip.init({_js(payload)});</script>"
        + content.tree)


def push_update(partial: dict) -> None:
    """Merge `partial` into the strip without re-rendering the deck list."""
    if mw.state != "deckBrowser":
        return
    mw.deckBrowser.web.eval(f"window.ebbinStrip && ebbinStrip.update({_js(partial)});")


@_safe
def refresh() -> None:
    """Full strip refresh (missions, XP, hints...) after events such as a finished pomodoro."""
    engine = state.get_engine()
    if engine is None or mw.state != "deckBrowser":
        return
    view = strip_payload(engine, int(time.time() * 1000), with_hints=False)["view"]
    view.pop("hints", None)  # the partial view has no hints; sending [] would erase the shown ones
    push_update(view)
