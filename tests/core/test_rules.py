from ebbin.core.rules import (
    Combo, LevelInfo, XpLedger, answer_xp, combo_multiplier, level_from_total,
    main_mission_bonus, next_combo, rank_for, xp_for_level,
)


def test_combo_reaches_cap_on_tenth_correct():
    c = Combo()
    for _ in range(10):
        c = next_combo(c, 3)
    assert combo_multiplier(c) == 1.5
    assert combo_multiplier(next_combo(c, 4)) == 1.5


def test_hard_keeps_combo_again_resets():
    c = next_combo(next_combo(Combo(), 3), 3)
    assert next_combo(c, 2).count == 2 and next_combo(c, 1).count == 0


def test_answer_xp_values():
    assert answer_xp(1, Combo(0), False) == 2
    assert answer_xp(3, Combo(1), False) == 11
    assert answer_xp(4, Combo(10), False) == 15
    assert answer_xp(3, Combo(10), True) == 8


def test_level_curve():
    assert xp_for_level(1) == 400 and xp_for_level(2) == 424
    assert level_from_total(0) == LevelInfo(1, 0, 400)
    assert level_from_total(424 + 400) == LevelInfo(3, 0, xp_for_level(3))


def test_ranks():
    assert rank_for(1) == "Rabisco" and rank_for(9) == "Rascunho"
    assert rank_for(59) == "Biblioteca" and rank_for(60) == "Ebbinghaus"


def test_main_mission_bonus():
    assert main_mission_bonus(10) == 130


def test_ledger_reconcile_drops_undone_answer():
    l = XpLedger()
    l.answers[101] = 10
    l.answers[102] = 12
    assert l.reconcile({101}) == [102] and l.total(bootstrap=5) == 15


def test_ledger_total_includes_bonuses_and_roundtrips_json():
    import json
    l = XpLedger()
    l.answers[1] = 10
    l.bonuses["main:5"] = 100
    l2 = XpLedger.from_dict(json.loads(json.dumps(l.to_dict())))
    assert l2.answers == {1: 10} and l2.total(0) == 110
    c = Combo.from_dict(json.loads(json.dumps(Combo(3).to_dict())))
    assert c == Combo(3)
