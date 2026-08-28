#!/usr/bin/env python3
"""Screen every market for settlement disagreement. Spends nothing.

    PYTHONPATH=src python scripts/run_settlement_agreement.py

**Run this before believing any backtest result.** A settlement offset is the
one defect that survives every check a backtest can run on itself: it is
constant, so it replicates perfectly across seasons and looks exactly like a
stable edge.
"""

from __future__ import annotations

import argparse
import sys

import pandas as pd

from football_betting_lab.config import OUTPUTS_DIR, PROCESSED_DIR, RAW_DIR
from football_betting_lab.data.build_datasets import PLAYER_LOGS_FILENAME
from football_betting_lab.forward_evidence import american_to_implied
from football_betting_lab.leagues import DEFAULT_LEAGUE_KEY, league_for
from football_betting_lab.markets import MARKETS_BY_KEY, PROP_MARKETS
from football_betting_lab.providers.historical import CACHE_DIRNAME
from football_betting_lab.providers.team_names import name_to_abbreviation, resolve_team
from football_betting_lab.reports import settlement_agreement
from football_betting_lab.reports.props_backtest import (
    _game_id,
    _game_weeks,
    best_price_per_selection,
    label_snapshots,
    load_bought_prices,
)

#: Featured provider keys only. The alternate ladder is one-sided and its
#: rungs sit far from the median by design, so including it would make every
#: market look like a suspect.
FEATURED_KEYS = {m.provider_key: m.key for m in PROP_MARKETS}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", default=DEFAULT_LEAGUE_KEY)
    parser.add_argument("--seasons", type=int, nargs="+", default=[2023, 2024, 2025])
    args = parser.parse_args(argv)

    league = league_for(args.league)
    logs_path = PROCESSED_DIR / PLAYER_LOGS_FILENAME
    if not logs_path.is_file():
        print(f"No player logs at {logs_path}.", file=sys.stderr)
        return 2
    logs = pd.read_csv(logs_path, low_memory=False)
    index: dict[tuple[str, str], object] = {}
    for row in logs.itertuples():
        index.setdefault((str(row.game_id), str(row.player_name).casefold()), row)

    prices = best_price_per_selection(
        label_snapshots(
            load_bought_prices(RAW_DIR / league.data_dir_segment / CACHE_DIRNAME, league)
        )
    )
    prices = prices[prices["phase"] == "card"] if "phase" in prices.columns else prices
    prices = prices[prices["provider_key"].isin(FEATURED_KEYS)].copy()
    prices["line"] = pd.to_numeric(prices["line"], errors="coerce")
    prices = prices.dropna(subset=["line"])
    # One row per wager, not per side: a two-sided market would otherwise
    # count every outcome twice and change nothing but the sample size.
    # Both sides of each featured line, so the pair can be devigged into the
    # market's own probability of the over.
    sides = prices.pivot_table(
        index=["event_id", "market", "player", "line", "date", "home_team", "away_team"],
        columns="selection",
        values="american_odds",
        aggfunc="max",
    ).reset_index()
    if "over" not in sides.columns or "under" not in sides.columns:
        print("Featured prices do not carry both sides.", file=sys.stderr)
        return 2
    sides = sides.dropna(subset=["over", "under"])
    over_implied = sides["over"].map(american_to_implied)
    under_implied = sides["under"].map(american_to_implied)
    sides["implied_over"] = over_implied / (over_implied + under_implied)
    prices = sides

    lookup = name_to_abbreviation(league)
    rows: list[dict] = []
    for season in args.seasons:
        subset = prices[prices["date"].astype(str).str[:4] == str(season)]
        weeks = _game_weeks(logs, subset, league, season)
        for event_id, frame in subset.groupby("event_id"):
            week = weeks.get(str(event_id))
            if week is None:
                continue
            first = frame.iloc[0]
            home = resolve_team(first["home_team"], league, lookup) or ""
            away = resolve_team(first["away_team"], league, lookup) or ""
            game_id = _game_id(logs, season, week, home, away)
            for row in frame.itertuples():
                entry = index.get((game_id, str(row.player).casefold()))
                if entry is None or not hasattr(entry, row.market):
                    continue
                if MARKETS_BY_KEY.get(row.market) is None:
                    continue
                rows.append(
                    {
                        "market": row.market,
                        "line": float(row.line),
                        "actual": float(getattr(entry, row.market)),
                        "implied_over": float(row.implied_over),
                    }
                )

    result = settlement_agreement.measure(pd.DataFrame(rows))
    report = settlement_agreement.render(result)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUTS_DIR / league.output_name("settlement_agreement", ".md")).write_text(
        report, encoding="utf-8"
    )
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
