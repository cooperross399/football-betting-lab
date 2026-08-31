# Does the model know anything the price does not?

Measured over **74,345 scored bets** on **768 games** across seasons 2023, 2024, 2025.

Every other instrument here asks whether a return is real. This one asks the question underneath. A model that loses money might be unlucky; **a model with a worse Brier score than the market is not unlucky, it is uninformed** — and no betting rule, subgroup or filter can rescue it, because every wager it places is an opinion worse than the price it pays for.

The market's implied probability **includes the vig**, so it is an over-estimate and it is being scored with a handicap. The comparison is tilted in the model's favour throughout.

## Is the model's probability honest?

| Model says | Bets | Actually happens | Market says | Model error | Market error |
|:---|---:|---:|---:|---:|---:|
| (0.0, 0.35] | 7,550 | 0.174 | 0.195 | -0.117 | -0.021 |
| (0.35, 0.45] | 7,902 | 0.258 | 0.276 | -0.142 | -0.018 |
| (0.45, 0.5] | 4,041 | 0.311 | 0.337 | -0.164 | -0.025 |
| (0.5, 0.55] | 4,689 | 0.366 | 0.385 | -0.160 | -0.019 |
| (0.55, 0.6] | 8,449 | 0.448 | 0.465 | -0.133 | -0.018 |
| (0.6, 0.65] | 14,417 | 0.485 | 0.510 | -0.139 | -0.024 |
| (0.65, 0.7] | 11,110 | 0.511 | 0.520 | -0.163 | -0.009 |
| (0.7, 0.8] | 11,487 | 0.507 | 0.523 | -0.235 | -0.017 |
| (0.8, 1.0] | 4,700 | 0.547 | 0.523 | -0.314 | +0.024 |

**Brier: model 0.26057, market 0.22703** over 74,345 bets. Lower is better.

## Walk-forward calibration

The map is fitted on prior seasons only. A calibration fitted on the season it scores is not a forecast, it is a description.

| Season | Bets | Model Brier | **Calibrated** Brier | Market Brier | Better than the price? |
|:---|---:|---:|---:|---:|:---|
| 2024 | 27,732 | 0.26153 | **0.23104** | 0.22756 | no |
| 2025 | 29,998 | 0.25710 | **0.22524** | 0.22329 | no |

**The model is never a better forecaster than the price, on any held-out season, even after calibration and even with the vig handicapping the market.** That is the whole answer. The problem is not the betting rule, the threshold or the choice of market: there is no information here that the price does not already carry, so there is no subgroup of it that can be profitable except by chance.

Calibration is still worth having — it cuts the loss materially — but a smaller loss is not a profit, and this table is the reason no filter will turn one into the other.

Calibration can rule a model out and never rule one in. Where this report rules one out, it is decisive; where it does not, it has only failed to.
