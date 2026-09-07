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

The feature covers **13,858 of 61,267 wagers** (22.6%). Rows without a prior-season rate are a relocated or expansion-less club-season and are excluded here rather than imputed.

The receiver's man-minus-zone differential has a measured split-half reliability of **0.145** over a full season, so roughly 86% of it is noise. It is shrunk by that factor before use, which gives the feature its fairest chance rather than its most flattering one.

The within-season z-score spans **-2.07 to +2.22** across the defence-seasons here. At `d = -0.0153` per standard deviation, moving from the most zone defence to the most man one shifts the log-odds of the over by **0.0657** — about **1.64 percentage points** at an even-money price.

Bootstrap over 96 defence-seasons (400 draws): `d` in **[-0.1188, +0.0659]**. The sandwich says [-0.1028, +0.0721]; a closed form nobody checked against a resample is how this repository shipped two interval defects.

**A `d` that includes zero is no demonstrated edge, in those words.** It does not say coverage is irrelevant to football; it says the closing price already holds whatever this measure of it knows.
