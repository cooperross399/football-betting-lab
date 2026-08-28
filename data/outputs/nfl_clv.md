# Closing-line value

CLV is the fastest honest signal at these sample sizes. An NFL season is 272 games and roughly six hundred bets separate a real +8% edge from zero, so a season of results is barely a signal — but whether the market agreed with the model by the time it stopped arguing converges far faster.

The backtest takes the **best available** card-time price across nine books, so the comparison is the **best available closing price**. Comparing a best-of-nine entry against a single book's close would manufacture CLV out of shopping.

132,630 bets matched a closing price; 8,610 did not and are excluded rather than counted as zero CLV.

| Market | Bets | Matched | Mean CLV | Positive | ROI | Reading |
|:-------|-----:|--------:|---------:|---------:|----:|:--------|
| `reception_yards` | 43,104 | 39,564 | +0.01% | 23% | +4.6% | **no measurable CLV** (+0.01%) beside a +4.6% return — the market did not move toward these bets |
| `rush_yards` | 18,948 | 17,025 | +0.02% | 24% | +12.4% | **no measurable CLV** (+0.02%) beside a +12.4% return — the market did not move toward these bets |
| `receptions` | 14,470 | 14,378 | +0.01% | 24% | +8.2% | **no measurable CLV** (+0.01%) beside a +8.2% return — the market did not move toward these bets |
| `pass_yards` | 11,256 | 9,573 | +0.03% | 23% | +1.3% | **no measurable CLV** (+0.03%) |
| `reception_longest` | 9,767 | 9,234 | +0.03% | 19% | +2.0% | **no measurable CLV** (+0.03%) beside a +2.0% return — the market did not move toward these bets |
| `sacks` | 9,160 | 9,144 | +0.05% | 13% | -11.9% | **no measurable CLV** (+0.05%) |
| `tackles_assists` | 6,812 | 6,568 | +0.02% | 18% | +16.3% | **no measurable CLV** (+0.02%) beside a +16.3% return — the market did not move toward these bets |
| `rush_attempts` | 5,661 | 5,497 | +0.06% | 23% | +7.5% | **no measurable CLV** (+0.06%) beside a +7.5% return — the market did not move toward these bets |
| `rush_longest` | 3,332 | 3,209 | +0.01% | 9% | +3.8% | **no measurable CLV** (+0.01%) beside a +3.8% return — the market did not move toward these bets |
| `pass_interceptions` | 2,920 | 2,913 | -0.02% | 16% | -12.6% | **no measurable CLV** (-0.02%) |
| `pass_attempts` | 2,876 | 2,796 | +0.02% | 20% | +5.7% | **no measurable CLV** (+0.02%) beside a +5.7% return — the market did not move toward these bets |
| `pass_completions` | 2,818 | 2,720 | -0.02% | 20% | -0.7% | **no measurable CLV** (-0.02%) |
| `anytime_td` | 2,685 | 2,673 | +0.02% | 24% | +9.8% | **no measurable CLV** (+0.02%) beside a +9.8% return — the market did not move toward these bets |
| `pass_tds` | 2,398 | 2,396 | -0.03% | 23% | +0.0% | **no measurable CLV** (-0.03%) |
| `field_goals` | 1,420 | 1,414 | +0.12% | 19% | -2.7% | **no measurable CLV** (+0.12%) |
| `kicking_points` | 1,223 | 1,201 | +0.08% | 18% | +2.4% | **no measurable CLV** (+0.08%) beside a +2.4% return — the market did not move toward these bets |
| `defensive_interceptions` | 1,186 | 1,175 | +0.01% | 13% | -27.2% | **no measurable CLV** (+0.01%) |
| `pass_longest_completion` | 1,025 | 975 | -0.01% | 9% | -2.4% | **no measurable CLV** (-0.01%) |
| `rush_tds` | 131 | 129 | +0.01% | 17% | -52.8% | **not enough evidence** — 129 matched bets, below the 200 declared in advance |
| `reception_tds` | 48 | 46 | -0.06% | 15% | -28.9% | **not enough evidence** — 46 matched bets, below the 200 declared in advance |
| **pooled** | 141,240 | 132,630 | +0.02% | 21% | +4.3% | **no measurable CLV** (+0.02%) beside a +4.3% return — the market did not move toward these bets |

Mean CLV is in probability points: positive means the price taken implied a lower probability than the close did, which is the direction that pays. **CLV cannot make a losing model profitable**, and it is reported beside the return rather than instead of it.

A mean below **0.5%** reads as *no measurable CLV*, not as positive or negative. With this many bets almost any departure from zero is statistically distinguishable and two hundredths of a point still cannot matter to anyone.
