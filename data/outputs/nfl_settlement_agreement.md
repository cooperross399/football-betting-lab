# Does settlement agree with what the books priced?

Both sides of a featured line are quoted, so the two prices devig to the market's own probability of the over. **That is what the outcome should match** — not a half, which would flag a 0.5-line touchdown market where a 13% over rate is exactly right. Where the realised rate sits well below the priced one, every bet in that market is scored against a smaller quantity than the book priced.

**That failure replicates perfectly across seasons**, because a constant offset is constant. It is the one defect that survives every check a backtest can run on itself, which is why this screen exists and why it runs before any result is believed.

| Market | Featured wagers | Priced over | Realised over | Gap | Worth to a one-sided model | Charted | Reading |
|:-------|----------------:|------------:|--------------:|----:|--------------------------:|:--------|:--------|
| `anytime_td` | 1,193 | 20% | 19% | -1% | 2% | no | agrees with the price |
| `field_goals` | 1,496 | 49% | 52% | +3% | 7% | no | agrees with the price |
| `kicking_points` | 1,729 | 50% | 53% | +4% | 7% | no | agrees with the price |
| `pass_attempts` | 2,541 | 50% | 48% | -2% | 5% | no | agrees with the price |
| `pass_completions` | 2,599 | 50% | 50% | +0% | 0% | no | agrees with the price |
| `pass_interceptions` | 1,731 | 44% | 42% | -2% | 4% | no | agrees with the price |
| `pass_longest_completion` | 2,795 | 50% | 48% | -2% | 4% | no | agrees with the price |
| `pass_tds` | 1,658 | 46% | 46% | -0% | 1% | no | agrees with the price |
| `pass_yards` | 10,579 | 50% | 50% | +0% | 1% | no | agrees with the price |
| `reception_longest` | 12,926 | 50% | 49% | -1% | 1% | no | agrees with the price |
| `reception_yards` | 36,073 | 48% | 47% | -0% | 1% | no | agrees with the price |
| `receptions` | 11,412 | 47% | 46% | -1% | 2% | no | agrees with the price |
| `rush_attempts` | 3,881 | 50% | 48% | -2% | 4% | no | agrees with the price |
| `rush_longest` | 5,023 | 50% | 47% | -3% | 5% | no | agrees with the price |
| `rush_yards` | 16,672 | 48% | 46% | -2% | 4% | no | agrees with the price |
| `sacks` | 4,141 | 33% | 32% | -2% | 3% | yes | agrees with the price |
| `tackles_assists` | 6,575 | 50% | 48% | -1% | 3% | yes | agrees with the price |

**No market is a settlement suspect.**

**Passing the screen is not a clean bill of health.** A wager at about even money returns roughly two units of ROI per unit of probability the outcome is mispriced by, so the *worth* column is what each gap hands a model that consistently takes the side it favours. A three-point gap is inside the tolerance and worth six points of return, which can be most of a market's measured edge.

The screen fires when the realised over rate sits more than 4% from the devigged price, on at least 200 featured wagers. Loose on purpose: four points is already larger than any edge this lab could plausibly have, and a screen that fires on everything is ignored.
