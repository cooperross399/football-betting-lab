# Does the first-half model beat real first-half prices?

10,640 bought first-half prices over 272 events, 0 of which could not be matched to a half-time score and were excluded rather than guessed at.

| Market | Bets | Won | Push | ROI | 95% interval | Verdict |
|:-------|-----:|----:|-----:|----:|:-------------|:--------|
| `moneyline_h1` | 559 | 201 | 46 | +2.4% | -16.4% to +21.3% | **no demonstrated edge** |
| `spread_h1` | 1,169 | 622 | 20 | +4.4% | -9.8% to +18.5% | **no demonstrated edge** |
| `total_points_h1` | 1,138 | 452 | 20 | -17.2% | -33.0% to -1.4% | interval excludes zero, **negative** |
| **pooled** | 2,866 | 1,275 | 86 | -4.6% | -15.2% to +6.1% | **no demonstrated edge** |

These markets are currently priced by nothing, so every row of them lands in `no_opinion` and accumulates no forward evidence. Shipping this model would change that — and shipping a model measured to lose would also fill the ledger with opinions already known to be wrong. **That is a trade Cooper decides, not this script**, and the verdict below records only what was measured.

Bets need 200 before a number is offered. Below that the verdict is *not enough evidence*.
