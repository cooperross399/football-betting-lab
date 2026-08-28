# Closing-line value

CLV is the fastest honest signal at these sample sizes. An NFL season is 272 games and roughly six hundred bets separate a real +8% edge from zero, so a season of results is barely a signal — but whether the market agreed with the model by the time it stopped arguing converges far faster.

The backtest takes the **best available** card-time price across nine books, so the comparison is the **best available closing price**. Comparing a best-of-nine entry against a single book's close would manufacture CLV out of shopping.

114,423 bets matched a closing price; 15,419 did not and are excluded rather than counted as zero CLV.

| Market | Bets | Matched | Moved | Toward | Mean CLV | ROI | Reading |
|:-------|-----:|--------:|------:|-------:|---------:|----:|:--------|
| `reception_yards` | 39,109 | 32,902 | 24,391 | 52% | +0.10% | +4.5% | **the market is indifferent** — of 24,391 prices that moved, 52% moved toward the bet. A model with information moves the line toward it more than half the time |
| `rush_yards` | 16,829 | 13,518 | 10,072 | 48% | +0.04% | +13.0% | **the market is indifferent** — of 10,072 prices that moved, 48% moved toward the bet. A model with information moves the line toward it more than half the time |
| `receptions` | 12,918 | 12,708 | 10,164 | 50% | +0.03% | +6.8% | **the market is indifferent** — of 10,164 prices that moved, 50% moved toward the bet. A model with information moves the line toward it more than half the time |
| `sacks` | 8,795 | 8,725 | 4,559 | 54% | +0.11% | -11.8% | **no measurable CLV** (+0.11%) |
| `reception_longest` | 8,917 | 7,837 | 4,575 | 54% | +0.11% | +2.5% | **no measurable CLV** (+0.11%) beside a +2.5% return — the market did not move toward these bets |
| `pass_yards` | 10,638 | 7,826 | 5,972 | 54% | +0.11% | +3.1% | **no measurable CLV** (+0.11%) beside a +3.1% return — the market did not move toward these bets |
| `tackles_assists` | 6,267 | 5,717 | 4,112 | 49% | -0.03% | +15.0% | **the market is indifferent** — of 4,112 prices that moved, 49% moved toward the bet. A model with information moves the line toward it more than half the time |
| `rush_attempts` | 5,153 | 4,765 | 3,562 | 53% | +0.19% | +6.6% | **no measurable CLV** (+0.19%) beside a +6.6% return — the market did not move toward these bets |
| `rush_longest` | 3,050 | 2,837 | 1,012 | 46% | -0.04% | +3.8% | **no measurable CLV** (-0.04%) beside a +3.8% return — the market did not move toward these bets |
| `pass_interceptions` | 2,750 | 2,741 | 1,745 | 48% | -0.09% | -10.2% | **the market is indifferent** — of 1,745 prices that moved, 48% moved toward the bet. A model with information moves the line toward it more than half the time |
| `anytime_td` | 2,632 | 2,607 | 1,920 | 39% | -0.27% | +7.5% | **no measurable CLV** (-0.27%) beside a +7.5% return — the market did not move toward these bets |
| `pass_attempts` | 2,762 | 2,593 | 1,767 | 47% | +0.00% | +5.9% | **the market is indifferent** — of 1,767 prices that moved, 47% moved toward the bet. A model with information moves the line toward it more than half the time |
| `pass_completions` | 2,663 | 2,469 | 1,835 | 51% | +0.02% | +1.2% | **the market is indifferent** — of 1,835 prices that moved, 51% moved toward the bet. A model with information moves the line toward it more than half the time |
| `pass_tds` | 2,354 | 2,346 | 1,690 | 52% | +0.03% | +0.2% | **the market is indifferent** — of 1,690 prices that moved, 52% moved toward the bet. A model with information moves the line toward it more than half the time |
| `field_goals` | 1,436 | 1,427 | 917 | 54% | +0.21% | -3.2% | **no measurable CLV** (+0.21%) |
| `defensive_interceptions` | 1,193 | 1,176 | 659 | 46% | -0.06% | -28.8% | **no measurable CLV** (-0.06%) |
| `kicking_points` | 1,212 | 1,150 | 673 | 53% | +0.10% | -0.7% | **no measurable CLV** (+0.10%) |
| `pass_longest_completion` | 953 | 873 | 273 | 48% | -0.00% | -2.6% | **the market is indifferent** — of 273 prices that moved, 48% moved toward the bet. A model with information moves the line toward it more than half the time |
| `rush_tds` | 150 | 148 | 125 | 52% | +0.08% | -36.3% | **not enough evidence** — 148 matched bets, below the 200 declared in advance |
| `reception_tds` | 61 | 58 | 37 | 51% | +0.09% | -31.2% | **not enough evidence** — 58 matched bets, below the 200 declared in advance |
| **pooled** | 129,842 | 114,423 | 80,060 | 51% | +0.06% | +4.1% | **the market is indifferent** — of 80,060 prices that moved, 51% moved toward the bet. A model with information moves the line toward it more than half the time |

Mean CLV is in probability points: positive means the price taken implied a lower probability than the close did, which is the direction that pays. **CLV cannot make a losing model profitable**, and it is reported beside the return rather than instead of it.

**`Moved` and `Toward` are the numbers to read.** A price that did not change carries no information either way, so the question is what the ones that did change did. A model with information moves the line toward it more than half the time.

A mean below **0.5%** reads as *no measurable CLV*, not as positive or negative. With this many bets almost any departure from zero is statistically distinguishable and two hundredths of a point still cannot matter to anyone.
