"""What day a game belongs to, and how CSV-borne text is read.

The provider timestamps a game by kickoff, in UTC. The league timestamps it by
the day it is played. For a Sunday-night or Monday-night kickoff those are
different days — a 20:20 Eastern kickoff is 00:20 UTC the following morning —
and joining prices to results on the raw UTC date silently drops them.

The NHL lab measured what that costs when it happens: **69% of every price
bought was discarded**, and what survived was not a random sample. This module
exists so the rule lives in one place, ported before a single price is
fetched rather than after a season of them is lost.

The league's calendar timezone comes from the registry, never from a literal
here. NCAAF will use the same rule with its own zone.
"""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from football_betting_lab.leagues import League


def game_date(commence_time: object, league: League) -> str:
    """The league game date for a provider timestamp, as `YYYY-MM-DD`.

    An unparseable value falls back to its leading ten characters, which is
    the best available guess and is never silently better than the input.
    """
    text = str(commence_time or "").strip()
    if not text:
        return ""
    candidate = text.replace("Z", "+00:00")
    try:
        moment = datetime.fromisoformat(candidate)
    except ValueError:
        return text[:10]
    if moment.tzinfo is None:
        # No timezone means no conversion is possible, and inventing one would
        # move every night game by a day.
        return text[:10]
    return moment.astimezone(league.timezone).date().isoformat()


def clean_text(value: object) -> str:
    """A CSV-safe string: NaN, None and whitespace all read as empty.

    `str(x or "")` looks like it does this and does not — float NaN is truthy,
    so an empty CSV cell round-trips to the literal string `"nan"`, which then
    matches nothing, resolves nothing, and renders as a player called nan.
    Three copies of that pattern shipped in the NHL lab before its equivalent
    of this function existed, and it was the fifth member of that repository's
    join-vocabulary bug family.
    """
    if value is None:
        return ""
    if isinstance(value, float) and value != value:  # NaN without numpy
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def row_game_date(row: object, league: League) -> str:
    """The league game date for a price row: commence time, else its date.

    The fallback exists for hand-built frames; real staged rows always carry a
    commence time. `or` cannot express this, because a NaN commence time is
    truthy and `game_date(nan)` is the string "nan" — which made two fixtures
    between the same clubs on different days share one key.
    """
    commence = clean_text(getattr(row, "commence_time", ""))
    return game_date(commence or clean_text(getattr(row, "date", "")), league)


#: A complete NFL season schedule names all 32 clubs. A cache with fewer has
#: games it simply does not know about, and cannot be used to judge whether a
#: fixture is preseason.
EXPECTED_NFL_CLUBS = 32


def schedule_path(league: League, raw_dir: Path) -> Path:
    return Path(raw_dir) / league.data_dir_segment / "schedule" / "nflverse_games.csv"


def known_regular_season_games(
    league: League, raw_dir: Path, *, season: int
) -> set[tuple[str, str, str]]:
    """(game date, HOME, AWAY) for every regular-season game the cache knows.

    The odds provider does not flag preseason. Books post exhibition lines from
    early August, the models are never fitted on them — nflverse publishes no
    preseason rows at all — and an unfiltered card would freeze opinions it has
    no business holding into the forward ledger, where they would rot as
    unsettleable noise.

    Callers get the club count from `schedule_cache_is_complete` and decide.
    The failure direction has to be theirs: an incomplete cache still yields a
    plausible date range, so a screen that trusts it drops every game whose
    rows never landed — silently, as "preseason".
    """
    path = schedule_path(league, raw_dir)
    known: set[tuple[str, str, str]] = set()
    if not path.is_file():
        return known
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row.get("season") != str(season) or row.get("game_type") != "REG":
                continue
            day = str(row.get("gameday", ""))[:10]
            home = str(row.get("home_team", "")).strip().upper()
            away = str(row.get("away_team", "")).strip().upper()
            if len(day) == 10 and home and away:
                known.add((day, home, away))
    return known


def schedule_cache_is_complete(
    league: League, raw_dir: Path, *, season: int
) -> tuple[bool, int]:
    """(is complete, clubs found) for the cached schedule.

    A partial cache is not a smaller truth. It is the same truth with holes,
    and the holes are indistinguishable from exhibition games to anything that
    only asks "is this fixture in the set?".
    """
    known = known_regular_season_games(league, raw_dir, season=season)
    clubs = {team for _, home, away in known for team in (home, away)}
    return len(clubs) >= EXPECTED_NFL_CLUBS, len(clubs)
