"""The $1 unistroke recognizer (Wobbrock, Wilson & Li, 2007), for circle / line / V.

How it works, in plain steps (so you can explain it):
  1. Resample the path to 64 evenly spaced points, so drawing speed does not matter.
  2. Rotate so the line from the center to the first point is horizontal. This makes it
     rotation-free: a V is a V however it is turned, a line is a line in any direction.
  3. Scale so the longest side of the shape is 1 (uniformly, so a line stays a line), and move
     its center to (0, 0), so size and position do not matter.
  4. Compare with every template: the average distance between matching points, trying a few
     small extra rotations. The closest template wins; score = 1 - distance / 0.707, so 1.0 is
     a perfect match and 0 is nothing alike.
Each template also gets reversed and mirrored copies, so a circle drawn clockwise or
counter-clockwise, or a V drawn backwards, both match.
"""
import json
import math
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

Point = Tuple[float, float]
N_POINTS = 64
HALF_DIAGONAL = 0.5 * math.sqrt(2.0)
PHI = 0.5 * (-1.0 + math.sqrt(5.0))


def path_length(pts: Sequence[Point]) -> float:
    return sum(math.dist(pts[i - 1], pts[i]) for i in range(1, len(pts)))


def resample(pts: Sequence[Point], n: int = N_POINTS) -> List[Point]:
    pts = list(pts)
    total = path_length(pts)
    if total <= 0:
        return [pts[0]] * n
    step = total / (n - 1)
    out = [pts[0]]
    acc = 0.0
    i = 1
    while i < len(pts):
        d = math.dist(pts[i - 1], pts[i])
        if d > 0 and acc + d >= step:
            t = (step - acc) / d
            q = (pts[i - 1][0] + t * (pts[i][0] - pts[i - 1][0]), pts[i - 1][1] + t * (pts[i][1] - pts[i - 1][1]))
            out.append(q)
            pts.insert(i, q)  # q is now the start of the next piece
            acc = 0.0
        else:
            acc += d
        i += 1
    while len(out) < n:  # rounding can leave us one short
        out.append(pts[-1])
    return out[:n]


def centroid(pts: Sequence[Point]) -> Point:
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)


def rotate(pts: Sequence[Point], angle: float) -> List[Point]:
    """Rotate about the origin."""
    c, s = math.cos(angle), math.sin(angle)
    return [(x * c - y * s, x * s + y * c) for x, y in pts]


def normalize(raw: Sequence[Point]) -> List[Point]:
    pts = resample(raw)
    cx, cy = centroid(pts)
    angle = math.atan2(cy - pts[0][1], cx - pts[0][0])
    pts = [(x - cx, y - cy) for x, y in pts]
    pts = rotate(pts, -angle)
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    size = max(max(xs) - min(xs), max(ys) - min(ys))
    if size > 1e-9:
        pts = [(x / size, y / size) for x, y in pts]
    cx, cy = centroid(pts)
    return [(x - cx, y - cy) for x, y in pts]


def _dist_at_angle(pts: Sequence[Point], tpl: Sequence[Point], angle: float) -> float:
    c, s = math.cos(angle), math.sin(angle)
    return sum(math.hypot(x * c - y * s - tx, x * s + y * c - ty) for (x, y), (tx, ty) in zip(pts, tpl)) / len(pts)


def distance_at_best_angle(pts, tpl, a=-math.radians(45), b=math.radians(45), threshold=math.radians(2)) -> float:
    x1, x2 = PHI * a + (1 - PHI) * b, (1 - PHI) * a + PHI * b
    f1, f2 = _dist_at_angle(pts, tpl, x1), _dist_at_angle(pts, tpl, x2)
    while abs(b - a) > threshold:
        if f1 < f2:
            b, x2, f2 = x2, x1, f1
            x1 = PHI * a + (1 - PHI) * b
            f1 = _dist_at_angle(pts, tpl, x1)
        else:
            a, x1, f1 = x1, x2, f2
            x2 = (1 - PHI) * a + PHI * b
            f2 = _dist_at_angle(pts, tpl, x2)
    return min(f1, f2)


@dataclass(frozen=True)
class Result:
    label: Optional[str]            # None when nothing matched well enough
    score: float                    # 0..1 of the best template (even if rejected)
    best_label: str                 # closest sigil, even if rejected
    ranking: Tuple[Tuple[str, float], ...]  # (label, best score), best first


# ---- built-in templates (so it works before you record anything) ------------------
def _circle(aspect: float = 1.0, turns: float = 1.0) -> List[Point]:
    n = 48
    return [(math.cos(2 * math.pi * turns * i / n), aspect * math.sin(2 * math.pi * turns * i / n)) for i in range(n + 1)]


def _line() -> List[Point]:
    return [(i / 20.0, 0.0) for i in range(21)]


def _v(half_angle_deg: float) -> List[Point]:
    k = math.tan(math.radians(half_angle_deg))
    return [(-1 + i / 10.0, -k * (1 - i / 10.0)) for i in range(11)] + [(i / 10.0, -k * (i / 10.0)) for i in range(1, 11)]


def default_templates() -> Dict[str, List[List[Point]]]:
    return {
        "circle": [_circle(1.0), _circle(0.75), _circle(1.0, 1.1)],
        "line": [_line()],
        "v": [_v(30), _v(45), _v(60)],
    }


class Recognizer:
    def __init__(self, templates: Optional[Dict[str, Iterable[Sequence[Point]]]] = None, min_score: float = 0.75):
        self.min_score = min_score
        self._templates: List[Tuple[str, List[Point]]] = []
        for label, tpls in (templates if templates is not None else default_templates()).items():
            for t in tpls:
                self.add_template(label, t)

    def add_template(self, label: str, points: Sequence[Point]) -> None:
        """Adds the stroke plus its reversed and mirrored copies."""
        pts = [tuple(p) for p in points]
        for variant in (pts, pts[::-1], [(x, -y) for x, y in pts], [(x, -y) for x, y in pts[::-1]]):
            self._templates.append((label, normalize(variant)))

    def labels(self) -> List[str]:
        return sorted({l for l, _ in self._templates})

    def classify(self, points: Sequence[Point]) -> Result:
        if len(points) < 2 or path_length(points) <= 0:
            return Result(None, 0.0, "", ())
        cand = normalize(points)
        best: Dict[str, float] = {}
        for label, tpl in self._templates:
            score = 1.0 - distance_at_best_angle(cand, tpl) / HALF_DIAGONAL
            if score > best.get(label, -1.0):
                best[label] = score
        ranking = tuple(sorted(best.items(), key=lambda kv: -kv[1]))
        top_label, top_score = ranking[0]
        return Result(top_label if top_score >= self.min_score else None, top_score, top_label, ranking)


# ---- recorded shapes (JSON lines: {"label": "circle", "points": [[x, y], ...]}) -----------
def save_shape(path: str, label: str, points: Sequence[Point]) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"label": label, "points": [[round(x, 5), round(y, 5)] for x, y in points]}) + "\n")


def load_shapes(path: str) -> List[Tuple[str, List[Point]]]:
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                row = json.loads(line)
                out.append((row["label"], [tuple(p) for p in row["points"]]))
    return out


def recognizer_from_shapes(shapes: Iterable[Tuple[str, Sequence[Point]]], min_score: float = 0.75,
                           with_defaults: bool = False) -> Recognizer:
    rec = Recognizer(None if with_defaults else {}, min_score)
    for label, pts in shapes:
        rec.add_template(label, pts)
    return rec
