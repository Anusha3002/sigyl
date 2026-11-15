import pytest

from game import FIZZLE, Card, CardType, default_deck


def test_default_deck_composition():
    deck = default_deck()
    assert len(deck) == 26
    count = lambda t: sum(1 for c in deck if c.type == t)
    assert count(CardType.ATTACK) == 10
    assert count(CardType.DEFENSE) == 7
    assert count(CardType.HEAL) == 2
    assert count(CardType.MIRROR) == 2
    assert count(CardType.VANISH) == 2
    assert count(CardType.SURGE) == 2
    assert count(CardType.CHARM) == 1


def test_values_are_multiples_of_ten_and_capped_at_50():
    for c in default_deck():
        if c.type in (CardType.ATTACK, CardType.DEFENSE, CardType.HEAL):
            assert c.value % 10 == 0 and 10 <= c.value <= 50


@pytest.mark.parametrize("bad", [0, 5, 15, 60, -10])
def test_invalid_values_rejected(bad):
    with pytest.raises(ValueError):
        Card(CardType.ATTACK, bad)


@pytest.mark.parametrize("t", [CardType.MIRROR, CardType.VANISH, CardType.CHARM, CardType.SURGE])
def test_valueless_cards_reject_a_value(t):
    with pytest.raises(ValueError):
        Card(t, 10)
    assert Card(t).value == 0
    assert FIZZLE.value == 0


def test_special_flag():
    assert all(Card(t).is_special for t in (CardType.MIRROR, CardType.VANISH, CardType.CHARM, CardType.SURGE))
    assert Card(CardType.HEAL, 30).is_special
    assert not Card(CardType.ATTACK, 10).is_special
    assert not Card(CardType.DEFENSE, 10).is_special


def test_names():
    assert Card(CardType.ATTACK, 30).name == "Attack 30"
    assert Card(CardType.MIRROR).name == "Mirror"
