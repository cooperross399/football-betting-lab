#!/usr/bin/env python3
"""What is knowing the inactives worth? Spends nothing.

    PYTHONPATH=src python scripts/run_inactives_value.py

The availability gate rests on a premise nobody measured: that the card, running
three hours out, gives up something real by not knowing who is playing. This
lab bought the evidence — a T-60 snapshot, inside the ninety-minute deadline —
and then labelled it `mid` and read it nowhere.
"""

from __future__ import annotations

import argparse
import sys

import pandas as pd

from football_betting_lab.config import OUTPUTS_DIR, RAW_DIR
from football_betting_lab.leagues import DEFAULT_LEAGUE_KEY, league_for
from football_betting_lab.providers.historical import CACHE_DIRNAME
from football_betting_lab.reports import inactives_value as iv
from football_betting_lab.reports.props_backtest import (
    CARD_TIME,
    MID,
    best_price_per_selection,
    label_snapshots,
    load_bought_prices,
    load_scored_bets,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", default=DEFAULT_LEAGUE_KEY)
    args = parser.parse_args(argv)
    league = league_for(args.league)

    cache = RAW_DIR / league.data_dir_segment / CACHE_DIRNAME
    if not cache.is_dir():
        print(f"No bought prices at {cache}.", file=sys.stderr)
        return 2
    prices = label_snapshots(load_bought_prices(cache, league))
    early = best_price_per_selection(prices[prices["phase"] == CARD_TIME])
    late = best_price_per_selection(prices[prices["phase"] == MID])
    if late.empty:
        print(
            "No T-60 snapshot in the cache, so the gate's premise cannot be "
            "measured here. That is an absence, not a confirmation.",
            file=sys.stderr,
        )
        return 2

    bets_path = OUTPUTS_DIR / league.output_name("props_backtest_bets", ".csv")
    if not bets_path.is_file():
        print(f"No scored bets at {bets_path}.", file=sys.stderr)
        return 2
    outcomes = load_scored_bets(bets_path)
    for frame in (early, late, outcomes):
        frame["line"] = pd.to_numeric(frame["line"], errors="coerce")

    keys = ["event_id", "market", "player", "selection", "line"]
    matched = early[keys].merge(late[keys], on=keys, how="inner")
    dropped = max(len(early) - len(matched), 0)

    result = iv.measure(early, late, outcomes)
    report = iv.render(result, dropped=dropped)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUTS_DIR / league.output_name("inactives_value", ".md")).write_text(
        report, encoding="utf-8"
    )
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
