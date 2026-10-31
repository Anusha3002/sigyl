"""Environment and camera check:  python -m tracking.check_env [--no-camera] [--max-index N]

Prints library versions, then tries camera indexes 0..N, saving one snapshot per
working camera into ./camera_check/ so you can see which index is which.
"""
import argparse
import os
import platform
import sys


def check_model() -> bool:
    """Load the hand landmarker model and run it once on a blank frame."""
    model = os.path.join("models", "hand_landmarker.task")
    if not os.path.exists(model):
        print("  hand model  MISSING: run scripts/setup_mac.sh (it downloads models/hand_landmarker.task)")
        return False
    try:
        import mediapipe as mp
        import numpy as np
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision

        options = vision.HandLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=model),
            running_mode=vision.RunningMode.IMAGE,
            num_hands=2,
        )
        landmarker = vision.HandLandmarker.create_from_options(options)
        blank = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.zeros((480, 640, 3), dtype=np.uint8))
        landmarker.detect(blank)
        getattr(landmarker, "close", lambda: None)()
        print("  hand model  loads and runs: OK")
        return True
    except Exception as err:
        print(f"  hand model  FAILED to run: {err}")
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-camera", action="store_true")
    ap.add_argument("--max-index", type=int, default=4)
    args = ap.parse_args()

    print(f"Python {platform.python_version()} on {platform.machine()} ({platform.system()})")
    ok = True
    for name in ("cv2", "numpy", "mediapipe", "yaml"):
        try:
            mod = __import__(name)
            print(f"  {name:<10} {getattr(mod, '__version__', 'installed')}")
        except Exception as err:  # report every missing library, not just the first
            ok = False
            print(f"  {name:<10} MISSING ({err})")
    if not ok:
        return 1
    if not check_model():
        return 1
    if args.no_camera:
        return 0

    import cv2

    os.makedirs("camera_check", exist_ok=True)
    backend = cv2.CAP_AVFOUNDATION if sys.platform == "darwin" else cv2.CAP_ANY
    print("Cameras (macOS may ask permission for Terminal the first time):")
    found = 0
    for i in range(args.max_index + 1):
        cap = cv2.VideoCapture(i, backend)
        if not cap.isOpened():
            print(f"  index {i}: not available")
            cap.release()
            continue
        got, frame = False, None
        for _ in range(15):  # let exposure settle
            got, frame = cap.read()
        if got:
            h, w = frame.shape[:2]
            path = os.path.join("camera_check", f"camera_{i}.jpg")
            cv2.imwrite(path, frame)
            print(f"  index {i}: {w}x{h}, snapshot saved to {path}")
            found += 1
        else:
            print(f"  index {i}: opened but returned no frame")
        cap.release()
    if not found:
        print()
        print("No camera returned a frame. Most likely macOS has not given this terminal app camera access:")
        print("  1. Open System Settings > Privacy & Security > Camera and switch on your terminal app")
        print("     (Terminal, iTerm, or the editor you run this from).")
        print("  2. If it is not listed, run:  tccutil reset Camera com.apple.Terminal")
        print("     then run this check again and click Allow when the prompt appears.")
        print("  3. Quit the terminal app completely (Cmd+Q), reopen it, and rerun this check.")
        print("Also make sure OBS is open and Start Virtual Camera is on.")
        return 2
    print("Open the snapshots to see which index is the OBS Virtual Camera.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
