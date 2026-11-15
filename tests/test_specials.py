"""Vanish, Charm and Surge."""
import pytest

from game import FIZZLE, Card, CardType, resolve_match, resolve_slot

A = lambda v: Card(CardType.ATTACK, v)
D = lambda v: Card(CardType.DEFENSE, v)
H = lambda v: Card(CardType.HEAL, v)
M = Card(CardType.MIRROR)
V = Card(CardType.VANISH)
C = Card(CardType.CHARM)
S = Card(CardType.SURGE)
F = FIZZLE


def slot(a, b, aura=(100, 100), surge=(0, 0)):
    return resolve_slot(1, a, b, aura, surge)


# ---- Vanish ---------------------------------------------------------------
@pytest.mark.parametrize("other", [A(50), H(50), M, D(30), C, S, F, V])
def test_vanish_makes_the_whole_slot_do_nothing(other):
    assert slot(V, other, (60, 60)).delta == (0, 0)
    assert slot(other, V, (60, 60)).delta == (0, 0)


def test_vanish_cancels_an_incoming_surge_setup():
    r = slot(S, V)
    assert r.surge_next == (0, 0)


# ---- Charm ----------------------------------------------------------------
def test_charm_steals_20():
    r = slot(C, F, (70, 80))
    assert r.delta == (20, -20) and r.aura == (90, 60)


def test_charm_is_not_blocked_by_defense_or_reflected_by_mirror():
    assert slot(C, D(50), (70, 80)).delta == (20, -20)
    assert slot(C, M, (70, 80)).delta == (20, -20)


def test_charm_and_attack_both_happen():
    r = slot(C, A(30), (70, 80))
    assert r.delta == (20 - 30, -20)


def test_charm_vs_charm_nets_zero():
    assert slot(C, C, (70, 80)).delta == (0, 0)


def test_charm_cannot_push_aura_below_zero_or_above_the_cap():
    r = slot(C, F, (95, 10))
    assert r.aura == (100, 0)


def test_both_players_can_hit_zero_in_the_same_slot_with_charm_and_attack():
    r = resolve_slot(1, C, A(50), (10, 10))
    assert r.aura == (0, 0)


def test_both_players_at_zero_after_a_slot_is_a_drawn_knockout():
    # equal attacks bring both players down together until both hit zero
    r = resolve_match([A(30), A(30), F, F, F], [A(30), A(30), F, F, F])
    assert r.slots[0].aura == (30, 30)
    assert r.slots[1].aura == (0, 0)
    assert r.knockout and r.winner is None and len(r.slots) == 2


# ---- Surge ----------------------------------------------------------------
def test_surge_boosts_the_next_slot_attack_by_20():
    r = resolve_match([S, A(30)], [F, F])
    assert r.slots[0].surge_next == (20, 0)
    assert r.slots[1].delta == (0, -50)


def test_surge_is_wasted_if_the_next_card_is_not_an_attack():
    r = resolve_match([S, D(30), A(30)], [F, F, F])
    assert r.slots[2].delta == (0, -30)  # the bonus was used up on the defense slot


def test_surge_in_the_last_slot_does_nothing():
    r = resolve_match([F, F, F, F, S], [F] * 5)
    assert r.aura == (60, 60) and r.winner is None


def test_surged_attack_counts_in_attack_vs_attack():
    r = resolve_match([S, A(10)], [F, A(30)])
    # the boosted 10 + 20 = 30 lands on them, their 30 lands on you
    assert r.slots[1].delta == (-30, -30)


def test_surged_attack_against_defense_and_mirror():
    r = resolve_match([S, A(10)], [F, D(20)])
    assert r.slots[1].delta == (0, -20)  # 30 minus half of the 20 defense
    r = resolve_match([S, A(10)], [F, M])
    assert r.slots[1].delta == (-30, 0)  # the mirror returns the boosted 30


def test_vanished_attack_still_uses_up_the_surge():
    r = resolve_match([S, A(30), A(30)], [F, V, F])
    assert r.slots[1].delta == (0, 0)
    assert r.slots[2].delta == (0, -30)  # no leftover bonus


def test_surge_vs_surge_each_boosts_their_own_next_attack():
    r = resolve_match([S, A(10)], [S, A(20)])
    # both boosted attacks land: you take 40, they take 30
    assert r.slots[1].delta == (-40, -30)


def test_surge_then_attacks_can_knock_out():
    r = resolve_match([S, A(50), A(50)], [F] * 3)
    assert r.slots[1].delta == (0, -60)  # 70 damage, but they only had 60
    assert r.knockout and r.winner == 0 and len(r.slots) == 2
