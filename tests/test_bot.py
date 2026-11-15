from game import Draft, resolve_match
from game.bot import HeuristicBot, RandomBot
from game.cards import CardType


def test_bots_complete_a_five_card_sequence():
    for bot in (RandomBot(1), HeuristicBot(1)):
        seq = bot.play_draft(Draft(5))
        assert len(seq) == 5


def test_bots_are_reproducible_with_a_seed():
    a = HeuristicBot(3).play_draft(Draft(9))
    b = HeuristicBot(3).play_draft(Draft(9))
    assert a == b


def test_fizzle_prob_one_gives_all_blanks():
    seq = RandomBot(1, fizzle_prob=1.0).play_draft(Draft(1))
    assert all(c.type == CardType.FIZZLE for c in seq)


def test_heuristic_limits_defensive_picks():
    for seed in range(200):
        seq = HeuristicBot(seed, noise=0).play_draft(Draft(seed))
        assert sum(1 for c in seq if c.type == CardType.DEFENSE) <= 4


def test_full_game_always_has_a_valid_result():
    for seed in range(300):
        r = resolve_match(HeuristicBot(seed).play_draft(Draft(seed)),
                          RandomBot(seed).play_draft(Draft(seed + 1000)))
        assert r.winner in (0, 1, None)
        assert 0 <= r.aura[0] <= 100 and 0 <= r.aura[1] <= 100
