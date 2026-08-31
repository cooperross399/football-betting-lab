# Does recency weighting win the priced test?

Each arm is the **whole** props backtest re-run with one change. The comparison that matters is the pooled return, because a policy that helps one market and hurts two has not helped.

| Arm | Bets | ROI | 95% interval |
|:----|-----:|----:|:-------------|
| baseline (no weighting) | 18,003 | -1.6% | -4.7% to +1.5% |
| half-life 8 games | 16,471 | -2.7% | -6.0% to +0.6% |

**Paired comparison, which is what decides.** Both arms bet the same 256 games, so the difference is measured per game and tested against zero: **-1.8% per bet, 95% interval -4.7% to +1.1%**.

**half-life 8 games returned -2.7% against the baseline's -1.6%, and the difference is not distinguishable from zero.** It does not ship. A higher number on the same data is not a result: the arms' own intervals span several times the gap between them, and the obvious motivation does not override the measurement — which is the entire reason a priced test exists.

1 variant(s) were tested against one bought season. Each spends a degree of freedom, and the verdict file records the count so any report citing it has to say so.

**Beating a baseline that loses is not an edge.** Both arms lose money against real prices; this experiment only decides which loses less, and a policy that ships on that basis is a smaller loss rather than a profit.
