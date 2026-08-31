# Allowlist evidence — NFL

**This allowlists nothing.** It is step four of the six in `docs/provider_allowlist_approval.md`. Claude prepares it and stops; step six is Cooper reading it and signing a receipt, or not.

The default verdict is **not supported**. A market earns anything else only by clearing every bar, and each bar exists because something failed it.

## What this rests on

| Input | State |
|:------|:------|
| Bought population | 816 games across 2023-2025 — **every NFL game for which historical props exist.** The provider serves them only after 2023-05-03, so there is no more to buy. |
| Snapshots per game | two priced (card time and the close), three bought |
| Null baseline | -9.5% betting everything — harness sound |
| Family correction | Bonferroni across 18 markets (x1.53) |
| Settlement screen | 1 suspect(s): tackles_assists |
| Selection gate | no player prop can produce a selection until the verdict `props_selectable_when_undesignated` is in force, which waits on one line in a book's did-not-play rules |

## Market by market

| Market | Bets | Verdict | Detail |
|:-------|-----:|:--------|:-------|
| `reception_yards` | 26,022 | **not supported** | fails: consensus; books; replication |
| `rush_yards` | 11,565 | **not supported** | fails: consensus; books; replication |
| `receptions` | 8,659 | **not supported** | fails: consensus; books; replication |
| `pass_yards` | 6,987 | **not supported** | fails: consensus; books; replication |
| `reception_longest` | 5,854 | **not supported** | fails: consensus; books; replication |
| `tackles_assists` | 4,428 | **not supported** | fails: settlement |
| `rush_attempts` | 3,532 | **not supported** | fails: consensus; books; replication |
| `rush_longest` | 2,004 | **not supported** | fails: consensus; books; replication |
| `pass_attempts` | 1,863 | **not supported** | fails: consensus; books; replication |
| `anytime_td` | 1,750 | **not supported** | fails: consensus; books; replication |
| `pass_completions` | 1,738 | **not supported** | fails: consensus; books; replication |
| `sacks` | 1,057 | **not supported** | fails: books |
| `pass_tds` | 878 | **not supported** | fails: consensus; books; replication |
| `kicking_points` | 739 | **not supported** | fails: consensus; books; replication |
| `pass_longest_completion` | 644 | **not supported** | fails: consensus; books; replication |
| `pass_interceptions` | 610 | **not supported** | fails: consensus; books; replication |
| `field_goals` | 400 | **not supported** | fails: consensus; books; replication |
| `defensive_interceptions` | 43 | **not supported** | fails: settlement; consensus; books; replication; sample |

### `anytime_td`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.5% |
| settlement | pass — agrees with the devigged price |
| consensus | **FAIL** — -14.1% at the median quote |
| books | **FAIL** — positive at 0 of 10 |
| replication | **FAIL** — 2023 -11.3% (654), 2024 +0.5% (525), 2025 +4.3% (571) |
| sample | pass — 1,750 bets against a declared minimum of 200 |

### `defensive_interceptions`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.5% |
| settlement | **FAIL** — never screened — the settlement report does not cover this market, so nothing is known about whether it settles on what it was priced on |
| consensus | **FAIL** — -34.7% at the median quote |
| books | **FAIL** — positive at 0 of 0 |
| replication | **FAIL** — 2024 -25.7% (14), 2025 -39.0% (29) |
| sample | **FAIL** — 43 bets against a declared minimum of 200 |

### `field_goals`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.5% |
| settlement | pass — agrees with the devigged price |
| consensus | **FAIL** — -6.6% at the median quote |
| books | **FAIL** — positive at 0 of 0 |
| replication | **FAIL** — 2023 +8.8% (168), 2024 -17.6% (121), 2025 -11.4% (111) |
| sample | pass — 400 bets against a declared minimum of 200 |

### `kicking_points`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.5% |
| settlement | pass — agrees with the devigged price |
| consensus | **FAIL** — -8.0% at the median quote |
| books | **FAIL** — positive at 0 of 3 |
| replication | **FAIL** — 2023 +1.2% (240), 2024 -12.6% (232), 2025 -8.2% (267) |
| sample | pass — 739 bets against a declared minimum of 200 |

### `pass_attempts`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.5% |
| settlement | pass — agrees with the devigged price |
| consensus | **FAIL** — -2.6% at the median quote |
| books | **FAIL** — positive at 2 of 8 |
| replication | **FAIL** — 2023 +7.1% (444), 2024 -4.9% (514), 2025 -1.5% (905) |
| sample | pass — 1,863 bets against a declared minimum of 200 |

### `pass_completions`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.5% |
| settlement | pass — agrees with the devigged price |
| consensus | **FAIL** — -9.2% at the median quote |
| books | **FAIL** — positive at 0 of 7 |
| replication | **FAIL** — 2023 -1.1% (466), 2024 -9.3% (514), 2025 -8.6% (758) |
| sample | pass — 1,738 bets against a declared minimum of 200 |

### `pass_interceptions`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.5% |
| settlement | pass — agrees with the devigged price |
| consensus | **FAIL** — -8.3% at the median quote |
| books | **FAIL** — positive at 0 of 5 |
| replication | **FAIL** — 2023 -12.4% (191), 2024 -6.5% (216), 2025 +3.2% (203) |
| sample | pass — 610 bets against a declared minimum of 200 |

### `pass_longest_completion`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.5% |
| settlement | pass — agrees with the devigged price |
| consensus | **FAIL** — -0.5% at the median quote |
| books | **FAIL** — positive at 0 of 0 |
| replication | **FAIL** — 2023 -3.2% (203), 2024 +7.2% (235), 2025 -3.6% (206) |
| sample | pass — 644 bets against a declared minimum of 200 |

### `pass_tds`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.5% |
| settlement | pass — agrees with the devigged price |
| consensus | **FAIL** — -12.1% at the median quote |
| books | **FAIL** — positive at 0 of 7 |
| replication | **FAIL** — 2023 -16.1% (268), 2024 -3.5% (321), 2025 -5.8% (289) |
| sample | pass — 878 bets against a declared minimum of 200 |

### `pass_yards`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.5% |
| settlement | pass — agrees with the devigged price |
| consensus | **FAIL** — -7.1% at the median quote |
| books | **FAIL** — positive at 0 of 8 |
| replication | **FAIL** — 2023 -9.4% (1538), 2024 +6.5% (2964), 2025 -17.5% (2485) |
| sample | pass — 6,987 bets against a declared minimum of 200 |

### `reception_longest`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.5% |
| settlement | pass — agrees with the devigged price |
| consensus | **FAIL** — -4.1% at the median quote |
| books | **FAIL** — positive at 0 of 7 |
| replication | **FAIL** — 2023 -1.1% (1063), 2024 -6.1% (1774), 2025 -2.4% (3017) |
| sample | pass — 5,854 bets against a declared minimum of 200 |

### `reception_yards`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.5% |
| settlement | pass — agrees with the devigged price |
| consensus | **FAIL** — -7.6% at the median quote |
| books | **FAIL** — positive at 1 of 11 |
| replication | **FAIL** — 2023 -2.5% (5302), 2024 -5.5% (10154), 2025 -7.6% (10566) |
| sample | pass — 26,022 bets against a declared minimum of 200 |

### `receptions`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.5% |
| settlement | pass — agrees with the devigged price |
| consensus | **FAIL** — -8.9% at the median quote |
| books | **FAIL** — positive at 0 of 10 |
| replication | **FAIL** — 2023 -1.7% (2010), 2024 -6.7% (3190), 2025 -5.3% (3459) |
| sample | pass — 8,659 bets against a declared minimum of 200 |

### `rush_attempts`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.5% |
| settlement | pass — agrees with the devigged price |
| consensus | **FAIL** — -11.0% at the median quote |
| books | **FAIL** — positive at 1 of 8 |
| replication | **FAIL** — 2023 -0.1% (701), 2024 -8.1% (1163), 2025 -10.9% (1668) |
| sample | pass — 3,532 bets against a declared minimum of 200 |

### `rush_longest`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.5% |
| settlement | pass — agrees with the devigged price |
| consensus | **FAIL** — -4.4% at the median quote |
| books | **FAIL** — positive at 0 of 5 |
| replication | **FAIL** — 2023 -7.4% (498), 2024 -4.3% (667), 2025 +0.0% (839) |
| sample | pass — 2,004 bets against a declared minimum of 200 |

### `rush_yards`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.5% |
| settlement | pass — agrees with the devigged price |
| consensus | **FAIL** — -1.0% at the median quote |
| books | **FAIL** — positive at 2 of 10 |
| replication | **FAIL** — 2023 -0.4% (2869), 2024 +2.8% (4633), 2025 -0.5% (4063) |
| sample | pass — 11,565 bets against a declared minimum of 200 |

### `sacks`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.5% |
| settlement | pass — agrees with the devigged price |
| consensus | pass — +0.7% at the median quote |
| books | **FAIL** — positive at 1 of 2 |
| replication | pass — 2024 +1.3% (495), 2025 +4.3% (562) |
| sample | pass — 1,057 bets against a declared minimum of 200 |

### `tackles_assists`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.5% |
| settlement | **FAIL** — realised rate sits more than 4% from it |
| consensus | pass — +10.6% at the median quote |
| books | pass — positive at 8 of 8 |
| replication | pass — 2023 +12.4% (1447), 2024 +11.2% (1662), 2025 +12.6% (1319) |
| sample | pass — 4,428 bets against a declared minimum of 200 |

## What a signature would and would not buy

**0 of 18 markets clear every bar.** Clearing them means the measurements do not rule the market out; it does not mean an edge is established. Nothing here predicts a return.

An allowlisted market still passes every gate on every run: staging validation, completeness, freshness, the kickoff guard, the quarterback-change quarantine and the availability gate. Approval says *these prices may be used*. It does not say *skip the checks*.

## What would change these numbers

- **The did-not-play rule.** Every return here assumes a book voids a prop for a player who takes no snap. If it grades them as losses, the whole record is -9.2% rather than -3.2%, across 5,174 voided selections. One line in a book's rules, and no measurement can settle it.
- **There is no compound-versus-count split.** At the consensus price, the compound-simulation markets pool to -6.3% over 67,005 bets and the count-only markets to -7.5% over 7,340 bets. An earlier version of this bundle reported that split as the strongest structure in the evidence. It was an artefact of two defects that touched only the compound markets — a walk-forward leak in the pooled per-play yardage file, and cross-season settlement — and it did not survive either fix.
- **The population cannot grow.** All 816 available games are bought. The only further evidence is forward, from 2026-09-09, at 272 games a season.
- **The NHL lab reached the same answer by a different route**: +1.4% over 4,830 bets became −1.6% over 73,918 once it bought its full population, and its approval was withdrawn. That is the direction of surprise to expect.
