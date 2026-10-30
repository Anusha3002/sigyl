"""Card definitions and the placeholder deck. Standard library only."""
from dataclasses import dataclass
from enum import Enum
from typing import List


class CardType(str, Enum):
    ATTACK = "attack"
    DEFENSE = "defense"
    HEAL = "heal"
    MIRROR = "mirror"
    FIZZLE = "fizzle"  # blank card locked in when a pick times out


MAX_VALUE = 50
START_AURA = 100
MAX_AURA = 100


@dataclass(frozen=True)
class Card:
    type: CardType
    value: int = 0

    def __post_init__(self):
        if self.type in (CardType.MIRROR, CardType.FIZZLE):
            if self.value != 0:
                raise ValueError(f"{self.type.value} cards have no value")
        else:
            if self.value % 10 != 0 or not 10 <= self.value <= MAX_VALUE:
                raise ValueError(f"value must be a multiple of 10 between 10 and {MAX_VALUE}, got {self.value}")

    @property
    def name(self) -> str:
        if self.type in (CardType.MIRROR, CardType.FIZZLE):
            return self.type.value.capitalize()
        return f"{self.type.value.capitalize()} {self.value}"


FIZZLE = Card(CardType.FIZZLE)

_ATTACKS = [10, 10, 10, 20, 20, 20, 30, 30, 40, 50]
_DEFENSES = [10, 20, 20, 30, 30, 40, 50]
_HEALS = [30, 50]
_MIRRORS = 2


def default_deck() -> List[Card]:
    """Placeholder 21-card deck. Edit the lists above to redesign it."""
    deck = [Card(CardType.ATTACK, v) for v in _ATTACKS]
    deck += [Card(CardType.DEFENSE, v) for v in _DEFENSES]
    deck += [Card(CardType.HEAL, v) for v in _HEALS]
    deck += [Card(CardType.MIRROR) for _ in range(_MIRRORS)]
    return deck
