from pathlib import Path

from ebbin.core.importplan import build_preview
from ebbin.data.importer import move_imported, run_import

FIX = Path(__file__).parent.parent / "fixtures" / "import"


def _setup_notetypes(col):
    basic = col.models.by_name("Basic")
    basic["name"] = "Básico"
    col.models.update_dict(basic)
    ikkz = col.models.new("IKKZ__TF.PT_BR")
    for name in ("Frente", "Verso", "Extra"):
        col.models.add_field(ikkz, col.models.new_field(name))
    t = col.models.new_template("Cartão 1")
    t["qfmt"], t["afmt"] = "{{Frente}}", "{{FrontSide}}<hr>{{Verso}}"
    col.models.add_template(ikkz, t)
    col.models.add(ikkz)


def _rows(col, paths, imported=frozenset()):
    return build_preview(paths, {n.name for n in col.models.all_names_and_ids()}, set(imported))


def test_import_two_files_creates_decks(col):
    _setup_notetypes(col)
    rows = _rows(col, [FIX / "basico.txt", FIX / "ikkz.txt"])
    assert all(not r.problems for r in rows)
    res = run_import(col, rows, "preserve")
    assert [(r.name, r.new, r.errors) for r in res] == [("basico.txt", 3, []), ("ikkz.txt", 3, [])]
    names = {d.name for d in col.decks.all_names_and_ids()}
    for d in ("Teste::Geo::Europa", "Teste::Mat", "Teste::Prova::Um", "Teste::Prova::Dois"):
        assert d in names
    assert col.decks.id_for_name("Teste::Mat") is not None
    assert len(col.find_notes("")) == 6


def test_reimport_preserve_vs_update(col):
    _setup_notetypes(col)
    rows = _rows(col, [FIX / "basico.txt"])
    run_import(col, rows, "preserve")
    nid = col.find_notes('"Front:Qual a capital da França?"')[0]
    note = col.get_note(nid)
    note["Back"] = "EDITADO"
    col.update_note(note)

    res = run_import(col, rows, "preserve")
    assert res[0].new == 0 and res[0].updated == 0
    assert res[0].duplicate == 3  # 1 editada (first_field_match) + 2 idênticas (duplicate)
    assert col.get_note(nid)["Back"] == "EDITADO"

    res = run_import(col, rows, "update")
    assert res[0].new == 0 and res[0].updated == 1 and res[0].duplicate == 2
    assert col.get_note(nid)["Back"] == "Paris"


def test_skips_problem_rows_and_isolates_failures(col, tmp_path):
    _setup_notetypes(col)
    rows = _rows(col, [FIX / "basico.txt", FIX / "basico.txt"])
    assert len(run_import(col, rows, "preserve")) == 1  # duplicate_of skipped
    bad = _rows(col, [FIX / "ikkz.txt"])[0]
    bad.path = tmp_path / "sumiu.txt"
    good = _rows(col, [FIX / "ikkz.txt"])[0]
    res = run_import(col, [bad, good], "preserve")
    assert res[0].errors and res[0].new == 0
    assert res[1].new == 3


def test_move_imported_collision(tmp_path):
    dest = tmp_path / "feitos"
    a = tmp_path / "x.txt"
    a.write_text("1")
    move_imported([a], dest)
    b = tmp_path / "x.txt"
    b.write_text("2")
    move_imported([b], dest)
    assert (dest / "x.txt").read_text() == "1"
    assert (dest / "x (2).txt").read_text() == "2"
    assert not a.exists()
