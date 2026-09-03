# Does the model know anything the price does not?

Every other instrument here asks whether a *return* is real. This one asks the question underneath: fitting

    logit P(over) = a + b*logit(p_market_devigged) + c*logit(p_model)

**if `c` cannot be told from zero, the model adds nothing to the price** and no threshold or subgroup built on it can be profitable except by chance. The market probability is devigged **per book** before the books are combined, because devigging a best-of-N over against a best-of-N under invents a market with far less hold than anyone quoted.

## The answer

**`c` = +0.0695, 95% interval [+0.0324, +0.1066] over 61,267 wagers across 762 games.** The interval excludes zero: the model carries a little information the devigged price does not.

**pooled, in sample** — 61,267 wagers, 762 games

| term | estimate | SE | 95% interval | |
|:--|--:|--:|:--|:--|
| `intercept` | -0.0333 | 0.0196 | [-0.0717, +0.0050] | includes zero |
| `b  logit(market)` | +0.9016 | 0.0323 | [+0.8384, +0.9648] | excludes zero |
| `c  logit(model)` | +0.0695 | 0.0189 | [+0.0324, +0.1066] | excludes zero |

**fitted without 2025** — 41,724 wagers, 506 games

| term | estimate | SE | 95% interval | |
|:--|--:|--:|:--|:--|
| `intercept` | -0.0068 | 0.0256 | [-0.0569, +0.0434] | includes zero |
| `b  logit(market)` | +0.8904 | 0.0342 | [+0.8233, +0.9575] | excludes zero |
| `c  logit(model)` | +0.0685 | 0.0238 | [+0.0218, +0.1152] | excludes zero |

## The interval, checked against a resample rather than asserted

The clustered standard error is a hand-rolled sandwich, and this repository has shipped two interval defects — one sqrt(games) too narrow on the forward ledger, one pairing a ratio point estimate with an unweighted standard error. So `c` is also estimated by resampling **games** with replacement.

| | standard error | 95% interval |
|:--|--:|:--|
| sandwich | 0.01894 | [+0.0324, +0.1066] |
| bootstrap over games | 0.01960 | [+0.0352, +0.1089] |

The sandwich is **0.966x** the resample. Both intervals exclude zero.

## The placebo, which runs every time

The model probability is shuffled within market and the fit repeated. A harness that returns a positive `c` on shuffled input is measuring its own plumbing.

`c` on shuffled input = **+0.0081**, interval [-0.0101, +0.0262] over 61,267 wagers — includes zero — the harness does not manufacture the result.

## And what it is worth, which is the part that decides anything

| forecaster | out-of-sample Brier |
|:--|--:|
| the raw model | 0.27871 |
| the devigged market price | 0.24742 |
| market alone, refitted | 0.24728 |
| market + model | 0.24700 |

**Adding the model to the price improves out-of-sample Brier by 0.00028.** For scale, this lab declared a 0.002 threshold in advance for whether crossing the inactives deadline was worth anything, and called the answer no at +0.00085. This is smaller than that.

The blend's own edge on the wagers the card selected is **negative**: mean -0.0107, median -0.0143, against a raw model edge whose median is +0.1357. The median two-sided book hold is **6.78%**, so a wager must beat a half-hold of 3.39% to be worth taking, and only **1.52%** of them do.

### Betting the blend, out of sample

| rule | bets | games | ROI | 95% interval | |
|:--|--:|--:|--:|:--|:--|
| the card as it stands, 2025 | 19,543 | 256 | -1.79% | [-4.47%, +0.89%] | **no demonstrated edge** |
| blend edge >= 0.00 | 3,593 | 255 | +1.30% | [-3.23%, +5.82%] | **no demonstrated edge** |
| blend edge >= 0.01 | 1,752 | 254 | +3.09% | [-2.96%, +9.14%] | **no demonstrated edge** |
| blend edge >= 0.02 | 823 | 228 | -0.35% | [-9.72%, +9.01%] | **no demonstrated edge** |
| blend edge >= 0.03 | 394 | 178 | -4.20% | [-18.38%, +9.99%] | **no demonstrated edge** |
| blend edge >= 0.05 | 107 | 49 | -20.10% | [-52.25%, +12.05%] | **no demonstrated edge** |

**Read the shape of that column, not its best row.** The return rises to a threshold and then falls away, which is what a scan over thresholds does to noise — a real edge strengthens as the filter tightens. Every interval includes zero, the thresholds were scanned rather than declared in advance, and the two positive rows are the two a reader would want to believe. **No demonstrated edge**, in those words.

## Per season, and per market

| cut | wagers | games | `c` | 95% interval | |
|:--|--:|--:|--:|:--|:--|
| season 2023 | 17,150 | 251 | +0.0624 | [-0.0058, +0.1305] | includes zero |
| season 2024 | 24,574 | 255 | +0.0705 | [+0.0053, +0.1357] | excludes zero |
| season 2025 | 19,543 | 256 | +0.0778 | [+0.0148, +0.1408] | excludes zero |
| `pass_attempts` | 1,495 | 623 | +0.0595 | [-0.0407, +0.1597] | includes zero |
| `pass_completions` | 1,375 | 626 | -0.0042 | [-0.1028, +0.0944] | includes zero |
| `pass_yards` | 5,141 | 664 | -0.0133 | [-0.1250, +0.0985] | includes zero |
| `reception_longest` | 4,866 | 749 | +0.0970 | [-0.0042, +0.1982] | includes zero |
| `reception_yards` | 19,162 | 759 | +0.0910 | [+0.0151, +0.1669] | excludes zero |
| `receptions` | 6,808 | 757 | +0.1037 | [+0.0399, +0.1675] | excludes zero |
| `rush_attempts` | 2,728 | 737 | +0.0605 | [-0.0113, +0.1324] | includes zero |
| `rush_longest` | 2,063 | 698 | +0.0629 | [-0.0700, +0.1958] | includes zero |
| `rush_yards` | 9,788 | 757 | +0.0549 | [-0.0223, +0.1320] | includes zero |
| `sacks` | 1,010 | 409 | +0.0917 | [-0.2620, +0.4455] | includes zero |
| `tackles_assists` | 3,578 | 727 | +0.1100 | [+0.0254, +0.1945] | excludes zero |

**Selection does not bias any of this.** The bets file holds only wagers the card selected at edge >= 6% against the vigged price, but selection is a deterministic function of the REGRESSORS and not of the outcome, so the conditional mean is unbiased. What it costs is support: the low-edge region is absent, so every number here speaks for the population the card actually bets.
