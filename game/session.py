"""One match against the bot, as a small state machine. Standard library only: no camera.

Phases:  waiting --start--> draft (5 picks) --> reveal (slot by slot) --> result --start--> draft ...

The screen calls:
  start(now)        the zoom gesture
  select(index)     a recognized sigil: highlight offer[index] (drawing another one changes it)
  lock(now)         the fist: commit the highlighted card (ignored when nothing is highlighted)
  tick(now)         every frame: handles the pick timer and the reveal pacing
`now` is a time in seconds from any clock, so tests can pass made-up times.
"""
from typing import List, Optional

from .bot import HeuristicBot
from .cards import FIZZLE, START_AURA, Card
from .draft import PICKS, Draft
from .match import MatchResult, SlotResult, resolve_match

WAITING, DRAFT, REVEAL, RESULT = "waiting", "draft", "reveal", "result"


class MatchSession:
    def __init__(self, seed: Optional[int] = None, pick_seconds: float = 30.0, reveal_seconds: float = 2.5):
        self.pick_seconds = pick_seconds
        self.reveal_seconds = reveal_seconds
        self._seed = seed
        self._games = 0
        self.phase = WAITING
        self.selected: Optional[int] = None
        self.picks: List[Card] = []
        self.result: Optional[MatchResult] = None
        self.revealed = 0          # how many slots of the result are shown so far
        self._draft: Optional[Draft] = None
        self._bot_draft: Optional[Draft] = None
        self._bot = None
        self._deadline = 0.0
        self._next_reveal = 0.0

    # ---- what the screen shows --------------------------------------------
    @property
    def offer(self) -> List[Card]:
        return list(self._draft.offer) if self._draft and self.phase == DRAFT else []

    @property
    def turn(self) -> int:
        return len(self.picks) + 1 if self.phase == DRAFT else len(self.picks)

    def time_left(self, now: float) -> float:
        return max(0.0, self._deadline - now) if self.phase == DRAFT else 0.0

    @property
    def shown_slots(self) -> List[SlotResult]:
        return self.result.slots[:self.revealed] if self.result else []

    @property
    def aura(self):
        shown = self.shown_slots
        return shown[-1].aura if shown else (START_AURA, START_AURA)

    @property
    def winner(self) -> Optional[int]:
        """0 = you, 1 = bot, None = draw. Only meaningful in the result phase."""
        return self.result.winner if self.result and self.phase == RESULT else None

    # ---- actions ----------------------------------------------------------
    def start(self, now: float) -> bool:
        if self.phase not in (WAITING, RESULT):
            return False
        seed = None if self._seed is None else self._seed + 2 * self._games
        self._games += 1
        self._draft = Draft(seed)
        self._bot_draft = Draft(None if seed is None else seed + 1)
        self._bot = HeuristicBot(None if seed is None else seed + 1)
        self.picks, self.result, self.revealed, self.selected = [], None, 0, None
        self.phase = DRAFT
        self._deadline = now + self.pick_seconds
        return True

    def select(self, index: int) -> bool:
        if self.phase != DRAFT or not 0 <= index < len(self._draft.offer):
            return False
        self.selected = index
        return True

    def lock(self, now: float) -> bool:
        if self.phase != DRAFT or self.selected is None:
            return False
        self._commit(now)
        return True

    def tick(self, now: float) -> None:
        if self.phase == DRAFT and now >= self._deadline:
            self._commit(now)  # takes the highlighted card, or a Fizzle if none
        elif self.phase == REVEAL and now >= self._next_reveal:
            if self.revealed < len(self.result.slots):
                self.revealed += 1
                self._next_reveal = now + self.reveal_seconds
            else:
                self.phase = RESULT

    # ---- internals --------------------------------------------------------
    def _commit(self, now: float) -> None:
        card = self._draft.pick(self.selected) if self.selected is not None else self._draft.fizzle()
        self.picks.append(card)
        idx = self._bot.pick_index(self._bot_draft)
        self._bot_draft.fizzle() if idx is None else self._bot_draft.pick(idx)
        self.selected = None
        if len(self.picks) >= PICKS:
            self.result = resolve_match(self._draft.sequence(), self._bot_draft.sequence())
            self.phase = REVEAL
            self.revealed = 0
            self._next_reveal = now + 1.0
        else:
            self._deadline = now + self.pick_seconds
