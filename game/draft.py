"""Draft phase: each player picks 5 cards from a rolling offer of 3."""
import random
from typing import List, Optional

from .cards import FIZZLE, Card, default_deck

PICKS = 5
OFFER_SIZE = 3


class DraftError(Exception):
    pass


class Draft:
    """One player's draft. Their own shuffled deck; picked cards leave only this deck."""

    def __init__(self, seed: Optional[int] = None, deck: Optional[List[Card]] = None):
        rng = random.Random(seed)
        self._draw_pile = list(deck if deck is not None else default_deck())
        rng.shuffle(self._draw_pile)
        if len(self._draw_pile) < PICKS + OFFER_SIZE - 1:
            raise ValueError("deck too small to draft from")
        self.offer: List[Card] = [self._draw_pile.pop() for _ in range(OFFER_SIZE)]
        self.picks: List[Card] = []

    @property
    def done(self) -> bool:
        return len(self.picks) >= PICKS

    @property
    def turn(self) -> int:
        """Pick number being made, 1..5 (5 once finished)."""
        return min(len(self.picks) + 1, PICKS)

    def pick(self, index: int) -> Card:
        """Lock in offer[index]; the offer is refilled from the draw pile."""
        if self.done:
            raise DraftError("draft is finished")
        if not 0 <= index < len(self.offer):
            raise DraftError(f"offer index out of range: {index}")
        card = self.offer.pop(index)
        self.picks.append(card)
        if self._draw_pile:
            self.offer.append(self._draw_pile.pop())
        return card

    def fizzle(self) -> Card:
        """Timeout with nothing selected: a blank card takes the slot."""
        if self.done:
            raise DraftError("draft is finished")
        self.picks.append(FIZZLE)
        return FIZZLE

    def sequence(self) -> List[Card]:
        if not self.done:
            raise DraftError("draft is not finished")
        return list(self.picks)
