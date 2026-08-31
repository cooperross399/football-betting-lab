> **Superseded in one respect, kept for the record.** This is the brief this
> lab was built from. It scopes NCAAF as a later addition to *this*
> repository; on 2026-08-31 Cooper decided college football is a separate
> project in its own repo. `CLAUDE.md` is authoritative where the two differ.

# Football Betting Lab — build brief (NFL now, NCAAF later)

---

## How to use this file

This is the complete brief. Everything the build needs is in here; nothing
else has to be pasted.

**1. Open a new Claude Code session in the right place.** In Terminal:

```bash
cd ~/Projects && claude
```

Use Claude Code, not a claude.ai Project — this build writes files, runs git,
creates a GitHub repo, sets up Actions workflows and manages secrets, none of
which a chat project can do.

**2. Give it one line:**

> Read `~/Projects/football-betting-lab-brief.md` and follow it. Start with
> "Start here", step 1.

Point at the file rather than pasting it, so this file stays the single source
of truth and edits to it are picked up on the next read.

**3. Have these ready** (the session will ask, but it saves a round trip):

- `gh` authenticated (`gh auth status`) — it already is on this machine.
- Python 3.12 at `/opt/homebrew/opt/python@3.12/bin/python3.12`.
- **The Odds API key.** Important: this is the *same account and the same
  quota* as the NHL lab. The NHL season is measured at ~26,000 credits against
  ~88,500 remaining, so football spends what is left over — the cost
  arithmetic below must account for both labs, not just this one. Store it as
  a GitHub secret (`FOOTBALL_ODDS_API_KEY`), never in a file that gets
  committed.
- A decision from me only when the brief says to stop and ask.

**4. Expect the first answer to be a plan, not code.** Step 1 is reading and
documenting; step 3 is showing me the credit arithmetic. That is deliberate.

---

Build me a **Football Betting Lab** at `/Users/cooperross/Projects/football-betting-lab`
(GitHub `cooperross399/football-betting-lab`, private), modelled on my existing
NHL lab.

**Scope: the NFL ships first. NCAAF is added later, and the architecture is
built for it from day one** — league is a first-class dimension everywhere, so
adding college football is a new adapter and a new set of fitted models, never
a refactor. Details in "Built for a second league" below. Do not build NCAAF
now; do not build anything that would have to be torn up to add it.

## Read this first, before writing a line of code

`/Users/cooperross/Projects/nhl-betting-lab` is the reference implementation
and it works. Read its `CLAUDE.md` (especially "Current operating state"),
`docs/`, `src/`, `tests/`, and `.github/workflows/gameday-refresh.yml` before
designing anything. Port its machinery rather than reinventing it:

- the **verdicts door** (`verdicts.ships()`) — recorded, versioned decisions
  read from disk, so what ships is auditable against the experiment that
  decided it, never asserted in code;
- the **forward-evidence ledger** — freeze the card's opinions before kickoff,
  settle them against the box score afterwards, never reprice, day-as-unit;
- the **allowlist receipt + PR gate** — no market reaches the card without
  measurement against real prices and a human acceptance receipt I sign;
- the **kickoff guard** (their puck-drop guard) — a started game, or one whose
  start cannot be confirmed, is quarantined and its stake removed;
- **`selection_key()`** — one function builds every join key on both sides.
  Their bug family here reached five members and cost weeks: provider team
  names vs abbreviations, UTC dates vs league dates (69% of prices silently
  discarded), `home -1.5` vs `home_minus`, outcomes staged in the wrong
  vocabulary, and a CSV round-trip turning empty players into the string
  `"nan"`. Assume I will hit all five again if I hand-build keys twice;
- the **accounting identity** — priced = no_opinion + below_threshold +
  unparseable + ambiguous + bets, reconciled and printed every run;
- **cache staleness checks**, **shrink guards**, `tests/test_no_secrets_committed.py`;
- **delivery**: GitHub Actions publishes each card to a `card-feed` branch, and
  a scheduled cloud routine reads that branch and pushes it to me in-app. No
  email, no laptop.

Port the discipline exactly. Change the sport, not the standards.

## The runway, and what it means for build order

The NFL regular season opens the Thursday after Labor Day — verify the exact
date from the schedule rather than trusting me. That is a short runway, and it
changes the priority order in a way I want you to take seriously:

**A measured, allowlisted, betting-ready model by Week 1 is not realistic, and
I do not want you to pretend otherwise.** What *is* realistic, and what matters
far more, is having the evidence organ running before Week 1:

> Historical prices can be bought later. **Forward evidence cannot be
> back-dated.** Every week the pipeline is not freezing opinions and settling
> them is a week of clean out-of-sample data that is gone permanently.

So the build order is:

1. **Data layer + odds staging + the forward-evidence organ**, live before
   Week 1, even with a crude first model. Freeze, settle, accumulate.
2. **Preseason exclusion**, immediately — books are posting preseason lines
   right now, the models must never be fitted on them, and preseason opinions
   must never enter the ledger. The NHL lab's preseason guard is the pattern,
   including its failure direction: abstain rather than nuke a real slate.
3. Models, walk-forward calibration, price backtest on bought history.
4. Measurement, replication, family-wise correction.
5. Only then: evidence assembled for me to approve a market.

Nothing is bet in the meantime, and the card says plainly that it is
accumulating evidence rather than making recommendations.

## Built for a second league

Everything league-specific comes from a **league registry**, never a hardcoded
string: league key, provider sport key (`americanfootball_nfl`, later
`americanfootball_ncaaf`), data-source adapter, market list, roster source,
season calendar, credit caps, model parameters, verdict files, policy entries
and receipts. Pin it with a discipline test: no league literal outside the
registry.

Then these rules hold when NCAAF arrives:

- Models are **fitted per league**, measurements **reported per league**,
  verdicts **recorded per league**. Nothing is ever pooled into a headline
  number — 135 FBS teams with 40-point talent gaps and 32 near-parity NFL
  teams do not share a distribution, and a figure computed across both
  describes neither.
- A shared or hierarchical model may only ship if it is **measured** to beat
  two separate models, on the price backtest, per league.
- A policy that wins in the NFL and loses in NCAAF ships in the NFL only.
- **Adding NCAAF must not move a single NFL number.** Record the NFL
  measurements before the addition and pin them with a regression test; if
  they shift, the addition changed something it had no business touching.
- Each league carries its **own acceptance receipt and its own allowlist
  entry**. Approving a market in the NFL never approves it in NCAAF.

## Step one: sources, verified before anything is built

Do not assume the NHL's free official API has an equivalent. Investigate and
write `docs/football_data_sources.md` recording what each source can and
cannot tell us, and its licence/terms:

- **NFL (now)**: the `nflverse` / `nfl_data_py` ecosystem — play-by-play,
  rosters, depth charts, snap counts, schedules — is the leading free option.
- **NCAAF (later)**: CollegeFootballData (CFBD) is the standard free API and
  needs its own key. When that day comes, treat it exactly like the odds key:
  a secret, never printed, written, compared, or committed.
- **Odds**: The Odds API, with the same shadow-staging discipline the NHL lab
  uses — staging invisible to the card, policy JSON allowlist, PR gate, human
  receipt.

If a source cannot supply what a market needs to **settle**, that market is not
wired. Fetching prices nothing can consume spends credits on rows no join will
ever find; pricing without honest settlement manufactures evidence.

## Markets — all of them

Team markets: moneyline, spread (and the full alternate ladder), totals, team
totals, first-half and quarter lines, and the three-way where offered.

Player props, wherever quoted: passing yards, attempts, completions, TDs,
interceptions, longest completion; rushing yards, attempts, TDs, longest rush;
receiving yards, receptions, TDs, longest reception; anytime TD scorer, first
TD scorer; kicking points, field goals made; tackles + assists, sacks,
defensive interceptions; plus every alternate ladder. Probe the provider for
what it actually serves rather than guessing — and probe **in season**,
because a market unquoted in August establishes nothing.

Store **distributions**, not point estimates, so any offered line prices
exactly and every alternate rung settles identically.

## Modelling requirements — where football differs from hockey

State and justify every distribution choice, then measure it. Specifically:

- **Yards are not Poisson.** A count model is right for receptions and maybe
  carries; it is wrong for yardage, which is a compound outcome (opportunities
  × yards-per-opportunity), heavily right-skewed and zero-inflated. Model it as
  a compound/mixture or by simulation, and show the fitted distribution against
  the empirical one.
- **Key numbers.** Football margins pile up on 3 and 7. A half-point across a
  key number is worth more than anywhere in hockey. Model pushes on whole
  numbers exactly, and report how much of any claimed edge is really just a
  half-point of line value.
- **Correlation is everywhere.** QB passing yards, WR receiving yards, team
  total and game total are the same event seen four ways. Never stake
  correlated selections as independent, never sum their edges, and report
  correlation-aware exposure per game. The NHL lab could mostly ignore this;
  here it is a first-order accounting problem.
- **Usage, not just rate.** Props are opportunity-driven. A model pricing a
  receiver without his snap share and route participation is pricing last
  month's role.
- **Game script.** Leads change play-calling and blowouts empty benches. A prop
  conditioned on a game state that does not happen is a bet on the script, and
  should be reported as such.
- **Schedule states.** Short weeks, bye-week rest, and international travel are
  the analogue of the NHL's back-to-backs — where a real, measured adjustment
  was found and shipped *because it won the price backtest*, while a
  better-calibrated correction was refused because it lost. Test them the same
  way, and ship only what wins.

## The gates that fail closed

Each is the analogue of "goalie saves needs a confirmed starter" — that market
is modelled, measured, and still cannot produce a selection, because the lab
has no confirmed-starter feed. Same standard here:

1. **Availability.** Inactives land ~90 minutes before kickoff. A player prop
   priced without confirmed availability is a coin flip on whether the bet
   exists. Build a confirmed-active gate; where no feed exists, the market is
   priced and tracked but **cannot produce a selection**, and the card says so
   in those words.
2. **Depth chart / QB changes.** A backup QB invalidates the whole passing and
   receiving tree for that team. Detect it, or quarantine that game's props.
3. **Weather.** Wind above a measured threshold moves passing and kicking
   markets materially. Model it from a real source or exclude affected markets
   and say why — never silently price a 25 mph game like a dome.
4. **Roster and role staleness.** Take a player's team and role from a current
   roster and depth chart, never from his last logged game. Measured in the NHL
   lab: 20.4% of priced players changed clubs over one summer, and each one
   produced no opinion at all until that was fixed. (This gets much worse in
   NCAAF later — portal and opt-outs.)
5. **Preseason** is excluded from fitting and from the card, counted and
   stated, never silently dropped.

## Measurement discipline — the part I care most about

Be harder on yourself here than the NHL lab was, because the samples are far
smaller. The NHL season is ~1,300 games; an NFL season is 272. **One season
cannot establish an edge, and the reports must say so out loud.**

- **Walk-forward only.** A model is priced only on games strictly earlier than
  the one being scored. Same-week data never touches its own fit.
- **Price backtest decides.** Calibration can rule a model out, never in.
- **Family-wise correction** across every market tested, reported beside the
  raw figure. With this many markets something will look profitable by chance;
  assume it is until it replicates.
- **Replication on held-out seasons** before any claim survives.
- **Minimum sample thresholds per market**, declared in advance, below which
  the verdict is "not enough evidence" — not a number.
- **Closing-line value is a first-class metric.** With samples this thin, CLV
  is the fastest honest signal available: track the closing price for every
  frozen opinion and report CLV per market alongside ROI. A winning record with
  negative CLV is variance, and the report must say that in those words.
- **"Conditioned on what, known when?"** Run this test on every adjustment. The
  NHL lab found a correction worth +162.8u on *actual* ice time that lost
  −37.6u on *expected* ice time — the only version a card can use. Hindsight
  leaks look exactly like edges.
- **Sample size beside every number.** An interval that includes zero is
  reported as **"no demonstrated edge"** — in those words.

## Cost, computed before it is spent

The Odds API bills per market per event for props, and **the quota is shared
with the NHL lab** — same account, same key pool. The NHL season is measured at
~26,000 credits against ~88,500 remaining, so football spends what is left.

Before building the fetch, compute the real season cost from the actual
schedule and put the arithmetic in `CLAUDE.md`: games per week, markets asked,
credits per week, credits per season, **plus the NHL lab's committed spend**,
against the quota remaining. Then set caps that cannot starve a slate, and read
the real rate from the response headers as it is spent rather than trusting the
documentation. **A starved fetch and an unquoted market look identical** —
never let the reports confuse them.

Do the same arithmetic for NCAAF before that day arrives: a single Saturday can
carry 60–80 games, and the weekly bill dwarfs the NFL's. If the three labs
together do not fit the quota, that is a decision for me to make with the
numbers in front of me, not a surprise halfway through October.

## Honesty rules — these are absolute

- Never fabricate odds, a line, an injury, a weather reading, or a player's
  status. A missing price stays missing.
- Never place a bet. Nothing here is ever wired to a sportsbook.
- No market reaches the card without measurement against real prices **and** a
  reviewed human acceptance receipt. Prepare the evidence and stop.
- An excluded market is never reported as a pass, an avoid, or a no-value call.
  A blocked card yields no selections and says why.
- Sample sizes beside every number; intervals including zero are "no
  demonstrated edge".
- Check per-bookmaker and alternate-line coverage before concluding a market
  "isn't offered".
- **Never print, write, compare, or commit an API key.** Secrets are GitHub
  secrets; `.env` is local-only and gitignored; port the secrets test.
- **Never merge with failing CI, never force-push, never weaken a gate, and
  never sign an acceptance receipt on my behalf.**

## How you work

Work autonomously: data, models, measurement, reports, tests, workflows, docs,
and PRs with green CI. Adversarially review your own work before calling it
done — reproduce every defect before fixing it, and add a regression test for
each. Stop and ask me for exactly two things: **allowlisting a provider or
market**, and **credit spend beyond a small measurement budget**.

Python 3.12 (`/opt/homebrew/opt/python@3.12/bin/python3.12`). Keep a
`CLAUDE.md` with a "Current operating state" section that a future session can
read as project memory, and pin its contract strings with tests.

## Start here

1. Read the NHL lab end to end and write `docs/what_we_can_and_cannot_claim.md`
   **before** the first measurement, so every number lands in a place that
   already knows how to read it.
2. Investigate and document the NFL data sources, including licence terms, and
   design the league registry so NCAAF drops in later.
3. Compute the NFL season credit cost — including the NHL lab's committed
   spend against the shared quota — and show me the arithmetic.
4. Then propose the build order against the Week 1 date, tell me what you need
   from me and when, and start with the evidence organ.
