#!/usr/bin/env python3
"""Can the card pick better? The four tests in docs/preregistered_pick_selection.md.

    PYTHONPATH=src python scripts/run_pick_selection_experiments.py

Spends no credits. Reads the 2023-25 card-time and closing ladder prices that
Historical Purchase bought once (restored into `data/raw/nfl/historical_prices`
by the `Pick Selection Experiments` workflow), prices every rung with the team
model walk-forward exactly as `run_team_ladder_backtest.py` does, then replays
the card's selection rules (`gameday_card.select`'s chain) under the baseline
and under each pre-registered change.

Writes `nfl_pick_selection.md`, `nfl_pick_selection.json`, and
`nfl_pick_selection_rungs.csv.gz` — every priced card-time rung with its model
probability, devigged fair probability at card time and close, and outcome — so
a later question about selection never needs the expiring artifact again.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from football_betting_lab.config import (
    CARD_EDGE_CEILING,
    CARD_EDGE_FLOOR,
    MAX_DEFAULT_JUICE,
    MAX_DEFAULT_PRICE,
    MIN_EDGE,
    OUTPUTS_DIR,
    RAW_DIR,
)
from football_betting_lab.data.build_datasets import build_team_games
from football_betting_lab.forward_evidence import american_to_implied, profit_on_win
from football_betting_lab.leagues import DEFAULT_LEAGUE_KEY, league_for
from football_betting_lab.models.scoring import distribution_for, empirical_pmf, fit_ratings
from football_betting_lab.providers.historical import CACHE_DIRNAME
from football_betting_lab.providers.team_names import name_to_abbreviation, resolve_team
from football_betting_lab.reports.card_pricing import MODELLED_TEAM_MARKETS, _team_probability
from football_betting_lab.reports.gameday_card import (
    above_floor,
    best_rung_per_question,
    cap_per_game,
    one_side_per_game,
    within_ceiling,
)
from football_betting_lab.reports.props_backtest import (
    events_in_season,
    label_snapshots,
    load_bought_prices,
)

SEASONS = (2023, 2024, 2025)
FIT_SEASONS = (2023, 2024)
HELD_OUT = 2025
SHRINK_WEIGHT = 0.5


def settle(market: str, side: str, line: float, home: float, away: float) -> str:
    """Same rule as `run_team_ladder_backtest._settle`; pushes are pushes."""
    margin, total = home - away, home + away
    if market in {"spread", "alternate_spread"}:
        value = margin + line if side == "home" else -margin + line
        return "push" if value == 0 else ("won" if value > 0 else "lost")
    if market in {"total_points", "alternate_total_points"}:
        if total == line:
            return "push"
        return "won" if (total > line) == (side == "over") else "lost"
    if market in {"team_total", "alternate_team_total"}:
        scored = home if side.startswith("home") else away
        if scored == line:
            return "push"
        return "won" if (scored > line) == side.endswith("over") else "lost"
    return "void"


def pair_key(market: str, side: str, line: float) -> tuple | None:
    """The two-sided question a rung belongs to, so each book can be devigged."""
    if market in {"spread", "alternate_spread"} and side in {"home", "away"}:
        return (market, round(line if side == "home" else -line, 2))
    if market in {"total_points", "alternate_total_points"} and side in {"over", "under"}:
        return (market, round(line, 2))
    if market in {"team_total", "alternate_team_total"}:
        team, _, _ = side.rpartition("_")
        return (market, team, round(line, 2))
    return None


def fair_probabilities(prices: pd.DataFrame) -> pd.DataFrame:
    """Median over books of each book's proportionally devigged probability.

    Keyed `(event_id, market, selection, line)`. A rung only one side of which
    a book quotes contributes nothing from that book: devigging needs both.
    """
    frame = prices.copy()
    frame["implied"] = frame["american_odds"].map(american_to_implied)
    frame["pair"] = [
        pair_key(m, s, l) for m, s, l in zip(frame["market"], frame["selection"], frame["line"])
    ]
    frame = frame.dropna(subset=["pair"])
    frame = frame.drop_duplicates(["event_id", "book", "market", "selection", "line"])
    sums = frame.groupby(["event_id", "book", "pair"])["implied"].transform("sum")
    sides = frame.groupby(["event_id", "book", "pair"])["implied"].transform("size")
    frame = frame[sides == 2].copy()
    frame["fair"] = frame["implied"] / sums[sides == 2]
    return (
        frame.groupby(["event_id", "market", "selection", "line"])["fair"]
        .median()
        .reset_index()
    )


def qb_changes(games: pd.DataFrame) -> dict[tuple[int, str, str], bool]:
    """`(season, home, away) -> True` when either club starts a new quarterback.

    "New" is against that club's previous regular-season game, across a season
    boundary too. A missing id on either side reads as unknown, not as a change.
    """
    long = pd.concat(
        [
            games.assign(team=games["home_team"], qb=games["home_qb_id"]),
            games.assign(team=games["away_team"], qb=games["away_qb_id"]),
        ]
    ).sort_values(["gameday", "game_id"])
    long["previous"] = long.groupby("team")["qb"].shift(1)
    long["changed"] = long["qb"].notna() & long["previous"].notna() & (long["qb"] != long["previous"])
    changed = long.groupby("game_id")["changed"].any()
    return {
        (int(r.season), str(r.home_team), str(r.away_team)): bool(changed.get(r.game_id, False))
        for r in games.itertuples()
    }


def price_rungs(league, cache: Path, schedule: pd.DataFrame) -> pd.DataFrame:
    prices = label_snapshots(load_bought_prices(cache, league))
    prices = prices[prices["market"].isin(MODELLED_TEAM_MARKETS)].copy()
    prices["line"] = pd.to_numeric(prices["line"], errors="coerce")
    prices["american_odds"] = pd.to_numeric(prices["american_odds"], errors="coerce")
    prices = prices.dropna(subset=["line", "american_odds"])
    card = prices[prices["phase"] == "card"]
    close = prices[prices["phase"] == "close"]
    fair_card = fair_probabilities(card).rename(columns={"fair": "fair_card"})
    fair_close = fair_probabilities(close).rename(columns={"fair": "fair_close"})

    games = build_team_games(league, RAW_DIR, tuple(range(2015, max(SEASONS) + 1)))
    played = games.dropna(subset=["home_score", "away_score"])
    regular = schedule[schedule["game_type"] == "REG"]
    changes = qb_changes(regular[regular["season"] >= 2014])
    lookup = name_to_abbreviation(league)
    by_key = {(int(r.season), str(r.home_team), str(r.away_team)): r for r in games.itertuples()}

    rows: list[dict] = []
    for season in SEASONS:
        subset = events_in_season(card, league, season)
        for event_id, frame in subset.groupby("event_id"):
            first = frame.iloc[0]
            home = resolve_team(first["home_team"], league, lookup)
            away = resolve_team(first["away_team"], league, lookup)
            game = by_key.get((season, str(home), str(away)))
            if game is None or pd.isna(game.home_score):
                continue
            history = played[
                (played["season"] < season)
                | ((played["season"] == season) & (played["week"] < game.week))
            ]
            if len(history) < 100:
                continue
            ratings = fit_ratings(history, before="9999-99-99")
            pmf = empirical_pmf(
                [int(s) for s in history["home_score"]] + [int(s) for s in history["away_score"]]
            )
            distribution = distribution_for(ratings, pmf, home_team=str(home), away_team=str(away))
            best = frame.sort_values("american_odds", ascending=False).drop_duplicates(
                ["market", "selection", "line"]
            )
            for row in best.itertuples():
                probability = _team_probability(
                    distribution, str(row.market), str(row.selection), float(row.line)
                )
                if probability is None:
                    continue
                outcome = settle(
                    str(row.market), str(row.selection), float(row.line),
                    float(game.home_score), float(game.away_score),
                )
                rows.append(
                    {
                        "season": season,
                        "week": int(game.week),
                        "event_id": str(event_id),
                        "home": str(home),
                        "away": str(away),
                        "qb_change": changes.get((season, str(home), str(away))),
                        "market": str(row.market),
                        "selection": str(row.selection),
                        "line": float(row.line),
                        "odds": int(row.american_odds),
                        "model": float(probability),
                        "outcome": outcome,
                    }
                )
    rungs = pd.DataFrame(rows)
    keys = ["event_id", "market", "selection", "line"]
    rungs = rungs.merge(fair_card, on=keys, how="left").merge(fair_close, on=keys, how="left")
    rungs["implied"] = rungs["odds"].map(american_to_implied)
    rungs["profit"] = np.where(
        rungs["outcome"] == "won",
        rungs["odds"].map(profit_on_win),
        np.where(rungs["outcome"] == "lost", -1.0, 0.0),
    )
    return rungs


def card_picks(rungs: pd.DataFrame, probability: pd.Series) -> pd.DataFrame:
    """The card's chain (`gameday_card.select`) on one probability column."""
    frame = rungs.assign(p=probability.values).dropna(subset=["p"])
    frame = frame[(frame["odds"] >= MAX_DEFAULT_JUICE) & (frame["odds"] <= MAX_DEFAULT_PRICE)]
    frame = frame.assign(edge=frame["p"] - frame["implied"])
    frame = frame[frame["edge"] >= MIN_EDGE]
    picks = [
        {"game": r.event_id, "market": r.market, "selection": r.selection, "line": r.line,
         "odds": r.odds, "edge": r.edge, "_index": r.Index}
        for r in frame.itertuples()
    ]
    picks, _ = within_ceiling(picks)
    picks, _ = one_side_per_game(picks)
    picks, _ = above_floor(picks)
    picks, _ = best_rung_per_question(picks)
    picks, _ = cap_per_game(picks)
    chosen = frame.loc[[p["_index"] for p in picks]]
    return chosen


def roi_interval(bets: pd.DataFrame) -> dict:
    staked = bets[bets["outcome"].isin(["won", "lost"])]
    if staked.empty:
        return {"bets": 0, "games": 0, "units": 0.0, "roi": None, "low": None, "high": None}
    per = staked.groupby("event_id")["profit"].agg(profit="sum", bets="size")
    n, g = int(per["bets"].sum()), len(per)
    roi = float(per["profit"].sum() / n)
    low = high = None
    if g > 1:
        resid = per["profit"] - roi * per["bets"]
        se = math.sqrt(float((resid**2).sum() / (g * (g - 1)))) / (n / g)
        low, high = roi - 1.96 * se, roi + 1.96 * se
    return {"bets": n, "games": g, "units": float(per["profit"].sum()), "roi": roi,
            "low": low, "high": high}


def paired_difference(variant: pd.DataFrame, baseline: pd.DataFrame, games: list[str]) -> dict:
    """Mean per-game units (variant minus baseline) over every game either could bet."""
    a = variant.groupby("event_id")["profit"].sum().reindex(games, fill_value=0.0)
    b = baseline.groupby("event_id")["profit"].sum().reindex(games, fill_value=0.0)
    d = a - b
    g = len(d)
    mean = float(d.mean()) if g else 0.0
    se = float(d.std(ddof=1) / math.sqrt(g)) if g > 1 else float("inf")
    return {"games": g, "units": float(d.sum()), "per_game": mean,
            "low": mean - 1.96 * se, "high": mean + 1.96 * se}


def logistic_fit(x: np.ndarray, y: np.ndarray, iterations: int = 50) -> np.ndarray:
    """Plain IRLS. Returns coefficients for `[1, x...]`."""
    X = np.column_stack([np.ones(len(x)), x])
    beta = np.zeros(X.shape[1])
    for _ in range(iterations):
        p = 1 / (1 + np.exp(-X @ beta))
        w = p * (1 - p)
        step = np.linalg.solve(X.T @ (X * w[:, None]), X.T @ (y - p))
        beta = beta + step
        if np.max(np.abs(step)) < 1e-10:
            break
    return beta


def logit(p: pd.Series) -> pd.Series:
    q = p.clip(1e-6, 1 - 1e-6)
    return np.log(q / (1 - q))


def fmt(block: dict) -> str:
    if not block.get("bets"):
        return "| 0 | 0 | 0.00 | n/a | n/a |"
    interval = (
        f"{block['low']:+.1%} to {block['high']:+.1%}" if block["low"] is not None else "n/a"
    )
    return (f"| {block['bets']:,} | {block['games']:,} | {block['units']:+.2f} | "
            f"{block['roi']:+.1%} | {interval} |")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", default=DEFAULT_LEAGUE_KEY)
    parser.add_argument("--rungs", type=Path, default=None,
                        help="Reuse a rungs file instead of pricing from the cache.")
    args = parser.parse_args(argv)
    league = league_for(args.league)
    schedule = pd.read_csv(RAW_DIR / league.data_dir_segment / "schedules" / "games.csv",
                           low_memory=False)

    if args.rungs is not None:
        rungs = pd.read_csv(args.rungs)
    else:
        cache = RAW_DIR / league.data_dir_segment / CACHE_DIRNAME
        if not cache.is_dir():
            print("Bought prices are missing.", file=sys.stderr)
            return 2
        rungs = price_rungs(league, cache, schedule)
        rungs.to_csv(OUTPUTS_DIR / league.output_name("pick_selection_rungs", ".csv.gz"), index=False)
    if rungs.empty:
        print("No priced rungs.", file=sys.stderr)
        return 2

    results: dict = {"rungs": int(len(rungs)), "games": int(rungs["event_id"].nunique())}
    baseline = card_picks(rungs, rungs["model"])

    # H1: recalibrate on 2023-24, apply to 2025.
    fit = rungs[rungs["season"].isin(FIT_SEASONS) & rungs["fair_card"].notna()
                & rungs["outcome"].isin(["won", "lost"])]
    beta = logistic_fit(
        np.column_stack([logit(fit["fair_card"]), logit(fit["model"])]),
        (fit["outcome"] == "won").astype(float).to_numpy(),
    )
    linear = beta[0] + beta[1] * logit(rungs["fair_card"]) + beta[2] * logit(rungs["model"])
    recalibrated = card_picks(rungs, 1 / (1 + np.exp(-linear)))
    results["h1_coefficients"] = {"a": float(beta[0]), "b_market": float(beta[1]),
                                  "c_model": float(beta[2]), "fit_rungs": int(len(fit))}

    # H2: halfway to the market, nothing fitted.
    shrunk = card_picks(rungs, SHRINK_WEIGHT * rungs["model"]
                        + (1 - SHRINK_WEIGHT) * rungs["fair_card"])

    # H3: skip a game where either club starts a new quarterback.
    flagged = baseline["qb_change"].fillna(False).astype(bool)
    no_qb_change = baseline[~flagged]

    variants = {"H1 recalibrated (fitted 2023-24)": recalibrated,
                "H2 halfway to the market": shrunk,
                "H3 skip quarterback-change games": no_qb_change}

    lines = ["# Can the card pick better?", ""]
    lines.append(
        "Pre-registered in `docs/preregistered_pick_selection.md` before any of this ran. "
        f"{results['rungs']:,} priced card-time ladder rungs over {results['games']:,} "
        "games, 2023-25, walk-forward. Every variant runs the card's own selection chain "
        "(-160 to +600, edge 3.5%+, 15% ceiling, one side, edge above 6%, best rung per "
        "question, 3 per game). Flat 1-unit stakes; intervals clustered by game."
    )
    lines.append("")
    for season in (*SEASONS, "all"):
        label = "2023-25" if season == "all" else str(season)
        def cut(frame):
            return frame if season == "all" else frame[frame["season"] == season]
        games = sorted(set(cut(rungs)["event_id"]))
        lines += [f"## {label}", "",
                  "| Rule | Bets | Games | Units | ROI | 95% |", "|:--|--:|--:|--:|--:|:--|"]
        base = roi_interval(cut(baseline))
        lines.append("| Baseline (today's card) " + fmt(base))
        results.setdefault("by_season", {})[label] = {"baseline": base}
        for name, frame in variants.items():
            block = roi_interval(cut(frame))
            diff = paired_difference(cut(frame), cut(baseline), games)
            results["by_season"][label][name] = {**block, "vs_baseline": diff}
            lines.append(f"| {name} " + fmt(block))
        lines += ["", "Paired against the baseline, units per game (variant minus baseline):",
                  "", "| Rule | Units | Per game | 95% |", "|:--|--:|--:|:--|"]
        for name in variants:
            d = results["by_season"][label][name]["vs_baseline"]
            lines.append(f"| {name} | {d['units']:+.2f} | {d['per_game']:+.3f} | "
                         f"{d['low']:+.3f} to {d['high']:+.3f} |")
        lines.append("")

    flagged_block = roi_interval(baseline[flagged])
    results["h3_flagged"] = flagged_block
    lines += ["## H3: baseline picks on quarterback-change games", "",
              "| | Bets | Games | Units | ROI | 95% |", "|:--|--:|--:|--:|--:|:--|",
              "| New starter on either side " + fmt(flagged_block),
              "| Same starters " + fmt(roi_interval(baseline[~flagged])), ""]

    coef = results["h1_coefficients"]
    lines += ["## H1 fit", "",
              f"On {coef['fit_rungs']:,} 2023-24 rungs: a = {coef['a']:+.3f}, "
              f"b (market) = {coef['b_market']:.3f}, c (model) = {coef['c_model']:.3f}. "
              "A model weight near zero means the price already holds what the model knows.",
              ""]

    with_close = baseline.dropna(subset=["fair_card", "fair_close"])
    move = with_close["fair_close"] - with_close["fair_card"]
    results["h4_clv"] = {"picks": int(len(move)), "mean_move": float(move.mean()) if len(move) else None,
                         "share_toward": float((move > 0).mean()) if len(move) else None,
                         "share_away": float((move < 0).mean()) if len(move) else None}
    h4 = results["h4_clv"]
    if h4["picks"]:
        lines += ["## H4: does the market move toward the card's picks? (diagnostic)", "",
                  f"Over {h4['picks']:,} baseline picks with a fair price at both snapshots, the "
                  f"picked side's devigged probability moved {h4['mean_move']:+.4f} on average "
                  f"from card time to the close; toward the pick on {h4['share_toward']:.1%}, "
                  f"away on {h4['share_away']:.1%}.", ""]

    (OUTPUTS_DIR / league.output_name("pick_selection", ".md")).write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUTPUTS_DIR / league.output_name("pick_selection", ".json")).write_text(
        json.dumps(results, indent=2, default=float) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
