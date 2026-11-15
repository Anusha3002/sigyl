"""The 26 card sigils: every card has one, and wobbly drawings of each are told apart."""
import math
import random

import pytest

from game.cards import CATALOG
from recognition.sigils import SIGILS, SigilRecognizer, looks_closed

REC = SigilRecognizer()


def wobbly(points, seed, amp=0.03, tilt_deg=6, scale=1.0, shift=(0.0, 0.0)):
    """A hand-drawn-ish copy: dense points, smooth wobble, slight tilt, any size and position."""
    from recognition.dollar1 import resample
    rnd = random.Random(seed)
    pts = resample(points, 80)
    size = max(max(p[0] for p in pts) - min(p[0] for p in pts), max(p[1] for p in pts) - min(p[1] for p in pts))
    ph = [rnd.uniform(0, 6.28) for _ in range(4)]
    a = math.radians(rnd.uniform(-tilt_deg, tilt_deg))
    out = []
    for i, (x, y) in enumerate(pts):
        t = i / 79
        x += amp * size * (math.sin(2 * math.pi * t + ph[0]) + 0.5 * math.sin(4 * math.pi * t + ph[1]))
        y += amp * size * (math.sin(2 * math.pi * t + ph[2]) + 0.5 * math.sin(4 * math.pi * t + ph[3]))
        out.append(((x * math.cos(a) - y * math.sin(a)) * scale + shift[0], (x * math.sin(a) + y * math.cos(a)) * scale + shift[1]))
    return out


def test_every_card_has_a_sigil_and_every_sigil_a_card():
    assert sorted(SIGILS) == sorted(title for title, _, _ in CATALOG)
    assert len(SIGILS) == 26


@pytest.mark.parametrize("name", sorted(SIGILS))
def test_clean_sigil_is_recognized_among_all_26(name):
    res = REC.classify(SIGILS[name][0])
    assert res.label == name and res.score > 0.95


@pytest.mark.parametrize("name", sorted(SIGILS))
def test_direction_does_not_matter(name):
    assert REC.classify(SIGILS[name][0][::-1]).label == name


@pytest.mark.parametrize("name", [n for n, (_, closed) in SIGILS.items() if closed])
def test_closed_sigils_can_start_anywhere(name):
    pts = SIGILS[name][0][:-1]
    k = len(pts) // 3
    turned = pts[k:] + pts[:k]
    assert REC.classify(turned + [turned[0]]).label == name


def test_size_and_position_do_not_matter():
    small = wobbly(SIGILS["Rake"][0], seed=1, amp=0.0, tilt_deg=0, scale=0.001, shift=(0.4, 0.6))
    assert REC.classify(small).label == "Rake"


def test_upright_shape_matters():
    upside_down = [(x, -y) for x, y in SIGILS["Wall"][0]]
    assert REC.classify(upside_down, ["Wall", "Cup"]).best_label == "Cup"
    sideways = [(y, x) for x, y in SIGILS["Hourglass"][0]]
    assert REC.classify(sideways, ["Hourglass", "Bowtie"]).best_label == "Bowtie"


def test_wobbly_drawings_among_three_offered_cards():
    """The game's real question: which of the 3 cards on offer? Random offers, wobbly drawings."""
    rnd = random.Random(7)
    names = sorted(SIGILS)
    right = total = 0
    for trial in range(150):
        offer = rnd.sample(names, 3)
        target = offer[0]
        res = REC.classify(wobbly(SIGILS[target][0], seed=trial), offer)
        total += 1
        right += res.label == target
    assert right / total >= 0.95


def test_scribble_is_rejected():
    rnd = random.Random(3)
    scribble = [(rnd.random(), rnd.random()) for _ in range(40)]
    assert REC.classify(scribble, ["Slash", "Ring", "Fang"]).label is None


def test_candidates_limit_the_answer():
    res = REC.classify(SIGILS["Ring"][0], ["Slash", "Fang", "Bolt"])
    assert res.best_label in ("Slash", "Fang", "Bolt") and res.label is None


def test_learning_from_a_real_drawing():
    rec = SigilRecognizer()
    odd = [(0, 0), (1, 0), (1, 1), (2, 1), (2, 0), (3, 0)]
    before = rec.score(odd, "Quake")
    rec.add_template("Quake", odd)
    assert rec.score(odd, "Quake") > 0.99 > before


def test_looks_closed():
    assert looks_closed(SIGILS["Ring"][0]) and not looks_closed(SIGILS["Slash"][0])


def test_evaluation_on_made_up_recordings(tmp_path, capsys):
    from recognition.dollar1 import save_shape
    from recognition.evaluate_sigils import main, score_all, summarize
    path = str(tmp_path / "sig.jsonl")
    for name in ("Slash", "Ring", "Rake", "Wall", "Cup"):
        for k in range(2):
            save_shape(path, name, wobbly(SIGILS[name][0], seed=k + 10))
    from recognition.dollar1 import load_shapes
    shapes = load_shapes(path)
    all26, confusion, (right, wrong, total), _ = summarize(score_all(shapes, learned=False), 0.72, 0.02)
    assert sum(all26.values()) == 10 and all26["right"] >= 9
    assert total == 10 * 300 and right / total > 0.95      # 300 = pairs of other cards
    import sys
    sys.argv = ["evaluate_sigils", path]
    assert main() == 0
    out = capsys.readouterr().out
    assert "among 3 on offer" in out and "leave-one-out" in out
