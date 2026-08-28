# Project status

Read this second, after `CLAUDE.md`. It is the shortest honest answer to
"where is this and what should I do next".

**As of 2026-08-28. Week 1 opens Wednesday 2026-09-09 — twelve days.**

## Where the lab is

**Built and running:**

- **The league registry**, with the NFL as its only entry and a discipline
  test that fails the build if a league literal appears anywhere else. NCAAF
  is a registry entry plus an adapter when it comes, and it comes **without
  player props** (Cooper, 2026-08-28).
- **The data layer.** Eight nflverse feeds cached; a completed season fetched
  once and never again; the current season refetched because the NFL revises
  statistics Monday to Wednesday and Thursday's copy is the clean one.
  Processed tables: 1,359 team-games and 72,457 player-games, 2022-2026.
- **The market registry**: 60 markets, each naming the nflverse quantity that
  settles it, the rest recorded as deferred with a reason.
- **The provider adapter**, proven against real responses. The first live
  shadow run staged 3,589 rows across 17 markets and 9 books with zero
  unparseable.
- **The retention probe**: all 27 tier-1 markets have historical prices, 25
  with enough coverage to measure against.
- **The models.** Team scoring by exponential tilting of the empirical score
  distribution, so key numbers survive and pushes are exact. Player props by
  one compound simulation per player, so receptions, yards, longest and
  touchdowns cannot disagree and every alternate rung prices from the same
  distribution.
- **Walk-forward calibration**, reported with its sample sizes and its
  defects.
- **The gates**: preseason, kickoff, availability, quarterback change, market
  eligibility, and a fail-closed per-league policy that allowlists nothing.
- **The forward-evidence organ**: freeze before kickoff, settle after, never
  reprice, day-as-unit, voids return the stake, unsettleable counted.
- **`Football Gameday Refresh`**, publishing to the `card-feed` branch. Run
  live end to end on 2026-08-28.

**Not built, deliberately:**

- **No half or quarter model.** Those markets are wired and settleable and
  have no model, so they are `no_opinion` — not `unparseable`, which would
  read as an adapter fault.
- **No bought historical prices.** The probe says they exist; the purchase is
  a credit-spend decision and therefore Cooper's.
- **No snap-share or target-share input.** Both feeds are cached and unused,
  so the model prices a player's recent role rather than his current one.
- **No game-script conditioning**, and the calibration measures what that
  costs: excess mass in the lowest decile, because nothing here knows a
  player's day can be cut short.
- **No weather source.** nflverse carries conditions, not forecasts.

## What the card does today

Prices every market it can, freezes every opinion into the ledger, settles the
days that are final, and **recommends nothing** — because no market has a
reviewed approval. It says so in those words, prints the accounting identity,
and names every excluded market with its reason.

That is not a degraded card. It is the product until the evidence exists.

## The two things only Cooper can do

1. **Allowlist a market.** Six steps in `docs/provider_allowlist_approval.md`;
   Claude prepares all six and stops at the sixth.
2. **Authorise credit spend** beyond a small measurement budget.

## What to do next, in order

1. **Let the schedule run from 2026-09-09 and let the ledger accumulate.** It
   is the only out-of-sample evidence stream, and it cannot be back-dated.
2. **Build the free closing-line backtest** on the nflverse schedule file —
   spread, total and both moneylines back to 1999, costing nothing. It is the
   first priced test the team model can face, and it should decide the team
   model the way the bought backtest decides in the NHL lab.
3. **Watch the first live slates** for the failure modes the gates were built
   against: unresolved club names, players unknown to the roster, an identity
   that does not reconcile.
4. Then, with Cooper's approval, the **historical purchase** and the prop
   backtest.
5. Only then: evidence assembled for a market to be approved.

## The honest summary

Nothing has been measured against a price. The machinery for finding out is
built and running, the calibration says the distributions are roughly the
right shape, and none of that is evidence that there is anything to find. The
first genuinely out-of-sample evidence this lab will ever have arrives on
2026-09-09, one game-day at a time.
