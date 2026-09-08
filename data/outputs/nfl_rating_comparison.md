# EPA ratings against points ratings

816 games, 3 season(s) (2023-2025), refitted 171 times — once per game-day, from data strictly earlier.

| target | points rater | EPA rater | paired difference | 95% interval | better? |
|:--|--:|--:|--:|:--|:--|
| mean absolute error, margin, EPA per game | 10.584 | 10.606 | -0.022 | [-0.106, +0.063] | no difference shown |
| mean absolute error, margin, EPA per play | 10.584 | 10.608 | -0.024 | [-0.110, +0.063] | no difference shown |
| mean absolute error, total, EPA per game | 10.504 | 10.770 | -0.266 | [-0.438, -0.087] | **EPA WORSE** |
| mean absolute error, total, EPA per play | 10.504 | 10.763 | -0.259 | [-0.430, -0.081] | **EPA WORSE** |

## Dispersion against signal

Mean absolute error alone cannot separate *carries less information* from *carries the same information, spread too wide*, and those have opposite remedies: the first needs a different feature, the second only needs heavier shrinkage.

| target | prediction sd | correlation with the result |
|:--|--:|--:|
| **actual margin** | 14.34 | — |
| points rater, margin | 4.22 | 0.3011 |
| EPA rater, margin | 4.92 | 0.3012 |
| **actual total** | 13.57 | — |
| points rater, total | 3.08 | 0.1720 |
| EPA rater, total | 4.20 | 0.1236 |

Predicting the league-average total for every game scores **10.640** mean absolute error. Any rater above that number is worse than not modelling totals at all.

## What this test could have found

- **margin, EPA per game**: standard error 0.043 points, so the minimum detectable improvement at 80% power is **0.121 points of mean absolute error**. The observed difference is -0.022. The interval includes zero: **no demonstrated improvement**, and an improvement smaller than 0.121 points would have been missed more often than not.
- **margin, EPA per play**: standard error 0.044 points, so the minimum detectable improvement at 80% power is **0.124 points of mean absolute error**. The observed difference is -0.024. The interval includes zero: **no demonstrated improvement**, and an improvement smaller than 0.124 points would have been missed more often than not.
- **total, EPA per game**: standard error 0.090 points, so the minimum detectable improvement at 80% power is **0.251 points of mean absolute error**. The observed difference is -0.266. **The interval excludes zero on the WRONG side — this is a demonstrated regression, not a null.**
- **total, EPA per play**: standard error 0.089 points, so the minimum detectable improvement at 80% power is **0.250 points of mean absolute error**. The observed difference is -0.259. **The interval excludes zero on the WRONG side — this is a demonstrated regression, not a null.**

Both raters shrink a team toward the league mean with the same prior and both read the same history, so this isolates the estimator. Neither is compared against a price here — a better forecast and a profitable one are different claims, and this file only supports the first.
