"""Summarize a timing log from the game.

  python -m ui.play --log-timing timing.jsonl      play a match or two, then quit with q
  python -m evaluation.report timing.jsonl

Prints frame rate, how long each stage of a frame takes, and the delay from finishing a sigil
to the result being on screen.
"""
import argparse
import json
from typing import Dict, List


def pct(values: List[float], p: float) -> float:
    """p-th percentile (0..100), nearest rank."""
    v = sorted(values)
    return v[min(len(v) - 1, max(0, int(round(p / 100.0 * (len(v) - 1)))))]


def load(path: str):
    header, frames, strokes = {}, [], []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            if "header" in row:
                header = row["header"]
            elif "stroke" in row:
                strokes.append(row["stroke"])
            else:
                frames.append(row)
    return header, frames, strokes


def summarize(frames: List[Dict], strokes: List[Dict]) -> Dict:
    out: Dict = {"frames": len(frames), "strokes": len(strokes)}
    if len(frames) > 1:
        gaps = [(b["t"] - a["t"]) * 1000.0 for a, b in zip(frames, frames[1:]) if b["t"] > a["t"]]
        out["seconds"] = frames[-1]["t"] - frames[0]["t"]
        out["fps_mean"] = (len(frames) - 1) / out["seconds"] if out["seconds"] > 0 else 0.0
        out["frame_ms"] = {"median": pct(gaps, 50), "p95": pct(gaps, 95), "worst": max(gaps)}
        out["slow_frames_pct"] = 100.0 * sum(1 for g in gaps if g > 50.0) / len(gaps)   # slower than 20 fps
        for key in ("camera_ms", "detect_ms", "game_ms", "draw_ms"):
            vals = [f[key] for f in frames]
            out[key] = {"median": pct(vals, 50), "p95": pct(vals, 95)}
        out["hand_seen_pct"] = 100.0 * sum(1 for f in frames if f["hand"]) / len(frames)
    if strokes:
        lat = [s["latency_ms"] for s in strokes]
        recog = [s["recognize_ms"] for s in strokes]
        out["latency_ms"] = {"median": pct(lat, 50), "p95": pct(lat, 95), "worst": max(lat), "under_200_pct": 100.0 * sum(1 for x in lat if x < 200) / len(lat)}
        out["recognize_ms"] = {"median": pct(recog, 50), "worst": max(recog)}
        out["recognized_pct"] = 100.0 * sum(1 for s in strokes if s["label"]) / len(strokes)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    args = ap.parse_args()
    header, frames, strokes = load(args.file)
    s = summarize(frames, strokes)
    print(f"Settings: {header}")
    if "fps_mean" not in s:
        print("Not enough frames in this log.")
        return 1
    print(f"\n{s['frames']} frames over {s['seconds']:.0f} s")
    print(f"Frame rate:        {s['fps_mean']:.1f} fps average")
    print(f"Time per frame:    median {s['frame_ms']['median']:.0f} ms, 95% under {s['frame_ms']['p95']:.0f} ms, worst {s['frame_ms']['worst']:.0f} ms")
    print(f"Frames slower than 20 fps: {s['slow_frames_pct']:.1f}%")
    print(f"Hand in view:      {s['hand_seen_pct']:.0f}% of frames")
    print("\nWhere a frame's time goes (median / 95%):")
    for key, label in (("camera_ms", "waiting for the camera"), ("detect_ms", "hand tracking (MediaPipe)"),
                       ("game_ms", "gestures, strokes, sigil matching, rules"), ("draw_ms", "drawing the screen")):
        print(f"  {label:<42} {s[key]['median']:6.1f} ms / {s[key]['p95']:6.1f} ms")
    if "latency_ms" in s:
        l = s["latency_ms"]
        print(f"\n{s['strokes']} sigils drawn; {s['recognized_pct']:.0f}% picked a card (the rest were refused)")
        print(f"Fingers start to open -> result on screen: median {l['median']:.0f} ms, 95% under {l['p95']:.0f} ms, worst {l['worst']:.0f} ms")
        print(f"  under the 200 ms target: {l['under_200_pct']:.0f}% of sigils")
        print(f"  of which matching the sigil itself takes: median {s['recognize_ms']['median']:.1f} ms, worst {s['recognize_ms']['worst']:.1f} ms")
        print("  (the rest: the fingers opening, the short wait that confirms you really let go, and one frame)")
    else:
        print("\nNo sigils were drawn in this log.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
