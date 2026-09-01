# Bringing the NFL lab to EPL parity — what that buys, and what it does not

**Written 2026-08-31. Week 1 opens Wednesday 2026-09-09 (NE @ SEA, 20:20 ET) — nine days from today.**

Cooper asked for this lab to be "just as detailed as our EPL model and routines."
This document is the plan for that. It leads with the part that is easy to lose in
a long list.

## 1. The honest framing

**None of the items below create an edge, and one of them can only reveal one.**

The NFL lab has no demonstrated edge, measured on the complete available
population and not a sample of it: 816 events, 5.67M bought price rows, 0 of 18
markets clearing the bars declared in advance. The deepest instrument says why.
The model is a **worse forecaster than the price it bets into** — Brier 0.26057
against the market's 0.22703 over **74,345 bets**, and after walk-forward isotonic
calibration it is still 0.23104 against 0.22756 on held-out 2024 (**27,732 bets**)
and 0.22524 against 0.22329 on held-out 2025 (**29,998 bets**). The market's
implied probability carries the vig, so it is being scored with a handicap, and it
wins anyway. Three headline findings from this repository were retracted as
artefacts in the last four days.

That result constrains every item here:

- **Porting measurement machinery onto a model with no skill produces more
  precise descriptions of a loss.** A per-market minimum-edge table, a shrinkage
  layer, a threshold sweep and a demotion feedback loop are all real EPL
  machinery and all of them, applied today, would refine *how much* this model
  loses. None of them can manufacture information the model does not have.
- **Exactly one item on this list can change the answer.** Splitting the pooled
  Brier by market (item 1) is the only proposed work whose output could be
  "no edge here, possibly there" rather than "no edge, restated." It costs hours
  and zero credits, and it will most likely find nothing.
- **The routine items are not about edge. They are about protecting the only
  evidence that can still grow.** The bought population is complete and cannot
  grow — the provider serves props only after 2023-05-03 and every event has been
  bought. The free closing-line series is fixed. The forward ledger is the sole
  remaining source: **272 regular-season games across 57 game days**, 2026-09-09
  to 2027-01-10, and **it cannot be back-dated**. A Sunday that is not frozen is
  permanently missing sample. That is the whole profit argument for a weekly
  routine, and it is a real one, but it is an argument about *option value*,
  not about return.

So the shape of this plan is: **one knowledge item, five items that protect the
2026 ledger, and thirteen items of reliability and tidiness.** Length is not
progress. A reader who takes the ranked table as a work programme and executes it
top to bottom will end the season with a lab that is materially better operated
and exactly as profitable as it is today.

**Scope note.** Eight dimensions were mapped; this pass received two of them in
full — the weekly operating routine, and strategies-as-first-class-modules —
plus the acceptance-receipt observation. The remaining six should be ranked into
the same table when they arrive rather than appended to the end of it, because
the ranking criterion below is what makes the table useful.

**The ranking criterion, stated once.** Items are ranked by expected contribution
to profit and ROI, which for this lab means: (a) does it change what we know about
whether an edge exists; (b) does it protect the 2026 forward ledger, which is the
only asset with future option value; (c) does it prevent a wrong opinion being
frozen into a ledger that is never revised. Everything else ranks below all three,
however well-built the EPL original is.

---

## 2. Ranked table

`Week 1?` = must be working before 2026-09-09 (or the stated date).

| # | Item | Category | Effort | Week 1? | What it changes |
|:--|:-----|:---------|:-------|:--------|:----------------|
| 1 | Per-market forecast skill, not one pooled Brier | profit | small | no | The only item that could turn "no edge anywhere" into "no edge here" |
| 2 | Slate-coverage watchdog: was every game date of the finished week frozen and settled? | profit | medium | **yes** | Stops a lost Sunday going unnoticed; lost sample cannot be recovered |
| 3 | An NFL week window derived from the schedule, not a calendar rule | reliability | small | **yes** | Precondition for 2, 5, 7, 8, 11, 15 — nothing in the repo knows what a week is |
| 4 | Feed-freshness DAG over the nflverse cache, graded on content | profit | medium | **yes** | A stale roster or 60-hour depth chart writes a wrong opinion into an unrevisable ledger |
| 5 | Freeze a calibrated probability column beside the raw one on every forward row | profit | small | **yes** | Cannot be back-dated. Not frozen in Week 1 means never scorable for 2026 |
| 6 | Re-settle pass for rows settled from provisional nflverse copies | profit | medium | **by 2026-09-14** | Defensive counting stats are revised Mon–Wed; Sunday rows are settled against numbers the league later changed |
| 7 | A second, independent weekly cron that watches the gameday workflow | reliability | small | **yes** | The current guard is inside the workflow it guards |
| 8 | `nfl_week_readiness` — the report the routine produces | reliability | medium | **yes (minimal)** | One card, one sentence, one named command; the container for 2/4/6 |
| 9 | Degraded-reasons file, and a posting rule that makes silence mean something | reliability | small | **yes** | ~300 comments a season trains the reader to stop opening the one that matters |
| 10 | Selection accounting identity + price-refusal summary | reliability | small | no | Six bare `continue`s become a reconciling identity; matters the day a market is allowlisted |
| 11 | Pre-week slate confirmation check (`nfl_slate_check.md`) | reliability | medium | no | Bye arithmetic, duplicate clubs, flexed kickoffs; partly covered by 4 for Week 1 |
| 12 | Grade the card on the calibrated probability, not the raw one | profit (nominal) | medium | no | Shrinks apparent edges. Correct, and changes nothing while nothing is selectable |
| 13 | Per-market and per-selection minimum-edge table | profit (nominal) | medium | no | Two constants become a table. No evidence yet exists to set the entries from |
| 14 | Per-strategy edge-threshold sweep, with the anti-fitting guard | profit (nominal) | small | no | Turns 3.5% from inherited to measured — and burns a degree of freedom doing it |
| 15 | Week-over-week snapshot drift comparison | reliability | medium | no | Distinguishes "the football moved" from "a feed moved underneath us" |
| 16 | GitHub-attested approval, replacing the typed `reviewer_name` | reliability | medium | no | Nothing is allowlisted, so nothing needs signing — but this is the right mechanism when something does |
| 17 | Blocker-to-remedy table | tidy | small | no | A terse status names its own fix. Cheapest item here; moves no money |
| 18 | Measured per-market ROI feeding back into live treatment — demotion only | profit (nominal) | medium | no | A gate that only tightens. Premature while nothing can be selected |
| 19 | A `strategies/` package: one module per family | reliability | large | no | The right architecture. Do it after item 1 says which families are worth keeping |

**Nine items are Week 1 work: 2, 3, 4, 5, 6, 7, 8, 9 — eight, plus the minimal
half of 8.** Their combined effort is one small package: two small modules
(3, 5), one small workflow (7), one small report change (9), and three medium
reports (2, 4, 8) that share the week-window primitive from item 3. That is the
nine days. Everything below the line waits.

---

## 3. The top five, in detail

### 1. Per-market forecast skill, not one pooled Brier

**EPL source.** `/Users/cooperross/Projects/epl-betting-lab/src/epl_betting_lab/reports/backtest_bias.py`
(`summarize_by(bets, ["market", "status"]) -> backtest_market_breakdown.csv`), and
`/Users/cooperross/Projects/epl-betting-lab/src/epl_betting_lab/reports/count_model_calibration.py`,
which scores the corners model on walk-forward calibration buckets because no
corner prices exist to backtest it against. The EPL lab never reports one number
for "the model"; every claim about model quality is attached to a market family.

**What to build.** `src/football_betting_lab/reports/forecast_skill.py::measure()`
currently reduces the whole `nfl_props_backtest_bets.csv` frame to one model
Brier and one market Brier, split only by season. Add a `by_market` list to
`SkillResult`, mirroring the shape of `props_backtest.MarketResult`, reporting
model / walk-forward-calibrated / market Brier per market key with the bet count
beside each. Apply the same family-wise Bonferroni correction that
`props_backtest.py` already applies across markets, and apply the same minimum:
the props backtest declares **200 bets** in advance and returns *not enough
evidence* below it, which already disqualifies `pass_interceptions` (199 bets),
`field_goals` (105) and `defensive_interceptions` (31). Run it with
`PYTHONPATH=src .venv/bin/python scripts/run_forecast_skill.py`; the data is on
disk and this spends nothing.

**Why it is ranked first.** `markets.py` itself distinguishes three distributional
shapes in prose — `receptions` is called out as the one family where a count
distribution is the right shape, pass/rush/reception yards are compound, and the
three `longest` markets are extreme-value — and the pooled Brier averages across
all of them. The retraction of three headline findings currently rests on that
pooled number. A single badly-shaped family with many bets (`reception_yards` has
10,511 of them) can bury a family that genuinely forecasts.

**What would prove it worked.** A per-market table where every market with ≥200
bets carries model, calibrated and market Brier and a family-corrected verdict.
Success is not "a market beats the price." Success is that the question is
answered per family instead of once. Concretely:

- If **no family's calibrated Brier is below the market's** after correction, the
  no-edge conclusion is strengthened, and items 12–14 and 18 should be dropped
  from this plan rather than deferred, because there is nothing for them to act on.
- If **one or more families do beat the price**, that is a **candidate, never a
  finding** — the same standard `tackles_assists` was held to. It must be recorded
  in `verdicts.py` with `variants_tested` incremented, and it needs replication on
  a season it was not selected on. Note the prior: `tackles_assists` is the one
  market that replicates (+12.4% / +11.2% / +12.6% across 2023/2024/2025, +11.7%
  over 3,109 held-out bets) and it is a settlement artefact — nflverse records
  about half a tackle per player-game fewer than the books settle on, and at a
  +0.5 offset the entire edge vanishes. Expect any survivor to be that shape until
  proved otherwise.

---

### 2. Slate-coverage watchdog: was every game date of the finished week frozen and settled?

**EPL source.** `/Users/cooperross/Projects/epl-betting-lab/src/epl_betting_lab/reports/schedule_health.py`
and `/Users/cooperross/Projects/epl-betting-lab/scripts/check_schedule_health.py`,
called from the "Watch that the matchday schedule is still running" step in
`/Users/cooperross/Projects/epl-betting-lab/.github/workflows/weekly-lab-check.yml`.
`gap_report(previous_run)` measures the gap behind the newest successful run
against `MAX_EXPECTED_GAP = 4 days` plus `LATENESS_ALLOWANCE = 6 hours`, returns
`(is_stale, sentence)`, and can exit non-zero — from a different cron than the one
it watches, on the stated reasoning that nothing detects its own total absence.

**What to build.** Go further than the EPL version, because *a run that happened*
is not *a slate that was frozen*. For each REG game date in the finished week —
read from `season.known_regular_season_games(league, raw_dir, season=2026)` against
the cache at `data/raw/nfl/schedule/nflverse_games.csv` — assert:

1. `data/archive/priced_snapshots/{date}.csv` exists on the `card-feed` branch and
   is non-empty;
2. every row in it appears in `data/processed/forward_evidence.csv` as settled or
   explicitly `unsettleable`.

Emit a per-date table and a single overall status from a closed vocabulary. Run it
from the weekly cron (item 7), never from `football-gameday-refresh.yml`.

**Why it is ranked second.** Today a dropped Sunday cron, a card that failed after
the restore step, and a bye-heavy week are indistinguishable. The gameday
workflow's only self-check is the `already-published?` guard, which is inside the
workflow it guards. The workflow already survived one class of this: the rehearsal
found a crash on exactly the branch state 2026-09-09 would have had — a card feed
with a card and no ledger — and the fix (restore to a temp, move only on success)
is the kind of failure this watchdog is meant to notice the *next* time.

**What would prove it worked.** Delete a snapshot from a scratch copy of the
`card-feed` branch and confirm the check names that exact date and exits non-zero;
restore it and confirm the check passes. Then, over the season: **57 game days,
and at the end of the year the watchdog's own record should account for all 57** —
each either covered, or covered by a named remediation, or recorded as
permanently lost with the date. A season that ends with "we think we got most of
them" is the failure this prevents.

---

### 3. An NFL week window derived from the schedule, not a calendar rule

**EPL source.** `/Users/cooperross/Projects/epl-betting-lab/src/epl_betting_lab/selected_slate.py`.
`selected_window()` finds the next round still to be played by clustering the
actual fixture dates — earliest date on or after today, extended through every
following date within `MAX_ROUND_GAP = 3 days` — and falls back to the last round
present when nothing is upcoming. Its docstring records the reason: the window used
to be two hardcoded dates, and once the season passed them every provider price
fell outside the window, every market reported `unavailable`, and every card came
back **Blocked** with nothing broken and nothing saying so.

**What to build.** A small module giving `current_week(league, raw_dir, today)` and
`previous_week(...)`, each returning `(week_number, [game_dates])`. Port the
*mechanism* — derive the window from the schedule that is on disk — but **take the
boundary from the `week` column in `nflverse_games.csv`, not from a gap
constant.** A three-day gap threshold would split a normal Thu/Sun/Mon week in
two. The schedule file carries the real `gameday` and `week`; use them.

**Why it is ranked third despite being small.** Nothing in this repository knows
what an NFL week is. The card prices "today plus `--horizon-days`" and the workflow
stamps `TZ=America/New_York date +%F`. Items 2, 6, 8, 11 and 15 all need the phrase
"last week" to mean something. And the calendar rule is a trap this lab has already
documented: **Week 1 2026 opens on a Wednesday** because Thursday's game
(SF @ LA, 2026-09-10) is at the Melbourne Cricket Ground. A Tue-to-Mon rule gets
that wrong silently, and `CLAUDE.md` already carries the warning that a future
session must not "correct" the Wednesday back.

**What would prove it worked.** A test that asserts `current_week` on
`2026-09-08` returns week 1 with `2026-09-09` as its first date, and that
`previous_week` on `2026-09-15` returns week 1 with all of its game dates — Wednesday
included. Plus a sweep over all **18 weeks and 57 game days** of the 2026 schedule
asserting every REG game date lands in exactly one week and every week is
contiguous in the `week` column. If the sweep leaves a date unassigned, the module
is wrong and the watchdog built on it would have under-reported.

---

### 4. A feed-freshness DAG over the nflverse cache, graded on content and not only on mtime

**EPL source.** `/Users/cooperross/Projects/epl-betting-lab/src/epl_betting_lab/workflow_status.py`
— `build_data_freshness_checks()`, `build_data_freshness_status()`,
`recommend_data_freshness_action()`, `inspect_fixture_date_freshness()`,
`inspect_current_odds_date_freshness()`. Twelve declared checks, each with
`sources`, `dependencies`, `minimum_sources`, `stale_status` and a `priority`; each
grading Fresh / Missing / Needs refresh / Stale / Not checked; each carrying the
exact command that clears it; dependency failures propagating downstream. The part
worth copying hardest is that it reads *inside* the file — a fixtures CSV whose
dates are all in the past is `Needs refresh` even though it was written a minute
ago.

**What to build.** A declared check list over the nflverse cache, in priority
order:

| Check | Passes when | Cleared by |
|:--|:--|:--|
| `schedules` | `nflverse_games.csv` contains a REG game inside the next 7 days **and** `season.schedule_cache_is_complete()` reports 32 clubs | `scripts/fetch_football_data.py` |
| `injuries_2026.csv` | carries rows for the current week | `scripts/fetch_football_data.py` |
| `depth_charts_2026.csv` | newest timestamp inside `gates.MAX_DEPTH_CHART_AGE_HOURS = 48.0` | `scripts/fetch_football_data.py` |
| `roster_2026.csv` / `roster_weekly_2026.csv` | present, and newer than the last completed week | `scripts/fetch_football_data.py` |
| `stats_player_week_2026.csv` | carries rows for the last completed week | `scripts/fetch_football_data.py` |
| derived `team_games` / `player_logs` | newer than every source above | `scripts/build_datasets.py` |

Wire `nflverse.staleness_hours(league, raw_dir, now=...)` as the mtime half.
It exists, its docstring explains that a cache with no manifest cannot answer "how
old is this?", and **it currently has zero callers anywhere in `src`, `scripts` or
`tests`.**

**Why it is a profit item and not hygiene.** Each of these failures writes a wrong
opinion into a ledger that is never revised:

- A stale roster mis-attributes players. Measured, not argued: the first live
  shadow run priced **61 players across the two Week 1 openers, and 6 (9.8%) were
  on a different club than their last logged game** (A.J. Brown PHI→NE, Romeo
  Doubs GB→NE, Mike Evans TB→SF, Christian Kirk HOU→SF, Emanuel Wilson GB→SEA,
  Reggie Gilliam BUF→NE); 10 more were unknown to the 2026 roster entirely.
- A depth chart older than 48 hours makes the quarterback question unanswerable,
  and an unanswerable question quarantines — the whole passing and receiving tree
  for that club, on Sunday morning, with no warning on Tuesday.
- A missing injury file is the state that makes **every player look healthy**.
  `gates.assess_availability` correctly distinguishes `NO_REPORT` from
  `UNDESIGNATED` at card time, but nothing warns in advance that the whole file is
  absent — and there is no 2026 injury file at all until Week 1's practice week,
  so the first real test of this is nine days away.

**What would prove it worked.** Point the checker at a fixture directory where the
depth chart is stamped 60 hours old and confirm it grades `Needs refresh` and names
`scripts/fetch_football_data.py`; touch the file without changing its contents and
confirm it *still* grades stale on content where content is the criterion (schedule
dates, injury week). Then the operational proof: across the season, **every
quarantine that appears on a Sunday card should have been preceded by a
`Needs refresh` line on the Tuesday before it.** A quarantine with no prior warning
is a check that is missing.

---

### 5. Freeze a calibrated probability column beside the raw one on every forward row

**EPL source.** `/Users/cooperross/Projects/epl-betting-lab/src/epl_betting_lab/models/calibration.py`
(`calibrate_probability`, `shrinkage_weight`, `ShrinkageConfig`), applied inside
every strategy — e.g. `strategies/ml_value.py`. No EPL strategy ever grades a raw
model probability. Each keeps **both** `raw_prob`/`raw_edge`/`raw_status` and
`calibrated_prob`/`calibrated_edge`/`calibrated_status` on the row, so the
shrinkage is visible rather than silent.

**What to build — and what deliberately not to, yet.** This item is the *freeze*
half only. Add a walk-forward-calibrated probability column to the frozen
forward-evidence row, alongside the raw model probability that is written today.
Nothing else changes: the card still grades the raw probability, `select()` is
untouched, and no selection behaviour moves. Grading on the calibrated number is
item 12 and it can wait, because with no market allowlisted there are zero
selections to change.

**Why this small piece is Week 1 work when the rest of the calibration item is
not.** Forward evidence cannot be back-dated. A calibrated probability that is not
written into the snapshot on 2026-09-09 cannot be recovered for 2026 — the
calibration map fitted later is a different map, and applying it retrospectively
to a frozen row produces a description, not a forecast. This is the one part of the
strategies dimension with a hard nine-day deadline, and it is small. The payoff is
that at the end of the season the two columns can be scored against each other on
real forward rows, which is exactly the comparison
`data/outputs/nfl_forecast_skill.md` makes on bought history and cannot yet make
forward.

**What would prove it worked.** The frozen snapshot for **2026-09-09** carries both
columns on every row, and a test asserts that a row with a raw probability and no
calibrated probability is refused rather than written. Then, at season end, a
forward version of the existing Brier table: raw vs calibrated vs market over the
2026 rows, with the row count stated. The prior from bought history is unambiguous
and should be stated in the report from day one — calibration cut 2025 from
−5.97% to −3.69% and 2024 from −2.90% to −1.05%, and **a smaller loss is not a
profit**.

---

## 4. What not to port, and why

**`thursday_decision_queue.py` and the `ACTION_PRIORITY` vocabulary.** Its labels —
"Review price", "Likely remove from card", "Candidate upgrade" — presuppose
selections sitting on a card. This lab produces none, correctly, because no market
is allowlisted. Porting it builds a queue that is empty by construction and reads
as though the lab is idle rather than as though it is disciplined. Port the run
verdict vocabulary from `epl_weekly_pipeline_history.py` (`Stable ready state`,
`Improved`, `New blockers`, `More review needed`, `Missing prior run`, `Failed`)
into the readiness report instead; "Stable" versus "New blockers" is the
week-to-week sentence the routine actually owes its reader.

**The positive half of `_market_reliability_from_backtest()`.** The EPL card reads
measured per-market ROI back and converts it into a ranking adjustment clipped to
±12 points. Port the demotion half only, if and when anything is selectable at
all — a bonus computed off a lab with no demonstrated edge is a fitting machine,
while a penalty is a gate that only tightens, which is consistent with the standing
rule that a gate is never weakened. And note the deeper reason to defer even the
penalty: the per-market numbers it would read are all "no demonstrated edge" —
`rush_yards` +1.6% over 7,502 held-out bets, `pass_yards` +1.1% over 4,502, both
with intervals spanning zero several times over. A demotion table built from
intervals that all include zero encodes noise as policy.

**Choosing a threshold from the sweep (item 14's tempting half).** Port
`build_threshold_breakdown` and port
`/Users/cooperross/Projects/epl-betting-lab/tests/test_longshot_cap.py::TestTheThresholdIsNotFittedToTheSample`
**together or not at all.** The EPL guard asserts `MAX_DEFAULT_PRICE > 300`
*because* +300 scored better in-sample and was deliberately not chosen. Without
that discipline a sweep across six candidate edges on the same complete bought
population is six free chances on a model already measured as uninformed, and every
variant must increment `variants_tested` in `verdicts.py`. The sweep's honest
output on this lab is "the least-bad losing threshold", which is not a reason to
move `MIN_EDGE`.

**The eleven-cron matchday cadence, `status.html`, the dashboard portal, and the
`current_odds_*` import/validation family.** These are shaped around a workflow
this lab does not have: manual odds entry against a 10:00 America/New_York provider
cutoff. The NFL lab fetches from an API on fixed game days. Copying the cadence
copies the constraint that produced it.

**`promoted_fades.py` and any review-spot strategy.** It emits spots and states it
does not auto-bet. In a lab with zero allowlisted markets that is a second empty
surface, and empty surfaces are how "nothing to report" starts looking like
coverage.

**Per-selection minimum edges (the `SELECTION_MIN_EDGES` half of item 13).** The
EPL entries — totals-under at 0.08 against totals at 0.065 — were set from measured
per-selection results. This lab has no per-selection measurement that survives, so
every entry would be taste dressed as a table. Ship the *mechanism*
(`minimum_edge_for(market, selection)` with `MIN_EDGE`/`MIN_PROP_EDGE` as an
unlowerable floor) with an **empty** override table if it ships at all, and fill it
only from item 1's output.

**A human acceptance receipt written by Claude, in any form.** `CLAUDE.md` forbids
it and `docs/provider_allowlist_approval.md` puts step 6 with Cooper. The EPL lab
solved the same problem correctly:
`/Users/cooperross/Projects/epl-betting-lab/src/epl_betting_lab/reports/github_approval.py`
takes the attestation from GitHub's API — a PR review or comment authored by the
approving account, containing an explicit approval block — and the automation only
*verifies and transcribes* it, failing closed on a missing phrase, an unexpected
author, the wrong PR, the wrong provider, an unapproved market, evidence that
changed after the approval, or an approval older than the freshness window. That is
the shape to port when something is ever ready to be signed, and it is strictly
better than this lab's current `reviewer_name` string in
`data/manual/staging_provider_policy.json`, which is a name whoever runs the
command types. It ranks 16th only because **nothing is allowlisted and nothing is
close to being allowlisted**, so there is currently no receipt to attest.

**The whole `strategies/` package split, for now.** It is the right architecture
and it is item 19 rather than item 5 for one reason: it is a large refactor that
adds no knowledge. Do it after item 1 reports which families are worth keeping. On
today's evidence the honest answer might be "none", and a package of eighteen
per-family modules for eighteen families with no demonstrated edge is machinery
standing in for a result.

---

## 5. The blunt part: routines or model work?

**Neither produces an edge on the evidence in hand, and the plan should not be
read as though one of them will.**

Here is the state, with sample sizes:

| Instrument | Result | Sample |
|:--|:--|:--|
| Forecast skill (the deepest one) | model Brier 0.26057 vs market 0.22703; calibrated 0.23104 vs 0.22756 (2024), 0.22524 vs 0.22329 (2025) — never better, on any held-out season | 74,345 bets / 27,732 / 29,998 |
| Null baseline | betting everything returns −9.47% | 366,725 bets |
| Props backtest, held-out | 0 of 18 markets clear; best are `rush_yards` +1.6% and `pass_yards` +1.1%, intervals spanning zero several times over | 7,502 and 4,502 bets |
| Team model on card-time ladders | −9.8% pooled, interval −17.5% to −2.2%, worsening by season (2023 −4.1%, 2024 −10.1%, 2025 −15.0%) | 54,641 bets, 773 games |
| Closing-line backtest | moneyline −6.2%, spread −1.9%, total −1.8%; every interval includes zero | 1,923 / 1,886 / 1,708 bets |
| Pre-registered subgroup search | 0 of 12 subgroups survived, 0 of 12 mechanisms held; four reversed outright | discovery 2023-24, validation 2025 |
| The one market that replicates | `tackles_assists` +11.7% held-out — and it is the one market the settlement screen flags. Same fact, not two | 3,109 held-out bets |

**What routines buy.** Not return. They buy the integrity of the only asset that
can still grow. The bought population is complete — 816 events, every NFL game for
which historical props exist — and cannot be extended. Forward evidence is 272
games a season and cannot be back-dated. Nine days of the work in items 2–9 makes
the difference between a 2026 ledger with 57 accounted-for game days and one where
nobody can say afterwards which Sundays were missed. That is worth doing and it is
worth doing **now**, because the deadline is real and the work is small.

**What routines do not buy.** They will not make the model informative. Items 12,
13, 14, 18 and 19 are the EPL's strategy machinery, and every one of them acts on a
signal this lab has measured as absent. Building them before item 1 reports is
building a distribution system for a product that does not exist.

**What model work might actually produce an edge — and the honest state of each:**

1. **Snap share and target share, lagged, as model inputs.** Available today and
   unused. The model fits usage from recent volume, which prices a player's recent
   role rather than his current one. This is the single genuine unexploited input
   in the repository. The caveat is severe and already measured: *contemporaneous*
   target share cleared discovery at +10.69% over 7,644 bets and is a **post-game
   quantity that could not have been bet**; on held-out 2025 it returned +6.68%
   over 4,904 bets with an interval of [−5.71%, +19.07%] which includes zero; and
   the **lagged version, which is knowable at bet time, is not monotone at all.**
   So the prior on this is poor. It is still the best remaining idea.
2. **The game-state mechanism the calibration named — and which the evidence then
   contradicted.** Walk-forward PIT found excess mass in the lowest decile on
   `rush_yards`, `rush_longest`, `pass_completions` and `pass_yards` (14.8–15.8%
   against 10%): very low outcomes happen more often than the model allows, because
   nothing here knows a player's day can be cut short. That story predicts under
   value-add is highest in blowouts. The subgroup search found the **opposite** —
   under value-add is highest in the *tightest* games (+7.39% at |spread| < 3) and
   flat everywhere wider. **The game-script model that finding motivated should not
   be built on this evidence.** Recording this here so it is not proposed again.
3. **An independent settlement source for `tackles_assists`.** It would resolve the
   one market that replicates. Be clear about the likely outcome: nflverse records
   about half a tackle per player-game fewer than the books settle on, the featured
   market is priced 50% over across 6,575 featured wagers while the outcome lands
   over 42% of the time, and at a +0.5 offset the entire +11.7% vanishes. Finding
   the source most likely **kills** the candidate rather than confirming it. That is
   still worth knowing, and it is the only way to ever know.
4. **Forward evidence itself.** 272 games a season. Do not expect it to settle
   anything in 2026: the props backtest declares 200 bets as its advance minimum
   and markets with 3,000+ bets still carry intervals spanning ±6 points. One
   forward season is a start on a multi-season question, which is precisely the
   argument for building the routine now and against expecting an answer from it
   soon.

**The sequence I would actually run:**

1. **Days 1–9 (to 2026-09-09): items 2, 3, 4, 5, 7, 9, and the minimal 8.** Hard
   deadline, small total effort, and the only work on this list with a date that
   cannot slip. Item 6 lands by 2026-09-14, before the first Monday settlement.
2. **Immediately after Week 1 ships: item 1.** Hours, zero credits, and the only
   item that can change what the lab knows. Its result decides whether items 12–14
   and 18 are deferred or **deleted**.
3. **Then model work — item (1) in the list above, lagged snap and target share —
   and not more porting.** If item 1 finds nothing (the likely case) and lagged
   usage adds nothing, then the correct answer is the one this repository has
   already reached honestly four independent times: there is no edge here, the lab
   is cheap to keep running, the forward ledger accumulates, and nothing is bet.

**The fifth possibility, said plainly, because a plan this long invites the
opposite conclusion.** It is possible that this model has no edge to find and that
no amount of routine-building, calibration, thresholding or per-market splitting
will change that. The machinery that established the current answer — and that
caught three of its own defects and retracted three of its own headline findings in
four days — is the product. Porting the EPL's operating routines makes that
machinery reliable and legible. It does not make it profitable, and this document
should not be cited later as though it planned to.