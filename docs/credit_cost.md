# What this costs, and whether it fits

`data/outputs/credit_cost.md` is the generated arithmetic, rebuilt by
`scripts/estimate_credit_cost.py` from the cached schedule so it cannot drift
from the market registry. This file is the reasoning around it, and it lives
in `docs/` rather than in the generated output because a finding appended to a
regenerated file lasts exactly one re-run.

## The correction that reorganised this document

The first version of this file treated 100,000 credits as a **single annual
pool**, because that is how the NHL lab's operating file reads. On 2026-08-28
Cooper confirmed the quota **resets monthly**.

That is not a detail. Under the annual reading, buying historical prices cost
twice the entire football budget and was impossible, and the whole build order
was shaped around doing without the instrument that decides everything in the
NHL lab. Under the monthly reading it costs **1.25 months** against a season
whose heaviest month uses 10% of one.

The wrong version is recorded here rather than deleted, because a plan built
on a reversed premise is worth knowing about when reading anything else this
lab wrote before 2026-08-28.

**The reset day is still unknown**, and is not assumed. The lab detects it by
watching `x-requests-used` fall in the response headers, which costs nothing.
Until it is known, any purchase needing most of a month is planned as though
the reset were the least convenient day it could be.

## Live pricing: not close to a constraint

The 2026 NFL regular season is **272 games across 57 game days**, 2026-09-09
to 2027-01-10. The NHL's 2026-27 season is **1,344 games across 185 game
days** — re-derived on 2026-08-28 from the league's own club-schedule
endpoint, and matching the NHL lab's recorded totals exactly, which is what
makes that table safe to use here.

| Scenario | Markets/event | NFL season | Worst month | NFL+NHL that month | Spare | Daily cap |
|:---------|--------------:|-----------:|:-----------|-------------------:|------:|----------:|
| featured only | 0 | 285 | 2027-01 | 4,559 | 95,441 | 100 |
| tier 1 | 46 | 12,797 | 2026-11 | 7,457 | 92,543 | 800 |
| **tier 1 + 2** | **83** | **22,861** | **2026-11** | **10,084** | **89,916** | **1,400** |
| full documented catalogue | 111 | 30,477 | 2026-11 | 12,072 | 87,928 | 1,800 |

**The heaviest month of the whole overlap uses about 10% of one month's
quota, running every market this lab has wired.** There is no version of the
live fetch that needs trimming, and the earlier instinct to ship a reduced
tier-1 market set to save credits was solving a problem that does not exist.

Tiers stay in the market registry, but they are now a **staging** decision —
what is wired and validated first — rather than a budget one. The card should
run tier 1 + 2 once both are settled and tested.

Every figure is the **pessimistic** bound: every asked market quoted and
billed. The per-event endpoint bills only markets it returns, so real spend is
lower. The cap is still set against the pessimistic bound, because a cap that
trusts the optimistic one is not a cap — and because a starved fetch and an
unquoted market look identical in the reports, which is the confusion this lab
must never make.

The daily cap comes from the season's worst slate — 2027-01-10, Week 18,
sixteen games kicking off simultaneously — and no other. A cap that clips the
largest slate of the season produces a degraded card on the day the card
matters most.

## Buying history: affordable, and therefore a decision rather than a wall

The historical endpoints bill **10 x markets x regions**. Historical player
props, alternate lines and period markets exist only after **2023-05-03**;
before that date only the featured markets are served.

| Purchase | Credits | Months of quota |
|:---------|--------:|----------------:|
| Featured markets only, one season | 8,160 | 0.08 |
| Twelve core props, one season | 32,640 | 0.33 |
| **Tier 1, one season, one snapshot per game** | **125,120** | **1.25** |
| Tier 1, one season, two snapshots (card-time and close) | 250,240 | 2.5 |
| Tier 1, two seasons, one snapshot | 250,240 | 2.5 |

With the leanest overlap month leaving 89,916 spare, a full tier-1 season
spread over two months fits without touching the live fetch at all.

**So the price-based backtest is available here, and the lab is not reduced to
calibration plus forward evidence.** That reverses the earlier conclusion.
Forward evidence is still built first and still cannot be back-dated; it is
simply no longer the only priced evidence this lab will ever have.

### What to buy is not obvious, and should not be guessed

Retention differs by market and by book, and the NHL lab discovered that the
hard way twice — `player_hits` returned zero rows from every book across 256
probed events, and the regulation three-way was retained by nobody. Spending
125,120 credits to find that out about football would be an expensive way to
learn something a probe answers for a fraction of it.

So the proposal is two steps, and the first is small:

1. **A retention probe**: roughly 20 past events spread across the 2024 and
   2025 seasons, tier-1 markets, one snapshot each.
   `20 x 46 x 10 = 9,200 credits` — under a tenth of one month. It answers,
   per market and per book, whether any historical price exists at all.
2. **The purchase**, sized from what step 1 finds, and re-costed before it is
   spent.

Both are credit spends and therefore Cooper's decision. Nothing is bought
without the number agreed first.

### One thing worth paying double for

The brief makes closing-line value a first-class metric. A single historical
snapshot per game gives one price and no CLV. **Two snapshots — one at roughly
the hour the card would have been built, one within minutes of kickoff — give
the model's price, the closing price, and therefore CLV on every historical
bet**, which is the fastest honest signal available at these sample sizes.

That doubles a one-season tier-1 purchase to 250,240, or about 2.5 months of
quota. Given the headroom, it is likely the better buy, and it is offered as
an option rather than assumed.

## The free instrument, which is still worth using

None of this displaces the closing-line series in the nflverse schedule file:
`spread_line`, `total_line` and both moneylines for every game back to 1999,
complete for 2024 and 2025, already present for 112 of the 272 2026 games, and
costing nothing.

It is one consensus closing line — no book, no ladder, no props — so it can
measure the **team model** and nothing else. But it can measure it back to
1999, which no purchase at any price can, and it is the right first priced
test precisely because it is free and deep.

## NCAAF now fits, which changes what "later" means

Order-of-magnitude arithmetic from a stated assumption, to be redone properly
from a real CFBD schedule before any NCAAF decision: roughly 136 FBS teams
playing about 12 games each is **~816 games** across about 15 Saturdays.

| Market set | Season credits | Per month over ~4 months |
|:-----------|---------------:|-------------------------:|
| tier 1 (46/event) | ~37,500 | ~9,400 |
| full catalogue (111/event) | ~90,600 | ~22,700 |

Added on top of the NFL and NHL peak month of 10,084, even the full catalogue
lands around **33,000 of 100,000**. **All three labs fit comfortably.**

Under the annual reading this was the one place the numbers said no. They do
not. So the reason to defer NCAAF is no longer money — it is that the NFL has
not been built yet, that 134 FBS teams with forty-point talent gaps are a
different distribution needing their own fitted models and their own verdicts,
and that **adding NCAAF must not move a single NFL number**.

The single Saturday cap is still real and still needs its own figure: 60 games
at 83 markets is about **5,000 credits in one day**, roughly four times the
NFL's worst slate. That is a cap to set, not a budget to worry about.
