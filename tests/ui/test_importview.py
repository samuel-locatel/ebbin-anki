from pathlib import Path

from ebbin.core.importplan import PreviewRow
from ebbin.data.importer import ImportResult
from ebbin.ui import importview as iv


def row(name, notes=3, problems=(), dup=None, nt="Básico", deck="D", sha=None):
    return PreviewRow(Path("/x") / name, name, nt, deck, notes, sha or name, list(problems), dup)


def test_situation():
    assert iv.situation(row("a.txt")) == "ok"
    assert iv.situation(row("a.txt", problems=["arquivo vazio"])) == "arquivo vazio"
    assert iv.situation(row("b.txt", dup="a.txt")) == "duplicado de a.txt"
    assert iv.situation(row("c.txt", problems=["x", "y"])) == "x; y"


def test_preview_view_totals_and_button():
    rows = [row("a.txt", 10), row("a (1).txt", 10, dup="a.txt"), row("c.txt", 5, problems=["arquivo vazio"]),
            row("d.txt", 4, nt=None, deck=None)]
    v = iv.preview_view(rows, 30.0, 20, [0] * 30)
    assert v["button"] == "Importar 2" and v["can_import"]
    assert v["total_text"] == "4 arquivos · 14 notas para importar"
    assert v["note"].startswith("Esses 14 novos somam ~")
    assert [r["ok"] for r in v["rows"]] == [True, False, False, True]
    assert v["rows"][3]["notetype"] == "—" and v["rows"][3]["deck"] == "—"


def test_preview_view_nothing_importable():
    v = iv.preview_view([row("a.txt", problems=["x"])], 30.0, 20, [])
    assert v["button"] == "Importar 0" and not v["can_import"] and v["note"] == ""


def test_results_view():
    res = [ImportResult("a.txt", new=5, updated=1, duplicate=2),
           ImportResult("b.txt", errors=["boom"])]
    v = iv.results_view(res, warning="w")
    assert v["rows"][0] == {"name": "a.txt", "new": 5, "existing": 3, "errors": "—", "failed": False}
    assert v["rows"][1]["errors"] == "boom" and v["rows"][1]["failed"]
    assert v["total_text"] == "5 novas · 3 já existiam" and v["warning"] == "w"


def test_succeeded_aligns_with_importable_rows():
    rows = [row("a.txt"), row("b.txt", dup="a.txt"), row("c.txt"), row("d.txt", problems=["x"])]
    res = [ImportResult("a.txt", new=1), ImportResult("c.txt", errors=["e"])]
    assert [r.name for r in iv.succeeded(rows, res)] == ["a.txt"]


def test_txt_files_non_recursive(tmp_path):
    (tmp_path / "b.txt").write_text("x")
    (tmp_path / "A.TXT").write_text("x")
    (tmp_path / "c.csv").write_text("x")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "d.txt").write_text("x")
    assert [p.name for p in iv.txt_files(tmp_path)] == ["A.TXT", "b.txt"]
