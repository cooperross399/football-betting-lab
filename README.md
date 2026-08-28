# Football Betting Lab

NFL now, NCAAF later. Modelled on `nhl-betting-lab`; the gates, the provider
staging discipline and the honesty rules are carried over because they were
earned there.

**Nothing has been measured. No market is allowlisted. Nothing is bet.**

Read `CLAUDE.md` first. Then:

| Document | What it answers |
|:---------|:----------------|
| `docs/what_we_can_and_cannot_claim.md` | What the evidence supports. Written before the first measurement. |
| `docs/football_data_sources.md` | Where every number comes from, what each source cannot tell us, and its licence. |
| `docs/credit_cost.md` | What this costs against a quota shared with the NHL lab. |
| `docs/build_order.md` | What is being built, in what order, and what is needed from Cooper. |

## Where things stand

The 2026 NFL regular season is **272 games across 57 game days**, opening
**Wednesday 2026-09-09**. Live pricing fits the shared Odds API quota
comfortably; **buying historical prices does not** — one season would cost
twice the entire football budget. So the priced instrument that decided
everything in the NHL lab is unavailable here, and the build order puts the
forward-evidence organ first: historical prices can be bought later, forward
evidence cannot be back-dated.

## Setup

```bash
/opt/homebrew/opt/python@3.12/bin/python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install -e .
```

## Commands

```bash
# The season's credit cost, computed from the cached schedule. Spends nothing.
PYTHONPATH=src .venv/bin/python scripts/estimate_credit_cost.py

# Tests
PYTHONPATH=src .venv/bin/python -m pytest -q
```

## Data attribution

Game, play-by-play, roster, depth chart, snap count and injury data come from
[nflverse](https://github.com/nflverse/nflverse-data), used under
**CC-BY-4.0**. Prices come from [The Odds API](https://the-odds-api.com).
Results never come from the odds provider.
