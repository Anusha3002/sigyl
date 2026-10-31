"""Gesture detection on made-up hands (no camera needed)."""
import pytest

from tracking.gestures import DRAWING, LOCKED, READY, WAITING, GestureConfig, GestureDetector, features
from tracking.landmarks import Hand

PALM = 0.1


def make_hand(pinch=2.0, curl=1.5, cx=0.5, cy=0.5, palm=PALM):
    """Hand with wrist at (cx, cy), palm size `palm`; `pinch` and `curl` are in palm sizes."""
    pts = [(cx, cy, 0.0)] * 21
    pts = list(pts)
    mcps = {5: -0.2, 9: 0.0, 13: 0.2, 17: 0.4}
    for mcp, dx in mcps.items():
        x, y = cx + dx * palm, cy - palm
        pts[mcp] = (x, y, 0.0)
        pts[mcp + 3] = (x, y - curl * palm, 0.0)       # fingertip
    ix, iy = pts[8][0], pts[8][1]
    pts[4] = (ix + pinch * palm, iy, 0.0)               # thumb tip
    return Hand("Right", 0.99, tuple(pts))


def run(det, hands, start=0.0, dt=33.3):
    """Feed hands one per frame; returns every (time, event)."""
    out, t = [], start
    for h in hands:
        for e in det.update(t, h).events:
            out.append((t, e))
        t += dt
    return out


def events(det, hands, **kw):
    return [e for _, e in run(det, hands, **kw)]


def zoom_sequence():
    return [make_hand(pinch=p) for p in (0.1, 0.1, 0.5, 1.0, 1.6, 2.0, 2.0)]


def test_features_are_in_palm_sizes():
    f = features(make_hand(pinch=0.5, curl=1.0))
    assert f.pinch == pytest.approx(0.5, abs=0.02)
    assert f.curl == pytest.approx(1.0, abs=0.02)
    assert f.palm == pytest.approx(PALM)


def test_features_do_not_depend_on_distance_to_camera():
    near = features(make_hand(pinch=0.8, palm=0.25))
    far = features(make_hand(pinch=0.8, palm=0.08))
    assert near.pinch == pytest.approx(far.pinch, abs=0.02)


def test_zoom_starts_the_game_once():
    det = GestureDetector()
    assert events(det, zoom_sequence()) == ["start"]
    assert det.phase == READY
    assert events(det, zoom_sequence(), start=5000) == []  # already started


def test_spread_without_a_closed_start_is_not_a_zoom():
    det = GestureDetector()
    assert events(det, [make_hand(pinch=2.0)] * 30) == []
    assert det.phase == WAITING


def test_slow_spread_is_not_a_zoom():
    det = GestureDetector()
    slow = [make_hand(pinch=0.1)] * 3 + [make_hand(pinch=0.1 + 0.02 * i) for i in range(70)]
    assert events(det, slow) == []


def test_pinch_then_release_draws_a_stroke():
    det = GestureDetector()
    events(det, zoom_sequence())
    seq = [make_hand(pinch=2.0)] * 20 + [make_hand(pinch=0.1)] * 15 + [make_hand(pinch=1.5)] * 10
    assert events(det, seq, start=1000) == ["pinch_begin", "pinch_end"]
    assert det.phase == READY


def test_pinch_is_ignored_before_the_zoom():
    det = GestureDetector()
    assert events(det, [make_hand(pinch=0.1)] * 30) == []


def test_a_one_frame_flicker_does_not_start_or_stop_drawing():
    det = GestureDetector()
    events(det, zoom_sequence())
    base = [make_hand(pinch=2.0)] * 20
    assert events(det, base + [make_hand(pinch=0.1)] + base, start=1000) == []
    seq = [make_hand(pinch=0.1)] * 15 + [make_hand(pinch=1.5)] + [make_hand(pinch=0.1)] * 5
    assert events(GestureDetector(), zoom_sequence() + [make_hand(pinch=2.0)] * 20 + seq, start=0) == ["start", "pinch_begin"]


def test_pinch_hysteresis_a_loose_pinch_stays_drawing():
    det = GestureDetector()
    events(det, zoom_sequence())
    seq = [make_hand(pinch=2.0)] * 20 + [make_hand(pinch=0.1)] * 10 + [make_hand(pinch=0.45)] * 10
    assert events(det, seq, start=1000) == ["pinch_begin"]
    assert det.phase == DRAWING


def test_fist_held_locks_in():
    det = GestureDetector()
    events(det, zoom_sequence())
    seq = [make_hand(pinch=2.0)] * 20 + [make_hand(pinch=0.8, curl=0.3)] * 30
    assert events(det, seq, start=1000) == ["lock"]
    assert det.phase == LOCKED


def test_short_fist_does_not_lock():
    det = GestureDetector()
    events(det, zoom_sequence())
    seq = [make_hand(pinch=0.8, curl=0.3)] * 8 + [make_hand(pinch=2.0)] * 20
    assert events(det, seq, start=1000) == []


def test_held_pinch_with_curled_fingers_is_not_a_fist():
    det = GestureDetector()
    events(det, zoom_sequence())
    seq = [make_hand(pinch=2.0)] * 20 + [make_hand(pinch=0.15, curl=0.38)] * 60
    assert events(det, seq, start=1000) == ["pinch_begin"]
    assert det.phase == DRAWING


def test_moving_fist_does_not_lock():
    det = GestureDetector()
    events(det, zoom_sequence())
    moving = [make_hand(pinch=0.8, curl=0.3, cx=0.2 + 0.01 * i) for i in range(40)]
    assert events(det, moving, start=1000) == []


def test_lock_ends_a_stroke_in_progress():
    det = GestureDetector()
    events(det, zoom_sequence())
    seq = [make_hand(pinch=2.0)] * 20 + [make_hand(pinch=0.1)] * 15 + [make_hand(pinch=0.8, curl=0.3)] * 30
    assert events(det, seq, start=1000) == ["pinch_begin", "pinch_end", "lock"]


def test_short_tracker_dropout_does_not_end_the_stroke():
    det = GestureDetector()
    events(det, zoom_sequence())
    seq = [make_hand(pinch=2.0)] * 20 + [make_hand(pinch=0.1)] * 15 + [None] * 3 + [make_hand(pinch=0.1)] * 5
    assert events(det, seq, start=1000) == ["pinch_begin"]


def test_losing_the_hand_for_long_ends_the_stroke():
    det = GestureDetector()
    events(det, zoom_sequence())
    seq = [make_hand(pinch=2.0)] * 20 + [make_hand(pinch=0.1)] * 15 + [None] * 10
    assert events(det, seq, start=1000) == ["pinch_begin", "pinch_end"]


def test_reset_starts_a_new_round():
    det = GestureDetector()
    events(det, zoom_sequence())
    det.reset()
    assert det.phase == WAITING
    assert events(det, zoom_sequence(), start=9000) == ["start"]


def test_config_rejects_unknown_names():
    with pytest.raises(ValueError):
        GestureConfig.from_dict({"zoom_oepn": 1.0})
    assert GestureConfig.from_dict({"zoom_open": 1.0}).zoom_open == 1.0
    assert GestureConfig.from_dict(None).pinch_on == 0.3
