"""Loads config.yaml with sensible defaults."""
import os
from typing import Any, Dict

DEFAULTS: Dict[str, Any] = {
    "camera_index": 0,
    "resolution": [640, 480],
    "fps": 30,
    "mirror": True,
    "fit": "crop",
    "max_hands": 1,
    "model_path": "models/hand_landmarker.task",
    "effect_quality": "medium",
}


def load_config(path: str = "config.yaml") -> Dict[str, Any]:
    cfg = dict(DEFAULTS)
    if os.path.exists(path):
        import yaml

        with open(path, "r", encoding="utf-8") as f:
            cfg.update(yaml.safe_load(f) or {})
    cfg["resolution"] = tuple(int(v) for v in cfg["resolution"])
    return cfg
