"""The 26 card sigils and the recognizer the game uses to tell which one was drawn.

Rule (decided with the card designs): the upright SHAPE matters, as printed on the card.
Where you start and which way you go round do not matter.

How it differs from dollar1.py (the circle / line / V recognizer):
  * no "rotate to a standard angle" step, so Wall (open at the bottom) and Cup (open at the
    top) stay different. Only a small tilt (up to 20 degrees either way) is forgiven.
  * every template is stored forwards and backwards (direction-free); closed shapes are also
    stored starting from 16 different points round the loop (start-free).
  * the game only asks "which of the 3 cards on offer is this?", not "which of all 26?".

The shapes below were traced by eye from the card PDF, in the PDF's own pixel units
(only proportions matter). Recordings of real drawings can be added with add_template().
"""
import math
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .dollar1 import HALF_DIAGONAL, N_POINTS, centroid, path_length, resample

Point = Tuple[float, float]
TILTS = tuple(math.radians(a) for a in (-20, -10, 0, 10, 20))
START_STEP = 4  # closed shapes: try a start every 4th point


def _arc(cx, cy, r, start_deg, turns, n=48, r_end=None) -> List[Point]:
    """Points on a circle (or a spiral if r_end is given). Angles: 0 = right, 90 = down (screen y)."""
    r_end = r if r_end is None else r_end
    out = []
    for i in range(n + 1):
        rr = r + (r_end - r) * i / n
        a = math.radians(start_deg) + 2 * math.pi * turns * i / n
        out.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return out


def _teardrop() -> List[Point]:
    top, (cx, cy), r = (675.0, 123.0), (675.0, 200.0), 38.0
    alpha = math.degrees(math.asin(r / (cy - top[1])))       # where the straight sides meet the round part
    start = -90 + (90 - alpha)                                # right-hand tangent point
    sweep = (360 - 2 * (90 - alpha)) / 360.0
    return [top] + _arc(cx, cy, r, start, sweep, 40) + [top]


# name -> (points, closed?)
SIGILS: Dict[str, Tuple[List[Point], bool]] = {
    "Slash": ([(118, 238), (233, 123)], False),
    "Fang": ([(368, 123), (418, 238), (483, 157)], False),
    "Bolt": ([(700, 123), (650, 175), (700, 175), (663, 237)], False),
    "Rake": ([(118, 588), (118, 472), (175, 530), (233, 472), (233, 588)], False),
    "Spear": ([(368, 588), (483, 472), (418, 472)], False),
    "Scythe": ([(700, 588), (700, 497)] + _arc(675, 497, 25, 0, -0.5, 16), False),
    "Crush": ([(115, 835), (175, 835), (175, 925), (235, 925)], False),
    "Bite": ([(366, 829), (486, 881), (366, 932)], False),
    "Talon": ([(618, 823), (685, 823), (733, 873), (733, 937), (685, 905)], False),
    "Quake": ([(115, 205), (135, 157), (155, 205), (175, 157), (195, 205), (215, 157), (235, 205)], False),
    "Wall": ([(365, 232), (365, 128), (486, 128), (486, 232)], False),
    "Shield": (_teardrop(), True),
    "Ring": (_arc(175, 530, 58, -90, 1.0), True),
    "Cup": ([(365, 486), (365, 532), (396, 576), (456, 576), (486, 532), (486, 486)], False),
    "Buckler": (_arc(675, 533, 58, -100, 1.6, 72, r_end=14), False),
    "Aegis": ([(115, 925), (175, 835), (235, 925), (115, 925)], True),
    "Gate": ([(365, 932), (365, 873), (426, 828), (486, 873), (486, 932), (456, 905)], False),
    "Mend": ([(615, 903), (645, 903), (676, 843), (690, 917), (706, 903), (736, 903)], False),
    "Bloom": ([(175, 238), (175, 187), (125, 155), (125, 123), (160, 123), (175, 155), (190, 123), (226, 123),
               (226, 155), (175, 187)], False),
    "Hourglass": ([(368, 123), (483, 123), (368, 238), (483, 238), (368, 123)], True),
    "Bowtie": ([(618, 123), (618, 238), (733, 123), (733, 238), (618, 123)], True),
    "Fade": (_arc(153, 530, 40, -57, -1.0) + _arc(196, 530, 40, -123, 1.0), False),
    "Wisp": ([(365 + 121 * i / 40, 530 + 37 * math.sin(2 * math.pi * i / 40)) for i in range(41)], False),
    "Rise": ([(618, 588), (668, 472), (733, 555)], False),
    "Spring": ([(115, 925), (160, 925), (190, 893), (190, 850), (160, 835), (130, 850), (130, 880), (160, 895),
                (205, 880), (235, 835)], False),
    "Heart": ([(425, 933), (365, 858), (380, 828), (410, 828), (425, 858), (440, 828), (470, 828), (486, 858),
               (425, 933)], True),
}


def normalize(points: Sequence[Point]) -> List[Point]:
    """64 evenly spaced points, centered, longest side scaled to 1. No rotation."""
    pts = resample(points, N_POINTS)
    cx, cy = centroid(pts)
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    size = max(max(xs) - min(xs), max(ys) - min(ys)) or 1.0
    return [((x - cx) / size, (y - cy) / size) for x, y in pts]


def _variants(points: Sequence[Point], closed: bool) -> List[List[Point]]:
    base = resample(points, N_POINTS)
    out = []
    for seq in (base, base[::-1]):
        if closed:
            loop = seq[:-1]
            for k in range(0, len(loop), START_STEP):
                turned = loop[k:] + loop[:k]
                out.append(normalize(turned + [turned[0]]))
        else:
            out.append(normalize(seq))
    return out


def _distance(cand: Sequence[Point], tpl: Sequence[Point]) -> float:
    best = float("inf")
    for a in TILTS:
        c, s = math.cos(a), math.sin(a)
        d = sum(math.hypot(x * c - y * s - tx, x * s + y * c - ty) for (x, y), (tx, ty) in zip(cand, tpl)) / len(cand)
        best = min(best, d)
    return best


def looks_closed(points: Sequence[Point]) -> bool:
    """A drawing counts as a loop when its ends meet (within a fifth of its size)."""
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    size = max(max(xs) - min(xs), max(ys) - min(ys)) or 1.0
    return math.dist(points[0], points[-1]) < 0.2 * size


@dataclass(frozen=True)
class SigilResult:
    label: Optional[str]                       # None = not recognized
    score: float                               # best score, 0..1
    best_label: str
    ranking: Tuple[Tuple[str, float], ...]     # every candidate, best first


class SigilRecognizer:
    def __init__(self, min_score: float = 0.72, min_margin: float = 0.02):
        """min_score: how good the best match must be. min_margin: how far ahead of the runner-up."""
        self.min_score = min_score
        self.min_margin = min_margin
        self._templates: Dict[str, List[List[Point]]] = {}
        for name, (pts, closed) in SIGILS.items():
            self._templates[name] = _variants(pts, closed)

    def names(self) -> List[str]:
        return list(self._templates)

    def add_template(self, name: str, points: Sequence[Point]) -> None:
        """Learn from a real drawing of this sigil."""
        pts = [tuple(p) for p in points]
        self._templates.setdefault(name, []).extend(_variants(pts, looks_closed(pts)))

    def score(self, points: Sequence[Point], name: str) -> float:
        cand = normalize(points)
        return 1.0 - min(_distance(cand, t) for t in self._templates[name]) / HALF_DIAGONAL

    def classify(self, points: Sequence[Point], candidates: Optional[Iterable[str]] = None) -> SigilResult:
        """Which of `candidates` (default: all sigils) was drawn?"""
        names = [n for n in (candidates if candidates is not None else self._templates) if n in self._templates]
        if len(points) < 2 or path_length(points) <= 0 or not names:
            return SigilResult(None, 0.0, "", ())
        cand = normalize(points)
        scored = sorted(((n, 1.0 - min(_distance(cand, t) for t in self._templates[n]) / HALF_DIAGONAL) for n in names),
                        key=lambda kv: -kv[1])
        top, top_score = scored[0]
        margin = top_score - scored[1][1] if len(scored) > 1 else 1.0
        ok = top_score >= self.min_score and margin >= self.min_margin
        return SigilResult(top if ok else None, top_score, top, tuple(scored))
