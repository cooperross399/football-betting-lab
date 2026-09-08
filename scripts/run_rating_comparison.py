#!/usr/bin/env python3
"""Do EPA ratings predict a game better than points ratings? Spends nothing.

    PYTHONPATH=src python scripts/run_rating_comparison.py --raw-dir <dir>

Both raters return the same `TeamRatings`, so this compares estimators and
nothing else. Ratings are refitted once per game-day from games and plays
strictly earlier, which is the same walk-forward rule the card runs under: in a
sixteen-game week, using the rest of the week leaks a result into the price of
a game kicking off at the same time.

The comparison is PAIRED — the same game scored by both — and the interval is a
bootstrap over games on the per-game difference. An unpaired comparison of two
means would be swamped by the variance of NFL scores, which is enormous and
identical for both models.

**A difference whose interval includes zero is no demonstrated improvement, and
the minimum detectable difference is printed beside it** so that "no difference"
cannot be read as "settled" when the test was never able to see one.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from football_betting_lab.config import OUTPUTS_DIR, RAW_DIR
from football_betting_lab.data import nflverse
from football_betting_lab.leagues import DEFAULT_LEAGUE_KEY, league_for
from football_betting_lab.models.scoring import fit_epa_ratings, fit_ratings

PLAY_COLUMNS = ["game_id", "game_date", "season", "season_type", "play_type",
                "epa", "posteam", "defteam"]


def load_plays(league, raw_dir: Path, seasons) -> pd.DataFrame:
    feed = nflverse.FEEDS_BY_NAME["pbp"]
    frames = []
    for season in sorted(seasons):
        path = nflverse.feed_path(feed, league, raw_dir, season)
        if not path.is_file():
            raise SystemExit(f"::error::No play-by-play at {path}.")
        frame = pd.read_csv(path, low_memory=False, usecols=PLAY_COLUMNS)
        frames.append(frame[frame["season_type"] == "REG"])
    return pd.concat(frames, ignore_index=True)


def load_games(league, raw_dir: Path, seasons) -> pd.DataFrame:
    path = nflverse.feed_path(nflverse.FEEDS_BY_NAME["schedules"], league, raw_dir, None)
    games = pd.read_csv(path, low_memory=False)
    games = games[games["season"].isin(seasons) & (games["game_type"] == "REG")]
    games = games.dropna(subset=["home_score", "away_score", "gameday"])
    return games.rename(columns={"gameday": "game_date"})


def bootstrap(values: np.ndarray, *, draws: int, seed: int = 11) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    means = [
        float(values[rng.integers(0, len(values), len(values))].mean())
        for _ in range(draws)
    ]
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", default=DEFAULT_LEAGUE_KEY)
    parser.add_argument("--seasons", type=int, nargs="+",
                        default=[2022, 2023, 2024, 2025])
    parser.add_argument("--test-from", type=int, default=2023,
                        help="First season scored. Earlier ones only build history.")
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--draws", type=int, default=2000)
    args = parser.parse_args(argv)
    league = league_for(args.league)

    games = load_games(league, args.raw_dir, args.seasons)
    plays = load_plays(league, args.raw_dir, args.seasons)
    scored = games[games["season"] >= args.test_from]
    if scored.empty:
        print("::error::No games to score.", file=sys.stderr)
        return 2

    rows = []
    for day, slate in scored.groupby(scored["game_date"].astype(str)):
        points = fit_ratings(games, before=day)
        epa = fit_epa_ratings(plays, games, before=day, basis="game")
        epa_play = fit_epa_ratings(plays, games, before=day, basis="play")
        if not epa.offence or not epa_play.offence:
            continue          # week one of the earliest season: no plays yet
        for game in slate.itertuples():
            actual_margin = float(game.home_score) - float(game.away_score)
            actual_total = float(game.home_score) + float(game.away_score)
            record = {"season": game.season, "game_date": day,
                      "actual_margin": actual_margin, "actual_total": actual_total}
            for name, rating in (("points", points), ("epa", epa), ("epa_play", epa_play)):
                home = rating.expected_points(game.home_team, game.away_team, at_home=True)
                away = rating.expected_points(game.away_team, game.home_team, at_home=False)
                record[f"{name}_margin"] = home - away
                record[f"{name}_total"] = home + away
            rows.append(record)

    frame = pd.DataFrame(rows)
    if frame.empty:
        print("::error::Nothing scored.", file=sys.stderr)
        return 2

    lines = [
        "# EPA ratings against points ratings",
        "",
        f"{len(frame):,} games, {frame['season'].nunique()} season(s) "
        f"({frame['season'].min()}-{frame['season'].max()}), refitted "
        f"{frame['game_date'].nunique():,} times — once per game-day, from data "
        "strictly earlier.",
        "",
        "| target | points rater | EPA rater | paired difference | 95% interval | better? |",
        "|:--|--:|--:|--:|:--|:--|",
    ]
    verdicts = []
    for target, variant in [(t_, v_) for t_ in ("margin", "total")
                            for v_ in ("epa", "epa_play")]:
        err_p = (frame[f"points_{target}"] - frame[f"actual_{target}"]).abs()
        err_e = (frame[f"{variant}_{target}"] - frame[f"actual_{target}"]).abs()
        diff = (err_p - err_e).to_numpy(float)   # positive = EPA closer
        lo, hi = bootstrap(diff, draws=args.draws)
        # `diff` is positive when EPA is CLOSER. An interval excluding zero
        # on the wrong side is a demonstrated REGRESSION, and reporting it as
        # "excludes zero, therefore better" is how a green tick gets attached
        # to a worse model.
        better, worse = lo > 0, hi < 0
        label = f"{target}, EPA per {'game' if variant == 'epa' else 'play'}"
        verdicts.append((label, float(diff.mean()), lo, hi, better, worse))
        lines.append(
            f"| mean absolute error, {label} | {err_p.mean():.3f} | "
            f"{err_e.mean():.3f} | {diff.mean():+.3f} | "
            f"[{lo:+.3f}, {hi:+.3f}] | "
            + ("**EPA better**" if better else "**EPA WORSE**" if worse else "no difference shown")
            + " |"
        )

    # Mean absolute error alone cannot tell "carries less signal" from "carries
    # the same signal, spread too wide" — and those have opposite remedies.
    lines += [
        "",
        "## Dispersion against signal",
        "",
        "Mean absolute error alone cannot separate *carries less information* "
        "from *carries the same information, spread too wide*, and those have "
        "opposite remedies: the first needs a different feature, the second only "
        "needs heavier shrinkage.",
        "",
        "| target | prediction sd | correlation with the result |",
        "|:--|--:|--:|",
    ]
    for target in ("margin", "total"):
        actual = frame[f"actual_{target}"]
        lines.append(f"| **actual {target}** | {actual.std():.2f} | — |")
        for name, shown in (("points", "points rater"), ("epa", "EPA rater")):
            column = frame[f"{name}_{target}"]
            correlation = float(np.corrcoef(column, actual)[0, 1])
            lines.append(f"| {shown}, {target} | {column.std():.2f} | {correlation:.4f} |")
    flat = float((frame["actual_total"] - frame["actual_total"].mean()).abs().mean())
    lines += [
        "",
        f"Predicting the league-average total for every game scores **{flat:.3f}** "
        "mean absolute error. Any rater above that number is worse than not "
        "modelling totals at all.",
    ]
    lines += ["", "## What this test could have found", ""]
    for target, mean, lo, hi, better, worse in verdicts:
        se = (hi - lo) / (2 * 1.96)
        mde = 2.8 * se
        lines.append(
            f"- **{target}**: standard error {se:.3f} points, so the minimum "
            f"detectable improvement at 80% power is **{mde:.3f} points of mean "
            f"absolute error**. The observed difference is {mean:+.3f}. "
            + (
                "The interval excludes zero on the improving side: a demonstrated "
                "improvement."
                if better else
                "**The interval excludes zero on the WRONG side — this is a "
                "demonstrated regression, not a null.**"
                if worse else
                f"The interval includes zero: **no demonstrated improvement**, and "
                f"an improvement smaller than {mde:.3f} points would have been "
                "missed more often than not."
            )
        )
    lines += [
        "",
        "Both raters shrink a team toward the league mean with the same prior "
        "and both read the same history, so this isolates the estimator. Neither "
        "is compared against a price here — a better forecast and a profitable "
        "one are different claims, and this file only supports the first.",
    ]

    body = "\n".join(lines) + "\n"
    out = OUTPUTS_DIR / league.output_name("rating_comparison", ".md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")
    print(body)
    print(f"Written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
