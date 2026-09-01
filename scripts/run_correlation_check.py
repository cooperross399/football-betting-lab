#!/usr/bin/env python3
"""Is the model's joint better than its marginals? Spends nothing.

    PYTHONPATH=src python scripts/run_correlation_check.py

The marginals lose to the price on every instrument this lab has. The joint is
a different quantity, produced as a byproduct of the compound simulation, and
priced by a different and usually cruder part of a sportsbook. This measures
whether it is accurate — and refuses to claim an edge it cannot measure.
"""

from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd

from football_betting_lab.config import OUTPUTS_DIR, PROCESSED_DIR
from football_betting_lab.data.build_datasets import PLAYER_LOGS_FILENAME
from football_betting_lab.leagues import DEFAULT_LEAGUE_KEY, league_for
from football_betting_lab.models.player_props import (
    fit_rates,
    load_play_yardage,
    simulate,
)
from football_betting_lab.reports import correlation as corr
from football_betting_lab.reports.props_backtest import load_scored_bets

#: (family, opportunity, yards, longest, touchdown). The compound families,
#: which are the only ones with a joint to check.
FAMILIES = (
    ("reception", "receptions", "reception_yards", "reception_longest", "reception_tds"),
    ("rush", "rush_attempts", "rush_yards", "rush_longest", "rush_tds"),
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", default=DEFAULT_LEAGUE_KEY)
    parser.add_argument("--season", type=int, default=2025,
                        help="Held-out season. Fits use seasons before it.")
    parser.add_argument("--draws", type=int, default=400)
    parser.add_argument("--players", type=int, default=400)
    args = parser.parse_args(argv)
    league = league_for(args.league)

    logs_path = PROCESSED_DIR / PLAYER_LOGS_FILENAME
    if not logs_path.is_file():
        print(f"No player logs at {logs_path}.", file=sys.stderr)
        return 2
    logs = pd.read_csv(logs_path, low_memory=False)
    per_play = load_play_yardage(PROCESSED_DIR, before_season=args.season)

    result = corr.CorrelationResult()
    for family, opp, yds, lng, td in FAMILIES:
        table = per_play.get(family, {}) if isinstance(per_play, dict) else {}
        if not table:
            continue
        rates = fit_rates(
            logs, before=f"{args.season}01", opportunity_column=opp,
            yards_column=yds, touchdown_column=td,
        )
        played = logs[(logs["season"] == args.season) & (logs[opp] > 0)]
        if played.empty:
            continue
        drawn_o, drawn_y, drawn_l = [], [], []
        for player_id in played["player_id"].dropna().unique()[: args.players]:
            entry = rates.get(str(player_id))
            if entry is None or not entry.is_usable:
                continue
            sim = simulate(entry, table, draws=args.draws, seed=7)
            drawn_o.append(sim.opportunities)
            drawn_y.append(sim.yards)
            drawn_l.append(sim.longest)
        if not drawn_o:
            continue
        o = np.concatenate(drawn_o)
        y = np.concatenate(drawn_y)
        l = np.concatenate(drawn_l)
        for label, real_a, real_b, sim_a, sim_b in (
            (f"{opp} x {yds}", played[opp], played[yds], o, y),
            (f"{yds} x {lng}", played[yds], played[lng], y, l),
        ):
            result.checks.append(
                corr.CorrelationCheck(
                    pair=label,
                    realised=float(real_a.corr(real_b)),
                    model=float(np.corrcoef(sim_a, sim_b)[0, 1]),
                    games=len(played),
                )
            )

    bets_path = OUTPUTS_DIR / league.output_name("props_backtest_bets", ".csv")
    if bets_path.is_file():
        result.joints = corr.joint_pairs(load_scored_bets(bets_path))

    report = corr.render(result)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUTS_DIR / league.output_name("correlation_check", ".md")).write_text(
        report, encoding="utf-8"
    )
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
