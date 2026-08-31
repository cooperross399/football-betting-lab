#!/usr/bin/env python3
"""Fit the per-market calibration maps the card freezes. Spends nothing.

    PYTHONPATH=src python scripts/fit_calibration.py --before-season 2026

The model is overconfident everywhere it was measured — it says 0.861 and the
outcome lands 0.547 — and walk-forward calibration closes most of that gap
without ever crossing the market's. So this is a **forecasting improvement, not
an edge**, and the artifact it writes must never be read as one.

It is fitted before Week 1 because **a calibrated probability cannot be
back-dated.** The ledger records what was believed before kickoff. If the
calibrated number is not frozen from the first game day, the season can never be
scored on it, and the bought population is complete so there is no other source.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date

import pandas as pd

from football_betting_lab.config import OUTPUTS_DIR
from football_betting_lab.leagues import DEFAULT_LEAGUE_KEY, league_for
from football_betting_lab.models import calibration as calib
from football_betting_lab.forward_evidence import LEDGER_FILENAME
from football_betting_lab.reports.props_backtest import load_scored_bets


def _settled_forward_rows(league, *, before: str) -> pd.DataFrame:
    """Settled forward-ledger rows, shaped like scored bets.

    The ledger is the only evidence that grows, so folding it in is what makes
    the maps improve during a season rather than being fitted once in August.
    """
    path = OUTPUTS_DIR / league.output_name("forward", "") / LEDGER_FILENAME
    if not path.is_file() or not path.stat().st_size:
        return pd.DataFrame()
    ledger = pd.read_csv(path)
    needed = {"snapshot_date", "market", "model_probability", "outcome"}
    if not needed.issubset(ledger.columns):
        return pd.DataFrame()
    ledger = ledger[ledger["snapshot_date"].astype(str) < before]
    ledger = ledger[ledger["outcome"].isin(["won", "lost"])]
    if ledger.empty:
        return pd.DataFrame()
    day = ledger["snapshot_date"].astype(str)
    month = pd.to_numeric(day.str[5:7], errors="coerce")
    year = pd.to_numeric(day.str[:4], errors="coerce")
    return pd.DataFrame({
        # The league season, not the calendar year: week 18 is played in
        # January and would otherwise be filed under the following season.
        "season": (year - (month < 3).astype(int)).astype("Int64"),
        "market": ledger["market"],
        "model_probability": pd.to_numeric(
            ledger["model_probability"], errors="coerce"
        ),
        "outcome": ledger["outcome"],
    }).dropna(subset=["season", "model_probability"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", default=DEFAULT_LEAGUE_KEY)
    parser.add_argument(
        "--include-forward",
        action="store_true",
        help="Fold in settled forward-ledger rows. This is how the maps improve "
             "during a season: every settled game day is more evidence about "
             "how overconfident the model is. Only rows settled STRICTLY "
             "BEFORE today are used, so a map never sees the slate it prices.",
    )
    parser.add_argument(
        "--before-season",
        type=int,
        default=2026,
        help="Fit on seasons strictly before this one. The same walk-forward "
             "rule the rest of the lab keeps.",
    )
    args = parser.parse_args(argv)
    league = league_for(args.league)

    path = OUTPUTS_DIR / league.output_name("props_backtest_bets", ".csv")
    if not path.is_file():
        print(f"No scored bets at {path}.", file=sys.stderr)
        return 2
    bets = load_scored_bets(path)

    if args.include_forward:
        # The season's own settled rows, which is what makes this improve
        # weekly rather than being fitted once and frozen. Strictly earlier
        # than today: a map that has seen the slate it prices is not a
        # forecast, and in-season that mistake is easy to make because the
        # data arrives continuously rather than in seasons.
        forward = _settled_forward_rows(league, before=date.today().isoformat())
        if not forward.empty:
            bets = pd.concat([bets, forward], ignore_index=True)
            print(
                f"Folded in {len(forward):,} settled forward row(s) from the "
                f"current season."
            )
        else:
            print(
                "No settled forward rows yet, so the maps are the historical "
                "ones. That is an absence, not a fault, before Week 1."
            )

    fitted = calib.fit(bets, before_season=args.before_season)
    if not fitted.markets:
        print(
            f"No market had {calib.MINIMUM_ROWS} rows before {args.before_season}; "
            "nothing was written.",
            file=sys.stderr,
        )
        return 2

    target = OUTPUTS_DIR / league.output_name("calibration", ".json")
    calib.save(fitted, target)
    print(f"Fitted on {fitted.fitted_on}; {len(fitted.markets)} market(s) -> {target}\n")
    print(f"{'market':<26}{'rows':>8}   {'0.30':>6}{'0.50':>7}{'0.70':>7}{'0.90':>7}")
    print("-" * 62)
    for name, entry in sorted(fitted.markets.items()):
        row = "".join(f"{entry.apply(p):>7.3f}" for p in (0.30, 0.50, 0.70, 0.90))
        print(f"{name:<26}{entry.rows:>8,}   {row}")
    print(
        "\nEach row reads: when the model said the column heading, the outcome "
        "landed at the value.\nA well-calibrated model would return the heading "
        "back. These do not, which is the point."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
