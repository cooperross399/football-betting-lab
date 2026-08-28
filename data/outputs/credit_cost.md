# What a 2026 NFL season costs in Odds API credits

Computed from the cached nflverse schedule: **272 regular-season games across 57 game days**, one region (`us`), each game fetched once on its own game day.

**The quota is 100,000 per calendar month**, shared with the NHL lab, whose season overlaps this one from late September to January. So the unit here is the month, and the question is whether the *worst* month fits.

| Scenario | Markets/event | NFL season | Worst month | NFL+NHL that month | Spare | Worst slate | Daily cap |
|:---------|--------------:|-----------:|:------------|-------------------:|------:|------------:|----------:|
| featured only | 0 | 285 | 2027-01 | 4,559 | 95,441 | 16 games = 5 | 100 |
| tier 1 | 46 | 12,797 | 2026-11 | 7,457 | 92,543 | 16 games = 741 | 800 |
| tier 1 + 2 | 83 | 22,861 | 2026-11 | 10,084 | 89,916 | 16 games = 1,333 | 1,400 |
| full documented catalogue | 111 | 30,477 | 2026-11 | 12,072 | 87,928 | 16 games = 1,781 | 1,800 |

Every figure is the **pessimistic** bound: every asked market quoted and billed. The per-event endpoint bills only markets it returns, so real spend is lower — but a cap set against the optimistic bound is not a cap.

## Month by month, at **tier 1 + 2**

| Month | NFL games | NFL credits | NHL games | NHL credits | Combined | Spare of 100,000 |
|:------|----------:|------------:|----------:|------------:|---------:|-----------:|
| 2026-09 | 48 | 4,034 | 8 | 162 | 4,196 | 95,804 |
| 2026-10 | 60 | 5,045 | 218 | 4,297 | 9,342 | 90,658 |
| 2026-11 | 71 | 5,973 | 209 | 4,111 | 10,084 | 89,916 |
| 2026-12 | 62 | 5,221 | 214 | 4,206 | 9,427 | 90,573 |
| 2027-01 | 31 | 2,588 | 231 | 4,544 | 7,132 | 92,868 |
| 2027-02 | 0 | 0 | 155 | 3,065 | 3,065 | 96,935 |
| 2027-03 | 0 | 0 | 227 | 4,468 | 4,468 | 95,532 |
| 2027-04 | 0 | 0 | 82 | 1,608 | 1,608 | 98,392 |

The heaviest month is **2026-11** at 10,084 credits, leaving **89,916 spare**. Across the eight months both seasons touch, the unused capacity totals **750,678 credits**.

**featured only** — Moneyline, spread and total from the bulk endpoint. No per-event call at all. The cheapest thing that can still freeze an opinion and settle it.

**tier 1** — The bulk three, seven per-event team markets, twenty player props and their nineteen alternate ladders.

**tier 1 + 2** — Everything this lab has wired and can settle: adds the quarter ladder, the second-half markets, the tie, the touchdown-order props and the composite yardage props.

**full documented catalogue** — Every NFL market the provider documents, including the quarter alternate ladders this lab has not wired.

## Buying history costs ten times as much — and now that is affordable

The historical endpoints bill **10 x markets x regions**, and historical player props, alternate lines and period markets exist only after 2023-05-03.

One season of tier-1 markets at one snapshot per game: 272 events x 46 markets x 10 = **125,120 credits**.

Against a single annual pool that was impossible. Against 100,000 a month it is **1.25 months of quota**, and the leanest month of the overlap still has 89,916 spare. Spread across two months it fits without touching the live fetch.

Cheaper shapes, for comparison:

* Featured markets only (moneyline, spread, total), one season: 8,160 credits — under a fifth of one month.
* Twelve core props, one season: 32,640.
* Two seasons of tier 1: 250,240, or about 2.5 months.

**This reverses the earlier conclusion in this repository.** A price-based backtest on bought NFL prop history is affordable, so the instrument that decides everything in the NHL lab is available here too. Forward evidence is still built first and still cannot be back-dated — but it is no longer the only priced evidence this lab will ever have.

It remains a credit-spend decision, and therefore Cooper's.

