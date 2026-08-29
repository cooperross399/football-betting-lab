# CLAUDE.md — Football Betting Lab Operating Instructions

This repository is the source of truth for the Football Betting Lab. Claude
operates it directly. Where anything else in the repo conflicts with this file,
this file wins.

**Active repo path: `/Users/cooperross/Projects/football-betting-lab`.**

**Scope: the NFL ships first. NCAAF is added later, and the architecture is
built for it from day one.** League is a first-class dimension everywhere, so
adding college football is a new registry entry, a new adapter and a new set of
fitted models — never a refactor. Do not build NCAAF now.

**NCAAF player props are out of scope** (Cooper, 2026-08-28: not essential).
College football is a team-markets league unless he says otherwise. That takes
the transfer portal, opt-outs and a per-player college data join off the
critical path entirely, and cuts a college Saturday's credit cost by roughly
four fifths.

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

**As of 2026-08-28. Nothing has been measured. There is no model, no fitted
parameter, no backtest, and no evidence of any kind about whether this works.**
The only numbers in this repository are counts of games, markets and credits.
Anything that sounds like a finding before Week 1 is a bug.

- **Week 1 opens Wednesday 2026-09-09**, NE @ SEA, 20:20 ET — **not** the
  Thursday after Labor Day, which is the season's second game (SF @ LA,
  2026-09-10). Verified against the nflverse schedule, as the brief instructed,
  rather than assumed. That is **12 days from today**.
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

- **The historical purchase is under way and 67% of the 2025 card-time
  snapshot is bought.** 183 of 272 events, **69,964 credits** against a 70,000
  cap, zero failures, stopped cleanly at the cap. **9,874 credits remain this
  month**; the rest waits for the reset, which the free daily quota check will
  observe rather than assume.
- **A partial purchase is a sample, not a prefix.** Events are bought in an
  order whose every prefix is spread across the season, so the 67% covers
  every week at 62-73%. The first ordering left the kickoff *windows* uneven
  (Sunday night 50%, Monday 76%), which matters because book coverage differs
  by window; the order is now stratified by window, measured against three
  alternatives, and the residual week imbalance is structural — 21 Thursday
  games across 18 weeks cannot be two-thirds sampled evenly.
- **Still to buy**: the remaining 89 card-time events (~34,000) and the full
  close snapshot (~99,000). Roughly 133,000, or 1.3 months.

- **The prop models lose against real prices, and the sample says so.**
  767,947 bought rows over 183 events, collapsed to 188,045 distinct wagers
  (one player, market, line and side is **one bet** quoted by up to nine
  books; a card takes the best price). Under the shipped bars: **pooled −6.7%
  over 24,470 bets, family-corrected interval −12.4% to −1.1% — the interval
  excludes zero and it is negative.** `data/outputs/nfl_props_backtest.md`.
  This measures the model, not a shippable policy: no player prop can reach a
  card at all.
- **Two markets have intervals excluding zero after correction**, and they
  point opposite ways: `sacks` **−14.2% over 2,164 bets** (confirmed bad) and
  `tackles_assists` **+16.2% over 941 bets**.
- **`tackles_assists` is a candidate, not a finding, and must be read as
  one.** It survives every free check: halves agree (+17.8% early, +14.5%
  late), 223 distinct players, the best single game is 7% of the profit and
  removing it leaves +15.1%. Settlement was checked against the books and
  agrees — at the featured line the Over hits 47.7%, so nflverse's defensive
  charting is not drifting from what the books settle. **None of that makes it
  a finding.** It is one season, 67% sampled, one of eighteen markets tested.
  The standard is replication on a season it was not selected on, and that
  needs a second season bought — roughly 99,000 credits, Cooper's decision.
- **Do not act on `tackles_assists`, and do not quietly drop it either.** It
  is the strongest candidate this lab has produced and it is the reason to
  prioritise a second season in the next purchase.
- **The count-model markets were calibrated after the backtest, not before**,
  because the props calibration only ever covered the three compound families.
  They are roughly centred (mean PIT 0.51-0.54 across tackles, sacks,
  interceptions, field goals, kicking points, passing touchdowns). That ruled
  out the first explanation offered for the tackles result and is why the
  second one had to be found.

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
- **The first-half model exists and does not ship either.** Pooled **−16.5%
  over 619 bets**, interval −29.5% to −3.5%. It is the crudest thing that
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

## What three seasons of bought prices say

**The purchase completed: 587,732 credits, 5.67M price rows, 816 events across
2023-2025, both snapshots on 815 of them, 4,473,866 credits left.**

- **The harness was validated before any result was believed.** Betting every
  priced selection with no model at all returns **−9.28% over 385,495 bets**
  (`scripts/run_null_baseline.py`). A sound harness returns roughly the vig
  here; if betting everything made money, nothing computed on top of it would
  mean anything.
- **The null baseline is not flat across seasons**: 2023 −5.2%, 2024 −8.3%,
  2025 −12.8%. The price samples differ in how soft they are, so **raw ROIs
  compared across seasons are comparing two different questions.** The pooled
  model results inherit that gradient almost exactly (+9.6%, +4.2%, −0.0%),
  which is why the pooled number is not the interesting one.
- **Two markets replicate positive on seasons they were not selected on.**
  `tackles_assists` **+16.1% / +14.9% / +18.2%** and `rush_yards` **+14.8% /
  +10.7% / +12.2%**, across 2023, 2024 and 2025. Held-out pooled, Bonferroni
  across 20 markets: tackles **+15.5% over 4,849 bets**, rush yards **+12.5%
  over 12,874**. `receptions` is positive in all three but decaying
  (+12.6/+7.6/+5.0).
- **This is the first thing in this lab that has cleared the bar the brief
  sets**, and four wrong explanations were tested and discarded before it was
  believed: settlement drift (Over hits ~50% at the featured line in every
  season), a single soft book (DraftKings shows +16.5% in 2023 and −3.6% in
  2025, and DraftKings does not misprice by 16%), best-of-N price selection
  (measured at 0.5 probability points among selected bets and **flat** across
  seasons, so it cannot explain a gradient), and a broken harness (the null
  test).
- **It is still not an edge that can be acted on.** No player prop can reach a
  card — inactives are declared ninety minutes before kickoff and no available
  feed publishes them. The model is also badly calibrated (overconfident in
  every price bucket: it says 0.73 and gets 0.59, says 0.37 and gets 0.17),
  so *why* it wins is not understood, and a miscalibrated model that wins is a
  reason for more scrutiny rather than less.
- **Nothing is allowlisted and nothing is bet.** The next step is the six-step
  approval in `docs/provider_allowlist_approval.md`, and step six is Cooper's.

## The tackles finding is dead, and how it died

**`tackles_assists` is a settlement artefact, not an edge.** The screen is one
number: the featured market is priced at **50% over** and the outcome lands
over **42%** of the time. That eight-point gap is worth **16%** to a model
that consistently takes the under — and the measured "edge" was **+16.3%**.
Those are the same number.

nflverse records about half a tackle per player-game fewer than whatever the
books settle on. At a +0.5 offset the entire edge vanishes and both sides
return the vig.

**This is the defect a backtest cannot catch by checking itself.** A
settlement offset is *constant*, so it replicated perfectly across three
seasons, survived split-half, survived fragility, survived a Bonferroni
correction across twenty markets, and had **no closing-line value** — which
was the only signal that ever pointed at it, and which I read as inconclusive
because I had bought too narrow a window.

`scripts/run_settlement_agreement.py` now runs this screen before any result
is believed. It compares the realised over rate to the **devigged price**, not
to a half — the naive version flagged `anytime_td`, where 13% is exactly
right, and the yardage markets on an absolute gap of 2.5 yards against a
37-yard line.

- **Sixteen of seventeen markets agree with their price** within three points.
  `sacks` agrees too (33% priced, 31% realised), so the sacks result is the
  model being on the wrong side, not a settlement fault.
- **Passing the screen is not a clean bill of health.** `rush_yards` has a
  three-point gap, inside tolerance, worth **5%** to a one-sided model against
  a measured **+12.4%**. So roughly 5 of its 12.4 points are settlement and
  **7 are unexplained** — it is now the only survivor, and a weaker one.
- **`tackles_assists` cannot be measured at all** until an independent
  settlement source exists. It joins goalie saves in the NHL lab: modelled,
  priced, and structurally unmeasurable.

**What made this findable:** the model bets 86% unders in tackles, and a
one-sided model plus a settlement offset is indistinguishable from an edge on
every test that only looks at returns. The question that broke it was not
"is this result robust" — it was **"what would betting one side with no model
at all return?"** For tackles, that is +10.2%.

## The verdict, on three seasons of bought prices at two snapshots

**No demonstrated edge anywhere.** Every instrument now agrees, and each was
built to catch a different failure.

| Instrument | What it says |
|:---|:---|
| Null baseline | Betting everything returns **−9.28%** over 385,495 bets. The harness is sound. |
| Settlement screen | `tackles_assists` is priced 50% over and lands 42%. That gap is worth **16%** to a one-sided model; the "edge" was **+16.3%**. |
| Closing-line value | Over a **six-hour** window, 70% of prices moved and **51% moved toward the bet**. Pooled mean CLV **+0.06 probability points**. |
| Replication | Replicates — and a constant settlement offset replicates by construction, so this proves nothing on its own. |

- **CLV is now a real test, not an inconclusive one.** The first window was 55
  minutes, which was a purchasing mistake; at six hours, 70% of prices move
  and the model's selections split **51/49**. `rush_yards` moves toward the
  bet **48%** of the time against a measured +13.0% return. **The market has
  no idea the model exists.**
- **`rush_yards` is the last thing standing and it does not stand.** A
  two-to-three point settlement gap is worth 4-5% of its 13%, and the residual
  has no market confirmation at all. A return with zero CLV and a partial
  settlement explanation is a residual, not an edge.
- **Nothing here is a failure of the lab.** Establishing that a model has no
  edge, on 8.4 million bought price rows across three seasons at two
  snapshots, with four independent instruments agreeing, **is the result.**
  The machinery that produced it is the product.

## `rush_yards` stands up, and an earlier reading of it was wrong

**Correction.** This file previously said roughly 5 of `rush_yards`' 13 points
were a settlement gap. That was wrong. The "worth to a one-sided model"
figure assumes a model that always takes one side; `rush_yards` bets **54%
unders**, which is nearly balanced, so a 2-point settlement gap contributes
**0.3%**, not 5%. The same arithmetic confirms `tackles_assists`: 85% unders
against a 7-point gap is worth **9.9%**, and its consensus return is **9.0%**.

**What `rush_yards` actually has**, after every instrument built to break it:

| Test | Result |
|:---|:---|
| Three seasons | +19.1%, +10.1%, +10.9% — positive in all three |
| Held-out pooled | **+14.0% over 11,269 bets**, Bonferroni across 20 markets |
| Null baseline | Harness returns −9.28% betting everything |
| Settlement screen | 2-point gap, worth **0.3%** at this model's side split |
| **Consensus price** | **+8.3%** — it is not a shopping premium |
| **By book** | positive at **10 of 11** |
| Closing-line value | **zero** — 48% of moving prices moved toward it |

Four of five instruments support it. Only CLV does not, and CLV measures
whether the market *corrects*, which a persistent structural bias need not.

**Beating the close was never the objective and this file over-weighted it.**
A +8.3% return at the median price across 16,829 bets and three seasons, at
ten of eleven books, is direct evidence of the thing that actually matters.
Zero CLV is a reason to keep asking why, not a refutation.

**What still blocks it from being a bet:** no market is allowlisted, and no
player prop can reach a card at all without an inactives feed. Those are the
binding constraints, not the evidence.

## The availability gate was solving a problem that does not exist

**A did-not-play prop is voided by the book, not lost.** The stake comes back.
So "will he play?" is not a question about whether the bet wins — it is a
question about whether there is a bet at all, and a bet that never existed
costs nothing.

Measured over three bought seasons on `rush_yards`:

| Designation that week | Bets | Voids | Void share | ROI |
|:---|---:|---:|---:|---:|
| **not on the injury report** | **15,620** | 2,167 | 12.2% | **+13.7%** |
| listed, no designation | 998 | 16 | 1.6% | +2.4% |
| Questionable | 211 | 36 | 14.6% | +11.8% |
| Doubtful | 0 | 13 | **100%** | — |
| Out | 0 | 116 | **100%** | — |

Every player listed **Out or Doubtful voided 100% of the time**, so they never
produce a staked bet at all — the gate that matters is already automatic. And
the return lives entirely in the **undesignated** population, which is also
the one whose availability is least in doubt. The gate and the edge want the
same thing.

**nflverse does carry inactives** — in `weekly_rosters.status` as `INA`, not
as a separate feed. It publishes at 07:00 UTC, so it is not live before a
Sunday kickoff, but it is what made this measurable.

### The one line that decides all of it

**Everything above assumes a book voids a did-not-play prop rather than
grading it a loss.** If it grades them as losses, the same record is
**−0.8%** instead of **+13.0%**.

That is the difference between a strategy and a disaster, it turns on one line
in a book's prop rules, and no amount of modelling can settle it. So the
policy sits behind the verdicts door as
`props_selectable_when_undesignated`, **not in force**, waiting on a human
who has read them. `scripts/run_availability_cost.py` recomputes both numbers.

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
