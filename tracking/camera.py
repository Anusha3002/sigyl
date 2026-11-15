"""Camera input: opens a camera by index, fits frames to the working size, optionally mirrors."""
import sys
from typing import Any, Optional, Tuple

import cv2


class CameraError(RuntimeError):
    pass


def fit_frame(frame, size: Tuple[int, int], mode: str = "crop"):
    """Resize `frame` to `size` (width, height). `crop` trims to the target shape first so the
    hand is not stretched; `stretch` just resizes."""
    w_t, h_t = size
    h, w = frame.shape[:2]
    if (w, h) == (w_t, h_t):
        return frame
    if mode == "crop":
        target = w_t / h_t
        current = w / h
        if current > target:  # too wide: trim the sides
            new_w = int(round(h * target))
            x0 = (w - new_w) // 2
            frame = frame[:, x0:x0 + new_w]
        elif current < target:  # too tall: trim top and bottom
            new_h = int(round(w / target))
            y0 = (h - new_h) // 2
            frame = frame[y0:y0 + new_h, :]
    elif mode != "stretch":
        raise ValueError(f"unknown fit mode {mode!r}")
    return cv2.resize(frame, (w_t, h_t), interpolation=cv2.INTER_AREA)


class Camera:
    def __init__(self, index: int = 0, size: Tuple[int, int] = (640, 480), fps: int = 30,
                 mirror: bool = True, fit: str = "crop", capture: Optional[Any] = None):
        self.size = tuple(size)
        self.mirror = mirror
        self.fit = fit
        if capture is None:
            backend = cv2.CAP_AVFOUNDATION if sys.platform == "darwin" else cv2.CAP_ANY
            capture = cv2.VideoCapture(index, backend)
            if capture.isOpened():
                capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.size[0])
                capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.size[1])
                capture.set(cv2.CAP_PROP_FPS, fps)
        if not capture.isOpened():
            raise CameraError(
                f"Could not open camera index {index}. Run `python -m tracking.check_env`, "
                "check camera permission for your terminal, and set camera_index in config.yaml."
            )
        self.cap = capture
        self.native_size = (
            int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
            int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        )

    def read(self):
        """Next frame at the working size, or None if the camera gave nothing."""
        ok, frame = self.cap.read()
        if not ok or frame is None:
            return None
        frame = fit_frame(frame, self.size, self.fit)
        return cv2.flip(frame, 1) if self.mirror else frame

    def release(self) -> None:
        self.cap.release()
