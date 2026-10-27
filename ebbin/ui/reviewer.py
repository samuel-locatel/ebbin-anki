"""Reviewer integration: asset injection and answer/undo/end hooks wired to the Engine."""
from __future__ import annotations

import functools
import json

import aqt.reviewer
from aqt import mw

from ebbin.ui import huddata, pomo_flow, popup, state

_ASSETS_JS = ("sketch.js", "sounds.js", "reviewer.js")


def _addon() -> str:
    return mw.addonManager.addonFromModule(__name__)


def _safe(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:  # never break Anki's review flow
            print(f"[ebbin] {fn.__name__} failed: {e!r}")
    return wrapper


def config_js(cfg: dict) -> str:
    payload = {
        "sounds_enabled": cfg["sounds"]["enabled"],
        "volume": cfg["sounds"]["volume"],
        "dark_theme": cfg["dark_theme"],
    }
    return f"window.ebbin && ebbin.setConfig({json.dumps(payload)});"


def pomo_view(engine) -> dict:
    """Pomodoro state plus the total length of the current phase (for the progress ring)."""
    p = engine.pomo
    phase = p.paused_from if p.phase == "paused" else p.phase
    pcfg = engine.cfg["pomodoro"]
    total = {"focus": pcfg["focus"], "short": pcfg["short"], "long": pcfg["long"]}.get(phase, 0) * 60
    return {"phase": p.phase, "remaining_s": p.remaining_s, "cycle": p.cycle,
            "total_s": total, "paused_from": p.paused_from}


def build_view(engine) -> dict:
    """today_view plus the fields the reviewer bar needs (combo, pomodoro total, HUD progress)."""
    view = engine.today_view()
    view["combo"] = engine.state.combo.count
    view["pomodoro"] = pomo_view(engine)
    view["hud"] = huddata.hud_view(view)
    return view


@_safe
def inject(web_content, context) -> None:
    if not isinstance(context, aqt.reviewer.Reviewer):
        return
    engine = state.get_engine()
    base = f"/_addons/{_addon()}/web"
    web_content.css.append(f"{base}/theme.css")
    web_content.js.extend(f"{base}/{name}" for name in _ASSETS_JS)
    if engine is not None:
        web_content.body += f"<script>{config_js(engine.cfg)}</script>"


@_safe
def on_show_question(card) -> None:
    engine = state.get_engine()
    if engine is None:
        return
    engine.before_show(card.id)
    mw.reviewer.web.eval(f"window.ebbin && ebbin.update({json.dumps(build_view(engine))});")


@_safe
def on_answer(reviewer, card, ease) -> None:
    engine = state.get_engine()
    if engine is None:
        return
    evt = engine.on_answer(card.id, ease)
    reviewer.web.eval(
        f"window.ebbin && ebbin.onAnswer({json.dumps(evt.to_dict())}, "
        f"{json.dumps(build_view(engine))});")


@_safe
def on_undo(changes) -> None:
    engine = state.get_engine()
    if engine is not None:
        engine.on_undo()


@_safe
def on_reviewer_end() -> None:
    engine = state.get_engine()
    if engine is None:
        return
    payload = engine.end_session(pomo_flow.deferral.on_reviewer_end())
    if payload is not None:
        popup.show_later(payload)


@_safe
def on_theme_change() -> None:
    engine = state.get_engine()
    if engine is None or mw.state != "review" or mw.reviewer is None:
        return
    js = ("window.ebbin && ebbin.setTheme(ebbinSketch.themeClass("
          f"{json.dumps(engine.cfg['dark_theme'])}));")
    mw.reviewer.web.eval(js)
