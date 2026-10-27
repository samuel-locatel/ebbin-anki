from pathlib import Path

from aqt import gui_hooks, mw
from aqt.qt import QAction

from ebbin.data import store
from ebbin.ui import (
    bridge, deckbrowser, import_dialog, pomodoro_ui, popup, reviewer, schedtools, skin, state, window,
)
from ebbin.ui.engine import Engine
from ebbin.ui.settingsdata import sanitize_config


def _on_open() -> None:
    window.open_window("metrics")


def _addon() -> str:
    return mw.addonManager.addonFromModule(__name__)


def _on_profile_open() -> None:
    try:
        addon = _addon()
        defaults = mw.addonManager.addonConfigDefaults(addon) or {}
        cfg, bad = sanitize_config(mw.addonManager.getConfig(addon) or {}, defaults)
        if bad:
            print(f"[ebbin] configuração inválida, usando o padrão para: {', '.join(bad)}")
        addon_dir = Path(mw.addonManager.addonsFolder(addon))
        state.set_engine(Engine(mw.col, cfg, store.path_for(addon_dir, mw.pm.name)))
        schedtools.apply_easy_cap(mw.col, cfg)
        pomodoro_ui.start(state.get_engine())
        # Anki renders the deck browser before profile_did_open, when no engine
        # existed yet, so the first screen has no strip until redrawn.
        if mw.state == "deckBrowser":
            mw.deckBrowser.refresh()
    except Exception as e:
        print(f"[ebbin] profile_did_open failed: {e!r}")


def _step(name: str, fn) -> None:
    try:
        fn()
    except Exception as e:
        print(f"[ebbin] profile_will_close ({name}) failed: {e!r}")


def _save_session() -> None:
    engine = state.get_engine()
    if engine is not None:
        engine.end_session("left_reviewer")  # persists the in-progress session (no popup)
        engine.save()


def _on_profile_close() -> None:
    _step("pomodoro", pomodoro_ui.stop)
    _step("popup", popup.close_if_open)
    _step("window", window.close_if_open)
    _step("import", import_dialog.close_if_open)
    _step("save", _save_session)
    _step("state", lambda: state.set_engine(None))


def register() -> None:
    bridge.register("open_window", window.open_window)
    bridge.register("open_import", import_dialog.open_import_dialog)
    mw.addonManager.setWebExports(__name__.split(".")[0], r"web/.*")
    # Anki's own Config button opens Ebbin's validated Ajustes instead of the raw JSON editor.
    mw.addonManager.setConfigAction(__name__.split(".")[0], lambda: window.open_window("settings"))
    action = QAction("Ebbin", mw)
    action.triggered.connect(_on_open)
    mw.form.menuTools.addAction(action)
    import_action = QAction("Ebbin: importar lotes .txt", mw)
    import_action.triggered.connect(lambda: import_dialog.open_import_dialog())
    mw.form.menuTools.addAction(import_action)

    gui_hooks.profile_did_open.append(_on_profile_open)
    gui_hooks.profile_will_close.append(_on_profile_close)
    gui_hooks.webview_will_set_content.append(reviewer.inject)
    gui_hooks.webview_will_set_content.append(deckbrowser.inject)
    gui_hooks.webview_will_set_content.append(skin.inject)  # after the two above: skin.css last
    gui_hooks.deck_browser_will_render_content.append(deckbrowser.on_render)
    gui_hooks.reviewer_did_show_question.append(reviewer.on_show_question)
    gui_hooks.reviewer_did_answer_card.append(reviewer.on_answer)
    gui_hooks.reviewer_did_answer_card.append(pomodoro_ui.on_answer)  # after reviewer.on_answer
    gui_hooks.state_did_change.append(pomodoro_ui.on_state_change)
    gui_hooks.state_did_undo.append(reviewer.on_undo)
    gui_hooks.reviewer_will_end.append(reviewer.on_reviewer_end)
    gui_hooks.webview_did_receive_js_message.append(bridge.handle)
    gui_hooks.theme_did_change.append(reviewer.on_theme_change)
    gui_hooks.theme_did_change.append(skin.on_theme_change)
    gui_hooks.theme_did_change.append(window.on_theme_change)
    gui_hooks.theme_did_change.append(import_dialog.on_theme_change)
