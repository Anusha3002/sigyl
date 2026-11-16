"""Play Sigyl against the bot.

  python -m ui.play                 camera + gestures
  It also learns from your own sigil drawings in data/sigils.jsonl when that file exists
  (record them with python -m tracking.record_sigils).

Gestures: zoom = start, pinch and draw a card's sigil = pick it, fist = lock it in.
Keys (for testing without gestures): s = start, 1 2 3 = pick that card, space = lock in,
r = back to the start screen, q = quit.
"""
import argparse
import json
import os
import time

import cv2

from game.session import DRAFT, RESULT, REVEAL, WAITING, MatchSession
from recognition.dollar1 import load_shapes
from recognition.sigils import SigilRecognizer
from tracking.camera import Camera
from tracking.config import load_config
from tracking.draw import draw_hand, draw_trail
from tracking.gestures import LOCKED, READY, GestureConfig, GestureDetector
from tracking.hands import HandTracker
from tracking.strokes import StrokeCapture
from .screen import CardArt, render

WINDOW = "Sigyl"
MESSAGE_SECONDS = 2.5


class Game:
    """Connects gestures and strokes to the match. No camera or window in here, so it can be tested."""

    def __init__(self, session: MatchSession, recognizer: SigilRecognizer, gesture_cfg: GestureConfig = None):
        self.session = session
        self.rec = recognizer
        self.det = GestureDetector(gesture_cfg)
        self.cap = StrokeCapture()
        self.message, self.detail, self._message_at = "", "", -1e9
        self.last_stroke, self.last_stroke_at, self.last_ok = None, -1e9, False
        self.stroke_report = None   # filled for one frame when a stroke was just judged (for the timing log)
        self._was_phase = session.phase

    def say(self, now: float, message: str, detail: str = "") -> None:
        self.message, self.detail, self._message_at = message, detail, now

    def current_message(self, now: float):
        return (self.message, self.detail) if now - self._message_at < MESSAGE_SECONDS else ("", "")

    # ---- inputs -----------------------------------------------------------
    def start(self, now: float) -> None:
        if self.session.start(now):
            if self.det.phase != READY:      # started with the keyboard: skip the zoom
                self.det.start_ready()
            self.cap.reset()
            self.say(now, "Draw the sigil of the card you want")

    def pick(self, now: float, index: int) -> None:
        if self.session.select(index):
            self.say(now, f"{self.session.offer[index].label} picked", "Fist to lock in, or draw another sigil to change")

    def lock(self, now: float) -> None:
        if self.session.phase != DRAFT:
            return
        if self.session.selected is None:
            self.say(now, "Draw a sigil first")
            return
        name = self.session.offer[self.session.selected].label
        self.session.lock(now)
        self.say(now, f"{name} locked in")

    def on_stroke(self, now: float, points) -> None:
        if self.session.phase != DRAFT:
            return
        offer = self.session.offer
        t0 = time.perf_counter()
        res = self.rec.classify(points, [c.title for c in offer])
        self.stroke_report = {"recognize_ms": round((time.perf_counter() - t0) * 1000.0, 2), "label": res.label,
                              "best": res.best_label, "score": round(res.score, 3), "offer": [c.title for c in offer]}
        self.last_stroke, self.last_stroke_at, self.last_ok = points, now, res.label is not None
        if res.label is None:
            self.say(now, "Not recognized, try again", f"closest: {res.best_label} ({res.score:.2f})" if res.best_label else "")
        else:
            self.pick(now, [c.title for c in offer].index(res.label))
            self.detail += f"   ({res.score:.2f})"

    def update(self, now: float, t_ms: float, hand) -> None:
        """Call once per frame with the tracked hand (or None)."""
        self.stroke_report = None
        state = self.det.update(t_ms, hand)
        stroke = self.cap.update(t_ms, state)
        if "start" in state.events:
            self.start(now)
        if stroke:
            self.on_stroke(now, stroke.points)
            if self.stroke_report is not None:
                self.stroke_report["drawn_ms"] = stroke.t_last_point
                self.stroke_report["points"] = len(stroke.points)
        if "lock" in state.events:
            self.lock(now)
        if self.det.phase == LOCKED and self.session.phase == DRAFT:
            self.det.start_ready()   # ready for the next pick
            self.cap.reset()
        self.session.tick(now)
        if self.session.phase == RESULT and self._was_phase != RESULT:
            self.det.reset()         # wait for a zoom to play again
            self.cap.reset()
        self._was_phase = self.session.phase


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--camera", type=int)
    ap.add_argument("--shapes", default="data/sigils.jsonl", help="recorded sigil drawings to learn from (used if the file exists)")
    ap.add_argument("--seconds", type=float, default=25.0, help="time per pick")
    ap.add_argument("--log-timing", metavar="FILE", help="write per-frame timings to FILE (for evaluation.report)")
    args = ap.parse_args()

    cfg = load_config(args.config)
    rec = SigilRecognizer()
    if args.shapes and os.path.exists(args.shapes):
        known = set(rec.names())
        for label, pts in load_shapes(args.shapes):
            if label in known:
                rec.add_template(label, pts)
        print(f"Learned from your drawings in {args.shapes}")
    game = Game(MatchSession(pick_seconds=args.seconds), rec, GestureConfig.from_dict(cfg.get("gestures")))
    art = CardArt()
    tracker = HandTracker(cfg["model_path"], max_hands=cfg["max_hands"])
    camera = Camera(args.camera if args.camera is not None else cfg["camera_index"], cfg["resolution"], cfg["fps"],
                    cfg["mirror"], cfg["fit"])
    log = open(args.log_timing, "w", encoding="utf-8") if args.log_timing else None
    if log:
        log.write(json.dumps({"header": {"resolution": list(cfg["resolution"]), "fps_target": cfg["fps"],
                                         "templates": sum(len(v) for v in rec._templates.values())}}) + "\n")
    start = time.time()
    try:
        while True:
            t_loop = time.perf_counter()
            frame = camera.read()
            if frame is None:
                break
            t_cam = time.perf_counter()
            now = time.time() - start
            hands = tracker.detect(frame, now * 1000.0)
            t_det = time.perf_counter()
            game.update(now, now * 1000.0, hands[0] if hands else None)
            t_upd = time.perf_counter()
            report = game.stroke_report

            if game.session.phase in (WAITING, DRAFT):
                for h in hands:
                    draw_hand(frame, h)
                draw_trail(frame, game.cap.live_points)
                if game.last_stroke and now - game.last_stroke_at < 1.5:
                    draw_trail(frame, game.last_stroke, color=(120, 255, 120) if game.last_ok else (90, 90, 235),
                               alpha=1.0 - (now - game.last_stroke_at) / 1.5)
            message, detail = game.current_message(now)
            cv2.imshow(WINDOW, render(frame, game.session, now, art, message, detail))
            key = cv2.waitKey(1) & 0xFF
            if log:
                t_end = time.perf_counter()
                log.write(json.dumps({"t": round(now, 3), "camera_ms": round((t_cam - t_loop) * 1e3, 2),
                                      "detect_ms": round((t_det - t_cam) * 1e3, 2), "game_ms": round((t_upd - t_det) * 1e3, 2),
                                      "draw_ms": round((t_end - t_upd) * 1e3, 2), "hand": bool(hands),
                                      "phase": game.session.phase}) + "\n")
                if report:
                    # from the moment the hand finished the shape to this frame being on screen
                    report["latency_ms"] = round((time.time() - start) * 1000.0 - report.pop("drawn_ms"), 1)
                    log.write(json.dumps({"t": round(now, 3), "stroke": report}) + "\n")
            if key in (ord("q"), 27):
                break
            if key == ord("s"):
                game.start(now)
            elif key in (ord("1"), ord("2"), ord("3")):
                game.pick(now, key - ord("1"))
            elif key in (32, 13):
                game.lock(now)
            elif key == ord("r"):
                game = Game(MatchSession(pick_seconds=args.seconds), rec, GestureConfig.from_dict(cfg.get("gestures")))
    finally:
        if log:
            log.close()
            print(f"Timing saved to {args.log_timing}. Summarize with:  python -m evaluation.report {args.log_timing}")
        camera.release()
        tracker.close()
        cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
