# Sigyl: game rules and engine spec (v1)

`game/` is pure Python (standard library only) and never imports camera, OpenCV, MediaPipe or numpy, so the same engine runs on a laptop and a Raspberry Pi 5. All randomness comes from a seeded `random.Random`, so games are reproducible.

## Flow
1. **Start:** the player makes the zoom gesture (pinch-out toward the camera). Once per game.
2. **Draft:** 5 picks. Each pick, 3 cards are offered. The player draws the sigil for one of them; a fist locks it in.
3. **Lock-in:** after pick 5, one more fist locks all 5 moves and starts the match.
4. **Match:** both sequences are revealed and resolved slot by slot (1 vs 1 ... 5 vs 5).
5. **Result:** an Aura of 0 ends the game at once. Otherwise, after slot 5 the higher Aura wins.

## Aura
Both players start at 100. Aura is clamped to 0..100.

## Cards
Values are multiples of 10, capped at 50.

| Type | What it does |
|---|---|
| Attack (10-50) | Deals its value to the opponent |
| Defense (10-50) | Blocks up to its value of an incoming attack |
| Heal (30 or 50) | Restores that much Aura |
| Mirror | Sends the opponent's attack back at them at the same value; you take 0 from it |
| Fizzle (blank) | Does nothing. Locked in when the timer runs out with nothing selected |

## Slot resolution (both cards are revealed at once)
- Attack vs Attack: only the difference counts. The lower attacker loses (higher - lower). Equal attacks cancel.
- Attack vs Defense: defender loses max(0, attack - defense).
- Attack vs Heal: both apply together, net = heal - attack, Aura clamped to 0..100.
- Attack vs Mirror: the attacker takes the attack value, the mirror player takes 0.
- Defense vs anything that is not an attack: nothing happens.
- Mirror vs anything that is not an attack: nothing happens (including Mirror vs Mirror).
- Heal vs Heal: both heal.
- Fizzle does nothing.
- After each slot: if either Aura is 0, stop. (Under these rules only one player can lose Aura in a slot, so both reaching 0 in the same slot cannot happen; the code still treats it as a draw.)
- After slot 5: higher Aura wins; equal Aura is a draw.

## Draft
- **Separate decks (assumption, not yet confirmed):** each player has their own shuffled copy of the same 21-card deck. Picked cards leave only that player's deck.
- The offer is 3 cards. After a pick, the chosen card leaves and one new card refills the offer; the two unpicked cards stay.
- The player sees their own picks, never the opponent's. 5 bulbs show progress.
- 25-second timer per pick. On timeout: lock in the highlighted card if there is one, otherwise a blank Fizzle (assumption, not yet confirmed).
- Redraw before the fist replaces the earlier selection (assumption, not yet confirmed).

## Placeholder deck (21 cards, to be redesigned by Anusha)
| Type | Count | Values |
|---|---|---|
| Attack | 10 | 10 x3, 20 x3, 30 x2, 40 x1, 50 x1 |
| Defense | 7 | 10 x1, 20 x2, 30 x2, 40 x1, 50 x1 |
| Heal | 2 | 30, 50 |
| Mirror | 2 | no value |

Extra specials proposed but not chosen: Vanish (cancel the opponent's card), Charm (steal 20 Aura), Surge (+20 on your next attack).

## Sigils
Only the 3 offered cards need distinct sigils, so a sigil means "which of the three" (for example circle, line, V), reused every turn. Not yet confirmed.

## Bot
`HeuristicBot` drafts by card value with a bit of seeded noise and caps on how many defense or heal cards it takes. `RandomBot` picks uniformly. Either can be given a `fizzle_prob` to simulate recognizer errors.
