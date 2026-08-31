# Closing-line value

CLV is the fastest honest signal at these sample sizes. An NFL season is 272 games and roughly six hundred bets separate a real +8% edge from zero, so a season of results is barely a signal — but whether the market agreed with the model by the time it stopped arguing converges far faster.

The backtest takes the **best available** card-time price across nine books, so the comparison is the **best available closing price**. Comparing a best-of-nine entry against a single book's close would manufacture CLV out of shopping.

68,767 bets matched a closing price; 10,006 did not and are excluded rather than counted as zero CLV.

| Market | Bets | Matched | Moved | Toward | Mean CLV | ROI | Reading |
|:-------|-----:|--------:|------:|-------:|---------:|----:|:--------|
| `reception_yards` | 26,022 | 22,024 | 16,312 | 53% | +0.10% | -5.7% | **the market is indifferent** — of 16,312 prices that moved, 53% moved toward the bet. A model with information moves the line toward it more than half the time |
| `rush_yards` | 11,565 | 9,320 | 6,944 | 48% | +0.06% | +0.9% | **the market is indifferent** — of 6,944 prices that moved, 48% moved toward the bet. A model with information moves the line toward it more than half the time |
| `receptions` | 8,659 | 8,542 | 6,815 | 50% | +0.02% | -5.0% | **the market is indifferent** — of 6,815 prices that moved, 50% moved toward the bet. A model with information moves the line toward it more than half the time |
| `pass_yards` | 6,987 | 5,195 | 3,930 | 53% | +0.10% | -5.5% | **no measurable CLV** (+0.10%) |
| `reception_longest` | 5,854 | 5,162 | 3,020 | 55% | +0.14% | -3.3% | **no measurable CLV** (+0.14%) |
| `tackles_assists` | 4,428 | 4,026 | 2,875 | 50% | -0.03% | +12.0% | **the market is indifferent** — of 2,875 prices that moved, 50% moved toward the bet. A model with information moves the line toward it more than half the time |
| `rush_attempts` | 3,532 | 3,269 | 2,451 | 52% | +0.14% | -7.8% | **the market is indifferent** — of 2,451 prices that moved, 52% moved toward the bet. A model with information moves the line toward it more than half the time |
| `rush_longest` | 2,004 | 1,880 | 677 | 47% | -0.03% | -3.3% | **the market is indifferent** — of 677 prices that moved, 47% moved toward the bet. A model with information moves the line toward it more than half the time |
| `anytime_td` | 1,750 | 1,748 | 1,300 | 40% | -0.25% | -2.7% | **no measurable CLV** (-0.25%) |
| `pass_attempts` | 1,863 | 1,743 | 1,157 | 48% | -0.00% | -0.4% | **the market is indifferent** — of 1,157 prices that moved, 48% moved toward the bet. A model with information moves the line toward it more than half the time |
| `pass_completions` | 1,738 | 1,616 | 1,188 | 51% | +0.03% | -6.8% | **the market is indifferent** — of 1,188 prices that moved, 51% moved toward the bet. A model with information moves the line toward it more than half the time |
| `sacks` | 1,057 | 1,045 | 527 | 53% | +0.15% | +2.9% | **the market is indifferent** — of 527 prices that moved, 53% moved toward the bet. A model with information moves the line toward it more than half the time |
| `pass_tds` | 878 | 870 | 647 | 48% | -0.08% | -8.1% | **the market is indifferent** — of 647 prices that moved, 48% moved toward the bet. A model with information moves the line toward it more than half the time |
| `kicking_points` | 739 | 693 | 400 | 52% | +0.06% | -6.5% | **the market is indifferent** — of 400 prices that moved, 52% moved toward the bet. A model with information moves the line toward it more than half the time |
| `pass_interceptions` | 610 | 609 | 399 | 51% | -0.02% | -5.1% | **the market is indifferent** — of 399 prices that moved, 51% moved toward the bet. A model with information moves the line toward it more than half the time |
| `pass_longest_completion` | 644 | 586 | 188 | 54% | +0.06% | +0.5% | **no measurable CLV** (+0.06%) |
| `field_goals` | 400 | 396 | 246 | 52% | +0.01% | -4.8% | **the market is indifferent** — of 246 prices that moved, 52% moved toward the bet. A model with information moves the line toward it more than half the time |
| `defensive_interceptions` | 43 | 43 | 24 | 50% | -0.04% | -34.7% | **not enough evidence** — 43 matched bets, below the 200 declared in advance |
| **pooled** | 78,773 | 68,767 | 49,100 | 51% | +0.06% | -3.2% | **the market is indifferent** — of 49,100 prices that moved, 51% moved toward the bet. A model with information moves the line toward it more than half the time |

Mean CLV is in probability points: positive means the price taken implied a lower probability than the close did, which is the direction that pays. **CLV cannot make a losing model profitable**, and it is reported beside the return rather than instead of it.

**`Moved` and `Toward` are the numbers to read.** A price that did not change carries no information either way, so the question is what the ones that did change did. A model with information moves the line toward it more than half the time.

A mean below **0.5%** reads as *no measurable CLV*, not as positive or negative. With this many bets almost any departure from zero is statistically distinguishable and two hundredths of a point still cannot matter to anyone.
