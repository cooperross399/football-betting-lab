# Where the metrics disagree with the line

3,403 games, 2012-2025. A club's rating comes from its own prior games only; the mapping from rating to points is refitted for each season on the seasons before it. Nothing sees the game it is pricing, or the rest of the week it is in.

## How far apart the two are

| | mean absolute divergence | correlation with the result |
|:--|--:|--:|
| margin | 2.98 points | -0.0136 |
| total | 2.73 points | -0.0194 |

**The correlation is the whole result, and both are slightly NEGATIVE.** It asks whether the metrics point the right way about what the line got wrong. Near zero means the disagreement is noise however large it is — and the model disagrees by about three points a game, so the disagreement is not small. It is simply uninformative, and if anything it leans the wrong way.

## Betting the disagreement, at -110

| threshold | market | bets | ROI | 95% interval |
|--:|:--|--:|--:|:--|
| 0 pts | spread | 3,403 | -3.53% | [-6.60%, -0.51%] |
| 0 pts | total | 3,403 | -5.66% | [-8.62%, -2.58%] |
| 1 pts | spread | 2,656 | -3.42% | [-6.91%, -0.01%] |
| 1 pts | total | 2,620 | -5.09% | [-8.82%, -1.49%] |
| 2 pts | spread | 1,975 | -2.82% | [-7.06%, +1.20%] |
| 2 pts | total | 1,890 | -5.12% | [-9.47%, -0.88%] |
| 3 pts | spread | 1,387 | -2.51% | [-7.78%, +2.34%] |
| 3 pts | total | 1,289 | -0.87% | [-5.77%, +4.38%] |
| 4 pts | spread | 931 | -2.71% | [-8.49%, +3.55%] |
| 4 pts | total | 829 | -1.50% | [-8.19%, +4.81%] |
| 6 pts | spread | 372 | +0.95% | [-8.50%, +10.68%] |
| 6 pts | total | 284 | -2.46% | [-13.19%, +8.64%] |

**No rule is profitable at any threshold, in either market.** All 12 rules tried are reported, so the count is the multiplicity.

**5 of them exclude zero on the LOSING side**, so at those thresholds this is a demonstrated loss rather than a null. Betting where the metrics disagree with the line does worse than not betting.

The best point estimate is +0.95% on 372 spread bets at the 6-point threshold — with an interval of [-8.50%, +10.68%]. That is what noise looks like when a filter has cut the sample to a few hundred, and it is the reason every threshold is printed rather than the flattering one.

A bet at -110 needs **52.38%** to break even, so a rule has to be right more than half the time by a clear margin before the hold is paid. Line shopping recovers about 4.7 points of hold across thirteen books but never reaches zero (`nfl_shopping_value.md`), so a losing rule stays losing at every book count.

## What this does and does not settle

It is the direct form of the question the board could not answer: not *are these clubs different*, which they plainly are, but *does the difference the metrics see land anywhere the price has not already been*. The rating is deliberately simple — trailing form on the metrics that survived the screen, mapped to points by least squares — because a more elaborate one fitted on the same history would be measuring the elaboration.

The mapping trains on up to 3,498 prior games, and the first scored season is the first with enough history behind it.
