# AGENT_LOG

Agent Track requirement. For each entry record: where the AI got it wrong, what was written by hand, and how it was verified.

| Date | Area | AI failure / correction | Written by hand | How verified |
|------|------|-------------------------|-----------------|--------------|
| 2026-10-18 | Game engine | AI started building a wizard-duel engine and a balance simulation after being asked only to discuss the game logic. Anusha interrupted. The draft was never committed and was deleted. | Game design (draft-and-resolve card game, Aura, gestures, card values) came from Anusha | Not applicable, work discarded |
| 2026-10-30 | Engine tests | AI's first mirror-vs-heal test used full Aura, so the heal was clamped and the test failed. The engine was right; the test was wrong. Fixed the test. | Rules and numbers (Aura 100, values capped at 50, attack difference, mirror, defense) specified by Anusha | pytest, 42 tests passing; exhaustive check over every card pair |
| 2026-10-30 | Rules check | While testing, AI found that both players reaching 0 in the same slot cannot happen under the agreed rules, and that knockouts are rare (0.3% in 5000 simulated games; about 22% of games end in a draw). Reported to Anusha for a decision rather than changing the rules. | Not applicable | `python -m game.simulate` with seeded bots |
