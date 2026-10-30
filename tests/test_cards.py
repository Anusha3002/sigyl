import pytest

from game import FIZZLE, Card, CardType, default_deck


def test_default_deck_composition():
    deck = default_deck()
    assert len(deck) == 21
    count = lambda t: sum(1 for c in deck if c.type == t)
    assert count(CardType.ATTACK) == 10
    assert count(CardType.DEFENSE) == 7
    assert count(CardType.HEAL) == 2
    assert count(CardType.MIRROR) == 2


def test_values_are_multiples_of_ten_and_capped_at_50():
    for c in default_deck():
        if c.type not in (CardType.MIRROR, CardType.FIZZLE):
            assert c.value % 10 == 0 and 10 <= c.value <= 50


@pytest.mark.parametrize("bad", [0, 5, 15, 60, -10])
def test_invalid_values_rejected(bad):
    with pytest.raises(ValueError):
        Card(CardType.ATTACK, bad)


def test_mirror_and_fizzle_have_no_value():
    with pytest.raises(ValueError):
        Card(CardType.MIRROR, 10)
    assert FIZZLE.value == 0


def test_names():
    assert Card(CardType.ATTACK, 30).name == "Attack 30"
    assert Card(CardType.MIRROR).name == "Mirror"
