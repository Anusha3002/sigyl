# Sigyl: game rules and engine spec (v1)

`game/` is pure Python (standard library only) and never imports camera, OpenCV, MediaPipe or numpy, so the same engine runs on a laptop and a Raspberry Pi 5. All randomness comes from a seeded `random.Random`, so games are reproducible.

## Flow
1. **Start:** the player makes the zoom gesture (thumb and index finger spreading apart, like zooming on a phone). Once per game.
2. **Draft:** 5 picks. Each pick, 3 cards are offered. The player draws the sigil for one of them; holding a fist for about half a second locks it in. Drawing again before the fist replaces the selection.
3. **Lock-in:** after pick 5, one more fist locks all 5 moves and starts the match.
4. **Match:** both sequences are revealed and resolved slot by slot (1 vs 1 ... 5 vs 5).
5. **Result:** an Aura of 0 ends the game at once. Otherwise, after slot 5 the higher Aura wins.

## Aura
Both players start at 100. Aura is clamped to 0..100.

## Cards
Attack, defense and heal values are multiples of 10, capped at 50.

| Type | What it does |
|---|---|
| Attack (10-50) | Deals its value to the opponent |
| Defense (10-50) | Blocks up to its value of an incoming attack |
| Heal (30 or 50) | Restores that much Aura |
| Mirror | Sends the opponent's attack back at them at the same value; you take 0 from it |
| Vanish | Cancels the slot: neither card does anything |
| Charm | Steals 20 Aura: the opponent loses 20, you gain 20 |
| Surge | The attack in your next slot deals 20 more |
| Fizzle (blank) | Does nothing. Locked in when the timer runs out with nothing selected |

Heal, Mirror, Vanish, Charm and Surge are the **special cards**.

## Slot resolution (both cards are revealed at once)
1. **Vanish** (either player): both cards do nothing this slot. A pending Surge is used up.
2. A pending **Surge** from the previous slot adds 20 to that player's attack in this slot, and is used up whether or not they play an attack. Surge in slot 5 does nothing.
3. Attack vs Attack: only the difference counts. The lower attacker loses (higher - lower). Equal attacks cancel.
4. Attack vs Defense: defender loses max(0, attack - defense).
5. Attack vs Mirror: the attacker takes the attack value (including any Surge bonus); the mirror player takes 0.
6. Attack vs anything else (heal, charm, surge, fizzle): the attack lands in full.
7. Heal: restores its value, applied together with any damage in the same slot (net change, then clamped to 0..100).
8. Charm: 20 moves from the opponent to the Charm player. Defense does not block it and Mirror does not reflect it. Charm vs Charm nets zero.
9. Defense and Mirror do nothing against cards that are not attacks.
10. After each slot: if either Aura is 0, stop. If both are 0 (possible with Charm vs Attack) it is a draw.
11. After slot 5: higher Aura wins; equal Aura is a draw.

## Draft
- Each player has their own shuffled copy of the deck. Picked cards leave only that player's deck.
- The offer is 3 cards. After a pick, the chosen card leaves and one new card refills the offer; unpicked cards stay.
- **Picks 1 and 2 offer only attack and defense cards.** After the second selection (pick or fizzle) the whole offer is redrawn from the full pile, so special cards can appear from pick 3. Offered-but-unpicked cards go back into the pile. Picked cards never return.
- The player sees their own picks, never the opponent's. 5 bulbs show progress.
- 25-second timer per pick. On timeout: lock in the highlighted card if there is one, otherwise a blank Fizzle.

## Placeholder deck (26 cards, to be redesigned by Anusha)
| Type | Count | Values |
|---|---|---|
| Attack | 10 | 10 x3, 20 x3, 30 x2, 40 x1, 50 x1 |
| Defense | 7 | 10 x1, 20 x2, 30 x2, 40 x1, 50 x1 |
| Heal | 2 | 30, 50 |
| Mirror | 2 | |
| Vanish | 2 | |
| Surge | 2 | |
| Charm | 1 | |

## Sigils
Only the 3 offered cards need distinct sigils, so a sigil means "which of the three" (slot A, B or C). Placeholder strokes for now: circle, line, V. Final designs and hand poses come later.

## Bots
`HeuristicBot` drafts by card value with a bit of seeded noise and caps on how many defense, heal or special cards it takes. `RandomBot` picks uniformly. Either can be given a `fizzle_prob` to simulate recognizer errors.

## Known issue (parked)
In simulation (5000 bot games) about 23% of games end tied and under 1% end in a knockout. Options to fix: chip damage, a lower starting Aura, a tiebreak, sudden death. Decide after the real cards exist.

## Update, Nov 15: named cards, one sigil per card, game screen

- Every card now has its own name and sigil (26 in total, same types and values as before). The list is `CATALOG` in `game/cards.py`; the shapes are in `recognition/sigils.py`; the card pictures are in `assets/cards/`.
- You pick a card by drawing its sigil. The upright shape matters; where you start and which direction you draw do not. The recognizer only chooses among the three cards on offer.
- A pick stays selected until you draw a different sigil. A fist locks it in. A fist with nothing selected does nothing.
- 30 seconds per pick. When time runs out the selected card is taken; with nothing selected the slot gets a Fizzle.
- After five picks the slots are revealed one at a time against the bot (the smarter bot), then the result; a zoom starts a new match.
- Run it with `python -m ui.play`. Keys for testing: s start, 1 2 3 pick, space lock, r restart, q quit.

