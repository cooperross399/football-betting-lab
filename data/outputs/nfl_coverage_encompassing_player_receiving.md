# Does man coverage say anything the price does not?

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

## placebo: rates reassigned across defences

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

The feature covers **12,729 of 30,836 wagers** (41.3%). Rows without a prior-season rate are a relocated or expansion-less club-season and are excluded here rather than imputed.

The receiver's man-minus-zone differential has a measured split-half reliability of **0.145** over a full season, so roughly 86% of it is noise. It is shrunk by that factor before use, which gives the feature its fairest chance rather than its most flattering one.

The within-season z-score spans **-2.07 to +2.22** across the defence-seasons here. At `d = +0.0014` per standard deviation, moving from the most zone defence to the most man one shifts the log-odds of the over by **0.0059** — about **0.15 percentage points** at an even-money price.

Bootstrap over 96 defence-seasons (400 draws): `d` in **[-0.0951, +0.0817]**. The sandwich says [-0.0835, +0.0863]; a closed form nobody checked against a resample is how this repository shipped two interval defects.

**A `d` that includes zero is no demonstrated edge, in those words.** It does not say coverage is irrelevant to football; it says the closing price already holds whatever this measure of it knows.
