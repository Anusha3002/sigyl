"""Draft bots. Seeded RNG so games are reproducible."""
import random
from typing import List, Optional

from .cards import Card, CardType
from .draft import Draft


class RandomBot:
    def __init__(self, seed: Optional[int] = None, fizzle_prob: float = 0.0):
        self.rng = random.Random(seed)
        self.fizzle_prob = fizzle_prob

    def pick_index(self, draft: Draft) -> Optional[int]:
        """Index into draft.offer, or None to fizzle."""
        if self.rng.random() < self.fizzle_prob:
            return None
        return self.rng.randrange(len(draft.offer))

    def play_draft(self, draft: Draft) -> List[Card]:
        while not draft.done:
            idx = self.pick_index(draft)
            draft.fizzle() if idx is None else draft.pick(idx)
        return draft.sequence()


class HeuristicBot(RandomBot):
    """Prefers strong cards, limits how many defense/heal/mirror cards it takes."""

    CAPS = {
        CardType.DEFENSE: 2, CardType.HEAL: 1, CardType.MIRROR: 1,
        CardType.VANISH: 1, CardType.CHARM: 1, CardType.SURGE: 1,
    }
    WEIGHT = {CardType.ATTACK: 1.0, CardType.DEFENSE: 0.7, CardType.HEAL: 0.8}
    FLAT_SCORE = {
        CardType.MIRROR: 35, CardType.VANISH: 30, CardType.CHARM: 40, CardType.SURGE: 25,
    }

    def __init__(self, seed: Optional[int] = None, fizzle_prob: float = 0.0, noise: float = 8.0):
        super().__init__(seed, fizzle_prob)
        self.noise = noise

    def _score(self, card: Card, picks: List[Card]) -> float:
        if card.type in self.FLAT_SCORE:
            base = self.FLAT_SCORE[card.type]
        else:
            base = card.value * self.WEIGHT[card.type]
        cap = self.CAPS.get(card.type)
        if cap is not None and sum(1 for p in picks if p.type == card.type) >= cap:
            base *= 0.3
        return base + self.rng.uniform(-self.noise, self.noise)

    def pick_index(self, draft: Draft) -> Optional[int]:
        if self.rng.random() < self.fizzle_prob:
            return None
        scores = [self._score(c, draft.picks) for c in draft.offer]
        return max(range(len(scores)), key=scores.__getitem__)
