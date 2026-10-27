"""Hand-drawn skin for Anki's own screens (reviewer, bottom bars, deck list, overview, top
toolbar): CSS/JS injected via webview_will_set_content. Never edits note types/templates."""
from __future__ import annotations

import functools
import json

from aqt import mw

from ebbin.ui import state
from ebbin.ui.skinmap import assets_for, context_name


def _safe(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:  # never break Anki's screens
            print(f"[ebbin] skin.{fn.__name__} failed: {e!r}")
    return wrapper


def _addon() -> str:
    return mw.addonManager.addonFromModule(__name__)


def _cfg() -> dict:
    """Live config; before profile_did_open (toolbar/deck list drawn first) read the add-on's."""
    engine = state.get_engine()
    if engine is not None:
        return engine.cfg
    return mw.addonManager.getConfig(_addon()) or {}


def _skin_on(cfg: dict) -> bool:
    return cfg.get("skin", True) is True


def _theme(cfg: dict) -> str:
    return cfg.get("dark_theme") if cfg.get("dark_theme") in ("night", "slate") else "night"


@_safe
def inject(web_content, context) -> None:
    """Registered after reviewer.inject/deckbrowser.inject, so skin.css lands after theme.css."""
    cfg = _cfg()
    assets = assets_for(context_name(context), _skin_on(cfg))
    if not assets["body_class"]:
        return
    base = f"/_addons/{_addon()}/web"
    for name in assets["css"]:
        if f"{base}/{name}" not in web_content.css:
            web_content.css.append(f"{base}/{name}")
    for name in assets["js"]:
        if f"{base}/{name}" not in web_content.js:
            web_content.js.append(f"{base}/{name}")
    init = json.dumps({"body_class": assets["body_class"], "dark_theme": _theme(cfg)})
    web_content.body += f"<script>window.ebbinSkin && ebbinSkin.init({init});</script>"


def _webviews() -> list:
    # mw.web hosts the reviewer, deck list and overview; mw.bottomWeb their bottom bars.
    return [w for w in (getattr(mw, "web", None), getattr(mw, "bottomWeb", None),
                        getattr(mw, "toolbarWeb", None)) if w is not None]


@_safe
def on_theme_change() -> None:
    """Night mode / dark theme changed: re-apply the theme class (skin.js also observes body)."""
    js = f"window.ebbinSkin && ebbinSkin.setTheme({json.dumps(_theme(_cfg()))});"
    for web in _webviews():
        web.eval(js)


@_safe
def redraw() -> None:
    """Re-render Anki's screens so the skin assets are added or dropped."""
    mw.toolbar.draw()
    if mw.state == "deckBrowser":
        mw.deckBrowser.refresh()
    elif mw.state == "overview":
        mw.overview.refresh()
    elif mw.state == "review":
        mw.reviewer.show()  # re-inits the reviewer web + bottom bar on the current card


@_safe
def on_config_saved(old: dict, new: dict) -> None:
    if old.get("skin") != new.get("skin"):
        redraw()
    elif old.get("dark_theme") != new.get("dark_theme"):
        on_theme_change()
