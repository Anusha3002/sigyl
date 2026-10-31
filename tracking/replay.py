"""Run gesture detection on a recorded landmark file and print what it found next to your key markers.

  python -m tracking.replay test_clip2.jsonl
"""
import argparse

from .config import load_config
from .gestures import GestureConfig, GestureDetector
from .landmarks import load_landmarks, load_markers


def replay(path: str, cfg: GestureConfig):
    header, frames = load_landmarks(path)
    det = GestureDetector(cfg)
    found = []
    for t, hands in frames:
        s = det.update(t, hands[0] if hands else None)
        for e in s.events:
            found.append((t, e))
    return found


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--config", default="config.yaml")
    args = ap.parse_args()
    cfg = GestureConfig.from_dict(load_config(args.config).get("gestures"))
    rows = [(t, f"marker {m}") for t, m in load_markers(args.file)] + [(t, f"  -> {e}") for t, e in replay(args.file, cfg)]
    for t, text in sorted(rows, key=lambda r: r[0]):
        print(f"{t / 1000:7.2f}s  {text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
