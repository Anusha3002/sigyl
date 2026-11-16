"""Collects the fingertip path of one stroke between pinch_begin and pinch_end.

Feed it every frame's GestureState. It returns a finished Stroke on pinch_end, or None if the
path was too short to be a real drawing (a pinch flicker, or a fist closing).
"""
import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .gestures import GestureState

Point = Tuple[float, float]


@dataclass(frozen=True)
class Stroke:
    points: Tuple[Point, ...]   # smoothed path, x and y normalized 0..1 of the frame
    t_start: float
    t_end: float
    t_last_point: float = 0.0   # when the last kept point was drawn (the moment the hand finished the shape)

    def length(self) -> float:
        return sum(math.dist(self.points[i - 1], self.points[i]) for i in range(1, len(self.points)))


class StrokeCapture:
    def __init__(self, min_points: int = 8, min_length: float = 0.20, smoothing: float = 0.5,
                 max_pinch: float = 0.45, trim: int = 2):
        """min_length is a fraction of the frame width; smoothing 0..1 (1 = no smoothing).

        max_pinch: only frames where the thumb-index gap is below this (palm sizes) add a point.
        While the fingers close or open, the pinch point jerks sideways, which put a stray tail on
        circles. trim: points dropped from each end for the same reason."""
        self.max_pinch = max_pinch
        self.trim = trim
        self.min_points = min_points
        self.min_length = min_length
        self.smoothing = smoothing
        self._points: List[Point] = []
        self._t_points: List[float] = []
        self._t_start = 0.0
        self.active = False

    @property
    def live_points(self) -> List[Point]:
        """Path so far, for drawing the trail while the person is still drawing."""
        return list(self._points)

    def reset(self) -> None:
        self._points = []
        self.active = False

    def update(self, t_ms: float, state: GestureState) -> Optional[Stroke]:
        if "pinch_begin" in state.events:
            self._points, self._t_points, self._t_start, self.active = [], [], t_ms, True
        if self.active and state.features is not None and state.pinching and state.features.pinch < self.max_pinch:
            p = state.features.point
            if self._points and self.smoothing < 1.0:
                q = self._points[-1]
                p = (q[0] + self.smoothing * (p[0] - q[0]), q[1] + self.smoothing * (p[1] - q[1]))
            self._points.append(p)
            self._t_points.append(t_ms)
        if "pinch_end" in state.events:
            pts = self._points[self.trim:len(self._points) - self.trim] if len(self._points) > 2 * self.trim else []
            times = self._t_points[self.trim:len(self._t_points) - self.trim] if pts else []
            stroke = Stroke(tuple(pts), self._t_start, t_ms, times[-1] if times else t_ms)
            self.active = False
            self._points = []
            if len(stroke.points) >= self.min_points and stroke.length() >= self.min_length:
                return stroke
        return None
