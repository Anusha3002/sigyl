# Sigyl: evaluation results

Last updated Nov 16, 2026. Every number here names what it was measured on. Numbers marked **small sample** should be re-measured before they go in the report.

Setup for all camera measurements: Apple-silicon Mac, webcam (camera 0), 640 x 480 at 30 fps, one player (Anusha), one hand, Python 3.12, MediaPipe 1.2.0 hand landmarker.

## 1. Sigil recognition (the 26 card sigils)

**Data.** 90 drawings by one person, recorded with `python -m tracking.record_sigils`: 3 to 5 of each of the 26 sigils, drawn in the air and captured through the real pipeline (camera, hand tracking, pinch detection, stroke capture). 4 recordings were removed by eye before evaluation because they were fragments or stray strokes, not attempts at the sigil (kept in `data/sigils_raw.jsonl` and `data/sigils_raw2.jsonl`). 3 cut-off Fade recordings were replaced by 2 whole ones taken from a later clip.

**Method.** Leave-one-out: each drawing is matched using the built-in shapes plus all the *other* recordings, never itself. Reproduce with `python -m recognition.evaluate_sigils data/sigils.jsonl`.

**The game's question: which of the 3 cards on offer was drawn?** Averaged over every possible pair of other cards (300 pairs per drawing).

| Templates | Right card | Wrong card | Not recognized |
|---|---|---|---|
| Built-in shapes only (traced by eye from the card designs) | 82.0% | 2.2% | 15.7% |
| Built-in + the player's own recordings | **94.3%** | **0.7%** | 5.0% |

**The harder question: which of all 26?** (Not what the game asks; shown for comparison.)

| Templates | Right | Wrong | Not recognized |
|---|---|---|---|
| Built-in shapes only | 66 / 90 (73%) | 3 | 21 |
| Built-in + the player's own recordings | 79 / 90 (88%) | 3 | 8 |

**Weakest sigils** (among 3 on offer, with the player's recordings): Wisp 70%, Quake 80%, Buckler 80%, Fade 80%, Gate 92%; all others 95% or above. Looking at the drawings, these four vary from one attempt to the next (Wisp from a deep U to a full wave, Quake with 3 or 4 peaks, Buckler coiling either way), so the cause is drawing consistency more than shape similarity.

**Mistakes among all 26** (learned setup): Wisp read as Rake, Fang read as Crush, Bite read as Spear, once each; 8 drawings refused.

**What changed the numbers along the way** (same kind of test each time):

| Step | Right card among 3 |
|---|---|
| Built-in shapes only, first 78 recordings | 77.5% |
| + player's recordings | 88.3% |
| + matching shapes stretched to a common box, 2 fragments removed | 92.1% |
| + more recordings of the weak sigils, 2 stray Gate strokes removed | 94.3% |

**Limits.** One person, one session's worth of drawing style, one camera and room. The thresholds (minimum score 0.72, minimum lead 0.02) were chosen before this data and not tuned on it; loosening them raises "right" to about 96% but doubles wrong-card picks. A simulation with made-up wobble had predicted 96% for the built-in shapes; the real figure was 77.5%, so simulated numbers are not reported here.

## 2. Earlier recognizer: circle, line, V ($1 unistroke)

30 drawings by one person (10 each), leave-one-out on recordings only: **29 / 30 (97%)**. Built-in templates alone: 28 / 30 (93%). The one miss was a V with an extra hook, refused rather than misread. Reproduce with `python -m recognition.evaluate data/shapes.jsonl --defaults`. This recognizer is rotation-free; the game now uses the orientation-aware one in section 1.

## 3. Speed

Measured during real matches with `python -m ui.play --log-timing FILE`, summarized by `python -m evaluation.report FILE`.

| Measure | Run A (391 s, two matches) | Run B (98 s, one match) |
|---|---|---|
| Frame rate | 29.6 fps | 29.1 fps |
| Median time per frame | 33 ms | 33 ms |
| Frames slower than 20 fps | 2.0% | 3.0% |
| Waiting for the camera (median) | 9.7 ms | 10.9 ms |
| Hand tracking, MediaPipe (median / 95%) | 6.0 / 9.2 ms | 5.4 / 9.0 ms |
| Gestures, strokes, rules (median) | under 0.1 ms | under 0.1 ms |
| Drawing the screen (median) | 17.0 ms | 16.6 ms |
| Matching one sigil against the 3 on offer (median / worst) | 5.0 / 17.1 ms | 1.6 / 9.5 ms |

The frame rate is capped by the camera (30 fps). The work per frame is about 23 ms (tracking plus drawing), so there is headroom on the Mac. Drawing the screen is the largest share; that is the first place to look when porting to the Raspberry Pi 5, which has not been tested.

## 4. Delay from finishing a sigil to seeing the result

Defined as: from the last frame where the pinch was still tight (just before the fingers begin to open) to the frame showing the result being on screen. Target from the proposal: under 200 ms.

| | Before | After |
|---|---|---|
| Sigils measured | 17 | 5 (**small sample**) |
| Median | 260 ms | 158 ms |
| 95th percentile | 324 ms | 325 ms |
| Worst | 594 ms | 325 ms |
| Under 200 ms | 1 of 17 | 4 of 5 |

Two things changed between the columns. (1) The clock: "before" started two frames early (at the trimmed end of the stroke), overstating the delay by about 67 ms. (2) The release wait was shortened from 80 ms to 50 ms; replaying four recorded clips at both settings split no stroke. So about 67 ms of the improvement is measurement and about 30 ms is real.

A sigil takes about 350 ms instead when the tracker reads the opening fingers as "slightly loose" rather than "clearly open". That wait is deliberate: it stops a brief misreading from cutting a drawing in two (see section 5).

## 5. Gesture detection

Checked on recorded landmark clips of one person, replayed through the detector (`python -m tracking.replay FILE`), and kept as regression tests in `tests/data/`:

- **Zoom to start:** fires once inside the marked zoom segment of the zoom-and-draw clip, and never falsely in it.
- **Fist to lock:** fires about 500 ms after a held fist in the fist clip. A held pinch with curled fingers no longer counts as a fist (the first rule did; the fix uses where the thumb sits: 0.43 to 0.57 palm sizes from the pinky knuckle in a fist, 0.93 to 1.06 in a pinch).
- **Pinch to draw:** a two-ring drawing was being cut in two when the tracker read a held pinch as 0.64 to 0.71 palm sizes for about 100 ms. A loose reading must now last 350 ms to end a stroke; the clip that showed the fault is a regression test.

There is no per-gesture accuracy figure yet: the clips hold only a handful of each gesture.

## 6. Game balance (simulation, not real play)

4,000 bot-vs-bot matches per row, `python -m game.simulate`, current rules (start 100 aura, both attacks land, defense blocks half).

| Match-up | Player 1 wins | Player 2 wins | Draw | Knockout |
|---|---|---|---|---|
| Smarter bot vs smarter bot | 45.9% | 45.2% | 8.9% | 13.6% |
| Smarter bot vs random bot | 66.9% | 25.0% | 8.1% | 11.3% |
| Random bot vs random bot | 43.9% | 44.9% | 11.2% | 6.1% |

Under the original rules (attacks cancel to the difference, defense blocks in full) 57% of slots changed nothing and 23% of matches were draws; now about 34% of slots change nothing.

## 7. Software tests

249 automated tests pass (`python -m pytest -q`), covering the rules, the draft, the bots, the recognizers, gesture detection on made-up and recorded hands, and a full match played by simulated gestures.

## Not measured yet

- More than one person. Everything above is one player.
- Per-gesture accuracy (zoom, pinch, fist) on a labeled set.
- The delay in section 4 on a larger sample.
- Different lighting, backgrounds, distances from the camera, or the left hand.
- The Raspberry Pi 5.
- A learned model or DTW as a comparison against the template matcher (listed in the proposal).
