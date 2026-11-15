"""Record your own drawings of the 26 card sigils.

  python -m tracking.record_sigils                 3 drawings of each sigil into data/sigils.jsonl
  python -m tracking.record_sigils --per-sigil 5
  python -m tracking.record_sigils --only Ring Shield Aegis

The card is shown on the right. Pinch, draw its sigil in the air, release. No zoom or fist needed.
Keys: u = undo the last drawing, n = skip to the next sigil, q = quit.
Everything is saved as you go; run it again to continue where you stopped.
"""
import argparse
import os
import time
from collections import Counter

import cv2
import numpy as np

from game.cards import CATALOG, Card
from recognition.dollar1 import load_shapes
from recognition.sigils import SigilRecognizer
from ui.screen import CAM_W, GOLD, GREEN, GREY, H, PANEL, RED, W, WHITE, CardArt, paste, shade, text
from .camera import Camera
from .config import load_config
from .draw import draw_hand, draw_trail
from .gestures import LOCKED, GestureConfig, GestureDetector
from .hands import HandTracker
from .record_shapes import write_all
from .strokes import StrokeCapture

WINDOW = "Sigyl - record sigils (u undo, n next, q quit)"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/sigils.jsonl")
    ap.add_argument("--per-sigil", type=int, default=3)
    ap.add_argument("--only", nargs="+", help="record just these sigils (card names)")
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--camera", type=int)
    args = ap.parse_args()

    cards = {title: Card(t, v, title) for title, t, v in CATALOG}
    names = list(cards)
    if args.only:
        wanted = {n.lower() for n in args.only}
        names = [n for n in names if n.lower() in wanted]
        if not names:
            print("None of those names is a card. Cards:", ", ".join(cards))
            return 1

    cfg = load_config(args.config)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    saved = load_shapes(args.out) if os.path.exists(args.out) else []
    counts = Counter(l for l, _ in saved)
    skipped = set()
    print(f"Resuming with {len(saved)} drawings." if saved else "Starting a new sigil file.")

    art, guesser = CardArt(), SigilRecognizer()
    tracker = HandTracker(cfg["model_path"], max_hands=cfg["max_hands"])
    camera = Camera(args.camera if args.camera is not None else cfg["camera_index"], cfg["resolution"], cfg["fps"],
                    cfg["mirror"], cfg["fit"])
    det, cap = GestureDetector(GestureConfig.from_dict(cfg.get("gestures"))), StrokeCapture()
    det.start_ready()
    last_stroke, last_text, last_ok, last_time = None, "", True, 0.0
    start = time.time()
    try:
        while True:
            todo = [n for n in names if counts[n] < args.per_sigil and n not in skipped]
            frame = camera.read()
            if frame is None:
                break
            t_ms = (time.time() - start) * 1000.0
            hands = tracker.detect(frame, t_ms)
            state = det.update(t_ms, hands[0] if hands else None)
            if det.phase == LOCKED:
                det.start_ready()
            stroke = cap.update(t_ms, state)
            if stroke and todo:
                name = todo[0]
                saved.append((name, list(stroke.points)))
                counts[name] += 1
                write_all(args.out, saved)
                guess = guesser.classify(stroke.points)
                last_ok = guess.best_label == name
                last_stroke, last_time = stroke, time.time()
                last_text = (f"saved. The built-in shapes read it as {guess.best_label} ({guess.score:.2f})"
                             + ("" if last_ok else "  - press u if you drew it wrong"))

            for h in hands:
                draw_hand(frame, h)
            draw_trail(frame, cap.live_points)
            if last_stroke and time.time() - last_time < 1.5:
                draw_trail(frame, last_stroke.points, color=(120, 255, 120) if last_ok else (90, 90, 235),
                           alpha=1.0 - (time.time() - last_time) / 1.5)
            canvas = np.zeros((H, W, 3), np.uint8)
            canvas[:, :CAM_W] = cv2.resize(frame, (CAM_W, H))
            canvas[:, CAM_W:] = PANEL
            shade(canvas, 0, 0, CAM_W, 70)
            done = sum(min(counts[n], args.per_sigil) for n in names)
            if todo:
                name = todo[0]
                text(canvas, f"Draw {name.upper()}   ({counts[name] + 1} of {args.per_sigil})", (CAM_W // 2, 32), 0.9, GOLD, 2, center=True)
                text(canvas, "pinch, draw the shape on the card, release", (CAM_W // 2, 58), 0.55, WHITE, 1, center=True)
                paste(canvas, art.get(cards[name], 280, 396), CAM_W + 20, 70)
            else:
                text(canvas, "All done! Press q.", (CAM_W // 2, 40), 1.0, GREEN, 2, center=True)
            text(canvas, f"{done} of {len(names) * args.per_sigil} drawings", (CAM_W + 20, 40), 0.65, WHITE, 2)
            text(canvas, f"sigil {len(names) - len(todo) + (1 if todo else 0)} of {len(names)}", (CAM_W + 20, 500), 0.6, GREY)
            for i, s in enumerate(("u  undo last drawing", "n  skip this sigil", "q  quit (saved as you go)")):
                text(canvas, s, (CAM_W + 20, 550 + i * 28), 0.55, WHITE)
            if last_text and time.time() - last_time < 4:
                shade(canvas, 0, H - 44, CAM_W, H)
                text(canvas, last_text, (CAM_W // 2, H - 16), 0.55, GREEN if last_ok else RED, 1, center=True)
            cv2.imshow(WINDOW, canvas)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break
            if key == ord("u") and saved:
                name, _ = saved.pop()
                counts[name] -= 1
                skipped.discard(name)
                write_all(args.out, saved)
                last_text, last_stroke, last_ok, last_time = f"removed one {name}", None, True, time.time()
            if key == ord("n") and todo:
                skipped.add(todo[0])
    finally:
        camera.release()
        tracker.close()
        cv2.destroyAllWindows()
    print(f"{len(saved)} drawings in {args.out}")
    print("Now run:  python -m recognition.evaluate_sigils " + args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
