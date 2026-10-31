"""Record labeled shapes so the recognizer learns YOUR drawing.

  python -m tracking.record_shapes                    10 each of circle, line, v into data/shapes.jsonl
  python -m tracking.record_shapes --per-shape 15 --shapes circle v

No zoom needed here. The window tells you what to draw: pinch, draw it in the air, release.
Keys: u = undo the last shape, q = quit (everything is saved as you go; run it again to continue).
"""
import argparse
import os
import time
from collections import Counter

import cv2

from recognition.dollar1 import Recognizer, load_shapes
from .camera import Camera
from .config import load_config
from .draw import draw_hand, draw_trail, put_lines
from .gestures import LOCKED, GestureConfig, GestureDetector
from .hands import HandTracker
from .strokes import StrokeCapture

WINDOW = "Sigyl - record shapes (u undo, q quit)"


def write_all(path, shapes):
    import json

    with open(path, "w", encoding="utf-8") as f:
        for label, pts in shapes:
            f.write(json.dumps({"label": label, "points": [[round(x, 5), round(y, 5)] for x, y in pts]}) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/shapes.jsonl")
    ap.add_argument("--per-shape", type=int, default=10)
    ap.add_argument("--shapes", nargs="+", default=["circle", "line", "v"])
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--camera", type=int)
    args = ap.parse_args()

    cfg = load_config(args.config)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    saved = load_shapes(args.out) if os.path.exists(args.out) else []
    counts = Counter(l for l, _ in saved)
    print(f"Resuming with {dict(counts)}" if saved else "Starting a new shape file.")

    tracker = HandTracker(cfg["model_path"], max_hands=cfg["max_hands"])
    camera = Camera(args.camera if args.camera is not None else cfg["camera_index"], cfg["resolution"], cfg["fps"],
                    cfg["mirror"], cfg["fit"])
    det, cap, guesser = GestureDetector(GestureConfig.from_dict(cfg.get("gestures"))), StrokeCapture(), Recognizer()
    det.start_ready()
    last_stroke, last_text, last_time = None, "", 0.0
    start = time.time()
    try:
        while True:
            todo = [s for s in args.shapes if counts[s] < args.per_shape]
            frame = camera.read()
            if frame is None:
                break
            t_ms = (time.time() - start) * 1000.0
            hands = tracker.detect(frame, t_ms)
            state = det.update(t_ms, hands[0] if hands else None)
            if det.phase == LOCKED:
                det.start_ready()  # a fist means nothing here
            stroke = cap.update(t_ms, state)
            if stroke and todo:
                label = todo[0]
                saved.append((label, list(stroke.points)))
                counts[label] += 1
                write_all(args.out, saved)
                guess = guesser.classify(stroke.points)
                last_stroke, last_time = stroke, time.time()
                last_text = f"saved as {label} (built-in guess: {guess.best_label} {guess.score:.2f})"

            for h in hands:
                draw_hand(frame, h)
            draw_trail(frame, cap.live_points)
            if last_stroke and time.time() - last_time < 1.5:
                draw_trail(frame, last_stroke.points, color=(120, 255, 120), alpha=1.0 - (time.time() - last_time) / 1.5)
            lines = [f"Draw: {todo[0].upper()}   ({counts[todo[0]]}/{args.per_shape})   pinch, draw, release"] if todo else ["All done! Press q."]
            lines.append("   ".join(f"{s} {counts[s]}/{args.per_shape}" for s in args.shapes))
            if last_text:
                lines.append(last_text)
            put_lines(frame, lines)
            cv2.imshow(WINDOW, frame)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break
            if key == ord("u") and saved:
                label, _ = saved.pop()
                counts[label] -= 1
                write_all(args.out, saved)
                last_text, last_stroke = f"undid one {label}", None
    finally:
        camera.release()
        tracker.close()
        cv2.destroyAllWindows()
    print(f"{len(saved)} shapes in {args.out}: {dict(counts)}")
    print("Check accuracy with:  python -m recognition.evaluate " + args.out + " --defaults")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
