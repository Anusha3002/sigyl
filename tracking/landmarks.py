"""Hand data types, MediaPipe result parsing and landmark files.

No camera, OpenCV or MediaPipe imports here, so the gesture and recognition code that
builds on this can be tested anywhere, including from recorded landmark files.
"""
import json
from dataclasses import dataclass
from typing import Any, Iterable, List, Optional, Sequence, Tuple

# Landmark indexes (MediaPipe's 21-point hand model)
WRIST = 0
THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP = 1, 2, 3, 4
INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP = 5, 6, 7, 8
MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP = 9, 10, 11, 12
RING_MCP, RING_PIP, RING_DIP, RING_TIP = 13, 14, 15, 16
PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP = 17, 18, 19, 20

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17),
]

Point = Tuple[float, float, float]


@dataclass(frozen=True)
class Hand:
    label: str  # "Left" or "Right" (your real hand, when the frame is mirrored before detection)
    score: float
    points: Tuple[Point, ...]  # 21 points, x and y normalized 0..1 (y grows downward), z relative depth

    def xy(self, index: int) -> Tuple[float, float]:
        p = self.points[index]
        return p[0], p[1]

    def pixels(self, width: int, height: int) -> List[Tuple[int, int]]:
        return [(int(round(p[0] * width)), int(round(p[1] * height))) for p in self.points]


def parse_result(result: Any) -> List[Hand]:
    """Turn a MediaPipe HandLandmarkerResult into Hand objects."""
    hands: List[Hand] = []
    landmarks = getattr(result, "hand_landmarks", None) or []
    handedness = getattr(result, "handedness", None) or []
    for i, lms in enumerate(landmarks):
        label, score = "Unknown", 0.0
        if i < len(handedness) and handedness[i]:
            cat = handedness[i][0]
            label = getattr(cat, "category_name", None) or getattr(cat, "display_name", "Unknown")
            score = float(getattr(cat, "score", 0.0))
        pts = tuple((float(p.x), float(p.y), float(p.z)) for p in lms)
        hands.append(Hand(label, score, pts))
    return hands


# ---- landmark files (JSON lines) ---------------------------------------------
def _hand_to_dict(h: Hand) -> dict:
    return {"label": h.label, "score": round(h.score, 4),
            "points": [[round(c, 5) for c in p] for p in h.points]}


def _hand_from_dict(d: dict) -> Hand:
    return Hand(d["label"], float(d["score"]), tuple(tuple(p) for p in d["points"]))


class LandmarkWriter:
    """Writes one JSON line per frame. The first line is a header with the settings."""

    def __init__(self, path: str, meta: Optional[dict] = None):
        self._f = open(path, "w", encoding="utf-8")
        self._f.write(json.dumps({"header": meta or {}}) + "\n")

    def write(self, t_ms: float, hands: Sequence[Hand]) -> None:
        self._f.write(json.dumps({"t": round(t_ms, 1), "hands": [_hand_to_dict(h) for h in hands]}) + "\n")

    def mark(self, t_ms: float, label: str) -> None:
        """Record a label (for example a key you pressed) at this moment."""
        self._f.write(json.dumps({"t": round(t_ms, 1), "marker": label}) + "\n")

    def close(self) -> None:
        self._f.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def load_landmarks(path: str) -> Tuple[dict, List[Tuple[float, List[Hand]]]]:
    """Returns (header, [(t_ms, hands), ...])."""
    header: dict = {}
    frames: List[Tuple[float, List[Hand]]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if "header" in row:
                header = row["header"]
            elif "marker" in row:
                continue
            else:
                frames.append((float(row["t"]), [_hand_from_dict(h) for h in row["hands"]]))
    return header, frames


def load_markers(path: str) -> List[Tuple[float, str]]:
    """Returns [(t_ms, label), ...] for every marker in a landmark file."""
    markers: List[Tuple[float, str]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                row = json.loads(line)
                if "marker" in row:
                    markers.append((float(row["t"]), row["marker"]))
    return markers
