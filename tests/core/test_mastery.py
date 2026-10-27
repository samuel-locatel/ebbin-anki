from ebbin.core.mastery import became_mastered, card_state, is_rescued, stars


def test_card_state_new_and_learning():
    assert card_state(0, 0, None) == "novo"
    assert card_state(1, 1, None) == "aprendendo"
    assert card_state(3, 1, 5.0) == "aprendendo"


def test_card_state_review_boundary():
    assert card_state(2, 2, 20.9) == "firme"
    assert card_state(2, 2, 21.0) == "dominado"
    assert card_state(2, 2, None) == "firme"


def test_became_mastered():
    assert became_mastered(None, 21.0)
    assert became_mastered(20.9, 21.0)
    assert not became_mastered(21.0, 30.0)
    assert not became_mastered(10.0, 20.9)
    assert not became_mastered(10.0, None)


def test_is_rescued():
    assert is_rescued(0.84, 3)
    assert not is_rescued(0.85, 3)
    assert not is_rescued(0.5, 1)
    assert not is_rescued(None, 3)


def test_stars():
    assert stars(0, 0) == 0
    assert stars(24, 100) == 0
    assert stars(25, 100) == 1
    assert stars(50, 100) == 2
    assert stars(79, 100) == 2
    assert stars(80, 100) == 3
