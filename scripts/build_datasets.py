#!/usr/bin/env python3
"""Rebuild the processed tables from the cached nflverse feeds. Spends nothing.

    PYTHONPATH=src python scripts/build_datasets.py --seasons 2022 2023 2024 2025

Derived data: every raw feed is cached and these rebuild from it, so a defect
found in the build is fixed by re-running rather than by re-fetching.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from football_betting_lab.config import PROCESSED_DIR, RAW_DIR
from football_betting_lab.data.build_datasets import build
from football_betting_lab.leagues import DEFAULT_LEAGUE_KEY, league_for


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", default=DEFAULT_LEAGUE_KEY)
    parser.add_argument("--seasons", type=int, nargs="+", required=True)
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--processed-dir", type=Path, default=PROCESSED_DIR)
    parser.add_argument(
        "--allow-shrink",
        action="store_true",
        help="Permit a table to lose more than half its rows. Deliberate only.",
    )
    args = parser.parse_args(argv)

    report = build(
        league_for(args.league),
        raw_dir=args.raw_dir,
        processed_dir=args.processed_dir,
        seasons=tuple(args.seasons),
        allow_shrink=args.allow_shrink,
    )
    print(report.summary_line())
    for note in report.notes:
        print(f"  note: {note}")
    for refusal in report.refused:
        print(f"  REFUSED: {refusal}", file=sys.stderr)
    return 1 if report.refused else 0


if __name__ == "__main__":
    raise SystemExit(main())
