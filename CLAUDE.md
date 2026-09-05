# CLAUDE.md — Football Betting Lab Operating Instructions

This repository is the source of truth for the Football Betting Lab. Claude
operates it directly. Where anything else in the repo conflicts with this file,
this file wins.

**Active repo path: `/Users/cooperross/Projects/football-betting-lab`.**

**Scope: this lab is the NFL, and only the NFL.** Cooper, 2026-08-31: NCAAF
is a **separate project in its own repository**, not a second league in this
one. Do not add college football here — not a registry entry, not an adapter,
not a season calendar. If a session finds itself widening this lab to cover
another league, it has misread this line.

The league registry stays, and it is not wasted work. It is what keeps the
league-specific pieces — provider sport key, market list, season calendar,
roster source, model parameters — in one place rather than scattered through
the code, which is exactly what makes this machinery copyable into a college
lab without a refactor first. It is now a **portability** device rather than
a multi-league one.

**What separation costs, stated once so it is not rediscovered the hard way.**
This lab and `../nhl-betting-lab` share no code, and the same defect classes
appeared independently in both: a 422 zeroing an entire per-event fetch, a
provider failure publishing as an empty slate, settlement joining on a raw
name string, an empty-slate exit running before the degraded check, and two
calendars for one slate. Six NHL fixes were ported into this lab **by hand**
on 2026-08-31. A third lab means a third hand-port, every time. That is the
price of separation, it is Cooper's call to pay it, and the mitigation is to
read the sibling labs' `docs/` before believing this one is sound.

The lab is modelled on `../nhl-betting-lab`, deliberately: the verdicts door,
the forward-evidence ledger, the allowlist receipt and PR gate, the start-time
guard, `selection_key()`, the accounting identity, the cache and shrink guards
and the honesty rules are carried over because they were earned there. Change
the sport, not the standards.

## Read these first

Every session, in this order. These replace chat history as project memory.

1. `CLAUDE.md` (this file) — hard rules, which override everything.
2. `docs/what_we_can_and_cannot_claim.md` — written before the first
   measurement. Read before making any claim about whether this works.
3. `docs/football_data_sources.md` — where every number comes from, what each
   source cannot tell us, and its licence.
4. `docs/credit_cost.md` — what this costs against a quota shared with the NHL
   lab, and the one unanswered question that moves the answer.
5. `docs/project_status.md` — where the lab is and what to do next.
6. `docs/build_order.md` — what was built, in what order, and why.
7. Latest `data/outputs/` reports, then PRs and Actions runs.

## Current operating state

**As of 2026-08-31. Everything is measured and the answer is no demonstrated
edge.** The models exist, the full available historical population is bought
and scored, and four independent instruments agree that nothing clears the
bars declared in advance. Three defects that had manufactured every earlier
positive result are fixed. **No market is allowlisted, nothing is bet, and
that is the correct state.**

- **Week 1 opens Wednesday 2026-09-09**, NE @ SEA, 20:20 ET — **not** the
  Thursday after Labor Day, which is the season's second game (SF @ LA,
  2026-09-10). Verified against the nflverse schedule, as the brief instructed,
  rather than assumed. That is **9 days from today**.
- **The 2026 regular season is 272 games across 57 game days**, 2026-09-09 to
  2027-01-10, weeks 1-18. Largest slate: 16 games on 2027-01-10, all
  simultaneous.
- **The quota resets monthly, and credits are not a constraint.** Confirmed by
  Cooper 2026-08-28. The heaviest month of the NFL/NHL overlap is 2026-11 at
  **10,084 of 100,000**, running every market this lab has wired. Tiers in the
  market registry are now a *staging* decision, not a budget one.
  `docs/credit_cost.md`.
- **An earlier version of this file said buying history was impossible. That
  was wrong**, and it was wrong because it read the quota as an annual pool.
  One season of tier-1 historical prices is 125,120 credits — **1.25 months**.
  The price-based backtest that decides everything in the NHL lab is available
  here. The record of the reversal stays in `docs/credit_cost.md`.
- **Three priced instruments**: the free closing-line series in the nflverse
  schedule file (back to 1999, complete for 2024-25, 112 of 272 2026 games
  already lined — one consensus line, no ladder, no props, team markets only);
  forward evidence at 272 games a season, which **cannot be back-dated** and is
  therefore built first regardless; and bought history, now probed.
- **The retention probe has run (2026-08-28, 7,280 credits, Cooper's
  approval).** 20 events stratified across kickoff windows, split evenly
  between 2024 and 2025, 46 provider keys each, 60 minutes before kickoff.
  **All 27 tier-1 markets have historical prices; 25 have enough to measure
  against**, across nine books. `reception_tds` and `rush_tds` are retained
  but thin — 2 of 20 events, one book each — and "retained" is not "measurable".
  Quota after: 79,659 of this month's 100,000.
- **The documented 10x historical rate is now measured, not assumed**: about
  10.4 credits per market returned. A full tier-1 season at one snapshot should
  cost nearer 99,000 than the pessimistic 125,120.
- **The probe reproduced the `total_2_5` mistake before it could be made.**
  Three featured prop keys returned nothing across all 20 events while their
  alternate ladders had them. Read per key that is three unmeasurable markets;
  read per market — the unit that gets modelled, measured and approved — it is
  none. Every retention conclusion rolls up to the market first. The reverse
  case is in the same data: `pass_longest_completion` is retained on 20 of 20
  and its ladder on none.
- **Two defects were found and fixed by reproduction, each with a regression
  test.** The probe cached chunk responses under a filename tagged with the
  chunk's *length*, so four ten-market chunks collided and three were lost —
  the NHL lab's `_markets_fingerprint` exists for exactly that and was not
  ported. And the secrets guard flagged the provider's 32-hex **event ids**,
  which are the same shape as an API key; the exemption is by recorded value,
  never by directory, so a hex run that is not a known event id is still a
  finding even under `data/raw/`.
- **The report is derived data and rebuilds from the run record**
  (`scripts/rerender_retention_probe.py`). Improving its wording must never
  cost 7,280 credits again.
- **NCAAF now fits the quota too.** All three labs at the full catalogue land
  around 33,000 of 100,000 in a peak month. The reason to defer college
  football is no longer money — it is that the NFL is not built, that FBS is a
  different distribution needing its own fits and verdicts, and that adding it
  must not move a single NFL number.
- **The league registry exists and the NFL is its only entry.**
  `src/football_betting_lab/leagues.py` holds every league-specific fact:
  sport key, adapter, market registry, timezone, credit cap, policy key,
  output prefix. A discipline test fails the build if a league literal appears
  anywhere else.
- **60 markets are wired with the nflverse quantity each settles against**,
  across two tiers; the provider's remaining NFL keys are in
  `markets.DEFERRED_MARKETS` with a reason each. Wired is not quoted and not
  allowlisted: **no market is allowlisted, and that is the correct state.**
- **Play-by-play settles almost everything**, including quarter and half
  scores and touchdown *ordering* — unlike the NHL lab, where periods and goal
  order were genuinely unsettleable. Defensive counting stats are the
  exception: they are revised by the NFL between Monday and Wednesday, so
  settlement reads the Thursday copy and re-settles rather than leaving a
  pre-correction row.
- **Route participation cannot be had in season.** nflverse's participation
  feed publishes only after the post-season. Snap share (PFR, in season,
  lagged) and target share (from play-by-play, same lag) are available; routes
  run are not, and no report will imply otherwise.
- **No feed publishes inactives, so no player prop can produce a selection.**
  The availability gate has five states and **nothing can reach `confirmed`**:
  `excluded` (listed Out), `doubtful`, `questionable`, `undesignated` (a report
  exists and the player is not on it — evidence, not confirmation), and
  `no_report` (no report filed at all). The last two are kept apart because a
  missing feed makes every player look healthy: there is no 2026 injury file
  until Week 1's practice week, and a gate that read that as "nobody is
  injured" would clear an entire slate. Player props are priced, frozen and
  settled; they cannot be selected. The exact analogue of goalie saves.
- **A player's club comes from the current roster, never his last logged
  game — measured live, not argued.** The first shadow run priced 61 players
  across the two Week 1 openers; **6 (9.8%) are on a different club than their
  last logged game** (A.J. Brown PHI→NE, Romeo Doubs GB→NE, Mike Evans TB→SF,
  Christian Kirk HOU→SF, Emanuel Wilson GB→SEA, Reggie Gilliam BUF→NE). Each
  would have matched neither side of its fixture and produced no opinion at
  all. The NHL lab's figure was 20.4% of 815; this one is 61 players over two
  games and the sample is stated wherever the number is. 10 more were unknown
  to the 2026 roster entirely.
- **Names resolve by identity, never by string**: `A.J.`/`AJ`,
  `Deebo Samuel Sr.`/`Deebo Samuel`, `D'Onta Foreman`. Disambiguated by the
  clubs in the fixture, and **a lone candidate on the wrong team is a void,
  not a match**. Clubs are validated against the league registry, because
  passing the provider's club names where abbreviations belong resolves every
  player to nothing and reads as a board full of unknown players — which is
  what happened on the first real call.
- **A quarterback change quarantines rather than reprices.** The model has no
  fitted knowledge of the backup, so a repriced number would be an invention
  that looks like an opinion. It quarantines the passing and receiving tree
  only — not the kicker, not either defence. A depth chart older than 48 hours
  cannot answer the question, and an unanswerable question quarantines.
- **Week 1 opens on a Wednesday because Thursday's game is in Australia.**
  SF @ LA on 2026-09-10 is at the Melbourne Cricket Ground, so the domestic
  opener moved to Wednesday 2026-09-09. This is recorded because it looks like
  a data error and is not one; a future session must not "correct" it back.
- **Retractable roofs are unknown before kickoff, and the `roof` column also
  lies.** It is blank for 43 of 272 2026 games — the five retractable domestic
  venues plus the Maracana and the Bernabeu — because whether the roof was open
  is a game-time fact. Worse, it is populated and **wrong** for three open-air
  international games (Stade de France, Munich, Melbourne), all labelled
  `dome`. The weather gate never keys on `roof` alone: neutral-site and
  international fixtures are roof-unknown regardless, and the domestic venue
  list is asserted in a test rather than read from the feed.
- **`nfl_data_py` is archived** (last push 2025-09-25). This lab fetches the
  nflverse release assets directly and caches them.
- **The adapter is proven against real responses.** The first live shadow run
  (2026-08-28, 41 credits against a 95 bound) staged **3,589 rows across 17
  markets and 9 books** for the two Week 1 openers, with **zero unparseable**.
  Books are pricing props twelve days out. `anytime_td` lands as touchdowns
  over 0.5 with no `yes`/`no` leaking into a selection; team totals land as
  `home_over`…`away_under`. Nothing staged can reach the card.
- **The data layer is built and the processed tables exist**: 1,359 team-games
  and 72,457 player-games over 2022-2026. Every tier-1 settlement column is
  present and asserted by test.
- **2022 has 271 regular-season games, not 272.** Buffalo-Cincinnati was
  abandoned and never replayed. A build that "corrected" this to 272 would be
  inventing a game; `tests/test_schedule_facts_a_fresh_clone_can_check.py`
  pins it **against the committed schedule**, so it now runs in CI — the
  version that pinned it before needed gitignored processed tables and was
  skipped in every CI run.
- **`anytime_td` settles on touchdowns SCORED, never `passing_tds`.** A
  quarterback who throws four has scored none. Reading the passing column
  would make every quarterback the likeliest scorer on the field. Of 105 QB
  games with four or more passing touchdowns, five carry an anytime
  touchdown, all from rushing or receiving.
- **Yardage can be negative, so a maximum can exceed its total.** AJ Dillon
  caught passes for 35 and −10 in 2023 week 14: total 25, longest 35. There are
  262 such cases in four seasons. The obvious sanity check is false here and
  "fixing" it would invent data.
- **The weekly stats and play-by-play disagree on 0.21% of single-reception
  games** (10 of 4,857; zero for rushes and completions) — laterals and
  gamebook revisions, not a join fault. Deliberately not reconciled: both
  sources describe the same play correctly. **No test bounds this any more.**
  The one that did needed the gitignored play-by-play, so it was skipped in
  every CI run, and #31 deleted it rather than keep a guard that never fired.
  The figure above is therefore a measurement from 2026-08-31, not a live
  invariant, and it will not fail if the feeds drift. A test asserts that this
  paragraph does not claim otherwise.
- **`roster_weekly_2026.csv` is byte-identical to `roster_2026.csv`** and holds
  only week 1. Before a season starts the "weekly" roster is a single snapshot,
  so anything expecting role history from it finds none — silently.
- **Schedule states are free and leak-free**: `home_rest`/`away_rest` are
  populated for all 272 2026 games today. 33 team-games on a short week, 30
  off a bye, and 8 neutral-site games — Melbourne, Rio, London twice, Paris,
  Madrid, Munich, Mexico City — six of them kicking off at 09:30 ET. Eight
  games is too few to measure an international effect, and the report will
  say that rather than reporting a number over eight games.

- **The models exist and are measured.** The team model takes its *shape*
  from the empirical score distribution and fits only the mean, by exponential
  tilting, so the lumps at 3, 7, 10, 14 survive and a whole-number line pushes
  exactly (−3 pushes 3.4% of the time, −3.5 never). Player props are **one
  compound simulation per player** — draw opportunities, draw that many
  per-play yardages tilted to his own efficiency, read the sum, the maximum
  and the touchdowns off the same draws. Receptions and yards and longest
  cannot disagree, and every alternate rung prices from the same distribution
  as the featured line.
- **Walk-forward calibration is run and reported**
  (`data/outputs/nfl_props_calibration.md`, fitted pre-2025, scored on 2025,
  1,248 / 1,193 / 526 player-games). Randomised PIT deciles are close to flat.
  All nine quantities have a mean PIT below 0.5 — but that is **three
  independent observations, not nine**: within a family, opportunities, yards
  and longest are read off one simulation. Three families leaning one way is
  what a coin does one time in eight, which is not enough to call systematic.
- **The calibration found the missing mechanism, and it is the expected one.**
  Excess mass in the lowest decile on `rush_yards`, `rush_longest`,
  `pass_completions` and `pass_yards` (14.8-15.8% against 10%): very low
  outcomes happen more often than the model allows, because **nothing here
  knows a player's day can be cut short**. Blowouts empty benches and injuries
  end afternoons. The model is unconditional on game state and says so; this
  is what that costs, measured.
- **Snap share and target share are available and not used yet.** The model
  fits usage from recent volume, which prices a player's recent role rather
  than his current one. Stated wherever a prop number appears.

- **The whole path runs, end to end.** `scripts/run_gameday_card.py` fetches,
  fits, prices, gates, freezes and settles; `Football Gameday Refresh`
  publishes the card to `card-feed`. Replayed against the real Week 1 board it
  priced 2,000 rows into 1,903 frozen opinions with the identity reconciling
  and **zero selections**, which is the correct output of a lab with no
  allowlisted market.
- **The ledger lives on the `card-feed` branch, not in an artifact.** A frozen
  opinion is evidence precisely because it was written before the game, so it
  cannot be rebuilt if it is lost to a retention window. Each run restores the
  ledger and the snapshots from the branch before it starts.
- **The card feed is built with git plumbing, never `git add -A`.** Only files
  named one at a time reach the branch. A working tree holding `data/staging/`
  and a `.env` staged wholesale is how a credential reaches a public ref, and
  a test forbids it in every workflow.

- **The team model does not beat the closing line, and that is now measured.**
  Walk-forward 2016-2025, 2,639 games, betting only where the model disagrees
  with the close by 3.5%+ at a price no worse than -160:
  moneyline **-6.2% over 1,923 bets**, spread **-1.9% over 1,886**, total
  **-1.8% over 1,708**. Every interval includes zero before and after the
  family correction. **No demonstrated edge**, on samples large enough to mean
  it. `data/outputs/nfl_closing_line_backtest.md`.
- **That test is conservative in two directions at once** and the report says
  so: it bets into the close, which is the sharpest price of the week, and it
  uses one consensus line rather than the best of the nine books quoting these
  games. A card does neither. CLV cannot be measured there at all, because the
  bet is placed at the close.
- **Two defects in that backtest were caught by disbelieving a good result.**
  It first reported **+21.6% on the spread over 1,695 bets**, an interval
  excluding zero even after correction. The cover rate was 61.5%, which is not
  a thing that happens. Both sides of a spread were being derived from one
  `spread_line` without negating for the away side, so **both sides could win
  the same game** — 147 of the 402 games where both were bet. And before that,
  the spread and total reported **zero bets**, which read as "the model never
  disagrees enough"; in fact their price columns had never been built, and a
  `getattr(..., None)` default turned a missing column into a quietly skipped
  market. A missing price column is now an error.

- **The historical purchase is complete and cannot grow.** 587,732 credits,
  5.67M price rows, **816 events across 2023-2025 — every NFL game for which
  historical props exist**, both snapshots on 815 of them. The provider serves
  props only after 2023-05-03, so there is no more to buy. 4,473,866 credits
  left. The only evidence that can still grow is forward, from 2026-09-09.
- **A partial purchase is a sample, not a prefix.** Events are bought in an
  order whose every prefix is spread across the season, so the 67% covers
  every week at 62-73%. The first ordering left the kickoff *windows* uneven
  (Sunday night 50%, Monday 76%), which matters because book coverage differs
  by window; the order is now stratified by window, measured against three
  alternatives, and the residual week imbalance is structural — 21 Thursday
  games across 18 weeks cannot be two-thirds sampled evenly.
- **The stratified order stopped mattering once the purchase completed**, but
  it is recorded because a future partial buy will need it again.

- **Every prop number this file used to carry was wrong, and the corrected
  answer is that nothing has a demonstrated edge.** Three defects were found
  after the first round of findings was written up, each of which inflated
  returns, and all three are fixed with regression tests. The account of what
  they were and what they cost is below, under *Three defects, and the numbers
  after them*. Read that before believing any prop figure anywhere.
- **The claim that the count models were "roughly centred" was false, and it
  was used to rule out an explanation.** An ad-hoc measurement reported mean
  PIT 0.51-0.54 across the count markets, and that was cited as evidence
  against the first explanation offered for the tackles result. It cannot have
  been true: the same model fitted `sacks` at **0.988 a game against a league
  mean of 0.069** — a fourteen-fold over-prediction — and a model that wrong
  cannot be centred. The number was never regenerated by a script, so nothing
  caught it. Re-measured after the zero-inflation fix, the same fit returns
  **0.044**.
- **The walk-forward calibration covers the three compound families only**
  (`data/outputs/nfl_props_calibration.md`, 9 quantities, fitted pre-2025 and
  scored on 2025). It is unchanged by the three fixes. **There is no committed
  calibration of the count markets**, and any future statement about their
  shape has to come from one.

- **The verdicts door exists and nothing ships through it.**
  `verdicts.py`: an experiment measures a policy, records its verdict as a
  file under `data/outputs/`, and the model reads that file rather than a
  constant. A missing or unreadable verdict ships nothing. Each verdict
  records `variants_tested`, because every variant tried against the same
  bought season spends a degree of freedom.
- **Recency weighting: measured on all three seasons, does not ship.**
  Half-life 8 games returned −2.7% against the baseline's −3.1%. The **paired**
  difference over the 768 games both arms bet is **−0.1% per bet, interval
  −1.5% to +1.4% — not distinguishable from zero**, and it fails to clear 2023
  and 2024 individually.
- **That verdict was a single-season coin flip until 2026-08-31.** The script
  scored one season and wrote a verdict file with one name, so the policy
  shipped or did not depending on which season had been run last: +2.3% on
  2025 shipped it, −1.8% on 2023 did not. Same policy, same script, opposite
  verdicts, and the card reads whichever ran most recently. It now scores every
  season and ships only if the paired difference clears in **all** of them. The first decision rule was `roi_variant >
  roi_baseline` and would have shipped it; comparing two overlapping intervals
  and taking the larger number is how a lab ships noise, and the arms' own
  intervals span several times the gap between them.
- **The first-half model exists and does not ship either.** Pooled **−4.6%
  over 2,866 bets**, interval −15.2% to +6.1% — **no demonstrated edge**.
  `total_points_h1` is the one component whose interval excludes zero, at
  **−17.2% over 1,138 bets**, and it excludes zero on the losing side.
- **That experiment carried the cross-season defect too, and its verdict
  changed.** It keyed every priced event to `args.season` while holding all
  three bought seasons, so a 2023 Chiefs-at-Broncos event settled against the
  2025 meeting. It previously reported −16.5% over 619 bets. The same defect,
  in a second script, written weeks apart. `events_in_season` is now the only
  way to answer that question and a discipline test enforces it
  (`tests/test_priced_events_are_matched_to_their_own_season.py`). It is the crudest thing that
  could work — each side's full-game expectation scaled by the league's
  first-half share (0.506, measured) with the shape from the empirical
  first-half distribution — and the priced test says no.
- **A half does not go to overtime, and that had to be fixed.**
  `GameDistribution` hardcoded the full-game rule, so the half model priced a
  level half at 0.4%. Measured over 1,087 games, **7.4% of first halves end
  level against 0.35% of full games** — a factor of twenty-one. Segments now
  carry `resolves_ties=False`.
- **The half markets stay `no_opinion` until a verdict says otherwise.** They
  are wired, settleable and retained on 20 of 20 probed events, and pricing
  them would fill the ledger with opinions already measured to lose. Whether
  that trade is worth making for the sake of forward evidence is Cooper's
  call, not a script's.

- **Credits are no longer a constraint.** Cooper added 5,000,000 on
  2026-08-28 and the month reset the same day (`x-requests-used` fell to 0,
  which the free daily quota check observed rather than assumed). The
  purchase programme is 2023, 2024 and 2025 at **two snapshots each** — card
  time and the close — 1,632 season-events, ~752,000 credits pessimistic.
  That buys **replication across seasons**, which is what the brief demands
  and what the `tackles_assists` candidate needs, and **CLV on every
  historical bet**.
- **A broken run reaches a human.** Every run posts to the pinned issue
  `Football Betting Lab — Claude Operating Home` (#1) — the card, or a loud
  degraded notice. The posting step always runs, because the case that most
  needs reporting is the one where an earlier step died. Verified by a real
  failure, not a contrived one.
- **The card refuses to fetch on a thin quota.** A run that starts with less
  than its cap gets partway through the slate and stops, freezing a biased
  subset into the ledger as though it were the day. An unreadable quota
  header does not block the run.
- **Rehearsals never touch the evidence.** `--rehearsal` writes to its own
  archive, settles nothing, labels its output `REHEARSAL — not a card`, and
  never publishes to `card-feed`. A live run pricing any date but today is
  **refused** without it: freezing a snapshot for a future slate would make
  the real run that day find one already standing and leave it there, and the
  first opinion of Week 1 would be a rehearsal taken before the teams were
  known.
- **The rehearsal found the crash the first real run would have hit.** It
  failed on exactly the branch state 2026-09-09 would have had — a card feed
  with a card and no ledger yet. `git show ...forward_evidence.csv > file`
  fails, the shell redirect creates the file anyway, and pandas refuses a
  zero-byte CSV. Fixed on both sides: the workflow writes restores to a temp
  and moves only on success (ledger **and** snapshots, which had the same
  hole), and the card reads every CSV defensively.
- **Card-time and closing prices are never mixed.** Each cached price carries
  the snapshot it came from, derived from the filename stamp. Without it the
  best-price collapse would take the better of a card-time price and a
  closing price for one wager — not a price anyone could have taken, and it
  would have inflated every measured edge. The backtest prices card time
  only; the close is for CLV.

## Three defects, and the numbers after them

Between them these produced every positive result this repository has ever
reported. Each was found by disbelieving a good number, none was found by a
test that existed at the time, and each now has one.

**1. Cross-season settlement.** `_game_weeks` matched a priced event to a
club pair *within the target season* and ignored the event's own kickoff,
while the caller handed it all three seasons at once. So a 2023
Detroit-at-Chicago event was also settled against the 2024 and 2025 meetings
of the same clubs. **406 of 794 events settled against more than one season;
100,466 of 148,587 bets were on such events.** One 2023 event appears 286
times in the bets file across three "seasons". The minimum-edge filter then
selected exactly the wagers where the stale line was most wrong, so the
mis-settled rows carried all of the apparent edge: **+23.5% against −6.4% on
the rows that settled against their own game.** It did not look like a bug.
It looked like three seasons of replication.

**2. A walk-forward leak.** `play_yardage.json` was built over every season
pooled and loaded once, outside the per-week loop, so the per-play yardage
distribution used to price week 1 of 2023 had seen 2025. **Only the compound
markets consume it** — which is precisely why the compound group looked good
and the count group did not.

**3. Zero-inflation in the count fits.** `fit_rates` conditioned on
appearance, so `sacks` was fitted at **0.978 a game against a league mean of
0.073** — a thirteen-fold over-prediction. That is why the model took the
Over on 92% of sacks and lost.

### What is left after all three

| Instrument | What it says now |
|:---|:---|
| Null baseline | Betting everything returns **−9.29% over 366,725 bets**. The harness is sound. |
| Backtest | 2023 **−2.6%** (18,329), 2024 **−2.5%** (30,119), 2025 **−5.4%** (32,557) — staked bets per season, computed from the committed `nfl_props_backtest_bets.csv` and pinned by a test that recomputes them. (Corrected 2026-09-03: read −1.6%/18,062, −2.1%/29,394, −5.2%/31,317 from before the settlement-join fix.) |
| Replication | **Nothing replicates** on a season it was not selected on. `tackles_assists` was the lone exception until its summation bug was fixed; it is now −1.0% over 2,758 held-out bets. |
| Settlement screen | **Every market agrees with its price.** `tackles_assists` was the only suspect; post-fix its gap is −1% over 6,575 featured wagers. |
| Price sensitivity | **No market is profitable at the consensus price.** `tackles_assists` is +0.9% there and positive at only 3 of 8 books. |
| Allowlist bundle | **0 of 18 markets clear every bar.** |

Every one of the eighteen markets returns **no demonstrated edge** on its
held-out seasons — that is the phrase and it is meant literally: the
family-corrected interval includes zero in every case. The best held-out
numbers are `rush_yards` **+2.2% over 7,780 bets** and `pass_yards` **+1.5%
over 4,469**, both with intervals spanning zero several times over.
(Corrected 2026-09-03: these read +1.6%/7,502 and +1.1%/4,502, from before the
settlement-join fix. `nfl_props_replication.md` is the source.)

## Two calendars for one slate, and the watchdog that never fetched either

**Found 2026-09-01 by firing the weekly watchdog after changing it**, which is
the discipline this file already states and had not been applied here.

**The watchdog's schedule fetch had never once succeeded.** Its argument was
`--only schedule`; the feed is `schedules`. The script exits 2 on an unknown
feed, and a `|| true` on the step swallowed it on every run since the workflow
was written. The comment on the step immediately below describes this exact
failure — *"`|| true` was here and swallowed an argument error"* — because the
previous fix corrected that step and left this one. **Fourth occurrence of the
family, second inside a fix for itself.**

It failed in the direction that looks like success. A committed calendar already
existed, so the coverage and freshness checks ran against it, **both returned
success**, and the week would have been reported **intact**. The gate now reads
the fetch's outcome first, and on the run that found this it printed *"broken
watchdog, NOT evidence about the ledger"* — which is what it was.

**And there were two calendars.** `season.schedule_path` named
`schedule/nflverse_games.csv`, which **nothing writes**. The `schedules` feed
lands at `schedules/games.csv`, which until now **nothing read**. So every fetch
updated one file and the card's preseason screen judged against the other,
frozen at whatever was last committed. They had already drifted — on the
`spread_line`, `total_line` and moneyline columns, which are not decoration
here: the schedule's closing prices are one of the three priced instruments this
lab has.

**What the stale calendar would have cost.** `known_regular_season_games`
decides whether a provider fixture is preseason by matching `(date, HOME, AWAY)`.
The NFL flexes games between slots and dates all season. A game whose date moved
would match nothing in a frozen calendar, be read as **preseason**, and be
dropped from the card — freezing no opinion for a game that was played, in a
ledger that cannot be back-dated. `schedule_cache_is_complete` would still have
reported 32 clubs, so nothing would have fired.

`schedule_path` now delegates to the feed, the orphan file is deleted, and two
tests hold the line: one asserts the path the code reads is the path the fetcher
writes, the other that no orphan reappears. A third asserts every `--only` in
every workflow names a feed that exists — an argument error is otherwise
discoverable only at runtime, which is exactly how this one survived.

## The forward ledger's interval was sqrt(games) too narrow

**Found 2026-09-01, eight days before the ledger starts accruing.** Found the
way the three earlier defects were: by writing an invariant test that asserted
something obvious — that clustering *widens* an interval — and then not
believing the result when it failed.

`forward_evidence.interval_by_game` divided by `games` twice, once building the
variance and again taking the root:

```
variance       = (w^2 * s^2 / G).sum() * G   # already Var(estimator)
standard_error = sqrt(variance / G)          # divides by G AGAIN
```

On twenty games of twenty perfectly correlated bets it reported a half-width of
**0.10 where a bootstrap over games gives 0.40** — out by exactly sqrt(20). Over
a full season of ~250 games it would have been out by a **factor of sixteen**.

**This is the worst function in the repository to have had it in.** It reads the
forward ledger — the only evidence this lab can still gather, and the one number
Week 1 starts producing. A too-narrow interval is precisely how *"no demonstrated
edge"* quietly becomes a claim, which is the failure its own docstring names. It
would have made "the interval excludes zero" fire on noise all season.

The illustration is not hypothetical. On the eight-game fixture in
`tests/test_numeric_invariants.py`, the broken estimator returns **(+0.040,
+0.509) — an interval excluding zero.** The correct one returns **(−0.223,
+0.771)**, which includes it. Same data, opposite conclusion.

Replaced with the cluster-robust standard error of a ratio estimator, which is
what a pooled ROI is: total profit over total bets, games contributing unequal
numbers of bets. **`props_backtest._interval` and
`closing_line_backtest._interval` were already correct**, and only this third
copy was wrong.

**Three copies of one formula is how that happens, and a comment saying "these
must agree" is not a guard.** `test_every_clustered_interval_in_the_repository_agrees_with_the_others`
now asserts all three return the same interval on the same per-game data, with
deliberately unequal bets per game — a ratio estimator and a mean-of-ratios
estimator agree when every cluster is the same size, so equal sizes would let a
wrong implementation pass. Reverting the fix fails that test.

## `tackles_assists` was a summation bug, not a settlement artefact — and this section said otherwise for days

**Correction, 2026-09-02.** This section claimed `tackles_assists` replicated at
**+12.4% / +11.2% / +12.6%**, returned **+11.7% over 3,109 held-out bets**, was
flagged by the settlement screen at a **seven-point** gap, was positive at **8 of
8 books**, and was *"structurally unmeasurable until an independent settlement
source exists"*. **Every one of those numbers is stale.** The committed reports
have said something different since the summation was fixed, and this file was
never updated to match. Found by mapping the measurement code and disbelieving
the mismatch.

The actual cause was the lab's own settlement arithmetic: `tackles_assists` is
the sum of **all three** defensive columns, and `def_tackles_with_assist` — a
tackle the player *made* while someone else assisted — was being omitted. That
is a data bug in this repository, not an unknowable offset in the books'.

What the four instruments say now, read from the committed reports rather than
from memory:

| Instrument | `tackles_assists` |
|:---|:---|
| Settlement screen | priced 50% over, realised **48%**, gap **−1%** over 6,575 featured wagers — **agrees with the price** |
| Replication | 2023 **−0.9%** (1,194), 2024 **−1.2%** (1,564), 2025 selection +8.6% (1,397) — **−1.0% over 2,758 held-out bets, no demonstrated edge** |
| Price sensitivity | +2.1% best-of-N, **+0.9% at the consensus**, positive at **3 of 8** books — mixed |
| Allowlist bundle | **not supported** — fails books and replication |

**So the market is measurable after all, and it is measured: no demonstrated
edge.** It does not belong beside goalie saves in the NHL lab, and the sentence
that put it there was wrong.

**This makes the lab's conclusion simpler, not weaker.** The old story was
"nothing replicates except one market, and that one is unmeasurable" — a null
with an asterisk. The true story is **nothing replicates, full stop**, and the
settlement screen agrees with the price on every market it can read.

**The lesson is the one this repository keeps paying for.** A number that no
script regenerates goes stale silently. These figures lived in prose while the
reports that superseded them sat in `data/outputs/`, and nothing compared the
two. The reports are derived data and are regenerated; this file is not, so a
claim here about a measured quantity must cite the report it came from.

- **Sixteen of seventeen screened markets agree with their price** within four
  points. `sacks` agrees too (33% priced, 32% realised), so the sacks result
  was the model being wrong, not settlement — and the zero-inflation fix
  explains it exactly.
- **The question that broke it** was never "is this result robust". It was
  **"what would betting one side with no model at all return?"**

## `rush_yards` does not stand up, and this file twice said it did

**Correction, and it is the second one on this market.** This file previously
reported `rush_yards` at **+14.0% held-out**, then at **+8.3% at the consensus
price, positive at 10 of 11 books**, and called it the last thing standing.
Both readings were computed on cross-season-settled bets with a leaked yardage
distribution. Neither survives.

| Test | Result now | Source |
|:---|:---|:---|
| Three seasons | +1.3% (2,971), +2.8% (4,809), +0.4% (4,274) | `nfl_props_replication.md` |
| Held-out pooled | **+2.2% over 7,780 bets** — interval includes zero, **no demonstrated edge** | `nfl_props_replication.md` |
| Settlement screen | agrees with the price | `nfl_settlement_agreement.md` |
| **Consensus price** | **−0.6%** | `nfl_price_sensitivity.md` |
| **Best of N books** | **+1.2%** over 11,573 bets | `nfl_price_sensitivity.md` |
| **By book** | positive at **2 of 10** | `nfl_price_sensitivity.md` |

It is a **shopping premium at best**: whatever is left exists only as the
maximum of ten quotes, and it is negative at the median price. A number that
is negative at the price most people can get is not an edge, and the earlier
sentence claiming otherwise was wrong on the arithmetic it was built from.

## There is no compound-versus-count split

This file reported the split as *"the strongest structure in the evidence"* —
compound markets **+3.5%** at the consensus against count-only at **−9.8%** —
and said it was a mechanism rather than a market. It was neither. It was
defect 2 and defect 3 sitting on opposite sides of the same line: the leak
lifted the compound group, the zero-inflation sank the count group, and the
split was the gap between two bugs.

After both fixes, at the best-of-N price, excluding the settlement artefact:

| Group | Bets | Best of N | Consensus |
|:---|---:|---:|---:|
| Compound-simulation markets (9) | 67,005 | **−4.3%** | **−6.3%** |
| Count-only markets | 7,340 | **−2.8%** | **−7.5%** |
| All markets | 74,345 | **−4.1%** | — |

At the best-of-N price the compound group is the *worse* of the two; at the
consensus price the two are within 1.2 points of each other and both are
comfortably negative. Either way there is no structure here to explain.

## The availability gate, measured again

**A did-not-play prop is voided by the book, not lost.** The stake comes back,
so "will he play?" is a question about whether there is a bet at all. That
part still holds. What does not hold is the return that made it interesting.

On `rush_yards` across three bought seasons:

| Designation that week | Bets | Voids | Void share | ROI |
|:---|---:|---:|---:|---:|
| not on the injury report | 10,678 | 629 | 5.6% | **+1.8%** |
| listed, no designation | 733 | 1 | 0.1% | −10.2% |
| Questionable | 154 | 10 | 6.1% | −12.9% |
| **all** | **11,565** | 640 | 5.2% | **+0.9%** |

Across all markets it is **−3.2% over 78,773 bets**. Every player listed Out
or Doubtful voided 100% of the time, so the gate that matters is already
automatic — that finding survives.

**The did-not-play clause no longer decides anything.** If a book graded
did-not-plays as losses rather than voids, `rush_yards` is **−4.4%** instead
of **+0.9%**, and all markets **−9.2%** instead of −3.2%. That was previously
the difference between +13.0% and −0.8% — a strategy or a disaster — and it
was the one question this lab was blocked on. It is now the difference
between roughly zero and clearly negative. **It is still worth answering
before anything is acted on, but nothing waits on it.**

## Every stat we can compute, tested against what the price got wrong

**0 of 9 pre-registered feature families. No demonstrated edge.**
`docs/preregistered_feature_search.md`, `data/outputs/nfl_feature_search.md`.

Cooper asked for every stat, record and analytic to be used. They were —
opponent defensive strength, player role, role trend, game script, rest,
weather, position, a defence-by-role interaction, and a combined fit on all of
them. All computed walk-forward and knowable before kickoff, over **78,253
staked bets**.

**The target was the residual, `won − market_implied`, and that choice is the
whole result.** The market already knows the opponent, the spread, the weather
and the depth chart. A feature that predicts a player's yards is one the price
already carries; only a feature that predicts what the price got **wrong** can
produce an edge. The two questions give opposite answers here:

| Question | Answer |
|:---|:---|
| Does opponent strength predict rushing yards? | **Yes** — yards allowed vary **2.25×** best to worst, and the model uses none of it |
| Does it predict what the *price* got wrong? | **No** — signed contrast **+4.35pp over 20,915 bets, CI [−0.93, +9.63]**; correlation with actual/line **r = 0.031** |

**You can watch the market do this.** On role trend, `market_implied` rises
monotonically across quartiles (0.410 → 0.426 on overs) while `won` does not.
The market reprices last-three-game usage in real time, and what is left after
that repricing is nothing.

**The cleanest single result is the combined fit.** A ridge model on every
pre-kickoff feature, in-sample, looks bettable: **+8.6% at a 0.03 threshold,
+16.0% at 0.05**. Out-of-fold, 5-fold grouped by game, the same rules are
**negative at every threshold** — −3.5%, −4.8%, −4.4%. That gap between
+16.0% and −4.4% is what "add all the stats and look" produces, and it is why
the held-out split is not optional.

**Three predicted directions reversed outright**: role trend (rising usage is
the *worst* overs bucket), game script (heavy underdogs are negative on unders),
and the defence-by-role interaction (low-usage players show the larger
weak-defence effect). Weather is not testable at all — 46 high-wind games
against the ~774 needed for a 2.5-point half-width.

**Worth building anyway:** the two defensive ratios, as a forecasting
improvement. A better forecaster is worth having before it is a profitable one.
**Not worth the degrees of freedom:** everything else.

## Does the model know anything the price does not? Something, not fully absorbed, and worth nothing

**Measured 2026-09-02, adversarially verified 2026-09-03.**
`scripts/run_encompassing.py`, `data/outputs/nfl_encompassing.md`. This is
the question underneath the Brier comparison: a model can lose on Brier either
because it is noise, or because it is noisy while carrying a real signal the
market lacks. Fitting

    logit P(over) = a + b*logit(p_market_devigged) + c*logit(p_model)

separates the two, because `c` is estimated **holding the price fixed**.

**`c` = +0.0695, interval [+0.0324, +0.1066] over 61,267 wagers across 762
games** — excludes zero. Out of sample, fitted without 2025, `c` = **+0.0685,
[+0.0218, +0.1152]**. It replicates on all three seasons (+0.062, +0.071,
+0.078). On the **full unselected wager universe** — 141,293 wagers, both sides,
every edge including negative — `c` = **+0.0727, [+0.0354, +0.1099]**, and on
the wagers the card *rejected* alone, **+0.089, [+0.010, +0.168]**. So
selection is not what produces it. **`b` = 0.89, not 1**: the devigged market
logit is itself slightly overconfident.

**Read "the model knows something" carefully; the honest phrase is "the price
does not fully absorb something correlated with the model."** On a carded
population the sign of `logit(model) − logit(market)` *is* the bet side on
99.997% of rows, so `c` and the side are nearly collinear — and the market has
a side asymmetry of its own: unders land about 2.4pp more often than the
devigged median says. With a bet-side dummy in the fit, `c` = **+0.0603,
[−0.0040, +0.1246] — includes zero**, while the point estimate barely moves.
That is collinearity, not refutation, but it means the placebo (below) cannot
distinguish model information from a side-specific market miscalibration,
because shuffling destroys the model–side correlation too.

**Multiplicity.** The single 2023-24 fit (z = 2.88) would not survive
correction for the several dozen specifications examined. The result rests on
the independent 2025 holdout (z = 2.97) and the pooled universe (z = 3.83).

**What it is worth decides the matter, and it is almost nothing.** Adding the
model to the price improves out-of-sample Brier from 0.24728 to **0.24700 — a
gain of 0.00028**, a third of the +0.00085 this lab already judged too small to
matter against a 0.002 threshold declared in advance.

**The blend's edge on the wagers the card selects is negative**, measured
against the vigged price actually bought and so already net of the hold: mean
−0.0107, median −0.0143, against a raw model edge whose median is +0.1357. Only
**18.4% (n = 3,593)** of carded 2025 wagers have a positive blend edge at all,
and those returned **+1.30%, [−3.23%, +5.82%]**. No threshold, side, market,
blend weight, Kelly staking, or per-game top-N rule — on the card or on the
full universe — produces an out-of-sample interval excluding zero in more than
one season. The median two-sided book hold is 6.78%, stated for scale; **an
earlier version of this section said only 1.5% of wagers cleared a half-hold,
which charged the vig twice. Withdrawn.**

**The one rule that replicates is not the model.** A forward search over 275
rules (threshold × side × market × blend weight), chosen on 2024 with a blend
fitted on 2023 only, picks `rush_attempts` **under** at blend edge ≥ 0.005;
on 2025 it returns **+10.8%, [+0.6%, +21.0%]** over 450 bets. It dissolves on
inspection: *all* 2025 `rush_attempts` unders return **+12.1%, [+4.3%,
+20.0%]** with no model at all, the blend-selected subset did worse than the
rows it dropped, the same rule was **−5.4% in 2023**, and `c` inside
`rush_attempts` includes zero in every season (+0.0605, [−0.011, +0.132]). A
2024-25 market/side quirk with a story attached — the exact object
`docs/preregistered_subgroup_search.md` warns about.

**Where the signal is:** receiving. `receptions` +0.104, `reception_yards`
+0.091, `reception_longest` +0.097, `tackles_assists` +0.110. Passing is
nothing — `pass_yards` −0.013, `pass_completions` −0.004.

**What makes this believable rather than the fourth retraction:**

- **A placebo runs every time.** Shuffled within market, `c` falls to
  **+0.0081, [−0.0101, +0.0262]**.
- **The interval is checked against a resample.** The hand-rolled sandwich is
  **0.966×** a bootstrap over games (SE 0.01894 against 0.01960); an
  independent 400-replicate bootstrap on the 2023-24 fit gave SD 0.0242
  against sandwich 0.0238, 0 of 400 replicates ≤ 0. Player, player-season,
  season-week and two-way clusters all exclude zero.
- **Selection is simulated AND measured.** With `c_true = 0` and the same
  edge ≥ 6% rule, the estimate is −0.0285, [−0.0891, +0.0322]; and the full
  unselected universe above says the same thing with real data.
- **Errors-in-variables cannot manufacture it.** Injecting noise into the
  market logit up to SD 0.40 (measured across-book SD is 0.022) moves `c` only
  to +0.089; corr(logit market, logit model) is 0.12.
- **The market is devigged per book.** Devigging best-of-N against best-of-N
  invents a market with almost no hold. Median hold 6.78% — so
  **`MIN_PROP_EDGE = 0.06` against a vigged price is about 2.6pp of real edge.**

**Adversarial verification ran on 2026-09-03** — three independent lenses
(plumbing, inference, economics) and a judge, after a first attempt died on
the account's session limit the day before. Every reported number reproduced.
**Nothing was refuted; two claims were weakened** ("orthogonal" → "not fully
absorbed"; the single fit's p-value → the holdout and the universe) **and one
bullet was withdrawn** (the double-charged half-hold). The report and this
section carry the weakened wording, and the side-dummy fit is now generated by
the script rather than asserted here.

## The model is a worse forecaster than the price it bets into

**This is the deepest result in the repository and it should be read before
any other number here.** Every other instrument asks whether a *return* is
real. This one asks the question underneath: does the model know anything the
price does not? It needs no settlement rule, no vig assumption and no edge
threshold — just a probability, an outcome, and the price's own implied
probability. `scripts/run_forecast_skill.py`.

The model is wildly overconfident; the market is nearly perfect:

| Model says | Bets | Actually happens | Market says | Model error | Market error |
|:---|---:|---:|---:|---:|---:|
| (0.6, 0.65] | 15,131 | 0.491 | 0.510 | **−0.134** | −0.019 |
| (0.7, 0.8] | 12,504 | 0.512 | 0.525 | **−0.230** | −0.013 |
| (0.8, 1.0] | 5,060 | 0.545 | 0.525 | **−0.316** | +0.020 |

**Brier over 78,253 bets: model 0.26106, market 0.22782.** Walk-forward
isotonic calibration — the map fitted on prior seasons only — closes most of
that gap and never crosses it:

| Season | Bets | Model | **Calibrated** | Market | Beats the price? |
|:---|---:|---:|---:|---:|:---|
| 2024 | 29,165 | 0.26222 | **0.23178** | 0.22827 | no |
| 2025 | 31,393 | 0.25691 | **0.22573** | 0.22390 | no |

**These figures were stale until 2026-09-03.** This table read 74,345 bets,
0.26057/0.22703 and a 2024 row of 0.26153/0.23104/0.22756 — the numbers from
before the settlement-join fix, which changed the bet population and every
count with it. `data/outputs/nfl_forecast_skill.md` had carried the corrected
values since, and nothing compared the two. The conclusion never moved; the
digits did.

The market's implied probability still has the **vig in it**, so it is an
over-estimate being scored with a handicap. The model loses anyway.

**Why this matters more than any subgroup search:** if the model is not a
better forecaster than the price, no betting rule, threshold or slice can be
profitable except by chance. A promising subgroup found after this table is a
coincidence with a story attached, and the pre-registered search in
`docs/preregistered_subgroup_search.md` has to be read against it.

**Calibration is still worth shipping.** It cuts 2025 from −5.97% to −3.69%
and 2024 from −2.90% to −1.05%. A smaller loss is not a profit, and this table
is the reason no filter turns one into the other.

## The team model on card-time ladders: the last untested angle, and it loses

**−9.8% pooled over 54,641 bets across 773 games, interval −17.9% to −1.8% —
excludes zero, negative.** `scripts/run_team_ladder_backtest.py`,
`data/outputs/nfl_team_ladder_backtest.md`.

This was the one substantial priced test the lab had never run, and it existed
because the closing-line backtest's own report called itself conservative in
two directions: it bets **into the close**, the sharpest price of the week, at
**one consensus line** rather than the best of nine books. This test does
neither — card-time snapshot, best price across every book quoting the rung,
which is what a card actually does.

It is also the only test that reaches the machinery the team model was built
for. Featured `moneyline`, `spread` and `total_points` were **never bought**
(the purchase was props-led), but 985,000 rows of `alternate_spread` and
`alternate_total_points` were, plus the team totals. Those ladders are where
the exponential tilt and the exact push mass at 3 and 7 do their work.

| Market | Bets | ROI | Corrected interval |
|:---|---:|---:|:---|
| `alternate_spread` | 23,211 | −11.6% | −25.8% to +2.7% |
| `alternate_total_points` | 17,057 | −7.2% | −23.5% to +9.1% |
| `alternate_team_total` | 7,753 | **−17.4%** | −32.2% to −2.6% |
| `team_total` | 6,620 | −1.7% | −13.8% to +10.4% |
| **pooled** | **54,641** | **−9.8%** | **−17.9% to −1.8%** |

Per season: 2023 −4.1%, 2024 −10.1%, 2025 −15.0%. It gets worse, not better.

**−9.8% is about the props null baseline (−9.29%)**, so the team model on
ladders is no better than betting them blind. Giving the model the friendliest
price it could ever see did not help, which is the same answer the Brier
comparison gives from a different direction.

**Settlement was proved against pricing before the number was believed.**
Twenty tests put all the distribution's mass on one scoreline and assert the
backtest settles each rung exactly as `GameDistribution.spread` / `.total` /
`.team_total` price it — including the pushes at 3 and 7, a missing line as a
void rather than a loss, and an unknown market as a void rather than a guess.
A sign error in any of those would have produced a plausible number rather
than an error.

## The fourth copy of the interval formula, and why it changes nothing

**Found 2026-09-02 by mapping the measurement code**, days after the third copy
was fixed. `run_team_ladder_backtest._interval` was outside the invariant test
because it lives in `scripts/` and takes a raw bets frame rather than a per-game
one, and it was a **different estimator**: a pooled ratio point estimate paired
with an **unweighted per-game-mean** standard error. Those agree only when every
game contributes the same number of bets, and on a ladder they never do — this
population runs **1 to 142 bets per game, median 74**.

**It changes no conclusion, and saying otherwise would overstate it.** Measured
against a bootstrap over games on the committed bets file (54,641 bets, 773
games): the old form was **0.960×** the bootstrap, the unified form **1.012×**.
Every point estimate, every per-season number and every verdict in
`nfl_team_ladder_backtest.md` is unchanged; only the intervals widen, pooled
from −17.5%/−2.2% to **−17.9%/−1.8%**, still excluding zero. The intervals above
are the corrected ones.

The guard now covers **all four** copies, the ladder included.

## The pre-registered subgroup search found nothing, in twelve directions

**0 of 12 subgroups survived, and 0 of 12 mechanisms held.**
`docs/preregistered_subgroup_search.md` was written before any subgroup was
measured; discovery on 2023-24, validation on held-out 2025, minimum 500 bets,
intervals clustered by game, Bonferroni across twelve.
`data/outputs/nfl_subgroup_search.md` has the full table.

**One subgroup cleared discovery and died twice.** Q3 of *contemporaneous*
target share returned +10.69% over 7,644 discovery bets. It fails for two
independent reasons, and the second is the disqualifying one: on held-out 2025
it returned **+6.68% over 4,904 bets with an interval of [−5.71%, +19.07%]**,
which includes zero — and **same-game target share is a post-game quantity**,
so it could not have been bet whatever the interval said. The lagged version,
which *is* knowable at bet time, is not monotone at all.

**Four mechanisms reversed outright**, which is worth more than the null result:

- **Blowout risk was backwards.** Under value-add is *highest* in the tightest
  games (+7.39% at |spread| < 3) and flat everywhere wider. The calibration's
  "days get cut short" story predicted the opposite, so **the game-script model
  that finding motivated should not be built** on this evidence.
- **Longshot bias was backwards.** The longest prices (+250 to +600) have the
  *highest* value-add.
- **Late-season was backwards.** Weeks 1-9 beat weeks 10-18.
- **Role stability was backwards.** Volatile roles +10.48%, stable roles −0.29%.

**No book is soft enough.** Gated on its own quote, the best is DraftKings at
**−2.02% over 16,794 bets** (interval [−6.43%, +2.38%]); five of ten are
negative with intervals excluding zero.

**A defect in the pre-registration, recorded so the next one is better:** three
of the twelve hypotheses were written with no predicted direction, so they
could not be falsified by direction and three slots were spent on cuts that
could only ever be exploratory. Also, the declared Bonferroni of twelve is too
generous — the search examined far more than twelve cells — and **nothing
cleared it even so.**

## The measurement that makes subgroup ROI readable

**Raw subgroup ROI is uninterpretable here.** The null baseline is **−12.4% on
overs and −2.6% on unders**, so "unders return −0.1%" reads as a finding and is
entirely a property of the price structure. What the model is worth in a
subgroup is its return **minus what betting that same cell blind returns**.

Pooled, that is **+4.28 points of value-add against a −3.22% return**: a
genuinely better-than-nothing model facing about 7.5 points of vig.

**The over-shading bias is real and too small to bet.** Blind unders across
exact-settlement markets return **−2.64% over 110,661 bets**.

**Correction, 2026-09-02.** This paragraph went on to say that the only markets
where blind unders are positive are `tackles_assists` (+9.26%) and `sacks`, and
that this *"confirms the settlement artefact from a third independent
direction"*. **The inference is dead** — there is no settlement artefact; see
the `tackles_assists` section above, where the settlement screen now reports a
−1% gap and the market agrees with its price.

**And neither number can be checked.** `−2.64% over 110,661` and `+9.26%`
appear in no committed report — `nfl_null_baseline.md` carries only
season/market/bets/ROI, with `tackles_assists` at **−5.00%** (4,575), **−14.05%**
(8,558) and **−9.86%** (6,938) across 2023-25, all negative. The per-side split
these sentences rest on was never written to a file. They are left here marked
rather than silently replaced with a number nothing generated, because
substituting an invented figure is the failure this correction is about. **A
per-side blind baseline needs regenerating by a script before any of it is
quoted again.**
## The measurement window is not the card's window

**Found 2026-08-31, nine days before Week 1, while auditing the sibling NHL
lab for the same defect.** Measured directly from the cache rather than from
the purchase constants, because the two disagree.

**Three snapshots were bought per event**, on 813 of 816:

| Snapshot | Lead | What labels it | Inactives known? |
|:---|---:|:---|:---|
| earliest | **T-360** | `label_snapshots` calls this **`card`** | no |
| middle | T-60 | called `mid`, **used by nothing** | yes |
| latest | T-6 | `close` | yes |

`label_snapshots` labels an event's **earliest** snapshot `card`. The purchase
code meant something else - `CARD_TIME_LEAD_MINUTES = 60` - so the snapshot the
purchase called card time is the one this lab labels `mid` and never reads.
**Every backtest that filtered `phase == "card"` used the six-hour-out price.**

**That corrects the first version of this section, which said every bought price
sat at T-60, inside the inactives window, knowing something the card never
would.** It did not. Inactives publish at T-90; the measurements sat at T-360
and are blind to them exactly as the card is. The lab's gate reasoning and its
measurements are consistent after all, which is the opposite of what was
recorded here for a day.

**What the real gap is, and which way it cuts.** The card runs at T-180 for a
13:00 ET kickoff; the measurements sat at T-360. Three hours earlier is a price
with *less* information in it, so the measured window is the **softer** of the
two - and every backtest lost at it anyway. A bias running toward the model, on
results that are uniformly negative, does not threaten them; it makes them more
robust. It would matter enormously if any result had been positive, and it is
recorded so a future one cannot quietly rest on it.

**What is genuinely wasted** is the T-60 purchase: a third of the snapshot
spend, bought deliberately, labelled `mid`, and read by nothing. Either the
label or the reader should change - and whichever changes, every number
measured before it changes has to be re-measured.

**And 2026 rows will not pool with 2023-25.** The forward ledger freezes at the
card's real window, which is neither T-360 nor T-60 and varies by kickoff slot.
The ledger records `commence_time` and `snapshot_date`, so the lead is
recoverable per row rather than assumed.

## What knowing the inactives is worth: almost nothing, measured

**0 of 17 markets.** `scripts/run_inactives_value.py`,
`data/outputs/nfl_inactives_value.md`.

The availability gate rests on a premise this lab argued about for weeks and
never measured: that a card running three hours out gives up something real by
not knowing who is playing. **The evidence was bought and then never read.** The
T-60 snapshot sits *inside* the ninety-minute inactives window, is a third of the
snapshot spend, and was labelled `mid` and consumed by nothing.

Comparing the pre-deadline price (T-360) with the post-deadline one (T-60) as
forecasts of the same settled outcome:

| Market | Wagers | Brier T-360 | Brier T-60 | Gain |
|:---|---:|---:|---:|---:|
| `pass_yards` | 5,275 | 0.22348 | 0.22263 | +0.00085 |
| `rush_yards` | 9,541 | 0.23559 | 0.23523 | +0.00036 |
| `reception_yards` | 22,318 | 0.22385 | 0.22366 | +0.00020 |
| `reception_longest` | 5,133 | 0.23885 | 0.23918 | **−0.00033** |

The largest gain is **+0.00085 against a 0.002 threshold declared in advance**,
and four markets are *worse* after the deadline. Mean price movement across five
hours is about **0.01 in probability**. **Crossing the inactives deadline buys
the market almost nothing.**

**The limitation is real and stated in the report: 82,810 wagers priced at T-360
had no price at T-60 and were dropped.** A scratched player loses his market
entirely, so the dropped rows are enriched in exactly the players the question
is about, and every figure is conditioned on the wager still existing an hour
out.

**But that limitation is also the answer.** The value of inactives is not in
repricing a wager — it is in knowing which wagers vanish, and those never
produce a staked bet at all. That is the same conclusion the availability-cost
report reached from the other side: every player listed Out or Doubtful voids
100% of the time, so the gate that matters is already automatic. Two
instruments, opposite directions, one answer.

**It is an upper bound, not a measurement.** Five hours of steam, weather and
late news move a line too, and nothing here separates them. A large gap could
have been any of those; a small gap is the informative result, because nothing
can be hiding inside it.

## The card's lead time, corrected: it was wrong in three ways and is now computed

**Correction, 2026-09-01.** This section previously carried a lead-time table
written by hand. **Three of its numbers were wrong**, and none of them were
caught by a test because no script generated them. The table is now
`data/outputs/nfl_carding_window.md`, computed by
`scripts/run_carding_window.py` from the workflow's own cron expressions and
the committed schedule cache, and pinned by `tests/test_carding_window.py`.
**Do not restate it in prose here.**

What the old table said, and what is true:

**1. It assumed ET is UTC−4 for all 272 games.** It said so — "ET is UTC−4 in
September" — and then applied that to a season running to 2027-01-10. ET is
UTC−5 from 2026-11-01. So "13:00 ET, 149 games, 3.0h lead" is really **54
games at 3.0h and 95 games at 4.0h**. Every row was wrong for its EST half.

**2. It read the last run before kickoff. That is not the run that cards the
game.** The backup triggers stand down when the first run publishes cleanly,
and the first run prices the whole league day at `--horizon-days 1`. So the
first firing owns the slate. The night window — documented at 3.25h and
3.33h — is really carded at **10.25–11.33h**. A reading that ignores the
standdown can only ever understate the lead, and it did so for 266 of 272
games.

**3. "Six games a season cannot be carded at all" is four.** The 09:30 ET
internationals straddle the DST boundary: the four October games kick at
13:30 UTC, before the 14:00 UTC cron; the two November games kick at **14:30
UTC**, after it.

### And two games a season are carded inside the inactives window

That is the consequence of the third error, and it contradicts two sentences
this file used to state flatly: *"all 272 games are carded blind to
inactives"* and *"the closest any run gets is three hours"*. Both are false
for `2026_09_CIN_ATL` (2026-11-08) and `2026_10_NE_DET` (2026-11-15), which
are carded **30 minutes** before kickoff — inactives drop at 90.

It is two games and it is not comfortable. The kickoff guard applies **no
grace period**, so whether those two enter the ledger at all depends on how
delayed the runner fleet is that morning. They are a different population
rather than a better-informed one, and the ledger records `commence_time` and
`snapshot_date`, so any future reading can exclude them on the lead rather
than on a note in a document. **Not engineered around**: an earlier November
cron would fix two games by carding forty others with less information.

## The card has three ways to fire, and none of them is assumed to work

**As of 2026-09-03.** Every layer below exists because the one above it was
measured not to be enough, and each is read rather than trusted.

| layer | mechanism | why it exists | how you know it fired |
|:--|:--|:--|:--|
| 1 | thirteen hourly `schedule:` triggers, 09:00–21:00 UTC | GitHub fires this repository's crons 115–443 min late (n=11) | `gh run list` shows `event: schedule` |
| 2 | **`NFL CARD DISPATCHER`** cloud routine, `trig_01HTMtmrT3Mx7BfupBvntZBm`, 13:00 UTC daily in season | with 13 triggers configured GitHub fired **three** on 2026-09-02, at the same times as with three configured — cron count may not be the lever; `workflow_dispatch` skips the cron queue | `gh run list` shows `event: workflow_dispatch`; the routine's final message names the run id |
| 3 | a human running `gh workflow run` | both above share one account rate limit and one GitHub scheduler | you did it |

**The dispatcher is a backstop, not a second card.** It passes
`respect_standdown=true`, which makes the workflow's own already-published
guard apply to a dispatch exactly as it does to a cron. On a day a cron got
there first, the dispatched run stands down in seconds and fetches nothing. A
human's dispatch leaves the flag at its default `false` and always runs, so
"run it anyway" still means that.

**13:00 UTC, and not 15:00.** Four hours before a 17:00 UTC (13:00 ET EDT)
kickoff, five before 18:00 UTC in EST, and clear of the BRIEF routine's 15:07
UTC slot — because a scheduled routine on this account can be **rejected
outright by the five-hour rate limit** (the BRIEF's 2026-09-02 fire was, in one
turn), and two routines in the same window compete for the same allowance.

**What was verified, and what was not.** Verified 2026-09-03 by a manual fire with a one-time calendar override, reverted immediately after: the routine provisioned, cloned the private repository, found that its environment has **no `gh` CLI**, and dispatched through the GitHub MCP tool `mcp__github__actions_run_trigger` with `respect_standdown=true`. Run 33727766819 was created **34 seconds** after the fire, both jobs succeeded, and the routine's final message named the run and sent no push. The prompt now names the MCP tool as the primary method and `gh` as the fallback, because the first run succeeded only by improvising — a stricter run would have reported a false failure. **Not verified:** a fire that lands inside the account's five-hour rate-limit window; the BRIEF's 2026-09-02 fire was rejected that way and left no run.

**A dispatch that never fires looks like a healthy day.** The routine pushes a
notification only when the dispatch itself fails; a fire the scheduler skipped
or the rate limit rejected leaves no run and no push. So the operating-home
post — one per card run, always — remains the only proof a day was carded.
Read it.

## GitHub fires none of this repository's crons on time, so the schedule is a net

**Measured 2026-09-02, and it supersedes the trigger design recorded below.**
The card's schedule had never fired when that section was written. It has now,
and so has everything else:

| workflow | cron | firings | delay, minutes |
|:---|:---|---:|:---|
| `Football Gameday Refresh` | 14:00 / 15:30 / 21:00 UTC | 5 | 115, 122, 123, 189, 199 |
| `Provider Quota` | 06:00 UTC | 5 | 304, 330, 343, 395, 443 |
| `Weekly Ledger Check` | 14:00 UTC Tue | 1 | 218 |

**11 scheduled firings, none on time, median 218 minutes.** The first run of the
day landed at 17:32 and 17:33 UTC on consecutive days.

**A cron time is therefore not a lead**, and every lead computed from one is a
best case rather than an expectation. This is the second time the carding table
rested on a premise nobody had checked; the first was assuming ET is UTC−4.

**A late trigger is not a later card.** 13:00 ET is 17:00 UTC. A 14:00 UTC
trigger three hours late arrives after kickoff, the guard quarantines the game,
and the ledger cannot be back-dated. On the old three-trigger schedule:

| delay | games carded | lost |
|---:|---:|---:|
| 0 min | 268 | 4 |
| 189 min | 212 | 60 |
| **304 min** | **117** | **155** — the whole 13:00 ET slate |
| 443 min | 76 | 196 |

**So the schedule is now thirteen hourly triggers from 09:00 to 21:00 UTC.**
Whichever GitHub actually runs first cards the day; the already-published guard
stands every later one down without fetching a price, so the redundancy costs
no credits. At the worst delay yet observed — 443 minutes — **266 of 272 games
are still carded**, against 76 on the old schedule.

**Two earlier problems dissolved as a side effect**, and both were recorded here
as facts about the lab:

- *"Six games a season cannot be carded at all"*, later corrected to four, is
  now **none**. The 09:30 ET internationals kick at 13:30 UTC, which is after
  09:00 UTC.
- *"Two games a season are carded inside the inactives window"* is now **none**.
  The 09:00 UTC trigger reaches them 5.5 hours out, so the season is one
  population again rather than 270 games plus two.

**What it costs, stated because it is a real cost.** A trigger that fires
promptly at 09:00 UTC cards a 13:00 ET game eight hours out rather than three.
That is a softer price with less information in it. The measured size of that
cost: crossing the inactives deadline is worth **+0.00085 Brier against a 0.002
threshold declared in advance**, and five hours of market movement is about
**0.01 in probability** (`nfl_inactives_value.md`). Losing 149 game-days of
frozen opinions is not recoverable at any price, so the trade is not close.

**Do not tidy the thirteen triggers into fewer.** The redundancy is the
mechanism, and `tests/test_carding_window.py` fails if the net stops surviving
the delays actually observed.

## The backup trigger could not back anything up, and now it can

**Found 2026-09-01 by the script above, and this one costs evidence rather
than accuracy.** The workflow's own comment cited GitHub's warning that
scheduled runs may be dropped — *"a single daily trigger is not a schedule, it
is a hope"* — and then set the backup seven hours after the primary.

Measured against the real schedule, a dropped or degraded 14:00 UTC run left,
of 272 games:

| | old (14:00 + 21:00 UTC) | now (+ 15:30 UTC) |
|:--|--:|--:|
| carded normally by the backup | **55** | **266** |
| carded inside the inactives window | 34 | **0** |
| not carded at all — kickoff already passed | **183** | 6 |

**Every 13:00 ET game was in the 183** — 149 games, 55% of the season. The
backup arrived after kickoff for two thirds of the slate, which is to say it
was not a backup.

A third cron at **15:30 UTC** now sits 90 minutes after the primary. It
changes **nothing** on a healthy day — the operative lead of all 272 games is
byte-identical, asserted by test — because the standdown guard reads the
published status and exits without fetching a price. The 21:00 UTC trigger
stays as a last resort for the night window only, and is documented as a
backstop rather than the "second pass for the Thursday and Monday night
windows" it was labelled and never was.

**A dropped Sunday run is not a delayed card. It is 16 games of frozen
opinions that cannot be back-dated**, and the forward ledger is the only
evidence this lab can still gather.

**The earlier note that "moving the cron earlier would make things worse"
still stands and is not what was done.** The *primary* cron did not move. What
moved is a backup that only ever runs when the primary already failed.

## The verdict

**No demonstrated edge anywhere, on the full available population.** 816
games, every NFL game for which historical props exist, two priced snapshots
each, 5.67M price rows, four independent instruments, and 0 of 18 markets
clearing the bars declared in advance.

The one market that replicates is the one the settlement screen flags, and
those are the same fact rather than two.

**This is the result.** Establishing that a model has no edge, on the complete
bought population, with the instruments that found three of its own defects,
is a finding. The machinery that produced it — and that produced three
retractions of its own headline findings in four days — is the product.

### What this does not settle

- **Three seasons is three seasons.** It is the full population for 2023-25,
  not a sample of it, but it is still three seasons.
- **The forward ledger is untouched by all of this.** It starts 2026-09-09 at
  272 games a season and it is the only evidence that can still grow.
- **The NHL lab reached the same answer by a different route**: its +1.4%
  over 4,830 bets became **−1.6% over 73,918** once it bought its full
  population, its one positive market failed replication, and its allowlist
  approval was **withdrawn**. It got there by buying more data; this lab got
  there by finding defects in its own harness. Two labs, two routes, one
  answer.
## CLV is a diagnostic, not a criterion

**Cooper's instruction, 2026-08-29: profit and ROI are the objective. Closing-
line value is not.** It never gates a decision here, it never leads a report,
and no market is refused for lacking it.

It stays in the repository because it earns its keep as a *diagnostic*: a high
return with no market movement was the first thing that pointed at the
`tackles_assists` settlement artefact, before the screen that proved it
existed. That is what it is for — raising a question, never answering one.

An earlier version of this file weighted it as though beating the close were
the goal. That was wrong. A model that makes money at a price you can get has
made money, whether or not the market ever agrees.

## Contract strings — never change these

Cooper's scheduled routines hard-code these. Renaming any of them silently
breaks his automation, and the breakage looks like the lab going quiet.

| Thing | Exact value |
|:------|:------------|
| Workflow name | `Football Gameday Refresh` |
| Workflow file | `.github/workflows/football-gameday-refresh.yml` |
| Card feed branch | `card-feed` |
| Operating home issue title | `Football Betting Lab — Claude Operating Home` |
| Changed-selections marker | `Selections changed` |
| Claims output | `data/outputs/nfl_what_we_can_claim.md` |
| Forward evidence output | `data/outputs/nfl_forward_evidence.md` |
| Odds API secret | `FOOTBALL_ODDS_API_KEY` |

The issue title uses an em dash (—), not a hyphen. The marker phrase is matched
literally. Every output file is league-prefixed, so NCAAF can never overwrite
an NFL record.

## Hard rules (never break these)

- **Never fabricate** odds, a line, an injury, a weather reading, or a
  player's status. A missing price stays missing.
- **Never place a bet** or automate one. Nothing here is ever wired to a
  sportsbook.
- **No market reaches the card without measurement against real prices and a
  reviewed human acceptance receipt.** Claude prepares the evidence and stops.
- **An excluded market is never a pass, an avoid, or a no-value call.** A
  blocked card yields no selections and says why.
- **State the sample size next to every measured number.** An interval that
  includes zero means **"no demonstrated edge"**, in those words.
- **Calibration can rule a model out, never in.** Where a priced test exists,
  it decides.
- **Never stake correlated selections as independent, and never sum their
  edges.** QB passing yards, WR receiving yards, team total and game total are
  one event seen four ways. Exposure is reported per game.
- **Report how much of any spread or total edge is a half-point at a key
  number.** Margins pile up on 3 and 7 and pushes are modelled exactly.
- **Before concluding a market "isn't offered", check per-bookmaker coverage
  including alternate lines** — and probe **in season**. A market unquoted in
  August establishes nothing.
- **Never print, write, compare, or commit an API key.** The production
  credential is the GitHub secret `FOOTBALL_ODDS_API_KEY`; `.env` is
  local-only and gitignored; `tests/test_no_secrets_committed.py` enforces it.
- **Never weaken a gate**, never sign a human acceptance receipt on Cooper's
  behalf, never merge with failing CI, never force-push. "Never merge with
  failing CI" is enforced, not asked: `main` is protected, `Tests` is the
  required status check, and `tests/test_workflows.py` pins that job — its
  name, its pytest invocation, its evidence chain — by parsing the workflow
  and executing its run blocks under stubs. A guard that greps for a spelling
  proves only that the spelling is absent.
- **No guard TEST is dropped from a run silently — the floor is per test, not
  per module.** This bullet used to say "the hard-rule guards cannot be
  dropped from a run", and the floors underneath it were per MODULE. Measured
  2026-09-04:
  `--deselect tests/test_no_secrets_committed.py::test_env_file_is_never_tracked`
  — from `pyproject.toml` addopts, from `PYTEST_ADDOPTS`, or from a `-c`
  config file — produced `1 deselected`, a pass count one below the control,
  pytest exit 0 and `scripts/check_test_results.py` exit 0, with a guard test
  gone and every layer green. "Silently" is the load-bearing word: a guard
  test deleted WITH its floor lowered in the same commit is a line in the diff
  that says so, which is what `GUARD_TEST_FLOORS` converts the silent removal
  into rather than preventing. Now: `conftest.py` exits the session when a
  required guard module collected nothing AND when pytest received a `--deselect`, `-k`,
  `-m`, `--ignore`, an ini `addopts` or a `PYTEST_ADDOPTS` — read off
  `config`, so the route it arrived by does not matter;
  `scripts/check_test_results.py` floors each required module's recorded
  testcases against the `test_*` functions `ast` finds in the file, and
  refuses evidence older than six hours — floored against the checkout, so no
  count is written down IN THAT SCRIPT; `tests/test_the_guards_exist.py`
  holds the per-module counts in `GUARD_TEST_FLOORS` — that IS where they are
  written down, and the same file re-derives them from `ast` so the table
  cannot drift from the checkout — and asserts each guard is tracked, still
  defines tests, and that no tracked
  `pytest.py`, `coverage.py`, `sitecustomize.py` or `usercustomize.py` can
  shadow the suite. The three hold one list. There is no skip allowlist and
  there will not be one. What is still NOT covered: a `--noconftest` run,
  which is explicit and banned from CI, and a guard whose tests are all
  present and all vacuous.
- **The experiment ledger is append-only, and that is checked at the diff.**
  `scripts/check_ledger_append_only.py`, run by `Ledger Guard` on every pull
  request, refuses a removed key, a count drop, a rewritten outcome or a
  same-key contradiction; `save()` takes an explicit floor. **Correction,
  2026-09-04:** five places in this repository said the old pre-floor `save()`
  "could never fire" because it "compared the ledger with itself". Measured by
  restoring it from `ac6d9b2` and running it: it RAISES on an in-process
  shrink (53 entries in the file, 35 in memory → `would fall from 53 entries
  to 35`). What it could not see is a ledger shrunk on disk and committed
  first — then the floor it re-reads is already 35, and the recorder exits 0
  printing `35 distinct hypotheses (+0)` with the render moving x1.69 → x1.63.
  That is the half the diff-level guard exists for. (The narrower claim is the
  one that was run, and it is the one `experiment_ledger.py` carries: nothing
  self-healed in that run — the recorder appended what it was asked for, which
  was nothing. "The recorder self-heals nothing" as an absolute was never
  tested here and is not asserted.)

  Measured 2026-09-05 on this branch: shrinking the file to 20 entries and
  re-running the recorder RAISES — `would fall from 53 entries to 20` — because
  the floor is `max(len(loaded), committed_entry_count(path))` and the second
  term shells out to `git show HEAD:<path>`, an observation the working file
  cannot influence.
- **Never spend API credits beyond a small measurement budget without asking.**
- **Never pool leagues into one number.** Fitted per league, reported per
  league, recorded per league, receipted per league.

## What Claude decides, and what Cooper decides

Claude works autonomously on: data, models, measurement, reports, tests,
workflows, docs, and opening PRs with green CI.

Claude stops and asks for exactly two things: **allowlisting a provider or a
market**, and **credit spend beyond a small measurement budget**.

## Main commands

```bash
# One-time local setup
/opt/homebrew/opt/python@3.12/bin/python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt && .venv/bin/python -m pip install -e .

# Cost arithmetic (spends nothing, touches no network)
PYTHONPATH=src .venv/bin/python scripts/estimate_credit_cost.py

# Tests
PYTHONPATH=src .venv/bin/python -m pytest -q
PYTHONPATH=src .venv/bin/python -m compileall -q src scripts
```
