# Does the model know anything the price does not?

Measured over **78,253 scored bets** on **768 games** across seasons 2023, 2024, 2025.

Every other instrument here asks whether a return is real. This one asks the question underneath. A model that loses money might be unlucky; **a model with a worse Brier score than the market is not unlucky, it is uninformed** — and no betting rule, subgroup or filter can rescue it, because every wager it places is an opinion worse than the price it pays for.

The market's implied probability **includes the vig**, so it is an over-estimate and it is being scored with a handicap. The comparison is tilted in the model's favour throughout.

## Is the model's probability honest?

| Model says | Bets | Actually happens | Market says | Model error | Market error |
|:---|---:|---:|---:|---:|---:|
| (0.0, 0.35] | 7,710 | 0.179 | 0.195 | -0.113 | -0.016 |
| (0.35, 0.45] | 8,034 | 0.258 | 0.277 | -0.142 | -0.018 |
| (0.45, 0.5] | 4,109 | 0.308 | 0.337 | -0.168 | -0.030 |
| (0.5, 0.55] | 4,969 | 0.369 | 0.387 | -0.157 | -0.018 |
| (0.55, 0.6] | 8,921 | 0.446 | 0.466 | -0.134 | -0.020 |
| (0.6, 0.65] | 15,131 | 0.491 | 0.510 | -0.134 | -0.019 |
| (0.65, 0.7] | 11,815 | 0.510 | 0.521 | -0.164 | -0.011 |
| (0.7, 0.8] | 12,504 | 0.512 | 0.525 | -0.230 | -0.013 |
| (0.8, 1.0] | 5,060 | 0.545 | 0.525 | -0.316 | +0.020 |

**Brier: model 0.26106, market 0.22782** over 78,253 bets. Lower is better.

## Walk-forward calibration

The map is fitted on prior seasons only. A calibration fitted on the season it scores is not a forecast, it is a description.

| Season | Bets | Model Brier | **Calibrated** Brier | Market Brier | Better than the price? |
|:---|---:|---:|---:|---:|:---|
| 2024 | 29,165 | 0.26222 | **0.23178** | 0.22827 | no |
| 2025 | 31,393 | 0.25691 | **0.22573** | 0.22390 | no |

## Per market, on held-out seasons only

Pooled Brier answers *does this model know anything*. It cannot answer *does it know anything **here***, and a model with no skill on average could still carry skill in one family and noise everywhere else. Each market's calibration map is its own, fitted on its own earlier seasons.

| Market | Held-out bets | Calibrated Brier | Market Brier | Better than the price? |
|:---|---:|---:|---:|:---|
| `sacks` | 585 | 0.22017 | 0.21907 | no |
| `reception_yards` | 20,729 | 0.22554 | 0.22342 | no |
| `rush_longest` | 1,503 | 0.25124 | 0.24775 | no |
| `reception_longest` | 4,763 | 0.24160 | 0.23772 | no |
| `pass_yards` | 5,413 | 0.22992 | 0.22586 | no |
| `rush_attempts` | 2,826 | 0.22486 | 0.22024 | no |
| `receptions` | 6,655 | 0.21914 | 0.21442 | no |
| `rush_yards` | 8,699 | 0.23835 | 0.23337 | no |
| `anytime_td` | 1,104 | 0.18599 | 0.18081 | no |
| `pass_completions` | 1,286 | 0.22964 | 0.22427 | no |
| `tackles_assists` | 2,848 | 0.24254 | 0.23603 | no |
| `pass_attempts` | 1,413 | 0.23971 | 0.23224 | no |

**No market forecasts better than the price** — 0 of 12 with at least 500 held-out bets. The pooled result was not hiding a good family inside a bad average.

**The model is never a better forecaster than the price, on any held-out season, even after calibration and even with the vig handicapping the market.** That is the whole answer. The problem is not the betting rule, the threshold or the choice of market: there is no information here that the price does not already carry, so there is no subgroup of it that can be profitable except by chance.

Calibration is still worth having — it cuts the loss materially — but a smaller loss is not a profit, and this table is the reason no filter will turn one into the other.

Calibration can rule a model out and never rule one in. Where this report rules one out, it is decisive; where it does not, it has only failed to.
