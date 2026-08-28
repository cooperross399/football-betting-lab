# Do the prop models beat real prices? — 2025

767,947 bought price rows across 183 events, collapsed to 188,045 distinct wagers — one player, market, line and side is **one bet**, quoted by up to nine books, and a card takes the best reachable price. Counting each book separately would multiply one wager by nine and narrow every interval by a factor of three while measuring nothing new.

Betting only where the model disagrees by at least 6.0% at a price between -160 and +600. Week 1 is excluded: it has no in-season history, so the fit would be last season's alone.

**This measures the model, not a shippable policy.** No player prop can reach a card at all — inactives are declared ninety minutes before kickoff and no available feed publishes them. A positive result here would be evidence that the model is good and that the availability gate is what blocks shipping.

**Closing-line value cannot be measured here.** These are card-time snapshots; CLV needs the closing snapshot too.

| Market | Bets | Games | Won | Push | Void | ROI | 95% interval | Family-corrected | Verdict |
|:-------|-----:|------:|----:|-----:|-----:|----:|:-------------|:-----------------|:--------|
| `reception_yards` | 7,403 | 172 | 2,952 | 0 | 606 | -7.8% | -13.8% to -1.9% | -16.8% to +1.1% | **no demonstrated edge** |
| `rush_yards` | 2,789 | 171 | 1,235 | 0 | 171 | -2.8% | -11.9% to +6.2% | -16.4% to +10.7% | **no demonstrated edge** |
| `receptions` | 2,426 | 171 | 923 | 0 | 181 | -4.1% | -11.0% to +2.7% | -14.4% to +6.2% | **no demonstrated edge** |
| `sacks` | 2,164 | 169 | 601 | 73 | 196 | -14.2% | -22.7% to -5.6% | -27.0% to -1.4% | interval excludes zero, negative |
| `reception_longest` | 2,135 | 171 | 958 | 0 | 166 | -3.7% | -10.6% to +3.3% | -14.1% to +6.8% | **no demonstrated edge** |
| `pass_yards` | 1,608 | 159 | 561 | 0 | 0 | -18.2% | -35.7% to -0.7% | -44.4% to +8.1% | **no demonstrated edge** |
| `rush_attempts` | 1,161 | 171 | 478 | 0 | 52 | -11.8% | -21.8% to -1.7% | -26.8% to +3.3% | **no demonstrated edge** |
| `tackles_assists` | 941 | 164 | 543 | 0 | 37 | +16.2% | +8.3% to +24.2% | +4.3% to +28.1% | interval excludes zero, positive |
| `pass_attempts` | 605 | 148 | 244 | 0 | 0 | -6.6% | -24.4% to +11.2% | -33.3% to +20.1% | **no demonstrated edge** |
| `rush_longest` | 582 | 165 | 300 | 0 | 34 | -2.1% | -11.3% to +7.1% | -15.9% to +11.7% | **no demonstrated edge** |
| `pass_interceptions` | 547 | 171 | 180 | 0 | 0 | -12.8% | -26.2% to +0.6% | -32.8% to +7.3% | **no demonstrated edge** |
| `pass_completions` | 519 | 150 | 203 | 0 | 0 | -11.9% | -28.2% to +4.3% | -36.3% to +12.4% | **no demonstrated edge** |
| `anytime_td` | 400 | 150 | 100 | 0 | 44 | +12.0% | -8.0% to +31.9% | -17.9% to +41.9% | **no demonstrated edge** |
| `pass_tds` | 346 | 150 | 100 | 0 | 0 | -11.6% | -29.3% to +6.1% | -38.1% to +14.8% | **no demonstrated edge** |
| `defensive_interceptions` | 344 | 137 | 50 | 0 | 25 | -9.7% | -32.5% to +13.2% | -43.9% to +24.5% | **no demonstrated edge** |
| `kicking_points` | 177 | 105 | 88 | 0 | 1 | -2.6% | -19.5% to +14.2% | -27.8% to +22.5% | **not enough evidence** — 177 bets, below the 200 declared in advance |
| `field_goals` | 170 | 96 | 70 | 0 | 1 | -7.2% | -27.2% to +12.8% | -37.1% to +22.8% | **not enough evidence** — 170 bets, below the 200 declared in advance |
| `pass_longest_completion` | 153 | 92 | 82 | 0 | 0 | +1.2% | -17.1% to +19.5% | -26.1% to +28.5% | **not enough evidence** — 153 bets, below the 200 declared in advance |
| **all markets pooled** | 24,470 | 172 | 9,668 | 73 | 1,514 | -6.7% | -10.5% to -2.9% | -12.4% to -1.1% | interval excludes zero, negative |

The family correction is Bonferroni across the 15 market(s) with at least 200 bets, applied because with twenty markets something will look profitable by chance. Intervals are clustered by game: the props on one afternoon are not independent.

6,396 priced rows named a player who could not be resolved on that season's roster, and produced no opinion. Reported rather than guessed at: a fuzzy match produces a confident price for a bet nobody placed.

## Markets whose interval excludes zero, and whether they survive

**None of what follows can make a candidate a finding.** A result that survives every check below is still one season, and the standard is replication on a season the market was not selected on. These checks only rule out the cheap explanations: a hot fortnight, one absurd afternoon, one player.

| Market | ROI | First half | Second half | Halves agree | Top game | Top 10 games | Without the best game | Players |
|:-------|----:|-----------:|------------:|:-------------|---------:|-------------:|----------------------:|--------:|
| `sacks` | -14.2% | -13.5% (1192) | -15.0% (972) | yes | -7% | -49% | -15.3% | 235 |
| `tackles_assists` | +16.2% | +17.8% (484) | +14.5% (457) | yes | 7% | 57% | +15.1% | 223 |

A result carried by one afternoon shows up as a large top-game share and collapses when it is removed. A result that is really one player shows up in the player count.

**What would settle it: a second season, bought and scored the same way.** That is roughly 99,000 credits — a credit-spend decision, and therefore Cooper's.

A void is a player who never appeared in the box score. The stake comes back; it is not a loss, and it is excluded from the return rather than counted as a zero.
