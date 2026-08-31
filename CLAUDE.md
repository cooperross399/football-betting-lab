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
  inventing a game; a test pins it.
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
  gamebook revisions, not a join fault. Bounded by a test at 1%, recorded, and
  deliberately not reconciled: both sources describe the same play correctly.
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
- **Recency weighting: measured, does not ship.** Half-life 8 games returned
  −5.2% against the baseline's −6.6%. The **paired** difference over the 172
  games both arms bet is **+1.4% per bet, interval −1.0% to +3.9% — not
  distinguishable from zero.** The first decision rule was `roi_variant >
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
| Null baseline | Betting everything returns **−9.47% over 366,725 bets**. The harness is sound. |
| Backtest | 2023 **−1.6%** (18,062), 2024 **−2.1%** (29,394), 2025 **−5.2%** (31,317). |
| Replication | **Nothing replicates** on a season it was not selected on, except `tackles_assists`. |
| Settlement screen | `tackles_assists` is the **only** suspect, and it is the thing that replicates. |
| Price sensitivity | **No market is profitable at the consensus price** except `tackles_assists`. |
| Allowlist bundle | **0 of 18 markets clear every bar.** |

Every one of the eighteen markets returns **no demonstrated edge** on its
held-out seasons — that is the phrase and it is meant literally: the
family-corrected interval includes zero in every case. The best held-out
numbers are `rush_yards` **+1.6% over 7,502 bets** and `pass_yards` **+1.1%
over 4,502**, both with intervals spanning zero several times over.

## `tackles_assists` is still a settlement artefact, and now it is the only thing left

It is the one market that replicates — **+12.4% / +11.2% / +12.6%** across
2023, 2024 and 2025, **+11.7% over 3,109 held-out bets** — and the one market
the settlement screen flags. Those are the same fact.

The screen is one number: the featured market is priced at **50% over** across
6,575 featured wagers and the outcome lands over **42%** of the time. That
seven-point gap is worth **15%** to a model that consistently takes the under,
and this model bets 86% unders. The measured return is **+11.7%**. nflverse
records about half a tackle per player-game fewer than whatever the books
settle on; at a +0.5 offset the entire edge vanishes and both sides return the
vig.

**A settlement offset is constant, so it replicates by construction.** It
survived split-half, fragility, a Bonferroni correction across twenty markets,
and it is positive at **8 of 8** books at the consensus price — because every
book settles on the number this lab cannot see. Replication is not evidence
against it. Replication is what it does.

`tackles_assists` cannot be measured at all until an independent settlement
source exists. It joins goalie saves in the NHL lab: modelled, priced, and
structurally unmeasurable.

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

| Test | Result now |
|:---|:---|
| Three seasons | −0.4%, +2.8%, −0.5% |
| Held-out pooled | **+1.6% over 7,502 bets** — interval includes zero, **no demonstrated edge** |
| Settlement screen | 2-point gap, agrees with the price |
| **Consensus price** | **−1.0%** |
| **Best of N books** | +0.9% |
| **By book** | positive at **2 of 10** |

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
| 0.60-0.65 | 14,417 | 0.485 | 0.510 | **−0.139** | −0.024 |
| 0.70-0.80 | 11,487 | 0.507 | 0.523 | **−0.235** | −0.017 |
| 0.80-1.00 | 4,700 | 0.547 | 0.523 | **−0.314** | +0.024 |

**Brier over 74,345 bets: model 0.26057, market 0.22703.** Walk-forward
isotonic calibration — the map fitted on prior seasons only — closes most of
that gap and never crosses it:

| Season | Model | **Calibrated** | Market | Beats the price? |
|:---|---:|---:|---:|:---|
| 2024 | 0.26153 | **0.23104** | 0.22756 | no |
| 2025 | 0.25710 | **0.22524** | 0.22329 | no |

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
exact-settlement markets return **−2.64% over 110,661 bets**. The only markets
where blind unders are positive are `tackles_assists` (+9.26%) and `sacks` —
both **charted**, which is the settlement-artefact family, and which confirms
that artefact from a third independent direction.
## The measurement window is not the card's window

**Found 2026-08-31, nine days before Week 1, while auditing the sibling NHL
lab for the same defect.**

Every bought price is at **T−60 minutes** (`CARD_TIME_LEAD_MINUTES = 60`).
The card runs at **14:00 UTC = 10:00 ET**, which for a 13:00 ET kickoff is
**T−180 minutes**; the 21:00 UTC backup is *after* the early slate starts and
those games are quarantined by the kickoff guard.

That two-hour gap straddles the one deadline this lab cares most about.
**NFL inactives are declared ninety minutes before kickoff:**

| | inactives public? |
|:--|:--|
| T−60 min — where every number here was measured | **yes** |
| T−180 min — where the card actually runs | **no** |

**The measurement sits inside the inactives window; the card sits outside
it.** Every figure above therefore describes a world in which you already
know who is playing, and the card does not live in that world.

This lab gates player props precisely because inactives are unknowable at
card time — and then measured those props at an hour when they were knowable.
Both statements cannot be load-bearing at once.

**What follows, and what does not.** It does not rescue anything: the
compound-versus-count split died of a cross-season settlement defect and
`tackles_assists` of a settlement offset, neither of which is a timing
question. What it does mean is that **any future positive result at T−60
must be re-measured at the card's real window before it means anything.**

And it sharpens the availability question rather than answering it. The NHL
lab is currently buying its own second window to ask whether its card simply
runs at the wrong hour. For football the honest answer may be that **no hour
works** — ninety minutes is inside every plausible card time, so the
availability gate would be permanent rather than provisional. Worth settling
deliberately rather than inheriting.

## The card's lead time is not one number, and no game is ever carded inside the inactives window

Computed from the real 2026 schedule, 272 games, against the two crons
(14:00 and 21:00 UTC). ET is UTC−4 in September; the lead is the run closest
to kickoff that still precedes it.

| kickoff ET | games | best lead | inactives known? |
|:--|--:|--:|:--|
| 13:00 | 149 | 3.0h | no |
| 16:25 | 37 | 6.4h | no |
| 20:15 | 33 | 3.2h | no |
| 16:05 | 21 | 6.1h | no |
| 20:20 | 20 | 3.3h | no |
| **09:30** (international) | **6** | **none — 14:00 UTC is 30 min AFTER kickoff** | no |

**All 272 games are carded blind to inactives**, which drop ninety minutes
out. The closest any run gets is three hours. So the T−60 measurement knows
something the card will never know, on **every game of the season** — not
some of them.

That is the sharper form of "the measurement window is not the card's
window". It is not a two-hour discrepancy to be tuned away; there is no cron
that fixes it, because the card must price a whole slate at once and the
slate's kickoffs span eleven hours.

### Six games a season cannot be carded at all

The 09:30 ET international games kick at 13:30 UTC and the first cron is
14:00 UTC — **thirty minutes late**. The card prices them and the kickoff
guard then quarantines them, which is the correct behaviour and produces no
wrong answer. It is a coverage gap, not a fault: 6 of 272 games, 2%.

**Moving the cron earlier would make things worse, not better.** A 12:00 UTC
run would card the whole day, and the already-published guard would then
stand the 14:00 run down — buying six international games at the cost of
carding 149 one-o'clock games two hours earlier, with less information. The
real fix is per-game carding rather than per-day, which is a design change
and not a scheduling one. Recorded rather than done.

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
  behalf, never merge with failing CI, never force-push.
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
