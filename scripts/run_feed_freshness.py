#!/usr/bin/env python3
"""Can the card hold an opinion today? Spends nothing, touches no network.

    PYTHONPATH=src python scripts/run_feed_freshness.py --season 2026

A stale feed does not fail. It answers with last week's truth, the card prices
it, and the forward ledger — which is never revised — keeps the wrong opinion.
Graded on content rather than file age, because a file rewritten this morning
with last week's rows is stale and its timestamp says fresh.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from football_betting_lab.config import OUTPUTS_DIR, PROCESSED_DIR, RAW_DIR
from football_betting_lab.data.build_datasets import TEAM_GAMES_FILENAME
from football_betting_lab.leagues import DEFAULT_LEAGUE_KEY, league_for
from football_betting_lab.reports import feed_freshness as ff

#: Each feed, what it must contain, and what a stale copy would cost. The
#: consequence is stated per feed because "refresh the feeds" is not an
#: instruction anyone can act on at 07:00 on a game day.
FEEDS = (
    ("rosters", "roster_{season}.csv", True,
     "a player priced against the club he left; every one of his rows voids"),
    ("weekly_rosters", "roster_weekly_{season}.csv", True,
     "inactives unseen, so a player who did not dress is priced as playing"),
    ("depth_charts", "depth_charts_{season}.csv", True,
     "QB1 unknown, so the passing and receiving tree cannot be quarantined"),
    ("injuries", "injuries_{season}.csv", False,
     "the availability gate reads every player as undesignated"),
    ("snap_counts", "snap_counts_{season}.csv", False,
     "role is fitted from volume alone, with no check on who was on the field"),
    ("player_stats", "stats_player_week_{season}.csv", False,
     "nothing settles: yesterday's frozen opinions stay unsettleable"),
)


def _week_and_clubs(path: Path) -> tuple[int | None, int]:
    try:
        frame = pd.read_csv(path, low_memory=False)
    except (OSError, pd.errors.EmptyDataError, pd.errors.ParserError):
        return None, 0
    week = None
    if "week" in frame.columns:
        weeks = pd.to_numeric(frame["week"], errors="coerce").dropna()
        week = int(weeks.max()) if len(weeks) else None
    clubs = 0
    for column in ("team", "club_code", "recent_team", "team_abbr"):
        if column in frame.columns:
            clubs = int(frame[column].astype(str).str.strip().nunique())
            break
    return week, clubs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", default=DEFAULT_LEAGUE_KEY)
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--as-of", default="")
    args = parser.parse_args(argv)
    league = league_for(args.league)

    as_of = date.fromisoformat(args.as_of) if args.as_of else date.today()
    games_path = PROCESSED_DIR / TEAM_GAMES_FILENAME
    # Game date -> season week. The week number is what a feed's own `week`
    # column can be compared against; a count of game days cannot.
    day_to_week: dict[str, int] = {}
    if games_path.is_file():
        games = pd.read_csv(games_path, low_memory=False)
        games = games[games["season"].astype(int) == int(args.season)]
        for day, wk in zip(games["game_date"].astype(str).str[:10], games["week"]):
            if len(day) == 10:
                day_to_week[day] = max(day_to_week.get(day, 0), int(wk))
    week = ff.expected_week(day_to_week, as_of)
    season_started = week is not None
    expected_clubs = len(league.club_abbreviations()) if hasattr(
        league, "club_abbreviations"
    ) else 32

    result = ff.FreshnessResult(as_of=as_of.isoformat(), week=week)
    for name, template, needs_clubs, consequence in FEEDS:
        path = RAW_DIR / league.data_dir_segment / name / template.format(
            season=args.season
        )
        present = path.is_file()
        reaches, clubs = _week_and_clubs(path) if present else (None, 0)
        result.feeds.append(
            ff.FeedState(
                name=name,
                consequence=consequence,
                present=present,
                covers_season=present,
                reaches_week=reaches,
                expected_week=week,
                clubs=clubs,
                expected_clubs=expected_clubs if needs_clubs else 0,
                # Before Week 1 a weekly feed has nothing to publish. Reading
                # that as staleness would block every preseason run.
                due=season_started,
            )
        )

    report = ff.render(result)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUTS_DIR / league.output_name("feed_freshness", ".md")).write_text(
        report, encoding="utf-8"
    )
    print(report)
    return 1 if result.blocking else 0


if __name__ == "__main__":
    raise SystemExit(main())
