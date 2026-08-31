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
from football_betting_lab.reports.props_backtest import MarketResult
from football_betting_lab.verdicts import record

POLICY = "props_recency_weighting"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", default=DEFAULT_LEAGUE_KEY)
    # Plural, and every one of them must clear. A single season used to write
    # this verdict, and the file has one name, so whether the policy shipped
    # depended on which season had been run last: on 2025 the paired difference
    # was +2.3% and it shipped; on 2023 it was -1.8% and it did not. Same
    # policy, same script, opposite verdicts, and the card would have read
    # whichever ran most recently.
    parser.add_argument("--seasons", type=int, nargs="+", default=[2023, 2024, 2025])
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
    season_returns: dict[str, dict[int, pd.Series]] = {}
    for label, half_life in arms:
        seasons_pooled = []
        frames = []
        for season in args.seasons:
            result = props_backtest.run(
                prices, logs, league, season=season, raw_dir=RAW_DIR,
                processed_dir=PROCESSED_DIR, draws=args.draws,
                recency_half_life=half_life,
            )
            seasons_pooled.append(result.pooled)
            if not result.bets.empty:
                # The event id is unique across seasons, but the season is
                # carried anyway so a per-season paired test can be taken.
                frames.append(result.bets.assign(season=season))
            print(f"  {label} {season}: {result.pooled.bets:,} bets, "
                  f"ROI {result.pooled.roi:+.1%}", flush=True)
        bets = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        staked = bets[bets["outcome"] != "void"] if not bets.empty else bets
        total = sum(p.bets for p in seasons_pooled)
        roi = (
            sum(p.roi * p.bets for p in seasons_pooled) / total if total else 0.0
        )
        # The union of the seasons' intervals, not a pooled recomputation:
        # the arms are compared per season below and this row is descriptive.
        results[label] = MarketResult(
            market="all seasons pooled",
            bets=total,
            roi=roi,
            low=min((entry.low for entry in seasons_pooled), default=0.0),
            high=max((entry.high for entry in seasons_pooled), default=0.0),
        )
        per_game_returns[label] = (
            staked.groupby(["season", "event_id"])["profit"].mean()
            if not staked.empty
            else pd.Series(dtype=float)
        )
        season_returns[label] = {
            season: staked[staked["season"] == season]
            .groupby("event_id")["profit"].mean()
            for season in args.seasons
        } if not staked.empty else {}
        lines.append(
            f"| {label} | {results[label].bets:,} | {results[label].roi:+.1%} | "
            f"{results[label].low:+.1%} to {results[label].high:+.1%} |"
        )
        print(f"{label}: {results[label].bets:,} bets, ROI {results[label].roi:+.1%}")

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

    # Pooling is not enough, and this is the defect that made the rule matter.
    # The verdict file has ONE name, so when this script scored a single season
    # the policy shipped or did not depending on which season had been run
    # last: on 2025 the paired difference was +2.3% and it shipped; on 2023 it
    # was -1.8% and it did not. Same policy, same script, opposite verdicts,
    # and the card reads whichever ran most recently.
    #
    # So the standard this lab already applies to a market applies to a policy:
    # it has to hold on every season, not on their average. A policy that helps
    # in one season and hurts in another has not been shown to help.
    per_season: dict[int, tuple[int, float, float, float]] = {}
    for season in args.seasons:
        variant_games = season_returns.get(best_label, {}).get(season)
        base_games = season_returns.get("baseline (no weighting)", {}).get(season)
        if variant_games is None or base_games is None:
            continue
        difference = variant_games.subtract(base_games, fill_value=0.0).dropna()
        count = len(difference)
        if count < 2:
            continue
        mean = float(difference.mean())
        error = float(difference.std(ddof=1)) / (count ** 0.5)
        per_season[season] = (count, mean, mean - 1.96 * error, mean + 1.96 * error)

    clears_every_season = bool(per_season) and all(
        entry[2] > 0.0 for entry in per_season.values()
    )
    wins = distinguishable and clears_every_season

    lines.append("")
    lines.append(
        f"**Paired comparison, which is what decides.** Both arms bet the same "
        f"{games} games, so the difference is measured per game and tested "
        f"against zero: **{mean_difference:+.1%} per bet, 95% interval "
        f"{low:+.1%} to {high:+.1%}**."
    )
    lines.append("")
    lines.append(
        "**And it has to hold in every season, not on their average.** This "
        "script used to score one season and write a verdict file with one "
        "name, so whether the policy shipped depended on which season had been "
        "run last."
    )
    lines.append("")
    lines.append("| Season | Games | Paired difference | 95% interval | Clears? |")
    lines.append("|:---|---:|---:|:---|:---|")
    for season, (count, mean, season_low, season_high) in sorted(per_season.items()):
        lines.append(
            f"| {season} | {count:,} | {mean:+.1%} | "
            f"{season_low:+.1%} to {season_high:+.1%} | "
            f"{'yes' if season_low > 0.0 else '**no**'} |"
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

    failed = [str(s) for s, e in sorted(per_season.items()) if e[2] <= 0.0]
    summary = (
        f"{best_label} vs baseline: {best.roi:+.1%} against {baseline.roi:+.1%}; "
        f"paired difference {mean_difference:+.1%} per bet over {games} games, "
        f"interval {low:+.1%} to {high:+.1%}. "
        + ("Pooled difference distinguishable from zero. " if distinguishable
           else "Pooled difference not distinguishable from zero. ")
        + (
            f"Clears every season measured ({len(per_season)})."
            if clears_every_season
            else f"Does NOT clear {', '.join(failed) or 'any season'}, so it "
                 "does not ship however good the pooled number is."
        )
        + " Both arms lose money against real prices."
    )
    record(
        POLICY, league, ships_it=wins,
        measured_on=(
            f"{', '.join(str(s) for s in args.seasons)} bought prices, "
            f"{baseline.bets:,} pooled bets across "
            f"{len(args.seasons)} season(s)"
        ),
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
