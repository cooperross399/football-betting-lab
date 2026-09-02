"""When each game is actually carded, computed from the crons rather than by hand.

`CLAUDE.md` carried a lead-time table written by hand, and three of its numbers
were wrong. This module exists so that table can never be written by hand
again: it reads the cron expressions out of the workflow file, reads the
kickoffs out of the schedule cache, and computes the answer.

## The three things the hand-written table got wrong

**It assumed ET is UTC-4 for the whole season.** The table said so explicitly -
"ET is UTC-4 in September" - and then applied that offset to all 272 games. The
season runs to 2027-01-10 and ET is UTC-5 from 2026-11-01, so every row was
wrong for its EST half. "13:00 ET, 149 games, 3.0h" is 54 games at 3.0h and 95
games at 4.0h.

**It took the last run before kickoff.** That is the wrong run. The second cron
exists as a backup and *stands down when the first published cleanly*, so under
normal operation the first run of the league date owns the whole slate - it
prices every game of the day at `--horizon-days 1`, freezes them, and publishes
a non-degraded status the backup then reads and defers to. The last run before
kickoff is what the schedule would deliver if the guard did not exist.

**It assumed every game with no run before kickoff is uncardable.** True, but
the count was six and it is four: the 09:30 ET internationals straddle the DST
boundary, and the two November ones kick at 14:30 UTC rather than 13:30, which
is *after* the 14:00 UTC run rather than before it.

## Why the third one matters more than the other two

Those two November games are carded **thirty minutes before kickoff**, which is
inside the ninety-minute inactives window. `CLAUDE.md` said "all 272 games are
carded blind to inactives" and "the closest any run gets is three hours". Both
sentences were false for two games a season.

It is a small exposure and it is not a comfortable one, because the kickoff
guard applies no grace period and GitHub documents that scheduled runs may be
delayed. Those two games are carded or quarantined depending on how loaded the
runner fleet is that morning, which is not a property a ledger should have.

## What this module refuses to guess

A cron with a restricted day-of-month or day-of-week field changes which days
fire, and getting that subtly wrong would produce a plausible table rather than
an error. `parse_workflow_crons` raises on one instead. The same reasoning as
the kickoff guard: the failure has to be loud, because the quiet version is
indistinguishable from a correct answer.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from football_betting_lab.leagues import League
from football_betting_lab.season import schedule_path


#: Every scheduled firing observed on this repository, in minutes late,
#: measured 2026-09-02 across `Football Gameday Refresh` (5), `Provider Quota`
#: (5) and `Weekly Ledger Check` (1). **None fired on time.** A cron time is
#: therefore not a lead, and any table that treats it as one is wrong in the
#: dangerous direction. Update this list when more firings accumulate; it is
#: evidence, not a constant.
OBSERVED_DELAYS_MINUTES = (115, 122, 123, 189, 199, 218, 304, 330, 343, 395, 443)

#: Inactives are declared about ninety minutes before kickoff. A card built
#: inside this window knows something every other card of the season does not,
#: which makes its rows a different population rather than a better one.
INACTIVES_LEAD_MINUTES = 90

#: Only the `schedule:` block of a workflow. A `cron` appearing in a comment or
#: in an unrelated key is not a trigger.
_SCHEDULE_BLOCK = re.compile(
    r"^\s*schedule:\s*$(?P<body>(?:\n(?:\s*#.*|\s*-\s*cron:.*|\s*))*)",
    re.MULTILINE,
)
_CRON_LINE = re.compile(r"^\s*-\s*cron:\s*[\"']?(?P<expr>[^\"'#]+?)[\"']?\s*$", re.MULTILINE)


@dataclass(frozen=True)
class Cron:
    """One cron trigger, as GitHub evaluates it: in UTC."""

    expression: str
    minutes: frozenset[int]
    hours: frozenset[int]
    months: frozenset[int]

    def fires_at(self, moment: datetime) -> bool:
        return (
            moment.month in self.months
            and moment.hour in self.hours
            and moment.minute in self.minutes
        )


def _field(raw: str, *, low: int, high: int, name: str, expression: str) -> frozenset[int]:
    """Expand one cron field. `*`, lists, ranges and steps; nothing else."""
    values: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        step = 1
        if "/" in part:
            part, _, step_text = part.partition("/")
            step = int(step_text)
        if part == "*":
            first, last = low, high
        elif "-" in part.lstrip("-"):
            first_text, _, last_text = part.partition("-")
            first, last = int(first_text), int(last_text)
        else:
            first = last = int(part)
        if first > last:
            # A wrapping range like `9-1` for months. Cron does not define one,
            # and the workflow writes `9-12,1` precisely because it does not.
            raise ValueError(
                f"The {name} field of cron {expression!r} wraps ({part!r}). "
                "Cron has no wrapping range; write it as a list."
            )
        values.update(range(first, last + 1, step))
    out_of_range = sorted(v for v in values if not low <= v <= high)
    if out_of_range:
        raise ValueError(
            f"The {name} field of cron {expression!r} yields {out_of_range}, "
            f"outside {low}-{high}."
        )
    return frozenset(values)


def parse_cron(expression: str) -> Cron:
    fields = expression.split()
    if len(fields) != 5:
        raise ValueError(
            f"Cron {expression!r} has {len(fields)} fields, not 5. This module "
            "computes when the card runs; it must not guess at that."
        )
    minute, hour, dom, month, dow = fields
    if dom.strip() != "*" or dow.strip() != "*":
        # Handling these correctly is more than this needs, and handling them
        # incorrectly produces a plausible table rather than an error.
        raise ValueError(
            f"Cron {expression!r} restricts day-of-month or day-of-week "
            f"({dom!r}, {dow!r}). This module only computes daily crons, and "
            "silently mis-answering is the failure it exists to prevent."
        )
    return Cron(
        expression=expression.strip(),
        minutes=_field(minute, low=0, high=59, name="minute", expression=expression),
        hours=_field(hour, low=0, high=23, name="hour", expression=expression),
        months=_field(month, low=1, high=12, name="month", expression=expression),
    )


def parse_workflow_crons(workflow_text: str) -> list[Cron]:
    """Every `schedule:` cron in a workflow file, in the order written.

    Read from the workflow rather than restated here, because a table that
    restates a schedule is a table that can disagree with it.
    """
    crons: list[Cron] = []
    for block in _SCHEDULE_BLOCK.finditer(workflow_text):
        for line in _CRON_LINE.finditer(block.group("body")):
            crons.append(parse_cron(line.group("expr")))
    return crons


def firings_on(league_date: date, crons: list[Cron], league: League) -> list[datetime]:
    """UTC instants that fire and whose **league date** is `league_date`.

    The workflow stamps `DAY=$(TZ=America/New_York date +%F)` in three places -
    the standdown guard, the card's own slate stamp, and the feed publish - so a
    run belongs to the league date it starts in, not to its UTC date. Those can
    differ, and a cron moved across UTC midnight would silently reassign a whole
    day of games to the day before.
    """
    found: list[datetime] = []
    for offset in (-1, 0, 1):
        day = league_date + timedelta(days=offset)
        for cron in crons:
            for hour in sorted(cron.hours):
                for minute in sorted(cron.minutes):
                    moment = datetime(
                        day.year, day.month, day.day, hour, minute, tzinfo=timezone.utc
                    )
                    if not cron.fires_at(moment):
                        continue
                    if moment.astimezone(league.timezone).date() == league_date:
                        found.append(moment)
    return sorted(set(found))


@dataclass(frozen=True)
class CardingRow:
    game_id: str
    league_date: date
    kickoff_et: str
    kickoff_utc: datetime
    offset_label: str
    #: The run that actually cards this game: the first firing of its league
    #: date, because the backup stands down when the first publishes cleanly.
    operative_lead_hours: float | None
    #: The backup's lead, reachable only when the first run is degraded or
    #: dropped. `None` when the backup does not precede kickoff either.
    fallback_lead_hours: float | None
    #: The last firing before kickoff - what the hand-written table computed.
    #: Kept so the correction is legible rather than asserted.
    naive_last_lead_hours: float | None

    @property
    def carded(self) -> bool:
        return self.operative_lead_hours is not None

    @property
    def inside_inactives(self) -> bool:
        return (
            self.operative_lead_hours is not None
            and self.operative_lead_hours * 60 < INACTIVES_LEAD_MINUTES
        )


def _kickoff(gameday: str, gametime: str, league: League) -> datetime:
    naive = datetime.fromisoformat(f"{gameday}T{gametime}:00")
    return naive.replace(tzinfo=league.timezone).astimezone(timezone.utc)


def scheduled_games(league: League, raw_dir: Path, *, season: int) -> list[dict[str, str]]:
    """Regular-season rows for one season, from the committed schedule cache."""
    path = schedule_path(league, raw_dir)
    if not path.is_file():
        raise FileNotFoundError(
            f"No cached schedule at {path}. This report is computed against the "
            "real schedule and refuses to be computed against nothing."
        )
    rows: list[dict[str, str]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row.get("season") != str(season) or row.get("game_type") != "REG":
                continue
            if len(str(row.get("gameday", ""))) < 10 or not row.get("gametime"):
                continue
            rows.append(row)
    return rows


def carding_rows(
    league: League, raw_dir: Path, *, season: int, crons: list[Cron]
) -> list[CardingRow]:
    if not crons:
        raise ValueError(
            "No crons were parsed from the workflow. A table computed from an "
            "empty schedule would report every game uncardable, which is a "
            "different claim from 'the schedule could not be read'."
        )
    out: list[CardingRow] = []
    for row in scheduled_games(league, raw_dir, season=season):
        gameday = str(row["gameday"])[:10]
        gametime = str(row["gametime"])[:5]
        kickoff = _kickoff(gameday, gametime, league)
        league_date = date.fromisoformat(gameday)
        firings = firings_on(league_date, crons, league)
        before = [t for t in firings if t < kickoff]
        first = firings[0] if firings else None

        def hours(moment: datetime | None) -> float | None:
            if moment is None or moment >= kickoff:
                return None
            return (kickoff - moment).total_seconds() / 3600

        out.append(
            CardingRow(
                game_id=str(row.get("game_id", "")),
                league_date=league_date,
                kickoff_et=gametime,
                kickoff_utc=kickoff,
                offset_label=_offset_label(kickoff, league),
                operative_lead_hours=hours(first),
                fallback_lead_hours=hours(firings[1] if len(firings) > 1 else None),
                naive_last_lead_hours=hours(before[-1] if before else None),
            )
        )
    return sorted(out, key=lambda r: (r.kickoff_utc, r.game_id))


def _offset_label(moment: datetime, league: League) -> str:
    local = moment.astimezone(league.timezone)
    name = local.tzname() or ""
    return name


def coverage_under_delay(
    rows: list[CardingRow], crons: list[Cron], league: League, delay_minutes: float
) -> tuple[int, dict[str, int]]:
    """(games still carded, games lost by kickoff slot) if every firing is late.

    The schedule is a net rather than a time, so the question is not "what is
    the lead" but "does ANY trigger still land before kickoff". A trigger that
    fires late is not a later card; past kickoff it is no card at all, and the
    ledger cannot be back-dated.
    """
    late = timedelta(minutes=delay_minutes)
    carded = 0
    lost: dict[str, int] = {}
    for row in rows:
        firings = firings_on(row.league_date, crons, league)
        if any(moment + late < row.kickoff_utc for moment in firings):
            carded += 1
        else:
            lost[row.kickoff_et] = lost.get(row.kickoff_et, 0) + 1
    return carded, lost


def days_without_any_run(rows: list[CardingRow], crons: list[Cron], league: League) -> list[date]:
    """Game days on which no cron fires at all.

    Distinct from a game the runs merely miss. The card's crons name months
    (`9-12,1`), so a schedule extending into February would go dark rather than
    late, and the symptom - a quiet day - is the same one a bye week produces.
    """
    return sorted(
        {r.league_date for r in rows if not firings_on(r.league_date, crons, league)}
    )


def _fmt(hours: float | None) -> str:
    if hours is None:
        return "—"
    if hours * 60 < 90:
        return f"**{hours * 60:.0f} min**"
    return f"{hours:.2f}h"


def render(rows: list[CardingRow], crons: list[Cron], *, season: int, league: League,
           dark_days: list[date]) -> str:
    lines: list[str] = []
    add = lines.append
    add(f"# When each {season} game is actually carded")
    add("")
    add(
        "Computed from the cron expressions in "
        "`.github/workflows/football-gameday-refresh.yml` and the committed "
        "schedule cache. **Nothing here is written by hand.** An earlier "
        "hand-written version of this table in `CLAUDE.md` had three of its "
        "numbers wrong, and this file exists so that cannot recur."
    )
    add("")
    add("Crons read from the workflow, evaluated in UTC as GitHub evaluates them:")
    add("")
    for cron in crons:
        add(f"- `{cron.expression}`")
    add("")
    add(
        "**The operative run is the first firing of the league date, not the "
        "last one before kickoff.** The second cron is a backup that stands "
        "down when the first published cleanly, and the first run prices the "
        "whole day at `--horizon-days 1`. So the backup's lead is reachable "
        "only on a day the first run was degraded or dropped."
    )
    add("")

    carded = [r for r in rows if r.carded]
    missed = [r for r in rows if not r.carded]
    inside = [r for r in rows if r.inside_inactives]
    moved = [
        r for r in rows
        if r.naive_last_lead_hours is not None
        and r.operative_lead_hours is not None
        and abs(r.naive_last_lead_hours - r.operative_lead_hours) > 1e-9
    ]

    add(f"- **{len(rows)}** regular-season games.")
    add(f"- **{len(carded)}** are carded; **{len(missed)}** have no run before kickoff at all.")
    add(
        f"- **{len(moved)}** commit EARLIER than a reading that ignores the "
        "standdown would say. That reading — take the last run before kickoff — "
        "is how the hand-written table got the night window wrong."
    )
    add(
        f"- **{len(inside)}** are carded inside the {INACTIVES_LEAD_MINUTES}-minute "
        "inactives window."
    )
    add("")

    add("## By kickoff slot")
    add("")
    add("| kickoff ET | offset | games | operative lead | backup lead | last-run-before-kickoff |")
    add("|:--|:--|--:|--:|--:|--:|")
    buckets: dict[tuple[str, str], list[CardingRow]] = {}
    for row in rows:
        buckets.setdefault((row.kickoff_et, row.offset_label), []).append(row)
    for (kickoff_et, offset), group in sorted(
        buckets.items(), key=lambda item: (-len(item[1]), item[0])
    ):
        first = group[0]
        add(
            f"| {kickoff_et} | {offset} | {len(group)} | "
            f"{_fmt(first.operative_lead_hours)} | {_fmt(first.fallback_lead_hours)} | "
            f"{_fmt(first.naive_last_lead_hours)} |"
        )
    add("")
    add(
        "Every slot appears once per UTC offset. A slot that spans the DST "
        "boundary is two rows because it is two different lead times, and "
        "collapsing them into one is exactly the error the hand-written table "
        "made."
    )
    add("")

    if missed:
        add("## Games with no run before kickoff")
        add("")
        add(
            "The card prices these and the kickoff guard then quarantines them. "
            "That is the correct behaviour and produces no wrong answer; it is "
            "a coverage gap, not a fault."
        )
        add("")
        add("| game | league date | kickoff ET | kickoff UTC | first run |")
        add("|:--|:--|:--|:--|:--|")
        for row in missed:
            firings = firings_on(row.league_date, crons, league)
            first = f"{firings[0]:%H:%M}Z" if firings else "none"
            add(
                f"| `{row.game_id}` | {row.league_date} | {row.kickoff_et} | "
                f"{row.kickoff_utc:%H:%M}Z | {first} |"
            )
        add("")

    add("## The schedule is a net, not a time")
    add("")
    add(
        "**Measured 2026-09-02: GitHub fired none of this repository's crons on "
        f"time.** {len(OBSERVED_DELAYS_MINUTES)} scheduled firings across three "
        f"workflows, delays of {min(OBSERVED_DELAYS_MINUTES)}-"
        f"{max(OBSERVED_DELAYS_MINUTES)} minutes, median "
        f"{sorted(OBSERVED_DELAYS_MINUTES)[len(OBSERVED_DELAYS_MINUTES) // 2]}. "
        "So a cron time is not a lead, and the leads in the table above are the "
        "best case rather than the expected one."
    )
    add("")
    add(
        "A late trigger is not a later card. Past kickoff the guard quarantines "
        "the game and there is no card at all — and the ledger cannot be "
        "back-dated. That is why the schedule is thirteen hourly triggers "
        "rather than a well-chosen time: whichever GitHub actually runs first "
        "cards the day, and the rest stand down for free."
    )
    add("")
    add("| delay | games carded | lost | worst slot lost |")
    add("|--:|--:|--:|:--|")
    for delay in (0, 60, 123, 189, 218, 304, 443):
        carded_n, lost = coverage_under_delay(rows, crons, league, delay)
        worst = (
            max(lost.items(), key=lambda item: item[1]) if lost else None
        )
        worst_text = f"{worst[1]} x {worst[0]} ET" if worst else "—"
        marker = "**" if delay in OBSERVED_DELAYS_MINUTES else ""
        add(
            f"| {marker}{delay} min{marker} | {carded_n} | {len(rows) - carded_n} "
            f"| {worst_text} |"
        )
    add("")
    observed_worst = max(OBSERVED_DELAYS_MINUTES)
    carded_worst, _ = coverage_under_delay(rows, crons, league, observed_worst)
    add(
        f"**At the worst delay yet observed ({observed_worst} min), "
        f"{carded_worst} of {len(rows)} games are still carded.** That is the "
        "number the net exists to hold up, and it is the one to re-check "
        "whenever the schedule is edited."
    )
    add("")

    add("## What a dropped first run costs")
    add("")
    add(
        "GitHub documents that scheduled workflows may be delayed or dropped "
        "entirely under load, so this is the case the backup triggers exist "
        "for. If the operative run does not publish, the next firing of the "
        "day cards the slate instead — and how much of the slate it can still "
        "reach is the whole value of the backup."
    )
    add("")
    rescued = [
        r for r in rows
        if r.fallback_lead_hours is not None
        and r.fallback_lead_hours * 60 >= INACTIVES_LEAD_MINUTES
    ]
    tight = [
        r for r in rows
        if r.fallback_lead_hours is not None
        and r.fallback_lead_hours * 60 < INACTIVES_LEAD_MINUTES
    ]
    unreachable = [r for r in rows if r.fallback_lead_hours is None]
    add(f"- **{len(rescued)}** carded normally by the backup.")
    add(
        f"- **{len(tight)}** carded inside the {INACTIVES_LEAD_MINUTES}-minute "
        "inactives window — a different population, not a rescue."
    )
    add(
        f"- **{len(unreachable)}** not carded at all: the backup arrives after "
        "kickoff and the guard quarantines them."
    )
    add("")
    add(
        "**A dropped run is not a delayed card, it is evidence that cannot be "
        "back-dated.** A backup that arrives after kickoff for most of the "
        "slate is not a backup; it is the same hope the primary trigger was "
        "not allowed to be."
    )
    add("")

    if inside:
        add("## Games carded inside the inactives window")
        add("")
        add(
            "**These are the only games of the season whose card knows who is "
            "playing.** Inactives are declared about ninety minutes out. Every "
            "other game is carded blind to them, which makes these rows a "
            "different population rather than a better-informed one."
        )
        add("")
        add(
            "The exposure is worse than the count suggests, and not in the "
            "direction of an edge: the kickoff guard applies **no grace "
            "period**, and GitHub documents that scheduled runs may be delayed "
            "under load. A run that starts late enough quarantines these games "
            "instead of carding them, so whether they enter the ledger at all "
            "depends on the runner fleet that morning."
        )
        add("")
        add("| game | league date | kickoff ET | kickoff UTC | lead |")
        add("|:--|:--|:--|:--|--:|")
        for row in inside:
            add(
                f"| `{row.game_id}` | {row.league_date} | {row.kickoff_et} | "
                f"{row.kickoff_utc:%H:%M}Z | {_fmt(row.operative_lead_hours)} |"
            )
        add("")

    if dark_days:
        add("## Game days on which no cron fires at all")
        add("")
        add(
            "**This is not a late run, it is no run.** The crons name months, "
            "so a schedule extending past them goes dark — and a dark day looks "
            "exactly like a bye week from the outside."
        )
        add("")
        for day in dark_days:
            add(f"- {day}")
        add("")
    else:
        add(
            "**Every game day of the season has at least one cron firing.** The "
            "crons name months rather than a date range, so this is checked "
            "rather than assumed."
        )
        add("")

    add("## What this costs, and which way it cuts")
    add("")
    add(
        "An earlier lead is a price with **less** information in it, so the "
        "games the backup was meant to re-card are carded into a softer market "
        "than the table claimed. That is the friendlier direction for a bettor "
        "and it changes nothing about a lab with no allowlisted market — but "
        "the ledger records `commence_time` and `snapshot_date`, so the lead is "
        "recoverable per row and no future reading of the ledger has to assume "
        "a window it did not have."
    )
    add("")
    add(
        "The measured value of a later card is small in any case: crossing the "
        "inactives deadline buys the market **+0.00085 Brier against a 0.002 "
        "threshold declared in advance** (`nfl_inactives_value.md`, 5,275 to "
        "22,318 wagers per market), and five hours of movement is about **0.01 "
        "in probability**. This is a correctness finding about the "
        "documentation, not a discovered cost."
    )
    return "\n".join(lines) + "\n"
