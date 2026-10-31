"""Leave-one-out accuracy and confusion matrix for recorded shapes.

  python -m recognition.evaluate shapes.jsonl            your recordings only
  python -m recognition.evaluate shapes.jsonl --defaults also show the built-in templates on your shapes

Each shape is recognized using all the OTHER recordings as templates, so a shape is never
matched against itself.
"""
import argparse
from collections import Counter, defaultdict

from .dollar1 import Recognizer, load_shapes, recognizer_from_shapes


def evaluate(shapes, min_score=0.75):
    confusion = defaultdict(Counter)
    for i, (label, pts) in enumerate(shapes):
        others = shapes[:i] + shapes[i + 1:]
        if not any(l == label for l, _ in others):
            continue
        res = recognizer_from_shapes(others, min_score).classify(pts)
        confusion[label][res.label or "(rejected)"] += 1
    total = sum(sum(c.values()) for c in confusion.values())
    correct = sum(c[l] for l, c in confusion.items())
    return correct, total, confusion


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--defaults", action="store_true", help="also test the built-in templates")
    args = ap.parse_args()
    shapes = load_shapes(args.file)
    print(f"{len(shapes)} recorded shapes: {dict(Counter(l for l, _ in shapes))}")
    correct, total, conf = evaluate(shapes)
    print(f"\nLeave-one-out (recordings only): {correct}/{total} = {correct / max(total, 1):.0%}")
    cols = sorted({c for row in conf.values() for c in row} | set(conf))
    print("true \\ guessed  " + "  ".join(f"{c:>10}" for c in cols))
    for l in sorted(conf):
        print(f"{l:<15} " + "  ".join(f"{conf[l][c]:>10}" for c in cols))
    if args.defaults:
        rec = Recognizer()
        ok = sum(1 for l, p in shapes if rec.classify(p).label == l)
        print(f"\nBuilt-in templates on your shapes: {ok}/{len(shapes)} = {ok / max(len(shapes), 1):.0%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
