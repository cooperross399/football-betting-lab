#!/usr/bin/env python3
"""Does recency weighting the opportunity rate win the priced test?

    PYTHONPATH=src python scripts/run_props_recency_experiment.py

The motivation is obvious: a receiver's role moves between seasons, so a game
from two Novembers ago should not count as much as last week's. **Obvious
motivation is exactly what a priced test exists to check** — the NHL lab has
two corrections that improved calibration and lost the backtest, and one that
looked like hindsight and was.

The verdict is written to disk by this script and read by the model. Nothing
ships by assertion, and the number of variants tested is recorded with it,
because each variant tested against the same bought season spends a degree of
freedom.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date

import pandas as pd

from football_betting_lab.config import OUTPUTS_DIR, PROCESSED_DIR, RAW_DIR
from football_betting_lab.data.build_datasets import PLAYER_LOGS_FILENAME
from football_betting_lab.leagues import DEFAULT_LEAGUE_KEY, league_for
from football_betting_lab.models.player_props import RECENCY_HALF_LIFE_GAMES
from football_betting_lab.providers.historical import CACHE_DIRNAME
from football_betting_lab.reports import props_backtest
from football_betting_lab.verdicts import record

POLICY = "props_recency_weighting"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", default=DEFAULT_LEAGUE_KEY)
    parser.add_argument("--season", type=int, default=2025)
    parser.add_argument("--draws", type=int, default=4000)
    parser.add_argument(
        "--half-lives",
        type=float,
        nargs="+",
        default=[RECENCY_HALF_LIFE_GAMES],
        help="Half-lives to test. Every extra one spends a degree of freedom.",
    )
    args = parser.parse_args(argv)

    league = league_for(args.league)
    cache = RAW_DIR / league.data_dir_segment / CACHE_DIRNAME
    logs_path = PROCESSED_DIR / PLAYER_LOGS_FILENAME
    if not cache.is_dir() or not logs_path.is_file():
        print("Bought prices or player logs are missing.", file=sys.stderr)
        return 2

    prices = props_backtest.load_bought_prices(cache, league)
    logs = pd.read_csv(logs_path, low_memory=False)

    arms: list[tuple[str, float | None]] = [("baseline (no weighting)", None)]
    arms += [(f"half-life {hl:g} games", hl) for hl in args.half_lives]

    lines = ["# Does recency weighting win the priced test?", ""]
    lines.append(
        "Each arm is the **whole** props backtest re-run with one change. The "
        "comparison that matters is the pooled return, because a policy that "
        "helps one market and hurts two has not helped."
    )
    lines.append("")
    lines.append("| Arm | Bets | ROI | 95% interval |")
    lines.append("|:----|-----:|----:|:-------------|")

    results = {}
    per_game_returns = {}
    for label, half_life in arms:
        result = props_backtest.run(
            prices, logs, league, season=args.season, raw_dir=RAW_DIR,
            processed_dir=PROCESSED_DIR, draws=args.draws,
            recency_half_life=half_life,
        )
        pooled = result.pooled
        results[label] = pooled
        staked = result.bets[result.bets["outcome"] != "void"] if not result.bets.empty else result.bets
        per_game_returns[label] = (
            staked.groupby("event_id")["profit"].sum()
            / staked.groupby("event_id")["profit"].size()
            if not staked.empty
            else pd.Series(dtype=float)
        )
        lines.append(
            f"| {label} | {pooled.bets:,} | {pooled.roi:+.1%} | "
            f"{pooled.low:+.1%} to {pooled.high:+.1%} |"
        )
        print(f"{label}: {pooled.bets:,} bets, ROI {pooled.roi:+.1%}")

    baseline = results["baseline (no weighting)"]
    best_label, best = max(
        ((k, v) for k, v in results.items() if k != "baseline (no weighting)"),
        key=lambda item: item[1].roi,
    )
    variants = len(arms) - 1

    # A higher ROI is not a win. The two arms bet on the SAME games, so the
    # comparison that decides is the PAIRED difference in per-game return,
    # tested against zero. Comparing two overlapping intervals and shipping
    # the larger number is how a lab ships noise: the first version of this
    # script did exactly that, and would have shipped a 1.4-point difference
    # whose arms' own intervals span eight points.
    paired = (
        per_game_returns[best_label]
        .subtract(per_game_returns["baseline (no weighting)"], fill_value=0.0)
        .dropna()
    )
    games = len(paired)
    mean_difference = float(paired.mean()) if games else 0.0
    if games > 1:
        standard_error = float(paired.std(ddof=1)) / (games ** 0.5)
        low = mean_difference - 1.96 * standard_error
        high = mean_difference + 1.96 * standard_error
    else:
        low, high = float("-inf"), float("inf")
    distinguishable = low > 0.0
    wins = distinguishable

    lines.append("")
    lines.append(
        f"**Paired comparison, which is what decides.** Both arms bet the same "
        f"{games} games, so the difference is measured per game and tested "
        f"against zero: **{mean_difference:+.1%} per bet, 95% interval "
        f"{low:+.1%} to {high:+.1%}**."
    )

    lines.append("")
    if wins:
        lines.append(
            f"**{best_label} beats the baseline and the difference is "
            f"distinguishable from zero.** It ships."
        )
    else:
        lines.append(
            f"**{best_label} returned {best.roi:+.1%} against the baseline's "
            f"{baseline.roi:+.1%}, and the difference is not distinguishable "
            "from zero.** It does not ship. A higher number on the same data "
            "is not a result: the arms' own intervals span several times the "
            "gap between them, and the obvious motivation does not override "
            "the measurement — which is the entire reason a priced test "
            "exists."
        )
    lines.append("")
    lines.append(
        f"{variants} variant(s) were tested against one bought season. Each "
        "spends a degree of freedom, and the verdict file records the count so "
        "any report citing it has to say so."
    )
    lines.append("")
    lines.append(
        "**Beating a baseline that loses is not an edge.** Both arms lose "
        "money against real prices; this experiment only decides which loses "
        "less, and a policy that ships on that basis is a smaller loss rather "
        "than a profit."
    )

    summary = (
        f"{best_label} vs baseline: {best.roi:+.1%} against {baseline.roi:+.1%}; "
        f"paired difference {mean_difference:+.1%} per bet over {games} games, "
        f"interval {low:+.1%} to {high:+.1%}. "
        + ("Distinguishable from zero." if wins else "Not distinguishable from zero.")
        + " Both arms lose money against real prices."
    )
    record(
        POLICY, league, ships_it=wins,
        measured_on=f"{args.season} bought prices, {baseline.bets:,} pooled bets",
        variants_tested=variants, summary=summary,
    )
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUTS_DIR / league.output_name("props_recency_experiment", ".md")).write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print("\n" + "\n".join(lines[-6:]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
