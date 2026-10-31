"""Drawing helpers for the demo window."""
from typing import Optional, Sequence, Tuple

import cv2
import numpy as np

from .landmarks import HAND_CONNECTIONS, INDEX_TIP, THUMB_TIP, Hand

LINE = (200, 160, 90)      # BGR, soft gold-ish
JOINT = (240, 240, 240)
TIPS = (0, 200, 255)


def draw_hand(frame, hand: Hand) -> None:
    h, w = frame.shape[:2]
    pts = hand.pixels(w, h)
    for a, b in HAND_CONNECTIONS:
        cv2.line(frame, pts[a], pts[b], LINE, 2, cv2.LINE_AA)
    for i, p in enumerate(pts):
        cv2.circle(frame, p, 5 if i in (THUMB_TIP, INDEX_TIP) else 3, TIPS if i in (THUMB_TIP, INDEX_TIP) else JOINT, -1, cv2.LINE_AA)


def put_lines(frame, lines: Sequence[str], origin: Tuple[int, int] = (10, 24)) -> None:
    x, y = origin
    for line in lines:
        cv2.putText(frame, line, (x + 1, y + 1), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2, cv2.LINE_AA)
        cv2.putText(frame, line, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
        y += 22


NEON = (255, 200, 60)      # BGR, cyan-ish glow (placeholder until the real visual style)


def draw_trail(frame, points: Sequence[Tuple[float, float]], color=NEON, alpha: float = 1.0) -> None:
    """Glowing line through normalized points: a wide soft layer, then a bright thin core."""
    if len(points) < 2:
        return
    h, w = frame.shape[:2]
    pts = np.array([[int(x * w), int(y * h)] for x, y in points], dtype=np.int32).reshape(-1, 1, 2)
    glow = frame.copy()
    cv2.polylines(glow, [pts], False, color, 12, cv2.LINE_AA)
    cv2.polylines(glow, [pts], False, (255, 255, 255), 3, cv2.LINE_AA)
    cv2.addWeighted(glow, 0.55 * alpha, frame, 1 - 0.55 * alpha, 0, dst=frame)
