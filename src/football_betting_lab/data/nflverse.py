"""Fetching and caching the nflverse release assets.

There is no free official NFL API. Everything the models are fitted on and
every settlement column comes from nflverse, a community project that scrapes,
cleans and republishes NFL data as static release assets on GitHub, under
**CC-BY-4.0**. Every report this lab publishes credits it.

`nfl_data_py` — the Python wrapper the obvious search finds — was archived on
GitHub (last push 2025-09-25). This module fetches the release assets directly
instead, which is what the NHL lab does with the NHL API and for the same
reason: **caching is not an optimisation, it is a correctness rule.** A
completed season's file is fetched once and never again, so a rebuild is
reproducible offline and cannot silently depend on when it was built.

## The one place that rule bends, and why

The NFL revises statistics. Corrections are applied between Monday and
Wednesday, and nflreadr documents that **Thursday's copy is the clean one**.
Defensive counting stats — tackles, assists, sacks — move the most.

So the current season's files are refetched, and a row settled from a
pre-correction copy is **re-settled rather than left**. `is_provisional` is
where that rule lives, so nothing has to remember it twice.

## What each feed is for

`stats_player_week` settles seventeen of the twenty tier-1 player markets on
its own: completions, attempts, passing yards and touchdowns, interceptions
thrown, carries, rushing yards and touchdowns, receptions, receiving yards and
touchdowns, field goals, extra points, solo tackles, tackle assists, sacks and
defensive interceptions. Anytime-touchdown settles from it too, by summing the
touchdowns a player actually **scored** — rushing, receiving, return and
defensive — which is not `passing_tds`, a column that counts touchdowns
*thrown*. Reading that one wrong would credit every scoring drive to the
quarterback.

`pbp` is needed for exactly what a weekly aggregate cannot hold: the **maximum**
of a per-play quantity (longest completion, longest rush, longest reception),
the ordering of touchdowns (first and last scorer), and anything split by
quarter or half. Those are the only reasons to pay for a season of play-by-play.

`rosters`, `weekly_rosters` and `depth_charts` decide a player's club and role
**now**, never from his last logged game. `injuries` is the availability gate's
only feed and cannot confirm, only exclude. `snap_counts` is the usage signal.

`participation` is the matchup half, and the player props model has no opponent
term at all without it. Per play it carries man or zone, the coverage shell
(`COVER_0` through `COVER_9`, `2_MAN`, `COMBO`), the number of pass rushers,
whether the quarterback was pressured, time to throw, the route run and both
personnel groupings. **Its coverage columns are populated on dropbacks only** —
22,055 of 45,184 rows in 2025 — so a 49% fill rate is this feed working, not
this feed broken. Anything computed from it is a rate per dropback, never per
play, or it understates by half. Charting begins in 2016.

The four `pfr_*` feeds are Pro Football Reference's weekly advanced splits,
from 2018. `pfr_pass` is the pressure a quarterback faced — blitzed, hurried,
hit, pressured, sacked, bad throws. `pfr_def` is what an individual defender
allowed in coverage — targets, completions, yards, passer rating, average depth
of target, yards after catch — and is the defender-level half of a receiving
matchup. `pfr_rec` and `pfr_rush` carry drops, passer rating when targeted,
broken tackles, and yards before and after contact.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

from football_betting_lab.leagues import League


NFLVERSE_BASE = "https://github.com/nflverse/nflverse-data/releases/download"

#: Only this host. The URL is built here, never passed in, so a caller cannot
#: point the fetcher somewhere else.
ALLOWED_HOST = "github.com"

ATTRIBUTION = (
    "Game, play-by-play, participation charting, roster, depth chart, snap "
    "count, advanced split and injury data from nflverse "
    "(https://github.com/nflverse/nflverse-data), used under CC-BY-4.0."
)

MANIFEST_FILENAME = "nflverse_manifest.json"


@dataclass(frozen=True)
class Feed:
    """One nflverse release asset, and what this lab uses it for."""

    name: str
    release: str
    #: `{season}` is substituted when the feed is published per season.
    filename: str
    purpose: str
    #: Feeds published once for all seasons rather than one file per season.
    per_season: bool = True
    #: Updated year-round rather than only in season, so a cached copy goes
    #: stale even in August.
    updates_year_round: bool = False
    #: The earliest season nflverse publishes this feed for, when it does not
    #: reach back as far as the rest. `None` means "no known floor".
    first_season: int | None = None
    #: Whether nflverse publishes this feed once, after the post-season, rather
    #: than through the year. Measured 2026-09-07 from the release assets:
    #: `pbp_participation_2025.csv` was created 2026-02-10 and never updated,
    #: and the four `advstats_week_*_2025.csv` on 2026-02-11.
    #:
    #: A feed like this can only ever supply the PRIOR season during a live
    #: one. It cannot see a coordinator change, a personnel change, or any
    #: in-season adaptation, and nothing built on it may be described as
    #: current-season form.
    published_after_the_season: bool = False
    #: Whether the gameday card path needs this feed. A research feed is
    #: fetched by the script that studies it, not on a path with a kickoff
    #: deadline — `participation` alone is 47 MB a season.
    #:
    #: The default is `True` on purpose, and the direction matters: a new feed
    #: the card needs but nobody flagged gets fetched anyway, while a new
    #: research feed merely costs a download until someone marks it. The other
    #: default would make the card quietly short of data, which is the failure
    #: this lab keeps finding and the one nobody notices.
    needed_for_the_card: bool = True

    def covers(self, season: int | None) -> bool:
        """Whether nflverse publishes this feed for `season` at all.

        Deliberately not a fetch. A feed charted from 2016 returning HTTP 404
        for 2015 is, in a failure count, indistinguishable from the same feed
        404ing for 2024 because a release was renamed — and those two mean
        opposite things. Asking first is what keeps the second one loud.
        """
        if season is None or self.first_season is None:
            return True
        return season >= self.first_season

    def resolve(self, season: int | None = None) -> str:
        return self.filename.format(season=season)

    def url(self, season: int | None = None) -> str:
        return f"{NFLVERSE_BASE}/{self.release}/{self.resolve(season)}"


FEEDS: tuple[Feed, ...] = (
    Feed(
        name="schedules",
        release="schedules",
        filename="games.csv",
        purpose=(
            "Every game 1999 onwards: kickoff, teams, result, rest days, roof, "
            "venue, and the closing spread, total and both moneylines — which "
            "is a free historical price series for the team markets, back "
            "further than any purchase can reach."
        ),
        per_season=False,
        updates_year_round=True,
    ),
    Feed(
        name="player_stats",
        release="stats_player",
        filename="stats_player_week_{season}.csv",
        purpose=(
            "Weekly player box statistics. Settles seventeen of the twenty "
            "tier-1 player markets without touching play-by-play."
        ),
    ),
    Feed(
        name="pbp",
        release="pbp",
        filename="play_by_play_{season}.csv.gz",
        purpose=(
            "Play-by-play. Needed only for what a weekly aggregate cannot "
            "hold: per-play maxima (longest completion, rush, reception), "
            "touchdown ordering, and quarter and half splits."
        ),
    ),
    Feed(
        name="rosters",
        release="rosters",
        filename="roster_{season}.csv",
        purpose="A player's current club. Never his last logged game's club.",
        updates_year_round=True,
    ),
    Feed(
        name="weekly_rosters",
        release="weekly_rosters",
        filename="roster_weekly_{season}.csv",
        purpose="Club and status by week, for walk-forward role history.",
    ),
    Feed(
        name="depth_charts",
        release="depth_charts",
        filename="depth_charts_{season}.csv",
        purpose=(
            "Role, timestamped rather than week-assigned from 2025 onward. "
            "The quarterback-change gate reads this."
        ),
        updates_year_round=True,
    ),
    Feed(
        name="injuries",
        release="injuries",
        filename="injuries_{season}.csv",
        purpose=(
            "The weekly injury report. The availability gate's only feed: it "
            "can exclude a player listed Out and can never confirm one active."
        ),
    ),
    Feed(
        name="snap_counts",
        release="snap_counts",
        filename="snap_counts_{season}.csv",
        purpose="Snap share, from Pro Football Reference. The usage signal.",
    ),
    Feed(
        name="players",
        release="players",
        filename="players.csv",
        per_season=False,
        updates_year_round=True,
        needed_for_the_card=False,
        purpose=(
            "The identifier crosswalk. Pro Football Reference's advanced "
            "splits are keyed by PFR's own player id and every other feed "
            "here by GSIS, so without this the two cannot be joined at all."
        ),
    ),
    Feed(
        name="participation",
        published_after_the_season=True,
        needed_for_the_card=False,
        release="pbp_participation",
        filename="pbp_participation_{season}.csv",
        first_season=2016,
        purpose=(
            "Per-play charting: man or zone, the coverage shell, pass rushers, "
            "pressure, time to throw, route and personnel. Coverage columns "
            "are on dropbacks only, so rates from it are per dropback."
        ),
    ),
    Feed(
        name="pfr_pass",
        published_after_the_season=True,
        needed_for_the_card=False,
        release="pfr_advstats",
        filename="advstats_week_pass_{season}.csv",
        first_season=2018,
        purpose=(
            "Weekly passing detail: times blitzed, hurried, hit, pressured "
            "and sacked, and bad throws. The quarterback's environment."
        ),
    ),
    Feed(
        name="pfr_rec",
        published_after_the_season=True,
        needed_for_the_card=False,
        release="pfr_advstats",
        filename="advstats_week_rec_{season}.csv",
        first_season=2018,
        purpose=(
            "Weekly receiving detail: drops, passer rating when targeted, "
            "broken tackles."
        ),
    ),
    Feed(
        name="pfr_rush",
        published_after_the_season=True,
        needed_for_the_card=False,
        release="pfr_advstats",
        filename="advstats_week_rush_{season}.csv",
        first_season=2018,
        purpose=(
            "Weekly rushing detail: yards before and after contact, and "
            "broken tackles."
        ),
    ),
    Feed(
        name="pfr_def",
        published_after_the_season=True,
        needed_for_the_card=False,
        release="pfr_advstats",
        filename="advstats_week_def_{season}.csv",
        first_season=2018,
        purpose=(
            "Weekly coverage detail per defender: targets, completions and "
            "yards allowed, passer rating allowed, average depth of target, "
            "yards after catch. The defender half of a receiving matchup."
        ),
    ),
)

FEEDS_BY_NAME: dict[str, Feed] = {feed.name: feed for feed in FEEDS}


class FetchError(RuntimeError):
    """A feed could not be fetched. Nothing partial is ever left behind."""


Requester = Callable[..., Any]


def _default_requester(url: str, *, timeout: float) -> Any:
    return requests.get(url, timeout=timeout, stream=True)


def feed_path(feed: Feed, league: League, raw_dir: Path, season: int | None) -> Path:
    return Path(raw_dir) / league.data_dir_segment / feed.name / feed.resolve(season)


def is_provisional(game_day: str, *, as_of: date) -> bool:
    """Whether a game's statistics may still be revised.

    The NFL applies stat corrections between Monday and Wednesday, and
    nflreadr documents Thursday's copy as the clean one. So a game is
    provisional until the Thursday **after** it was played.

    This is not a rounding detail. Defensive counting stats — the settlement
    columns for `tackles_assists`, `sacks` and `solo_tackles` — move the most,
    and a bet settled from a Monday copy and never revisited would be settled
    against a number the league itself later disagreed with.
    """
    try:
        played = date.fromisoformat(str(game_day)[:10])
    except ValueError:
        # An unparseable date cannot be shown to be final, and "cannot be
        # shown final" is the same as provisional everywhere else here.
        return True
    # Thursday is weekday 3. The first Thursday strictly after the game.
    days_ahead = (3 - played.weekday()) % 7 or 7
    return as_of < played + timedelta(days=days_ahead)


def season_is_complete(season: int, *, today: date) -> bool:
    """Whether a season's files can be treated as final.

    A season is over once its playoffs are, which is comfortably before March.
    Being conservative costs one refetch; being wrong the other way freezes a
    half-finished season into the cache forever.
    """
    return today >= date(season + 1, 3, 1)


def fetch_feed(
    feed: Feed,
    league: League,
    *,
    raw_dir: Path,
    season: int | None = None,
    today: date | None = None,
    refresh: bool = False,
    requester: Requester | None = None,
    timeout_seconds: float = 180.0,
) -> tuple[Path, str]:
    """Fetch one feed into the cache. Returns `(path, what happened)`.

    Writes to a temporary file and renames, so an interrupted fetch can never
    leave a truncated CSV that parses into a smaller, plausible dataset.
    """
    moment = today or date.today()
    target = feed_path(feed, league, raw_dir, season)
    if target.is_file() and not refresh:
        if season is not None and season_is_complete(season, today=moment):
            return target, "cached (season complete, never refetched)"
        if not feed.updates_year_round and season is None:
            return target, "cached"
    url = feed.url(season)
    get = requester or _default_requester
    try:
        response = get(url, timeout=timeout_seconds)
    except (requests.RequestException, OSError, TimeoutError) as exc:
        raise FetchError(
            f"{feed.name} could not be fetched ({type(exc).__name__}). "
            "Nothing was written."
        ) from exc
    status = int(getattr(response, "status_code", 0) or 0)
    if status != 200:
        raise FetchError(
            f"{feed.name} returned HTTP {status or 'unknown'} from nflverse. "
            "Nothing was written."
        )

    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix + ".partial")
    try:
        with partial.open("wb") as handle:
            content = getattr(response, "raw", None)
            if content is not None and hasattr(content, "read"):
                shutil.copyfileobj(content, handle)
            else:
                handle.write(getattr(response, "content", b"") or b"")
        if partial.stat().st_size == 0:
            raise FetchError(
                f"{feed.name} returned an empty body. Nothing was written."
            )
        partial.replace(target)
    finally:
        partial.unlink(missing_ok=True)
    return target, "fetched"


def read_manifest(league: League, raw_dir: Path) -> dict[str, Any]:
    path = Path(raw_dir) / league.data_dir_segment / MANIFEST_FILENAME
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _cached_file_is_gone(entry: Any, *, raw_dir: Path) -> bool:
    """Whether an entry carried forward names a file no longer in the cache.

    Absence has to be SHOWN. An entry that carries no usable path is kept,
    because "cannot be checked" and "is not there" are different facts — the
    same rule `is_provisional` applies to a date it cannot parse.
    """
    if not isinstance(entry, Mapping):
        return False
    relative = entry.get("path")
    if not isinstance(relative, str) or not relative:
        return False
    try:
        return not (Path(raw_dir) / relative).is_file()
    except OSError:
        return False


def write_manifest(
    league: League, raw_dir: Path, entries: Mapping[str, Any], *, fetched_at: str
) -> Path:
    """Record what was fetched and when, MERGED per feed-season.

    A cache with no manifest cannot answer "how old is this?", and a report
    built on data of unknown age is a report whose staleness is invisible —
    which is the shape every silent-shortfall bug in these labs has taken.

    NO RUN IS THE WHOLE CACHE, and this used to set `"feeds"` to the entries of
    the run that called it. `--only schedules` fetches one feed and leaves
    thirty other cached files where they were; `--card-only` fetches eight and
    leaves the five research feeds — 47 MB a season of `participation` among
    them — untouched on disk. Writing a run's entries wholesale dropped every
    feed it had not asked for, so the file whose stated job is the sentence
    above answered *nothing at all* for most of the cache. Measured before this
    merged: a full run of `player_stats` and `pbp` for 2022 followed by `--only
    player_stats` left a manifest naming `player_stats 2022` alone, with
    `pbp 2022` still cached and still readable. And because
    `data/raw/nfl/nflverse_manifest.json` is TRACKED in a checkout several
    sessions share, the truncated copy is committable by a session that never
    ran a fetch.

    So entries merge per feed-season, and each carries its OWN `fetched_at`.
    A feed refetched today is dated today; a feed last fetched in August still
    says August, because carrying an entry forward with today's date would be
    worse than dropping it — a month-old file would read as fetched this
    morning and nothing downstream could tell. The top-level `fetched_at` is
    unchanged and still means what `staleness_hours` has always read it as:
    when a fetch last ran.

    The rule has two halves. The manifest may not forget a feed that is cached,
    and it may not remember one that is not — a carried entry whose file is no
    longer under `raw_dir` is dropped, on the showable-absence rule above.
    """
    path = Path(raw_dir) / league.data_dir_segment / MANIFEST_FILENAME
    previous = read_manifest(league, raw_dir)
    carried_feeds = previous.get("feeds")
    # Every entry in the manifest as committed predates per-feed stamps, and
    # each was written by the run whose top-level stamp it sits under. That is
    # the true date for them; leaving them bare would make the per-feed
    # question unanswerable for the whole existing cache.
    carried_at = str(previous.get("fetched_at", "")) or None

    feeds: dict[str, Any] = {}
    if isinstance(carried_feeds, Mapping):
        for label, entry in carried_feeds.items():
            if _cached_file_is_gone(entry, raw_dir=raw_dir):
                continue
            if isinstance(entry, Mapping) and carried_at and "fetched_at" not in entry:
                entry = {**entry, "fetched_at": carried_at}
            feeds[str(label)] = entry
    for label, entry in entries.items():
        # Per feed-season, not per field: a refetched entry replaces its
        # predecessor whole, so a `bytes` this run did not measure cannot
        # survive as though it had.
        feeds[str(label)] = (
            {**entry, "fetched_at": fetched_at} if isinstance(entry, Mapping) else entry
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "league": league.key,
        "fetched_at": fetched_at,
        "attribution": ATTRIBUTION,
        "feeds": feeds,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _hours_since(stamp: Any, *, now: datetime) -> float | None:
    """Hours between an ISO stamp and `now`, or None when it says nothing."""
    try:
        moment = datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
    except ValueError:
        return None
    if moment.tzinfo is None:
        return None
    return (now.astimezone(timezone.utc) - moment).total_seconds() / 3600.0


def staleness_hours(
    league: League,
    raw_dir: Path,
    *,
    now: datetime,
    feed_season: str | None = None,
) -> float | None:
    """How old the cache is, or None when it has never been fetched.

    None is not zero, and callers must not treat it as such. "Never fetched"
    and "fetched a moment ago" are opposite conditions.

    `feed_season` asks the narrower question, of one manifest label —
    `"pbp 2025"`, or `"schedules"` for a feed published once for all seasons.
    Since `write_manifest` merges, these are DIFFERENT questions after a
    partial run: `--only schedules` leaves the cache written moments ago and
    `pbp 2025` a month old, and only the per-feed answer says so. A label the
    manifest does not carry is None for the same reason the whole cache is —
    it was never fetched, which is not the same as fresh, and falling back to
    the cache's own stamp would blur exactly that.
    """
    manifest = read_manifest(league, raw_dir)
    if feed_season is None:
        return _hours_since(manifest.get("fetched_at", ""), now=now)
    feeds = manifest.get("feeds")
    entry = feeds.get(feed_season) if isinstance(feeds, Mapping) else None
    if not isinstance(entry, Mapping):
        return None
    return _hours_since(entry.get("fetched_at", ""), now=now)
