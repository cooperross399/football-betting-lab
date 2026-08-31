# Allowlist evidence — NFL

**This allowlists nothing.** It is step four of the six in `docs/provider_allowlist_approval.md`. Claude prepares it and stops; step six is Cooper reading it and signing a receipt, or not.

The default verdict is **not supported**. A market earns anything else only by clearing every bar, and each bar exists because something failed it.

## What this rests on

| Input | State |
|:------|:------|
| Bought population | 816 games across 2023-2025 — **every NFL game for which historical props exist.** The provider serves them only after 2023-05-03, so there is no more to buy. |
| Snapshots per game | two priced (card time and the close), three bought |
| Null baseline | -9.3% betting everything — harness sound |
| Family correction | Bonferroni across 18 markets (x1.53) |
| Settlement screen | 0 suspect(s): none |
| Selection gate | no player prop can produce a selection until the verdict `props_selectable_when_undesignated` is in force, which waits on one line in a book's did-not-play rules |

## Market by market

| Market | Bets | Verdict | Detail |
|:-------|-----:|:--------|:-------|
| `reception_yards` | 26,028 | **not supported** | fails: consensus; books; replication |
| `rush_yards` | 11,573 | **not supported** | fails: consensus; books |
| `receptions` | 8,666 | **not supported** | fails: consensus; books; replication |
| `pass_yards` | 6,937 | **not supported** | fails: consensus; books; replication |
| `reception_longest` | 5,800 | **not supported** | fails: consensus; books; replication |
| `tackles_assists` | 3,987 | **not supported** | fails: books; replication |
| `rush_attempts` | 3,527 | **not supported** | fails: consensus; books; replication |
| `rush_longest` | 2,014 | **not supported** | fails: consensus; books; replication |
| `pass_attempts` | 1,850 | **not supported** | fails: consensus; books; replication |
| `pass_completions` | 1,753 | **not supported** | fails: consensus; books; replication |
| `anytime_td` | 1,740 | **not supported** | fails: consensus; books; replication |
| `sacks` | 1,079 | **not supported** | fails: consensus; books |
| `pass_tds` | 861 | **not supported** | fails: consensus; books; replication |
| `kicking_points` | 742 | **not supported** | fails: consensus; books; replication |
| `pass_longest_completion` | 658 | **not supported** | fails: consensus; books; replication |
| `pass_interceptions` | 613 | **not supported** | fails: consensus; books; replication |
| `field_goals` | 385 | **not supported** | fails: consensus; books; replication |
| `defensive_interceptions` | 40 | **not supported** | fails: settlement; consensus; books; replication; sample |

### `anytime_td`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.3% |
| settlement | pass — agrees with the devigged price |
| consensus | **FAIL** — -12.2% at the median quote |
| books | **FAIL** — positive at 0 of 10 |
| replication | **FAIL** — 2023 -11.0% (636), 2024 +8.1% (522), 2025 +3.2% (582) |
| sample | pass — 1,740 bets against a declared minimum of 200 |

### `defensive_interceptions`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.3% |
| settlement | **FAIL** — never screened — the settlement report does not cover this market, so nothing is known about whether it settles on what it was priced on |
| consensus | **FAIL** — -42.7% at the median quote |
| books | **FAIL** — positive at 0 of 0 |
| replication | **FAIL** — 2024 -20.0% (13), 2025 -53.7% (27) |
| sample | **FAIL** — 40 bets against a declared minimum of 200 |

### `field_goals`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.3% |
| settlement | pass — agrees with the devigged price |
| consensus | **FAIL** — -5.3% at the median quote |
| books | **FAIL** — positive at 0 of 0 |
| replication | **FAIL** — 2023 +9.4% (162), 2024 -16.5% (115), 2025 -9.0% (108) |
| sample | pass — 385 bets against a declared minimum of 200 |

### `kicking_points`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.3% |
| settlement | pass — agrees with the devigged price |
| consensus | **FAIL** — -7.8% at the median quote |
| books | **FAIL** — positive at 0 of 3 |
| replication | **FAIL** — 2023 +2.9% (241), 2024 -13.4% (233), 2025 -8.5% (268) |
| sample | pass — 742 bets against a declared minimum of 200 |

### `pass_attempts`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.3% |
| settlement | pass — agrees with the devigged price |
| consensus | **FAIL** — -2.2% at the median quote |
| books | **FAIL** — positive at 2 of 8 |
| replication | **FAIL** — 2023 +7.6% (437), 2024 -4.9% (514), 2025 -0.6% (899) |
| sample | pass — 1,850 bets against a declared minimum of 200 |

### `pass_completions`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.3% |
| settlement | pass — agrees with the devigged price |
| consensus | **FAIL** — -9.7% at the median quote |
| books | **FAIL** — positive at 0 of 7 |
| replication | **FAIL** — 2023 -1.5% (467), 2024 -8.5% (521), 2025 -10.2% (765) |
| sample | pass — 1,753 bets against a declared minimum of 200 |

### `pass_interceptions`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.3% |
| settlement | pass — agrees with the devigged price |
| consensus | **FAIL** — -8.4% at the median quote |
| books | **FAIL** — positive at 0 of 5 |
| replication | **FAIL** — 2023 -11.6% (194), 2024 -4.7% (216), 2025 +0.4% (203) |
| sample | pass — 613 bets against a declared minimum of 200 |

### `pass_longest_completion`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.3% |
| settlement | pass — agrees with the devigged price |
| consensus | **FAIL** — -1.4% at the median quote |
| books | **FAIL** — positive at 0 of 0 |
| replication | **FAIL** — 2023 -6.1% (205), 2024 +3.4% (238), 2025 +0.3% (215) |
| sample | pass — 658 bets against a declared minimum of 200 |

### `pass_tds`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.3% |
| settlement | pass — agrees with the devigged price |
| consensus | **FAIL** — -12.2% at the median quote |
| books | **FAIL** — positive at 0 of 7 |
| replication | **FAIL** — 2023 -14.0% (257), 2024 -3.4% (317), 2025 -8.2% (287) |
| sample | pass — 861 bets against a declared minimum of 200 |

### `pass_yards`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.3% |
| settlement | pass — agrees with the devigged price |
| consensus | **FAIL** — -6.9% at the median quote |
| books | **FAIL** — positive at 0 of 8 |
| replication | **FAIL** — 2023 -9.9% (1524), 2024 +7.4% (2941), 2025 -17.3% (2472) |
| sample | pass — 6,937 bets against a declared minimum of 200 |

### `reception_longest`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.3% |
| settlement | pass — agrees with the devigged price |
| consensus | **FAIL** — -4.3% at the median quote |
| books | **FAIL** — positive at 0 of 7 |
| replication | **FAIL** — 2023 -2.3% (1037), 2024 -5.9% (1752), 2025 -2.6% (3011) |
| sample | pass — 5,800 bets against a declared minimum of 200 |

### `reception_yards`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.3% |
| settlement | pass — agrees with the devigged price |
| consensus | **FAIL** — -7.7% at the median quote |
| books | **FAIL** — positive at 0 of 11 |
| replication | **FAIL** — 2023 -3.2% (5299), 2024 -5.2% (10154), 2025 -7.9% (10575) |
| sample | pass — 26,028 bets against a declared minimum of 200 |

### `receptions`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.3% |
| settlement | pass — agrees with the devigged price |
| consensus | **FAIL** — -8.6% at the median quote |
| books | **FAIL** — positive at 0 of 10 |
| replication | **FAIL** — 2023 -0.5% (2011), 2024 -6.3% (3180), 2025 -5.6% (3475) |
| sample | pass — 8,666 bets against a declared minimum of 200 |

### `rush_attempts`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.3% |
| settlement | pass — agrees with the devigged price |
| consensus | **FAIL** — -10.9% at the median quote |
| books | **FAIL** — positive at 1 of 8 |
| replication | **FAIL** — 2023 -0.7% (701), 2024 -8.0% (1155), 2025 -10.7% (1671) |
| sample | pass — 3,527 bets against a declared minimum of 200 |

### `rush_longest`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.3% |
| settlement | pass — agrees with the devigged price |
| consensus | **FAIL** — -4.5% at the median quote |
| books | **FAIL** — positive at 0 of 5 |
| replication | **FAIL** — 2023 -6.8% (511), 2024 -5.0% (663), 2025 -0.0% (840) |
| sample | pass — 2,014 bets against a declared minimum of 200 |

### `rush_yards`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.3% |
| settlement | pass — agrees with the devigged price |
| consensus | **FAIL** — -0.6% at the median quote |
| books | **FAIL** — positive at 2 of 10 |
| replication | pass — 2023 +0.5% (2874), 2024 +2.6% (4640), 2025 +0.1% (4059) |
| sample | pass — 11,573 bets against a declared minimum of 200 |

### `sacks`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.3% |
| settlement | pass — agrees with the devigged price |
| consensus | **FAIL** — -0.0% at the median quote |
| books | **FAIL** — positive at 1 of 2 |
| replication | pass — 2024 +0.6% (494), 2025 +3.8% (585) |
| sample | pass — 1,079 bets against a declared minimum of 200 |

### `tackles_assists`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.3% |
| settlement | pass — agrees with the devigged price |
| consensus | pass — +0.9% at the median quote |
| books | **FAIL** — positive at 3 of 8 |
| replication | **FAIL** — 2023 -0.4% (1139), 2024 -1.8% (1497), 2025 +8.5% (1351) |
| sample | pass — 3,987 bets against a declared minimum of 200 |

## What a signature would and would not buy

**0 of 18 markets clear every bar.** Clearing them means the measurements do not rule the market out; it does not mean an edge is established. Nothing here predicts a return.

An allowlisted market still passes every gate on every run: staging validation, completeness, freshness, the kickoff guard, the quarterback-change quarantine and the availability gate. Approval says *these prices may be used*. It does not say *skip the checks*.

## What would change these numbers

- **The did-not-play rule.** Every return here assumes a book voids a prop for a player who takes no snap. If it grades them as losses, the whole record is -9.7% rather than -3.7%, across 5,152 voided selections. One line in a book's rules, and no measurement can settle it.
- **There is no compound-versus-count split.** At the consensus price, the compound-simulation markets pool to -6.3% over 66,956 bets and the count-only markets to -4.2% over 11,297 bets. An earlier version of this bundle reported that split as the strongest structure in the evidence. It was an artefact of two defects that touched only the compound markets — a walk-forward leak in the pooled per-play yardage file, and cross-season settlement — and it did not survive either fix.
- **The population cannot grow.** All 816 available games are bought. The only further evidence is forward, from 2026-09-09, at 272 games a season.
- **The NHL lab reached the same answer by a different route**: +1.4% over 4,830 bets became −1.6% over 73,918 once it bought its full population, and its approval was withdrawn. That is the direction of surprise to expect.
