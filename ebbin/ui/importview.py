"""View-model da janela de importação em lote (sem aqt): linhas da prévia, totais e resultados."""
from __future__ import annotations

from pathlib import Path

from ebbin.core.importplan import PreviewRow, budget_note
from ebbin.core.metrics import project_load


def txt_files(folder: Path) -> list[Path]:
    """Os `*.txt` diretamente na pasta (sem recursão), em ordem alfabética."""
    return sorted((p for p in Path(folder).iterdir() if p.is_file() and p.suffix.lower() == ".txt"),
                  key=lambda p: p.name.lower())


def is_importable(row: PreviewRow) -> bool:
    return not row.problems and row.duplicate_of is None


def importable(rows: list[PreviewRow]) -> list[PreviewRow]:
    return [r for r in rows if is_importable(r)]


def situation(row: PreviewRow) -> str:
    parts = list(row.problems)
    if row.duplicate_of:
        parts.append(f"duplicado de {row.duplicate_of}")
    return "; ".join(parts) if parts else "ok"


def preview_view(rows: list[PreviewRow], avg_s: float, budget_min: int, scheduled: list[int]) -> dict:
    ok_rows = importable(rows)
    new_total = sum(r.notes for r in ok_rows)
    n = len(ok_rows)
    view_rows = [{"name": r.name, "notetype": r.notetype or "—", "deck": r.deck or "—",
                  "notes": r.notes, "status": situation(r), "ok": is_importable(r)} for r in rows]
    note = budget_note(new_total, avg_s, budget_min, project_load(scheduled, 0)) if n else ""
    return {
        "stage": "preview",
        "rows": view_rows,
        "total_text": f"{len(rows)} arquivos · {new_total} notas para importar",
        "note": note,
        "button": f"Importar {n}",
        "can_import": n > 0,
    }


def results_view(results, warning: str = "") -> dict:
    rows = []
    for r in results:
        rows.append({"name": r.name, "new": r.new, "existing": r.updated + r.duplicate,
                     "errors": "; ".join(r.errors) if r.errors else "—", "failed": bool(r.errors)})
    new = sum(r["new"] for r in rows)
    existing = sum(r["existing"] for r in rows)
    return {
        "stage": "results",
        "rows": rows,
        "total_text": f"{new} novas · {existing} já existiam",
        "warning": warning,
    }


def succeeded(rows: list[PreviewRow], results) -> list[PreviewRow]:
    """Linhas importadas sem erro. `results` segue a ordem das linhas importáveis (run_import)."""
    return [row for row, res in zip(importable(rows), results) if not res.errors]
