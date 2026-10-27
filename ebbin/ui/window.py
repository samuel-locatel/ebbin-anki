"""Ebbin window (Métricas / Objetivos / Ajustes): non-modal QDialog hosting an AnkiWebView.

JS talks to Python with pycmd("ebbinwin:<cmd>:<json>") where json = {"id": n, "arg": ...};
the reply is pushed back with ebbinWin.receive(id, ok, json)."""
from __future__ import annotations

import functools
import json
from datetime import date, datetime
from pathlib import Path

import aqt
from aqt import mw
from aqt.qt import QDialog, QFileDialog, QVBoxLayout
from aqt.theme import theme_manager
from aqt.webview import AnkiWebView

from ebbin.data import queries as q
from ebbin.ui import pomodoro_ui, popup, reviewer, schedtools, settingsdata, skin, state
from ebbin.ui import windowdata as wd
from ebbin.ui.engine import Engine

TABS = ("metrics", "objectives", "settings")
_ASSETS_JS = ("sketch.js", "sounds.js", "charts.js", "window.js")
_dialog: "WindowDialog | None" = None


def _safe(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:  # never break Anki
            print(f"[ebbin] {fn.__name__} failed: {e!r}")
    return wrapper


def _js(obj) -> str:
    return json.dumps(obj, ensure_ascii=False).replace("<", "\\u003c")


def _addon() -> str:
    return mw.addonManager.addonFromModule(__name__)


def _today_date(col) -> date:
    return datetime.fromtimestamp(q.day_start_ms(col) / 1000).date()


def _refresh_strip() -> None:
    if mw.state == "deckBrowser":
        mw.deckBrowser.refresh()


def _push_config(cfg: dict) -> None:
    """Sound/theme config to every webview that cached it (13b reads config once)."""
    if mw.state == "review" and mw.reviewer is not None:
        mw.reviewer.web.eval(reviewer.config_js(cfg))
    if _dialog is not None:
        _dialog.web.eval(f"window.ebbinWin && ebbinWin.setConfig({_js(settingsdata.webview_config(cfg))});")
    _refresh_strip()


# ---- commands (arg already decoded) ---------------------------------------------------

def _engine() -> Engine:
    eng = state.get_engine()
    if eng is None:
        raise RuntimeError("Ebbin ainda não carregou o perfil")
    return eng


def _cmd_init(_arg):
    eng = _engine()
    return {"cfg": eng.cfg, "web": settingsdata.webview_config(eng.cfg)}


def _cmd_metrics(arg):
    eng = _engine()
    scope = "active" if arg.get("scope") == "active" else "all"
    period = arg.get("period") if arg.get("period") in ("30d", "12w", "all") else "30d"
    return wd.metrics_payload(eng.col, eng.state, eng.cfg, scope, period, _today_date(eng.col))


def _cmd_objectives(_arg):
    eng = _engine()
    return wd.objectives_payload(eng.col, eng.state, _today_date(eng.col), eng.cfg["mastered_days"])


def _objectives_after_change():
    eng = _engine()
    eng.save()
    _refresh_strip()
    return _cmd_objectives(None)


def _cmd_obj_save(arg):
    wd.objective_upsert(_engine().state, arg)
    return _objectives_after_change()


def _cmd_obj_activate(arg):
    wd.objective_activate(_engine().state, str(arg))
    return _objectives_after_change()


def _cmd_obj_archive(arg):
    eng = _engine()
    summary = wd.objective_archive(eng.col, eng.state, str(arg), _today_date(eng.col), eng.cfg["mastered_days"])
    return {"summary": summary, "payload": _objectives_after_change()}


def _cmd_obj_delete(arg):
    wd.objective_delete(_engine().state, str(arg))
    return _objectives_after_change()


def _cmd_settings_save(arg):
    eng = _engine()
    cfg = settingsdata.validate_config(arg, eng.cfg)  # ValueError -> shown inline
    mw.addonManager.writeConfig(_addon(), cfg)
    old, eng.cfg = eng.cfg, cfg
    schedtools.apply_easy_cap(mw.col, cfg)
    _push_config(cfg)
    skin.on_config_saved(old, cfg)
    return {"cfg": cfg}


def _cmd_browse(arg):
    aqt.dialogs.open("Browser", mw, search=(f"cid:{int(arg)}",))
    return None


def _cmd_export(_arg):
    eng = _engine()
    eng.save()
    path, _ = QFileDialog.getSaveFileName(
        _dialog or mw, "Exportar dados do Ebbin", str(Path.home() / "ebbin-dados.json"), "JSON (*.json)")
    if not path:
        return {"saved": False}
    Path(path).write_text(settingsdata.export_json(eng.path), encoding="utf-8")
    return {"saved": True}


def _cmd_reset(_arg):
    eng = _engine()
    path, cfg = eng.path, eng.cfg
    pomodoro_ui.stop()
    popup.close_if_open()
    if path.exists():
        path.unlink()
    state.set_engine(Engine(mw.col, cfg, path))  # recreates + bootstraps XP
    pomodoro_ui.start(state.get_engine())
    _refresh_strip()
    return {"reset": True}


_COMMANDS = {
    "init": _cmd_init, "metrics": _cmd_metrics, "objectives": _cmd_objectives,
    "obj_save": _cmd_obj_save, "obj_activate": _cmd_obj_activate, "obj_archive": _cmd_obj_archive,
    "obj_delete": _cmd_obj_delete, "settings_save": _cmd_settings_save, "browse": _cmd_browse,
    "export": _cmd_export, "reset": _cmd_reset,
}


def run_command(cmd: str, arg):
    """Returns (ok, result). Expected user errors (ValueError/KeyError) become messages."""
    fn = _COMMANDS.get(cmd)
    if fn is None:
        return False, "comando desconhecido"
    try:
        return True, fn(arg)
    except ValueError as e:
        return False, str(e)
    except KeyError:
        return False, "item não encontrado"
    except Exception as e:
        print(f"[ebbin] window command {cmd} failed: {e!r}")
        return False, "erro inesperado"


class WindowDialog(QDialog):
    def __init__(self):
        super().__init__(mw)
        self.setWindowTitle("Ebbin")
        self.resize(980, 720)
        self.setModal(False)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.web = AnkiWebView(parent=self, title="ebbin window")
        self.web.set_bridge_command(self._on_bridge, self)
        layout.addWidget(self.web)

    def _on_bridge(self, message: str) -> None:
        prefix = "ebbinwin:"
        if not message.startswith(prefix):
            return
        cmd, _, raw = message[len(prefix):].partition(":")
        try:
            body = json.loads(raw) if raw else {}
            call_id, arg = body["id"], body.get("arg")
        except (ValueError, KeyError, TypeError):
            return
        ok, result = run_command(cmd, arg)
        self.web.eval(f"window.ebbinWin && ebbinWin.receive({_js(call_id)}, {_js(ok)}, {_js(result)});")

    def load(self, tab: str) -> None:
        base = f"/_addons/{_addon()}/web"
        self.web.stdHtml(
            '<div id="ebbin-win" class="ebbin"></div>'
            f"<script>ebbinWin.init({_js({'tab': tab})});</script>",
            css=[f"{base}/theme.css"],
            js=[f"{base}/{name}" for name in _ASSETS_JS],
            context=self)

    def retheme(self) -> None:
        eng = state.get_engine()
        if eng is not None:
            self.web.eval(f"window.ebbinWin && ebbinWin.setTheme(ebbinSketch.themeClass({_js(eng.cfg['dark_theme'])}));")

    def done(self, r) -> None:
        global _dialog
        if _dialog is self:
            _dialog = None
        self.web.cleanup()
        super().done(r)
        self.deleteLater()


@_safe
def open_window(tab) -> None:
    global _dialog
    tab = tab if tab in TABS else "metrics"
    if state.get_engine() is None:
        return
    if _dialog is None:
        _dialog = WindowDialog()
        _dialog.load(tab)
    else:
        _dialog.web.eval(f"window.ebbinWin && ebbinWin.select({_js(tab)});")
    _dialog.show()
    _dialog.raise_()
    _dialog.activateWindow()


def close_if_open() -> None:
    if _dialog is not None:
        _dialog.close()


@_safe
def on_theme_change() -> None:
    if _dialog is not None:
        _dialog.retheme()
