from datetime import datetime

from ebbin.data import queries as q
from tests.conftest import seed_revlog

DAY = 86_400_000


def _add(col, front="a", back="b", model="Basic"):
    note = col.new_note(col.models.by_name(model))
    note["Front"], note["Back"] = front, back
    col.add_note(note, col.decks.id("Default"))
    return note.cards()[0].id


def test_review_before_rollover_counts_previous_day(col):
    col.set_config("rollover", 4)
    cutoff_ms = col.sched.day_cutoff * 1000
    t = col.sched.today
    assert q.day_start_ms(col) == cutoff_ms - DAY
    assert q.today(col) == t
    assert q.day_of_ms(col, cutoff_ms - 1) == t
    assert q.day_of_ms(col, cutoff_ms - DAY) == t
    assert q.day_of_ms(col, cutoff_ms - DAY - 1) == t - 1
    assert q.day_of_ms(col, cutoff_ms) == t + 1
    two_am = int(datetime.now().replace(hour=2, minute=0, second=0, microsecond=0).timestamp() * 1000)
    expected = t if two_am >= q.day_start_ms(col) else t - 1
    assert q.day_of_ms(col, two_am) == expected


def test_avg_time_defaults_to_30_on_empty(col):
    assert q.avg_time_s(col) == 30.0
    assert q.median_time_s(col) is None


def test_avg_time_last_14_days_only(col):
    cid = _add(col)
    now = q.day_start_ms(col) + 1000
    seed_revlog(col, [
        {"id": now, "cid": cid, "ease": 3, "time": 10000},
        {"id": now + 1, "cid": cid, "ease": 3, "time": 20000},
        {"id": now - 20 * DAY, "cid": cid, "ease": 3, "time": 90000},
    ])
    assert q.avg_time_s(col) == 15.0
    assert q.median_time_s(col) == 15.0


def test_n_items_counts_tf_markers(col):
    c1 = _add(col, "T===<br>a<br><br>F===<br>b", "x")
    c2 = _add(col, "plain", "x")
    now = q.day_start_ms(col) + 1000
    seed_revlog(col, [{"id": now, "cid": c1, "ease": 3}, {"id": now + 1, "cid": c2, "ease": 3}])
    rows = {r.cid: r for r in q.reviews_since(col, now)}
    assert rows[c1].n_items == 2
    assert rows[c2].n_items == 1
    assert rows[c1].deck == "Default" and rows[c1].notetype == "Basic"


def test_reviews_since_excludes_manual_and_ease0_and_filters_dids(col):
    cid = _add(col)
    now = q.day_start_ms(col) + 1000
    seed_revlog(col, [
        {"id": now, "cid": cid, "ease": 3},
        {"id": now + 1, "cid": cid, "ease": 3, "type": 4},
        {"id": now + 2, "cid": cid, "ease": 0},
    ])
    rows = q.reviews_since(col, now)
    assert [r.id for r in rows] == [now]
    assert rows[0].day == q.today(col)
    assert 0 <= rows[0].hour <= 23
    assert q.reviews_since(col, now, dids={99999}) == []
    assert len(q.reviews_since(col, now, dids={rows[0].did})) == 1


def test_deck_names_use_double_colon_and_deck_ids_under(col):
    child = col.decks.id("Med::Anat")
    other = col.decks.id("Other")
    assert child in q.deck_ids_under(col, ["Med"])
    assert other not in q.deck_ids_under(col, ["Med"])
    cid = _add(col)
    col.db.execute("update cards set did=? where id=?", child, cid)
    now = q.day_start_ms(col) + 1000
    seed_revlog(col, [{"id": now, "cid": cid, "ease": 3}])
    assert q.reviews_since(col, now)[0].deck == "Med::Anat"


def test_counts_and_snapshot(col):
    c1 = _add(col, "a")
    c2 = _add(col, "b")
    assert q.new_available(col) == 2
    assert q.new_available(col, {col.decks.id("Default")}) == 2
    assert q.new_available(col, set()) == 0
    t = col.sched.today
    col.db.execute("update cards set queue=2, type=2, due=? where id=?", t - 1, c1)
    col.db.execute("update cards set queue=2, type=2, due=? where id=?", t + 3, c2)
    assert q.due_today(col) == 1
    assert q.new_available(col) == 0
    assert q.scheduled_due_by_day(col, 5) == [1, 0, 0, 1, 0]
    snap = q.card_snapshot(col, c1)
    assert snap.stability is None and snap.retrievability is None and snap.ctype == 2


def test_snapshot_with_fsrs_memory_state(col):
    col.set_config("fsrs", True)
    cid = _add(col)
    card = col.sched.getCard()
    col.sched.answerCard(card, 3)
    snap = q.card_snapshot(col, cid)
    assert isinstance(snap.stability, float)
