# Project status

Read this second, after `CLAUDE.md`. It is the shortest honest answer to
"where is this and what should I do next".

**As of 2026-08-29. Week 1 opens Wednesday 2026-09-09 — eleven days.**

## The one-line summary

The machinery is built, running and unusually well instrumented. **The
evidence is genuinely mixed**, one apparent finding has already been killed by
that instrumentation, and **nothing is allowlisted, so nothing is bet.**

## What the evidence says

Measured on the **entire** population of NFL games for which historical props
exist — 816 games across 2023-25, three snapshots each, 8.4M price rows. The
provider serves props only after 2023-05-03, so **there is no more to buy.**

- **The models split by how a market is priced, not by which market it is.**
  At the consensus (median) price, clustered by game: the nine
  compound-simulation markets return **+3.5% over 100,230 bets, interval
  +1.4% to +5.7%**; the ten count-only markets return **−9.8%, interval
  −12.1% to −7.5%**. That split is the strongest structure in the evidence.
- **Three markets clear every bar** in the allowlist evidence bundle:
  `rush_yards`, `receptions`, `reception_longest`. All compound.
- **`tackles_assists` returned +16% across three seasons and was an
  artefact.** nflverse undercounts assisted tackles; the featured market is
  priced 50% over and lands 42%. That gap is worth 16% to a model betting 86%
  unders, and the measured edge was +16.3%.
- **The team model does not beat the closing line**: moneyline −6.2%, spread
  −1.9%, total −1.8%, every interval including zero.
- **The mechanism behind the compound/count split is not understood**, which
  is the largest open question in the lab.

## The instruments, and why each exists

Each was built because something failed it. Run all of them before believing a
result.

| Script | Catches |
|:---|:---|
| `run_null_baseline.py` | A broken harness. Betting everything must lose; it returns −9.28%. |
| `run_settlement_agreement.py` | Settling on a different quantity from the one priced. A constant offset replicates perfectly and survives every other check. |
| `run_price_sensitivity.py` | An edge that exists only as the maximum of N quotes, or at one soft book. |
| `run_props_replication.py` | A result that holds only on the season it was found in. Necessary, and by itself not sufficient. |
| `run_availability_cost.py` | What not knowing who plays actually costs. |
| `run_clv.py` | A diagnostic only. Profit and ROI are the objective. |

## What blocks a bet

1. **Nothing is allowlisted.** The evidence bundle is prepared; step six is
   Cooper's signature and Claude never writes it.
2. **No player prop can produce a selection** until the verdict
   `props_selectable_when_undesignated` is in force — and that waits on one
   line in a book's rules: whether a did-not-play prop is **voided** or graded
   a loss. Void gives `rush_yards` +13.0%; loss gives −0.8%.

## What to do next, in order

1. **Answer the did-not-play question.** Everything downstream turns on it and
   no measurement can settle it.
2. **Explain the compound/count split.** +3.5% against −9.8% is either a real
   mechanism worth building on or a defect not yet found. Until it is
   understood, the supported markets are a result rather than a strategy.
3. **Let the forward ledger accumulate from 2026-09-09.** It is the only
   evidence that can still grow, at 272 games a season, and it cannot be
   back-dated.
4. **Do not tune models against the bought data.** The population is complete
   and every variant tested against it spends a degree of freedom. The
   verdicts door records how many have been spent.

## The parallel worth keeping in view

The NHL lab's +1.4% over 4,830 bets became **−1.6% over 73,918** once it
bought its full population, its one positive market failed replication, and
its allowlist approval was **withdrawn**. That is the direction of surprise to
expect. The difference here is that this lab already holds its full
population — but three seasons is still three seasons.

## The honest summary

Everything measurable has been measured, on all the data that exists, with
five independent instruments. Three markets survive. One apparent finding was
killed by the instruments rather than by luck, which is the strongest evidence
that the machinery works. Whether the survivors are real is not yet known, and
the lab says so.
