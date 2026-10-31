#!/usr/bin/env bash
# Sets up the Python 3.12 environment for Sigyl on a Mac and checks the camera.
# Usage:  bash scripts/setup_mac.sh
set -euo pipefail
cd "$(dirname "$0")/.."

PY="$(command -v python3.12 || true)"
if [ -z "$PY" ] && [ -x /opt/homebrew/bin/python3.12 ]; then PY=/opt/homebrew/bin/python3.12; fi
if [ -z "$PY" ]; then
  echo "python3.12 was not found. Install it with:  brew install python@3.12"
  exit 1
fi

echo "Using $($PY --version) at $PY"
"$PY" -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install opencv-python numpy mediapipe pyyaml pytest

echo
echo "Downloading the MediaPipe hand landmarker model (about 8 MB)..."
mkdir -p models
if [ ! -f models/hand_landmarker.task ]; then
  curl -L --fail -o models/hand_landmarker.task \
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
fi

echo
echo "Installed versions:"
python -m pip freeze | grep -iE '^(opencv-python|numpy|mediapipe|pyyaml|pytest)==' | tee requirements.lock.txt
echo
echo "Running the environment and camera check. If macOS asks, allow camera access for Terminal."
echo "Start the OBS Virtual Camera first if you want it to show up."
python -m tracking.check_env
echo
echo "Done. Next time, activate the environment with:  source .venv/bin/activate"
