# Where every number comes from, and what it cannot tell us

Verified by fetching each source on **2026-08-28**, not assumed. Where a
source was probed and found absent, that is recorded as an absence with its
date, because "the source does not have this" and "we looked in the wrong
place" have looked identical before and the second one cost the NHL lab a
market for a season.

## The headline: there is no free official NFL API equivalent to `api-web.nhle.com`

The NHL lab is built on a public, keyless, unlimited official API. **The NFL
has no such thing.** Everything below comes from the nflverse project, which
is a community effort that scrapes, cleans and republishes NFL data as static
release assets on GitHub.

That difference has three consequences the lab has to live with:

1. **The data arrives on nflverse's schedule, not the NFL's.** Update cadences
   are documented per feed below and are checked at run time, never assumed.
2. **A feed can stop.** nflverse's own participation feed already did — its
   NGS source died mid-2023 season. A run that finds a feed stale must fail
   closed, not carry on with old numbers.
3. **Attribution is required.** The data is CC-BY-4.0.

## nflverse — the primary source

**Licence: Creative Commons Attribution 4.0 International** (verified from the
`nflverse/nflverse-data` repository metadata, 2026-08-28). Permissive, with
attribution required. Every report this lab publishes credits nflverse.

**Access: the release assets directly over HTTPS**, at
`https://github.com/nflverse/nflverse-data/releases/download/{tag}/{file}`.
CSV, parquet, rds and qs are published for most feeds.

> **`nfl_data_py` is archived.** The Python wrapper the brief names as the
> leading option was archived on GitHub, last pushed 2025-09-25 (verified
> 2026-08-28). This lab does **not** depend on it. It fetches the release
> assets itself and caches them, which is what the NHL lab does with the NHL
> API and for the same reason: a cached completed game never changes, so a
> rebuild is reproducible offline and cannot silently depend on when it ran.

### What each feed carries, when it updates, and whether 2026 exists yet

Update cadences are quoted from nflreadr's own data-schedule article; the 2026
column was probed by HTTP on 2026-08-28.

| Feed (release tag) | What it carries | Updates | 2026 present? |
|:-------------------|:----------------|:--------|:--------------|
| `schedules` | Every game 1999-2026: date, kickoff, teams, result, rest days, roof, surface, stadium, referee, starting QBs, **and closing spread / total / moneyline** | **every 5 minutes** in season | **Yes** — 272 REG games, last updated 2026-08-28 10:36 EDT |
| `pbp` | Play-by-play, 1999- . The settlement source for nearly every market | nightly after each game day, plus in-day updates; raw JSON within ~15 min of a game ending; **Thursday's copy is the clean one**, after the NFL's Mon-Wed stat corrections | No — no games played |
| `stats_player` / `stats_team` | Computed player and team box stats, incl. defensive | same schedule as pbp | No |
| `rosters` / `weekly_rosters` | Club, position, depth-chart position, status, jersey, ids | daily 07:00 UTC | **Yes** |
| `depth_charts` | Depth chart by position, **timestamped** (`dt`) rather than week-assigned from 2025 onward | daily 07:00 UTC, **year-round** | **Yes** |
| `snap_counts` | Per-game offensive / defensive / special-teams snaps and share, from Pro Football Reference | 0, 6, 12, 18 UTC in season | No — no games played |
| `injuries` | Weekly injury report: `report_status`, `practice_status`, primary and secondary injury | in season | **No** — first reports land in Week 1's practice week |
| `pfr_advstats` | PFR advanced passing / rushing / receiving / defence | daily 07:00 UTC in season | No |
| `nextgen_stats` | NGS weekly passing / rushing / receiving | nightly 03:00-05:00 ET in season | No |
| `pbp_participation` | Personnel and **route participation** | **post-season only — does not update during the season** | n/a |
| `players` | Player registry: ids across every source, names, birth dates | continuous | Yes |

### The three things this table says that matter most

**Route participation is not available in season.** From 2023 the
participation feed comes from FTN and is published only after all post-season
games are complete. So a live card can use **snap share** (PFR, updated in
season, lagged to completed games) and **target share** (derivable from
play-by-play, same lag) — but not routes run. The brief asks for a model that
knows a receiver's "snap share and route participation"; it can have the first
and it cannot have the second, and no report will imply otherwise.

**The schedule file carries a free historical price series.** `spread_line`,
`total_line`, `home_moneyline` and `away_moneyline` are complete for every
2024 and 2025 regular-season game (272/272 each), and **112 of the 272 2026
games are already lined**. This is a genuine priced test for the team model,
free, and it will be used.

Its limits are equally real and are stated everywhere it is used: it is **one
consensus closing line**, not a book quote; there is **no alternate ladder**,
no per-book variation, no half or quarter lines, and **no props**. It can
measure the team model against the close. It cannot answer "what price was
actually available", and it cannot measure a prop at all.

**Weather is not in this file for a game that has not been played.** `temp` and
`wind` are populated for 173 of 272 2024 games and 177 of 272 in 2025 —
outdoor games only, and not all of them — and for **0 of 272** 2026 games. It
is a record of conditions, not a forecast. See the weather gate below.

## The Odds API — prices only, never results

Sport key `americanfootball_nfl`. Later, `americanfootball_ncaaf`. The only
source of prices and the only source that costs anything. It is **never** a
source of results: settlement always comes from nflverse play-by-play, so a
provider outage can never change what a bet did.

Billing, from the provider's own documentation (fetched 2026-08-28):

| Endpoint | Cost |
|:---------|:-----|
| `/v4/sports` | free |
| `/v4/sports/{sport}/events` | free |
| `/v4/sports/{sport}/odds` (bulk) | `markets x regions` |
| `/v4/sports/{sport}/events/{id}/odds` | `unique markets **returned** x regions` |
| `/v4/sports/{sport}/scores?daysFrom=N` | 2 |
| any `/v4/historical/...` equivalent | **10x** the live rate |

Because the per-event endpoint bills only markets that come back, an
asked-for market nobody quotes costs nothing — which is why the alternate
ladders are carried year-round rather than written off. The cap is still
enforced against the pessimistic bound, because a cap that trusts the
optimistic one is not a cap. Full arithmetic in `docs/credit_cost.md`.

**Historical player props, alternate lines and period markets exist only after
2023-05-03.** Before that date the historical endpoints serve featured markets
only.

### What the provider documents for the NFL

Fetched from the provider's market documentation on 2026-08-28. **The NFL and
NCAAF share one market list** — the documentation heads it "NFL, NCAAF, CFL
Player Props API" — which is a real argument for the league registry and not
for a second market table.

- **Featured (bulk):** `h2h`, `spreads`, `totals`.
- **Additional (per event):** `alternate_spreads`, `alternate_totals`,
  `team_totals`, `alternate_team_totals`, `h2h_3_way`.
- **Period (per event):** moneyline, 3-way, spread, total and team total, each
  in first-half, second-half and Q1-Q4 variants, plus alternate ladders for
  each. 53 per-event team markets in total.
- **Player props (per event):** 32 keys, plus 26 `_alternate` ladders.

That is **111 per-event markets**. Every one of them is either wired in
`src/football_betting_lab/markets.py` with the nflverse quantity it settles
against, or listed in that module's `DEFERRED_MARKETS` with its reason.

**Documented is not quoted.** This list is what the provider says it serves.
What books actually hang for a given NFL game must be probed **in season** —
a market unquoted in August establishes nothing — and per bookmaker,
including the alternate ladders. The `total_2_5` lesson from the EPL lab is
the standing reason.

## Settlement: what nflverse can and cannot settle

The good news, and it is a real difference from hockey: **play-by-play settles
almost everything.**

| Market family | Settles from | Confidence |
|:--------------|:-------------|:-----------|
| Moneyline, spread, total, team total | final score | exact |
| Half and quarter versions of all of the above | scoring plays filtered by `qtr` | exact |
| The tie (`h2h_3_way`) | final score; NFL regular-season games do end level | exact |
| Passing / rushing / receiving yards, attempts, completions, TDs, INTs, receptions | play-by-play sums | exact |
| Longest completion / rush / reception | per-play maximum | exact |
| Anytime / first / last touchdown scorer | play-by-play, **including ordering** | exact |
| Kicking points, field goals, PATs | play-by-play kick results | exact |
| Tackles + assists, solo tackles, sacks, defensive interceptions | `stats_player` defensive columns | exact, but **subject to the NFL's Mon-Wed stat corrections** |

The last row is the one that needs care. Defensive counting stats are revised
after the fact more than any other family. Settlement therefore reads the
**Thursday** copy of the week's data, which nflreadr documents as the clean
one, and a row settled from a pre-correction copy is re-settled, never left.

Nothing here needs a market this lab cannot settle. That is why the wired list
is large and the deferred list is short — the opposite of the NHL lab, where
periods and goal ordering were genuinely unsettleable.

## The gates that fail closed, and which feed each one depends on

### 1. Availability — no feed publishes inactives

Inactives are declared about ninety minutes before kickoff. **nflverse
publishes no inactives feed.** What it publishes is the weekly **injury
report**: `report_status` (Out / Doubtful / Questionable) and
`practice_status`, filed Wednesday to Friday.

That is enough to *exclude* and not enough to *confirm*:

- A player whose latest report status is **Out** is excluded. Definitive.
- A player who is **Questionable** or unlisted is **not confirmed active**.

So player props are priced and tracked for those players and **cannot produce
a selection**, and the card says so in those words. This is the exact analogue
of goalie saves in the NHL lab: modelled, measured, and structurally unable to
reach a card until a confirmed-availability source exists.

If a legitimate inactives source is found later, this gate opens and the
change is judged by the priced test, not by whether it feels better.

### 2. Depth chart and quarterback changes

A backup quarterback invalidates the whole passing and receiving tree for that
team. `depth_charts` updates daily at 07:00 UTC year-round and is
**timestamped rather than week-assigned from 2025 onward**, so the current
chart is readable at card time. A quarterback change against the last fitted
state quarantines that game's props rather than repricing them from a role the
model no longer believes.

### 3. Weather — and the retractable-roof problem

There is no weather in nflverse for an unplayed game. So either an external
forecast source is wired, or wind-sensitive markets (passing, kicking, totals)
are excluded on outdoor games and the card says why. **Never silently price a
25 mph game like a dome.**

There is a second, sharper problem the data surfaced. For the 2026 season,
`roof` is blank for **43 of 272 games**, and they are not random: they are the
retractable-roof venues — State Farm, NRG, Lucas Oil, Mercedes-Benz, AT&T —
plus the two European neutral sites. nflverse leaves `roof` blank until the
game is played **because whether the roof was open is a game-time fact**.

So a weather gate cannot ask "is this a dome?" and get an answer for those
five venues before kickoff. They are treated as **roof unknown**, which falls
on the excluded side, the same way an unconfirmed start time falls on the
not-a-play side.

### 4. Roster and role staleness

A player's club and role come from the **current roster and depth chart**,
never from his last logged game. The NHL lab measured this: 166 of 815 priced
players (20.4%) had changed clubs over one summer, and each produced no
opinion at all until it was fixed — a fifth of the pool missing on opening
night, looking exactly like books not posting props. `rosters` and
`weekly_rosters` update daily and 2026 is already published.

### 5. Preseason

**The models can never be fitted on preseason, because nflverse does not
publish it.** The schedule file carries `REG` and `POST` only; there are no
`PRE` rows at all. Fitting is safe by construction.

The card is not. Books post preseason lines from early August, and the
provider does not flag them. So the card screens every priced game against the
**known regular-season schedule** — the direct analogue of the NHL lab's
`known_regular_season_games()`, including its failure direction: an incomplete
schedule cache must **abstain**, not silently reclassify a real slate as
preseason. Preseason games are counted and stated, never quietly dropped.

### 6. Schedule states — free, leak-free, and already in the file

`home_rest` and `away_rest` are populated for all 272 2026 games before a snap
is played. For 2026 that gives, without any modelling: **33 team-games on a
short week** (four days' rest or fewer), **30 coming off a bye** (thirteen or
more), and **8 neutral-site games**, two of them in Europe.

These are the analogue of the NHL's back-to-backs, where a measured adjustment
shipped *because it won the priced test* while a better-calibrated correction
was refused *because it lost*. They will be tested the same way and shipped
only if they win.

## NCAAF — later, and what will need checking then

Not built now. When it is:

- **CollegeFootballData (CFBD)** is the standard free API and **requires its
  own key**. That key is treated exactly like the odds key: a GitHub secret,
  never printed, written, compared, or committed.
- The provider serves NCAAF from the same 32 prop keys and the same period
  ladder as the NFL, so the market registry is largely reusable — but **what
  books actually quote for a Group of Five game on a Tuesday night is a
  different question entirely** and must be probed, not inherited.
- The credit arithmetic must be redone first. A single Saturday can carry
  sixty to eighty games; see `docs/credit_cost.md` for why that does not fit
  the current quota alongside two existing labs.
- Roster churn is far worse than the NFL's — the transfer portal and opt-outs
  — so gate 4 gets stricter, not looser.

## Sources deliberately not used

| Source | Why not |
|:-------|:--------|
| `nfl_data_py` | Archived on GitHub (last push 2025-09-25). The release assets it wrapped are fetched directly instead. |
| ESPN / NFL.com undocumented endpoints | No licence, no stability guarantee, and no attribution path. If a confirmed-inactives feed can only come from here, that is a decision for Cooper with the terms in front of him — not something to start scraping. |
| Any paid data vendor | None is subscribed. |
