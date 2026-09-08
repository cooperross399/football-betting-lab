# Does the volume a ruled-out team-mate leaves behind say anything the price does not?

## market and model only

12,365 wagers, 1277 clusters.

| term | estimate | 95% interval | tells from zero |
|:--|--:|:--|:--|
| intercept | -0.0850 | [-0.1617, -0.0083] | yes |
| b  logit(market) | +0.7444 | [+0.5944, +0.8944] | yes |
| c  logit(model) | +0.0635 | [-0.0112, +0.1381] | no |

## with the role feature

12,365 wagers, 1277 clusters.

| term | estimate | 95% interval | tells from zero |
|:--|--:|:--|:--|
| intercept | -0.0861 | [-0.1631, -0.0092] | yes |
| b  logit(market) | +0.7490 | [+0.5985, +0.8996] | yes |
| c  logit(model) | +0.0604 | [-0.0153, +0.1361] | no |
| d1 share vacated by the club (z) | -0.0358 | [-0.2053, +0.1337] | no |
| d  this player's share of it (z) | +0.0124 | [-0.1750, +0.1997] | no |

## same fit, clustered by player_season

12,365 wagers, 418 clusters.

| term | estimate | 95% interval | tells from zero |
|:--|--:|:--|:--|
| intercept | -0.0861 | [-0.1624, -0.0099] | yes |
| b  logit(market) | +0.7490 | [+0.5916, +0.9064] | yes |
| c  logit(model) | +0.0604 | [-0.0158, +0.1366] | no |
| d1 share vacated by the club (z) | -0.0358 | [-0.2267, +0.1551] | no |
| d  this player's share of it (z) | +0.0124 | [-0.1889, +0.2136] | no |

## placebo: the feature reassigned across its own clusters

12,365 wagers, 1277 clusters.

| term | estimate | 95% interval | tells from zero |
|:--|--:|:--|:--|
| intercept | -0.0849 | [-0.1616, -0.0082] | yes |
| b  logit(market) | +0.7430 | [+0.5931, +0.8929] | yes |
| c  logit(model) | +0.0639 | [-0.0108, +0.1386] | no |
| d1 share vacated by the club (z) | -0.0550 | [-0.1894, +0.0794] | no |
| d  this player's share of it (z) | +0.0263 | [-0.1002, +0.1528] | no |

## What the estimate means in probability

The feature covers **12,365 of 14,579 wagers** (84.8%). Excluded rows are a receiver with fewer than three prior weeks this season, or holding too small a share for an absence to expand. Nothing is excluded for a missing rate.

**This is the only feature here whose mechanism was confirmed before any price was involved.** Volume genuinely redistributes: a player's week-W share gain regressed on the pro-rata share he would receive gives +0.220, 95% [+0.113, +0.326] over 11,856 player-weeks — about 0.85 targets a game between a club that has vacated under 5% of its targets and one that has vacated over 15%. It is also the only feature the props model cannot see at all, because `fit_rates` reads a player's own history and that history was recorded while somebody else held the role. Every injury row used was filed at least six hours before kickoff.

The feature spans **-0.21 to +9.07**. At `d = +0.0124` per standard deviation, moving from one end of it to the other shifts the log-odds of the over by **0.1147** — about **2.87 percentage points** at an even-money price.

Bootstrap over 1,277 club-week clusters (400 draws): `d` in **[-0.1778, +0.2044]**. The sandwich says [-0.1750, +0.1997]; a closed form nobody checked against a resample is how this repository shipped two interval defects.

**A `d` that includes zero is no demonstrated edge, in those words.** It does not say coverage is irrelevant to football, and it does not say the question is settled. Read the power section below before concluding anything from it.

The control is the **card price, about six hours before kickoff** — not the closing price. The two correlate at 0.986 and refitting against the actual close moves nothing, but this fit does not test the close.

## What this test could not have found

**`d` is identified by 1,277 clusters, not 12,365 wagers.** The feature is constant inside a club-week, so every wager sharing one carries the same value of the regressor. Dropping three quarters of the *wagers* barely moves the standard error; dropping three quarters of the *clusters* moves it by the square root of four, as it should. The wager count is the population the answer speaks for. It is not the sample size.

**Minimum detectable effect at 80% power: `d` = +0.2677.** Anything smaller than that, this design would miss more often than not. For scale, the props model's own contribution in the same fit is `c = +0.0604` — so the test could only have found this feature carrying 443% of what an entire player-props model carries beyond the price. Nobody expected that, and the design was never in a position to find less.

**What the interval fails to exclude, in money.** If `d` truly sat at the upper edge of its interval (+0.1997), the wagers where the feature favours the bet actually placed (7,545 of 12,365) would gain about **+2.20 ROI points** — roughly **+55 units a season** at the lab's flat 1-unit stake, against a rushing card that currently returns 5.09%. That is an effect large enough to erase most of the hold, and this test did not reject it.

**18% of the card never reaches this fit, and it is not a random part of it.** 17,905 wagers were scored; 3,228 (18.0%) have no two-sided price at their line and are dropped before anything is fitted — **100.0% of them overs**, because an over-only alternate line has no under to devig against. `encompassing.py` argues that selection here is harmless since it is a deterministic function of the regressors; that argument does **not** cover this drop, because whether a book quoted two sides is not a function of the price or the model. The null holds for the two-sided-priced population and is untested outside it.

**So the honest statement is the narrow one.** Not "the volume a ruled-out team-mate leaves behind carries nothing", but: *a within-season measure of it, identified by 1,277 clusters, could not be told from zero by a test whose noise floor sits above the range of effects that would be worth money.* The placebo makes the same point from the other side — a feature reassigned at random routinely produces coefficients larger than every real point estimate here.
