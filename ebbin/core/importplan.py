"""Planejamento da importação em lote de arquivos .txt (sem anki/aqt)."""
from __future__ import annotations

import hashlib
import statistics
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

_SEPARATORS = {"tab": "\t", "comma": ",", "semicolon": ";", "space": " ", "pipe": "|", "colon": ":"}


@dataclass
class FileHeader:
    separator: str | None = None
    html: bool | None = None
    notetype: str | None = None
    tags_col: int | None = None
    deck_col: int | None = None


@dataclass
class PreviewRow:
    path: Path
    name: str
    notetype: str | None
    deck: str | None
    notes: int
    sha256: str
    problems: list[str] = field(default_factory=list)
    duplicate_of: str | None = None


def _int(value: str) -> int | None:
    try:
        n = int(value.strip())
    except ValueError:
        return None
    return n if n > 0 else None


def parse_header(text: str) -> FileHeader:
    """Lê as linhas `#chave:valor` do início; linhas desconhecidas são ignoradas."""
    header = FileHeader()
    for line in text.lstrip("﻿").splitlines():
        if not line.startswith("#"):
            break
        key, sep, value = line[1:].partition(":")
        if not sep:
            continue
        key = key.strip().lower()
        value = value.rstrip("\r\n")
        if key == "separator":
            v = value.strip()
            header.separator = _SEPARATORS.get(v.lower(), value if value else None)
        elif key == "html":
            if value.strip().lower() in ("true", "false"):
                header.html = value.strip().lower() == "true"
        elif key == "notetype":
            header.notetype = value.strip() or None
        elif key == "tags column":
            header.tags_col = _int(value)
        elif key == "deck column":
            header.deck_col = _int(value)
    return header


def _preview_one(path: Path, known_notetypes: set[str], already_imported: set[str]) -> PreviewRow:
    raw = path.read_bytes()
    row = PreviewRow(path=path, name=path.name, notetype=None, deck=None, notes=0,
                     sha256=hashlib.sha256(raw).hexdigest())
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        row.problems.append("não é UTF-8")
        return row
    if not text.strip():
        row.problems.append("arquivo vazio")
        return row
    header = parse_header(text)
    row.notetype = header.notetype
    data = [ln for ln in text.splitlines() if ln.strip() and not ln.startswith("#")]
    row.notes = len(data)
    if header.separator is None:
        row.problems.append("cabeçalho #separator ausente")
    if header.notetype is not None and header.notetype not in known_notetypes:
        row.problems.append(f"tipo de nota não existe: {header.notetype}")
    if header.deck_col is not None and header.separator is not None:
        decks = []
        for ln in data:
            cols = ln.split(header.separator)
            if len(cols) >= header.deck_col and cols[header.deck_col - 1].strip():
                decks.append(cols[header.deck_col - 1].strip())
        if decks:
            row.deck = Counter(decks).most_common(1)[0][0]
    if row.sha256 in already_imported:
        row.problems.append("já importado antes")
    return row


def build_preview(paths: list[Path], known_notetypes: set[str], already_imported: set[str]) -> list[PreviewRow]:
    rows: list[PreviewRow] = []
    first_by_hash: dict[str, str] = {}
    for p in paths:
        row = _preview_one(Path(p), known_notetypes, already_imported)
        if row.sha256 in first_by_hash:
            row.duplicate_of = first_by_hash[row.sha256]
        else:
            first_by_hash[row.sha256] = row.name
        rows.append(row)
    return rows


def budget_note(new_notes: int, avg_s: float, budget_min: int, projected_daily_reviews: list[int]) -> str:
    """Estimativa de carga extra: x = round((média(projeção[:7]) + extra) * avg_s / 60) min/dia.

    `extra` = revisões diárias médias adicionadas pelos novos cards na próxima semana,
    aproximado por `new_notes * 4 / 7` (cada card novo gera ~4 revisões na primeira
    semana, mesmo modelo da Tarefa 11 com offsets 1, 3, 8, 20 sem o dia 20).
    """
    week = projected_daily_reviews[:7]
    base = statistics.mean(week) if week else 0
    extra = new_notes * 4 / 7
    x = round((base + extra) * avg_s / 60)
    text = f"Esses {new_notes} novos somam ~{x} min/dia de revisão na próxima semana"
    if x > budget_min:
        text += f" · passa do seu orçamento de {budget_min} min"
    return text
