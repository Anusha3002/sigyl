"""Gesture + drawing demo: zoom to start, pinch to draw a sigil, fist to lock in.

  python -m tracking.sigil_demo                      uses the built-in circle / line / V
  python -m tracking.sigil_demo --shapes data/shapes.jsonl   also learns from your recordings
Keys: r = start over (back to waiting for the zoom), q = quit.
"""
import argparse
import os
import time

import cv2

from recognition.dollar1 import Recognizer, load_shapes, default_templates
from .camera import Camera
from .config import load_config
from .draw import draw_hand, draw_trail, put_lines
from .gestures import DRAWING, LOCKED, READY, WAITING, GestureConfig, GestureDetector
from .hands import HandTracker
from .strokes import StrokeCapture

WINDOW = "Sigyl - draw a sigil (r reset, q quit)"
PROMPT = {WAITING: "Zoom (pinch, then spread your fingers wide) to start",
          READY: "Pinch and draw a circle, a line or a V",
          DRAWING: "Drawing... release to finish",
          LOCKED: "LOCKED IN!  (press r to start over)"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--camera", type=int)
    ap.add_argument("--shapes", help="file of recorded shapes to learn from (from record_shapes)")
    args = ap.parse_args()

    cfg = load_config(args.config)
    rec = Recognizer()
    if args.shapes and os.path.exists(args.shapes):
        for label, pts in load_shapes(args.shapes):
            rec.add_template(label, pts)
        print(f"Learned from {args.shapes}")
    tracker = HandTracker(cfg["model_path"], max_hands=cfg["max_hands"])
    camera = Camera(args.camera if args.camera is not None else cfg["camera_index"], cfg["resolution"], cfg["fps"],
                    cfg["mirror"], cfg["fit"])
    det, cap = GestureDetector(GestureConfig.from_dict(cfg.get("gestures"))), StrokeCapture()
    shown, shown_at, shown_stroke, history = "", 0.0, None, []
    start = time.time()
    try:
        while True:
            frame = camera.read()
            if frame is None:
                break
            t_ms = (time.time() - start) * 1000.0
            hands = tracker.detect(frame, t_ms)
            state = det.update(t_ms, hands[0] if hands else None)
            stroke = cap.update(t_ms, state)
            if stroke:
                res = rec.classify(stroke.points)
                shown = f"{(res.label or 'not recognized').upper()}   ({res.best_label} {res.score:.2f})"
                shown_at, shown_stroke = time.time(), stroke
                if res.label:
                    history.append(res.label)
            for h in hands:
                draw_hand(frame, h)
            draw_trail(frame, cap.live_points)
            if shown_stroke and time.time() - shown_at < 2.0:
                draw_trail(frame, shown_stroke.points, color=(120, 255, 120), alpha=1.0 - (time.time() - shown_at) / 2.0)
            lines = [PROMPT[det.phase]]
            if shown and time.time() - shown_at < 2.0:
                lines.append("Sigil: " + shown)
            if history:
                lines.append("Drawn so far: " + ", ".join(history))
            if not hands:
                lines.append("(no hand in view)")
            put_lines(frame, lines)
            cv2.imshow(WINDOW, frame)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break
            if key == ord("r"):
                det.reset()
                cap.reset()
                history, shown = [], ""
    finally:
        camera.release()
        tracker.close()
        cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
