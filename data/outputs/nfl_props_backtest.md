# Do the prop models beat real prices? — 2024

8,393,403 bought price rows across 816 events, collapsed to 627,626 distinct wagers — one player, market, line and side is **one bet**, quoted by up to nine books, and a card takes the best reachable price. Counting each book separately would multiply one wager by nine and narrow every interval by a factor of three while measuring nothing new.

Betting only where the model disagrees by at least 6.0% at a price between -160 and +600. Week 1 is excluded: it has no in-season history, so the fit would be last season's alone.

**This measures the model, not a shippable policy.** No player prop can reach a card at all — inactives are declared ninety minutes before kickoff and no available feed publishes them. A positive result here would be evidence that the model is good and that the availability gate is what blocks shipping.

**Closing-line value cannot be measured here.** These are card-time snapshots; CLV needs the closing snapshot too.

| Market | Bets | Games | Won | Push | Void | ROI | 95% interval | Family-corrected | Verdict |
|:-------|-----:|------:|----:|-----:|-----:|----:|:-------------|:-----------------|:--------|
| `reception_yards` | 10,096 | 254 | 4,005 | 0 | 715 | -5.2% | -11.2% to +0.9% | -14.3% to +4.0% | **no demonstrated edge** |
| `rush_yards` | 4,608 | 254 | 2,044 | 0 | 208 | +3.1% | -5.2% to +11.4% | -9.4% to +15.6% | **no demonstrated edge** |
| `receptions` | 3,164 | 255 | 1,182 | 0 | 225 | -6.3% | -12.7% to +0.2% | -16.0% to +3.4% | **no demonstrated edge** |
| `pass_yards` | 2,935 | 243 | 1,268 | 0 | 10 | +7.9% | -5.1% to +20.8% | -11.6% to +27.3% | **no demonstrated edge** |
| `reception_longest` | 1,740 | 250 | 817 | 0 | 144 | -5.4% | -11.7% to +0.9% | -14.9% to +4.1% | **no demonstrated edge** |
| `tackles_assists` | 1,657 | 248 | 963 | 0 | 87 | +10.9% | +6.3% to +15.5% | +3.9% to +17.9% | interval excludes zero, positive |
| `rush_attempts` | 1,152 | 246 | 522 | 0 | 54 | -7.2% | -15.8% to +1.4% | -20.2% to +5.8% | **no demonstrated edge** |
| `rush_longest` | 675 | 228 | 339 | 0 | 19 | -3.0% | -12.2% to +6.2% | -16.9% to +10.8% | **no demonstrated edge** |
| `pass_completions` | 527 | 216 | 244 | 0 | 1 | -9.6% | -20.6% to +1.4% | -26.2% to +7.0% | **no demonstrated edge** |
| `anytime_td` | 519 | 221 | 127 | 0 | 48 | +5.0% | -13.5% to +23.6% | -22.9% to +33.0% | **no demonstrated edge** |
| `pass_attempts` | 513 | 212 | 255 | 0 | 1 | -5.1% | -16.3% to +6.2% | -22.1% to +11.9% | **no demonstrated edge** |
| `sacks` | 513 | 197 | 207 | 10 | 44 | +5.2% | -10.8% to +21.3% | -19.0% to +29.4% | **no demonstrated edge** |
| `pass_tds` | 313 | 189 | 109 | 0 | 1 | -3.2% | -20.4% to +13.9% | -29.1% to +22.7% | **no demonstrated edge** |
| `pass_longest_completion` | 239 | 131 | 130 | 0 | 0 | +3.0% | -14.0% to +20.0% | -22.7% to +28.6% | **no demonstrated edge** |
| `kicking_points` | 234 | 145 | 102 | 0 | 2 | -12.6% | -29.0% to +3.8% | -37.3% to +12.1% | **no demonstrated edge** |
| `pass_interceptions` | 216 | 166 | 98 | 0 | 0 | -6.6% | -21.2% to +8.0% | -28.6% to +15.4% | **no demonstrated edge** |
| `field_goals` | 112 | 93 | 46 | 0 | 3 | -19.4% | -36.3% to -2.6% | -44.8% to +5.9% | **not enough evidence** — 112 bets, below the 200 declared in advance |
| `defensive_interceptions` | 15 | 12 | 2 | 0 | 4 | -30.7% | -119.5% to +58.1% | -164.6% to +103.2% | **not enough evidence** — 15 bets, below the 200 declared in advance |
| `rush_tds` | 1 | 1 | 0 | 0 | 0 | -100.0% | -inf% to +inf% | -inf% to +inf% | **not enough evidence** — 1 bets, below the 200 declared in advance |
| **all markets pooled** | 29,229 | 256 | 12,460 | 10 | 1,566 | -1.6% | -5.0% to +1.8% | -6.7% to +3.6% | **no demonstrated edge** |

The family correction is Bonferroni across the 16 market(s) with at least 200 bets, applied because with twenty markets something will look profitable by chance. Intervals are clustered by game: the props on one afternoon are not independent.

6,662 priced rows named a player who could not be resolved on that season's roster, and produced no opinion. Reported rather than guessed at: a fuzzy match produces a confident price for a bet nobody placed.

## Markets whose interval excludes zero, and whether they survive

**None of what follows can make a candidate a finding.** A result that survives every check below is still one season, and the standard is replication on a season the market was not selected on. These checks only rule out the cheap explanations: a hot fortnight, one absurd afternoon, one player.

| Market | ROI | First half | Second half | Halves agree | Top game | Top 10 games | Without the best game | Players |
|:-------|----:|-----------:|------------:|:-------------|---------:|-------------:|----------------------:|--------:|
| `tackles_assists` | +10.9% | +15.9% (924) | +4.6% (733) | **no** | 4% | 32% | +10.5% | 302 |

A result carried by one afternoon shows up as a large top-game share and collapses when it is removed. A result that is really one player shows up in the player count.

**What would settle it: a second season, bought and scored the same way.** That is roughly 99,000 credits — a credit-spend decision, and therefore Cooper's.

A void is a player who never appeared in the box score. The stake comes back; it is not a loss, and it is excluded from the return rather than counted as a zero.
