"""Card definitions and the placeholder deck. Standard library only."""
from dataclasses import dataclass
from enum import Enum
from typing import List


class CardType(str, Enum):
    ATTACK = "attack"
    DEFENSE = "defense"
    HEAL = "heal"
    MIRROR = "mirror"
    VANISH = "vanish"
    CHARM = "charm"
    SURGE = "surge"
    FIZZLE = "fizzle"  # blank card locked in when a pick times out


# Special cards only appear in drafts from pick 3 on.
SPECIAL_TYPES = frozenset(
    {CardType.HEAL, CardType.MIRROR, CardType.VANISH, CardType.CHARM, CardType.SURGE}
)
# Types that carry no number.
NO_VALUE_TYPES = frozenset(
    {CardType.MIRROR, CardType.VANISH, CardType.CHARM, CardType.SURGE, CardType.FIZZLE}
)

MAX_VALUE = 50
START_AURA = 100
MAX_AURA = 100


@dataclass(frozen=True)
class Card:
    type: CardType
    value: int = 0
    title: str = ""  # the card's own name, e.g. "Slash"; also the name of its sigil


    def __post_init__(self):
        if self.type in NO_VALUE_TYPES:
            if self.value != 0:
                raise ValueError(f"{self.type.value} cards have no value")
        else:
            if self.value % 10 != 0 or not 10 <= self.value <= MAX_VALUE:
                raise ValueError(f"value must be a multiple of 10 between 10 and {MAX_VALUE}, got {self.value}")

    @property
    def is_special(self) -> bool:
        return self.type in SPECIAL_TYPES

    @property
    def name(self) -> str:
        if self.type in NO_VALUE_TYPES:
            return self.type.value.capitalize()
        return f"{self.type.value.capitalize()} {self.value}"

    @property
    def label(self) -> str:
        """What to show a player: the card's own name if it has one."""
        return self.title or self.name


FIZZLE = Card(CardType.FIZZLE)

# The deck: every card has its own name and its own sigil (see recognition/sigils.py).
CATALOG = [
    ("Slash", CardType.ATTACK, 30), ("Fang", CardType.ATTACK, 20), ("Bolt", CardType.ATTACK, 20),
    ("Rake", CardType.ATTACK, 40), ("Spear", CardType.ATTACK, 50), ("Scythe", CardType.ATTACK, 20),
    ("Crush", CardType.ATTACK, 10), ("Bite", CardType.ATTACK, 30), ("Talon", CardType.ATTACK, 10),
    ("Quake", CardType.ATTACK, 10),
    ("Wall", CardType.DEFENSE, 10), ("Shield", CardType.DEFENSE, 20), ("Ring", CardType.DEFENSE, 40),
    ("Cup", CardType.DEFENSE, 30), ("Buckler", CardType.DEFENSE, 50), ("Aegis", CardType.DEFENSE, 30),
    ("Gate", CardType.DEFENSE, 20),
    ("Mend", CardType.HEAL, 30), ("Bloom", CardType.HEAL, 50),
    ("Hourglass", CardType.MIRROR, 0), ("Bowtie", CardType.MIRROR, 0),
    ("Fade", CardType.VANISH, 0), ("Wisp", CardType.VANISH, 0),
    ("Rise", CardType.SURGE, 0), ("Spring", CardType.SURGE, 0),
    ("Heart", CardType.CHARM, 0),
]


def default_deck() -> List[Card]:
    """The 26-card deck. Edit CATALOG above to redesign it."""
    return [Card(t, v, title) for title, t, v in CATALOG]
