"""Draft phase: each player picks 5 cards from a rolling offer of 3.

Picks 1 and 2 only offer attack and defense cards. After the second selection the
whole offer is redrawn from the full pile (offered-but-unpicked cards go back in), so
special cards can show up from pick 3. Picked cards never return.
"""
import random
from typing import List, Optional

from .cards import FIZZLE, Card, default_deck

PICKS = 5
OFFER_SIZE = 3
SPECIAL_FROM_PICK = 3


class DraftError(Exception):
    pass


class Draft:
    """One player's draft. Their own shuffled deck; picked cards leave only this deck."""

    def __init__(self, seed: Optional[int] = None, deck: Optional[List[Card]] = None):
        self._rng = random.Random(seed)
        pile = list(deck if deck is not None else default_deck())
        if len(pile) < PICKS + OFFER_SIZE - 1:
            raise ValueError("deck too small to draft from")
        if sum(1 for c in pile if not c.is_special) < OFFER_SIZE + 1:
            raise ValueError("need at least 4 attack or defense cards for the first two picks")
        self._rng.shuffle(pile)
        self._pile: List[Card] = pile
        self.offer: List[Card] = [self._draw(allow_special=False) for _ in range(OFFER_SIZE)]
        self.picks: List[Card] = []

    # ---- queries -------------------------------------------------------
    @property
    def done(self) -> bool:
        return len(self.picks) >= PICKS

    @property
    def turn(self) -> int:
        """Pick number being made, 1..5 (5 once finished)."""
        return min(len(self.picks) + 1, PICKS)

    def remaining(self) -> List[Card]:
        """Every card not yet picked (offer plus draw pile)."""
        return list(self.offer) + list(self._pile)

    # ---- actions -------------------------------------------------------
    def pick(self, index: int) -> Card:
        """Lock in offer[index]."""
        self._check_open()
        if not 0 <= index < len(self.offer):
            raise DraftError(f"offer index out of range: {index}")
        card = self.offer.pop(index)
        self.picks.append(card)
        self._after_selection(took_card=True)
        return card

    def fizzle(self) -> Card:
        """Timeout with nothing selected: a blank card takes the slot."""
        self._check_open()
        self.picks.append(FIZZLE)
        self._after_selection(took_card=False)
        return FIZZLE

    def sequence(self) -> List[Card]:
        if not self.done:
            raise DraftError("draft is not finished")
        return list(self.picks)

    # ---- internals -----------------------------------------------------
    def _check_open(self) -> None:
        if self.done:
            raise DraftError("draft is finished")

    def _draw(self, allow_special: bool) -> Card:
        for i in range(len(self._pile) - 1, -1, -1):
            if allow_special or not self._pile[i].is_special:
                return self._pile.pop(i)
        raise DraftError("no card left to draw")

    def _after_selection(self, took_card: bool) -> None:
        made = len(self.picks)
        if made == SPECIAL_FROM_PICK - 1:
            # redraw the whole offer from the full pile
            self._pile.extend(self.offer)
            self.offer = []
            self._rng.shuffle(self._pile)
            while len(self.offer) < OFFER_SIZE and self._pile:
                self.offer.append(self._draw(allow_special=True))
        elif took_card and self._pile and not self.done:
            self.offer.append(self._draw(allow_special=made + 1 >= SPECIAL_FROM_PICK))
