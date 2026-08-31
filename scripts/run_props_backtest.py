#!/usr/bin/env python3
"""Measure the prop models against the bought historical prices. Spends nothing.

    PYTHONPATH=src python scripts/run_props_backtest.py --season 2025

The prices are already paid for; this only reads the cache. Where a priced
test exists, it decides.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from football_betting_lab.config import OUTPUTS_DIR, PROCESSED_DIR, RAW_DIR
from football_betting_lab.data.build_datasets import PLAYER_LOGS_FILENAME
from football_betting_lab.leagues import DEFAULT_LEAGUE_KEY, league_for
from football_betting_lab.providers.historical import CACHE_DIRNAME
from football_betting_lab.reports import props_backtest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", default=DEFAULT_LEAGUE_KEY)
    parser.add_argument("--season", type=int, default=2025)
    parser.add_argument("--draws", type=int, default=8000)
    args = parser.parse_args(argv)

    league = league_for(args.league)
    cache = RAW_DIR / league.data_dir_segment / CACHE_DIRNAME
    if not cache.is_dir():
        print(f"No bought prices at {cache}.", file=sys.stderr)
        return 2
    logs_path = PROCESSED_DIR / PLAYER_LOGS_FILENAME
    if not logs_path.is_file():
        print(f"No player logs at {logs_path}.", file=sys.stderr)
        return 2

    prices = props_backtest.load_bought_prices(cache, league)
    logs = pd.read_csv(logs_path, low_memory=False)
    result = props_backtest.run(
        prices,
        logs,
        league,
        season=args.season,
        raw_dir=RAW_DIR,
        processed_dir=PROCESSED_DIR,
        draws=args.draws,
    )
    report = props_backtest.render(result)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUTS_DIR / league.output_name("props_backtest", ".md")).write_text(
        report, encoding="utf-8"
    )
    if not result.bets.empty:
        # Season-scoped, and never the pooled filename. This script scores ONE
        # season; the pooled `props_backtest_bets.csv` that four downstream
        # reports read is written only by run_props_replication.py, which
        # scores every season. They used to share a filename, so running this
        # one last replaced three seasons of evidence with one and every
        # downstream report carried on under its three-season heading.
        result.bets.assign(season=args.season).to_csv(
            OUTPUTS_DIR
            / league.output_name(f"props_backtest_bets_{args.season}", ".csv"),
            index=False,
        )
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
