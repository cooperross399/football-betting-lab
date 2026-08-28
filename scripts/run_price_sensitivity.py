#!/usr/bin/env python3
"""Does the measured edge survive at a price you could actually get? Free.

    PYTHONPATH=src python scripts/run_price_sensitivity.py

A number that exists only as the maximum of thirteen quotes is a different
thing from a disagreement with the market, and only one of them is a strategy.
"""

from __future__ import annotations

import argparse
import sys

import pandas as pd

from football_betting_lab.config import OUTPUTS_DIR, RAW_DIR
from football_betting_lab.leagues import DEFAULT_LEAGUE_KEY, league_for
from football_betting_lab.providers.historical import CACHE_DIRNAME
from football_betting_lab.reports import price_sensitivity
from football_betting_lab.reports.props_backtest import label_snapshots, load_bought_prices


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", default=DEFAULT_LEAGUE_KEY)
    args = parser.parse_args(argv)

    league = league_for(args.league)
    bets_path = OUTPUTS_DIR / league.output_name("props_backtest_bets", ".csv")
    if not bets_path.is_file():
        print(f"No backtest bets at {bets_path}.", file=sys.stderr)
        return 2
    bets = pd.read_csv(bets_path)
    prices = label_snapshots(
        load_bought_prices(RAW_DIR / league.data_dir_segment / CACHE_DIRNAME, league)
    )
    prices = prices[prices["phase"] == "card"]

    results = price_sensitivity.measure(bets, prices)
    report = price_sensitivity.render(results)
    (OUTPUTS_DIR / league.output_name("price_sensitivity", ".md")).write_text(
        report, encoding="utf-8"
    )
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
