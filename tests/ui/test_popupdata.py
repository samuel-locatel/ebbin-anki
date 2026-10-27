from ebbin.ui.popupdata import build_view, format_duration


def payload(**kw):
    p = {"session_xp": 412, "answers": 37, "acc": 89.4, "duration_s": 1180,
         "level_before": {"level": 7, "into": 400, "needed": 1000},
         "level_after": {"level": 7, "into": 820, "needed": 1000},
         "main_bonus": 80, "streak": 12, "streak_bonus": 20, "rescued": 3, "mastered_new": 2,
         "badge": "Preciso", "records": ["Maior combo"], "tomorrow_due": 34, "fits_budget": True}
    p.update(kw)
    return p


def test_duration():
    assert format_duration(1180) == "19m40s"
    assert format_duration(65) == "1m05s"


def test_basic():
    v = build_view(payload(), 20)
    assert v["xp"] == 412
    assert v["summary"] == "37 revisões · 89% de acerto · 19m40s"
    assert v["remaining_text"] == "faltam 180 XP p/ o nível 8"
    assert v["a_pct"] == 40 and round(v["b_pct"]) == 42
    assert not v["level_up"] and v["level_up_text"] == ""
    assert [r["text"] for r in v["rows"]] == [
        "Desafio cumprido", "dias seguidos", "3 memórias resgatadas", "2 novos dominados"]
    assert v["rows"][0]["delta"] == "+80" and v["rows"][1]["delta"] == "+20"
    assert v["badge"] == "Preciso"
    assert v["records"] == ["novo recorde: Maior combo"]
    assert v["footer"] == "Amanhã: ~34 revisões previstas · cabe nos 20 min"


def test_acc_half_up():
    assert "89% de acerto" in build_view(payload(acc=88.5), 20)["summary"]


def test_level_up():
    v = build_view(payload(level_after={"level": 8, "into": 100, "needed": 1200}), 20)
    assert v["level_up"] and v["level_up_text"] == "nível 8!"
    assert v["a_pct"] == 0 and round(v["b_pct"], 1) == 8.3
    assert v["remaining_text"] == "faltam 1100 XP p/ o nível 9"


def test_no_bonus_empty_extras():
    v = build_view(payload(main_bonus=0, streak_bonus=0, rescued=0, mastered_new=0,
                           badge=None, records=[]), 20)
    assert v["rows"] == [] and v["badge"] is None and v["records"] == []


def test_over_budget():
    v = build_view(payload(fits_budget=False), 15)
    assert v["footer"].endswith("· passa dos 15 min")


def test_theme_class_matches_sketch_themeclass():
    from ebbin.ui.popupdata import theme_class
    assert theme_class(False, "night") == ""
    assert theme_class(False, "slate") == ""
    assert theme_class(True, "night") == "night"
    assert theme_class(True, "slate") == "slate"
    assert theme_class(True, "weird") == "night"
