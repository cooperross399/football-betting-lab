# Does recency weighting win the priced test?

Each arm is the **whole** props backtest re-run with one change. The comparison that matters is the pooled return, because a policy that helps one market and hurts two has not helped.

| Arm | Bets | ROI | 95% interval |
|:----|-----:|----:|:-------------|
| baseline (no weighting) | 24,434 | -6.6% | -10.3% to -2.8% |
| half-life 8 games | 21,450 | -5.2% | -9.2% to -1.2% |

**Paired comparison, which is what decides.** Both arms bet the same 172 games, so the difference is measured per game and tested against zero: **+1.4% per bet, 95% interval -1.0% to +3.9%**.

**half-life 8 games returned -5.2% against the baseline's -6.6%, and the difference is not distinguishable from zero.** It does not ship. A higher number on the same data is not a result: the arms' own intervals span several times the gap between them, and the obvious motivation does not override the measurement — which is the entire reason a priced test exists.

1 variant(s) were tested against one bought season. Each spends a degree of freedom, and the verdict file records the count so any report citing it has to say so.

**Beating a baseline that loses is not an edge.** Both arms lose money against real prices; this experiment only decides which loses less, and a policy that ships on that basis is a smaller loss rather than a profit.
