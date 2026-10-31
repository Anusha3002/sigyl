from types import SimpleNamespace as NS

from tracking.landmarks import (
    HAND_CONNECTIONS, INDEX_TIP, THUMB_TIP, Hand, LandmarkWriter, load_landmarks, parse_result,
)


def fake_result(n_hands=1, label="Right", score=0.97):
    hands = [[NS(x=i / 100, y=i / 200, z=-i / 1000) for i in range(21)] for _ in range(n_hands)]
    handed = [[NS(category_name=label, score=score)] for _ in range(n_hands)]
    return NS(hand_landmarks=hands, handedness=handed)


def test_parse_result_reads_points_label_and_score():
    hands = parse_result(fake_result())
    assert len(hands) == 1
    h = hands[0]
    assert h.label == "Right" and abs(h.score - 0.97) < 1e-9
    assert len(h.points) == 21
    assert h.points[10] == (0.10, 0.05, -0.01)


def test_parse_result_with_no_hands_or_missing_fields():
    assert parse_result(NS(hand_landmarks=[], handedness=[])) == []
    assert parse_result(NS()) == []
    h = parse_result(NS(hand_landmarks=fake_result().hand_landmarks, handedness=[]))[0]
    assert h.label == "Unknown"


def test_two_hands_are_both_returned():
    assert len(parse_result(fake_result(2))) == 2


def test_pixels_scale_to_the_frame():
    h = parse_result(fake_result())[0]
    px = h.pixels(640, 480)
    assert px[0] == (0, 0) and px[20] == (128, 48)


def test_xy_helper_and_landmark_indexes():
    h = parse_result(fake_result())[0]
    assert h.xy(THUMB_TIP) == (0.04, 0.02)
    assert (THUMB_TIP, INDEX_TIP) == (4, 8)


def test_connections_cover_all_21_points():
    used = {i for pair in HAND_CONNECTIONS for i in pair}
    assert used == set(range(21))
    assert len(HAND_CONNECTIONS) == 21


def test_landmark_file_roundtrip(tmp_path):
    path = str(tmp_path / "clip.jsonl")
    hand = parse_result(fake_result())[0]
    with LandmarkWriter(path, {"size": [640, 480]}) as w:
        w.write(0.0, [hand])
        w.write(33.3, [])
        w.write(66.6, [hand])
    header, frames = load_landmarks(path)
    assert header["size"] == [640, 480]
    assert [t for t, _ in frames] == [0.0, 33.3, 66.6]
    assert len(frames[0][1]) == 1 and frames[1][1] == []
    got = frames[2][1][0]
    assert got.label == "Right"
    assert all(abs(a - b) < 1e-4 for p, q in zip(got.points, hand.points) for a, b in zip(p, q))
