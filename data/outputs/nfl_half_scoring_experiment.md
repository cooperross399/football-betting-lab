# Does the first-half model beat real first-half prices?

2,380 bought first-half prices over 183 events, 0 of which could not be matched to a half-time score and were excluded rather than guessed at.

| Market | Bets | Won | Push | ROI | 95% interval | Verdict |
|:-------|-----:|----:|-----:|----:|:-------------|:--------|
| `moneyline_h1` | 125 | 36 | 10 | -16.7% | -38.6% to +5.3% | **not enough evidence** — 125 bets |
| `spread_h1` | 255 | 113 | 5 | -12.7% | -30.5% to +5.1% | **no demonstrated edge** |
| `total_points_h1` | 239 | 91 | 4 | -20.5% | -40.2% to -0.8% | excludes zero |
| **pooled** | 619 | 240 | 19 | -16.5% | -29.5% to -3.5% | excludes zero |

These markets are currently priced by nothing, so every row of them lands in `no_opinion` and accumulates no forward evidence. Shipping this model would change that — and shipping a model measured to lose would also fill the ledger with opinions already known to be wrong. **That is a trade Cooper decides, not this script**, and the verdict below records only what was measured.

Bets need 200 before a number is offered. Below that the verdict is *not enough evidence*.
