"""Timing report on a made-up log."""
import json

from evaluation.report import load, pct, summarize


def test_percentiles():
    assert pct([1, 2, 3, 4, 5], 50) == 3 and pct([5, 1], 100) == 5 and pct([7], 95) == 7


def test_summary_of_a_made_up_log(tmp_path):
    path = tmp_path / "t.jsonl"
    rows = [{"header": {"resolution": [640, 480]}}]
    for i in range(301):   # 10 seconds at 30 fps
        rows.append({"t": round(i / 30, 3), "camera_ms": 20, "detect_ms": 8, "game_ms": 0.5, "draw_ms": 4, "hand": i % 10 != 0, "phase": "draft"})
    rows.append({"t": 3.0, "stroke": {"recognize_ms": 2.0, "label": "Slash", "best": "Slash", "score": 0.9, "offer": ["Slash", "Ring", "Fang"], "points": 40, "latency_ms": 150.0}})
    rows.append({"t": 6.0, "stroke": {"recognize_ms": 6.0, "label": None, "best": "Ring", "score": 0.5, "offer": ["Slash", "Ring", "Fang"], "points": 30, "latency_ms": 250.0}})
    path.write_text("\n".join(json.dumps(r) for r in rows))
    header, frames, strokes = load(str(path))
    s = summarize(frames, strokes)
    assert header["resolution"] == [640, 480] and s["frames"] == 301 and s["strokes"] == 2
    assert 29.5 < s["fps_mean"] < 30.5 and 32 < s["frame_ms"]["median"] < 35
    assert s["detect_ms"]["median"] == 8 and s["slow_frames_pct"] == 0
    assert s["latency_ms"]["under_200_pct"] == 50 and s["recognized_pct"] == 50
    assert round(s["hand_seen_pct"]) == 90


def test_stroke_remembers_when_its_last_point_was_drawn():
    from tests.test_strokes import circle_path, drawing, run_all
    from tests.test_gestures import zoom_sequence
    det, cap, _ = run_all(zoom_sequence())
    _, _, strokes = run_all(drawing(circle_path()), start=1000, det=det, cap=cap)
    s = strokes[0]
    assert s.t_start < s.t_last_point <= s.t_end
    assert s.t_end - s.t_last_point < 250   # the release wait plus the trimmed points
