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

That asymmetry holds whatever the budget is. It is worth saying plainly that
it held for the wrong reason for a few hours on 2026-08-28: the first version
of this document argued that the historical purchase was unaffordable, which
was an artefact of reading the quota as an annual pool rather than a monthly
one. It is affordable — 1.25 months for a full season (`docs/credit_cost.md`).

The order does not change. Bought history will still be there in November.
The opinion the card would have held on 2026-09-09 will not.

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

## Phase 2 — September into October: models, and the priced tests

1. **Walk-forward fits.** A game is priced only from games strictly earlier
   than it. In a sixteen-game week the temptation to use the rest of the week
   is large and the answer is no.
2. **Distributional validation.** Every fitted shape shown against the
   empirical distribution it claims to describe. A shape that has not been
   shown is an assertion.
3. **The free closing-line backtest, first.** The nflverse schedule file
   carries a closing spread, total and both moneylines for every game back to
   1999, complete for 2024 and 2025. This is a real priced test for the team
   model, costing nothing, going back twenty-seven seasons — deeper than any
   purchase at any price — and it decides the team model the way the bought
   backtest decides in the NHL lab. Its limits are stated everywhere it is
   used: one consensus line, no ladder, no props, no book.
4. **The retention probe, then the prop backtest.** Roughly 20 past events
   across 2024 and 2025, tier-1 markets, one snapshot each — about 9,200
   credits — to establish per market and per book whether any historical price
   exists at all. The NHL lab found `player_hits` retained by nobody across
   256 probed events, and the regulation three-way likewise; spending 125,120
   credits to learn that about football would be an expensive way to find out
   something a probe answers for a fraction of it. Then the purchase, sized
   from what the probe finds and re-costed before it is spent.

   Both are credit spends and therefore Cooper's.
5. **Key-number accounting.** Pushes modelled exactly; every spread or total
   edge reported alongside how much of it is a half-point at 3 or 7.
6. **Schedule states, tested the NHL way.** Short weeks, byes, international
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

**Answered on 2026-08-28:**

1. ~~Does the quota reset?~~ **Monthly.** This reversed the central conclusion
   of the first draft: credits are not a constraint, buying history is
   affordable, and NCAAF fits too. Every document carrying the old conclusion
   has been corrected, and the reversal is recorded rather than deleted.
2. ~~`FOOTBALL_ODDS_API_KEY` as a GitHub secret.~~ Set — **but not where the
   workflow will look for it.** `cooperross399/football-betting-lab` reports
   zero Actions secrets, while `nhl-betting-lab` shows its `NHL_ODDS_API_KEY`
   as expected, so the read is working and the football repo genuinely has
   none. Worth a check at **Settings → Secrets and variables → Actions** on
   the football repo, named exactly `FOOTBALL_ODDS_API_KEY`. Nothing is
   blocked until the first live fetch, around 2026-09-03.

**Still open, and now a real choice rather than a constraint:**

3. ~~The retention probe.~~ **Run 2026-08-28 on your instruction. 7,280
   credits, 79,659 remaining this month.** All 27 tier-1 markets have
   historical prices; 25 have enough to measure against, across nine books.
   `data/outputs/nfl_retention_probe.md`.

4. **What history to buy, once the probe answers.** The shapes and their
   costs, all against 100,000 a month:

   | Purchase | Credits | Months |
   |:---------|--------:|-------:|
   | Twelve core props, one season, one snapshot | 32,640 | 0.33 |
   | Tier 1, one season, one snapshot | 125,120 | 1.25 |
   | **Tier 1, one season, two snapshots (card-time and close)** | **250,240** | **2.5** |
   | Tier 1, two seasons, one snapshot | 250,240 | 2.5 |

   The probe revises those figures downward: billing is per market
   **returned**, and it observed 21% fewer than the pessimistic bound, so a
   full tier-1 season at one snapshot should land nearer **99,000** than
   125,120, and the two-snapshot version nearer **198,000** than 250,240.

   My recommendation is still the two-snapshot version. A single snapshot gives one
   price and no closing-line value; two — one at roughly the hour the card
   would have been built, one within minutes of kickoff — give the model's
   price, the closing price, and therefore **CLV on every historical bet**.
   The brief makes CLV a first-class metric, and at 272 games a season it is
   the fastest honest signal available. Given roughly 90,000 spare credits a
   month, the doubling costs headroom nobody is using.

   This is not urgent. It can wait until the probe reports and the models
   exist to be tested.

5. **The quota reset day**, if you happen to know it. Not blocking — the lab
   detects it for free by watching `x-requests-used` fall in the response
   headers — but a 2.5-month purchase is easier to schedule if it starts the
   day after a reset rather than the day before one.

Nothing is bet in the meantime. Nothing is allowlisted. The card says it is
accumulating evidence, because that is what it is doing.

---

## How those questions were answered

This file is a record of what was built and why, so the questions above are
left as they were asked. Every one of them is now closed.

1. **The purchase happened, in full.** Cooper approved it and added 5,000,000
   credits on 2026-08-28. **587,732 credits, 816 events across 2023-2025, two
   priced snapshots each** — every NFL game for which the provider serves
   historical props, since it serves none before 2023-05-03. There is nothing
   left to buy. The two-snapshot recommendation was taken.
2. **The quota resets monthly** (Cooper, 2026-08-28), which reversed this
   file's central conclusion that history was unaffordable. Credits were never
   the constraint.
3. **CLV is not a first-class metric here.** Cooper, 2026-08-29: *profit and
   ROI are the objective*. The passage above argues for the two-snapshot
   purchase partly on CLV grounds; the purchase was right, the reasoning was
   over-weighted, and CLV is now a diagnostic that raises questions and never
   answers one. It earned that keep once — a high return with no market
   movement was the first thing that pointed at the `tackles_assists`
   settlement artefact.
4. **NCAAF player props are out of scope** (Cooper, 2026-08-28).

## What the build order got right, and what it did not

**Right: the forward-evidence organ before the models.** It cannot be
back-dated, and it is now the only evidence that can still grow. Everything
historical is spent.

**Wrong, or at least incomplete: measurement was treated as a phase.** The
order runs data → models → measurement → evidence, as though measurement is
something done once the models exist. In practice **every positive result this
lab produced was an artefact**, and each was found by an instrument built
*after* the finding it killed — the null baseline, the settlement screen, the
price-sensitivity test, and a discipline test for the cross-season match, all
written because something had already got through.

A truer ordering would put the instruments before the models: a harness that
cannot be checked produces numbers that cannot be believed, and the checking
is not a later phase. The corrected state and the three retractions are in
`CLAUDE.md` and `docs/what_we_can_and_cannot_claim.md`.
