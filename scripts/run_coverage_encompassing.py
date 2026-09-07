#!/usr/bin/env python3
"""Does the opponent's man-coverage rate say anything the price does not?

    PYTHONPATH=src python scripts/run_coverage_encompassing.py --raw-dir ...

The player props model has no opponent term: `fit_rates` builds a player's
rates from his own history, so a receiver's distribution is identical against
the league's heaviest man defence and its heaviest zone one. This asks whether
the simplest opponent term worth having carries anything once the closing price
is held fixed:

    logit P(over) = a + b*logit(p_market) + c*logit(p_model) + d*man_rate_faced

`d` is the whole report. If it cannot be told from zero, the market already
holds whatever the coverage tendency knows, and wiring it into the model can
only add variance. That is the expected answer and it is worth having:
a defence's scheme identity is the most public fact about it.

The man rate is the PRIOR season's, which is both leak-free and the only thing
a live card could ever have — nflverse publishes participation once, after the
post-season.

Clustered by DEFENCE-SEASON, not by game. `man_rate` takes one value across
every wager a defence-season supplies, so a game-level cluster would treat
about ninety independent quantities as tens of thousands.
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
from football_betting_lab.reports import coverage_feature as cov
from football_betting_lab.reports import encompassing
from football_betting_lab.reports.encompassing import devigged_market
from football_betting_lab.reports.props_backtest import normalise_name

D_NAME = "d  man rate faced (z)"


def load_participation(league, raw_dir: Path, seasons) -> pd.DataFrame:
    feed = nflverse.FEEDS_BY_NAME["participation"]
    frames = []
    missing = []
    for season in sorted(seasons):
        path = nflverse.feed_path(feed, league, raw_dir, season)
        if not path.is_file():
            missing.append(f"{season} ({path})")
            continue
        frames.append(
            pd.read_csv(
                path,
                low_memory=False,
                usecols=["nflverse_game_id", "possession_team", "defense_man_zone_type"],
            )
        )
    if missing:
        raise SystemExit(
            "::error::No participation file for " + ", ".join(missing) +
            ". Fetch it: scripts/fetch_football_data.py --only participation"
        )
    return pd.concat(frames, ignore_index=True)


def load_rosters(league, raw_dir: Path, seasons) -> pd.DataFrame:
    feed = nflverse.FEEDS_BY_NAME["weekly_rosters"]
    return pd.concat(
        [
            pd.read_csv(
                nflverse.feed_path(feed, league, raw_dir, s),
                low_memory=False,
                usecols=["season", "week", "team", "gsis_id"],
            )
            for s in sorted(seasons)
        ],
        ignore_index=True,
    )


def report(fits, extras) -> str:
    lines = ["# Does man coverage say anything the price does not?", ""]
    for fit in fits:
        if fit is None:
            continue
        lines += [
            f"## {fit.label}",
            "",
            f"{fit.wagers:,} wagers, {fit.games} clusters.",
            "",
            "| term | estimate | 95% interval | tells from zero |",
            "|:--|--:|:--|:--|",
        ]
        for c in fit.coefficients:
            verdict = "no" if c.includes_zero else "yes"
            lines.append(
                f"| {c.name} | {c.value:+.4f} | [{c.low:+.4f}, {c.high:+.4f}] | {verdict} |"
            )
        lines.append("")
    lines += extras
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", default=DEFAULT_LEAGUE_KEY)
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument(
        "--markets", default="receiving", choices=("receiving", "all"),
        help="Receiving markets are where a coverage scheme has a mechanism.",
    )
    parser.add_argument("--bootstrap", type=int, default=400)
    args = parser.parse_args(argv)
    league = league_for(args.league)

    bets_path = OUTPUTS_DIR / league.output_name("props_backtest_bets", ".csv")
    if not bets_path.is_file():
        print(f"::error::No scored bets at {bets_path}.", file=sys.stderr)
        return 2
    bets = pd.read_csv(bets_path, low_memory=False)
    if args.markets == "receiving":
        bets = bets[bets["market"].isin(cov.RECEIVING_MARKETS)]
    bets = bets.copy()
    bets["identity"] = bets["player"].map(normalise_name)
    bets["line"] = pd.to_numeric(bets["line"], errors="coerce")

    market = devigged_market(league, args.raw_dir)
    frame = bets.merge(market, on=["event_id", "market", "identity", "line"], how="inner")
    frame = frame.dropna(subset=["actual", "line", "model_probability", "p_market"])
    frame = frame[frame["actual"] != frame["line"]].copy()
    if frame.empty:
        print("::error::Nothing merged.", file=sys.stderr)
        return 2

    widest = frame.groupby(["event_id", "market", "identity", "line"]).size().max()
    if int(widest) > 1:
        print(f"::error::The price join duplicated wagers ({widest} on one key).",
              file=sys.stderr)
        return 2

    seasons = sorted(frame["season"].astype(int).unique())
    schedule = pd.read_csv(
        nflverse.feed_path(nflverse.FEEDS_BY_NAME["schedules"], league, args.raw_dir, None),
        low_memory=False,
        usecols=["season", "week", "away_team", "home_team", "game_type"],
    )
    frame = cov.opponent_of_each_wager(
        frame, load_rosters(league, args.raw_dir, seasons), schedule
    )
    rates = cov.man_rate_by_defence(
        load_participation(league, args.raw_dir, [s - 1 for s in seasons])
    )
    frame = cov.attach_prior_season_man_rate(frame, rates)

    have = frame["man_rate"].notna()
    coverage_line = (
        f"The feature covers **{int(have.sum()):,} of {len(frame):,} wagers** "
        f"({100 * have.mean():.1f}%). Rows without a prior-season rate are a "
        "relocated or expansion-less club-season and are excluded here rather "
        "than imputed."
    )
    frame = frame[have].copy()

    frame["y"] = (frame["actual"] > frame["line"]).astype(float)
    over = frame["selection"].astype(str).str.lower().eq("over")
    frame["p_model"] = np.where(over, frame["model_probability"], 1.0 - frame["model_probability"])
    frame["side_over"] = over.astype(float)
    frame["defence_season"] = frame["opponent"].astype(str) + "_" + frame["rate_season"].astype(str)
    # The within-season z-score, never the raw rate: the league mean moves up
    # to 17 points between consecutive seasons, so a globally centred raw rate
    # would make this regressor partly an indicator of the season.
    frame["man_centred"] = frame["man_rate_z"]

    extra = ((D_NAME, "man_centred"),)
    baseline = encompassing.fit(frame, "market and model only", cluster="defence_season")
    withman = encompassing.fit(frame, "with man rate faced", extra=extra, cluster="defence_season")
    if baseline is None or withman is None:
        print("::error::Too few wagers or defence-seasons to fit.", file=sys.stderr)
        return 2

    # Placebo: reassign the rates ACROSS defence-seasons. Shuffling the column
    # row-wise would break the within-cluster constancy that makes this feature
    # what it is, and would flatter the interval.
    rng = np.random.default_rng(11)
    keys = frame["defence_season"].unique()
    shuffled = dict(zip(keys, rng.permutation(
        frame.groupby("defence_season")["man_centred"].first().reindex(keys).to_numpy()
    )))
    sham_frame = frame.copy()
    sham_frame["man_centred"] = sham_frame["defence_season"].map(shuffled)
    sham = encompassing.fit(
        sham_frame, "placebo: rates reassigned across defences", extra=extra,
        cluster="defence_season",
    )

    # The sandwich, checked against a resample of the clusters it claims.
    X = np.column_stack([
        np.ones(len(frame)), encompassing.logit(frame["p_market"]),
        encompassing.logit(frame["p_model"]), frame["man_centred"].to_numpy(float),
    ])
    y = frame["y"].to_numpy(float)
    groups = frame["defence_season"].to_numpy()
    unique = np.unique(groups)
    rows_by = {g: np.where(groups == g)[0] for g in unique}
    draws = []
    for _ in range(args.bootstrap):
        picked = rng.choice(unique, len(unique), replace=True)
        rows = np.concatenate([rows_by[g] for g in picked])
        draws.append(encompassing.fit_logistic(X[rows], y[rows])[3])
    lo, hi = np.percentile(draws, [2.5, 97.5])

    d = next(c for c in withman.coefficients if c.name == D_NAME)
    spread = frame["man_rate_z"].max() - frame["man_rate_z"].min()
    swing = abs(d.value) * spread
    extras = [
        "## What the estimate means in probability",
        "",
        coverage_line,
        "",
        f"The within-season z-score spans **{frame['man_rate_z'].min():+.2f} to "
        f"{frame['man_rate_z'].max():+.2f}** across the defence-seasons here. "
        f"At `d = {d.value:+.4f}` per standard deviation, "
        f"moving from the most zone defence to the most man one shifts the log-odds "
        f"of the over by **{swing:.4f}** — about "
        f"**{100 * (encompassing.expit(np.array([swing])) - 0.5)[0]:.2f} percentage points** "
        "at an even-money price.",
        "",
        f"Bootstrap over {len(unique)} defence-seasons ({args.bootstrap} draws): "
        f"`d` in **[{lo:+.4f}, {hi:+.4f}]**. The sandwich says "
        f"[{d.low:+.4f}, {d.high:+.4f}]; a closed form nobody checked against a "
        "resample is how this repository shipped two interval defects.",
        "",
        "**A `d` that includes zero is no demonstrated edge, in those words.** "
        "It does not say coverage is irrelevant to football; it says the closing "
        "price already holds whatever this measure of it knows.",
    ]

    out = OUTPUTS_DIR / league.output_name(f"coverage_encompassing_{args.markets}", ".md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report([baseline, withman, sham], extras), encoding="utf-8")
    print(report([baseline, withman, sham], extras))
    print(f"Written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
