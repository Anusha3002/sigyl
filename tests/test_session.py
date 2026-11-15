"""The match flow against the bot, with made-up clock times."""
from game.cards import CardType
from game.session import DRAFT, RESULT, REVEAL, WAITING, MatchSession


def play_draft(s, now=0.0):
    s.start(now)
    for _ in range(5):
        s.select(0)
        now += 3
        assert s.lock(now)
    return now


def test_starts_waiting_and_ignores_everything_until_started():
    s = MatchSession(seed=1)
    assert s.phase == WAITING and s.offer == []
    assert not s.select(0) and not s.lock(0.0)
    s.tick(100.0)
    assert s.phase == WAITING


def test_start_gives_three_cards_and_a_25_second_timer():
    s = MatchSession(seed=1)
    assert s.start(10.0)
    assert s.phase == DRAFT and len(s.offer) == 3 and s.turn == 1
    assert s.time_left(10.0) == 25.0 and s.time_left(25.0) == 10.0
    assert all(c.title for c in s.offer)


def test_selection_sticks_until_another_sigil_is_drawn():
    s = MatchSession(seed=1)
    s.start(0.0)
    s.select(2)
    s.tick(5.0)
    assert s.selected == 2
    s.select(0)
    assert s.selected == 0
    chosen = s.offer[0]
    s.lock(6.0)
    assert s.picks == [chosen] and s.selected is None and s.turn == 2


def test_fist_with_nothing_selected_does_nothing():
    s = MatchSession(seed=1)
    s.start(0.0)
    assert not s.lock(1.0)
    assert s.picks == [] and s.turn == 1


def test_timer_takes_the_highlighted_card():
    s = MatchSession(seed=1)
    s.start(0.0)
    s.select(1)
    chosen = s.offer[1]
    s.tick(24.9)
    assert s.picks == []
    s.tick(25.0)
    assert s.picks == [chosen] and s.time_left(25.0) == 25.0


def test_timer_with_nothing_selected_gives_a_fizzle():
    s = MatchSession(seed=1)
    s.start(0.0)
    s.tick(31.0)
    assert [c.type for c in s.picks] == [CardType.FIZZLE]


def test_five_picks_then_reveal_slot_by_slot_then_result():
    s = MatchSession(seed=4, reveal_seconds=2.0)
    now = play_draft(s)
    assert s.phase == REVEAL and len(s.picks) == 5 and s.shown_slots == []
    assert s.aura == (60, 60)
    n = len(s.result.slots)
    for i in range(1, n + 1):
        now += 2.0
        s.tick(now)
        assert len(s.shown_slots) == i and s.aura == s.result.slots[i - 1].aura
    assert s.phase == REVEAL
    s.tick(now + 2.0)
    assert s.phase == RESULT and s.winner == s.result.winner


def test_bot_picks_are_real_cards_and_your_picks_are_your_slots():
    s = MatchSession(seed=4)
    play_draft(s)
    assert [slot.cards[0] for slot in s.result.slots] == s.picks[:len(s.result.slots)]
    assert all(slot.cards[1].type != CardType.FIZZLE for slot in s.result.slots)


def test_no_actions_during_reveal_and_new_match_after_result():
    s = MatchSession(seed=4, reveal_seconds=0.1)
    now = play_draft(s)
    assert not s.start(now) and not s.select(0)
    for _ in range(10):
        now += 1
        s.tick(now)
    assert s.phase == RESULT
    assert s.start(now)
    assert s.phase == DRAFT and s.picks == [] and s.turn == 1 and s.aura == (60, 60)


def test_same_seed_same_match():
    a, b = MatchSession(seed=9), MatchSession(seed=9)
    play_draft(a), play_draft(b)
    assert a.picks == b.picks and a.result.aura == b.result.aura
