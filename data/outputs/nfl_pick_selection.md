# Can the card pick better?

Pre-registered in `docs/preregistered_pick_selection.md` before any of this ran. 371,315 priced card-time ladder rungs over 814 games, 2023-25, walk-forward. Every variant runs the card's own selection chain (-160 to +600, edge 3.5%+, 15% ceiling, one side, edge above 6%, best rung per question, 3 per game). Flat 1-unit stakes; intervals clustered by game.

Copied from `Pick Selection Experiments` run 45043102215 (2026-11-22). The run's artifact `pick-selection-experiments` also holds the JSON and every priced rung (`nfl_pick_selection_rungs.csv.gz`); `historical-prices-kept` is a second 90-day copy of the bought prices, whose original artifact expires 2026-11-26.

## Verdict

**Nothing clears the bar declared in advance, so nothing ships.** The baseline card loses (-5.2% over 1,282 bets, 668 games, **no demonstrated edge**), and none of the three changes improves it by a margin the data can tell from zero.

The H1 fit is the finding that explains the rest: with the devigged market price in the regression, **the model's weight is 0.000** over 224,258 rungs. On these ladders the model knows nothing the price does not, so the recalibrated card selects nothing at all, and abstaining beats the card by +66.85u over 2023-25 (+36.91u on held-out 2025) — an interval that still includes zero.

## 2023

| Rule | Bets | Games | Units | ROI | 95% |
|:--|--:|--:|--:|--:|:--|
| Baseline (today's card) | 432 | 226 | -18.82 | -4.4% | -18.0% to +9.3% |
| H1 recalibrated (fitted 2023-24) | 0 | 0 | 0.00 | n/a | n/a |
| H2 halfway to the market | 453 | 219 | -39.36 | -8.7% | -25.2% to +7.8% |
| H3 skip quarterback-change games | 331 | 171 | -27.55 | -8.3% | -23.8% to +7.2% |

Paired against the baseline, units per game (variant minus baseline):

| Rule | Units | Per game | 95% |
|:--|--:|--:|:--|
| H1 recalibrated (fitted 2023-24) | +18.82 | +0.069 | -0.148 to +0.287 |
| H2 halfway to the market | -20.55 | -0.076 | -0.358 to +0.206 |
| H3 skip quarterback-change games | -8.73 | -0.032 | -0.138 to +0.073 |

## 2024

| Rule | Bets | Games | Units | ROI | 95% |
|:--|--:|--:|--:|--:|:--|
| Baseline (today's card) | 417 | 219 | -11.12 | -2.7% | -18.1% to +12.8% |
| H1 recalibrated (fitted 2023-24) | 0 | 0 | 0.00 | n/a | n/a |
| H2 halfway to the market | 378 | 192 | -6.80 | -1.8% | -20.0% to +16.4% |
| H3 skip quarterback-change games | 325 | 171 | -7.52 | -2.3% | -19.8% to +15.2% |

Paired against the baseline, units per game (variant minus baseline):

| Rule | Units | Per game | 95% |
|:--|--:|--:|:--|
| H1 recalibrated (fitted 2023-24) | +11.12 | +0.041 | -0.196 to +0.278 |
| H2 halfway to the market | +4.32 | +0.016 | -0.260 to +0.292 |
| H3 skip quarterback-change games | +3.61 | +0.013 | -0.099 to +0.126 |

## 2025 (held out for H1)

| Rule | Bets | Games | Units | ROI | 95% |
|:--|--:|--:|--:|--:|:--|
| Baseline (today's card) | 433 | 223 | -36.91 | -8.5% | -24.0% to +7.0% |
| H1 recalibrated (fitted 2023-24) | 0 | 0 | 0.00 | n/a | n/a |
| H2 halfway to the market | 393 | 189 | -21.75 | -5.5% | -23.2% to +12.2% |
| H3 skip quarterback-change games | 337 | 172 | -54.62 | -16.2% | -33.3% to +0.9% |

Paired against the baseline, units per game (variant minus baseline):

| Rule | Units | Per game | 95% |
|:--|--:|--:|:--|
| H1 recalibrated (fitted 2023-24) | +36.91 | +0.136 | -0.112 to +0.384 |
| H2 halfway to the market | +15.16 | +0.056 | -0.226 to +0.338 |
| H3 skip quarterback-change games | -17.71 | -0.065 | -0.188 to +0.057 |

## 2023-25

| Rule | Bets | Games | Units | ROI | 95% |
|:--|--:|--:|--:|--:|:--|
| Baseline (today's card) | 1,282 | 668 | -66.85 | -5.2% | -13.8% to +3.4% |
| H1 recalibrated (fitted 2023-24) | 0 | 0 | 0.00 | n/a | n/a |
| H2 halfway to the market | 1,224 | 600 | -67.92 | -5.5% | -15.6% to +4.5% |
| H3 skip quarterback-change games | 993 | 514 | -89.68 | -9.0% | -18.7% to +0.6% |

Paired against the baseline, units per game (variant minus baseline):

| Rule | Units | Per game | 95% |
|:--|--:|--:|:--|
| H1 recalibrated (fitted 2023-24) | +66.85 | +0.082 | -0.053 to +0.217 |
| H2 halfway to the market | -1.07 | -0.001 | -0.163 to +0.160 |
| H3 skip quarterback-change games | -22.84 | -0.028 | -0.094 to +0.038 |

## H3: baseline picks on quarterback-change games

| | Bets | Games | Units | ROI | 95% |
|:--|--:|--:|--:|--:|:--|
| New starter on either side | 289 | 154 | +22.84 | +7.9% | -10.5% to +26.4% |
| Same starters | 993 | 514 | -89.68 | -9.0% | -18.7% to +0.6% |

The predicted direction was wrong: the card did *better* on games with a new starter. Both intervals include zero, so this is not a reason to seek those games out either.

## H1 fit

On 224,258 2023-24 rungs: a = -0.000, b (market) = 1.118, c (model) = -0.000. A model weight near zero means the price already holds what the model knows. The intercept is zero by construction: every two-sided rung enters once from each side.

## H4: closing-line movement (diagnostic)

Not measurable: no baseline pick had a devigged closing price to compare against, so the cache holds no usable closing team-market quotes for these rungs. It decided nothing either way.
