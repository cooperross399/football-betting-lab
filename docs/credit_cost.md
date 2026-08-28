# What this costs, and whether it fits

`data/outputs/credit_cost.md` is the generated arithmetic, rebuilt by
`scripts/estimate_credit_cost.py` from the cached schedule so it cannot drift
from the market registry. This file is the reasoning around it, and it lives
in `docs/` rather than in the generated output because a finding appended to a
regenerated file lasts exactly one re-run — the NHL lab learned that with
`schedule_states_checked.md`.

## The arithmetic, as of 2026-08-28

The 2026 NFL regular season is **272 games across 57 game days**, one region
(`us`), each game fetched once on its own game day.

The shared account had **88,527 of 100,000 credits remaining** on 2026-08-26,
and the NHL lab has committed **26,091** of them to its own season (185 game
days, 1,344 games, 19 asked markets, one fetch a day). So football is spending
**62,436**, not 88,527.

| Scenario | Markets/event | NFL season | + NHL | Headroom | Worst slate | Daily cap |
|:---------|--------------:|-----------:|------:|---------:|------------:|----------:|
| featured only | 0 | 285 | 26,376 | +62,151 | 5 | 100 |
| **tier 1** | **46** | **12,797** | **38,888** | **+49,639** | **741** | **800** |
| tier 1 + 2 | 83 | 22,861 | 48,952 | +39,575 | 1,333 | 1,400 |
| full documented catalogue | 111 | 30,477 | 56,568 | +31,959 | 1,781 | 1,800 |

Every figure is the **pessimistic** bound: every asked market quoted and
billed. The per-event endpoint bills only markets it actually returns, so the
real spend will be lower — but a cap set against the optimistic bound is not a
cap, and the NHL lab has already had one August board starve the nearest nine
games by spending its budget four days out.

## What this says

**Live pricing fits, comfortably, even at the full catalogue.** That was not
obvious before it was computed, and it is the most useful thing this
arithmetic establishes. There is no need to trim markets to afford the season.

The worst slate is 2027-01-10 — Week 18, all sixteen games kicking off
simultaneously. The daily cap is set from that game and no other, because a
cap that clips the largest slate of the season is a cap that produces a
degraded card on the day the card matters most.

## What does not fit, and this is the important part

**Buying historical prices.** The historical endpoints bill ten times the live
rate. One NFL season of tier-1 markets, at one snapshot per game:

> 272 events x 46 markets x 10 credits = **125,120 credits**

against roughly 62,000 remaining for football. That is **twice the entire
football budget for one season at one snapshot**, and it buys a single frozen
moment per game rather than a closing line.

There is no version of this that fits by being clever. Trimming to twelve core
props is still 32,640 for one season — over half the football budget, spent on
one season of one snapshot, leaving nothing for the live pricing that
accumulates forward evidence.

**So the instrument that decided everything in the NHL lab is not available
here.** The NHL lab's verdicts — what ships, what does not, which corrections
are real — all rest on 192 bought event-days of props and two bought seasons
of team markets. This lab cannot buy the equivalent, and every report will say
so rather than presenting calibration as though it filled the gap.

## What is available instead

1. **The free closing-line series.** The nflverse schedule file carries
   `spread_line`, `total_line` and both moneylines for every game back to
   1999 — complete for 2024 and 2025, and already present for 112 of the 272
   2026 games. This is a real priced test for the **team model** and it costs
   nothing. It is one consensus line, not a book quote, with no ladder and no
   props, and it can never answer "what price was actually available".
2. **Forward evidence.** Frozen before kickoff, settled after, never repriced.
   Stronger than a reconstruction in one way and much slower in another: 272
   games a season. This is why the build order puts it first.
3. **A targeted historical purchase**, if Cooper wants one. A single market
   family, one snapshot, one season, with the arithmetic agreed in advance.
   That is a credit-spend decision and therefore his alone.

## The one thing that would change all of this

**Does the quota reset, and how often?** Everything above treats 100,000 as a
single pool, because that is how the NHL lab's operating file treats it. If
the plan's quota is **monthly**, then football, hockey and college football
all fit with room to spare, and the historical purchase becomes affordable
across a few months.

This has not been verified, and it is the single assumption that moves the
answer most. It is free to check — the `x-requests-remaining` header on the
free `/v4/sports` endpoint, read on two dates either side of a reset, or the
plan page on Cooper's account. **This is question 1 for Cooper**, and the
NCAAF arithmetic below is not worth finishing until it is answered.

## NCAAF, roughly, so nobody is surprised in October

Not computed from a real schedule — CFBD needs a key this lab does not have —
so this is order-of-magnitude arithmetic from a stated assumption, clearly
labelled as such, and it will be redone properly before any NCAAF decision.

Roughly 136 FBS teams playing about 12 games each is **~816 games**, more than
three times the NFL's 272, concentrated into about 15 Saturdays.

| Market set | Games | Credits |
|:-----------|------:|--------:|
| featured only (bulk) | 816 | ~100 |
| tier 1 (46/event) | 816 | ~37,500 |
| full catalogue (111/event) | 816 | ~90,600 |

Against a **single annual pool**, NCAAF at tier 1 alongside the NHL and the
NFL is 26,091 + 12,797 + 37,500 = **76,388 of 88,527** — it fits, barely, with
nothing left for a single historical purchase or a re-fetch. At the full
catalogue it does not fit at all.

A single Saturday with 60 games at 46 markets is **2,760 credits in one day**,
which is larger than the NFL's entire worst slate and needs its own cap.

So: NCAAF is affordable only at a reduced market set, only if the pool is
annual, and only with the historical purchase abandoned entirely. If the pool
is monthly, none of that is true and the question changes completely. Hence
question 1.
