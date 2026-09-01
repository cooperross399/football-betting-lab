# When each 2026 game is actually carded

Computed from the cron expressions in `.github/workflows/football-gameday-refresh.yml` and the committed schedule cache. **Nothing here is written by hand.** An earlier hand-written version of this table in `CLAUDE.md` had three of its numbers wrong, and this file exists so that cannot recur.

Crons read from the workflow, evaluated in UTC as GitHub evaluates them:

- `0 14 * 9-12,1 *`
- `30 15 * 9-12,1 *`
- `0 21 * 9-12,1 *`

**The operative run is the first firing of the league date, not the last one before kickoff.** The second cron is a backup that stands down when the first published cleanly, and the first run prices the whole day at `--horizon-days 1`. So the backup's lead is reachable only on a day the first run was degraded or dropped.

- **272** regular-season games.
- **268** are carded; **4** have no run before kickoff at all.
- **266** are carded EARLIER than a last-run-before-kickoff reading would say, because the backup stands down.
- **2** are carded inside the 90-minute inactives window.

## By kickoff slot

| kickoff ET | offset | games | operative lead | backup lead | last-run-before-kickoff |
|:--|:--|--:|--:|--:|--:|
| 13:00 | EST | 95 | 4.00h | 2.50h | 2.50h |
| 13:00 | EDT | 54 | 3.00h | 1.50h | 1.50h |
| 16:25 | EDT | 19 | 6.42h | 4.92h | 4.92h |
| 20:15 | EST | 19 | 11.25h | 9.75h | 4.25h |
| 16:25 | EST | 18 | 7.42h | 5.92h | **25 min** |
| 20:15 | EDT | 14 | 10.25h | 8.75h | 3.25h |
| 16:05 | EST | 13 | 7.08h | 5.58h | **5 min** |
| 20:20 | EST | 12 | 11.33h | 9.83h | 4.33h |
| 16:05 | EDT | 8 | 6.08h | 4.58h | 4.58h |
| 20:20 | EDT | 8 | 10.33h | 8.83h | 3.33h |
| 09:30 | EDT | 4 | — | — | — |
| 09:30 | EST | 2 | **30 min** | — | **30 min** |
| 16:30 | EST | 2 | 7.50h | 6.00h | **30 min** |
| 15:00 | EST | 1 | 6.00h | 4.50h | 4.50h |
| 17:00 | EST | 1 | 8.00h | 6.50h | **60 min** |
| 20:00 | EST | 1 | 11.00h | 9.50h | 4.00h |
| 20:35 | EDT | 1 | 10.58h | 9.08h | 3.58h |

Every slot appears once per UTC offset. A slot that spans the DST boundary is two rows because it is two different lead times, and collapsing them into one is exactly the error the hand-written table made.

## Games with no run before kickoff

The card prices these and the kickoff guard then quarantines them. That is the correct behaviour and produces no wrong answer; it is a coverage gap, not a fault.

| game | league date | kickoff ET | kickoff UTC | first run |
|:--|:--|:--|:--|:--|
| `2026_04_IND_WAS` | 2026-10-04 | 09:30 | 13:30Z | 14:00Z |
| `2026_05_PHI_JAX` | 2026-10-11 | 09:30 | 13:30Z | 14:00Z |
| `2026_06_HOU_JAX` | 2026-10-18 | 09:30 | 13:30Z | 14:00Z |
| `2026_07_PIT_NO` | 2026-10-25 | 09:30 | 13:30Z | 14:00Z |

## What a dropped first run costs

GitHub documents that scheduled workflows may be delayed or dropped entirely under load, so this is the case the backup triggers exist for. If the operative run does not publish, the next firing of the day cards the slate instead — and how much of the slate it can still reach is the whole value of the backup.

- **266** carded normally by the backup.
- **0** carded inside the 90-minute inactives window — a different population, not a rescue.
- **6** not carded at all: the backup arrives after kickoff and the guard quarantines them.

**A dropped run is not a delayed card, it is evidence that cannot be back-dated.** A backup that arrives after kickoff for most of the slate is not a backup; it is the same hope the primary trigger was not allowed to be.

## Games carded inside the inactives window

**These are the only games of the season whose card knows who is playing.** Inactives are declared about ninety minutes out. Every other game is carded blind to them, which makes these rows a different population rather than a better-informed one.

The exposure is worse than the count suggests, and not in the direction of an edge: the kickoff guard applies **no grace period**, and GitHub documents that scheduled runs may be delayed under load. A run that starts late enough quarantines these games instead of carding them, so whether they enter the ledger at all depends on the runner fleet that morning.

| game | league date | kickoff ET | kickoff UTC | lead |
|:--|:--|:--|:--|--:|
| `2026_09_CIN_ATL` | 2026-11-08 | 09:30 | 14:30Z | **30 min** |
| `2026_10_NE_DET` | 2026-11-15 | 09:30 | 14:30Z | **30 min** |

**Every game day of the season has at least one cron firing.** The crons name months rather than a date range, so this is checked rather than assumed.

## What this costs, and which way it cuts

An earlier lead is a price with **less** information in it, so the games the backup was meant to re-card are carded into a softer market than the table claimed. That is the friendlier direction for a bettor and it changes nothing about a lab with no allowlisted market — but the ledger records `commence_time` and `snapshot_date`, so the lead is recoverable per row and no future reading of the ledger has to assume a window it did not have.

The measured value of a later card is small in any case: crossing the inactives deadline buys the market **+0.00085 Brier against a 0.002 threshold declared in advance** (`nfl_inactives_value.md`, 5,275 to 22,318 wagers per market), and five hours of movement is about **0.01 in probability**. This is a correctness finding about the documentation, not a discovered cost.
