import pytest

from game import Card, CardType, Draft, DraftError
from game.cards import FIZZLE


def test_initial_offer_is_three_cards_from_the_deck():
    d = Draft(seed=1)
    assert len(d.offer) == 3
    assert d.turn == 1 and not d.done


def test_pick_moves_card_and_refills_offer():
    d = Draft(seed=1)
    before = list(d.offer)
    picked = d.pick(1)
    assert picked == before[1]
    assert d.picks == [before[1]]
    assert len(d.offer) == 3
    # the two unpicked cards stay on offer
    assert before[0] in d.offer and before[2] in d.offer


def test_five_picks_finish_the_draft():
    d = Draft(seed=2)
    for _ in range(5):
        d.pick(0)
    assert d.done and len(d.sequence()) == 5
    with pytest.raises(DraftError):
        d.pick(0)
    with pytest.raises(DraftError):
        d.fizzle()


def test_sequence_before_done_raises():
    d = Draft(seed=2)
    d.pick(0)
    with pytest.raises(DraftError):
        d.sequence()


def test_bad_index_raises():
    d = Draft(seed=3)
    with pytest.raises(DraftError):
        d.pick(3)
    with pytest.raises(DraftError):
        d.pick(-1)


def test_fizzle_takes_a_slot_without_using_a_card():
    d = Draft(seed=4)
    offer = list(d.offer)
    assert d.fizzle() == FIZZLE
    assert d.offer == offer
    assert d.turn == 2


def test_same_seed_is_reproducible_and_different_seeds_differ():
    a, b, c = Draft(7), Draft(7), Draft(8)
    assert a.offer == b.offer
    runs = {tuple(Draft(s).offer) for s in range(20)}
    assert len(runs) > 1


def test_players_have_separate_decks():
    d1, d2 = Draft(1), Draft(1)
    d1.pick(0)
    assert d2.picks == [] and len(d2.offer) == 3


def test_a_picked_card_does_not_return_to_the_offer():
    d = Draft(5, deck=[Card(CardType.ATTACK, v) for v in (10, 20, 30, 40, 50, 10, 20)])
    picked = [d.pick(0) for _ in range(5)]
    # every card in the 7-card deck is used at most once across picks + offer
    assert len(picked) + len(d.offer) <= 7


def test_deck_too_small_rejected():
    with pytest.raises(ValueError):
        Draft(1, deck=[Card(CardType.ATTACK, 10)] * 4)
