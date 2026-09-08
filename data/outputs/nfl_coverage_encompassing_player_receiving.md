# Does a receiver's man-zone split against the defence's man rate say anything the price does not?

## market and model only

12,729 wagers, 96 clusters.

| term | estimate | 95% interval | tells from zero |
|:--|--:|:--|:--|
| intercept | -0.0269 | [-0.1225, +0.0686] | no |
| b  logit(market) | +0.8972 | [+0.7591, +1.0353] | yes |
| c  logit(model) | +0.1461 | [+0.0457, +0.2464] | yes |

## with the player feature

12,729 wagers, 96 clusters.

| term | estimate | 95% interval | tells from zero |
|:--|--:|:--|:--|
| intercept | -0.0259 | [-0.1209, +0.0691] | no |
| b  logit(market) | +0.9002 | [+0.7583, +1.0421] | yes |
| c  logit(model) | +0.1431 | [+0.0384, +0.2478] | yes |
| d1 opponent man rate (z) | +0.0143 | [-0.0998, +0.1285] | no |
| d2 receiver man-zone split (z, shrunk) | +0.0233 | [-0.0689, +0.1154] | no |
| d  the interaction (receiver split x opponent man rate) | +0.0014 | [-0.0835, +0.0863] | no |

## same fit, clustered by player_season

12,729 wagers, 253 clusters.

| term | estimate | 95% interval | tells from zero |
|:--|--:|:--|:--|
| intercept | -0.0259 | [-0.1055, +0.0537] | no |
| b  logit(market) | +0.9002 | [+0.7415, +1.0589] | yes |
| c  logit(model) | +0.1431 | [+0.0392, +0.2470] | yes |
| d1 opponent man rate (z) | +0.0143 | [-0.0827, +0.1113] | no |
| d2 receiver man-zone split (z, shrunk) | +0.0233 | [-0.0548, +0.1013] | no |
| d  the interaction (receiver split x opponent man rate) | +0.0014 | [-0.0866, +0.0894] | no |

## placebo: the feature reassigned across its own clusters

12,729 wagers, 96 clusters.

| term | estimate | 95% interval | tells from zero |
|:--|--:|:--|:--|
| intercept | -0.0270 | [-0.1202, +0.0662] | no |
| b  logit(market) | +0.8969 | [+0.7558, +1.0380] | yes |
| c  logit(model) | +0.1474 | [+0.0442, +0.2506] | yes |
| d1 opponent man rate (z) | +0.0917 | [+0.0025, +0.1808] | yes |
| d2 receiver man-zone split (z, shrunk) | +0.0221 | [-0.0719, +0.1160] | no |
| d  the interaction (receiver split x opponent man rate) | +0.0295 | [-0.0630, +0.1220] | no |

## What the estimate means in probability

The feature covers **12,729 of 30,836 wagers** (41.3%). Every excluded row is excluded because the receiver did not clear 25 targets against **both** coverages in the prior season — not because a rate was missing, of which there are none. **The null below speaks for the busiest receiver-seasons only**, which is where a coverage effect would be easiest to find, not hardest.

The receiver's man-minus-zone differential has a measured split-half reliability of **0.145** over a full season. The differential is shrunk by that factor, and **the shrinkage changes nothing**: a constant multiplier is annihilated by the z-standardisation on the next line, so `d` is bit-identical at any reliability. It is kept because the shrunk column is the one a *predictive* use would need, but no claim rests on it here. The reliability that governs a prior-season feature is the **year-over-year** carryover, which is weaker still: r = +0.02 to +0.11 across gates, every interval crossing zero.

The feature spans **-5.82 to +5.73**. At `d = +0.0014` per standard deviation, moving from one end of it to the other shifts the log-odds of the over by **0.0160** — about **0.40 percentage points** at an even-money price.

Bootstrap over 96 defence-season clusters (400 draws): `d` in **[-0.0951, +0.0817]**. The sandwich says [-0.0835, +0.0863]; a closed form nobody checked against a resample is how this repository shipped two interval defects.

**A `d` that includes zero is no demonstrated edge, in those words.** It does not say coverage is irrelevant to football, and it does not say the question is settled. Read the power section below before concluding anything from it.

The control is the **card price, about six hours before kickoff** — not the closing price. The two correlate at 0.986 and refitting against the actual close moves nothing, but this fit does not test the close.

## What this test could not have found

**`d` is identified by 96 clusters, not 12,729 wagers.** The feature is constant inside a defence-season, so every wager sharing one carries the same value of the regressor. Dropping three quarters of the *wagers* barely moves the standard error; dropping three quarters of the *clusters* moves it by the square root of four, as it should. The wager count is the population the answer speaks for. It is not the sample size.

**Minimum detectable effect at 80% power: `d` = +0.1213.** Anything smaller than that, this design would miss more often than not. For scale, the props model's own contribution in the same fit is `c = +0.1431` — so the test could only have found a single public scheme statistic carrying 85% of what an entire player-props model carries beyond the price. Nobody expected that, and the design was never in a position to find less.

**What the interval fails to exclude, in money.** If `d` truly sat at the upper edge of its interval (+0.0863), the wagers where the feature favours the bet actually placed (6,157 of 12,729) would gain about **+3.02 ROI points** — roughly **+62 units a season** at the lab's flat 1-unit stake, against a receiving card that currently returns -3.81%. That is an effect large enough to erase most of the hold, and this test did not reject it.

**27% of the card never reaches this fit, and it is not a random part of it.** 43,722 wagers were scored; 11,917 (27.3%) have no two-sided price at their line and are dropped before anything is fitted — **100.0% of them overs**, because an over-only alternate line has no under to devig against. `encompassing.py` argues that selection here is harmless since it is a deterministic function of the regressors; that argument does **not** cover this drop, because whether a book quoted two sides is not a function of the price or the model. The null holds for the two-sided-priced population and is untested outside it.

**So the honest statement is the narrow one.** Not "a receiver's man-zone split against the defence's man rate carries nothing", but: *a prior-season measure of it, identified by 96 clusters, could not be told from zero by a test whose noise floor sits above the range of effects that would be worth money.* The placebo makes the same point from the other side — a feature reassigned at random routinely produces coefficients larger than every real point estimate here.
