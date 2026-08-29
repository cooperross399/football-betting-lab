# Allowlist evidence — NFL

**This allowlists nothing.** It is step four of the six in `docs/provider_allowlist_approval.md`. Claude prepares it and stops; step six is Cooper reading it and signing a receipt, or not.

The default verdict is **not supported**. A market earns anything else only by clearing every bar, and each bar exists because something failed it.

## What this rests on

| Input | State |
|:------|:------|
| Bought population | 816 games across 2023-2025 — **every NFL game for which historical props exist.** The provider serves them only after 2023-05-03, so there is no more to buy. |
| Snapshots per game | two priced (card time and the close), three bought |
| Null baseline | -9.3% betting everything — harness sound |
| Family correction | Bonferroni across 20 markets (x1.54) |
| Settlement screen | 1 suspect(s): tackles_assists |
| Selection gate | no player prop can produce a selection until the verdict `props_selectable_when_undesignated` is in force, which waits on one line in a book's did-not-play rules |

## Market by market

| Market | Bets | Verdict | Detail |
|:-------|-----:|:--------|:-------|
| `rush_yards` | 16,829 | **supported for review** | clears every bar — **this is a recommendation to review, not an approval** |
| `receptions` | 12,918 | **supported for review** | clears every bar — **this is a recommendation to review, not an approval** |
| `reception_longest` | 8,917 | **supported for review** | clears every bar — **this is a recommendation to review, not an approval** |
| `reception_yards` | 39,109 | **not supported** | fails: replication |
| `pass_yards` | 10,638 | **not supported** | fails: books; replication |
| `sacks` | 8,795 | **not supported** | fails: consensus; books; replication |
| `tackles_assists` | 6,267 | **not supported** | fails: settlement |
| `rush_attempts` | 5,153 | **not supported** | fails: consensus; replication |
| `rush_longest` | 3,050 | **not supported** | fails: consensus; replication |
| `pass_attempts` | 2,762 | **not supported** | fails: replication |
| `pass_interceptions` | 2,750 | **not supported** | fails: consensus; books; replication |
| `pass_completions` | 2,663 | **not supported** | fails: consensus; books; replication |
| `anytime_td` | 2,632 | **not supported** | fails: books; replication |
| `pass_tds` | 2,354 | **not supported** | fails: books; replication |
| `field_goals` | 1,436 | **not supported** | fails: consensus; books; replication |
| `kicking_points` | 1,212 | **not supported** | fails: consensus; books; replication |
| `defensive_interceptions` | 1,193 | **not supported** | fails: consensus; books; replication |
| `pass_longest_completion` | 953 | **not supported** | fails: consensus; books; replication |
| `rush_tds` | 150 | **not supported** | fails: consensus; books; replication; sample |
| `reception_tds` | 61 | **not supported** | fails: books; replication; sample |

### `anytime_td`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.3% |
| settlement | pass — agrees with the devigged price |
| consensus | pass — +0.2% at the median quote |
| books | **FAIL** — positive at 2 of 10 |
| replication | **FAIL** — 2023 -2.3% (878), 2024 +11.8% (847), 2025 +12.9% (907) |
| sample | pass — 2,632 bets against a declared minimum of 200 |

### `defensive_interceptions`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.3% |
| settlement | pass — agrees with the devigged price |
| consensus | **FAIL** — -11.0% at the median quote |
| books | **FAIL** — positive at 0 of 2 |
| replication | **FAIL** — 2023 -18.5% (145), 2024 -40.1% (468), 2025 -22.2% (580) |
| sample | pass — 1,193 bets against a declared minimum of 200 |

### `field_goals`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.3% |
| settlement | pass — agrees with the devigged price |
| consensus | **FAIL** — -5.4% at the median quote |
| books | **FAIL** — positive at 1 of 3 |
| replication | **FAIL** — 2023 +0.9% (455), 2024 -12.2% (559), 2025 +4.2% (422) |
| sample | pass — 1,436 bets against a declared minimum of 200 |

### `kicking_points`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.3% |
| settlement | pass — agrees with the devigged price |
| consensus | **FAIL** — -4.8% at the median quote |
| books | **FAIL** — positive at 1 of 5 |
| replication | **FAIL** — 2023 +0.6% (447), 2024 -6.7% (402), 2025 +4.4% (363) |
| sample | pass — 1,212 bets against a declared minimum of 200 |

### `pass_attempts`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.3% |
| settlement | pass — agrees with the devigged price |
| consensus | pass — +2.9% at the median quote |
| books | pass — positive at 7 of 8 |
| replication | **FAIL** — 2023 +18.6% (865), 2024 -2.5% (851), 2025 +2.2% (1046) |
| sample | pass — 2,762 bets against a declared minimum of 200 |

### `pass_completions`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.3% |
| settlement | pass — agrees with the devigged price |
| consensus | **FAIL** — -2.0% at the median quote |
| books | **FAIL** — positive at 2 of 8 |
| replication | **FAIL** — 2023 +8.2% (894), 2024 -2.6% (833), 2025 -2.2% (936) |
| sample | pass — 2,663 bets against a declared minimum of 200 |

### `pass_interceptions`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.3% |
| settlement | pass — agrees with the devigged price |
| consensus | **FAIL** — -6.6% at the median quote |
| books | **FAIL** — positive at 0 of 8 |
| replication | **FAIL** — 2023 +1.8% (783), 2024 -14.4% (908), 2025 -15.5% (1059) |
| sample | pass — 2,750 bets against a declared minimum of 200 |

### `pass_longest_completion`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.3% |
| settlement | pass — agrees with the devigged price |
| consensus | **FAIL** — -1.9% at the median quote |
| books | **FAIL** — positive at 0 of 3 |
| replication | **FAIL** — 2023 -2.6% (328), 2024 -1.4% (370), 2025 -4.4% (255) |
| sample | pass — 953 bets against a declared minimum of 200 |

### `pass_tds`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.3% |
| settlement | pass — agrees with the devigged price |
| consensus | pass — +3.1% at the median quote |
| books | **FAIL** — positive at 0 of 9 |
| replication | **FAIL** — 2023 -17.9% (757), 2024 +17.5% (826), 2025 -0.5% (771) |
| sample | pass — 2,354 bets against a declared minimum of 200 |

### `pass_yards`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.3% |
| settlement | pass — agrees with the devigged price |
| consensus | pass — +3.5% at the median quote |
| books | **FAIL** — positive at 4 of 8 |
| replication | **FAIL** — 2023 +11.8% (3287), 2024 +6.2% (4009), 2025 -9.1% (3342) |
| sample | pass — 10,638 bets against a declared minimum of 200 |

### `reception_longest`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.3% |
| settlement | pass — agrees with the devigged price |
| consensus | pass — +0.1% at the median quote |
| books | pass — positive at 7 of 8 |
| replication | pass — 2023 +4.1% (2381), 2024 +2.5% (2858), 2025 +1.4% (3678) |
| sample | pass — 8,917 bets against a declared minimum of 200 |

### `reception_tds`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.3% |
| settlement | pass — agrees with the devigged price |
| consensus | pass — +23.4% at the median quote |
| books | **FAIL** — positive at 0 of 0 |
| replication | **FAIL** — 2023 -100.0% (14), 2024 +44.7% (29), 2025 -100.0% (18) |
| sample | **FAIL** — 61 bets against a declared minimum of 200 |

### `reception_yards`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.3% |
| settlement | pass — agrees with the devigged price |
| consensus | pass — +1.6% at the median quote |
| books | pass — positive at 9 of 11 |
| replication | **FAIL** — 2023 +11.0% (10599), 2024 +4.6% (14444), 2025 -0.5% (14066) |
| sample | pass — 39,109 bets against a declared minimum of 200 |

### `receptions`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.3% |
| settlement | pass — agrees with the devigged price |
| consensus | pass — +1.5% at the median quote |
| books | pass — positive at 7 of 10 |
| replication | pass — 2023 +11.8% (3629), 2024 +5.9% (4659), 2025 +3.7% (4630) |
| sample | pass — 12,918 bets against a declared minimum of 200 |

### `rush_attempts`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.3% |
| settlement | pass — agrees with the devigged price |
| consensus | **FAIL** — -0.5% at the median quote |
| books | pass — positive at 8 of 9 |
| replication | **FAIL** — 2023 +20.7% (1346), 2024 +7.0% (1776), 2025 -3.2% (2031) |
| sample | pass — 5,153 bets against a declared minimum of 200 |

### `rush_longest`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.3% |
| settlement | pass — agrees with the devigged price |
| consensus | **FAIL** — -0.6% at the median quote |
| books | pass — positive at 6 of 6 |
| replication | **FAIL** — 2023 +7.1% (902), 2024 -0.2% (1048), 2025 +4.9% (1100) |
| sample | pass — 3,050 bets against a declared minimum of 200 |

### `rush_tds`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.3% |
| settlement | pass — agrees with the devigged price |
| consensus | **FAIL** — -13.5% at the median quote |
| books | **FAIL** — positive at 0 of 0 |
| replication | **FAIL** — 2023 -77.7% (22), 2024 -17.7% (97), 2025 -65.2% (31) |
| sample | **FAIL** — 150 bets against a declared minimum of 200 |

### `rush_yards`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.3% |
| settlement | pass — agrees with the devigged price |
| consensus | pass — +8.3% at the median quote |
| books | pass — positive at 10 of 11 |
| replication | pass — 2023 +19.1% (4869), 2024 +10.1% (6400), 2025 +10.9% (5560) |
| sample | pass — 16,829 bets against a declared minimum of 200 |

### `sacks`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.3% |
| settlement | pass — agrees with the devigged price |
| consensus | **FAIL** — -5.8% at the median quote |
| books | **FAIL** — positive at 0 of 5 |
| replication | **FAIL** — 2023 +0.2% (1309), 2024 -10.9% (3671), 2025 -16.8% (3815) |
| sample | pass — 8,795 bets against a declared minimum of 200 |

### `tackles_assists`

| Bar | Result |
|:----|:-------|
| harness | pass — betting everything returns -9.3% |
| settlement | **FAIL** — realised rate sits more than 4% from it |
| consensus | pass — +9.0% at the median quote |
| books | pass — positive at 8 of 8 |
| replication | pass — 2023 +13.1% (2180), 2024 +14.2% (2261), 2025 +18.4% (1826) |
| sample | pass — 6,267 bets against a declared minimum of 200 |

## What a signature would and would not buy

**3 of 20 markets clear every bar.** Clearing them means the measurements do not rule the market out; it does not mean an edge is established. Nothing here predicts a return.

An allowlisted market still passes every gate on every run: staging validation, completeness, freshness, the kickoff guard, the quarterback-change quarantine and the availability gate. Approval says *these prices may be used*. It does not say *skip the checks*.

## What would change these numbers

- **The did-not-play rule.** Every return here assumes a book voids a prop for a player who takes no snap. If it grades them as losses, `rush_yards` is −0.8% rather than +13.0%. One line in a book's rules, and no measurement can settle it.
- **The mechanism is not understood.** The compound-simulation markets pool to +3.5% at the consensus price (interval +1.4% to +5.7% over 100,230 bets) and the count-only markets to −9.8%. That split is the strongest structure in the evidence and nothing here explains it.
- **The population cannot grow.** All 816 available games are bought. The only further evidence is forward, from 2026-09-09, at 272 games a season.
- **The NHL lab went the other way at scale**: +1.4% over 4,830 bets became −1.6% over 73,918 on its full population, and its approval was withdrawn. That is the direction of surprise to expect.
