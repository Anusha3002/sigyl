import pytest

pytest.importorskip("yaml")

from tracking.config import DEFAULTS, load_config


def test_defaults_when_file_missing(tmp_path):
    cfg = load_config(str(tmp_path / "nope.yaml"))
    assert cfg["resolution"] == (640, 480) and cfg["camera_index"] == 0 and cfg["mirror"] is True


def test_file_overrides_defaults(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("camera_index: 2\nresolution: [320, 240]\nmax_hands: 2\n")
    cfg = load_config(str(p))
    assert cfg["camera_index"] == 2 and cfg["resolution"] == (320, 240) and cfg["max_hands"] == 2
    assert cfg["fps"] == DEFAULTS["fps"]


def test_repo_config_file_loads():
    cfg = load_config("config.yaml")
    assert cfg["resolution"] == (640, 480) and cfg["model_path"].endswith("hand_landmarker.task")
