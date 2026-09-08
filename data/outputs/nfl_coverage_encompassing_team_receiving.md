# Does man coverage say anything the price does not?

## market and model only

30,836 wagers, 96 clusters.

| term | estimate | 95% interval | tells from zero |
|:--|--:|:--|:--|
| intercept | -0.0114 | [-0.0697, +0.0469] | no |
| b  logit(market) | +0.9743 | [+0.8829, +1.0656] | yes |
| c  logit(model) | +0.0952 | [+0.0360, +0.1543] | yes |

## with the team feature

30,836 wagers, 96 clusters.

| term | estimate | 95% interval | tells from zero |
|:--|--:|:--|:--|
| intercept | -0.0114 | [-0.0696, +0.0469] | no |
| b  logit(market) | +0.9741 | [+0.8831, +1.0652] | yes |
| c  logit(model) | +0.0953 | [+0.0363, +0.1543] | yes |
| d  the interaction (receiver split x opponent man rate) | +0.0094 | [-0.0520, +0.0709] | no |

## placebo: rates reassigned across defences

30,836 wagers, 96 clusters.

| term | estimate | 95% interval | tells from zero |
|:--|--:|:--|:--|
| intercept | -0.0124 | [-0.0690, +0.0441] | no |
| b  logit(market) | +0.9731 | [+0.8840, +1.0623] | yes |
| c  logit(model) | +0.0971 | [+0.0379, +0.1563] | yes |
| d  the interaction (receiver split x opponent man rate) | +0.0588 | [-0.0026, +0.1201] | no |

## What the estimate means in probability

The feature covers **30,836 of 30,836 wagers** (100.0%). Rows without a prior-season rate are a relocated or expansion-less club-season and are excluded here rather than imputed.

The feature is the defence's man rate alone; no receiver split enters it.

The within-season z-score spans **-2.07 to +2.22** across the defence-seasons here. At `d = +0.0094` per standard deviation, moving from the most zone defence to the most man one shifts the log-odds of the over by **0.0405** — about **1.01 percentage points** at an even-money price.

Bootstrap over 96 defence-seasons (400 draws): `d` in **[-0.0472, +0.0761]**. The sandwich says [-0.0520, +0.0709]; a closed form nobody checked against a resample is how this repository shipped two interval defects.

**A `d` that includes zero is no demonstrated edge, in those words.** It does not say coverage is irrelevant to football, and it does not say the question is settled. Read the power section below before concluding anything from it.

The control is the **card price, about six hours before kickoff** — not the closing price. The two correlate at 0.986 and refitting against the actual close moves nothing, but this fit does not test the close.

## What this test could not have found

**`d` is identified by 96 quantities, not 30,836.** The man rate is constant inside a defence-season, so every wager against one defence carries the same value of the regressor. Dropping three quarters of the *wagers* barely moves the standard error; dropping three quarters of the *defence-seasons* moves it by the square root of four, as it should. The wager count is the population the answer speaks for. It is not the sample size.

**Minimum detectable effect at 80% power: `d` = +0.0878.** Anything smaller than that, this design would miss more often than not. For scale, the props model's own contribution in the same fit is `c = +0.0953` — so the test could only have found a single public scheme statistic carrying 92% of what an entire player-props model carries beyond the price. Nobody expected that, and the design was never in a position to find less.

**What the interval fails to exclude, in money.** If `d` truly sat at the upper edge of its interval (+0.0709), the wagers where the feature favours the bet actually placed (15,216 of 30,836) would gain about **+3.05 ROI points** — roughly **+155 units a season** at the lab's flat 1-unit stake, against a receiving card that currently returns -3.22%. That is an effect large enough to erase most of the hold, and this test did not reject it.

**A quarter of the card never reaches this fit, and it is not a random quarter.** 43,722 wagers were scored; 11,917 (27.3%) have no two-sided price at their line and are dropped before anything is fitted — **100.0% of them overs**, because an over-only alternate line has no under to devig against. `encompassing.py` argues that selection here is harmless since it is a deterministic function of the regressors; that argument does **not** cover this drop, because whether a book quoted two sides is not a function of the price or the model. The null holds for the two-sided-priced population and is untested outside it.

**So the honest statement is the narrow one.** Not "coverage carries nothing", but: *a prior-season scheme proxy, measured over 96 defence-seasons, could not be told from zero by a test whose noise floor sits above the range of effects that would be worth money.* The placebo makes the same point from the other side — a feature reassigned at random routinely produces coefficients larger than every real point estimate here.
