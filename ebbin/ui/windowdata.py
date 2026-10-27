"""Data/ops layer behind the Métricas / Objetivos / Ajustes window (no aqt imports)."""
from __future__ import annotations

import json
import uuid
from datetime import date, timedelta

from ebbin.core import mastery, metrics, objectives
from ebbin.core.challenge import capacity
from ebbin.core.objectives import Objective
from ebbin.data import queries as q
from ebbin.ui.engine import streak_for

_DAY_MS = 86_400_000
_CAL_DAYS = 84
_MIN_ANSWERS = 10
_PERIOD_DAYS = {"30d": 30, "12w": 84, "all": None}
_FALLBACK_IVL = 21


def _objective_list(state) -> list[Objective]:
    return [Objective.from_dict(d) for d in state.objectives]


def _active_objective(state) -> Objective | None:
    for o in _objective_list(state):
        if o.id == state.active_objective and not o.archived:
            return o
    return None


def _save_objectives(state, objs: list[Objective]) -> None:
    state.objectives = [o.to_dict() for o in objs]


def _desired_retention(col, dids: set[int] | None) -> float:
    try:
        if dids:
            for did in sorted(dids):
                return float(col.decks.config_dict_for_deck_id(did)["desiredRetention"])
        return float(col.decks.config_dict_for_deck_id(1)["desiredRetention"])
    except Exception:
        return 0.90


def _cids_in(col, dids: set[int] | None) -> set[int] | None:
    if dids is None:
        return None
    if not dids:
        return set()
    marks = ",".join("?" * len(dids))
    return set(col.db.list(f"select id from cards where did in ({marks})", *dids))


def _mastered_cards(col, dids: set[int] | None, mastered_days: float) -> tuple[int, int]:
    """(mastered, total) cards in the decks; no memory state -> ivl >= 21 fallback."""
    where, args = "", []
    if dids is not None:
        if not dids:
            return 0, 0
        where = f" and did in ({','.join('?' * len(dids))})"
        args = list(dids)
    total = int(col.db.scalar(f"select count() from cards where 1=1{where}", *args) or 0)
    done = 0
    for ivl, data in col.db.all(f"select ivl, data from cards where type = 2{where}", *args):
        stability = None
        try:
            stability = json.loads(data or "{}").get("s")
        except ValueError:
            pass
        if stability is not None:
            done += stability >= mastered_days
        else:
            done += ivl >= _FALLBACK_IVL
    return done, total


def metrics_payload(col, state, cfg: dict, scope: str, period: str, today_date: date) -> dict:
    t = q.today(col)
    obj = _active_objective(state) if scope == "active" else None
    dids = q.deck_ids_under(col, obj.deck_roots) if obj else None
    n_days = _PERIOD_DAYS.get(period, 30)
    start = q.day_start_ms(col)
    since = 0 if n_days is None else start - (n_days - 1) * _DAY_MS
    fetch_since = 0 if n_days is None else min(since, start - (_CAL_DAYS - 1) * _DAY_MS)
    all_rows = q.reviews_since(col, fetch_since, dids)
    rows = [r for r in all_rows if n_days is None or r.day >= t - n_days + 1]
    cal_first = t - _CAL_DAYS + 1

    cons = metrics.consistency(
        [r for r in all_rows if r.day >= cal_first], list(range(cal_first, t + 1)),
        state.missions_by_day, cfg["budget_min"])
    streak, _ = streak_for(col, state)
    cons["streak"] = {"current": streak.current, "best": streak.best}
    for cell in cons["calendar"]:  # 0 = Monday, so the heatmap can align columns to calendar weeks
        cell["weekday"] = (today_date - timedelta(days=t - cell["day"])).weekday()

    tr = metrics.true_retention(rows)
    desired = _desired_retention(col, dids)
    improve = {
        "by_deck_accuracy": metrics.by_deck_accuracy(rows),
        "by_tag_compare": metrics.by_tag_compare(rows),
        "problem_cards": metrics.problem_cards(rows),
        "true_retention": tr,
        "desired_retention": desired,
        "retention_hint": metrics.retention_hint(tr, desired),
        "accuracy_by_hour": metrics.accuracy_by_hour(rows),
    }

    cids = _cids_in(col, dids)
    since_id = 0 if n_days is None else since
    mastered_n = sum(1 for rid, cid in state.mastered.items()
                     if rid >= since_id and (cids is None or cid in cids))
    secs = sum(r.time_ms for r in rows) // 1000
    avg_s = q.avg_time_s(col) or 30.0
    k = objectives.suggest_new_today(capacity(cfg["budget_min"], avg_s), q.due_today(col))
    series = metrics.project_load(q.scheduled_due_by_day(col), k if q.new_available(col, dids) > 0 else 0)
    cap = capacity(cfg["budget_min"], avg_s)
    off = metrics.first_over_budget_day(series, avg_s, cfg["budget_min"])
    efficiency = {
        "sec_per_card_trend": metrics.sec_per_card_trend(rows),
        "sec_by_items": metrics.sec_by_items(rows),
        "items_hint": metrics.items_hint(rows),
        "mastered_per_hour": metrics.mastered_per_hour(mastered_n, secs),
        "load": {
            "series": series, "capacity": cap,
            "first_over": (today_date + timedelta(days=off)).strftime("%d/%m") if off is not None else None,
        },
    }

    retention_series, rescued_by_week = [], []
    for w in range(12):
        lo = cal_first + 7 * w
        wk = [r for r in all_rows if lo <= r.day < lo + 7 and r.type == 1]
        retention_series.append(round(sum(1 for r in wk if r.ease > 1) / len(wk), 4) if wk else None)
        n = 0
        for rid, cid in state.rescued.items():
            if lo <= q.day_of_ms(col, rid) < lo + 7 and (cids is None or cid in cids):
                n += 1
        rescued_by_week.append(n)

    return {
        "consistency": cons, "improve": improve, "efficiency": efficiency,
        "curve": {"retention_series": retention_series, "rescued_by_week": rescued_by_week},
        "empty": len(rows) < _MIN_ANSWERS,
        "scope_fallback": scope == "active" and obj is None,
    }


def objectives_payload(col, state, today_date: date, mastered_days: float = 21) -> dict:
    items = []
    for o in _objective_list(state):
        dids = q.deck_ids_under(col, o.deck_roots)
        remaining = q.new_available(col, dids)
        dl = objectives.days_left(o, today_date)
        done, total = _mastered_cards(col, dids, mastered_days)
        items.append({
            "id": o.id, "name": o.name, "exam_date": o.exam_date, "deck_roots": list(o.deck_roots),
            "archived": o.archived, "archived_summary": o.archived_summary,
            "countdown": objectives.countdown_text(o, today_date), "days_left": dl,
            "new_remaining": remaining, "pace": objectives.new_pace(remaining, dl),
            "stars": mastery.stars(done, total),
        })
    names = sorted(n.name.replace("\x1f", "::") for n in col.decks.all_names_and_ids())
    return {"active_id": state.active_objective, "items": items, "decks": names}


def objective_upsert(state, data: dict) -> str:
    name = str(data.get("name") or "").strip()
    if not name:
        raise ValueError("nome obrigatório")
    exam = data.get("exam_date") or None
    if exam is not None:
        try:
            date.fromisoformat(exam)
        except (TypeError, ValueError):
            raise ValueError("data inválida") from None
    roots = data.get("deck_roots") or []
    if not isinstance(roots, list) or not all(isinstance(r, str) for r in roots):
        raise ValueError("decks inválidos")
    objs = _objective_list(state)
    oid = data.get("id")
    existing = next((o for o in objs if o.id == oid), None) if oid else None
    if existing:
        existing.name, existing.exam_date, existing.deck_roots = name, exam, list(roots)
    else:
        oid = uuid.uuid4().hex
        objs.append(Objective(id=oid, name=name, exam_date=exam, deck_roots=list(roots)))
    _save_objectives(state, objs)
    return oid


def objective_activate(state, oid: str) -> None:
    objs = objectives.activate(_objective_list(state), oid)  # KeyError if unknown
    _save_objectives(state, objs)
    state.active_objective = oid


def objective_archive(col, state, oid: str, today_date: date, mastered_days: float = 21) -> dict:
    objs = _objective_list(state)
    o = next((x for x in objs if x.id == oid), None)
    if o is None:
        raise KeyError(oid)
    dids = q.deck_ids_under(col, o.deck_roots)
    rows = q.reviews_since(col, 0, dids)
    summary = {
        "mastered": _mastered_cards(col, dids, mastered_days)[0],
        "study_days": len({r.day for r in rows}),
        "accuracy": round(sum(1 for r in rows if r.ease > 1) / len(rows), 4) if rows else None,
    }
    _save_objectives(state, objectives.archive(objs, oid, summary))
    if state.active_objective == oid:
        state.active_objective = None
    return summary


def objective_delete(state, oid: str) -> None:
    state.objectives = [d for d in state.objectives if d.get("id") != oid]
    if state.active_objective == oid:
        state.active_objective = None
