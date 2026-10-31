"""Stroke capture on made-up hands moving through the air."""
import math

from recognition.dollar1 import Recognizer
from tracking.gestures import GestureDetector
from tracking.strokes import StrokeCapture
from tests.test_gestures import make_hand, zoom_sequence


def run_all(hands, start=0.0, dt=33.3, det=None, cap=None):
    det, cap = det or GestureDetector(), cap or StrokeCapture()
    strokes, t = [], start
    for h in hands:
        s = cap.update(t, det.update(t, h))
        if s:
            strokes.append(s)
        t += dt
    return det, cap, strokes


def drawing(path, open_before=15, open_after=10):
    """open hand, pinch moving along path, open hand again"""
    return ([make_hand(pinch=2.0, cx=path[0][0], cy=path[0][1])] * open_before
            + [make_hand(pinch=0.1, cx=x, cy=y) for x, y in path]
            + [make_hand(pinch=1.5, cx=path[-1][0], cy=path[-1][1])] * open_after)


def circle_path(n=45):
    return [(0.5 + 0.12 * math.cos(2 * math.pi * i / n), 0.5 + 0.12 * math.sin(2 * math.pi * i / n)) for i in range(n + 1)]


def test_circle_in_the_air_is_captured_and_recognized():
    det, cap, _ = run_all(zoom_sequence())
    _, _, strokes = run_all(drawing(circle_path()), start=1000, det=det, cap=cap)
    assert len(strokes) == 1
    assert Recognizer().classify(strokes[0].points).label == "circle"


def test_line_and_v_in_the_air():
    det, cap, _ = run_all(zoom_sequence())
    line = [(0.3 + 0.01 * i, 0.5 + 0.004 * i) for i in range(40)]
    v = [(0.3 + 0.01 * i, 0.3 + 0.02 * i) for i in range(20)] + [(0.5 + 0.01 * i, 0.7 - 0.02 * i) for i in range(1, 21)]
    _, _, s1 = run_all(drawing(line), start=1000, det=det, cap=cap)
    _, _, s2 = run_all(drawing(v), start=4000, det=det, cap=cap)
    assert Recognizer().classify(s1[0].points).label == "line"
    assert Recognizer().classify(s2[0].points).label == "v"


def test_short_flicker_is_not_a_stroke():
    det, cap, _ = run_all(zoom_sequence())
    tiny = [(0.5, 0.5)] * 6
    _, _, strokes = run_all(drawing(tiny), start=1000, det=det, cap=cap)
    assert strokes == []


def test_live_points_grow_while_drawing_then_clear():
    det, cap = GestureDetector(), StrokeCapture()
    run_all(zoom_sequence(), det=det, cap=cap)
    run_all(drawing(circle_path(), open_after=0)[:40], start=1000, det=det, cap=cap)
    assert len(cap.live_points) > 5 and cap.active
    run_all([make_hand(pinch=1.5)] * 10, start=3000, det=det, cap=cap)
    assert cap.live_points == [] and not cap.active


def test_nothing_is_captured_before_the_zoom():
    _, _, strokes = run_all(drawing(circle_path()))
    assert strokes == []
