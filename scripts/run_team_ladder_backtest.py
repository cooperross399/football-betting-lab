#!/usr/bin/env python3
"""Does the team model beat real *card-time* prices on the alternate ladders?

    PYTHONPATH=src python scripts/run_team_ladder_backtest.py

**The one substantial priced test this lab has never run.** The closing-line
backtest bets into the close at a single consensus line, and its own report
says that is conservative in two directions at once: the close is the sharpest
price of the week, and one consensus line is not the best of the nine books a
card would shop. This bets the card-time snapshot at the best available price,
which is what a card actually does.

It is also the only test that reaches the machinery the team model was built
for. Featured `moneyline`, `spread` and `total_points` were never bought — the
purchase was props-led — but **985,000 rows of `alternate_spread` and
`alternate_total_points`** were, plus the team totals. Those ladders are where
the exponential tilt and the exact push mass at 3 and 7 do their work, and
where a thinner market is at least plausible.

Walk-forward throughout: ratings and the empirical score shape are fitted only
on games kicking off strictly before the game being priced.
"""

from __future__ import annotations

import argparse
import sys
from statistics import NormalDist

import pandas as pd

from football_betting_lab.config import OUTPUTS_DIR, PROCESSED_DIR, RAW_DIR
from football_betting_lab.data.build_datasets import TEAM_GAMES_FILENAME
from football_betting_lab.forward_evidence import american_to_implied, profit_on_win
from football_betting_lab.leagues import DEFAULT_LEAGUE_KEY, league_for
from football_betting_lab.models.scoring import (
    distribution_for,
    empirical_pmf,
    fit_ratings,
)
from football_betting_lab.providers.historical import CACHE_DIRNAME
from football_betting_lab.providers.team_names import name_to_abbreviation, resolve_team
from football_betting_lab.reports.card_pricing import (
    MODELLED_TEAM_MARKETS,
    _team_probability,
)
from football_betting_lab.reports.props_backtest import (
    MINIMUM_BETS,
    best_price_per_selection,
    events_in_season,
    label_snapshots,
    load_bought_prices,
)

#: Declared here rather than discovered: the same 6% the props backtest uses,
#: and the same -160 juice floor. Reusing them means this test cannot be the
#: one that got a friendlier threshold.
MIN_EDGE = 0.06
MAX_JUICE = -160.0


def _settle(row, home_score: float, away_score: float) -> str:
    """Settle one ladder rung from the final score.

    Pushes are returned as pushes, never as losses. A whole-number rung pushes
    often enough at 3 and 7 that grading them as losses would manufacture a
    negative result out of the sport's own lumpiness.
    """
    line = row.line
    if line is None or pd.isna(line):
        return "void"
    line = float(line)
    margin = home_score - away_score
    total = home_score + away_score
    market, side = str(row.market), str(row.selection)

    if market in {"spread", "alternate_spread"}:
        value = margin + line if side == "home" else -margin + line
        return "push" if value == 0 else ("won" if value > 0 else "lost")
    if market in {"total_points", "alternate_total_points"}:
        if total == line:
            return "push"
        return "won" if (total > line) == (side == "over") else "lost"
    if market in {"team_total", "alternate_team_total"}:
        scored = home_score if side.startswith("home") else away_score
        if scored == line:
            return "push"
        return "won" if (scored > line) == side.endswith("over") else "lost"
    return "void"


def _interval(bets: pd.DataFrame) -> tuple[float, float, float]:
    """ROI and a 95% interval from between-GAME variation.

    Clustered because one game supplies many rungs of the same ladder, and
    those rungs settle on one final score. Treating them as independent would
    narrow every interval by roughly the square root of the rungs per game,
    which on a ladder is a factor of three or four.
    """
    staked = bets[bets["outcome"] != "void"]
    if staked.empty:
        return 0.0, 0.0, 0.0
    roi = float(staked["profit"].mean())
    per_game = staked.groupby("event_id")["profit"].mean()
    if len(per_game) < 2:
        return roi, float("-inf"), float("inf")
    error = float(per_game.std(ddof=1)) / (len(per_game) ** 0.5)
    return roi, roi - 1.96 * error, roi + 1.96 * error


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", default=DEFAULT_LEAGUE_KEY)
    parser.add_argument("--seasons", type=int, nargs="+", default=[2023, 2024, 2025])
    parser.add_argument("--min-edge", type=float, default=MIN_EDGE)
    args = parser.parse_args(argv)
    league = league_for(args.league)

    cache = RAW_DIR / league.data_dir_segment / CACHE_DIRNAME
    games_path = PROCESSED_DIR / TEAM_GAMES_FILENAME
    if not cache.is_dir() or not games_path.is_file():
        print("Bought prices or team games are missing.", file=sys.stderr)
        return 2

    games = pd.read_csv(games_path, low_memory=False)
    played = games.dropna(subset=["home_score", "away_score"])

    prices = label_snapshots(load_bought_prices(cache, league))
    prices = prices[prices["phase"] == "card"]
    prices = prices[prices["market"].isin(MODELLED_TEAM_MARKETS)].copy()
    if prices.empty:
        print("No card-time team-market prices were bought.", file=sys.stderr)
        return 2
    prices["line"] = pd.to_numeric(prices["line"], errors="coerce")
    prices = prices.dropna(subset=["line"])
    prices = best_price_per_selection(prices)

    lookup = name_to_abbreviation(league)
    by_key = {
        (int(row.season), str(row.home_team), str(row.away_team)): row
        for row in games.itertuples()
    }

    rows: list[dict] = []
    unmatched = 0
    for season in args.seasons:
        # From each event's own kickoff, never from the season the caller
        # happens to be looping over. Two scripts in this repository have
        # already settled priced events against the wrong season.
        subset = events_in_season(prices, league, season)
        for event_id, frame in subset.groupby("event_id"):
            first = frame.iloc[0]
            home = resolve_team(first["home_team"], league, lookup)
            away = resolve_team(first["away_team"], league, lookup)
            game = by_key.get((season, str(home), str(away)))
            if game is None or pd.isna(game.home_score):
                unmatched += 1
                continue
            history = played[
                (played["season"] < season)
                | ((played["season"] == season) & (played["week"] < game.week))
            ]
            if len(history) < 100:
                continue
            ratings = fit_ratings(history, before="9999-99-99")
            pmf = empirical_pmf(
                [int(s) for s in history["home_score"]]
                + [int(s) for s in history["away_score"]]
            )
            distribution = distribution_for(
                ratings, pmf, home_team=str(home), away_team=str(away)
            )
            for row in frame.itertuples():
                probability = _team_probability(
                    distribution, str(row.market), str(row.selection), float(row.line)
                )
                if probability is None:
                    continue
                odds = float(row.american_odds)
                if odds < MAX_JUICE:
                    continue
                edge = probability - american_to_implied(odds)
                if edge < args.min_edge:
                    continue
                outcome = _settle(row, float(game.home_score), float(game.away_score))
                rows.append(
                    {
                        "season": season,
                        "event_id": str(event_id),
                        "market": str(row.market),
                        "selection": str(row.selection),
                        "line": float(row.line),
                        "odds": odds,
                        "model_probability": probability,
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
    lines = ["# Does the team model beat real card-time ladder prices?", ""]
    lines.append(
        f"{len(prices):,} bought card-time team-market prices over "
        f"{prices['event_id'].nunique():,} events; {unmatched:,} events could "
        "not be matched to a played game and were excluded rather than guessed "
        "at."
    )
    lines.append("")
    lines.append(
        "**This is the fair version of the closing-line test.** That one bets "
        "into the close at one consensus line, which its own report calls "
        "conservative in two directions. This bets the card-time snapshot at "
        "the best price across every book quoting the rung — what a card "
        "actually does. Featured `moneyline`, `spread` and `total_points` were "
        "never bought, so the ladders are what there is, and they are also "
        "where the exponential tilt and the exact push mass at 3 and 7 do "
        "their work."
    )
    lines.append("")
    if bets.empty:
        lines.append(
            "**No wager cleared the bar**, so no number is offered in its "
            "place. That is an absence, not a result."
        )
    else:
        families = bets["market"].nunique()
        factor = (
            NormalDist().inv_cdf(1 - (0.05 / max(families, 1)) / 2) / 1.96
            if families > 1
            else 1.0
        )
        lines.append("| Market | Bets | Games | Won | Push | ROI | 95% interval | Verdict |")
        lines.append("|:---|---:|---:|---:|---:|---:|:---|:---|")
        for market, group in sorted(bets.groupby("market")):
            roi, low, high = _interval(group)
            staked = group[group["outcome"] != "void"]
            half = (high - low) / 2 * factor
            clow, chigh = roi - half, roi + half
            if len(staked) < MINIMUM_BETS:
                verdict = f"**not enough evidence** — under {MINIMUM_BETS}"
            elif clow <= 0.0 <= chigh:
                verdict = "**no demonstrated edge**"
            else:
                verdict = "interval excludes zero, " + (
                    "**positive**" if roi > 0 else "**negative**"
                )
            lines.append(
                f"| `{market}` | {len(staked):,} | "
                f"{group['event_id'].nunique():,} | "
                f"{int((group['outcome'] == 'won').sum()):,} | "
                f"{int((group['outcome'] == 'push').sum()):,} | {roi:+.1%} | "
                f"{clow:+.1%} to {chigh:+.1%} | {verdict} |"
            )
        roi, low, high = _interval(bets)
        staked = bets[bets["outcome"] != "void"]
        pooled = (
            f"**not enough evidence** — under {MINIMUM_BETS}"
            if len(staked) < MINIMUM_BETS
            else (
                "**no demonstrated edge**"
                if low <= 0.0 <= high
                else "interval excludes zero, "
                + ("**positive**" if roi > 0 else "**negative**")
            )
        )
        lines.append(
            f"| **pooled** | {len(staked):,} | {bets['event_id'].nunique():,} | "
            f"{int((bets['outcome'] == 'won').sum()):,} | "
            f"{int((bets['outcome'] == 'push').sum()):,} | {roi:+.1%} | "
            f"{low:+.1%} to {high:+.1%} | {pooled} |"
        )
        lines.append("")
        lines.append("Per season, because a pooled number can hide a reversal:")
        lines.append("")
        lines.append("| Season | Bets | ROI |")
        lines.append("|:---|---:|---:|")
        for season, group in sorted(bets.groupby("season")):
            sub = group[group["outcome"] != "void"]
            lines.append(
                f"| {season} | {len(sub):,} | {sub['profit'].mean():+.1%} |"
                if len(sub)
                else f"| {season} | 0 | — |"
            )
        lines.append("")
        lines.append(
            f"Intervals are clustered by game and corrected across the "
            f"{families} markets tested. Pushes are returned as pushes: a "
            "whole-number rung pushes often enough at 3 and 7 that grading "
            "them as losses would manufacture a negative result out of the "
            "sport's own lumpiness."
        )

    report = "\n".join(lines) + "\n"
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUTS_DIR / league.output_name("team_ladder_backtest", ".md")).write_text(
        report, encoding="utf-8"
    )
    if not bets.empty:
        bets.to_csv(
            OUTPUTS_DIR / league.output_name("team_ladder_bets", ".csv"), index=False
        )
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
