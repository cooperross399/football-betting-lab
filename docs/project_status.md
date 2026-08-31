# Project status

Read this second, after `CLAUDE.md`. It is the shortest honest answer to
"where is this and what should I do next".

**As of 2026-08-31. Week 1 opens Wednesday 2026-09-09 — nine days.**

## The one-line summary

The machinery is built, running and unusually well instrumented. **It found
three defects in its own headline findings and every one of those findings is
now retracted.** The corrected answer is **no demonstrated edge anywhere**, and
nothing is allowlisted, so nothing is bet.

## What the evidence says

Measured on the **entire** population of NFL games for which historical props
exist — 816 games across 2023-25, two priced snapshots each, 5.67M price rows.
The provider serves props only after 2023-05-03, so **there is no more to buy.**

- **0 of 18 markets clear every bar** in the allowlist evidence bundle. Every
  market's family-corrected interval includes zero on its held-out seasons,
  which is *no demonstrated edge* in this lab's own declared words.
- **No market is profitable at the consensus price** except `tackles_assists`,
  which the settlement screen flags. The one market that replicates and the
  one market that is a suspect are the same market, and that is not a
  coincidence — a constant settlement offset replicates by construction.
- **The prop models lose, and lose less than nothing.** 2023 −1.6%, 2024
  −2.1%, 2025 −5.2%, against a null baseline of −9.47%. The model is better
  than betting at random and still loses.
- **The team model does not beat the closing line**: moneyline −6.2%, spread
  −1.9%, total −1.8%, every interval including zero.

### Three retractions, in the order they happened

| Claim this lab published | What it actually is |
|:---|:---|
| `tackles_assists` **+16%**, replicated across three seasons | A settlement artefact. Still is, at the corrected +11.7%. |
| `rush_yards` **+14.0%** held-out, **+8.3%** at consensus, 10 of 11 books | **+1.6%** held-out, **−1.0%** at consensus, 2 of 10 books. |
| Compound markets **+3.5%** vs count-only **−9.8%** — "the strongest structure in the evidence" | No split. **−6.3%** vs **−7.5%** at the consensus price. It was the gap between two bugs. |

The three defects behind them — cross-season settlement, a walk-forward leak
in the pooled per-play yardage file, and zero-inflation in the count fits —
are fixed with regression tests. `CLAUDE.md` has the full account.

## The instruments, and why each exists

Each was built because something failed it. Run all of them before believing a
result.

| Script | Catches |
|:---|:---|
| `run_null_baseline.py` | A broken harness. Betting everything must lose; it returns −9.47%. |
| `run_settlement_agreement.py` | Settling on a different quantity from the one priced. A constant offset replicates perfectly and survives every other check. |
| `run_price_sensitivity.py` | An edge that exists only as the maximum of N quotes, or at one soft book. |
| `run_props_replication.py` | A result that holds only on the season it was found in. Necessary, and by itself not sufficient. |
| `run_availability_cost.py` | What not knowing who plays actually costs. |
| `run_clv.py` | A diagnostic only. Profit and ROI are the objective. |

**Run the replication, not the single-season backtest, before any of the
downstream reports.** `run_props_backtest.py` scores one season and writes a
season-scoped file; the pooled `nfl_props_backtest_bets.csv` that four reports
read comes only from `run_props_replication.py`. They shared a filename until
2026-08-31, and a concurrent session overwrote three seasons of evidence with
one while this was being fixed.

## What blocks a bet

1. **The evidence itself.** Nothing clears the bars. This is the binding
   constraint now, and it was not before.
2. **Nothing is allowlisted.** The bundle is prepared; step six is Cooper's
   signature and Claude never writes it. There is currently nothing in it to
   sign for.
3. **No player prop can produce a selection** until the verdict
   `props_selectable_when_undesignated` is in force.

## What to do next, in order

1. **Let the forward ledger accumulate from 2026-09-09.** It is now the *only*
   evidence that can still grow, at 272 games a season, and it cannot be
   back-dated. Everything else is spent.
2. **Do not tune models against the bought data.** The population is complete
   and every variant tested against it spends a degree of freedom. The
   verdicts door records how many have been spent, and the three retractions
   above are what happens when a result is believed before the instruments
   have all run.
3. **Answer the did-not-play question when convenient.** It no longer decides
   anything — void gives `rush_yards` +0.9%, loss gives −4.4%, and neither is
   an edge — but a live card would still need the answer.
4. **Treat the modelling as unfinished, not as failed.** Nothing here says the
   NFL is unbeatable. It says this model, on this data, has no demonstrated
   edge, and it says so on a large enough sample to mean it.

## The parallel worth keeping in view

The NHL lab's +1.4% over 4,830 bets became **−1.6% over 73,918** once it
bought its full population, its one positive market failed replication, and
its allowlist approval was **withdrawn**. Both labs have now arrived at the
same answer by different routes: this one by finding defects in its own
harness, that one by buying more data.

## The honest summary

Everything measurable has been measured, on all the data that exists, with
five independent instruments. **Nothing survives.** Three apparent findings
were killed by the instruments rather than by luck — one of them twice — which
is the strongest evidence that the machinery works and the clearest possible
warning against believing the next good number before every instrument has run
on it.
