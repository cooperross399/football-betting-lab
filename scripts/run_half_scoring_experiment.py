#!/usr/bin/env python3
"""Does the first-half model beat real first-half prices?

    PYTHONPATH=src python scripts/run_half_scoring_experiment.py

The half and quarter markets are wired, settleable, and priced by nothing —
every row of them lands in `no_opinion`. The retention probe found them
retained on 20 of 20 events across eight or nine books, so they are also
measurable, which is why they are worth a model rather than a shrug.

The model is deliberately the crudest thing that could work: each side's
full-game expectation scaled by the league's first-half share, with the shape
taken from the empirical distribution of first-half team scores. Whether that
is good enough is a question for this test.

The verdict is written to disk and read by the card. Nothing ships by
assertion.
"""

from __future__ import annotations

import argparse
import sys

import pandas as pd

from football_betting_lab.config import (
    MAX_DEFAULT_JUICE,
    MIN_EDGE,
    OUTPUTS_DIR,
    PROCESSED_DIR,
    RAW_DIR,
)
from football_betting_lab.data.build_datasets import (
    HALF_SCORES_FILENAME,
    TEAM_GAMES_FILENAME,
)
from football_betting_lab.forward_evidence import american_to_implied, profit_on_win
from football_betting_lab.leagues import DEFAULT_LEAGUE_KEY, league_for
from football_betting_lab.models.scoring import empirical_pmf, fit_half_model, fit_ratings
from football_betting_lab.providers.historical import CACHE_DIRNAME
from football_betting_lab.providers.team_names import name_to_abbreviation, resolve_team
from football_betting_lab.reports.card_pricing import HALF_MARKETS, _team_probability
from football_betting_lab.reports.props_backtest import (
    MINIMUM_BETS,
    best_price_per_selection,
    load_bought_prices,
)
from football_betting_lab.verdicts import record

POLICY = "half_scoring_model"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", default=DEFAULT_LEAGUE_KEY)
    parser.add_argument("--season", type=int, default=2025)
    parser.add_argument("--min-edge", type=float, default=MIN_EDGE)
    args = parser.parse_args(argv)

    league = league_for(args.league)
    games = pd.read_csv(PROCESSED_DIR / TEAM_GAMES_FILENAME, low_memory=False)
    halves_path = PROCESSED_DIR / HALF_SCORES_FILENAME
    if not halves_path.is_file():
        print(f"No half scores at {halves_path}.", file=sys.stderr)
        return 2
    halves = pd.read_csv(halves_path)

    prices = best_price_per_selection(
        load_bought_prices(RAW_DIR / league.data_dir_segment / CACHE_DIRNAME, league)
    )
    prices = prices[prices["market"].isin(HALF_MARKETS)].copy()
    if prices.empty:
        print("No first-half prices were bought.", file=sys.stderr)
        return 2

    lookup = name_to_abbreviation(league)
    half_by_game = {row.game_id: row for row in halves.itertuples()}
    games_by_key = {
        (str(row.season), str(row.home_team), str(row.away_team)): row
        for row in games.itertuples()
    }

    rows: list[dict] = []
    unmatched = 0
    for event_id, frame in prices.groupby("event_id"):
        first = frame.iloc[0]
        home = resolve_team(first["home_team"], league, lookup)
        away = resolve_team(first["away_team"], league, lookup)
        game = games_by_key.get((str(args.season), str(home), str(away)))
        if game is None or game.game_id not in half_by_game:
            unmatched += 1
            continue
        half = half_by_game[game.game_id]
        played = games.dropna(subset=["home_score", "away_score"])
        history = played[
            (played["season"] < args.season)
            | ((played["season"] == args.season) & (played["week"] < game.week))
        ]
        if history.empty:
            continue
        ratings = fit_ratings(history, before="9999-99-99")
        model = fit_half_model(
            halves[halves["game_id"].isin(set(history["game_id"]))], history
        )
        if model is None:
            continue
        distribution = model.distribution(ratings, home_team=home, away_team=away)

        margin = float(half.home_h1) - float(half.away_h1)
        combined = float(half.home_h1) + float(half.away_h1)
        for row in frame.itertuples():
            probability = _team_probability(
                distribution, HALF_MARKETS[row.market], row.selection, row.line
            )
            if probability is None:
                continue
            odds = float(row.american_odds)
            if odds < MAX_DEFAULT_JUICE:
                continue
            edge = probability - american_to_implied(odds)
            if edge < args.min_edge:
                continue
            outcome = _settle(row, margin, combined)
            rows.append(
                {
                    "event_id": str(event_id),
                    "market": row.market,
                    "selection": row.selection,
                    "line": row.line,
                    "odds": odds,
                    "edge": edge,
                    "outcome": outcome,
                    "profit": (
                        profit_on_win(odds)
                        if outcome == "won"
                        else (-1.0 if outcome == "lost" else 0.0)
                    ),
                }
            )

    bets = pd.DataFrame(rows)
    lines = ["# Does the first-half model beat real first-half prices?", ""]
    lines.append(
        f"{len(prices):,} bought first-half prices over "
        f"{prices['event_id'].nunique()} events, {unmatched} of which could "
        "not be matched to a half-time score and were excluded rather than "
        "guessed at."
    )
    lines.append("")
    if bets.empty:
        lines.append("**No bet cleared the bar.** No number is offered in its place.")
        ships = False
        summary = "No bet cleared the edge bar, so nothing was measured."
    else:
        lines.append("| Market | Bets | Won | Push | ROI | 95% interval | Verdict |")
        lines.append("|:-------|-----:|----:|-----:|----:|:-------------|:--------|")
        overall_profit = float(bets["profit"].sum())
        for market in sorted(bets["market"].unique()):
            subset = bets[bets["market"] == market]
            roi, low, high = _interval(subset)
            verdict = (
                f"**not enough evidence** — {len(subset)} bets"
                if len(subset) < MINIMUM_BETS
                else ("**no demonstrated edge**" if low <= 0 <= high else "excludes zero")
            )
            lines.append(
                f"| `{market}` | {len(subset):,} | "
                f"{int((subset['outcome'] == 'won').sum()):,} | "
                f"{int((subset['outcome'] == 'push').sum()):,} | {roi:+.1%} | "
                f"{low:+.1%} to {high:+.1%} | {verdict} |"
            )
        roi, low, high = _interval(bets)
        lines.append(
            f"| **pooled** | {len(bets):,} | "
            f"{int((bets['outcome'] == 'won').sum()):,} | "
            f"{int((bets['outcome'] == 'push').sum()):,} | {roi:+.1%} | "
            f"{low:+.1%} to {high:+.1%} | "
            + ("**no demonstrated edge**" if low <= 0 <= high else "excludes zero")
            + " |"
        )
        ships = roi > 0 and len(bets) >= MINIMUM_BETS
        summary = (
            f"Pooled {roi:+.1%} over {len(bets):,} bets ({overall_profit:+.1f}u), "
            f"interval {low:+.1%} to {high:+.1%}."
        )
        lines.append("")
        lines.append(
            "These markets are currently priced by nothing, so every row of "
            "them lands in `no_opinion` and accumulates no forward evidence. "
            "Shipping this model would change that — and shipping a model "
            "measured to lose would also fill the ledger with opinions "
            "already known to be wrong. **That is a trade Cooper decides, not "
            "this script**, and the verdict below records only what was "
            "measured."
        )

    lines.append("")
    lines.append(
        f"Bets need {MINIMUM_BETS} before a number is offered. Below that the "
        "verdict is *not enough evidence*."
    )

    record(
        POLICY, league, ships_it=ships,
        measured_on=f"{args.season} bought first-half prices",
        variants_tested=1, summary=summary,
    )
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUTS_DIR / league.output_name("half_scoring_experiment", ".md")).write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print("\n".join(lines))
    return 0


def _settle(row, margin: float, combined: float) -> str:
    if row.market == "moneyline_h1":
        if margin == 0:
            return "push"
        return "won" if (margin > 0) == (row.selection == "home") else "lost"
    line = float(row.line)
    if row.market == "spread_h1":
        adjusted = (margin if row.selection == "home" else -margin) + line
        return "push" if adjusted == 0 else ("won" if adjusted > 0 else "lost")
    if combined == line:
        return "push"
    return "won" if (combined > line) == (row.selection == "over") else "lost"


def _interval(bets: pd.DataFrame) -> tuple[float, float, float]:
    import math

    per_game = bets.groupby("event_id").agg(
        profit=("profit", "sum"), bets=("profit", "size")
    )
    total = int(per_game["bets"].sum())
    games = len(per_game)
    if not total:
        return 0.0, 0.0, 0.0
    roi = float(per_game["profit"].sum() / total)
    if games < 2:
        return roi, float("-inf"), float("inf")
    mean_bets = total / games
    variance = float(((per_game["profit"] - roi * per_game["bets"]) ** 2).sum())
    se = math.sqrt(variance / (games * (games - 1))) / mean_bets
    return roi, roi - 1.96 * se, roi + 1.96 * se


if __name__ == "__main__":
    raise SystemExit(main())
