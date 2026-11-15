"""Special cards unlock from pick 3."""
from collections import Counter

from game import Card, CardType, Draft, default_deck


def counts(cards):
    return Counter(cards)


def test_first_two_offers_have_no_special_cards():
    for seed in range(300):
        d = Draft(seed)
        assert not any(c.is_special for c in d.offer)
        d.pick(0)
        assert not any(c.is_special for c in d.offer)


def test_specials_can_appear_from_pick_three():
    seen = False
    for seed in range(300):
        d = Draft(seed)
        d.pick(0)
        d.pick(0)
        assert d.turn == 3
        if any(c.is_special for c in d.offer):
            seen = True
    assert seen


def test_a_fizzle_at_pick_two_still_triggers_the_redraw():
    seen = False
    for seed in range(300):
        d = Draft(seed)
        d.pick(0)
        d.fizzle()
        if any(c.is_special for c in d.offer):
            seen = True
    assert seen


def test_cards_are_conserved_and_picks_never_return():
    original = counts(default_deck())
    for seed in range(100):
        d = Draft(seed)
        for _ in range(5):
            d.pick(0)
        picked = counts(d.picks)
        left = counts(d.remaining())
        assert picked + left == original
        # a picked card value never exceeds what the deck holds
        for card, n in picked.items():
            assert n <= original[card]


def test_unpicked_offered_cards_go_back_into_the_pile():
    d = Draft(11)
    d.pick(0)
    total_before = len(d.remaining())
    d.pick(0)  # triggers the redraw at pick 3
    assert len(d.remaining()) == total_before - 1
    assert len(d.offer) == 3


def test_deck_needs_enough_attack_or_defense_cards():
    import pytest
    deck = [Card(CardType.ATTACK, 10)] * 3 + [Card(CardType.HEAL, 30)] * 6
    with pytest.raises(ValueError):
        Draft(1, deck=deck)
