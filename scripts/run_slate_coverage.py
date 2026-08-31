#!/usr/bin/env python3
"""Is the forward ledger intact? Spends nothing.

    PYTHONPATH=src python scripts/run_slate_coverage.py --season 2026

The bought population is complete and cannot grow. The forward ledger is the
only evidence left, it accrues at 272 games a season, and it **cannot be
back-dated**. A game day that was never frozen is sample that does not exist.

This is an inventory of that asset, read against the schedule rather than
against what was fetched — a check that compares the ledger to itself reports a
day that never ran as a day that had nothing to say.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime

import pandas as pd

from football_betting_lab.config import OUTPUTS_DIR, PROCESSED_DIR
from football_betting_lab.data.build_datasets import TEAM_GAMES_FILENAME
from football_betting_lab.forward_evidence import LEDGER_FILENAME, snapshots_dir
from football_betting_lab.leagues import DEFAULT_LEAGUE_KEY, league_for
from football_betting_lab.reports import slate_coverage


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", default=DEFAULT_LEAGUE_KEY)
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--archive-dir", default="")
    parser.add_argument(
        "--as-of", default="",
        help="ISO date to judge against. Defaults to today in league time.",
    )
    args = parser.parse_args(argv)
    league = league_for(args.league)

    games_path = PROCESSED_DIR / TEAM_GAMES_FILENAME
    if not games_path.is_file():
        print(f"No team games at {games_path}.", file=sys.stderr)
        return 2
    games = pd.read_csv(games_path, low_memory=False)
    scheduled = slate_coverage.scheduled_days(games, season=args.season)
    if not scheduled:
        print(
            f"The schedule cache knows no {args.season} game days. That is an "
            "absence, not an intact ledger — fetch the schedule before "
            "believing this report.",
            file=sys.stderr,
        )
        return 2

    archive = (
        __import__("pathlib").Path(args.archive_dir)
        if args.archive_dir
        else OUTPUTS_DIR / league.output_name("forward", "")
    )
    snapshots = slate_coverage.snapshot_row_counts(snapshots_dir(archive))
    ledger_path = archive / LEDGER_FILENAME
    ledger = (
        pd.read_csv(ledger_path)
        if ledger_path.is_file() and ledger_path.stat().st_size
        else pd.DataFrame()
    )
    settled = slate_coverage.settled_row_counts(ledger)

    as_of = (
        date.fromisoformat(args.as_of)
        if args.as_of
        else datetime.now(league.zoneinfo()).date()
        if hasattr(league, "zoneinfo")
        else date.today()
    )
    result = slate_coverage.measure(
        scheduled=scheduled, snapshot_rows=snapshots,
        settled_rows=settled, as_of=as_of,
    )
    report = slate_coverage.render(result, season=args.season)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUTS_DIR / league.output_name("slate_coverage", ".md")).write_text(
        report, encoding="utf-8"
    )
    print(report)
    # A lost game day is the one failure this organ cannot survive, so it exits
    # non-zero: a workflow that reports it in a file nobody opens has not
    # reported it.
    return 1 if result.lost else 0


if __name__ == "__main__":
    raise SystemExit(main())
