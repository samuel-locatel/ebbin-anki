"""Executa a importação de arquivos .txt via API de CSV do Anki."""
from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

from anki.import_export_pb2 import CsvMetadata
from anki.collection import ImportCsvRequest

from ebbin.core.importplan import PreviewRow


@dataclass
class ImportResult:
    name: str
    new: int = 0
    updated: int = 0
    duplicate: int = 0
    errors: list[str] = field(default_factory=list)


_ERROR_LABELS = (
    ("conflicting", "{n} notas em conflito"),
    ("missing_notetype", "{n} notas sem tipo de nota"),
    ("missing_deck", "{n} notas sem baralho"),
    ("empty_first_field", "{n} notas com primeiro campo vazio"),
)


def _import_one(col, row: PreviewRow, dupe: str) -> ImportResult:
    md = col.get_csv_metadata(str(row.path), None)
    md.dupe_resolution = CsvMetadata.PRESERVE if dupe == "preserve" else CsvMetadata.UPDATE
    md.match_scope = CsvMetadata.NOTETYPE
    out = col.import_csv(ImportCsvRequest(path=str(row.path), metadata=md))
    log = out.log
    errors = []
    for attr, tmpl in _ERROR_LABELS:
        n = len(getattr(log, attr))
        if n:
            errors.append(tmpl.format(n=n))
    # Anki 26.08 reports notes overwritten in UPDATE mode under `first_field_match`
    # (verified empirically; `updated` stays empty), so count those as updated.
    updated = len(log.updated) + (len(log.first_field_match) if dupe == "update" else 0)
    duplicate = len(log.duplicate) + (len(log.first_field_match) if dupe == "preserve" else 0)
    return ImportResult(row.name, new=len(log.new), updated=updated,
                        duplicate=duplicate, errors=errors)


def run_import(col, rows: list[PreviewRow], dupe: str) -> list[ImportResult]:
    results = []
    for row in rows:
        if row.problems or row.duplicate_of:
            continue
        try:
            results.append(_import_one(col, row, dupe))
        except Exception as exc:  # um arquivo ruim não derruba os outros
            results.append(ImportResult(row.name, errors=[str(exc)]))
    return results


def move_imported(paths: list[Path], dest: Path) -> None:
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    for p in paths:
        p = Path(p)
        target = dest / p.name
        n = 2
        while target.exists():
            target = dest / f"{p.stem} ({n}){p.suffix}"
            n += 1
        shutil.move(str(p), str(target))
