#!/usr/bin/env python3
"""Does the model know anything the price does not? Spends nothing.

    PYTHONPATH=src python scripts/run_forecast_skill.py

The question underneath every other instrument. If the model is not a better
forecaster than the market it bets into, no betting rule, subgroup or filter
can make it profitable — so this runs before any search for one.
"""

from __future__ import annotations

import argparse
import sys

from football_betting_lab.config import OUTPUTS_DIR
from football_betting_lab.leagues import DEFAULT_LEAGUE_KEY, league_for
from football_betting_lab.reports import forecast_skill
from football_betting_lab.reports.forecast_skill import settlement_suspects
from football_betting_lab.reports.props_backtest import coverage_line, load_scored_bets


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", default=DEFAULT_LEAGUE_KEY)
    args = parser.parse_args(argv)
    league = league_for(args.league)

    path = OUTPUTS_DIR / league.output_name("props_backtest_bets", ".csv")
    if not path.is_file():
        print(f"No scored bets at {path}.", file=sys.stderr)
        return 2
    bets = load_scored_bets(path)
    suspects = settlement_suspects(
        OUTPUTS_DIR / league.output_name("settlement_agreement", ".md")
    )
    bets = bets[
        (bets["outcome"] != "void") & (~bets["market"].isin(suspects))
    ].copy()
    print(
        f"excluding {len(suspects)} settlement suspect(s): "
        f"{', '.join(sorted(suspects)) or 'none'}",
    )
    if bets.empty:
        print("No staked bets to score.", file=sys.stderr)
        return 2

    result = forecast_skill.measure(bets)
    report = forecast_skill.render(result, bets, coverage=coverage_line(bets))
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUTS_DIR / league.output_name("forecast_skill", ".md")).write_text(
        report, encoding="utf-8"
    )
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
