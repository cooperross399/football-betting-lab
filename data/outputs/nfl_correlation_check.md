# Is the model's joint better than its marginals?

Every other instrument here measures **marginal** skill — can the model beat the price on one leg — and the answer is a flat no. This measures a different quantity. The compound simulation draws opportunities once and reads receptions, yards and longest off **the same draws**, so a joint distribution falls out of how it is built. A joint can be right while the marginals are wrong.

## Does the simulated correlation match the realised one?

| Pair | Realised | Model | Error | Games | Matched? |
|:---|---:|---:|---:|---:|:---|
| receptions x reception_yards | 0.800 | 0.814 | +0.014 | 3,872 | yes |
| reception_yards x reception_longest | 0.792 | 0.835 | +0.043 | 3,872 | yes |
| rush_attempts x rush_yards | 0.848 | 0.866 | +0.017 | 2,253 | yes |
| rush_yards x rush_longest | 0.789 | 0.786 | -0.003 | 2,253 | yes |

**All 4 pair(s) matched within 0.10.** The joint is accurate where the marginals are not, which is the one asymmetry this lab has found.

## How far is reality from independence?

| Legs | Side | Combinations | Realised P(both) | Independence | Ratio |
|:---|:---|---:|---:|---:|---:|
| reception_yards + receptions | over | 36,233 | 0.237 | 0.144 | 1.65x |
| reception_longest + reception_yards | over | 30,191 | 0.303 | 0.184 | 1.64x |
| reception_yards + rush_yards | over | 10,987 | 0.180 | 0.167 | 1.07x |
| reception_yards + receptions | under | 10,841 | 0.345 | 0.214 | 1.61x |
| rush_attempts + rush_yards | over | 10,556 | 0.195 | 0.158 | 1.24x |
| reception_longest + receptions | over | 8,012 | 0.225 | 0.168 | 1.34x |
| pass_completions + pass_yards | over | 7,593 | 0.187 | 0.147 | 1.27x |
| rush_attempts + rush_yards | under | 7,400 | 0.396 | 0.248 | 1.59x |
| reception_longest + reception_yards | under | 6,595 | 0.393 | 0.258 | 1.53x |
| pass_attempts + pass_yards | over | 6,330 | 0.177 | 0.152 | 1.17x |
| pass_completions + pass_yards | under | 5,248 | 0.345 | 0.240 | 1.44x |
| anytime_td + reception_yards | over | 5,198 | 0.120 | 0.095 | 1.26x |

## What this is not

**This is the size of the correlation, not the size of an edge.** Modern books apply correlation adjustments to same-game parlays; they do not price independence. The independence column shows how much work a book's SGP model has to do, not how much of it that model gets wrong.

The edge, if there is one, is the gap between a book's correlation model and the true one — and **that gap cannot be measured without same-game-parlay prices, which this lab has never bought.** Until those exist, an accurate joint is a promising asset and not a demonstrated edge, in those words.

**And the marginals still have to be fixed.** A parlay's price is P(A) x P(B|A): a perfect copula on overconfident marginals still produces a wrong joint probability. The calibration maps exist for exactly that, and a joint built on raw model probabilities would inherit a 0.3 overconfidence at every leg.
