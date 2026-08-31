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

### What to buy — now informed by the probe rather than guessed

Retention differs by market and by book, and the NHL lab discovered that the
hard way twice — `player_hits` returned zero rows from every book across 256
probed events, and the regulation three-way was retained by nobody. Spending
125,120 credits to find that out about football would have been an expensive
way to learn something the probe answered for 7,280.

What it found changes the sizing in one useful direction: because the
endpoint bills per market **returned**, the pessimistic 125,120 for a full
tier-1 season is an overestimate by roughly the same 21% the probe observed.
A full season of tier-1 markets at one snapshot should land nearer
**99,000 credits** — still about a month, and now a measured figure rather
than a bound. The two thin markets add almost nothing to that either way.

So the proposal was two steps, and the first is now done.

**Step 1 — the retention probe, run 2026-08-28.** 20 events, stratified across
kickoff windows, split evenly between 2024 and 2025, 46 provider keys each, at
a snapshot 60 minutes before kickoff.

* **Cost: 7,280 credits** against a pessimistic bound of 9,220. The 21%
  shortfall is not slack — the endpoint bills per market *returned*, so it is
  exactly the keys no book retained.
* **The documented 10x historical rate is confirmed by measurement**: 7,260
  credits over 696 market-events, plus 20 slate listings — about 10.4 per
  market returned. Nothing in this repository assumes the rate any more.
* **All 27 tier-1 markets have historical prices; 25 have enough to measure
  against.** Nine books. `data/outputs/nfl_retention_probe.md`.
* Quota after the probe: **79,659 remaining of this month's 100,000.**

**Step 2 — the purchase**, now sizeable with real numbers rather than a
pessimistic bound. See "What to buy" below.

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

## NCAAF: not a money question at all, and now a smaller one

**Cooper ruled NCAAF player props out of scope on 2026-08-28** — not
essential. College football is a team-markets league unless he says otherwise.
That takes the transfer portal, opt-outs and a per-player college data join
off the critical path entirely, and it changes the arithmetic below more than
the monthly reset did.

Order-of-magnitude figures from a stated assumption, to be redone properly
from a real CFBD schedule before any NCAAF decision: roughly 136 FBS teams
playing about 12 games each is **~816 games** across about 15 Saturdays.

| Market set | Season credits | Per month over ~4 months |
|:-----------|---------------:|-------------------------:|
| **team markets only (~11/event)** | **~9,000** | **~2,300** |
| tier 1 with props (46/event) | ~37,500 | ~9,400 |
| full catalogue (111/event) | ~90,600 | ~22,700 |

Added on top of the NFL and NHL peak month of 10,084, college team markets
land around **12,400 of 100,000**. Even the full catalogue would have fitted,
at ~33,000. With props out of scope it is not close.

A single Saturday of 60 games at team markets only is about **700 credits** —
smaller than one NFL Sunday. That is still a cap to set, computed from a real
schedule, but it is not a budget to worry about.

So nothing about NCAAF is deferred for money. What defers it is that the NFL
is not built, that 134 FBS teams with forty-point talent gaps are a different
distribution needing their own fitted models and their own verdicts, and that
**adding NCAAF must not move a single NFL number** — a rule that is now
satisfied structurally rather than by testing, because as of 2026-08-31 NCAAF
is a separate repository and cannot touch this lab's numbers at all. What it
CAN still touch is the shared quota: one Odds API account funds every lab, so
a college Saturday's cost is subtracted from the same pool as an NFL Sunday's
and the arithmetic here must be read against all labs together.
