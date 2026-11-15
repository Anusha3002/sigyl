"""How well are recorded sigil drawings recognized?

  python -m recognition.evaluate_sigils data/sigils.jsonl

Reports two setups:
  built-in    only the shapes traced from the card designs
  learned     built-in shapes plus your other recordings (leave-one-out: a drawing is never
              matched against itself)
and for each, two questions:
  among all 26     the hard, artificial case
  among 3 on offer the game's real question, averaged over every possible pair of other cards
"""
import argparse
from collections import Counter, defaultdict
from itertools import combinations
from typing import Dict, List, Sequence, Tuple

from .dollar1 import load_shapes
from .sigils import SIGILS, SigilRecognizer

Point = Tuple[float, float]


def decide(scores: Dict[str, float], names: Sequence[str], min_score: float, min_margin: float):
    """Same rule as SigilRecognizer.classify, on scores already computed."""
    ranked = sorted(names, key=lambda n: -scores[n])
    top = ranked[0]
    margin = scores[top] - scores[ranked[1]] if len(ranked) > 1 else 1.0
    return top if scores[top] >= min_score and margin >= min_margin else None


def score_all(shapes: List[Tuple[str, List[Point]]], learned: bool) -> List[Tuple[str, Dict[str, float]]]:
    """For every drawing: its score against each of the 26 sigils."""
    out = []
    base = SigilRecognizer()
    for i, (label, pts) in enumerate(shapes):
        rec = base
        if learned:
            rec = SigilRecognizer()
            for j, (l, p) in enumerate(shapes):
                if j != i:
                    rec.add_template(l, p)
        out.append((label, {n: rec.score(pts, n) for n in rec.names()}))
    return out


def summarize(scored, min_score: float, min_margin: float):
    names = list(SIGILS)
    all26 = Counter()
    confusion = defaultdict(Counter)
    offer_right = offer_wrong = offer_total = 0
    per_sigil = defaultdict(lambda: [0, 0])
    for label, scores in scored:
        guess = decide(scores, names, min_score, min_margin)
        all26["right" if guess == label else ("rejected" if guess is None else "wrong")] += 1
        if guess != label:
            confusion[label][guess or "(not recognized)"] += 1
        others = [n for n in names if n != label]
        for a, b in combinations(others, 2):
            g = decide(scores, (label, a, b), min_score, min_margin)
            offer_total += 1
            offer_right += g == label
            offer_wrong += g is not None and g != label
            per_sigil[label][0] += g == label
            per_sigil[label][1] += 1
    return all26, confusion, (offer_right, offer_wrong, offer_total), per_sigil


def report(title: str, scored, min_score: float, min_margin: float) -> None:
    all26, confusion, (right, wrong, total), per_sigil = summarize(scored, min_score, min_margin)
    n = sum(all26.values())
    print(f"\n== {title} ==")
    print(f"among all 26:      right {all26['right']}/{n} = {all26['right'] / n:.0%}   wrong {all26['wrong']}   not recognized {all26['rejected']}")
    print(f"among 3 on offer:  right {right / total:.1%}   wrong card {wrong / total:.1%}   not recognized {(total - right - wrong) / total:.1%}")
    worst = sorted(per_sigil.items(), key=lambda kv: kv[1][0] / kv[1][1])[:6]
    print("weakest sigils (among 3 on offer): " + ", ".join(f"{k} {v[0] / v[1]:.0%}" for k, v in worst))
    pairs = sorted(((c, a, b) for a, row in confusion.items() for b, c in row.items()), reverse=True)[:10]
    if pairs:
        print("most common mistakes among all 26:")
        for c, a, b in pairs:
            print(f"   {a} read as {b}: {c}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    args = ap.parse_args()
    shapes = [(l, p) for l, p in load_shapes(args.file) if l in SIGILS]
    counts = Counter(l for l, _ in shapes)
    print(f"{len(shapes)} drawings of {len(counts)} sigils (fewest: {min(counts.values())}, most: {max(counts.values())})")
    missing = [n for n in SIGILS if n not in counts]
    if missing:
        print("no drawings yet for: " + ", ".join(missing))
    rec = SigilRecognizer()
    report("built-in shapes only", score_all(shapes, learned=False), rec.min_score, rec.min_margin)
    if any(c > 1 for c in counts.values()):
        print("\n(working out the learned setup, this takes a little while...)")
        report("built-in + your other recordings (leave-one-out)", score_all(shapes, learned=True), rec.min_score, rec.min_margin)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
