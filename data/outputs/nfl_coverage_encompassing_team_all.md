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

**A `d` that includes zero is no demonstrated edge, in those words.** It does not say coverage is irrelevant to football; it says the closing price already holds whatever this measure of it knows.
