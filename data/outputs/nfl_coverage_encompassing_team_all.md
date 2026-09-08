# Does man coverage say anything the price does not?

## market and model only

61,267 wagers, 96 clusters.

| term | estimate | 95% interval | tells from zero |
|:--|--:|:--|:--|
| intercept | -0.0333 | [-0.0727, +0.0060] | no |
| b  logit(market) | +0.9016 | [+0.8360, +0.9672] | yes |
| c  logit(model) | +0.0695 | [+0.0347, +0.1043] | yes |

## with the team feature

61,267 wagers, 96 clusters.

| term | estimate | 95% interval | tells from zero |
|:--|--:|:--|:--|
| intercept | -0.0333 | [-0.0726, +0.0060] | no |
| b  logit(market) | +0.9015 | [+0.8357, +0.9672] | yes |
| c  logit(model) | +0.0697 | [+0.0346, +0.1048] | yes |
| d  the interaction (receiver split x opponent man rate) | -0.0139 | [-0.0548, +0.0271] | no |

## placebo: rates reassigned across defences

61,267 wagers, 96 clusters.

| term | estimate | 95% interval | tells from zero |
|:--|--:|:--|:--|
| intercept | -0.0334 | [-0.0728, +0.0060] | no |
| b  logit(market) | +0.9014 | [+0.8359, +0.9668] | yes |
| c  logit(model) | +0.0695 | [+0.0348, +0.1043] | yes |
| d  the interaction (receiver split x opponent man rate) | +0.0077 | [-0.0339, +0.0492] | no |

## What the estimate means in probability

The feature covers **61,267 of 61,267 wagers** (100.0%). Rows without a prior-season rate are a relocated or expansion-less club-season and are excluded here rather than imputed.

The feature is the defence's man rate alone; no receiver split enters it.

The within-season z-score spans **-2.07 to +2.22** across the defence-seasons here. At `d = -0.0139` per standard deviation, moving from the most zone defence to the most man one shifts the log-odds of the over by **0.0594** — about **1.48 percentage points** at an even-money price.

Bootstrap over 96 defence-seasons (400 draws): `d` in **[-0.0526, +0.0295]**. The sandwich says [-0.0548, +0.0271]; a closed form nobody checked against a resample is how this repository shipped two interval defects.

**A `d` that includes zero is no demonstrated edge, in those words.** It does not say coverage is irrelevant to football, and it does not say the question is settled. Read the power section below before concluding anything from it.

The control is the **card price, about six hours before kickoff** — not the closing price. The two correlate at 0.986 and refitting against the actual close moves nothing, but this fit does not test the close.

## What this test could not have found

**`d` is identified by 96 quantities, not 61,267.** The man rate is constant inside a defence-season, so every wager against one defence carries the same value of the regressor. Dropping three quarters of the *wagers* barely moves the standard error; dropping three quarters of the *defence-seasons* moves it by the square root of four, as it should. The wager count is the population the answer speaks for. It is not the sample size.

**Minimum detectable effect at 80% power: `d` = +0.0585.** Anything smaller than that, this design would miss more often than not. For scale, the props model's own contribution in the same fit is `c = +0.0697` — so the test could only have found a single public scheme statistic carrying 84% of what an entire player-props model carries beyond the price. Nobody expected that, and the design was never in a position to find less.

**What the interval fails to exclude, in money.** If `d` truly sat at the upper edge of its interval (+0.0271), the wagers where the feature favours the bet actually placed (30,621 of 61,267) would gain about **+1.17 ROI points** — roughly **+120 units a season** at the lab's flat 1-unit stake, against a receiving card that currently returns -2.86%. That is an effect large enough to erase most of the hold, and this test did not reject it.

**A quarter of the card never reaches this fit, and it is not a random quarter.** 82,811 wagers were scored; 20,325 (24.5%) have no two-sided price at their line and are dropped before anything is fitted — **100.0% of them overs**, because an over-only alternate line has no under to devig against. `encompassing.py` argues that selection here is harmless since it is a deterministic function of the regressors; that argument does **not** cover this drop, because whether a book quoted two sides is not a function of the price or the model. The null holds for the two-sided-priced population and is untested outside it.

**So the honest statement is the narrow one.** Not "coverage carries nothing", but: *a prior-season scheme proxy, measured over 96 defence-seasons, could not be told from zero by a test whose noise floor sits above the range of effects that would be worth money.* The placebo makes the same point from the other side — a feature reassigned at random routinely produces coefficients larger than every real point estimate here.
