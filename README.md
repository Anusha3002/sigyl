# Arcane

Gesture-controlled, turn-based spellcasting game. NYU Computer Vision, Fall 2026.
Authors: Anusha and Anjali Paliyam.

Pipeline: camera -> MediaPipe Hands -> stroke capture -> recognizer -> spell engine -> effects -> display.

Rule: `game/` never imports camera, OpenCV, or MediaPipe code, so it runs unchanged on a laptop and a Raspberry Pi 5.

Build order: game engine + tests -> webcam/pinch-to-ink -> $1 recognizer -> connect + effects -> Pi smoke test -> port + evaluation.
