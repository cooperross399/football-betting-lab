# CLAUDE.md — Football Betting Lab Operating Instructions

This repository is the source of truth for the Football Betting Lab. Claude
operates it directly. Where anything else in the repo conflicts with this file,
this file wins.

**Active repo path: `/Users/cooperross/Projects/football-betting-lab`.**

**Scope: the NFL ships first. NCAAF is added later, and the architecture is
built for it from day one.** League is a first-class dimension everywhere, so
adding college football is a new registry entry, a new adapter and a new set of
fitted models — never a refactor. Do not build NCAAF now.

The lab is modelled on `../nhl-betting-lab`, deliberately: the verdicts door,
the forward-evidence ledger, the allowlist receipt and PR gate, the start-time
guard, `selection_key()`, the accounting identity, the cache and shrink guards
and the honesty rules are carried over because they were earned there. Change
the sport, not the standards.

## Read these first

Every session, in this order. These replace chat history as project memory.

1. `CLAUDE.md` (this file) — hard rules, which override everything.
2. `docs/what_we_can_and_cannot_claim.md` — written before the first
   measurement. Read before making any claim about whether this works.
3. `docs/football_data_sources.md` — where every number comes from, what each
   source cannot tell us, and its licence.
4. `docs/credit_cost.md` — what this costs against a quota shared with the NHL
   lab, and the one unanswered question that moves the answer.
5. `docs/build_order.md` — what is being built, in what order, and why.
6. Latest `data/outputs/` reports, then PRs and Actions runs.

## Current operating state

**As of 2026-08-28. Nothing has been measured. There is no model, no fitted
parameter, no backtest, and no evidence of any kind about whether this works.**
The only numbers in this repository are counts of games, markets and credits.
Anything that sounds like a finding before Week 1 is a bug.

- **Week 1 opens Wednesday 2026-09-09**, NE @ SEA, 20:20 ET — **not** the
  Thursday after Labor Day, which is the season's second game (SF @ LA,
  2026-09-10). Verified against the nflverse schedule, as the brief instructed,
  rather than assumed. That is **12 days from today**.
- **The 2026 regular season is 272 games across 57 game days**, 2026-09-09 to
  2027-01-10, weeks 1-18. Largest slate: 16 games on 2027-01-10, all
  simultaneous.
- **The quota resets monthly, and credits are not a constraint.** Confirmed by
  Cooper 2026-08-28. The heaviest month of the NFL/NHL overlap is 2026-11 at
  **10,084 of 100,000**, running every market this lab has wired. Tiers in the
  market registry are now a *staging* decision, not a budget one.
  `docs/credit_cost.md`.
- **An earlier version of this file said buying history was impossible. That
  was wrong**, and it was wrong because it read the quota as an annual pool.
  One season of tier-1 historical prices is 125,120 credits — **1.25 months**.
  The price-based backtest that decides everything in the NHL lab is available
  here. The record of the reversal stays in `docs/credit_cost.md`.
- **Three priced instruments**: the free closing-line series in the nflverse
  schedule file (back to 1999, complete for 2024-25, 112 of 272 2026 games
  already lined — one consensus line, no ladder, no props, team markets only);
  forward evidence at 272 games a season, which **cannot be back-dated** and is
  therefore built first regardless; and bought history, now probed.
- **The retention probe has run (2026-08-28, 7,280 credits, Cooper's
  approval).** 20 events stratified across kickoff windows, split evenly
  between 2024 and 2025, 46 provider keys each, 60 minutes before kickoff.
  **All 27 tier-1 markets have historical prices; 25 have enough to measure
  against**, across nine books. `reception_tds` and `rush_tds` are retained
  but thin — 2 of 20 events, one book each — and "retained" is not "measurable".
  Quota after: 79,659 of this month's 100,000.
- **The documented 10x historical rate is now measured, not assumed**: about
  10.4 credits per market returned. A full tier-1 season at one snapshot should
  cost nearer 99,000 than the pessimistic 125,120.
- **The probe reproduced the `total_2_5` mistake before it could be made.**
  Three featured prop keys returned nothing across all 20 events while their
  alternate ladders had them. Read per key that is three unmeasurable markets;
  read per market — the unit that gets modelled, measured and approved — it is
  none. Every retention conclusion rolls up to the market first. The reverse
  case is in the same data: `pass_longest_completion` is retained on 20 of 20
  and its ladder on none.
- **Two defects were found and fixed by reproduction, each with a regression
  test.** The probe cached chunk responses under a filename tagged with the
  chunk's *length*, so four ten-market chunks collided and three were lost —
  the NHL lab's `_markets_fingerprint` exists for exactly that and was not
  ported. And the secrets guard flagged the provider's 32-hex **event ids**,
  which are the same shape as an API key; the exemption is by recorded value,
  never by directory, so a hex run that is not a known event id is still a
  finding even under `data/raw/`.
- **The report is derived data and rebuilds from the run record**
  (`scripts/rerender_retention_probe.py`). Improving its wording must never
  cost 7,280 credits again.
- **NCAAF now fits the quota too.** All three labs at the full catalogue land
  around 33,000 of 100,000 in a peak month. The reason to defer college
  football is no longer money — it is that the NFL is not built, that FBS is a
  different distribution needing its own fits and verdicts, and that adding it
  must not move a single NFL number.
- **The league registry exists and the NFL is its only entry.**
  `src/football_betting_lab/leagues.py` holds every league-specific fact:
  sport key, adapter, market registry, timezone, credit cap, policy key,
  output prefix. A discipline test fails the build if a league literal appears
  anywhere else.
- **60 markets are wired with the nflverse quantity each settles against**,
  across two tiers; the provider's remaining NFL keys are in
  `markets.DEFERRED_MARKETS` with a reason each. Wired is not quoted and not
  allowlisted: **no market is allowlisted, and that is the correct state.**
- **Play-by-play settles almost everything**, including quarter and half
  scores and touchdown *ordering* — unlike the NHL lab, where periods and goal
  order were genuinely unsettleable. Defensive counting stats are the
  exception: they are revised by the NFL between Monday and Wednesday, so
  settlement reads the Thursday copy and re-settles rather than leaving a
  pre-correction row.
- **Route participation cannot be had in season.** nflverse's participation
  feed publishes only after the post-season. Snap share (PFR, in season,
  lagged) and target share (from play-by-play, same lag) are available; routes
  run are not, and no report will imply otherwise.
- **No feed publishes inactives.** The weekly injury report can *exclude*
  (`report_status == Out`) and cannot *confirm*. So player props for
  unconfirmed players are priced and tracked and **cannot produce a
  selection** — the exact analogue of goalie saves in the NHL lab.
- **Week 1 opens on a Wednesday because Thursday's game is in Australia.**
  SF @ LA on 2026-09-10 is at the Melbourne Cricket Ground, so the domestic
  opener moved to Wednesday 2026-09-09. This is recorded because it looks like
  a data error and is not one; a future session must not "correct" it back.
- **Retractable roofs are unknown before kickoff, and the `roof` column also
  lies.** It is blank for 43 of 272 2026 games — the five retractable domestic
  venues plus the Maracana and the Bernabeu — because whether the roof was open
  is a game-time fact. Worse, it is populated and **wrong** for three open-air
  international games (Stade de France, Munich, Melbourne), all labelled
  `dome`. The weather gate never keys on `roof` alone: neutral-site and
  international fixtures are roof-unknown regardless, and the domestic venue
  list is asserted in a test rather than read from the feed.
- **`nfl_data_py` is archived** (last push 2025-09-25). This lab fetches the
  nflverse release assets directly and caches them.
- **Schedule states are free and leak-free**: `home_rest`/`away_rest` are
  populated for all 272 2026 games today. 33 team-games on a short week, 30
  off a bye, and 8 neutral-site games — Melbourne, Rio, London twice, Paris,
  Madrid, Munich, Mexico City — six of them kicking off at 09:30 ET. Eight
  games is too few to measure an international effect, and the report will
  say that rather than reporting a number over eight games.

## Contract strings — never change these

Cooper's scheduled routines hard-code these. Renaming any of them silently
breaks his automation, and the breakage looks like the lab going quiet.

| Thing | Exact value |
|:------|:------------|
| Workflow name | `Football Gameday Refresh` |
| Workflow file | `.github/workflows/football-gameday-refresh.yml` |
| Card feed branch | `card-feed` |
| Operating home issue title | `Football Betting Lab — Claude Operating Home` |
| Changed-selections marker | `Selections changed` |
| Claims output | `data/outputs/nfl_what_we_can_claim.md` |
| Forward evidence output | `data/outputs/nfl_forward_evidence.md` |
| Odds API secret | `FOOTBALL_ODDS_API_KEY` |

The issue title uses an em dash (—), not a hyphen. The marker phrase is matched
literally. Every output file is league-prefixed, so NCAAF can never overwrite
an NFL record.

## Hard rules (never break these)

- **Never fabricate** odds, a line, an injury, a weather reading, or a
  player's status. A missing price stays missing.
- **Never place a bet** or automate one. Nothing here is ever wired to a
  sportsbook.
- **No market reaches the card without measurement against real prices and a
  reviewed human acceptance receipt.** Claude prepares the evidence and stops.
- **An excluded market is never a pass, an avoid, or a no-value call.** A
  blocked card yields no selections and says why.
- **State the sample size next to every measured number.** An interval that
  includes zero means **"no demonstrated edge"**, in those words.
- **Calibration can rule a model out, never in.** Where a priced test exists,
  it decides.
- **Never stake correlated selections as independent, and never sum their
  edges.** QB passing yards, WR receiving yards, team total and game total are
  one event seen four ways. Exposure is reported per game.
- **Report how much of any spread or total edge is a half-point at a key
  number.** Margins pile up on 3 and 7 and pushes are modelled exactly.
- **Before concluding a market "isn't offered", check per-bookmaker coverage
  including alternate lines** — and probe **in season**. A market unquoted in
  August establishes nothing.
- **Never print, write, compare, or commit an API key.** The production
  credential is the GitHub secret `FOOTBALL_ODDS_API_KEY`; `.env` is
  local-only and gitignored; `tests/test_no_secrets_committed.py` enforces it.
- **Never weaken a gate**, never sign a human acceptance receipt on Cooper's
  behalf, never merge with failing CI, never force-push.
- **Never spend API credits beyond a small measurement budget without asking.**
- **Never pool leagues into one number.** Fitted per league, reported per
  league, recorded per league, receipted per league.

## What Claude decides, and what Cooper decides

Claude works autonomously on: data, models, measurement, reports, tests,
workflows, docs, and opening PRs with green CI.

Claude stops and asks for exactly two things: **allowlisting a provider or a
market**, and **credit spend beyond a small measurement budget**.

## Main commands

```bash
# One-time local setup
/opt/homebrew/opt/python@3.12/bin/python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt && .venv/bin/python -m pip install -e .

# Cost arithmetic (spends nothing, touches no network)
PYTHONPATH=src .venv/bin/python scripts/estimate_credit_cost.py

# Tests
PYTHONPATH=src .venv/bin/python -m pytest -q
PYTHONPATH=src .venv/bin/python -m compileall -q src scripts
```
