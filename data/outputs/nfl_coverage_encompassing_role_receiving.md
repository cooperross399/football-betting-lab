# Does the volume a ruled-out team-mate leaves behind say anything the price does not?

## market and model only

25,968 wagers, 1304 clusters.

| term | estimate | 95% interval | tells from zero |
|:--|--:|:--|:--|
| intercept | -0.0034 | [-0.0592, +0.0525] | no |
| b  logit(market) | +0.9978 | [+0.8851, +1.1106] | yes |
| c  logit(model) | +0.0846 | [+0.0117, +0.1576] | yes |

## with the role feature

25,968 wagers, 1304 clusters.

| term | estimate | 95% interval | tells from zero |
|:--|--:|:--|:--|
| intercept | -0.0043 | [-0.0600, +0.0514] | no |
| b  logit(market) | +0.9917 | [+0.8788, +1.1045] | yes |
| c  logit(model) | +0.0927 | [+0.0194, +0.1660] | yes |
| d1 share vacated by the club (z) | +0.0857 | [-0.0165, +0.1880] | no |
| d  this player's share of it (z) | -0.0441 | [-0.1465, +0.0583] | no |

## same fit, clustered by player_season

25,968 wagers, 839 clusters.

| term | estimate | 95% interval | tells from zero |
|:--|--:|:--|:--|
| intercept | -0.0043 | [-0.0575, +0.0489] | no |
| b  logit(market) | +0.9917 | [+0.8802, +1.1031] | yes |
| c  logit(model) | +0.0927 | [+0.0278, +0.1575] | yes |
| d1 share vacated by the club (z) | +0.0857 | [-0.0197, +0.1911] | no |
| d  this player's share of it (z) | -0.0441 | [-0.1444, +0.0562] | no |

## placebo: the feature reassigned across its own clusters

25,968 wagers, 1304 clusters.

| term | estimate | 95% interval | tells from zero |
|:--|--:|:--|:--|
| intercept | -0.0030 | [-0.0589, +0.0528] | no |
| b  logit(market) | +1.0000 | [+0.8865, +1.1134] | yes |
| c  logit(model) | +0.0823 | [+0.0088, +0.1558] | yes |
| d1 share vacated by the club (z) | +0.0250 | [-0.0762, +0.1262] | no |
| d  this player's share of it (z) | -0.0326 | [-0.1391, +0.0739] | no |

## What the estimate means in probability

The feature covers **25,968 of 30,836 wagers** (84.2%). Excluded rows are a receiver with fewer than three prior weeks this season, or holding too small a share for an absence to expand. Nothing is excluded for a missing rate.

**This is the only feature here whose mechanism was confirmed before any price was involved.** Volume genuinely redistributes: a player's week-W share gain regressed on the pro-rata share he would receive gives +0.220, 95% [+0.113, +0.326] over 11,856 player-weeks — about 0.85 targets a game between a club that has vacated under 5% of its targets and one that has vacated over 15%. It is also the only feature the props model cannot see at all, because `fit_rates` reads a player's own history and that history was recorded while somebody else held the role. Every injury row used was filed at least six hours before kickoff.

The feature spans **-0.33 to +13.88**. At `d = -0.0441` per standard deviation, moving from one end of it to the other shifts the log-odds of the over by **0.6265** — about **15.17 percentage points** at an even-money price.

Bootstrap over 1,304 club-week clusters (400 draws): `d` in **[-0.1581, +0.0719]**. The sandwich says [-0.1465, +0.0583]; a closed form nobody checked against a resample is how this repository shipped two interval defects.

**A `d` that includes zero is no demonstrated edge, in those words.** It does not say coverage is irrelevant to football, and it does not say the question is settled. Read the power section below before concluding anything from it.

The control is the **card price, about six hours before kickoff** — not the closing price. The two correlate at 0.986 and refitting against the actual close moves nothing, but this fit does not test the close.

## What this test could not have found

**`d` is identified by 1,304 clusters, not 25,968 wagers.** The feature is constant inside a club-week, so every wager sharing one carries the same value of the regressor. Dropping three quarters of the *wagers* barely moves the standard error; dropping three quarters of the *clusters* moves it by the square root of four, as it should. The wager count is the population the answer speaks for. It is not the sample size.

**Minimum detectable effect at 80% power: `d` = +0.1462.** Anything smaller than that, this design would miss more often than not. For scale, the props model's own contribution in the same fit is `c = +0.0927` — so the test could only have found a single public scheme statistic carrying 158% of what an entire player-props model carries beyond the price. Nobody expected that, and the design was never in a position to find less.

**What the interval fails to exclude, in money.** If `d` truly sat at the upper edge of its interval (+0.0583), the wagers where the feature favours the bet actually placed (10,126 of 25,968) would gain about **+1.45 ROI points** — roughly **+49 units a season** at the lab's flat 1-unit stake, against a receiving card that currently returns -2.09%. That is an effect large enough to erase most of the hold, and this test did not reject it.

**27% of the card never reaches this fit, and it is not a random part of it.** 43,722 wagers were scored; 11,917 (27.3%) have no two-sided price at their line and are dropped before anything is fitted — **100.0% of them overs**, because an over-only alternate line has no under to devig against. `encompassing.py` argues that selection here is harmless since it is a deterministic function of the regressors; that argument does **not** cover this drop, because whether a book quoted two sides is not a function of the price or the model. The null holds for the two-sided-priced population and is untested outside it.

**So the honest statement is the narrow one.** Not "the volume a ruled-out team-mate leaves behind carries nothing", but: *a prior-season measure of it, identified by 1,304 clusters, could not be told from zero by a test whose noise floor sits above the range of effects that would be worth money.* The placebo makes the same point from the other side — a feature reassigned at random routinely produces coefficients larger than every real point estimate here.
