# Week 1, 2026 — matchup board

Profiles are the **2025 season**, which for Week 1 is what exists. Every figure is a z-score across the league that season, never a raw rate: league-wide levels move between seasons and a raw number is two different rulers.

**This is context, not a card.** Six features built from these feeds have been tested against the closing line and all six returned no demonstrated edge. A layer agreeing with another layer describes a matchup; it does not price one. The layers are also correlated with each other by construction, so four of them agreeing is closer to one opinion than to four.

## What each layer is worth

Carryover of relative position, measured by `scripts/run_feature_reliability.py`: how well the statistic describes the same club a year later. **A layer near zero cannot carry a read however confident the prose around it sounds.**

| layer | carryover | |
|:--|--:|:--|
| average depth of target faced | +0.782 | usable |
| rush yards before contact | +0.674 | usable |
| blitz rate, 5+ | +0.548 | usable |
| rush yards after contact | +0.500 | usable |
| completion % allowed | +0.458 | usable |
| pressure rate generated | +0.439 | usable |
| man coverage rate | +0.435 | usable |
| pressure rate allowed | +0.391 | weak |

## The games

`spread` is from the home side: positive means the home club is favoured by it. Implied totals are `(total ± spread) / 2`.

| kickoff | game | spread | total | implied (A/H) | rush edge A | rush edge H | pass edge A | pass edge H |
|:--|:--|--:|--:|:--|--:|--:|--:|--:|
| 2026-09-09 20:20 | NE @ SEA | +3.0 | 44.5 | 20.75 / 23.75 | -0.21 | -0.01 | +1.03 | -0.10 |
| 2026-09-10 20:35 | SF @ LA | +3.5 | 48.5 | 22.50 / 26.00 | -2.89 | -0.49 | +0.09 | +2.24 |
| 2026-09-13 13:00 | CHI @ CAR | -3.0 | 47.5 | 25.25 / 22.25 | +0.32 | -1.67 | +1.24 | -0.47 |
| 2026-09-13 13:00 | TB @ CIN | +3.5 | 50.5 | 23.50 / 27.00 | +0.64 | -1.81 | +1.16 | -0.17 |
| 2026-09-13 13:00 | NO @ DET | +7.0 | 49.5 | 21.25 / 28.25 | -0.66 | -0.37 | -1.06 | +0.49 |
| 2026-09-13 13:00 | BUF @ HOU | -1.5 | 44.5 | 23.00 / 21.50 | +0.99 | -1.32 | -0.34 | -0.82 |
| 2026-09-13 13:00 | BAL @ IND | -3.5 | 47.5 | 25.50 / 22.00 | -0.06 | +0.07 | -0.04 | +0.64 |
| 2026-09-13 13:00 | CLE @ JAX | +8.5 | 40.5 | 16.00 / 24.50 | +2.26 | +0.41 | -3.68 | -1.04 |
| 2026-09-13 13:00 | ATL @ PIT | +3.5 | 42.5 | 19.50 / 23.00 | -1.29 | -0.48 | -0.27 | -0.40 |
| 2026-09-13 13:00 | NYJ @ TEN | +1.5 | 39.5 | 19.00 / 20.50 | +0.28 | +0.21 | -0.23 | +0.26 |
| 2026-09-13 16:25 | ARI @ LAC | +9.5 | 47.5 | 19.00 / 28.50 | +0.13 | -0.11 | -1.09 | +0.73 |
| 2026-09-13 16:25 | MIA @ LV | +3.5 | 41.5 | 19.00 / 22.50 | -0.53 | -0.02 | +0.08 | -0.56 |
| 2026-09-13 16:25 | GB @ MIN | +1.5 | 46.5 | 22.50 / 24.00 | +0.87 | +1.37 | +0.24 | -1.13 |
| 2026-09-13 16:25 | WAS @ PHI | +5.5 | 44.5 | 19.50 / 25.00 | -0.70 | +0.62 | -1.02 | +1.82 |
| 2026-09-13 20:20 | DAL @ NYG | -3.0 | 48.5 | 25.75 / 22.75 | +3.22 | -0.74 | +1.07 | +1.73 |
| 2026-09-14 20:15 | DEN @ KC | +3.0 | 43.5 | 20.25 / 23.25 | +1.37 | +0.60 | +0.41 | -0.81 |

**Pass-rush edge** adds a club's own pressure rate generated to the pressure its opponent's line allowed, both as z-scores, because the two halves point the same way. Both halves are CLUB-level and carry +0.439 and +0.391 — not the +0.884 that belongs to an individual defender's pressures per game, which is a different statistic and is not what this column is built from. Even that stronger one was **no demonstrated edge** against the price when tested directly on sack markets.

## The per-club profiles

| club | pressure rate generated | pressure rate allowed | man coverage rate | blitz rate, 5+ | completion % allowed | average depth of target faced | rush yards before contact | rush yards after contact |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|
| ARI | -1.37 | -0.22 | -0.36 | -0.02 | +0.85 | -0.15 | +0.23 | -0.33 |
| ATL | +0.39 | -0.32 | +0.22 | +1.33 | -0.83 | +1.58 | +0.01 | +0.68 |
| BAL | -0.60 | +0.20 | +0.16 | -0.65 | -0.13 | +0.63 | +2.10 | +0.94 |
| BUF | +1.30 | -1.49 | -0.07 | -0.19 | -1.41 | +0.32 | +1.13 | +0.73 |
| CAR | -2.72 | +0.75 | -1.41 | -0.05 | +0.01 | +0.26 | -0.07 | -0.20 |
| CHI | -0.42 | +1.05 | +1.64 | +0.23 | +0.54 | +1.00 | +1.94 | -1.08 |
| CIN | -0.21 | -0.63 | +0.66 | -1.72 | +0.65 | -0.80 | -0.30 | -0.21 |
| CLE | +1.58 | +1.05 | +1.31 | +0.12 | +0.27 | -1.03 | -2.12 | +1.28 |
| DAL | +0.54 | -0.78 | -0.78 | +0.18 | +2.06 | +0.24 | +0.43 | +0.54 |
| DEN | +1.13 | -0.49 | +1.72 | +0.96 | -1.65 | +1.25 | +0.03 | -0.06 |
| DET | +0.56 | -0.09 | +1.48 | +0.27 | -0.66 | +2.93 | +1.22 | -0.52 |
| GB | +0.20 | +0.14 | -1.44 | -0.96 | +0.42 | -0.52 | -0.45 | -0.13 |
| HOU | +0.17 | -0.32 | -0.03 | -0.80 | -1.62 | +0.89 | -1.22 | -0.06 |
| IND | -0.13 | +0.53 | +0.77 | +0.15 | -0.01 | -0.00 | -0.13 | +0.99 |
| JAX | -0.64 | +0.68 | -0.86 | -0.01 | -0.55 | +0.17 | -0.51 | -0.13 |
| KC | +1.10 | +0.24 | +0.71 | +1.09 | +1.19 | -1.63 | +0.74 | -1.47 |
| LA | +0.64 | -0.77 | -0.64 | -1.17 | -0.56 | -0.26 | +0.68 | -0.02 |
| LAC | +0.11 | +1.50 | -1.11 | -1.14 | -1.74 | -0.40 | +0.34 | -0.12 |
| LV | -0.68 | +0.37 | -1.34 | -0.87 | +1.50 | -0.72 | -2.68 | +0.52 |
| MIA | -0.90 | +0.66 | -0.46 | +1.00 | +1.44 | -0.53 | -0.97 | +3.02 |
| MIN | +1.23 | +0.68 | -1.74 | +3.31 | -0.25 | -2.11 | -0.23 | +0.99 |
| NE | -0.08 | -0.97 | +0.10 | +0.84 | -0.56 | -0.20 | +0.05 | +0.03 |
| NO | -0.58 | -0.93 | -1.32 | -0.31 | -0.03 | +0.05 | -1.39 | -0.80 |
| NYG | +0.04 | +2.67 | +1.16 | +0.54 | +0.08 | -0.04 | +0.59 | -0.97 |
| NYJ | -1.64 | +0.42 | +1.19 | +0.16 | +0.24 | -0.39 | +1.14 | -0.50 |
| PHI | +0.84 | -1.09 | +1.60 | -1.35 | -1.96 | +1.19 | +0.38 | -1.33 |
| PIT | -0.15 | -1.68 | +0.70 | +0.71 | +0.39 | -1.76 | -0.77 | +0.85 |
| SEA | +0.96 | -0.13 | -0.37 | -1.18 | -0.74 | -0.98 | -0.20 | -0.43 |
| SF | -2.12 | -1.13 | -0.70 | -0.84 | +0.92 | -0.50 | -0.56 | -1.62 |
| TB | +1.27 | -1.60 | -0.20 | +1.17 | +0.02 | +0.67 | +0.55 | -1.63 |
| TEN | -0.21 | +1.92 | -0.63 | -0.82 | +1.30 | +0.58 | +0.07 | -0.61 |
| WAS | +0.39 | -0.22 | +0.04 | +0.02 | +0.80 | +0.28 | -0.02 | +1.69 |

## Offensive identity and efficiency

From play-by-play and Next Gen Stats, prior season, z-scored across the league. Ranked left to right by how well each describes the same club a year later — **the leftmost columns are scheme identity, which carries hardest; the rightmost are defensive, which carries least.** That ordering is the finding: 21 of 24 metrics measured on both sides of the ball carry better on offence than on defence.

| club | shotgun rate (offence) | no-huddle rate (offence) | pass rate over expected (offence) | receiver separation (offence) | time to throw (offence) | success rate, dropbacks (offence) | QB hits allowed (offence) | points per drive (offence) | EPA per dropback (offence) | third-down rate (offence) | EPA per dropback allowed (defence) | stuff rate (defence) | havoc rate (defence) |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| ARI | +0.55 | +0.22 | +1.84 | -0.48 | +0.29 | -0.14 | +0.80 | -0.47 | -0.16 | +0.46 | +1.06 | +1.07 | -0.39 |
| ATL | +1.29 | +0.11 | -1.15 | +0.30 | -0.51 | -0.10 | -0.61 | -0.55 | -0.28 | -1.40 | -0.34 | -1.17 | +0.65 |
| BAL | -0.13 | -0.66 | -1.93 | +1.72 | +0.51 | +0.20 | +0.58 | +0.57 | -0.20 | +0.32 | +0.39 | +0.10 | -0.59 |
| BUF | -1.49 | -0.36 | -0.36 | +2.36 | +0.42 | +0.84 | -0.81 | +1.65 | +1.18 | +1.20 | -0.97 | -0.00 | +1.58 |
| CAR | +0.05 | -0.35 | -1.12 | -1.26 | -0.14 | -0.45 | +0.05 | -0.73 | -0.56 | -0.77 | +0.66 | -1.10 | -0.50 |
| CHI | -1.24 | -0.47 | -0.48 | +2.20 | +3.12 | -0.19 | -1.22 | +0.59 | +0.57 | +0.74 | +0.08 | -1.46 | +0.18 |
| CIN | +1.44 | -0.68 | +1.17 | -0.72 | -0.89 | -0.02 | -0.02 | -0.16 | -0.50 | +0.90 | +1.20 | -2.03 | -1.57 |
| CLE | +0.17 | -0.08 | -0.42 | -1.67 | +1.11 | -2.65 | +1.88 | -2.21 | -2.31 | -1.34 | -1.36 | +1.65 | +2.58 |
| DAL | -0.32 | -0.07 | +0.38 | -0.63 | -0.14 | +0.67 | -0.15 | +1.20 | +0.92 | +0.38 | +1.75 | +0.54 | +0.08 |
| DEN | -0.10 | +0.28 | +1.13 | +0.29 | +0.20 | -0.16 | -1.23 | -0.01 | +0.53 | +0.39 | -1.09 | +0.16 | -1.51 |
| DET | -1.28 | -0.36 | -0.67 | +0.47 | -1.26 | +0.64 | +1.33 | +1.28 | +1.00 | -0.16 | -0.32 | -0.61 | -1.06 |
| GB | -0.29 | -0.11 | -0.62 | -0.82 | +0.54 | +1.18 | +0.02 | +1.06 | +1.67 | +2.12 | +0.42 | -1.01 | -0.63 |
| HOU | -0.37 | -0.58 | +0.38 | -1.05 | -0.73 | -0.25 | -0.74 | -0.36 | +0.15 | -0.51 | -1.52 | -0.12 | +0.68 |
| IND | +0.51 | -0.45 | +0.40 | -0.78 | -1.55 | +0.34 | -0.29 | +1.61 | +0.26 | +0.70 | +0.15 | +0.62 | +0.09 |
| JAX | -0.50 | -0.29 | +1.15 | -0.79 | +0.23 | +0.33 | -0.50 | +0.39 | +0.32 | -0.07 | -1.37 | -0.15 | +0.10 |
| KC | +1.31 | -0.70 | +1.83 | +1.46 | -0.28 | +0.11 | +0.93 | +0.41 | +0.28 | -0.47 | -0.12 | +0.05 | -0.30 |
| LA | -2.26 | -0.32 | +1.54 | — | — | +1.65 | -0.65 | +1.43 | +1.41 | +0.02 | -0.86 | -2.21 | -1.12 |
| LAC | +0.49 | -0.58 | +0.86 | -0.84 | +0.30 | -0.10 | +1.64 | +0.07 | -0.33 | +1.44 | -0.93 | +1.10 | +1.70 |
| LAR | — | — | — | -1.25 | -0.36 | — | — | — | — | — | — | — | — |
| LV | +0.05 | -0.11 | +0.16 | +0.90 | -0.47 | -1.05 | +1.26 | -1.74 | -1.63 | -1.29 | +0.49 | +1.46 | +1.26 |
| MIA | +0.51 | -0.60 | -1.05 | +0.72 | -1.41 | -0.54 | -0.69 | -0.26 | -0.40 | -1.05 | +1.07 | +0.15 | -0.19 |
| MIN | -0.93 | -0.22 | +0.32 | +0.94 | +0.50 | -0.88 | +1.97 | -0.92 | -1.55 | -1.75 | -1.43 | +0.56 | +1.67 |
| NE | -1.06 | -0.71 | +1.38 | -0.21 | +1.16 | +2.12 | -0.01 | +0.92 | +2.06 | +0.78 | -0.71 | -0.14 | +0.28 |
| NO | +1.17 | +1.22 | -0.22 | +0.26 | -1.45 | -0.12 | -0.68 | -1.32 | -0.74 | -0.01 | -0.51 | +0.43 | +0.15 |
| NYG | +0.98 | +1.10 | -0.70 | +0.03 | -0.07 | -0.61 | +0.98 | +0.21 | -0.02 | +0.16 | +0.15 | +0.80 | +0.39 |
| NYJ | +0.68 | -0.01 | -1.91 | +0.17 | +0.04 | -1.29 | +1.29 | -1.35 | -1.45 | -1.04 | +2.14 | +1.24 | -0.89 |
| PHI | +1.00 | +0.88 | -0.06 | -1.13 | +1.21 | -0.27 | -1.36 | -0.13 | +0.23 | -0.53 | -0.98 | -1.44 | -0.87 |
| PIT | +0.06 | +0.16 | +0.46 | -0.05 | -2.07 | -0.43 | -1.15 | -0.17 | -0.06 | +0.12 | +0.02 | -0.68 | +0.17 |
| SEA | -1.77 | -0.24 | -1.32 | +0.75 | +0.16 | +1.55 | -0.88 | +0.10 | +0.61 | +0.07 | -1.03 | +0.27 | +0.23 |
| SF | -1.10 | -0.59 | +0.41 | -0.54 | +0.87 | +1.63 | -0.44 | +1.14 | +0.95 | +2.34 | +0.83 | -0.12 | -0.76 |
| TB | -0.05 | -0.35 | -0.35 | -0.69 | -0.08 | -0.40 | -1.72 | -0.39 | -0.04 | +0.40 | +0.32 | +1.43 | +0.80 |
| TEN | +0.65 | +0.03 | -0.46 | +0.53 | +1.25 | -2.06 | +0.73 | -1.85 | -1.88 | -1.73 | +1.22 | +1.15 | -0.49 |
| WAS | +1.95 | +4.88 | -0.58 | -0.17 | -0.48 | +0.48 | -0.29 | -0.02 | -0.04 | -0.44 | +1.58 | -0.56 | -1.71 |

| layer | carryover |
|:--|--:|
| shotgun rate (offence) | +0.709 |
| no-huddle rate (offence) | +0.565 |
| pass rate over expected (offence) | +0.497 |
| receiver separation (offence) | +0.457 |
| time to throw (offence) | +0.453 |
| success rate, dropbacks (offence) | +0.441 |
| QB hits allowed (offence) | +0.430 |
| points per drive (offence) | +0.419 |
| EPA per dropback (offence) | +0.411 |
| third-down rate (offence) | +0.407 |
| EPA per dropback allowed (defence) | +0.206 |
| stuff rate (defence) | +0.378 |
| havoc rate (defence) | +0.330 |

## What is not here

- **Player prop prices.** Paid provider; not fetched. Nothing above prices a player market.
- **The role and injury layer.** 0 report rows carry a status for Week 1 so far — clubs file on the Wednesday. An empty layer is shown empty rather than filled with zeroes that would read as "nobody is hurt".
- **Coach and player quotes.** Proprietary, with no free equivalent, and the layer with the least behind it: a feed that scores almost every team positive cannot discriminate between them.

Game, play-by-play, participation charting, roster, depth chart, snap count, advanced split and injury data from nflverse (https://github.com/nflverse/nflverse-data), used under CC-BY-4.0.
