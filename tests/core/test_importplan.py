from pathlib import Path

from ebbin.core.importplan import budget_note, build_preview, parse_header

FIX = Path(__file__).parent.parent / "fixtures" / "import"
KNOWN = {"Básico", "IKKZ__TF.PT_BR"}


def test_parse_header_basico():
    h = parse_header((FIX / "basico.txt").read_text(encoding="utf-8"))
    assert (h.separator, h.html, h.notetype, h.tags_col, h.deck_col) == ("\t", False, "Básico", 3, 4)


def test_parse_header_ikkz_with_bom():
    h = parse_header("﻿" + (FIX / "ikkz.txt").read_text(encoding="utf-8"))
    assert (h.separator, h.html, h.notetype, h.tags_col, h.deck_col) == ("\t", True, "IKKZ__TF.PT_BR", 4, 5)


def test_parse_header_separators_and_garbage():
    assert parse_header("#separator:comma\n").separator == ","
    assert parse_header("#separator:semicolon\n").separator == ";"
    assert parse_header("#separator:|\n").separator == "|"
    h = parse_header("#lixo\n#html:talvez\n#deck column:abc\n")
    assert h == parse_header("")


def test_preview_ok_counts_and_deck():
    rows = build_preview([FIX / "basico.txt", FIX / "ikkz.txt"], KNOWN, set())
    b, i = rows
    assert b.problems == [] and b.notes == 3 and b.deck == "Teste::Geo::Europa"
    assert b.notetype == "Básico" and len(b.sha256) == 64
    assert i.problems == [] and i.notes == 3 and i.deck == "Teste::Prova::Um"


def test_preview_problems(tmp_path):
    unk = tmp_path / "a.txt"
    unk.write_text("#separator:tab\n#notetype:Nada\nx\ty\n", encoding="utf-8")
    empty = tmp_path / "b.txt"
    empty.write_bytes(b"")
    latin = tmp_path / "c.txt"
    latin.write_bytes("#separator:tab\n#notetype:Básico\nçã\tx\n".encode("latin-1"))
    nosep = tmp_path / "d.txt"
    nosep.write_text("#notetype:Básico\nx\ty\n", encoding="utf-8")
    rows = build_preview([unk, empty, latin, nosep], KNOWN, set())
    assert rows[0].problems == ["tipo de nota não existe: Nada"]
    assert rows[1].problems == ["arquivo vazio"]
    assert rows[2].problems == ["não é UTF-8"]
    assert rows[3].problems == ["cabeçalho #separator ausente"]


def test_preview_already_imported_and_duplicates(tmp_path):
    copy = tmp_path / "copia.txt"
    copy.write_bytes((FIX / "basico.txt").read_bytes())
    first = build_preview([FIX / "basico.txt"], KNOWN, set())[0]
    rows = build_preview([FIX / "basico.txt", copy], KNOWN, {first.sha256})
    assert "já importado antes" in rows[0].problems
    assert rows[0].duplicate_of is None
    assert rows[1].duplicate_of == "basico.txt"


def test_budget_note():
    s = budget_note(40, 32, 20, [30] * 7)
    # (30 + 160/7) * 32/60 = 28.2 -> 28
    assert s.startswith("Esses 40 novos somam ~28 min/dia de revisão na próxima semana")
    assert "passa do seu orçamento de 20 min" in s
    assert "passa" not in budget_note(1, 30, 60, [10] * 7)
