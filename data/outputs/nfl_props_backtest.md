# Do the prop models beat real prices? — 2025

8,393,403 bought price rows across 816 events, collapsed to 627,626 distinct wagers — one player, market, line and side is **one bet**, quoted by up to nine books, and a card takes the best reachable price. Counting each book separately would multiply one wager by nine and narrow every interval by a factor of three while measuring nothing new.

Betting only where the model disagrees by at least 6.0% at a price between -160 and +600. Week 1 is excluded: it has no in-season history, so the fit would be last season's alone.

**This measures the model, not a shippable policy.** No player prop can reach a card at all — inactives are declared ninety minutes before kickoff and no available feed publishes them. A positive result here would be evidence that the model is good and that the availability gate is what blocks shipping.

**Closing-line value cannot be measured here.** These are card-time snapshots; CLV needs the closing snapshot too.

| Market | Bets | Games | Won | Push | Void | ROI | 95% interval | Family-corrected | Verdict |
|:-------|-----:|------:|----:|-----:|-----:|----:|:-------------|:-----------------|:--------|
| `reception_yards` | 10,511 | 255 | 4,219 | 0 | 882 | -7.6% | -12.6% to -2.5% | -15.2% to +0.0% | **no demonstrated edge** |
| `rush_yards` | 4,051 | 254 | 1,838 | 0 | 245 | +0.7% | -7.0% to +8.5% | -10.8% to +12.3% | **no demonstrated edge** |
| `receptions` | 3,474 | 254 | 1,318 | 0 | 270 | -6.1% | -11.7% to -0.6% | -14.4% to +2.1% | **no demonstrated edge** |
| `reception_longest` | 2,976 | 254 | 1,349 | 0 | 276 | -2.9% | -8.8% to +3.1% | -11.8% to +6.1% | **no demonstrated edge** |
| `pass_yards` | 2,534 | 232 | 857 | 0 | 0 | -18.9% | -33.4% to -4.5% | -40.5% to +2.6% | **no demonstrated edge** |
| `rush_attempts` | 1,671 | 252 | 707 | 0 | 54 | -10.8% | -18.9% to -2.8% | -22.8% to +1.2% | **no demonstrated edge** |
| `tackles_assists` | 1,331 | 244 | 755 | 0 | 51 | +12.8% | +6.2% to +19.4% | +2.9% to +22.7% | interval excludes zero, positive |
| `pass_attempts` | 885 | 222 | 382 | 0 | 0 | -0.5% | -15.8% to +14.8% | -23.4% to +22.4% | **no demonstrated edge** |
| `rush_longest` | 837 | 245 | 442 | 0 | 46 | +0.3% | -7.2% to +7.9% | -11.0% to +11.6% | **no demonstrated edge** |
| `pass_completions` | 777 | 226 | 303 | 0 | 0 | -9.1% | -25.0% to +6.8% | -32.9% to +14.7% | **no demonstrated edge** |
| `sacks` | 602 | 227 | 228 | 20 | 68 | +3.7% | -10.5% to +17.9% | -17.6% to +24.9% | **no demonstrated edge** |
| `anytime_td` | 580 | 219 | 139 | 0 | 51 | +3.0% | -12.0% to +18.0% | -19.4% to +25.5% | **no demonstrated edge** |
| `pass_tds` | 279 | 187 | 107 | 0 | 0 | -7.6% | -24.3% to +9.2% | -32.6% to +17.5% | **no demonstrated edge** |
| `kicking_points` | 262 | 158 | 121 | 0 | 2 | -7.5% | -22.9% to +7.8% | -30.5% to +15.5% | **no demonstrated edge** |
| `pass_longest_completion` | 218 | 128 | 118 | 0 | 0 | +2.3% | -13.0% to +17.6% | -20.6% to +25.2% | **no demonstrated edge** |
| `pass_interceptions` | 199 | 156 | 95 | 0 | 0 | +3.4% | -15.2% to +22.1% | -24.5% to +31.4% | **not enough evidence** — 199 bets, below the 200 declared in advance |
| `field_goals` | 105 | 92 | 44 | 0 | 0 | -12.0% | -33.3% to +9.4% | -44.0% to +20.0% | **not enough evidence** — 105 bets, below the 200 declared in advance |
| `defensive_interceptions` | 31 | 27 | 5 | 0 | 4 | -3.2% | -78.6% to +72.2% | -116.2% to +109.7% | **not enough evidence** — 31 bets, below the 200 declared in advance |
| **all markets pooled** | 31,323 | 256 | 13,027 | 20 | 1,949 | -5.2% | -8.9% to -1.5% | -10.7% to +0.3% | **no demonstrated edge** |

The family correction is Bonferroni across the 15 market(s) with at least 200 bets, applied because with twenty markets something will look profitable by chance. Intervals are clustered by game: the props on one afternoon are not independent.

8,073 priced rows named a player who could not be resolved on that season's roster, and produced no opinion. Reported rather than guessed at: a fuzzy match produces a confident price for a bet nobody placed.

## Markets whose interval excludes zero, and whether they survive

**None of what follows can make a candidate a finding.** A result that survives every check below is still one season, and the standard is replication on a season the market was not selected on. These checks only rule out the cheap explanations: a hot fortnight, one absurd afternoon, one player.

| Market | ROI | First half | Second half | Halves agree | Top game | Top 10 games | Without the best game | Players |
|:-------|----:|-----------:|------------:|:-------------|---------:|-------------:|----------------------:|--------:|
| `tackles_assists` | +12.8% | +13.2% (689) | +12.4% (642) | yes | 7% | 52% | +12.0% | 251 |

A result carried by one afternoon shows up as a large top-game share and collapses when it is removed. A result that is really one player shows up in the player count.

**What would settle it: a second season, bought and scored the same way.** That is roughly 99,000 credits — a credit-spend decision, and therefore Cooper's.

A void is a player who never appeared in the box score. The stake comes back; it is not a loss, and it is excluded from the return rather than counted as a zero.
