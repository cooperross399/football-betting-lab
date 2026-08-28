# Does settlement agree with what the books priced?

Both sides of a featured line are quoted, so the two prices devig to the market's own probability of the over. **That is what the outcome should match** — not a half, which would flag a 0.5-line touchdown market where a 13% over rate is exactly right. Where the realised rate sits well below the priced one, every bet in that market is scored against a smaller quantity than the book priced.

**That failure replicates perfectly across seasons**, because a constant offset is constant. It is the one defect that survives every check a backtest can run on itself, which is why this screen exists and why it runs before any result is believed.

| Market | Featured wagers | Priced over | Realised over | Gap | Worth to a one-sided model | Charted | Reading |
|:-------|----------------:|------------:|--------------:|----:|--------------------------:|:--------|:--------|
| `tackles_assists` | 6,494 | 50% | 42% | -7% | 15% | yes | **settlement suspect** — outcomes land 7% below what the price implied; this market settles on a charted quantity |
| `anytime_td` | 1,193 | 20% | 19% | -1% | 2% | no | agrees with the price |
| `field_goals` | 1,454 | 49% | 53% | +4% | 7% | no | agrees with the price |
| `kicking_points` | 1,678 | 50% | 54% | +4% | 7% | no | agrees with the price |
| `pass_attempts` | 2,479 | 50% | 48% | -2% | 5% | no | agrees with the price |
| `pass_completions` | 2,550 | 50% | 50% | -0% | 0% | no | agrees with the price |
| `pass_interceptions` | 1,689 | 44% | 42% | -2% | 3% | no | agrees with the price |
| `pass_longest_completion` | 2,712 | 50% | 49% | -1% | 2% | no | agrees with the price |
| `pass_tds` | 1,618 | 46% | 45% | -1% | 2% | no | agrees with the price |
| `pass_yards` | 10,335 | 50% | 50% | +1% | 1% | no | agrees with the price |
| `reception_longest` | 12,670 | 50% | 49% | -0% | 1% | no | agrees with the price |
| `reception_yards` | 35,641 | 48% | 47% | -0% | 1% | no | agrees with the price |
| `receptions` | 11,254 | 47% | 46% | -1% | 2% | no | agrees with the price |
| `rush_attempts` | 3,810 | 50% | 48% | -2% | 4% | no | agrees with the price |
| `rush_longest` | 4,924 | 50% | 47% | -3% | 6% | no | agrees with the price |
| `rush_yards` | 16,453 | 48% | 46% | -2% | 4% | no | agrees with the price |
| `sacks` | 4,059 | 33% | 31% | -2% | 4% | yes | agrees with the price |

**1 market(s) are settlement suspects**, and 1 of them settle on a charted quantity: `tackles_assists`.

A settlement suspect's measured edge is **not evidence of anything** until an independent source settles the question. It is not a small caveat: an offset of half a unit was enough to turn a three-season, family-corrected, split-half-stable +16% into the vig.

**Passing the screen is not a clean bill of health.** A wager at about even money returns roughly two units of ROI per unit of probability the outcome is mispriced by, so the *worth* column is what each gap hands a model that consistently takes the side it favours. A three-point gap is inside the tolerance and worth six points of return, which can be most of a market's measured edge.

The screen fires when the realised over rate sits more than 4% from the devigged price, on at least 200 featured wagers. Loose on purpose: four points is already larger than any edge this lab could plausibly have, and a screen that fires on everything is ignored.
