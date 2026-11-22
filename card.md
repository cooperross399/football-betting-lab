# NFL card — 2026-11-22

This card is **accumulating evidence, not making recommendations.**

**28 market(s) have a reviewed approval**: `alternate_spread`, `alternate_team_total`, `alternate_total_points`, `anytime_td`, `defensive_interceptions`, `field_goals`, `kicking_points`, `moneyline`, `moneyline_h1`, `pass_attempts`, `pass_completions`, `pass_interceptions`, `pass_longest_completion`, `pass_tds`, `pass_yards`, `reception_longest`, `reception_yards`, `receptions`, `rush_attempts`, `rush_longest`, `rush_yards`, `sacks`, `spread`, `spread_h1`, `tackles_assists`, `team_total`, `total_points`, `total_points_h1`. Every other market is priced, frozen into the forward ledger, and excluded from selection with a stated reason.

## Slate (11 game(s))

- Arizona Cardinals @ Kansas City Chiefs
- Baltimore Ravens @ Carolina Panthers
- Jacksonville Jaguars @ New York Giants
- Las Vegas Raiders @ Denver Broncos
- Miami Dolphins @ Buffalo Bills
- Minnesota Vikings @ San Francisco 49ers
- New Orleans Saints @ Chicago Bears
- New York Jets @ Los Angeles Chargers
- Pittsburgh Steelers @ Philadelphia Eagles
- Tampa Bay Buccaneers @ Detroit Lions
- Tennessee Titans @ Dallas Cowboys

## Selections

Every one of these cleared an approved market, a modelled opinion, its edge threshold, the juice and price bars, the availability gate and the kickoff guard. **A cleared bar is not a prediction.**

**Bet down to** is the worst price at which a pick still clears the card's 6% edge bar, never worse than -160. Below it, the pick is no longer a selection.

| Game | Market | Selection | Line | Price | Book | Edge | Bet down to |
|:-----|:-------|:----------|-----:|------:|:-----|-----:|------------:|
| New York Jets @ Los Angeles Chargers | `alternate_spread` | home | -8 | +230 | betrivers | +14.3% | +159 |
| Tennessee Titans @ Dallas Cowboys | `alternate_team_total` | home_under | 27.5 | +190 | fanduel | +14.3% | +134 |
| Arizona Cardinals @ Kansas City Chiefs | `alternate_spread` | away | 12.5 | +142 | fanduel | +14.0% | +103 |
| Las Vegas Raiders @ Denver Broncos | `alternate_team_total` | away_over | 16.5 | +140 | fanduel | +12.9% | +106 |
| Pittsburgh Steelers @ Philadelphia Eagles | `alternate_total_points` | over | 43.5 | +196 | fanduel | +12.4% | +149 |
| Arizona Cardinals @ Kansas City Chiefs | `total_points` | over | 40 | -107 | lowvig | +12.4% | -138 |
| New York Jets @ Los Angeles Chargers | `alternate_team_total` | away_under | 12.5 | +390 | fanduel | +11.2% | +291 |
| Jacksonville Jaguars @ New York Giants | `alternate_team_total` | away_under | 22.5 | +186 | fanduel | +10.5% | +154 |
| New Orleans Saints @ Chicago Bears | `alternate_team_total` | away_over | 17.5 | -105 | betmgm | +9.7% | -121 |
| Miami Dolphins @ Buffalo Bills | `alternate_total_points` | over | 51.5 | +210 | fanduel | +9.2% | +183 |
| Minnesota Vikings @ San Francisco 49ers | `alternate_spread` | home | -8.5 | +215 | fanduel | +9.1% | +188 |
| Las Vegas Raiders @ Denver Broncos | `alternate_team_total` | home_under | 22.5 | +190 | fanduel | +9.0% | +167 |
| Jacksonville Jaguars @ New York Giants | `moneyline` | home | — | +235 | betus | +8.9% | +206 |
| Pittsburgh Steelers @ Philadelphia Eagles | `alternate_team_total` | away_under | 15.5 | +270 | betmgm | +8.4% | +240 |
| Tampa Bay Buccaneers @ Detroit Lions | `alternate_spread` | home | -8.5 | +196 | fanduel | +7.7% | +182 |
| Miami Dolphins @ Buffalo Bills | `alternate_team_total` | home_under | 25.5 | +235 | fanduel | +6.9% | +226 |
| Minnesota Vikings @ San Francisco 49ers | `alternate_team_total` | away_under | 21.5 | -112 | betmgm | +6.5% | -114 |
| Tampa Bay Buccaneers @ Detroit Lions | `alternate_team_total` | home_over | 33.5 | +330 | draftkings | +6.3% | +325 |
| Jacksonville Jaguars @ New York Giants | `alternate_total_points` | under | 38.5 | +230 | fanduel | +6.1% | +229 |

**Too far from the market.** 369 selection(s) on 7 game(s) (Arizona Cardinals @ Kansas City Chiefs, Baltimore Ravens @ Carolina Panthers, Las Vegas Raiders @ Denver Broncos, Miami Dolphins @ Buffalo Bills, New Orleans Saints @ Chicago Bears, Pittsburgh Steelers @ Philadelphia Eagles, Tennessee Titans @ Dallas Cowboys) were dropped because an answer to the same question carried an edge above 15%. The model sits far from every book there, which usually means news it does not have, so the card takes no side on that question.

**Edge floor.** 165 selection(s) on the kept side cleared their market's threshold but not 6%, and were not selected: the card selects only edges strictly above 6%.

**One pick per question.** 296 selection(s) cleared every bar but were other rungs of a question the card already answers, and were not selected: each game's margin, total and team totals carry only their largest edge.

Player props are priced and tracked and **cannot produce a selection**. Inactives are declared about ninety minutes before kickoff and no available feed publishes them, so no player can be confirmed active. This is a missing source, not a judgement about any market's value.

## Markets, and why each is excluded

An excluded market is never a pass, an avoid, or a no-value call. Those are genuine model judgements about markets that were actually priced and modelled; this is a different thing entirely.

**28 market(s)** — eligible

`alternate_spread`, `alternate_team_total`, `alternate_total_points`, `anytime_td`, `defensive_interceptions`, `field_goals`, `kicking_points`, `moneyline`, `moneyline_h1`, `pass_attempts`, `pass_completions`, `pass_interceptions`, `pass_longest_completion`, `pass_tds`, `pass_yards`, `reception_longest`, `reception_yards`, `receptions`, `rush_attempts`, `rush_longest`, `rush_yards`, `sacks`, `spread`, `spread_h1`, `tackles_assists`, `team_total`, `total_points`, `total_points_h1`


## The accounting identity

`priced 55,834 = no_opinion 5,550 + unparseable 0 + ambiguous 0 + opinions 50,284 — reconciles.`

Where the opinions did not go:

- 1554 x no fitted rate for `reception_yards`
- 871 x no fitted rate for `receptions`
- 561 x no fitted rate for `rush_yards`
- 490 x no fitted rate for `anytime_td`
- 261 x no fitted rate for `pass_yards`
- 257 x player not on a current roster
- 217 x no fitted rate for `rush_attempts`
- 198 x `moneyline_h1` needs the first-half model, which is not in force — see the recorded verdict
- 198 x `spread_h1` needs the first-half model, which is not in force — see the recorded verdict
- 198 x `total_points_h1` needs the first-half model, which is not in force — see the recorded verdict

## Forward evidence

50,284 opinion(s) frozen for 2026-11-22; 588,608 row(s) in the settled ledger.

Frozen before kickoff, settled after, never repriced. Historical prices can be bought later; forward evidence cannot be back-dated.

> Calibration fitted on 2023-2025, covering 17 market(s), frozen beside every raw probability.

## TD Due List

Anytime touchdown, over 0.5. Listed: 8+ touchdowns scored last regular season, on a drought of 3+ games (12+), 4+ games (10-11), 5+ games (8-9). Context only: no units, nothing here is a selection or is frozen.

Since 2016, listed players scored in 29.9% of 723 games against 40.5% for the same qualifiers when not due (n = 4,716); betting every listed over at the best price 2023-25 returned -3.6% over 241 bets (-24.2% to +17.0%): no demonstrated edge.

Availability checked against the injury report and weekly roster; Out, Doubtful and reserve-list players are removed, Questionable ones flagged.

| Player | Team | Opp | Kickoff | Last season | Drought (bar) | 1 in N for him | Status | Best price |
|:--|:--|:--|:--|--:|:--|--:|:--|:--|
| Jauan Jennings | MIN | SF | 20:20 ET | 9 TD, 53% of games | 7 (5) | 1 in 207 | — | +475 (draftkings) |
| Dallas Goedert | PHI | PIT | 16:25 ET | 11 TD, 53% of games | 6 (4) | 1 in 97 | — | +425 (draftkings) |
| Travis Etienne | NO | CHI | 13:00 ET | 13 TD, 53% of games | 6 (3) | 1 in 92 | — | +300 (circasports) |
| Trevor Lawrence | JAX | NYG | 13:00 ET | 9 TD, 35% of games | 10 (5) | 1 in 78 | — | +525 (fanatics) |
| Kenny Gainwell | TB | DET | 13:00 ET | 8 TD, 35% of games | 5 (5) | 1 in 9 | — | +390 (draftkings) |

Removed, not playing this week (injury report and weekly roster):

- De'Von Achane (MIA): on a reserve list (injured reserve or similar)
