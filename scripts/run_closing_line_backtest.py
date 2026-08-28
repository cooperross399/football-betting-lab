#!/usr/bin/env python3
"""Measure the team model against the closing line. Free, spends nothing.

    PYTHONPATH=src python scripts/run_closing_line_backtest.py

Where a priced test exists, it decides. This is the first one this lab has.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from football_betting_lab.config import MIN_EDGE, OUTPUTS_DIR, PROCESSED_DIR
from football_betting_lab.data.build_datasets import TEAM_GAMES_FILENAME
from football_betting_lab.leagues import DEFAULT_LEAGUE_KEY, league_for
from football_betting_lab.reports import closing_line_backtest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", default=DEFAULT_LEAGUE_KEY)
    parser.add_argument("--seasons", type=int, nargs="+", default=list(range(2016, 2026)))
    parser.add_argument("--min-edge", type=float, default=MIN_EDGE)
    parser.add_argument("--games", type=Path, default=None)
    args = parser.parse_args(argv)

    league = league_for(args.league)
    path = args.games or (PROCESSED_DIR / TEAM_GAMES_FILENAME)
    if not path.is_file():
        print(f"No team games at {path}.", file=sys.stderr)
        return 2
    games = pd.read_csv(path, low_memory=False)

    result = closing_line_backtest.run(
        games, seasons=tuple(args.seasons), min_edge=args.min_edge
    )
    report = closing_line_backtest.render(result)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUTS_DIR / league.output_name("closing_line_backtest", ".md")).write_text(
        report, encoding="utf-8"
    )
    if not result.bets.empty:
        result.bets.to_csv(
            OUTPUTS_DIR / league.output_name("closing_line_bets", ".csv"), index=False
        )
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
