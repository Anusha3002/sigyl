"""Gesture detection from hand landmarks: zoom to start, pinch to draw, fist to lock in.

Works on Hand objects only (no camera, OpenCV or MediaPipe), so it can be tested with made-up
hands and replayed from recorded landmark files.

Phases:   WAITING --zoom--> READY <--pinch/release--> DRAWING        READY --fist held--> LOCKED
Events (returned by update, one frame each): "start", "pinch_begin", "pinch_end", "lock"

All sizes are divided by the palm size (wrist to middle-finger knuckle), so the numbers do not
depend on how far you are from the camera. Every threshold can be changed under `gestures:` in
config.yaml.
"""
import math
from collections import deque
from dataclasses import dataclass, field, fields
from typing import Deque, Dict, List, Optional, Tuple

from .landmarks import (INDEX_MCP, INDEX_TIP, MIDDLE_MCP, MIDDLE_TIP, PINKY_MCP, PINKY_TIP, RING_MCP, RING_TIP,
                        THUMB_TIP, WRIST, Hand)

WAITING, READY, DRAWING, LOCKED = "waiting", "ready", "drawing", "locked"
FINGERS = ((INDEX_TIP, INDEX_MCP), (MIDDLE_TIP, MIDDLE_MCP), (RING_TIP, RING_MCP), (PINKY_TIP, PINKY_MCP))


@dataclass
class GestureConfig:
    zoom_closed: float = 0.35     # thumb-index gap (in palm sizes) that counts as "closed" at the start of a zoom
    zoom_open: float = 1.2        # gap that counts as "spread wide" at the end of a zoom
    zoom_window_ms: float = 700   # the spread must happen within this time
    pinch_on: float = 0.3         # gap below this = pinching
    pinch_off: float = 0.55       # gap above this = released (higher than pinch_on so it does not flicker)
    pinch_hold_ms: float = 60     # pinch must last this long before drawing starts
    release_hold_ms: float = 80   # release must last this long before drawing stops
    start_cooldown_ms: float = 400  # after the zoom, ignore pinches for this long
    fist_curl: float = 0.45       # every fingertip closer than this (palm sizes) to its knuckle = fist
    fist_thumb_tuck: float = 0.7  # thumb tip this close (palm sizes) to the pinky knuckle = thumb tucked across the palm.
                                  # A fist also has thumb and index touching, so this is what tells it from a pinch.
    fist_hold_ms: float = 500     # fist must be held this long to lock in
    fist_max_speed: float = 1.0   # palm sizes per second; a moving hand is drawing, not a fist
    lost_ms: float = 150          # hand may vanish this long (tracker dropouts) without ending anything

    @classmethod
    def from_dict(cls, d: Optional[Dict]) -> "GestureConfig":
        d = d or {}
        names = {f.name for f in fields(cls)}
        unknown = set(d) - names
        if unknown:
            raise ValueError(f"Unknown gesture setting(s) in config.yaml: {sorted(unknown)}")
        return cls(**d)


@dataclass(frozen=True)
class Features:
    pinch: float                     # thumb tip to index tip, in palm sizes
    curl: float                      # largest fingertip-to-knuckle distance, in palm sizes (small = fist)
    thumb_tuck: float                # thumb tip to pinky knuckle, in palm sizes (small = thumb folded across the palm)
    palm: float                      # palm size in the image (0..1); grows as the hand nears the camera
    center: Tuple[float, float]      # palm center
    point: Tuple[float, float]       # where the pinch is (midpoint of thumb tip and index tip)


def features(hand: Hand) -> Features:
    d = lambda a, b: math.dist(hand.xy(a), hand.xy(b))
    palm = max(d(WRIST, MIDDLE_MCP), 1e-6)
    pinch = d(THUMB_TIP, INDEX_TIP) / palm
    curl = max(d(t, m) for t, m in FINGERS) / palm
    cx = sum(hand.xy(i)[0] for i in (WRIST, INDEX_MCP, MIDDLE_MCP, PINKY_MCP)) / 4
    cy = sum(hand.xy(i)[1] for i in (WRIST, INDEX_MCP, MIDDLE_MCP, PINKY_MCP)) / 4
    (tx, ty), (ix, iy) = hand.xy(THUMB_TIP), hand.xy(INDEX_TIP)
    return Features(pinch, curl, d(THUMB_TIP, PINKY_MCP) / palm, palm, (cx, cy), ((tx + ix) / 2, (ty + iy) / 2))


@dataclass(frozen=True)
class GestureState:
    phase: str
    events: Tuple[str, ...] = ()
    pinching: bool = False
    fist: bool = False
    hand_seen: bool = False
    features: Optional[Features] = None


class GestureDetector:
    def __init__(self, config: Optional[GestureConfig] = None):
        self.cfg = config or GestureConfig()
        self.reset()

    def reset(self) -> None:
        """Back to WAITING (a new round)."""
        self.phase = WAITING
        self._pinch_hist: Deque[Tuple[float, float]] = deque()
        self._center_hist: Deque[Tuple[float, Tuple[float, float], float]] = deque()
        self._pinching = False
        self._pinch_change_since: Optional[float] = None
        self._fist_since: Optional[float] = None
        self._last_seen: Optional[float] = None
        self._ready_since = 0.0
        self._last: Optional[GestureState] = None

    def update(self, t_ms: float, hand: Optional[Hand]) -> GestureState:
        c = self.cfg
        events: List[str] = []

        if hand is None:
            if self._last_seen is not None and t_ms - self._last_seen > c.lost_ms:
                if self.phase == DRAWING:
                    events.append("pinch_end")
                    self.phase = READY
                self._pinching = False
                self._pinch_change_since = None
                self._fist_since = None
                self._pinch_hist.clear()
                self._center_hist.clear()
            return self._state(events, hand_seen=False, feats=None)

        self._last_seen = t_ms
        f = features(hand)
        self._pinch_hist.append((t_ms, f.pinch))
        while self._pinch_hist and t_ms - self._pinch_hist[0][0] > c.zoom_window_ms:
            self._pinch_hist.popleft()
        self._center_hist.append((t_ms, f.center, f.palm))
        while self._center_hist and t_ms - self._center_hist[0][0] > 250:
            self._center_hist.popleft()

        if self.phase == LOCKED:
            return self._state(events, True, f)

        if self.phase == WAITING:
            if f.pinch >= c.zoom_open and min(p for _, p in self._pinch_hist) <= c.zoom_closed:
                self.phase = READY
                self._ready_since = t_ms
                self._pinch_hist.clear()
                events.append("start")
            return self._state(events, True, f)

        # READY or DRAWING ----------------------------------------------------
        fist_pose = f.curl <= c.fist_curl and f.thumb_tuck <= c.fist_thumb_tuck
        fist = fist_pose and self._speed() <= c.fist_max_speed
        if fist:
            if self._fist_since is None:
                self._fist_since = t_ms
            if t_ms - self._fist_since >= c.fist_hold_ms:
                if self.phase == DRAWING:
                    events.append("pinch_end")
                self._pinching = False
                self.phase = LOCKED
                events.append("lock")
                return self._state(events, True, f)
        else:
            self._fist_since = None

        if t_ms - self._ready_since >= c.start_cooldown_ms:
            self._update_pinch(t_ms, f, events, fist_pose)
        return self._state(events, True, f)

    # ---- helpers ------------------------------------------------------------
    def _update_pinch(self, t_ms: float, f: Features, events: List[str], fist_pose: bool) -> None:
        c = self.cfg
        # A fist has thumb and index touching too, so a closing fist must not start a stroke.
        want = (f.pinch < c.pinch_on and not fist_pose) if not self._pinching else (not f.pinch > c.pinch_off and not fist_pose)
        if want == self._pinching:
            self._pinch_change_since = None
            return
        if self._pinch_change_since is None:
            self._pinch_change_since = t_ms
        need = c.pinch_hold_ms if want else c.release_hold_ms
        if t_ms - self._pinch_change_since >= need:
            self._pinching = want
            self._pinch_change_since = None
            if want:
                self.phase = DRAWING
                events.append("pinch_begin")
            else:
                self.phase = READY
                events.append("pinch_end")

    def _speed(self) -> float:
        """Palm movement in palm sizes per second over the last quarter second."""
        if len(self._center_hist) < 2:
            return 0.0
        (t0, (x0, y0), p0), (t1, (x1, y1), _) = self._center_hist[0], self._center_hist[-1]
        if t1 - t0 < 80:
            return 0.0
        return math.hypot(x1 - x0, y1 - y0) / max(p0, 1e-6) / ((t1 - t0) / 1000.0)

    def _state(self, events: List[str], hand_seen: bool, feats: Optional[Features]) -> GestureState:
        fist = self._fist_since is not None or self.phase == LOCKED
        s = GestureState(self.phase, tuple(events), self._pinching, fist, hand_seen, feats)
        self._last = s
        return s
