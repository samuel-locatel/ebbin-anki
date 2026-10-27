"""End-of-session pop-up (design A): frameless QDialog hosting an AnkiWebView."""
from __future__ import annotations

import functools
import json

from aqt import mw
from aqt.qt import QDialog, QKeySequence, QShortcut, Qt, QTimer, QVBoxLayout
from aqt.theme import theme_manager
from aqt.webview import AnkiWebView

from ebbin.ui import popupdata, state

_WIDTH, _HEIGHT = 560, 520  # initial size; popup.js then reports the content height
_MIN_HEIGHT = 320
_REVEAL_FALLBACK_MS = 800  # show anyway if the page never reports its height
_ASSETS_JS = ("sketch.js", "sounds.js", "popup.js")
_dialog: "PopupDialog | None" = None


def _safe(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:  # never break Anki
            print(f"[ebbin] {fn.__name__} failed: {e!r}")
    return wrapper


def _js(obj) -> str:
    """JSON safe to embed in inline script / eval (no raw '<')."""
    return json.dumps(obj, ensure_ascii=False).replace("<", "\\u003c")


def _addon() -> str:
    return mw.addonManager.addonFromModule(__name__)


class PopupDialog(QDialog):
    def __init__(self):
        super().__init__(mw)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setFixedSize(_WIDTH, _HEIGHT)
        self.setModal(False)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.web = AnkiWebView(parent=self, title="ebbin popup")
        self.web.set_bridge_command(self._on_bridge, self)
        layout.addWidget(self.web)
        QShortcut(QKeySequence("Esc"), self, activated=self.close)
        self._ready = False
        self._reveal_pending = False

    def _on_bridge(self, cmd: str) -> None:
        if cmd == "ebbinpopup:close":
            self.close()
        elif cmd.startswith("ebbinpopup:height:"):
            try:
                self._fit(int(cmd.rsplit(":", 1)[1]))
            except ValueError:
                pass

    def _fit(self, content_h: int) -> None:
        """Size the dialog to the page content (capped by the screen; the page scrolls beyond)."""
        screen = self.screen() or mw.screen()
        cap = screen.availableGeometry().height() - 40 if screen is not None else _HEIGHT
        height = max(_MIN_HEIGHT, min(content_h, cap))
        if height != self.height():
            self.setFixedSize(_WIDTH, height)
            self._center()
        self._reveal()

    def _center(self) -> None:
        g = mw.frameGeometry()
        self.move(g.center().x() - _WIDTH // 2, g.center().y() - self.height() // 2)

    @staticmethod
    def _call(view: dict, cfg: dict) -> str:
        sounds = {"sounds_enabled": cfg["sounds"]["enabled"], "volume": cfg["sounds"]["volume"],
                  "dark_theme": cfg["dark_theme"]}
        return f"ebbinPopup.setConfig({_js(sounds)});ebbinPopup.show({_js(view)});"

    def present(self, view: dict, cfg: dict) -> None:
        call = self._call(view, cfg)
        if self._ready:
            self.web.eval(call)
        else:
            base = f"/_addons/{_addon()}/web"
            theme = popupdata.theme_class(theme_manager.night_mode, cfg["dark_theme"])
            self.web.stdHtml(
                f'<div id="ebbin-popup" class="ebbin {theme}"></div>'
                f"<script>{call}</script>",
                css=[f"{base}/theme.css"],
                js=[f"{base}/{name}" for name in _ASSETS_JS],
                context=self)
            self._ready = True
        self._center()
        if self.isVisible():  # replacing an open popup's content
            self.raise_()
            if mw.state != "review":
                self.activateWindow()
            return
        # First show is transparent until the page reports its height (_fit): the webview is
        # laid out at its real width, but the user never sees the resize or a default
        # background. A timer reveals it anyway if no report arrives.
        self.setWindowOpacity(0.0)
        self._reveal_pending = True
        in_review = mw.state == "review"
        # mid-review: never take keyboard focus (Space/Enter belong to the card)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, in_review)
        self.show()
        self.raise_()
        if not in_review:
            self.activateWindow()
        QTimer.singleShot(_REVEAL_FALLBACK_MS, self._reveal)

    def _reveal(self) -> None:
        if self._reveal_pending:
            self._reveal_pending = False
            self.setWindowOpacity(1.0)

    def done(self, r) -> None:
        global _dialog
        if _dialog is self:
            _dialog = None
        self.web.cleanup()
        super().done(r)
        self.deleteLater()


@_safe
def _show() -> None:
    global _dialog
    payload = state.take_pending_popup()
    engine = state.get_engine()
    if payload is None or engine is None:
        return
    view = popupdata.build_view(payload, engine.cfg["budget_min"])
    if _dialog is None:
        _dialog = PopupDialog()
    _dialog.present(view, engine.cfg)


def close_if_open() -> None:
    if _dialog is not None:
        _dialog.close()


def show_later(payload: dict) -> None:
    """Store the payload and display it on the next event-loop turn (replaces an open popup)."""
    state.set_pending_popup(payload)
    QTimer.singleShot(0, _show)
