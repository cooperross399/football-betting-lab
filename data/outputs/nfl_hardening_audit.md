# Hardening audit — NFL lab

Seven dimensions were audited adversarially. Every candidate was then handed to a
separate agent whose only job was to **refute** it: re-read the code, re-run the
claim against the live data, and look for the guard upstream that makes the
defect unreachable.

**7 of 14 candidates survived. Seven dissolved.** Half of what the first pass
called a finding was not one — the mechanism was real but nothing wrong followed
from it, the trigger needed a change that has not shipped, or the reproduction
did not reproduce against the artifacts on disk. That ratio is the reason for the
second pass, and it is the number to remember when reading any single-pass audit
of this lab. Nothing below is a style note: every row produces a wrong number or
a wrong decision.

## Confirmed

| # | Finding | Where | What it produces | Fix |
|:--|:--------|:------|:-----------------|:----|
| 1 | Prop settlement joins players by raw provider string while pricing joins by resolved identity | `src/football_betting_lab/reports/props_backtest.py:497` | 3,006 gradeable bets on 99 players graded `void — did not dress`; every one of those 99 strings is 100% void across all its bets, the signature of a join failure rather than genuine inactives. The published record is −3.7% over 78,253 bets; on identity it is −3.64% over 81,259. `nfl_availability_cost.md`'s "**6.2%** of selections voided" is really 2.6%, and the void-rule sensitivity behind `CLAUDE.md:625` ("all markets −9.2% instead of −3.2%") is −6.1%. | Settle on the id the model priced with. `resolution.entry.player_id` is already computed at `props_backtest.py:317`; pass it into `_settle` and replace the `casefold()` mask with a `logs["player_id"]` match. Record `player_id` on the bet row (line 333) so downstream reports stop splitting one man into two. Minimum equivalent fix: map both sides through `rosters.normalise_name`, exactly as `forward_evidence.py:281` already does. Re-run `run_props_replication.py` and `run_availability_cost.py`, then correct the hardcoded 6.2% at `availability_cost.py:18` and the −9.2%/−3.2% at `CLAUDE.md:624-625`. |
| 2 | `best_price_per_selection` collapses on the raw provider string, so one wager survives as two or three | `src/football_betting_lab/reports/props_backtest.py:168` | 517 wagers appear under more than one spelling of one identity, across 1,095 rows of `nfl_props_backtest_bets.csv`, each keeping its own "best" price — one afternoon's opinion staked twice. 625 of those rows currently void under finding 1, so fixing the settlement join **alone** converts 625 silent voids into 625 duplicate stakes, inflating the bet count and narrowing every interval. | Key the collapse on resolved identity, not `player`. Do it in the same change as finding 1 — either both joins move to identity or neither does. |
| 3 | Day-level ledger dedup permanently discards every row that was still inside the patience window | `src/football_betting_lab/forward_evidence.py:415` (with `:293-304` and `scripts/run_gameday_card.py:390`) | A row whose game is not final when the day's other rows settle is dropped by `settle_snapshot`, the day is then stamped into the ledger by `append_ledger`, and the day is never reopened. The row is never settled, never voided, and never counted `unsettleable`. The report prints "0 unsettleable" and computes that day's ROI on the **early-window subset** — the selection bias the day-as-unit rule exists to prevent. It also makes the documented correction rule unreachable: `nflverse.is_provisional` has zero callers, and defensive stats revised Monday–Wednesday can never be re-settled. | Make the pending test a whole-day pre-pass: if any row of the day is unresolved and the day is inside `PATIENCE_DAYS`, settle nothing for that day and leave it out of the ledger; when the window expires the day settles whole, unresolved rows landing as `UNSETTLEABLE` and being counted. If partial settlement is preferred instead, move the dedup key from `snapshot_date` to the full row key and drop the day-level skip at `run_gameday_card.py:390` — the two halves do not work independently. |
| 4 | `settle_snapshot` looks the game up by `snapshot_date` instead of the row's own frozen kickoff | `src/football_betting_lab/forward_evidence.py:288` | `game_index` is keyed on `games.game_date`; `commence_time` is frozen in `SNAPSHOT_COLUMNS` for this purpose and never read. Any game whose played date differs from the card's date misses the lookup, looks "not final", and after the patience window is recorded `UNSETTLEABLE` with its final score sitting in the games table — which is precisely the postponement case `PATIENCE_DAYS` was built for. Load-bearing on a second fail-open: `run_gameday_card.py:209` filters the staged prices to the slate only `if "date" in prices.columns`, so a frame missing that column freezes tomorrow's games into today's snapshot, and every one of them is then unsettleable. | Key the lookup on the date of the row's own `commence_time`, falling back to `snapshot_date` only when it is blank. Make the slate-date filter at `run_gameday_card.py:209` fail closed: a staged frame with no `date` column is a broken stage, not a full slate. |
| 5 | The forward report's pooled verdict skips the family correction every market row above it gets | `src/football_betting_lab/forward_evidence.py:585` | Market rows are judged on `clow/chigh`, widened by `factor`; the pooled line is judged on the raw `pooled_low/pooled_high`. With the live input (`experiment_ledger.json` holds 53 hypotheses) the factor is 1.687, so the single most quotable sentence in the file is held to an interval 1.69x narrower than every row above it — and line 609 then tells the reader the numbers are family-corrected across all 53. A pooled +6.0% on a raw interval of +0.5% to +11.5% prints "interval excludes zero, **positive**"; corrected it is −3.7% to +15.7%, which any single market would report as no demonstrated edge. | Apply `factor` to the pooled half-width before the reading is chosen. `props_backtest.py:643` already does this correctly by rendering the pooled row through the same helper as every market row; make this the same shape rather than a second copy of the rule. |
| 6 | The quarterback-change gate has no caller at either end | `scripts/run_gameday_card.py` / `src/football_betting_lab/reports/gameday_card.py:202` | `gates.check_quarterback`, `gates.current_qb1` and `QB_DEPENDENT_MARKETS` are referenced only by tests; the runner never reads `data/raw/nfl/depth_charts/` and `build_card` takes no depth-chart argument — while `gameday_card.py:26` lists "Quarterback change" as gate 5 of 5. `write_snapshot` freezes **every priced row**, selected or not, so a team whose QB1 has changed since the fit freezes its whole passing and receiving tree priced off the departed quarterback into the one record this lab never revises, and the calibration refit and allowlist evidence later read it back. | Load the depth chart in the runner, pass it to `build_card`, and run `check_quarterback` per team before pricing, quarantining `QB_DEPENDENT_MARKETS` on a changed or unanswerable QB1. Note that `MAX_DEPTH_CHART_AGE_HOURS` is 48 and the cached 2026 chart's newest `dt` is 2026-08-27T18:05:02Z — 122 hours old today — so the gate will refuse to answer until the fetch is fixed. That refusal must block the tree, not wave it through. |
| 7 | `feed_freshness` cannot grade a feed stale unless it happens to carry a `week` column | `scripts/run_feed_freshness.py:45` with `src/football_betting_lab/reports/feed_freshness.py:60-65` | `depth_charts_2026.csv` has no `week` column, so `reaches_week` is None, the week test is skipped, and the only surviving check is "has 32 clubs", which a four-month-old file passes. Verified against the real file: state `current` at `expected_week=12` with the newest row dated 2026-08-27. The same hole covers `injuries`, `snap_counts` and `player_stats`, which pass `needs_clubs=False` and so lose the club check too — an unparseable or zero-byte file returns `(None, 0)` and grades `current` in Week 12 (verified at unit level). The watchdog reports Ready on exactly the feeds whose staleness it exists to catch, and the module's premise, "graded on content, not file age", is unenforced for four of six feeds. | Grade the depth chart on its own `dt` column against the slate date. Treat `reaches_week is None` on a present, due feed as STALE rather than OK. Make an unparseable or empty file MISSING rather than a silent `(None, 0)`, so the `git show > file` zero-byte pattern this repo already documents cannot read as current. |

### Where these land

Findings 1 and 2 change numbers **already published**: `nfl_props_backtest.md`,
`nfl_props_replication.md`, `nfl_availability_cost.md` and the void-rule
sensitivity quoted in `CLAUDE.md`. They must be fixed together and the reports
re-run before any of those numbers is quoted again.

Findings 3, 4 and 5 are in the forward path, whose ledger is empty today. Every
one of them fires on the first real game day, into a record that is never
revised. They are cheaper to fix now than at any later moment in the season.

Findings 6 and 7 both have the same shape: a gate that is documented as in force
and has no caller, or a check that cannot fail. Neither errors. Both answer.

## Checked and found sound

Where not to look again.

- `settle_snapshot`'s log index joins on identity, not spelling
  (`forward_evidence.py:271-283`) — this is the *fixed* copy of finding 1, and
  its comment names the defect. The forward path settles players correctly.
- `props_backtest.render` applies the Bonferroni factor to the pooled row through
  the same `row()` helper as every market row (`props_backtest.py:641-643`) —
  the correct copy of the rule broken at `forward_evidence.py:585`.
- `write_snapshot`'s one-opinion-a-day rule (`forward_evidence.py:164-176`): a
  second run cannot overwrite the day, and an empty snapshot does not lock it.
  Both halves are needed and both are present.
- `_settle_row` returns `UNSETTLEABLE` rather than guessing when the market
  column or the line is missing (`forward_evidence.py:352-358`).
- `gates.report_coverage` fails **closed** when the `team` column is absent
  (`gates.py:147-148`): the empty set means NO_REPORT, the blocking state.
- The degraded-run guard in `scripts/run_gameday_card.py:191-203`: any fetch
  error or early stop publishes no card at all, so a partial slate cannot be
  frozen as a whole one.
- The preseason and kickoff gates are genuinely wired into `select()`
  (`gameday_card.py:165-176`); a started or unconfirmable game is quarantined and
  its stake removed.
- `rosters` and `weekly_rosters` really are graded on content in
  `feed_freshness` — they carry both `week` and `team`, so the week and club
  tests both run. The hole in finding 7 does not extend to them.
- No player prop can reach a selection today: `select()` refuses every
  `PLAYER` market while `props_selectable_when_undesignated` is unshipped, and
  that matches the card's documented gate 4.

## Unresolved — not findings

Real mechanisms that produce no wrong number or wrong decision **today**. Each
one becomes a finding the moment the change it waits on lands, so each belongs in
that change, not in a later audit.

- **Three tier-1 half markets can be priced but not settled.** `moneyline_h1`,
  `spread_h1` and `total_points_h1` are absent from `TEAM_SETTLEMENT`
  (`forward_evidence.py:102`), so `_settle_row` returns `UNSETTLEABLE` for all
  three while `data/processed/half_scores.csv` holds the answer. Not reachable
  today: `price_slate` is called without `half_distributions`
  (`run_gameday_card.py:253-255`), so no h1 row can be frozen. Fix it in the
  change that ships the first-half verdict, not after.
- **One boolean stands in for six availability states.** `select()` gates player
  props on `undesignated_allowed` alone (`gameday_card.py:165`), and
  `gates.assess_availability` / `report_coverage` have no caller in `src/` or
  `scripts/`. Today the blanket refusal matches the card's documented gate 4, so
  no wrong decision follows. The day `props_selectable_when_undesignated` ships,
  a player listed **Out** and every player on a team that filed no report both
  become selectable on that one flag.
- **`assess_availability` fail-opens.** If the injuries frame lacks `gsis_id` the
  rows are emptied and the empty branch returns UNDESIGNATED — the one
  non-confirmed state a verdict can make selectable — with a reason string that
  affirmatively asserts availability (`gates.py:186-192`); an unrecognised
  `report_status` falls the same way. Real fail-opens in a function nothing
  calls. They must be closed in the same change that wires the gate, or that
  change ships a gate that answers "available" for a player listed Out.
- **`feed_freshness` checks `due` before `present`** (`feed_freshness.py:52`), so
  six absent feeds with `due=False` return `is_ready=True` (verified). The
  refutation held: the trigger is a `team_games.csv` with no rows for the season,
  in which case the card prices nothing anyway, and the claim that today's report
  already says all six feeds are current is false — the live
  `nfl_feed_freshness.md` reads "Not ready — 3 of 6". Worth reordering the two
  tests when finding 7 is fixed; not worth a finding on its own.