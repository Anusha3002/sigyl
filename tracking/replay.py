"""Run gesture detection on a recorded landmark file and print what it found next to your key markers.

  python -m tracking.replay test_clip2.jsonl
"""
import argparse

from .config import load_config
from .gestures import GestureConfig, GestureDetector
from .landmarks import load_landmarks, load_markers
from .strokes import StrokeCapture


def replay(path: str, cfg: GestureConfig):
    header, frames = load_landmarks(path)
    det = GestureDetector(cfg)
    found = []
    for t, hands in frames:
        s = det.update(t, hands[0] if hands else None)
        for e in s.events:
            found.append((t, e))
    return found


def replay_strokes(path: str, cfg: GestureConfig, recognizer):
    """Returns [(t_end_ms, Stroke, Result)] for every stroke found in the file."""
    _, frames = load_landmarks(path)
    det, cap, out = GestureDetector(cfg), StrokeCapture(), []
    for t, hands in frames:
        stroke = cap.update(t, det.update(t, hands[0] if hands else None))
        if stroke:
            out.append((t, stroke, recognizer.classify(stroke.points)))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--config", default="config.yaml")
    args = ap.parse_args()
    cfg = GestureConfig.from_dict(load_config(args.config).get("gestures"))
    from recognition.dollar1 import Recognizer

    rows = [(t, f"marker {m}") for t, m in load_markers(args.file)] + [(t, f"  -> {e}") for t, e in replay(args.file, cfg)]
    for t, stroke, res in replay_strokes(args.file, cfg, Recognizer()):
        rows.append((t, f"  ==> stroke of {len(stroke.points)} points, {stroke.t_end - stroke.t_start:.0f} ms: "
                        f"{res.label or '(rejected)'}  [best guess {res.best_label} {res.score:.2f}]"))
    for t, text in sorted(rows, key=lambda r: r[0]):
        print(f"{t / 1000:7.2f}s  {text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
