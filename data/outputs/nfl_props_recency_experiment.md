# Does recency weighting win the priced test?

Each arm is the **whole** props backtest re-run with one change. The comparison that matters is the pooled return, because a policy that helps one market and hurts two has not helped.

| Arm | Bets | ROI | 95% interval |
|:----|-----:|----:|:-------------|
| baseline (no weighting) | 31,361 | -5.3% | -8.9% to -1.6% |
| half-life 8 games | 26,648 | -3.1% | -6.8% to +0.6% |

**Paired comparison, which is what decides.** Both arms bet the same 256 games, so the difference is measured per game and tested against zero: **+2.3% per bet, 95% interval +0.1% to +4.5%**.

**half-life 8 games beats the baseline and the difference is distinguishable from zero.** It ships.

1 variant(s) were tested against one bought season. Each spends a degree of freedom, and the verdict file records the count so any report citing it has to say so.

**Beating a baseline that loses is not an edge.** Both arms lose money against real prices; this experiment only decides which loses less, and a policy that ships on that basis is a smaller loss rather than a profit.
