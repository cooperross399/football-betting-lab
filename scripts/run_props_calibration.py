#!/usr/bin/env python3
"""Measure whether the prop distributions are the right shape. Spends nothing.

    PYTHONPATH=src python scripts/run_props_calibration.py

Calibration can rule a model out and can never rule one in. See
`docs/what_we_can_and_cannot_claim.md`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from football_betting_lab.config import OUTPUTS_DIR, PROCESSED_DIR
from football_betting_lab.data.build_datasets import PLAYER_LOGS_FILENAME
from football_betting_lab.leagues import DEFAULT_LEAGUE_KEY, league_for
from football_betting_lab.reports import props_calibration


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", default=DEFAULT_LEAGUE_KEY)
    parser.add_argument("--fit-before", type=int, default=2025)
    parser.add_argument("--score-season", type=int, default=2025)
    parser.add_argument("--sample", type=int, default=1500)
    parser.add_argument("--processed-dir", type=Path, default=PROCESSED_DIR)
    args = parser.parse_args(argv)

    league = league_for(args.league)
    path = args.processed_dir / PLAYER_LOGS_FILENAME
    if not path.is_file():
        print(f"No player logs at {path}. Run build_datasets first.", file=sys.stderr)
        return 2
    logs = pd.read_csv(path, low_memory=False)

    results = props_calibration.calibrate(
        logs,
        args.processed_dir,
        fit_before=args.fit_before,
        score_season=args.score_season,
        sample=args.sample,
    )
    report = props_calibration.render(
        results, fit_before=args.fit_before, score_season=args.score_season
    )
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUTS_DIR / league.output_name("props_calibration", ".md")).write_text(
        report, encoding="utf-8"
    )
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
