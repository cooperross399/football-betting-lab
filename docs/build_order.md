# The build order, against a Week 1 that is twelve days away

## The date that sets everything

**Week 1 opens Wednesday 2026-09-09** (NE @ SEA, 20:20 ET). Verified against
the nflverse schedule rather than assumed — the brief's expectation of "the
Thursday after Labor Day" describes the season's *second* game, SF @ LA on
2026-09-10. Today is 2026-08-28, so there are **twelve days**.

## What is realistic, said plainly

**A measured, allowlisted, betting-ready model by Week 1 is not realistic, and
this document will not pretend otherwise.** Nothing here has been measured.
Nothing can be allowlisted, because allowlisting requires measurement against
real prices and a signed receipt, and neither exists.

What is realistic, and matters far more:

> Historical prices can be bought later. **Forward evidence cannot be
> back-dated.** Every week the pipeline is not freezing opinions and settling
> them is a week of clean out-of-sample data that is gone permanently.

That asymmetry is sharper here than it was in hockey, because the credit
arithmetic says the historical purchase is not affordable at all
(`docs/credit_cost.md`). Forward evidence is not the cheap option. It is very
close to the only option.

## Phase 0 — before 2026-09-09: the evidence organ, running

Everything in this phase exists to make the first kickoff count. A crude model
that freezes an opinion and settles it honestly is worth more than a good model
that starts in October.

1. **Data layer.** nflverse release assets fetched and cached: schedules,
   play-by-play, player and team stats, rosters, weekly rosters, depth charts,
   snap counts, injuries. A completed game is never refetched. Staleness is
   checked before reuse, four ways, as in the NHL lab.
2. **`selection_key()` and the league-date rule, first, in one place.** The NHL
   lab's join-vocabulary bug family reached five members and cost weeks. One
   function builds every key on both sides, and the fixtures use it too.
3. **Odds staging.** The provider adapter writes to `data/staging/`, which the
   card cannot read. Fail-closed policy allowlisting nothing, PR gate,
   eligibility per market.
4. **The gates, all of them, before the first card**: start-time guard,
   preseason screen against the known regular-season schedule, availability
   gate, quarterback-change quarantine, roof/weather exclusion, roster
   staleness. Every one fails closed.
5. **The forward-evidence organ.** Snapshot before kickoff, settle after,
   day-as-unit, never repriced, voids return the stake, a game with no result
   inside the patience window is unsettleable and counted.
6. **A first model, deliberately crude**, and honest about it: a team model
   from scores and rest, and prop models from per-game rates with the right
   distributional shapes (compound for yardage, counts for receptions,
   extreme-value for longest-anything). It exists to produce an opinion worth
   freezing, not to be believed.
7. **The card, saying what it is.** No selections. It states in those words
   that it is accumulating evidence rather than making recommendations, and it
   prints the accounting identity every run:
   `priced = no_opinion + below_threshold + unparseable + ambiguous + bets`.
8. **Delivery.** `Football Gameday Refresh` publishes each card to the
   `card-feed` branch; the cloud routine reads that branch and pushes it
   in-app. No email, no laptop.

**Phase 0 must be running on 2026-09-09.** If something in it is not ready,
the thing that ships is the snapshot-and-settle loop with a cruder model
still, never a slipped start.

## Phase 1 — from Week 1: accumulate, and do not touch it

Freeze, settle, count. Weekly. The ledger is the product of this phase and
nothing else is.

The card continues to make no recommendations. `data/outputs/nfl_forward_
evidence.md` reports what the ledger supports, with sample sizes, with
intervals clustered by game because the selections inside one game are not
independent, and with "no demonstrated edge" in those words while it is true.

## Phase 2 — September into October: models, and the one priced test that is free

1. **Walk-forward fits.** A game is priced only from games strictly earlier
   than it. In a sixteen-game week the temptation to use the rest of the week
   is large and the answer is no.
2. **Distributional validation.** Every fitted shape shown against the
   empirical distribution it claims to describe. A shape that has not been
   shown is an assertion.
3. **The free closing-line backtest.** The nflverse schedule file carries a
   closing spread, total and both moneylines for every game back to 1999,
   complete for 2024 and 2025. This is a real priced test for the team model,
   costing nothing, and it decides the team model the way the bought backtest
   decides in the NHL lab. Its limits — one consensus line, no ladder, no
   props, no book — are stated everywhere it is used.
4. **Key-number accounting.** Pushes modelled exactly; every spread or total
   edge reported alongside how much of it is a half-point at 3 or 7.
5. **Schedule states, tested the NHL way.** Short weeks, byes, international
   travel. Shipped only if they win the priced test, refused if they only
   improve calibration.

## Phase 3 — measurement discipline

Family-wise correction across every market tested, reported beside the raw
figure. Minimum sample thresholds declared in advance. Replication on held-out
seasons. CLV tracked per frozen opinion and reported per market beside ROI,
with a winning record on negative CLV called variance in those words.

## Phase 4 — evidence assembled, and then stop

The allowlist evidence bundle, per market, per league, with its honest default
of **not supported**. Claude prepares all of it and stops. Cooper signs or does
not.

## What I need from you, and when

**Now — free, and it changes the plan most:**

1. **Does the Odds API quota reset, and how often?** Everything in
   `docs/credit_cost.md` treats 100,000 as a single annual pool, because that
   is how the NHL lab's operating file treats it. If it is **monthly**, then
   the NFL, the NHL and NCAAF all fit easily and the historical purchase
   becomes affordable — and the "no bought backtest" conclusion that shapes
   this whole build order is wrong. It is free to check: the
   `x-requests-remaining` header on the free `/v4/sports` endpoint, or your
   plan page.

**Before 2026-09-03, so there is time to shadow-run before Week 1:**

2. **`FOOTBALL_ODDS_API_KEY` as a GitHub secret** on the new repository. Same
   account and same pool as the NHL lab. Never in a file.

**Around Week 1, and this is a credit-spend decision:**

3. **Authorisation for an in-season market probe** — a few hundred credits, to
   find out which of the 111 documented markets books actually quote for an
   NFL game, per bookmaker, including the alternate ladders. Probing in August
   establishes nothing. I will bring the exact number before spending it.

**Whenever you want to answer it, and not before question 1:**

4. **Whether to buy any historical prices at all**, and if so which markets.
   At the current understanding of the quota the answer is probably no, and
   the team model gets its priced test free from the schedule file regardless.

Nothing is bet in the meantime. Nothing is allowlisted. The card says it is
accumulating evidence, because that is what it is doing.
