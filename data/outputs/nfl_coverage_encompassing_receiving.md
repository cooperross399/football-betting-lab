# Does man coverage say anything the price does not?

## market and model only

30,836 wagers, 96 clusters.

| term | estimate | 95% interval | tells from zero |
|:--|--:|:--|:--|
| intercept | -0.0114 | [-0.0697, +0.0469] | no |
| b  logit(market) | +0.9743 | [+0.8829, +1.0656] | yes |
| c  logit(model) | +0.0952 | [+0.0360, +0.1543] | yes |

## with man rate faced

30,836 wagers, 96 clusters.

| term | estimate | 95% interval | tells from zero |
|:--|--:|:--|:--|
| intercept | -0.0114 | [-0.0696, +0.0469] | no |
| b  logit(market) | +0.9741 | [+0.8831, +1.0652] | yes |
| c  logit(model) | +0.0953 | [+0.0363, +0.1543] | yes |
| d  man rate faced (z) | +0.0094 | [-0.0520, +0.0709] | no |

## placebo: rates reassigned across defences

30,836 wagers, 96 clusters.

| term | estimate | 95% interval | tells from zero |
|:--|--:|:--|:--|
| intercept | -0.0124 | [-0.0690, +0.0441] | no |
| b  logit(market) | +0.9731 | [+0.8840, +1.0623] | yes |
| c  logit(model) | +0.0971 | [+0.0379, +0.1563] | yes |
| d  man rate faced (z) | +0.0588 | [-0.0026, +0.1201] | no |

## What the estimate means in probability

The feature covers **30,836 of 30,836 wagers** (100.0%). Rows without a prior-season rate are a relocated or expansion-less club-season and are excluded here rather than imputed.

The within-season z-score spans **-2.07 to +2.22** across the defence-seasons here. At `d = +0.0094` per standard deviation, moving from the most zone defence to the most man one shifts the log-odds of the over by **0.0405** — about **1.01 percentage points** at an even-money price.

Bootstrap over 96 defence-seasons (400 draws): `d` in **[-0.0472, +0.0761]**. The sandwich says [-0.0520, +0.0709]; a closed form nobody checked against a resample is how this repository shipped two interval defects.

**A `d` that includes zero is no demonstrated edge, in those words.** It does not say coverage is irrelevant to football; it says the closing price already holds whatever this measure of it knows.
