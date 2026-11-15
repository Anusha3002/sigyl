"""MediaPipe hand landmarker wrapper (Tasks API, video mode)."""
from typing import List

import cv2
import numpy as np

from .landmarks import Hand, parse_result


class HandTracker:
    def __init__(self, model_path: str, max_hands: int = 1, min_detection: float = 0.5,
                 min_presence: float = 0.5, min_tracking: float = 0.5):
        import mediapipe as mp  # imported here so the rest of the package works without it
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision

        self._mp = mp
        options = vision.HandLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=model_path),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=max_hands,
            min_hand_detection_confidence=min_detection,
            min_hand_presence_confidence=min_presence,
            min_tracking_confidence=min_tracking,
        )
        self._landmarker = vision.HandLandmarker.create_from_options(options)
        self._last_ts = -1

    def detect(self, frame_bgr, timestamp_ms: float) -> List[Hand]:
        """Find hands in one BGR frame. Timestamps must increase; we enforce that."""
        ts = max(int(timestamp_ms), self._last_ts + 1)
        self._last_ts = ts
        rgb = np.ascontiguousarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
        image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
        return parse_result(self._landmarker.detect_for_video(image, ts))

    def close(self) -> None:
        self._landmarker.close()
