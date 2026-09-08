# Does man coverage say anything the price does not?

## market and model only

13,858 wagers, 96 clusters.

| term | estimate | 95% interval | tells from zero |
|:--|--:|:--|:--|
| intercept | -0.0283 | [-0.1125, +0.0559] | no |
| b  logit(market) | +0.9059 | [+0.7798, +1.0319] | yes |
| c  logit(model) | +0.1391 | [+0.0465, +0.2316] | yes |

## with the player feature

13,858 wagers, 96 clusters.

| term | estimate | 95% interval | tells from zero |
|:--|--:|:--|:--|
| intercept | -0.0276 | [-0.1112, +0.0559] | no |
| b  logit(market) | +0.9075 | [+0.7796, +1.0353] | yes |
| c  logit(model) | +0.1376 | [+0.0430, +0.2323] | yes |
| d1 opponent man rate (z) | +0.0136 | [-0.0876, +0.1149] | no |
| d2 receiver man-zone split (z, shrunk) | +0.0237 | [-0.0656, +0.1130] | no |
| d  the interaction (receiver split x opponent man rate) | -0.0153 | [-0.1028, +0.0721] | no |

## same fit, clustered by player_season

13,858 wagers, 253 clusters.

| term | estimate | 95% interval | tells from zero |
|:--|--:|:--|:--|
| intercept | -0.0276 | [-0.1048, +0.0495] | no |
| b  logit(market) | +0.9075 | [+0.7555, +1.0594] | yes |
| c  logit(model) | +0.1376 | [+0.0378, +0.2374] | yes |
| d1 opponent man rate (z) | +0.0136 | [-0.0769, +0.1042] | no |
| d2 receiver man-zone split (z, shrunk) | +0.0237 | [-0.0544, +0.1018] | no |
| d  the interaction (receiver split x opponent man rate) | -0.0153 | [-0.0954, +0.0647] | no |

## placebo: rates reassigned across defences

13,858 wagers, 96 clusters.

| term | estimate | 95% interval | tells from zero |
|:--|--:|:--|:--|
| intercept | -0.0278 | [-0.1103, +0.0546] | no |
| b  logit(market) | +0.9067 | [+0.7798, +1.0337] | yes |
| c  logit(model) | +0.1403 | [+0.0466, +0.2340] | yes |
| d1 opponent man rate (z) | +0.0680 | [-0.0124, +0.1485] | no |
| d2 receiver man-zone split (z, shrunk) | +0.0234 | [-0.0662, +0.1130] | no |
| d  the interaction (receiver split x opponent man rate) | -0.0037 | [-0.0864, +0.0790] | no |

## What the estimate means in probability

The feature covers **13,858 of 61,267 wagers** (22.6%). Every excluded row is excluded because the receiver did not clear 25 targets against **both** coverages in the prior season — not because a rate was missing, of which there are none. **The null below speaks for the busiest receiver-seasons only**, which is where a coverage effect would be easiest to find, not hardest.

The receiver's man-minus-zone differential has a measured split-half reliability of **0.145** over a full season. The differential is shrunk by that factor, and **the shrinkage changes nothing**: a constant multiplier is annihilated by the z-standardisation on the next line, so `d` is bit-identical at any reliability. It is kept because the shrunk column is the one a *predictive* use would need, but no claim rests on it here. The reliability that governs a prior-season feature is the **year-over-year** carryover, which is weaker still: r = +0.02 to +0.11 across gates, every interval crossing zero.

The within-season z-score spans **-2.07 to +2.22** across the defence-seasons here. At `d = -0.0153` per standard deviation, moving from the most zone defence to the most man one shifts the log-odds of the over by **0.0657** — about **1.64 percentage points** at an even-money price.

Bootstrap over 96 defence-seasons (400 draws): `d` in **[-0.1188, +0.0659]**. The sandwich says [-0.1028, +0.0721]; a closed form nobody checked against a resample is how this repository shipped two interval defects.

**A `d` that includes zero is no demonstrated edge, in those words.** It does not say coverage is irrelevant to football, and it does not say the question is settled. Read the power section below before concluding anything from it.

The control is the **card price, about six hours before kickoff** — not the closing price. The two correlate at 0.986 and refitting against the actual close moves nothing, but this fit does not test the close.

## What this test could not have found

**`d` is identified by 96 quantities, not 13,858.** The man rate is constant inside a defence-season, so every wager against one defence carries the same value of the regressor. Dropping three quarters of the *wagers* barely moves the standard error; dropping three quarters of the *defence-seasons* moves it by the square root of four, as it should. The wager count is the population the answer speaks for. It is not the sample size.

**Minimum detectable effect at 80% power: `d` = +0.1250.** Anything smaller than that, this design would miss more often than not. For scale, the props model's own contribution in the same fit is `c = +0.1376` — so the test could only have found a single public scheme statistic carrying 91% of what an entire player-props model carries beyond the price. Nobody expected that, and the design was never in a position to find less.

**What the interval fails to exclude, in money.** If `d` truly sat at the upper edge of its interval (+0.0721), the wagers where the feature favours the bet actually placed (6,740 of 13,858) would gain about **+2.49 ROI points** — roughly **+56 units a season** at the lab's flat 1-unit stake, against a receiving card that currently returns -4.03%. That is an effect large enough to erase most of the hold, and this test did not reject it.

**A quarter of the card never reaches this fit, and it is not a random quarter.** 82,811 wagers were scored; 20,325 (24.5%) have no two-sided price at their line and are dropped before anything is fitted — **100.0% of them overs**, because an over-only alternate line has no under to devig against. `encompassing.py` argues that selection here is harmless since it is a deterministic function of the regressors; that argument does **not** cover this drop, because whether a book quoted two sides is not a function of the price or the model. The null holds for the two-sided-priced population and is untested outside it.

**So the honest statement is the narrow one.** Not "coverage carries nothing", but: *a prior-season scheme proxy, measured over 96 defence-seasons, could not be told from zero by a test whose noise floor sits above the range of effects that would be worth money.* The placebo makes the same point from the other side — a feature reassigned at random routinely produces coefficients larger than every real point estimate here.
