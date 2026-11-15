"""Slot-by-slot resolution of two locked-in sequences. Deterministic, no randomness."""
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

from .cards import FIZZLE, MAX_AURA, START_AURA, Card, CardType

SURGE_BONUS = 20  # added to the attack in the slot after a Surge
DEFENSE_BLOCK = 0.5  # a defense card blocks this share of its value (Buckler 50 blocks 25)
CHARM_STEAL = 20  # Aura moved from the opponent to the Charm player


@dataclass(frozen=True)
class SlotResult:
    slot: int  # 1-based
    cards: Tuple[Card, Card]
    delta: Tuple[int, int]  # Aura change applied to each player (after clamping)
    aura: Tuple[int, int]  # Aura after the slot
    note: str = ""
    surge_next: Tuple[int, int] = (0, 0)  # Surge bonus carried into the next slot


@dataclass
class MatchResult:
    slots: List[SlotResult] = field(default_factory=list)
    winner: Optional[int] = None  # 0, 1, or None for a draw
    knockout: bool = False

    @property
    def aura(self) -> Tuple[int, int]:
        return self.slots[-1].aura if self.slots else (START_AURA, START_AURA)


def resolve_slot(
    slot: int,
    a: Card,
    b: Card,
    aura: Tuple[int, int],
    surge: Tuple[int, int] = (0, 0),
) -> SlotResult:
    """Resolve one slot. `surge` is the bonus each player carries in from a Surge last slot."""
    notes: List[str] = []

    # Vanish: if either player plays it, both cards do nothing this slot.
    if a.type == CardType.VANISH or b.type == CardType.VANISH:
        ea = eb = FIZZLE
        notes.append("vanish cancels the slot")
    else:
        ea, eb = a, b

    ta, tb = ea.type, eb.type
    # a pending Surge boosts an attack in this slot and is used up either way
    va = ea.value + (surge[0] if ta == CardType.ATTACK else 0)
    vb = eb.value + (surge[1] if tb == CardType.ATTACK else 0)
    if (ta == CardType.ATTACK and surge[0]) or (tb == CardType.ATTACK and surge[1]):
        notes.append("surge boost")

    c0 = c1 = 0

    # attacks
    if ta == CardType.ATTACK and tb == CardType.ATTACK:
        # two attacks do not cancel: both land in full
        c1 -= va
        c0 -= vb
        notes.append("both attacks land")
    else:
        if ta == CardType.ATTACK:
            if tb == CardType.MIRROR:
                c0 -= va  # reflected back at the attacker
                notes.append("mirror reflects")
            elif tb == CardType.DEFENSE:
                c1 -= max(0, va - int(vb * DEFENSE_BLOCK))
            else:
                c1 -= va
        if tb == CardType.ATTACK:
            if ta == CardType.MIRROR:
                c1 -= vb
                notes.append("mirror reflects")
            elif ta == CardType.DEFENSE:
                c0 -= max(0, vb - int(va * DEFENSE_BLOCK))
            else:
                c0 -= vb

    # heals
    if ta == CardType.HEAL:
        c0 += va
    if tb == CardType.HEAL:
        c1 += vb

    # charm: steals Aura; not blocked by defense and not reflected by mirror
    if ta == CardType.CHARM:
        c0 += CHARM_STEAL
        c1 -= CHARM_STEAL
    if tb == CardType.CHARM:
        c1 += CHARM_STEAL
        c0 -= CHARM_STEAL

    n0 = max(0, min(MAX_AURA, aura[0] + c0))
    n1 = max(0, min(MAX_AURA, aura[1] + c1))
    next_surge = (
        SURGE_BONUS if ta == CardType.SURGE else 0,
        SURGE_BONUS if tb == CardType.SURGE else 0,
    )
    return SlotResult(slot, (a, b), (n0 - aura[0], n1 - aura[1]), (n0, n1), "; ".join(notes), next_surge)


def resolve_match(seq0: Sequence[Card], seq1: Sequence[Card]) -> MatchResult:
    if len(seq0) != len(seq1):
        raise ValueError("sequences must be the same length")
    result = MatchResult()
    aura = (START_AURA, START_AURA)
    surge = (0, 0)
    for i, (a, b) in enumerate(zip(seq0, seq1), start=1):
        slot = resolve_slot(i, a, b, aura, surge)
        result.slots.append(slot)
        aura, surge = slot.aura, slot.surge_next
        if aura[0] == 0 or aura[1] == 0:
            result.knockout = True
            break
    if aura[0] == aura[1]:
        result.winner = None
    else:
        result.winner = 0 if aura[0] > aura[1] else 1
    return result
