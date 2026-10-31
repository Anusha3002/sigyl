"""Drawing helpers for the demo window."""
from typing import Sequence, Tuple

import cv2

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
