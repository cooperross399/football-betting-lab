# What a 2026 NFL season costs in Odds API credits

Computed from the cached nflverse schedule: **272 regular-season games across 57 game days**, one region (`us`), each game fetched once on its own game day.

The shared account had **88,527 of 100,000 credits remaining** as of 2026-08-26, and the NHL lab has already committed **26,091** of them to its own season. So football is spending **62,436**, not 88,527.

| Scenario | Markets/event | Season (pessimistic) | + NHL | Against 88,527 | Worst slate | Daily cap |
|:---------|--------------:|---------------------:|------:|--------:|------------:|----------:|
| featured only | 0 | 285 | 26,376 | +62,151 | 16 games = 5 | 100 |
| tier 1 | 46 | 12,797 | 38,888 | +49,639 | 16 games = 741 | 800 |
| tier 1 + 2 | 83 | 22,861 | 48,952 | +39,575 | 16 games = 1,333 | 1,400 |
| full documented catalogue | 111 | 30,477 | 56,568 | +31,959 | 16 games = 1,781 | 1,800 |

**featured only** — Moneyline, spread and total from the bulk endpoint. No per-event call at all. The cheapest thing that can still freeze an opinion and settle it.

  57 bulk calls x 3 markets = 171; 272 events x 0 markets = 0; results 114. Pessimistic total **285**; optimistic floor (nothing but the featured three quoted anywhere) 285.

**tier 1** — What a Week 1 fetch asks for: the bulk three, seven per-event team markets, twenty player props and their nineteen alternate ladders.

  57 bulk calls x 3 markets = 171; 272 events x 46 markets = 12,512; results 114. Pessimistic total **12,797**; optimistic floor (nothing but the featured three quoted anywhere) 285.

**tier 1 + 2** — Everything this lab has wired and can settle: adds the quarter ladder, the second-half markets, the tie, the touchdown-order props and the composite yardage props.

  57 bulk calls x 3 markets = 171; 272 events x 83 markets = 22,576; results 114. Pessimistic total **22,861**; optimistic floor (nothing but the featured three quoted anywhere) 285.

**full documented catalogue** — Every NFL market the provider documents, including the quarter alternate ladders this lab has not wired. Printed as the ceiling, not as a plan.

  57 bulk calls x 3 markets = 171; 272 events x 111 markets = 30,192; results 114. Pessimistic total **30,477**; optimistic floor (nothing but the featured three quoted anywhere) 285.

## Buying history costs ten times as much

The historical endpoints bill **10 x markets x regions**, and historical player props, alternate lines and period markets exist only after 2023-05-03.

One season of tier-1 markets at one snapshot per game: 272 events x 46 markets x 10 = **125,120 credits**. That is 1.4x the entire remaining quota, for one season, at one snapshot per game.

This is the number that decides the build order. A price backtest on bought NFL prop history is not affordable at the current quota on any market set worth measuring, and no amount of care in the code changes that. Forward evidence — frozen before kickoff, settled after — is not a cheaper substitute for it; it is the only priced evidence this lab can afford to collect, and every week it is not running is a week of it gone permanently.

