"""Batch .txt import dialog: AnkiWebView (theme.css) + native file pickers.

JS -> Python: pycmd("ebbinimp:<cmd>") with cmd in pick_files | pick_folder | import | close.
Import runs in `CollectionOp` (background thread, progress popup, UI refresh through
operation_did_execute). run_import returns results rather than OpChanges, so the op returns
an OpChanges flagged for everything an import touches and the results are collected in a
closure. Each file is its own backend import, hence one undo step per file (not a single step)."""
from __future__ import annotations

import functools
import json
from pathlib import Path

from anki.collection import OpChanges
from aqt import mw
from aqt.operations import CollectionOp
from aqt.qt import QDialog, QFileDialog, QTimer, QVBoxLayout
from aqt.webview import AnkiWebView

from ebbin.core.importplan import PreviewRow, build_preview
from ebbin.data import queries as q
from ebbin.data.importer import move_imported, run_import
from ebbin.ui import importview, state

_dialog: "ImportDialog | None" = None


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


def _all_changed() -> OpChanges:
    return OpChanges(card=True, note=True, deck=True, tag=True, browser_table=True,
                     browser_sidebar=True, note_text=True, study_queues=True)


class ImportDialog(QDialog):
    def __init__(self):
        super().__init__(mw)
        self.setWindowTitle("Ebbin · importar lotes")
        self.resize(900, 640)
        self.setModal(False)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.web = AnkiWebView(parent=self, title="ebbin import")
        self.web.set_bridge_command(self._on_bridge, self)
        layout.addWidget(self.web)
        self.rows: list[PreviewRow] = []
        self.busy = False

    def reject(self) -> None:  # Esc
        if not self.busy:
            super().reject()

    def closeEvent(self, event) -> None:  # window X / close_if_open
        if self.busy:
            event.ignore()
        else:
            super().closeEvent(event)

    # ---- page --------------------------------------------------------------------
    def load(self) -> None:
        eng = state.get_engine()
        base = f"/_addons/{_addon()}/web"
        cfg = {"dark_theme": eng.cfg["dark_theme"]} if eng else {}
        self.web.stdHtml(
            '<div id="ebbin-import" class="ebbin"></div>'
            f"<script>ebbinImport.setConfig({_js(cfg)});ebbinImport.show({_js({'stage': 'empty'})});</script>",
            css=[f"{base}/theme.css"],
            js=[f"{base}/sketch.js", f"{base}/import.js"],
            context=self)

    def _show(self, view: dict) -> None:
        self.web.eval(f"window.ebbinImport && ebbinImport.show({_js(view)});")

    def retheme(self) -> None:
        eng = state.get_engine()
        if eng is not None:
            self.web.eval("window.ebbinImport && ebbinImport.setTheme("
                          f"ebbinSketch.themeClass({_js(eng.cfg['dark_theme'])}));")

    # ---- bridge ------------------------------------------------------------------
    @_safe
    def _on_bridge(self, message: str) -> None:
        prefix = "ebbinimp:"
        if not message.startswith(prefix):
            return
        cmd = message[len(prefix):]
        if cmd == "close":
            if not self.busy:
                self.close()
        elif self.busy:
            return
        elif cmd == "pick_files":
            self.pick_files()
        elif cmd == "pick_folder":
            self.pick_folder()
        elif cmd == "import":
            self.start_import()

    # ---- picking -----------------------------------------------------------------
    def pick_files(self) -> None:
        names, _ = QFileDialog.getOpenFileNames(
            mw, "Importar lotes", str(Path.home() / "Downloads"), "Texto (*.txt)")
        if names:
            self.preview([Path(n) for n in names])

    def pick_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(mw, "Escolher pasta", str(Path.home() / "Downloads"))
        if folder:
            self.preview(importview.txt_files(Path(folder)))

    def preview(self, paths: list[Path]) -> None:
        eng = state.get_engine()
        if eng is None:
            return
        col = eng.col
        known = {m.name for m in col.models.all_names_and_ids()}
        self.rows = build_preview(paths, known, set(eng.state.imported_hashes))
        self._show(importview.preview_view(
            self.rows, q.avg_time_s(col), eng.cfg["budget_min"], q.scheduled_due_by_day(col)))

    # ---- import ------------------------------------------------------------------
    def start_import(self) -> None:
        eng = state.get_engine()
        rows = list(self.rows)
        if eng is None or not importview.importable(rows):
            return
        self.busy = True
        self._show({"stage": "importing"})
        dupe = eng.cfg["import"]["dupe"]
        results: list = []

        def op(col):
            results.extend(run_import(col, rows, dupe))
            return _all_changed()

        def done(_changes):
            self.busy = False
            self.rows = []
            warning = _after_import(eng, rows, results)
            if _dialog is self:
                self._show(importview.results_view(results, warning))

        def failed(exc):
            self.busy = False
            if _dialog is self:
                self._show({"stage": "results", "rows": [], "total_text": "", "warning": f"Falha na importação: {exc}"})

        CollectionOp(self, op).success(done).failure(failed).run_in_background()

    def done(self, r) -> None:
        global _dialog
        if _dialog is self:
            _dialog = None
        self.web.cleanup()
        super().done(r)
        self.deleteLater()


def _after_import(eng, rows: list[PreviewRow], results: list) -> str:
    """Record hashes and move files for the files imported without errors. Returns a warning."""
    ok = importview.succeeded(rows, results)
    if not ok:
        return ""
    seen = eng.state.imported_hashes
    for r in ok:
        if r.sha256 not in seen:
            seen.append(r.sha256)
    eng.save()
    imp = eng.cfg["import"]
    if not imp["move_after"]:
        return ""
    try:
        move_imported([r.path for r in ok], Path(imp["dest"]).expanduser())
    except Exception as e:
        print(f"[ebbin] move_imported failed: {e!r}")
        return f"Importado, mas não consegui mover os arquivos: {e}"
    return ""


@_safe
def open_import_dialog(_arg=None) -> None:
    global _dialog
    if state.get_engine() is None:
        return
    fresh = _dialog is None
    if fresh:
        _dialog = ImportDialog()
        _dialog.load()
    _dialog.show()
    _dialog.raise_()
    _dialog.activateWindow()
    if fresh:
        dlg = _dialog
        QTimer.singleShot(0, lambda: dlg.pick_files() if _dialog is dlg else None)


def close_if_open() -> None:
    if _dialog is not None:
        _dialog.close()


@_safe
def on_theme_change() -> None:
    if _dialog is not None:
        _dialog.retheme()
