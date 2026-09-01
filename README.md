# Football Betting Lab

NFL now, NCAAF later. Modelled on `nhl-betting-lab`; the gates, the provider
staging discipline and the honesty rules are carried over because they were
earned there.

**Everything available has been measured and the answer is no demonstrated
edge.** 816 games — every NFL game for which historical props exist — five
instruments, 0 of 18 markets clearing the bars declared in advance. **No
market is allowlisted, nothing is bet, and that is the correct state.** The
forward ledger, from 2026-09-09, is the only evidence that can still grow.

Read `CLAUDE.md` first. Then:

| Document | What it answers |
|:---------|:----------------|
| `docs/what_we_can_and_cannot_claim.md` | What the evidence supports. Written before the first measurement. |
| `docs/football_data_sources.md` | Where every number comes from, what each source cannot tell us, and its licence. |
| `docs/credit_cost.md` | What this costs against a quota shared with the NHL lab. |
| `docs/build_order.md` | What is being built, in what order, and what is needed from Cooper. |
| `docs/new_session_prompt.md` | How to start a session on this lab, and the facts that live outside the repo. |
| `data/outputs/nfl_carding_window.md` | When each game is actually carded, and what a dropped run costs. Computed from the crons, never written by hand. |

## Where things stand

The 2026 NFL regular season is **272 games across 57 game days**, opening
**Wednesday 2026-09-09**.

The Odds API quota resets monthly, and credits are not a constraint: the
heaviest month of the NFL/NHL overlap uses about 10% of one month, running
every wired market. Buying historical prices is affordable too — 1.25 months
for a full season.

The build order still puts the forward-evidence organ first, and for the one
reason that has not changed: **historical prices can be bought later, forward
evidence cannot be back-dated.**

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

# When each game is actually carded, and what a dropped run would cost.
# Reads the workflow's crons and the schedule cache. Spends nothing.
PYTHONPATH=src .venv/bin/python scripts/run_carding_window.py --season 2026

# Tests
PYTHONPATH=src .venv/bin/python -m pytest -q
```

## Data attribution

Game, play-by-play, roster, depth chart, snap count and injury data come from
[nflverse](https://github.com/nflverse/nflverse-data), used under
**CC-BY-4.0**. Prices come from [The Odds API](https://the-odds-api.com).
Results never come from the odds provider.
