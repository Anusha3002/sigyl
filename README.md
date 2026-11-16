# SIGYL

A gesture-controlled, turn-based card game. You pick cards by drawing their sigils in the air in front of a webcam, then your five cards face the bot's, slot by slot.

NYU Computer Vision, Fall 2026. Team Arcane: Anusha C and Anjali Paliyam.

## How it works

camera -> hand landmarks (MediaPipe) -> gestures -> stroke capture -> sigil recognizer -> game engine -> game screen

- **Zoom** (pinch, then spread your fingers wide) starts a match.
- **Pinch and draw** a card's sigil to pick that card. Draw a different sigil to change your mind.
- **Fist** (hold about half a second) locks the pick in.

## Set up (Mac)

Needs Python 3.12 and a webcam.

```
bash scripts/setup_mac.sh
source .venv/bin/activate
```

The script creates `.venv`, installs the packages, downloads the hand model, and checks your cameras. If the camera is "not authorized", allow your terminal under System Settings > Privacy & Security > Camera and run it again. Set `camera_index` in `config.yaml` to the camera you want.

## Play

```
python -m ui.play
```

Keys, for testing without gestures: `s` start, `1` `2` `3` pick a card, `space` lock in, `r` back to the start screen, `q` quit.

## Rules

- Each player has their own deck of 26 cards. Every card has a name, a type, and its own sigil.
- A match is five picks. Each pick shows three cards and gives you 25 seconds. If time runs out, the card you had picked is taken; with nothing picked, the slot gets a Fizzle, which does nothing.
- The first two picks offer only Attack and Defense cards. Special cards can appear from the third pick.
- Both players start at 100 aura (also the maximum). After the draft, slot 1 faces slot 1, and so on. A player at 0 aura is knocked out and the match ends there. Otherwise the higher aura after five slots wins; equal aura is a draw.

| Type | Cards | What it does |
|---|---|---|
| Attack | 10 (values 10 to 50) | Takes that much aura from the opponent. Two attacks in the same slot both land. |
| Defense | 7 (values 10 to 50) | Blocks half its value of an attack. |
| Heal | 2 (30, 50) | Restores that much aura. |
| Mirror | 2 | Reflects an attack back at the attacker. |
| Vanish | 2 | Cancels both cards in the slot. |
| Surge | 2 | Adds 20 to your attack in the next slot. |
| Charm | 1 | Steals 20 aura; cannot be blocked or reflected. |

Full rules and their history: `docs/GAME_SPEC.md`.

## What is in the repo

| Folder | What it holds |
|---|---|
| `game/` | The rules: cards, draft, slot resolution, bot, match session. Standard library only; never imports camera, OpenCV or MediaPipe, so it runs anywhere. |
| `tracking/` | Camera, hand landmarks, gesture detection, stroke capture, and small demo tools. |
| `recognition/` | The sigil recognizer (`sigils.py`) and the earlier $1 recognizer for circle, line and V (`dollar1.py`). |
| `ui/` | The game screen and the play loop. |
| `assets/cards/` | The 26 card images. |
| `data/` | Recorded shape drawings. |
| `tests/` | Unit tests, including two recorded hand clips and a full match played by simulated gestures. |
| `docs/` | Game spec (`GAME_SPEC.md`) and evaluation results (`EVALUATION.md`). |
| `AGENT_LOG.md` | Log of AI assistance: what was generated, what went wrong, how it was checked. |

## Other tools

```
python -m pytest -q                              run the tests
python -m tracking.demo                          live hand view
python -m tracking.sigil_demo                    zoom, draw circle / line / V, fist
python -m tracking.record_sigils                 record your own drawings of the 26 sigils
python -m recognition.evaluate_sigils data/sigils.jsonl   accuracy of the sigil recognizer on them
python -m tracking.record_shapes                 record labeled circle / line / V drawings
python -m recognition.evaluate data/shapes.jsonl leave-one-out accuracy and confusion table
python -m tracking.replay FILE.jsonl             run gesture detection on a recorded landmark file
python -m game.simulate                          bot-vs-bot statistics
python -m ui.play --log-timing timing.jsonl      play while logging speed
python -m evaluation.report timing.jsonl         frame rate, time per stage, drawing-to-result delay
```

## Status

Working: one player against the bot, on a Mac, with one hand.

Known limits:
- Everything has been measured on one player only. With that player's recorded drawings the game picks the right card 94.3% of the time; see `docs/EVALUATION.md`.
- Not built yet: two players, the final visual style, a clip replay mode, and the Raspberry Pi 5 port.
