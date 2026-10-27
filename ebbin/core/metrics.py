"""Métricas, projeção de carga e insights semanais (puro, sem anki/aqt)."""

from collections import defaultdict

from ebbin.core.models import ReviewRow

_WEEKDAYS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
_LAPSE_TYPES = (1, 2)


def _acc(rows) -> float | None:
    if not rows:
        return None
    return round(sum(1 for r in rows if r.ease > 1) / len(rows), 4)


def _sec(rows) -> float | None:
    if not rows:
        return None
    return round(sum(r.time_ms for r in rows) / len(rows) / 1000, 1)


def _is_lapse(r: ReviewRow) -> bool:
    return r.ease == 1 and r.type in _LAPSE_TYPES


def _leaf(deck: str) -> str:
    return deck.rsplit("::", 1)[-1]


def consistency(rows, days, missions_by_day, budget_min) -> dict:
    ms: dict[int, int] = defaultdict(int)
    for r in rows:
        ms[r.day] += r.time_ms
    calendar = []
    met_count = 0
    of_days = 0
    within = 0
    for d in days:
        minutes = round(ms.get(d, 0) / 60000, 1)
        met = bool(missions_by_day.get(d, {}).get("main_done", False))
        met_count += met
        if minutes > 0:
            of_days += 1
            if minutes <= budget_min:
                within += 1
        calendar.append({"day": d, "minutes": minutes, "met": met})
    return {
        "calendar": calendar,
        "met_pct": met_count / len(days) if days else 0,
        "within_budget": within,
        "of_days": of_days,
    }


def by_deck_accuracy(rows, min_reviews=20) -> list[dict]:
    groups: dict[str, list] = defaultdict(list)
    for r in rows:
        groups[_leaf(r.deck)].append(r)
    out = [
        {
            "deck": deck,
            "acc": _acc(rs),
            "lapses": sum(1 for r in rs if _is_lapse(r)),
            "n": len(rs),
        }
        for deck, rs in groups.items()
        if len(rs) >= min_reviews
    ]
    out.sort(key=lambda x: x["acc"])
    return out


def by_tag_compare(
    rows, pairs=(("certo-errado", "conceito"), ("pegadinha", "questao-real"))
) -> list[dict]:
    tagged = [(set(r.tags.split()), r) for r in rows]
    out = []
    for a, b in pairs:
        ra = [r for t, r in tagged if a in t]
        rb = [r for t, r in tagged if b in t]
        out.append(
            {
                "a": a,
                "b": b,
                "acc_a": _acc(ra),
                "acc_b": _acc(rb),
                "sec_a": _sec(ra),
                "sec_b": _sec(rb),
            }
        )
    return out


def problem_cards(rows, top=15) -> list[dict]:
    counts: dict[int, int] = defaultdict(int)
    for r in rows:
        if _is_lapse(r):
            counts[r.cid] += 1
    items = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [{"cid": c, "lapses": n} for c, n in items[:top]]


def true_retention(rows) -> float | None:
    rs = [r for r in rows if r.type == 1]
    if len(rs) < 30:
        return None
    return sum(1 for r in rs if r.ease > 1) / len(rs)


def retention_hint(true_ret, desired=0.90) -> str | None:
    if true_ret is None:
        return None
    if true_ret < desired - 0.03:
        return "Retenção abaixo da meta: rode Otimizar no FSRS e evite apertar Fácil em dúvida"
    if true_ret > desired + 0.04:
        return "Retenção acima da meta: dá pra aceitar intervalos maiores"
    return None


def accuracy_by_hour(rows) -> list[float | None]:
    buckets: list[list] = [[] for _ in range(24)]
    for r in rows:
        if 0 <= r.hour < 24:
            buckets[r.hour].append(r)
    return [_acc(b) for b in buckets]


def sec_per_card_trend(rows, by="week") -> list[dict]:
    groups: dict[int, list] = defaultdict(list)
    for r in rows:
        groups[r.day // 7].append(r)
    return [{"week": w, "sec": _sec(groups[w])} for w in sorted(groups)]


def _item_bucket(n: int):
    return n if n in (1, 2, 3) else "4+"


def sec_by_items(rows) -> list[dict]:
    groups: dict = defaultdict(list)
    for r in rows:
        groups[_item_bucket(max(r.n_items, 1))].append(r)
    return [
        {"items": k, "sec": _sec(groups[k]), "n": len(groups[k])}
        for k in (1, 2, 3, "4+")
        if k in groups
    ]


def items_hint(rows) -> str | None:
    one = [r for r in rows if r.n_items == 1]
    many = [r for r in rows if r.n_items >= 2]
    if len(one) < 20 or len(many) < 20:
        return None
    s1 = sum(r.time_ms for r in one) / len(one)
    s2 = sum(r.time_ms for r in many) / len(many)
    if s1 <= 0 or s2 / s1 < 2:
        return None
    x = f"{s2 / s1:.1f}".replace(".", ",")
    return f"Cards com vários itens levam {x}× mais tempo: peça ao agente 1 item por card"


def mastered_per_hour(mastered_count: int, review_seconds: int) -> float:
    if review_seconds <= 0:
        return 0.0
    return mastered_count / (review_seconds / 3600)


def project_load(scheduled, new_per_day, horizon=30) -> list[int]:
    load = list(scheduled[:horizon]) + [0] * max(0, horizon - len(scheduled))
    if new_per_day > 0:
        for d in range(horizon):
            for off in (1, 3, 8, 20):
                if d + off < horizon:
                    load[d + off] += new_per_day
    return load


def first_over_budget_day(load, avg_s, budget_min) -> int | None:
    for i, n in enumerate(load):
        if n * avg_s > budget_min * 60:
            return i
    return None


def _join_pt(items: list[str]) -> str:
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " e " + items[-1]


def weekly_insights(
    rows_this_week, rows_last_week, study_days_this_week, week_days
) -> list[str]:
    out: list[str] = []

    this_g: dict[str, list] = defaultdict(list)
    last_g: dict[str, list] = defaultdict(list)
    for r in rows_this_week:
        this_g[_leaf(r.deck)].append(r)
    for r in rows_last_week:
        last_g[_leaf(r.deck)].append(r)
    best = None
    for deck, rt in this_g.items():
        rl = last_g.get(deck)
        if not rl or len(rt) < 10 or len(rl) < 10:
            continue
        pp = round((_acc(rl) - _acc(rt)) * 100)
        if pp >= 5 and (best is None or pp > best[1]):
            best = (deck, pp)
    if best:
        out.append(f"{best[0]} caiu {best[1]} pp")

    if len(rows_this_week) >= 20 and len(rows_last_week) >= 20:
        a = sum(r.time_ms for r in rows_last_week) / len(rows_last_week) / 1000
        b = sum(r.time_ms for r in rows_this_week) / len(rows_this_week) / 1000
        if a > 0 and abs(b - a) / a >= 0.10:
            verb = "caiu" if b < a else "subiu"
            out.append(f"Seu tempo por card {verb} de {round(a)}s para {round(b)}s")

    missed = [_WEEKDAYS[wd] for d, wd in week_days if d not in study_days_this_week]
    if missed:
        out.append(f"{_join_pt(missed)} sem estudo")

    return out[:3]
