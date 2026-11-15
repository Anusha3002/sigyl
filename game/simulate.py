"""Bot-vs-bot sanity check of the rules: python -m game.simulate"""
from collections import Counter

from .bot import HeuristicBot, RandomBot
from .draft import Draft
from .match import resolve_match


def play(bot0, bot1, seed0: int, seed1: int):
    s0 = bot0.play_draft(Draft(seed0))
    s1 = bot1.play_draft(Draft(seed1))
    return resolve_match(s0, s1)


def run(n: int, make0, make1):
    wins, kos, aura_gap = Counter(), 0, 0
    for i in range(n):
        r = play(make0(i), make1(i), seed0=i, seed1=100_000 + i)
        wins[r.winner] += 1
        kos += r.knockout
        aura_gap += abs(r.aura[0] - r.aura[1])
    return wins, kos / n, aura_gap / n


if __name__ == "__main__":
    n = 5000
    cases = {
        "Random vs Random": (lambda s: RandomBot(s), lambda s: RandomBot(10_000 + s)),
        "Heuristic vs Heuristic": (lambda s: HeuristicBot(s), lambda s: HeuristicBot(10_000 + s)),
        "Heuristic(P0) vs Random(P1)": (lambda s: HeuristicBot(s), lambda s: RandomBot(10_000 + s)),
    }
    for name, (m0, m1) in cases.items():
        w, ko, gap = run(n, m0, m1)
        print(f"{name:<30} P0 {w[0]/n:5.1%}  P1 {w[1]/n:5.1%}  draw {w[None]/n:5.1%}  knockout {ko:5.1%}  avg aura gap {gap:5.1f}")
