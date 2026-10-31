"""Live hand view.

  python -m tracking.demo                          live camera, press q or Esc to quit
  python -m tracking.demo --save-landmarks a.jsonl records the landmarks of every frame;
                                                   press a key to label the next gesture
  python -m tracking.demo --video clip.mp4 --save-landmarks a.jsonl --no-window
                                                   runs the tracker on a recorded clip
"""
import argparse
import time

import cv2

from .camera import Camera, fit_frame
from .config import load_config
from .draw import draw_hand, put_lines
from .hands import HandTracker
from .landmarks import LandmarkWriter

WINDOW = "Sigyl - hand view (q to quit)"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--camera", type=int, help="camera index (overrides config.yaml)")
    ap.add_argument("--video", help="run on a recorded video file instead of a camera")
    ap.add_argument("--save-landmarks", metavar="FILE", help="write landmarks of every frame to FILE (JSON lines)")
    ap.add_argument("--seconds", type=float, help="stop after this many seconds")
    ap.add_argument("--no-window", action="store_true", help="do not open a window")
    args = ap.parse_args()

    cfg = load_config(args.config)
    size = cfg["resolution"]
    tracker = HandTracker(cfg["model_path"], max_hands=cfg["max_hands"])

    video = None
    camera = None
    if args.video:
        video = cv2.VideoCapture(args.video)
        if not video.isOpened():
            print(f"Could not open video {args.video}")
            return 1
        video_fps = video.get(cv2.CAP_PROP_FPS) or cfg["fps"]
        source = f"video {args.video}"
    else:
        camera = Camera(args.camera if args.camera is not None else cfg["camera_index"],
                        size, cfg["fps"], cfg["mirror"], cfg["fit"])
        source = f"camera {args.camera if args.camera is not None else cfg['camera_index']} (native {camera.native_size[0]}x{camera.native_size[1]})"
    print(f"Source: {source}. Working size {size[0]}x{size[1]}.")

    writer = None
    if args.save_landmarks:
        writer = LandmarkWriter(args.save_landmarks, {"size": list(size), "source": source, "mirror": cfg["mirror"]})

    start = time.time()
    frame_no = 0
    fps_smooth = 0.0
    last = start
    detect_ms = 0.0
    last_marker = "-"
    try:
        while True:
            if video is not None:
                ok, frame = video.read()
                if not ok:
                    break
                frame = fit_frame(frame, size, cfg["fit"])
                if cfg["mirror"]:
                    frame = cv2.flip(frame, 1)
                t_ms = frame_no / video_fps * 1000.0
            else:
                frame = camera.read()
                if frame is None:
                    print("Camera returned no frame.")
                    break
                t_ms = (time.time() - start) * 1000.0

            t0 = time.time()
            hands = tracker.detect(frame, t_ms)
            detect_ms = 0.9 * detect_ms + 0.1 * (time.time() - t0) * 1000.0 if frame_no else (time.time() - t0) * 1000.0
            if writer:
                writer.write(t_ms, hands)

            now = time.time()
            inst = 1.0 / max(now - last, 1e-6)
            fps_smooth = inst if frame_no == 0 else 0.9 * fps_smooth + 0.1 * inst
            last = now
            frame_no += 1

            if not args.no_window:
                for h in hands:
                    draw_hand(frame, h)
                put_lines(frame, [
                    f"FPS {fps_smooth:4.1f}   detect {detect_ms:4.1f} ms",
                    f"hands {len(hands)}" + (f"   {hands[0].label} ({hands[0].score:.2f})" if hands else ""),
                ] + ([f"marker: {last_marker}   (press a key to label what you do next)"] if writer else []))
                cv2.imshow(WINDOW, frame)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), 27):
                    break
                if 32 < key < 127 and writer:  # any other key: label what you are about to do
                    last_marker = chr(key)
                    writer.mark(t_ms, last_marker)
            if args.seconds and time.time() - start >= args.seconds:
                break
    finally:
        if writer:
            writer.close()
        if camera:
            camera.release()
        if video:
            video.release()
        tracker.close()
        cv2.destroyAllWindows()
    elapsed = time.time() - start
    print(f"{frame_no} frames in {elapsed:.1f}s ({frame_no / max(elapsed, 1e-6):.1f} fps average).")
    if writer:
        print(f"Landmarks saved to {args.save_landmarks}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
