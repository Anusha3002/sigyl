"""Slot-by-slot resolution of two locked-in sequences. Deterministic, no randomness."""
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

from .cards import MAX_AURA, START_AURA, Card, CardType


@dataclass(frozen=True)
class SlotResult:
    slot: int  # 1-based
    cards: Tuple[Card, Card]
    delta: Tuple[int, int]  # Aura change applied to each player (after clamping)
    aura: Tuple[int, int]  # Aura after the slot
    note: str = ""


@dataclass
class MatchResult:
    slots: List[SlotResult] = field(default_factory=list)
    winner: Optional[int] = None  # 0, 1, or None for a draw
    knockout: bool = False

    @property
    def aura(self) -> Tuple[int, int]:
        return self.slots[-1].aura if self.slots else (START_AURA, START_AURA)


def _raw_change(a: Card, b: Card) -> Tuple[int, int, str]:
    """Unclamped Aura change for (player0, player1) and a short note for one slot."""
    t0, t1 = a.type, b.type
    c0 = c1 = 0
    note = ""

    # attacks
    if t0 == CardType.ATTACK and t1 == CardType.ATTACK:
        if a.value > b.value:
            c1 -= a.value - b.value
            note = "attack beats weaker attack"
        elif b.value > a.value:
            c0 -= b.value - a.value
            note = "attack beats weaker attack"
        else:
            note = "equal attacks cancel"
    else:
        for me, (mt, mv), (ot, ov) in ((0, (t0, a.value), (t1, b.value)), (1, (t1, b.value), (t0, a.value))):
            if mt != CardType.ATTACK:
                continue
            dmg = mv
            if ot == CardType.DEFENSE:
                dmg = max(0, mv - ov)
                note = "defense blocks"
            elif ot == CardType.MIRROR:
                # reflected: the attacker takes it instead
                if me == 0:
                    c0 -= mv
                else:
                    c1 -= mv
                note = "mirror reflects"
                continue
            if me == 0:
                c1 -= dmg
            else:
                c0 -= dmg

    # heals (applied together with damage as a net change)
    if t0 == CardType.HEAL:
        c0 += a.value
        note = note or "heal"
    if t1 == CardType.HEAL:
        c1 += b.value
        note = note or "heal"
    return c0, c1, note


def resolve_slot(slot: int, a: Card, b: Card, aura: Tuple[int, int]) -> SlotResult:
    c0, c1, note = _raw_change(a, b)
    n0 = max(0, min(MAX_AURA, aura[0] + c0))
    n1 = max(0, min(MAX_AURA, aura[1] + c1))
    return SlotResult(slot, (a, b), (n0 - aura[0], n1 - aura[1]), (n0, n1), note)


def resolve_match(seq0: Sequence[Card], seq1: Sequence[Card]) -> MatchResult:
    if len(seq0) != len(seq1):
        raise ValueError("sequences must be the same length")
    result = MatchResult()
    aura = (START_AURA, START_AURA)
    for i, (a, b) in enumerate(zip(seq0, seq1), start=1):
        slot = resolve_slot(i, a, b, aura)
        result.slots.append(slot)
        aura = slot.aura
        if aura[0] == 0 or aura[1] == 0:
            result.knockout = True
            break
    if aura[0] == aura[1]:
        result.winner = None
    else:
        result.winner = 0 if aura[0] > aura[1] else 1
    return result
