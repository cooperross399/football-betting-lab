# When each 2026 game is actually carded

Computed from the cron expressions in `.github/workflows/football-gameday-refresh.yml` and the committed schedule cache. **Nothing here is written by hand.** An earlier hand-written version of this table in `CLAUDE.md` had three of its numbers wrong, and this file exists so that cannot recur.

Crons read from the workflow, evaluated in UTC as GitHub evaluates them:

- `0 9 * 9-12,1 *`
- `0 10 * 9-12,1 *`
- `0 11 * 9-12,1 *`
- `0 12 * 9-12,1 *`
- `0 13 * 9-12,1 *`
- `0 14 * 9-12,1 *`
- `0 15 * 9-12,1 *`
- `0 16 * 9-12,1 *`
- `0 17 * 9-12,1 *`
- `0 18 * 9-12,1 *`
- `0 19 * 9-12,1 *`
- `0 20 * 9-12,1 *`
- `0 21 * 9-12,1 *`

**The operative run is the first firing of the league date, not the last one before kickoff.** The second cron is a backup that stands down when the first published cleanly, and the first run prices the whole day at `--horizon-days 1`. So the backup's lead is reachable only on a day the first run was degraded or dropped.

- **272** regular-season games.
- **272** are carded; **0** have no run before kickoff at all.
- **272** commit EARLIER than a reading that ignores the standdown would say. That reading — take the last run before kickoff — is how the hand-written table got the night window wrong.
- **0** are carded inside the 90-minute inactives window.

## By kickoff slot

| kickoff ET | offset | games | operative lead | backup lead | last-run-before-kickoff |
|:--|:--|--:|--:|--:|--:|
| 13:00 | EST | 95 | 9.00h | 8.00h | **60 min** |
| 13:00 | EDT | 54 | 8.00h | 7.00h | **60 min** |
| 16:25 | EDT | 19 | 11.42h | 10.42h | **25 min** |
| 20:15 | EST | 19 | 16.25h | 15.25h | 4.25h |
| 16:25 | EST | 18 | 12.42h | 11.42h | **25 min** |
| 20:15 | EDT | 14 | 15.25h | 14.25h | 3.25h |
| 16:05 | EST | 13 | 12.08h | 11.08h | **5 min** |
| 20:20 | EST | 12 | 16.33h | 15.33h | 4.33h |
| 16:05 | EDT | 8 | 11.08h | 10.08h | **5 min** |
| 20:20 | EDT | 8 | 15.33h | 14.33h | 3.33h |
| 09:30 | EDT | 4 | 4.50h | 3.50h | **30 min** |
| 09:30 | EST | 2 | 5.50h | 4.50h | **30 min** |
| 16:30 | EST | 2 | 12.50h | 11.50h | **30 min** |
| 15:00 | EST | 1 | 11.00h | 10.00h | **60 min** |
| 17:00 | EST | 1 | 13.00h | 12.00h | **60 min** |
| 20:00 | EST | 1 | 16.00h | 15.00h | 4.00h |
| 20:35 | EDT | 1 | 15.58h | 14.58h | 3.58h |

Every slot appears once per UTC offset. A slot that spans the DST boundary is two rows because it is two different lead times, and collapsing them into one is exactly the error the hand-written table made.

## The schedule is a net, not a time

**Measured 2026-09-02: GitHub fired none of this repository's crons on time.** 11 scheduled firings across three workflows, delays of 115-443 minutes, median 218. So a cron time is not a lead, and the leads in the table above are the best case rather than the expected one.

A late trigger is not a later card. Past kickoff the guard quarantines the game and there is no card at all — and the ledger cannot be back-dated. That is why the schedule is thirteen hourly triggers rather than a well-chosen time: whichever GitHub actually runs first cards the day, and the rest stand down for free.

| delay | games carded | lost | worst slot lost |
|--:|--:|--:|:--|
| 0 min | 272 | 0 | — |
| 60 min | 272 | 0 | — |
| **123 min** | 272 | 0 | — |
| **189 min** | 272 | 0 | — |
| **218 min** | 272 | 0 | — |
| **304 min** | 268 | 4 | 4 x 09:30 ET |
| **443 min** | 266 | 6 | 6 x 09:30 ET |

**At the worst delay yet observed (443 min), 266 of 272 games are still carded.** That is the number the net exists to hold up, and it is the one to re-check whenever the schedule is edited.

## What a dropped first run costs

GitHub documents that scheduled workflows may be delayed or dropped entirely under load, so this is the case the backup triggers exist for. If the operative run does not publish, the next firing of the day cards the slate instead — and how much of the slate it can still reach is the whole value of the backup.

- **272** carded normally by the backup.
- **0** carded inside the 90-minute inactives window — a different population, not a rescue.
- **0** not carded at all: the backup arrives after kickoff and the guard quarantines them.

**A dropped run is not a delayed card, it is evidence that cannot be back-dated.** A backup that arrives after kickoff for most of the slate is not a backup; it is the same hope the primary trigger was not allowed to be.

**Every game day of the season has at least one cron firing.** The crons name months rather than a date range, so this is checked rather than assumed.

## What this costs, and which way it cuts

An earlier lead is a price with **less** information in it, so the games the backup was meant to re-card are carded into a softer market than the table claimed. That is the friendlier direction for a bettor and it changes nothing about a lab with no allowlisted market — but the ledger records `commence_time` and `snapshot_date`, so the lead is recoverable per row and no future reading of the ledger has to assume a window it did not have.

The measured value of a later card is small in any case: crossing the inactives deadline buys the market **+0.00085 Brier against a 0.002 threshold declared in advance** (`nfl_inactives_value.md`, 5,275 to 22,318 wagers per market), and five hours of movement is about **0.01 in probability**. This is a correctness finding about the documentation, not a discovered cost.
