import pytest

from game import FIZZLE, Card, CardType, default_deck, resolve_match, resolve_slot

A = lambda v: Card(CardType.ATTACK, v)
D = lambda v: Card(CardType.DEFENSE, v)
H = lambda v: Card(CardType.HEAL, v)
M = Card(CardType.MIRROR)
F = Card(CardType.FIZZLE)


def slot(a, b, aura=(100, 100)):
    return resolve_slot(1, a, b, aura)


def test_attack_vs_weaker_attack_only_difference_counts():
    r = slot(A(10), A(20))
    assert r.delta == (-10, 0)  # the 10-point attacker loses 10
    r = slot(A(40), A(10))
    assert r.delta == (0, -30)


def test_equal_attacks_cancel():
    assert slot(A(30), A(30)).delta == (0, 0)


def test_attack_vs_defense():
    assert slot(A(30), D(10)).delta == (0, -20)
    assert slot(A(30), D(30)).delta == (0, 0)
    assert slot(A(10), D(50)).delta == (0, 0)  # block can't go negative
    assert slot(D(20), A(50)).delta == (-30, 0)


def test_attack_vs_heal_nets_together():
    assert slot(A(30), H(50), (100, 60)).delta == (0, 20)  # 60 +50 -30
    assert slot(A(50), H(30), (100, 100)).delta == (0, -20)


def test_heal_is_clamped_at_100():
    assert slot(H(50), F, (80, 100)).delta == (20, 0)
    assert slot(H(30), F, (100, 100)).aura == (100, 100)


def test_attack_vs_mirror_reflects_same_value():
    assert slot(A(40), M).delta == (-40, 0)
    assert slot(M, A(20)).delta == (0, -20)


def test_mirror_against_non_attack_does_nothing():
    for other in (D(30), M, F):
        assert slot(M, other).delta == (0, 0)
    # a heal opposite a mirror still heals
    assert slot(M, H(30), (100, 50)).delta == (0, 30)


def test_defense_against_non_attack_does_nothing():
    assert slot(D(50), D(50)).delta == (0, 0)
    assert slot(D(50), F).delta == (0, 0)


def test_heal_vs_heal_both_heal():
    assert slot(H(30), H(50), (50, 50)).delta == (30, 50)


def test_aura_cannot_go_below_zero():
    r = slot(A(50), F, (100, 20))
    assert r.aura == (100, 0) and r.delta == (0, -20)


def test_fizzle_does_nothing():
    assert slot(F, F).delta == (0, 0)
    assert slot(A(20), F).delta == (0, -20)


def test_higher_aura_wins_after_five_slots():
    seq0 = [A(10), F, F, F, F]
    seq1 = [F, F, F, F, F]
    r = resolve_match(seq0, seq1)
    assert r.aura == (100, 90) and r.winner == 0 and not r.knockout
    assert len(r.slots) == 5


def test_equal_aura_is_a_draw():
    r = resolve_match([F] * 5, [F] * 5)
    assert r.winner is None and not r.knockout


def test_knockout_stops_early():
    r = resolve_match([A(50), A(50), A(50), A(50), A(50)], [F] * 5)
    assert r.knockout and r.winner == 0
    assert len(r.slots) == 2 and r.aura == (100, 0)


def test_only_one_player_can_lose_aura_in_a_slot():
    """So both players reaching 0 in the same slot cannot happen with these rules."""
    cards = default_deck() + [FIZZLE]
    for x in cards:
        for y in cards:
            d = resolve_slot(1, x, y, (100, 100)).delta
            assert not (d[0] < 0 and d[1] < 0), (x, y, d)
            d = resolve_slot(1, x, y, (50, 50)).delta
            assert not (d[0] < 0 and d[1] < 0), (x, y, d)


def test_equal_aura_after_all_slots_is_a_draw():
    r = resolve_match([A(50), A(10), F, F, F], [A(10), A(50), F, F, F])
    assert r.aura == (60, 60) and r.winner is None


def test_mismatched_lengths_rejected():
    with pytest.raises(ValueError):
        resolve_match([F], [F, F])


def test_slot_results_report_cards_and_slot_numbers():
    r = resolve_match([A(10), A(20)], [D(10), D(10)])
    assert [s.slot for s in r.slots] == [1, 2]
    assert r.slots[0].cards == (A(10), D(10))
