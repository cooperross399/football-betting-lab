# Historical retention probe — NFL

**20 of 20 probed events returned a snapshot**, taken 60 minutes before kickoff, across 46 requested markets.

7,280 credit(s) actually spent over 120 request(s); the pessimistic pre-flight bound was 9,220; 79659 remaining.

Actual spend was **79% of the pessimistic bound**. The gap is not slack — it is the measurement: the endpoint bills per market *returned*, so the shortfall is exactly the markets no book retained.

## What was sampled

Stratified by kickoff window, because book coverage is not uniform across the schedule and a sample drawn from national night games would measure marquee retention and call it retention.

| Kickoff window | Events probed |
|:---------------|--------------:|
| monday night | 2 |
| other | 1 |
| sunday early | 10 |
| sunday late | 5 |
| sunday night | 1 |
| thursday night | 1 |

Seasons: 2024 (10), 2025 (10). Probing never goes earlier than 2023-05-03, before which the provider served featured markets only — absence there would be the data not existing, not the provider not retaining it.

## Retention by market — the unit that actually gets approved

A market and its alternate ladder are one market everywhere else in this repository, so they are one row here. Reading the per-key table below on its own is how the EPL lab wrote off `total_2_5` for a season: the complete line was absent from the featured market and present in the ladder the whole time.

| Market | Provider keys | Verdict | Books | Priced outcomes |
|:-------|:--------------|:--------|------:|----------------:|
| `alternate_spread` | `alternate_spreads` | retained — priced in 20 of 20 events | 7 | 10,641 |
| `alternate_total_points` | `alternate_totals` | retained — priced in 20 of 20 events | 7 | 11,936 |
| `anytime_td` | `player_anytime_td` | retained — priced in 20 of 20 events | 8 | 3,734 |
| `field_goals` | `player_field_goals`, `player_field_goals_alternate` | retained — priced in 20 of 20 events | 4 | 297 |
| `kicking_points` | `player_kicking_points`, `player_kicking_points_alternate` | retained — priced in 20 of 20 events | 6 | 372 |
| `moneyline_h1` | `h2h_h1` | retained — priced in 20 of 20 events | 9 | 296 |
| `pass_attempts` | `player_pass_attempts`, `player_pass_attempts_alternate` | retained — priced in 20 of 20 events | 8 | 804 |
| `pass_completions` | `player_pass_completions`, `player_pass_completions_alternate` | retained — priced in 20 of 20 events | 8 | 844 |
| `pass_interceptions` | `player_pass_interceptions`, `player_pass_interceptions_alternate` | retained — priced in 20 of 20 events | 7 | 535 |
| `pass_longest_completion` | `player_pass_longest_completion`, `player_pass_longest_completion_alternate` | retained — priced in 20 of 20 events | 6 | 348 |
| `pass_tds` | `player_pass_tds`, `player_pass_tds_alternate` | retained — priced in 20 of 20 events | 8 | 1,190 |
| `pass_yards` | `player_pass_yds`, `player_pass_yds_alternate` | retained — priced in 20 of 20 events | 8 | 2,973 |
| `reception_longest` | `player_reception_longest`, `player_reception_longest_alternate` | retained — priced in 20 of 20 events | 6 | 2,095 |
| `reception_yards` | `player_reception_yds`, `player_reception_yds_alternate` | retained — priced in 20 of 20 events | 8 | 10,832 |
| `receptions` | `player_receptions`, `player_receptions_alternate` | retained — priced in 20 of 20 events | 8 | 6,669 |
| `spread_h1` | `spreads_h1` | retained — priced in 20 of 20 events | 8 | 286 |
| `team_total` | `team_totals` | retained — priced in 20 of 20 events | 7 | 830 |
| `total_points_h1` | `totals_h1` | retained — priced in 20 of 20 events | 8 | 286 |
| `rush_attempts` | `player_rush_attempts`, `player_rush_attempts_alternate` | retained — priced in 19 of 20 events | 8 | 1,455 |
| `rush_longest` | `player_rush_longest`, `player_rush_longest_alternate` | retained — priced in 19 of 20 events | 6 | 636 |
| `rush_yards` | `player_rush_yds`, `player_rush_yds_alternate` | retained — priced in 19 of 20 events | 8 | 4,975 |
| `sacks` | `player_sacks`, `player_sacks_alternate` | retained — priced in 19 of 20 events | 5 | 1,040 |
| `tackles_assists` | `player_tackles_assists`, `player_tackles_assists_alternate` | retained — priced in 18 of 20 events | 6 | 1,540 |
| `alternate_team_total` | `alternate_team_totals` | retained — priced in 17 of 20 events | 5 | 4,056 |
| `defensive_interceptions` | `player_defensive_interceptions`, `player_defensive_interceptions_alternate` | retained — priced in 9 of 20 events | 2 | 145 |
| `reception_tds` | `player_reception_tds`, `player_reception_tds_alternate` | retained but thin — priced in only 2 of 20 events across 1 book(s) | 1 | 4 |
| `rush_tds` | `player_rush_tds`, `player_rush_tds_alternate` | retained but thin — priced in only 2 of 20 events across 1 book(s) | 1 | 6 |

**27 of 27 markets have historical prices at all, and 25 have enough to measure against.**

2 are retained but too thin to support a measurement — fewer than a quarter of the probed events, or a single book quoting them: `reception_tds` (2/20 events, 1 book(s), 4 outcomes), `rush_tds` (2/20 events, 1 book(s), 6 outcomes). A measurement against one book measures that book's pricing, not the market's. These are bought only if a purchase is buying their neighbours anyway, and their evidence accumulates forward.

## Retention, provider key by provider key

The same data before the rollup. Useful for deciding what to *ask* for — an unretained key is a key not worth buying — and misleading for deciding what can be *measured*, which the table above answers.

| Provider market | This lab calls it | Verdict | Books | Priced outcomes |
|:----------------|:------------------|:--------|------:|----------------:|
| `alternate_spreads` | `alternate_spread` | retained — priced in 20 of 20 events | 7 | 10,641 |
| `alternate_totals` | `alternate_total_points` | retained — priced in 20 of 20 events | 7 | 11,936 |
| `team_totals` | `team_total` | retained — priced in 20 of 20 events | 7 | 830 |
| `alternate_team_totals` | `alternate_team_total` | retained — priced in 17 of 20 events | 5 | 4,056 |
| `h2h_h1` | `moneyline_h1` | retained — priced in 20 of 20 events | 9 | 296 |
| `spreads_h1` | `spread_h1` | retained — priced in 20 of 20 events | 8 | 286 |
| `totals_h1` | `total_points_h1` | retained — priced in 20 of 20 events | 8 | 286 |
| `player_pass_yds` | `pass_yards` | retained — priced in 20 of 20 events | 8 | 826 |
| `player_pass_attempts` | `pass_attempts` | retained — priced in 20 of 20 events | 8 | 450 |
| `player_pass_completions` | `pass_completions` | retained — priced in 20 of 20 events | 8 | 430 |
| `player_pass_tds` | `pass_tds` | retained — priced in 20 of 20 events | 8 | 574 |
| `player_pass_interceptions` | `pass_interceptions` | retained — priced in 20 of 20 events | 7 | 438 |
| `player_pass_longest_completion` | `pass_longest_completion` | retained — priced in 20 of 20 events | 6 | 348 |
| `player_rush_yds` | `rush_yards` | retained — priced in 19 of 20 events | 8 | 1,620 |
| `player_rush_attempts` | `rush_attempts` | retained — priced in 19 of 20 events | 8 | 631 |
| `player_rush_tds` | `rush_tds` | not seen in any of 20 events — no historical price to test against | 0 | 0 |
| `player_rush_longest` | `rush_longest` | retained — priced in 19 of 20 events | 5 | 600 |
| `player_receptions` | `receptions` | retained — priced in 20 of 20 events | 8 | 2,884 |
| `player_reception_yds` | `reception_yards` | retained — priced in 20 of 20 events | 8 | 3,732 |
| `player_reception_tds` | `reception_tds` | not seen in any of 20 events — no historical price to test against | 0 | 0 |
| `player_reception_longest` | `reception_longest` | retained — priced in 20 of 20 events | 6 | 1,672 |
| `player_anytime_td` | `anytime_td` | retained — priced in 20 of 20 events | 8 | 3,734 |
| `player_kicking_points` | `kicking_points` | retained — priced in 20 of 20 events | 6 | 267 |
| `player_field_goals` | `field_goals` | retained — priced in 20 of 20 events | 4 | 190 |
| `player_tackles_assists` | `tackles_assists` | retained — priced in 18 of 20 events | 6 | 1,051 |
| `player_sacks` | `sacks` | retained — priced in 19 of 20 events | 4 | 659 |
| `player_defensive_interceptions` | `defensive_interceptions` | not seen in any of 20 events — no historical price to test against | 0 | 0 |
| `player_pass_yds_alternate` | `pass_yards` | retained — priced in 20 of 20 events | 7 | 2,147 |
| `player_pass_attempts_alternate` | `pass_attempts` | retained — priced in 10 of 20 events | 2 | 354 |
| `player_pass_completions_alternate` | `pass_completions` | retained — priced in 14 of 20 events | 3 | 414 |
| `player_pass_tds_alternate` | `pass_tds` | retained — priced in 20 of 20 events | 7 | 616 |
| `player_pass_interceptions_alternate` | `pass_interceptions` | retained — priced in 12 of 20 events | 3 | 97 |
| `player_pass_longest_completion_alternate` | `pass_longest_completion` | not seen in any of 20 events — no historical price to test against | 0 | 0 |
| `player_rush_yds_alternate` | `rush_yards` | retained — priced in 19 of 20 events | 7 | 3,355 |
| `player_rush_attempts_alternate` | `rush_attempts` | retained — priced in 14 of 20 events | 5 | 824 |
| `player_rush_tds_alternate` | `rush_tds` | retained — priced in 2 of 20 events | 1 | 6 |
| `player_rush_longest_alternate` | `rush_longest` | retained — priced in 4 of 20 events | 1 | 36 |
| `player_receptions_alternate` | `receptions` | retained — priced in 19 of 20 events | 7 | 3,785 |
| `player_reception_yds_alternate` | `reception_yards` | retained — priced in 19 of 20 events | 7 | 7,100 |
| `player_reception_tds_alternate` | `reception_tds` | retained — priced in 2 of 20 events | 1 | 4 |
| `player_reception_longest_alternate` | `reception_longest` | retained — priced in 13 of 20 events | 3 | 423 |
| `player_kicking_points_alternate` | `kicking_points` | retained — priced in 11 of 20 events | 2 | 105 |
| `player_field_goals_alternate` | `field_goals` | retained — priced in 14 of 20 events | 2 | 107 |
| `player_tackles_assists_alternate` | `tackles_assists` | retained — priced in 9 of 20 events | 2 | 489 |
| `player_sacks_alternate` | `sacks` | retained — priced in 14 of 20 events | 4 | 381 |
| `player_defensive_interceptions_alternate` | `defensive_interceptions` | retained — priced in 9 of 20 events | 2 | 145 |

## What this supports

**42 of 46 provider keys returned prices**, covering **27 of 27 markets**. The second number is the one that matters: it is markets, not keys, that get modelled, measured and approved.

**4 provider keys were not seen in any of 20 events**: `player_defensive_interceptions`, `player_pass_longest_completion_alternate`, `player_reception_tds`, `player_rush_tds`.

**4 of those are still measurable**, because another key feeds the same market — `player_defensive_interceptions`, `player_pass_longest_completion_alternate`, `player_reception_tds`, `player_rush_tds`. This is the `total_2_5` lesson in a new costume, and it is why the rollup above is the table to read.

None of this is a statement about whether a market is worth betting. It is a statement about whether a priced test of it is possible. See `docs/what_we_can_and_cannot_claim.md`.
