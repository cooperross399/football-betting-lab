#!/usr/bin/env python3
"""What the accumulated forward ledger supports. Spends nothing.

    PYTHONPATH=src python scripts/run_forward_evidence.py

The ledger is the only evidence this lab can still gather — the bought
population is complete — so it is also the only place a mistake in reading it
compounds for a season. Every instrument the historical work earned is applied
here: settlement suspects are excluded by name, intervals are clustered by
game, and an interval including zero is "no demonstrated edge" in those words.
"""

from __future__ import annotations

import argparse
import sys

import pandas as pd

from football_betting_lab.config import OUTPUTS_DIR, PROCESSED_DIR
from football_betting_lab.forward_evidence import LEDGER_FILENAME, render_ledger
from football_betting_lab.leagues import DEFAULT_LEAGUE_KEY, league_for


def settlement_suspects(league) -> frozenset[str]:
    """Read the screen's own output, so the two cannot drift apart."""
    path = OUTPUTS_DIR / league.output_name("settlement_agreement", ".md")
    if not path.is_file():
        return frozenset()
    found = {
        line.split("`")[1]
        for line in path.read_text(encoding="utf-8").splitlines()
        if "settlement suspect" in line and line.startswith("| `")
    }
    return frozenset(found)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", default=DEFAULT_LEAGUE_KEY)
    args = parser.parse_args(argv)
    league = league_for(args.league)

    path = PROCESSED_DIR / LEDGER_FILENAME
    ledger = (
        pd.read_csv(path, low_memory=False) if path.is_file() else pd.DataFrame()
    )
    report = render_ledger(
        ledger, league, settlement_suspects=settlement_suspects(league)
    )
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUTS_DIR / league.output_name("forward_evidence", ".md")).write_text(
        report, encoding="utf-8"
    )
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
