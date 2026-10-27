"""Deck-browser hints (no aqt imports). Ids are stable per day so a dismissal sticks."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from ebbin.core.challenge import capacity
from ebbin.core.metrics import first_over_budget_day, project_load, weekly_insights
from ebbin.core.objectives import Objective, suggest_new_today
from ebbin.data import queries as q
from ebbin.ui.schedtools import apply_auto_new, fsrs_reminder_due

_DAY_MS = 86_400_000


def _anki_date(col) -> date:
    """Calendar date of the current Anki day (day start, not midnight)."""
    return datetime.fromtimestamp(q.day_start_ms(col) / 1000).date()


def _weekly_text(col, st, t: int, weekday: int) -> str | None:
    """Summary of the Mon..Sun week ending on the latest Sunday; None if nothing to say."""
    sunday = t - ((weekday + 1) % 7)
    if st.installed_day > sunday:
        return None
    first_time = st.last_weekly_summary_day < sunday
    # Already shown: keep it visible for the rest of the day it was first shown.
    if not first_time and not (st.last_weekly_summary_day == sunday and st.weekly_shown_day == t):
        return None
    st.last_weekly_summary_day = sunday
    monday = sunday - 6
    since = q.day_start_ms(col) - (t - (monday - 7)) * _DAY_MS
    rows = q.reviews_since(col, since)
    this_week = [r for r in rows if monday <= r.day <= sunday]
    if not this_week:
        return None
    last_week = [r for r in rows if r.day < monday]
    insights = weekly_insights(this_week, last_week, {r.day for r in this_week},
                               [(d, d - monday) for d in range(monday, sunday + 1)])
    text = " · ".join(insights[:3]) or None
    if text and first_time:
        st.weekly_shown_day = t
    return text


def _active_objective(st) -> Objective | None:
    for d in st.objectives:
        if d.get("id") == st.active_objective and not d.get("archived"):
            return Objective.from_dict(d)
    return None


def auto_new_hint(col, st, cfg: dict) -> dict | None:
    """Runs apply_auto_new at most once per Anki day (mutates st.day_stats; the caller saves).
    Shared-preset skips are remembered in day_stats so the hint survives later rebuilds."""
    t = q.today(col)
    obj = _active_objective(st)
    if cfg.get("auto_new_per_day") and obj is not None:
        avg_s = q.avg_time_s(col)
        res = apply_auto_new(col, st, cfg, obj, capacity(cfg["budget_min"], avg_s), q.due_today(col))
        if res is not None:
            st.day_stats.setdefault(t, {})["auto_new_skipped"] = list(res["skipped_shared"])
    names = st.day_stats.get(t, {}).get("auto_new_skipped") or []
    if not names or not cfg.get("auto_new_per_day") or obj is None:
        return None
    return {"id": f"autonew:{t}", "kind": "warn",
            "text": f"Novos automáticos: o preset '{', '.join(names)}' é compartilhado com outros "
                    "decks — crie um preset só para o objetivo"}


def build_hints(col, engine_state, cfg: dict, today_view: dict) -> list[dict]:
    """Hints to show now. May mutate engine_state (weekly summary day, fsrs_reminder, day_stats
    auto_new); the caller saves the state."""
    st = engine_state
    t = q.today(col)
    today_date = _anki_date(col)
    budget = cfg["budget_min"]
    avg_s = q.avg_time_s(col)
    k = suggest_new_today(capacity(budget, avg_s), q.due_today(col))
    has_new = q.new_available(col) > 0
    out: list[dict] = []

    off = first_over_budget_day(project_load(q.scheduled_due_by_day(col), k if has_new else 0), avg_s, budget)
    if off is not None:
        when = (today_date + timedelta(days=off)).strftime("%d/%m")
        out.append({"id": f"load:{t}", "kind": "warn",
                    "text": f"No ritmo atual você passa dos {budget} min em {when}"})
    if k > 0 and has_new:
        out.append({"id": f"suggest:{t}", "kind": "tip", "text": f"sugestão: {k} novos hoje"})

    weekly = _weekly_text(col, st, t, today_date.weekday())
    if weekly:
        sunday = t - ((today_date.weekday() + 1) % 7)
        out.append({"id": f"weekly:{sunday}", "kind": "info", "text": weekly})

    m_used = st.missions_by_day.get(t, {}).get("m_used", 1.0)
    if st.comeback_days_left > 0 or (m_used < 1.0 and m_used != st.m):
        out.append({"id": f"comeback:{t}", "kind": "info", "text": "bem-vindo de volta"})

    if fsrs_reminder_due(col, st):
        out.append({"id": f"fsrs:{t}", "kind": "fsrs",
                    "text": "Hora de otimizar o FSRS: abra as opções do deck e clique em Otimizar"})

    auto = auto_new_hint(col, st, cfg)
    if auto:
        out.append(auto)

    return [h for h in out if h["id"] not in st.dismissed_hints]
