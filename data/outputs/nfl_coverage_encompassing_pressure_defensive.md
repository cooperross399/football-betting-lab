# Does a rusher's pressure rate against the line in front of him say anything the price does not?

## market and model only

3,696 wagers, 723 clusters.

| term | estimate | 95% interval | tells from zero |
|:--|--:|:--|:--|
| intercept | -0.0611 | [-0.1465, +0.0243] | no |
| b  logit(market) | +0.8748 | [+0.6251, +1.1246] | yes |
| c  logit(model) | +0.1727 | [+0.0714, +0.2740] | yes |

## with the pressure feature

3,696 wagers, 723 clusters.

| term | estimate | 95% interval | tells from zero |
|:--|--:|:--|:--|
| intercept | -0.0597 | [-0.1445, +0.0252] | no |
| b  logit(market) | +0.8826 | [+0.6119, +1.1533] | yes |
| c  logit(model) | +0.1726 | [+0.0692, +0.2760] | yes |
| d1 rusher pressures per game (z) | -0.0082 | [-0.0798, +0.0633] | no |
| d2 opposing line pressure allowed (z) | -0.0314 | [-0.1031, +0.0404] | no |
| d  the interaction (rusher x line) | -0.0194 | [-0.0842, +0.0455] | no |

## same fit, clustered by defence_season

3,696 wagers, 96 clusters.

| term | estimate | 95% interval | tells from zero |
|:--|--:|:--|:--|
| intercept | -0.0597 | [-0.1561, +0.0368] | no |
| b  logit(market) | +0.8826 | [+0.6505, +1.1147] | yes |
| c  logit(model) | +0.1726 | [+0.0708, +0.2745] | yes |
| d1 rusher pressures per game (z) | -0.0082 | [-0.0804, +0.0639] | no |
| d2 opposing line pressure allowed (z) | -0.0314 | [-0.1114, +0.0487] | no |
| d  the interaction (rusher x line) | -0.0194 | [-0.0855, +0.0467] | no |

## placebo: the feature reassigned across its own clusters

3,696 wagers, 723 clusters.

| term | estimate | 95% interval | tells from zero |
|:--|--:|:--|:--|
| intercept | -0.0596 | [-0.1445, +0.0252] | no |
| b  logit(market) | +0.8754 | [+0.6256, +1.1252] | yes |
| c  logit(model) | +0.1722 | [+0.0707, +0.2737] | yes |
| d1 rusher pressures per game (z) | -0.0136 | [-0.0798, +0.0526] | no |
| d2 opposing line pressure allowed (z) | +0.0279 | [-0.0443, +0.1001] | no |
| d  the interaction (rusher x line) | -0.0088 | [-0.0748, +0.0572] | no |

## What the estimate means in probability

The feature covers **3,696 of 4,588 wagers** (80.6%). Excluded rows are a defender with too few charted games in the prior season, or an offence whose quarterbacks did not reach that either — not a missing rate, and not imputed.

The rusher's pressures per game is the most persistent feature in this lab — carryover of relative position +0.884 over 2018-2025, measured by scripts/run_feature_reliability.py. That is why it was the one worth a real test, and why the market has had every year to price it.

The feature spans **-8.70 to +6.84**. At `d = -0.0194` per standard deviation, moving from one end of it to the other shifts the log-odds of the over by **0.3012** — about **7.47 percentage points** at an even-money price.

Bootstrap over 723 player-season clusters (400 draws): `d` in **[-0.0828, +0.0435]**. The sandwich says [-0.0842, +0.0455]; a closed form nobody checked against a resample is how this repository shipped two interval defects.

**A `d` that includes zero is no demonstrated edge, in those words.** It does not say coverage is irrelevant to football, and it does not say the question is settled. Read the power section below before concluding anything from it.

The control is the **card price, about six hours before kickoff** — not the closing price. The two correlate at 0.986 and refitting against the actual close moves nothing, but this fit does not test the close.

## What this test could not have found

**`d` is identified by 723 clusters, not 3,696 wagers.** The feature is constant inside a player-season, so every wager sharing one carries the same value of the regressor. Dropping three quarters of the *wagers* barely moves the standard error; dropping three quarters of the *clusters* moves it by the square root of four, as it should. The wager count is the population the answer speaks for. It is not the sample size.

**Minimum detectable effect at 80% power: `d` = +0.0926.** Anything smaller than that, this design would miss more often than not. For scale, the props model's own contribution in the same fit is `c = +0.1726` — so the test could only have found a single public scheme statistic carrying 54% of what an entire player-props model carries beyond the price. Nobody expected that, and the design was never in a position to find less.

**What the interval fails to exclude, in money.** If `d` truly sat at the upper edge of its interval (+0.0455), the wagers where the feature favours the bet actually placed (1,662 of 3,696) would gain about **+1.58 ROI points** — roughly **+9 units a season** at the lab's flat 1-unit stake, against a defensive card that currently returns 2.66%. That is an effect large enough to erase most of the hold, and this test did not reject it.

**13% of the card never reaches this fit, and it is not a random part of it.** 5,393 wagers were scored; 687 (12.7%) have no two-sided price at their line and are dropped before anything is fitted — **99.7% of them overs**, because an over-only alternate line has no under to devig against. `encompassing.py` argues that selection here is harmless since it is a deterministic function of the regressors; that argument does **not** cover this drop, because whether a book quoted two sides is not a function of the price or the model. The null holds for the two-sided-priced population and is untested outside it.

**So the honest statement is the narrow one.** Not "a rusher's pressure rate against the line in front of him carries nothing", but: *a prior-season measure of it, identified by 723 clusters, could not be told from zero by a test whose noise floor sits above the range of effects that would be worth money.* The placebo makes the same point from the other side — a feature reassigned at random routinely produces coefficients larger than every real point estimate here.
