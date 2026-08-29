#!/usr/bin/env python3
"""What does not knowing who will play actually cost? Spends nothing.

    PYTHONPATH=src python scripts/run_availability_cost.py --market rush_yards
"""

from __future__ import annotations

import argparse
import sys

import pandas as pd

from football_betting_lab.config import OUTPUTS_DIR, RAW_DIR
from football_betting_lab.leagues import DEFAULT_LEAGUE_KEY, league_for
from football_betting_lab.reports import availability_cost


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", default=DEFAULT_LEAGUE_KEY)
    parser.add_argument("--market", default="")
    parser.add_argument("--seasons", type=int, nargs="+", default=[2023, 2024, 2025])
    args = parser.parse_args(argv)

    league = league_for(args.league)
    bets_path = OUTPUTS_DIR / league.output_name("props_backtest_bets", ".csv")
    if not bets_path.is_file():
        print(f"No backtest bets at {bets_path}.", file=sys.stderr)
        return 2
    bets = pd.read_csv(bets_path)
    if args.market:
        bets = bets[bets["market"] == args.market]
        if bets.empty:
            print(f"No bets in `{args.market}`.", file=sys.stderr)
            return 2

    frames = []
    for season in args.seasons:
        path = RAW_DIR / league.data_dir_segment / "injuries" / f"injuries_{season}.csv"
        if path.is_file():
            frames.append(pd.read_csv(path, low_memory=False))
    if not frames:
        print("No injury reports cached.", file=sys.stderr)
        return 2
    injuries = pd.concat(frames, ignore_index=True)
    injuries = injuries[injuries["season_type"] == "REG"]
    lookup = {
        f"{name.casefold()}|{season}|{week}": (
            status if isinstance(status, str) and status.strip()
            else availability_cost.LISTED_NO_DESIGNATION
        )
        for name, season, week, status in zip(
            injuries["full_name"], injuries["season"], injuries["week"],
            injuries["report_status"],
        )
    }
    keys = (
        bets["player"].astype(str).str.casefold()
        + "|" + bets["season"].astype(str)
        + "|" + bets["week"].astype(str)
    )
    result = availability_cost.measure(bets, keys.map(lookup))
    report = availability_cost.render(result, market=args.market or "all markets")
    suffix = f"_{args.market}" if args.market else ""
    (OUTPUTS_DIR / league.output_name(f"availability_cost{suffix}", ".md")).write_text(
        report, encoding="utf-8"
    )
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
