import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")

from tracking.camera import Camera, CameraError, fit_frame


class FakeCapture:
    def __init__(self, frames, opened=True, size=(1920, 1080)):
        self.frames = list(frames)
        self.opened = opened
        self.size = size
        self.released = False

    def isOpened(self):
        return self.opened

    def read(self):
        if not self.frames:
            return False, None
        return True, self.frames.pop(0)

    def get(self, prop):
        return {cv2.CAP_PROP_FRAME_WIDTH: self.size[0], cv2.CAP_PROP_FRAME_HEIGHT: self.size[1]}.get(prop, 0)

    def release(self):
        self.released = True


def frame(w, h, value=0):
    return np.full((h, w, 3), value, dtype=np.uint8)


def test_fit_frame_noop_when_already_the_right_size():
    f = frame(640, 480)
    assert fit_frame(f, (640, 480)) is f


def test_crop_keeps_the_middle_and_the_target_shape():
    f = frame(1920, 1080)
    f[:, :240] = 10      # left strip that must be cropped away
    f[:, -240:] = 20     # right strip that must be cropped away
    f[:, 240:-240] = 99  # the 1440x1080 middle (4:3)
    out = fit_frame(f, (640, 480), "crop")
    assert out.shape == (480, 640, 3)
    assert out.min() == 99 and out.max() == 99


def test_crop_trims_top_and_bottom_for_tall_frames():
    f = frame(480, 800)
    f[:100] = 5
    f[-100:] = 6
    f[100:-100] = 77  # 480x600 middle is 4:5... target 4:3 -> 480x360
    out = fit_frame(f, (640, 480), "crop")
    assert out.shape == (480, 640, 3)
    assert out.min() == 77 and out.max() == 77


def test_stretch_resizes_without_cropping():
    f = frame(1920, 1080)
    f[:, :240] = 10
    out = fit_frame(f, (640, 480), "stretch")
    assert out.shape == (480, 640, 3)
    assert out[240, 20, 0] == 10   # the left strip is still there (80 px wide after scaling)
    assert out[240, 200, 0] == 0


def test_unknown_fit_mode_rejected():
    with pytest.raises(ValueError):
        fit_frame(frame(100, 100), (50, 40), "zoom")


def test_camera_reads_fits_and_mirrors():
    f = frame(1920, 1080)
    f[:, 240:960] = 50   # left half of the middle crop
    f[:, 960:-240] = 150  # right half of the middle crop
    cam = Camera(capture=FakeCapture([f]), size=(640, 480), mirror=True)
    out = cam.read()
    assert out.shape == (480, 640, 3)
    assert out[240, 10, 0] == 150 and out[240, 630, 0] == 50  # flipped left to right
    assert cam.native_size == (1920, 1080)


def test_camera_without_mirror_keeps_orientation():
    f = frame(640, 480)
    f[:, :320] = 50
    f[:, 320:] = 150
    out = Camera(capture=FakeCapture([f], size=(640, 480)), mirror=False).read()
    assert out[240, 10, 0] == 50 and out[240, 630, 0] == 150


def test_read_returns_none_when_no_frame():
    assert Camera(capture=FakeCapture([])).read() is None


def test_unopened_camera_raises_a_helpful_error():
    with pytest.raises(CameraError, match="check_env"):
        Camera(index=3, capture=FakeCapture([], opened=False))


def test_release_releases_the_capture():
    cap = FakeCapture([])
    Camera(capture=cap).release()
    assert cap.released
