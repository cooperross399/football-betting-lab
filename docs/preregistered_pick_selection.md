# Pre-registration: can the card pick better? (2026-11-22)

Written and committed **before** any of the tests below was run. Cooper,
2026-11-22: "How can we improve the model to improve pick selection and make
more money". The tracker's posted NFL picks were 106-107 for +10.71u, but one
game (Tampa Bay @ Dallas, 2026-10-08) carries +13.55u of it; without it the
record is 44-101, -2.84u, ROI -19.3% over 71 games, and November alone is a
demonstrated loss (18-52, -31.8%, 34 games). That is a small live sample. The
priced history is the larger one: 773 games of 2023-25 card-time ladder prices,
bought once (Historical Purchase run 33214635431, artifact expiring
2026-11-26).

## What is already tested and not repeated here

Edge bands, market type, over/under and price filters (failed out of sample on
2025, thread "Alt spreads pick one side"); recency weighting (no detectable
difference). Re-running any of those on the same seasons is the same degree of
freedom twice, so none is a hypothesis here.

The "model overrates road blowouts" bias in project memory is a **college**
finding (n = 3,864, 2021-25, cfbfastR). It is not evidence about the NFL and is
not tested here as if it were.

## The baseline

The card's current rules, replayed on the 2023-25 card-time prices exactly as
`gameday_card.select` applies them: price between -160 and +600, edge at least
3.5% against the best price, drop a question with any edge above 15%, one side
per question, edge strictly above 6%, the best rung per question, at most 3
picks per game. Flat 1-unit stakes, pushes returned. Intervals clustered by
game.

## Hypotheses

**H1. Recalibrate toward the market (fitted).** The encompassing result says
the model is overconfident and the price carries most of what it knows. Fit
`logit P(win) = a + b*logit(fair) + c*logit(model)` on every 2023-24 card-time
rung that has a devigged fair price (`fair` = the median over books of each
book's two-sided devigged probability), apply it unchanged to 2025, and run the
card's rules on the recalibrated probability. *Prediction:* fewer picks and a
better 2025 return than the baseline's on the same games.

**H2. Shrink halfway to the market (unfitted).** `p = 0.5*model + 0.5*fair`,
the card's rules unchanged. No parameter is fitted, so all three seasons are
out of sample. *Prediction:* better than the baseline in each season.

**H3. Quarterback change.** The ratings are fitted on results produced by the
quarterback who played. A game where either club starts a different
quarterback from its previous regular-season game (nflverse `*_qb_id`) is one
the model cannot see and the market can. *Prediction:* baseline picks on those
games return less than picks on the rest; skipping them improves the card.
This is the team-market counterpart of `gates.check_quarterback`, which covers
props only and has no caller.

**H4. Closing-line value (diagnostic, decides nothing).** For each baseline
pick, the change in the devigged fair probability of the picked side from card
time to the close. Profit is the objective (Cooper, 2026-08-29); this only says
whether the market moves toward or away from what the card picks.

## The bar, declared now

A change ships only if, on the seasons it was not fitted on, the paired
per-game difference in units against the baseline has a 95% interval (by game)
that **excludes zero in its favour**, and the difference is not negative in any
single held-out season. Fewer picks with a return that is still negative is
reported as **betting less**, which loses less, and not as an edge. If nothing
clears the bar, nothing ships, and the report says so in those words.

Four hypotheses, recorded in the experiment ledger under
`pick-selection-2026-11`.
