# Does settlement agree with what the books priced?

Both sides of a featured line are quoted, so the two prices devig to the market's own probability of the over. **That is what the outcome should match** — not a half, which would flag a 0.5-line touchdown market where a 13% over rate is exactly right. Where the realised rate sits well below the priced one, every bet in that market is scored against a smaller quantity than the book priced.

**That failure replicates perfectly across seasons**, because a constant offset is constant. It is the one defect that survives every check a backtest can run on itself, which is why this screen exists and why it runs before any result is believed.

| Market | Featured wagers | Priced over | Realised over | Gap | Worth to a one-sided model | Charted | Reading |
|:-------|----------------:|------------:|--------------:|----:|--------------------------:|:--------|:--------|

**No market is a settlement suspect.**

**Passing the screen is not a clean bill of health.** A wager at about even money returns roughly two units of ROI per unit of probability the outcome is mispriced by, so the *worth* column is what each gap hands a model that consistently takes the side it favours. A three-point gap is inside the tolerance and worth six points of return, which can be most of a market's measured edge.

The screen fires when the realised over rate sits more than 4% from the devigged price, on at least 200 featured wagers. Loose on purpose: four points is already larger than any edge this lab could plausibly have, and a screen that fires on everything is ignored.
