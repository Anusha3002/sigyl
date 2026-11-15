"""Recognizer tests with made-up strokes (hand-drawn wobble added with a seeded random)."""
import math
import random

import pytest

from recognition.dollar1 import Recognizer, load_shapes, normalize, path_length, recognizer_from_shapes, resample, save_shape


def circle(r=1.0, start=0.0, direction=1, closed=0.97, n=50, noise=0.0, seed=0, cx=0.0, cy=0.0):
    rnd = random.Random(seed)
    return [(cx + r * math.cos(start + direction * 2 * math.pi * closed * i / n) + rnd.gauss(0, noise),
             cy + r * math.sin(start + direction * 2 * math.pi * closed * i / n) + rnd.gauss(0, noise)) for i in range(n + 1)]


def line(length=1.0, angle=0.0, n=30, noise=0.0, seed=0):
    rnd = random.Random(seed)
    return [(length * i / n * math.cos(angle) + rnd.gauss(0, noise), length * i / n * math.sin(angle) + rnd.gauss(0, noise)) for i in range(n + 1)]


def vee(size=1.0, spread=0.6, n=15, noise=0.0, seed=0):
    rnd = random.Random(seed)
    left = [(-spread * size * (1 - i / n), -size * (1 - i / n)) for i in range(n + 1)]
    right = [(spread * size * i / n, -size * i / n) for i in range(1, n + 1)]
    return [(x + rnd.gauss(0, noise), y + rnd.gauss(0, noise)) for x, y in left + right]


def rot(pts, a):
    c, s = math.cos(a), math.sin(a)
    return [(x * c - y * s, x * s + y * c) for x, y in pts]


def label(pts):
    return Recognizer().classify(pts).label


def test_resample_gives_even_points():
    pts = resample([(0, 0), (10, 0)], 11)
    assert len(pts) == 11 and pts[5][0] == pytest.approx(5.0) and pts[-1][0] == pytest.approx(10.0)


def test_resample_keeps_path_length_roughly():
    c = circle(noise=0.0)
    assert path_length(resample(c)) == pytest.approx(path_length(c), rel=0.02)


def test_normalize_ignores_size_and_position():
    a = normalize(circle(r=0.05, cx=0.3, cy=0.7))
    b = normalize(circle(r=3.0, cx=-9, cy=4))
    assert max(math.dist(p, q) for p, q in zip(a, b)) < 1e-6


@pytest.mark.parametrize("start", [0.0, 1.0, 2.5, 4.0])
@pytest.mark.parametrize("direction", [1, -1])
def test_circle_any_start_any_direction(start, direction):
    assert label(circle(start=start, direction=direction, noise=0.03, seed=1)) == "circle"


@pytest.mark.parametrize("angle", [0.0, 0.7, 1.57, 2.4, 3.14, -1.0])
def test_line_any_direction(angle):
    assert label(line(angle=angle, noise=0.01, seed=2)) == "line"


@pytest.mark.parametrize("angle", [0.0, 0.8, 1.6, 3.14, 4.5])
def test_v_any_rotation(angle):
    assert label(rot(vee(noise=0.02, seed=3), angle)) == "v"


def test_v_drawn_backwards():
    assert label(vee(noise=0.02, seed=4)[::-1]) == "v"


@pytest.mark.parametrize("spread", [0.4, 0.6, 1.0])
def test_v_of_different_openness(spread):
    assert label(vee(spread=spread, noise=0.02, seed=5)) == "v"


def test_wobbly_shapes_across_seeds():
    for seed in range(20):
        assert label(circle(noise=0.06, seed=seed, r=0.5)) == "circle"
        assert label(line(noise=0.02, seed=seed, angle=seed * 0.3)) == "line"
        assert label(rot(vee(noise=0.04, seed=seed), seed * 0.5)) == "v"


def test_score_is_high_for_clean_and_ranking_is_sorted():
    r = Recognizer().classify(circle())
    assert r.score > 0.9 and [s for _, s in r.ranking] == sorted((s for _, s in r.ranking), reverse=True)


def test_scribble_is_rejected():
    rnd = random.Random(9)
    scribble = [(rnd.random(), rnd.random()) for _ in range(40)]
    assert Recognizer().classify(scribble).label is None


def test_degenerate_input_does_not_crash():
    assert Recognizer().classify([]).label is None
    assert Recognizer().classify([(0.5, 0.5)] * 5).label is None


def test_templates_from_recordings_and_files(tmp_path):
    path = str(tmp_path / "s.jsonl")
    for i in range(3):
        save_shape(path, "zig", [(0, 0), (1, 1), (2, 0), (3, 1), (4, 0)])
        save_shape(path, "circle", circle(noise=0.02, seed=i))
    shapes = load_shapes(path)
    assert len(shapes) == 6
    rec = recognizer_from_shapes(shapes)
    assert rec.labels() == ["circle", "zig"]
    assert rec.classify([(0, 0), (1, 1), (2, 0), (3, 1), (4, 0)]).label == "zig"
