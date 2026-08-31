#!/usr/bin/env python3
"""Closing-line value on every bought bet. Spends nothing.

    PYTHONPATH=src python scripts/run_clv.py

Needs both snapshots: the card-time price a bet was placed at, and the close
it is judged against.
"""

from __future__ import annotations

import argparse
import sys

import pandas as pd

from football_betting_lab.config import OUTPUTS_DIR, RAW_DIR
from football_betting_lab.leagues import DEFAULT_LEAGUE_KEY, league_for
from football_betting_lab.providers.historical import CACHE_DIRNAME
from football_betting_lab.reports import clv
from football_betting_lab.reports.props_backtest import (
    load_bought_prices,
    load_scored_bets,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", default=DEFAULT_LEAGUE_KEY)
    args = parser.parse_args(argv)

    league = league_for(args.league)
    bets_path = OUTPUTS_DIR / league.output_name("props_backtest_bets", ".csv")
    if not bets_path.is_file():
        print(f"No backtest bets at {bets_path}.", file=sys.stderr)
        return 2
    bets = load_scored_bets(bets_path)
    prices = load_bought_prices(RAW_DIR / league.data_dir_segment / CACHE_DIRNAME, league)

    result = clv.measure(bets, prices)
    report = clv.render(result)
    (OUTPUTS_DIR / league.output_name("clv", ".md")).write_text(report, encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
