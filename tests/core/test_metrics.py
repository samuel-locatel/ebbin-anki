from ebbin.core import metrics as m
from ebbin.core.models import ReviewRow


def R(ease=3, deck="A::B", tags="", time_ms=5000, type=1, day=0, hour=9, n_items=1, cid=1):
    return ReviewRow(0, cid, 1, deck, "nt", tags, ease, time_ms, type, day, hour, n_items)


def test_empty_inputs():
    assert m.by_deck_accuracy([]) == []
    assert m.problem_cards([]) == []
    assert m.true_retention([]) is None
    assert m.accuracy_by_hour([]) == [None] * 24
    assert m.sec_per_card_trend([]) == []
    assert m.sec_by_items([]) == []
    assert m.items_hint([]) is None
    assert m.weekly_insights([], [], set(), []) == []
    c = m.consistency([], [], {}, 30)
    assert c["met_pct"] == 0 and c["calendar"] == []
    assert all(t["acc_a"] is None for t in m.by_tag_compare([]))


def test_consistency():
    rows = [R(day=1, time_ms=600000), R(day=2, time_ms=3600000)]
    c = m.consistency(rows, [0, 1, 2, 3], {1: {"main_done": True}}, 30)
    assert c["calendar"][1] == {"day": 1, "minutes": 10.0, "met": True}
    assert c["met_pct"] == 0.25
    assert (c["of_days"], c["within_budget"]) == (2, 1)


def test_deck_accuracy():
    rows = [R(ease=1, deck="X::Bom") for _ in range(5)] + [R(deck="X::Bom") for _ in range(15)]
    rows += [R(deck="Y::Otimo") for _ in range(20)] + [R(deck="Z") for _ in range(5)]
    out = m.by_deck_accuracy(rows)
    assert [d["deck"] for d in out] == ["Bom", "Otimo"]
    assert out[0] == {"deck": "Bom", "acc": 0.75, "lapses": 5, "n": 20}


def test_tag_compare():
    rows = [R(tags="certo-errado x", ease=1, time_ms=2000), R(tags="conceito", time_ms=4000)]
    t = m.by_tag_compare(rows)[0]
    assert (t["acc_a"], t["acc_b"], t["sec_a"], t["sec_b"]) == (0.0, 1.0, 2.0, 4.0)
    assert m.by_tag_compare(rows)[1]["acc_a"] is None


def test_problem_cards():
    rows = [R(ease=1, cid=2)] * 3 + [R(ease=1, cid=3)] + [R(ease=1, cid=4, type=0)]
    assert m.problem_cards(rows, top=1) == [{"cid": 2, "lapses": 3}]
    assert len(m.problem_cards(rows)) == 2


def test_retention():
    assert m.true_retention([R()] * 29) is None
    rows = [R()] * 27 + [R(ease=1)] * 3
    assert m.true_retention(rows) == 0.9
    assert m.retention_hint(0.80).startswith("Retenção abaixo")
    assert m.retention_hint(0.95).startswith("Retenção acima")
    assert m.retention_hint(0.90) is None and m.retention_hint(None) is None


def test_hour_trend_items():
    h = m.accuracy_by_hour([R(hour=3), R(hour=3, ease=1)])
    assert h[3] == 0.5 and h[4] is None and len(h) == 24
    assert m.sec_per_card_trend([R(day=8, time_ms=2000), R(day=1)]) == [
        {"week": 0, "sec": 5.0},
        {"week": 1, "sec": 2.0},
    ]
    rows = [R(n_items=1, time_ms=2000)] * 20 + [R(n_items=5, time_ms=5000)] * 20
    assert [b["items"] for b in m.sec_by_items(rows)] == [1, "4+"]
    assert m.items_hint(rows) == "Cards com vários itens levam 2,5× mais tempo: peça ao agente 1 item por card"
    assert m.items_hint(rows[:30]) is None


def test_mastered_per_hour():
    assert m.mastered_per_hour(10, 7200) == 5
    assert m.mastered_per_hour(10, 0) == 0


def test_projection():
    assert m.project_load([10] * 30, 0) == [10] * 30
    p = m.project_load([0] * 30, 10)
    assert p[1] == 10 and p[3] == 20 and p[0] == 0 and len(p) == 30
    assert len(m.project_load([1], 0)) == 30
    assert m.first_over_budget_day([30] * 5 + [50] * 25, 32, 20) == 5
    assert m.first_over_budget_day([1], 1, 20) is None


def test_weekly_insights():
    last = [R(deck="D::Dir", time_ms=10000)] * 20
    this = [R(deck="D::Dir", ease=1, time_ms=5000)] * 10 + [R(deck="D::Dir", time_ms=5000)] * 10
    wd = [(100 + i, i) for i in range(7)]
    out = m.weekly_insights(this, last, {100, 103, 104, 105}, wd)
    assert out == [
        "Dir caiu 50 pp",
        "Seu tempo por card caiu de 10s para 5s",
        "ter, qua e dom sem estudo",
    ]
    assert m.weekly_insights([], [], {100, 101, 102, 103, 104, 105}, wd) == ["dom sem estudo"]
