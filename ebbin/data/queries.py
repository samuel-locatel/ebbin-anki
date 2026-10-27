"""Read layer: Anki collection -> plain dataclasses."""
from __future__ import annotations

import re
import statistics
from datetime import datetime

from ..core.models import CardSnap, ReviewRow

_DAY_MS = 86_400_000
_MARKER_RE = re.compile(r"[TF]===")


def day_start_ms(col) -> int:
    return (col.sched.day_cutoff - 86400) * 1000


def today(col) -> int:
    return col.sched.today


def day_of_ms(col, ms: int) -> int:
    cutoff_ms = col.sched.day_cutoff * 1000
    return col.sched.today - (cutoff_ms - 1 - ms) // _DAY_MS


def _n_items(flds: str) -> int:
    return max(1, len(_MARKER_RE.findall(flds)))


def reviews_since(col, since_ms: int, dids: set[int] | None = None) -> list[ReviewRow]:
    rows = col.db.all(
        "select r.id, r.cid, c.did, d.name, nt.name, n.tags, r.ease, r.time, r.type, n.flds "
        "from revlog r join cards c on c.id = r.cid join notes n on n.id = c.nid "
        "join notetypes nt on nt.id = n.mid join decks d on d.id = c.did "
        "where r.id >= ? and r.type != 4 and r.ease != 0 order by r.id",
        since_ms,
    )
    out = []
    for rid, cid, did, deck, nt, tags, ease, time_ms, rtype, flds in rows:
        if dids is not None and did not in dids:
            continue
        out.append(
            ReviewRow(
                id=rid, cid=cid, did=did, deck=deck.replace("\x1f", "::"), notetype=nt,
                tags=tags, ease=ease, time_ms=time_ms, type=rtype,
                day=day_of_ms(col, rid), hour=datetime.fromtimestamp(rid / 1000).hour,
                n_items=_n_items(flds),
            )
        )
    return out


def _since_days(col, days: int) -> int:
    return day_start_ms(col) - (days - 1) * _DAY_MS


def avg_time_s(col, days: int = 14) -> float:
    rows = reviews_since(col, _since_days(col, days))
    if not rows:
        return 30.0
    return sum(r.time_ms for r in rows) / len(rows) / 1000


def median_time_s(col, days: int = 14) -> float | None:
    rows = reviews_since(col, _since_days(col, days))
    if not rows:
        return None
    return statistics.median(r.time_ms for r in rows) / 1000


def due_today(col) -> int:
    t = col.sched.today
    review = col.db.scalar("select count() from cards where queue in (2, 3) and due <= ?", t)
    learn = col.db.scalar("select count() from cards where queue = 1 and due <= ?", col.sched.day_cutoff)
    return int(review or 0) + int(learn or 0)


def new_available(col, dids: set[int] | None = None) -> int:
    if dids is None:
        return int(col.db.scalar("select count() from cards where queue = 0") or 0)
    if not dids:
        return 0
    marks = ",".join("?" * len(dids))
    return int(col.db.scalar(f"select count() from cards where queue = 0 and did in ({marks})", *dids) or 0)


def card_snapshot(col, cid: int) -> CardSnap:
    card = col.get_card(cid)
    ms = card.memory_state
    stability = float(ms.stability) if ms is not None else None
    r = col.card_stats_data(cid).fsrs_retrievability
    return CardSnap(stability=stability, retrievability=float(r) if r else None, ctype=card.type)


def deck_ids_under(col, root_names: list[str]) -> set[int]:
    roots = set(root_names)
    ids = set()
    for did, name in col.db.all("select id, name from decks"):
        name = name.replace("\x1f", "::")
        if any(name == r or name.startswith(r + "::") for r in roots):
            ids.add(did)
    return ids


def scheduled_due_by_day(col, horizon: int = 30) -> list[int]:
    t = col.sched.today
    out = [0] * horizon
    for due, n in col.db.all("select due, count() from cards where queue in (2, 3) group by due"):
        off = max(0, due - t)
        if off < horizon:
            out[off] += n
    return out
