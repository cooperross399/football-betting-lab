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
from football_betting_lab.reports.props_backtest import coverage_line, load_scored_bets


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
    bets = load_scored_bets(bets_path)
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
    # Keyed on `gsis_id`, not on the spelling of a name.
    #
    # This joined `injuries["full_name"].casefold()` to `bets["player"]` until
    # 2026-09-23 — the same shape the hardening audit condemned in
    # `props_backtest.py` and that was fixed there, left in place here. It
    # misses on every suffix and punctuation variant the two feeds spell
    # differently: `Dexter Lawrence II`, `Michael Pittman Jr.`, `AJ Brown`,
    # `Cor'Dale Flott`. Measured against the bought population, 228 bets on 10
    # players were on an injury report by id and invisible by name — 34 of them
    # **Questionable**, which is the one designation that measures positive.
    #
    # And it fails OPEN. `measure` does `designations.fillna(NOT_LISTED)`, so
    # every miss lands in "not on the report" — the undesignated bucket, which
    # is precisely the population `props_selectable_when_undesignated` would
    # make selectable. A join failure here does not produce a gap; it produces
    # a player who looks unencumbered.
    #
    # `bets` has carried `player_id` since the settlement fix, so the id is
    # already on both sides and no normalisation is needed.
    lookup = {
        f"{str(gsis_id).strip()}|{season}|{week}": (
            status if isinstance(status, str) and status.strip()
            else availability_cost.LISTED_NO_DESIGNATION
        )
        for gsis_id, season, week, status in zip(
            injuries["gsis_id"], injuries["season"], injuries["week"],
            injuries["report_status"],
        )
        if str(gsis_id).strip() and str(gsis_id).strip().lower() != "nan"
    }
    if "player_id" not in bets.columns:
        print(
            "::error::the bets file has no player_id column, so the injury "
            "designation cannot be joined on identity. Re-run "
            "scripts/run_props_replication.py, which writes it.",
            file=sys.stderr,
        )
        return 2
    keys = (
        bets["player_id"].astype(str).str.strip()
        + "|" + bets["season"].astype(str)
        + "|" + bets["week"].astype(str)
    )
    result = availability_cost.measure(bets, keys.map(lookup))
    report = availability_cost.render(
        result, market=args.market or "all markets", coverage=coverage_line(bets)
    )
    suffix = f"_{args.market}" if args.market else ""
    (OUTPUTS_DIR / league.output_name(f"availability_cost{suffix}", ".md")).write_text(
        report, encoding="utf-8"
    )
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
