from ebbin.data.bootstrap import initial_xp
from tests.conftest import seed_revlog


def _add(col):
    note = col.new_note(col.models.by_name("Basic"))
    note["Front"], note["Back"] = "a", "b"
    col.add_note(note, col.decks.id("Default"))
    return note.cards()[0].id


def test_initial_xp_sums_base_xp(col):
    cid = _add(col)
    seed_revlog(col, [
        {"id": 1000, "cid": cid, "ease": 1},
        {"id": 2000, "cid": cid, "ease": 3},
        {"id": 3000, "cid": cid, "ease": 4},
    ])
    assert initial_xp(col) == 22


def test_initial_xp_empty(col):
    assert initial_xp(col) == 0
