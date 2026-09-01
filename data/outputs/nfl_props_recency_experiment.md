# Does recency weighting win the priced test?

Each arm is the **whole** props backtest re-run with one change. The comparison that matters is the pooled return, because a policy that helps one market and hurts two has not helped.

| Arm | Bets | ROI | 95% interval |
|:----|-----:|----:|:-------------|
| baseline (no weighting) | 78,693 | -3.1% | -8.9% to +1.6% |
| half-life 8 games | 68,666 | -2.7% | -6.8% to +1.2% |

**Paired comparison, which is what decides.** Both arms bet the same 768 games, so the difference is measured per game and tested against zero: **-0.1% per bet, 95% interval -1.5% to +1.4%**.

**And it has to hold in every season, not on their average.** This script used to score one season and write a verdict file with one name, so whether the policy shipped depended on which season had been run last.

| Season | Games | Paired difference | 95% interval | Clears? |
|:---|---:|---:|:---|:---|
| 2023 | 256 | -1.8% | -4.7% to +1.1% | **no** |
| 2024 | 256 | -0.7% | -3.0% to +1.6% | **no** |
| 2025 | 256 | +2.3% | +0.1% to +4.5% | yes |

**half-life 8 games returned -2.7% against the baseline's -3.1%, and the difference is not distinguishable from zero.** It does not ship. A higher number on the same data is not a result: the arms' own intervals span several times the gap between them, and the obvious motivation does not override the measurement — which is the entire reason a priced test exists.

1 variant(s) were tested against one bought season. Each spends a degree of freedom, and the verdict file records the count so any report citing it has to say so.

**Beating a baseline that loses is not an edge.** Both arms lose money against real prices; this experiment only decides which loses less, and a policy that ships on that basis is a smaller loss rather than a profit.
