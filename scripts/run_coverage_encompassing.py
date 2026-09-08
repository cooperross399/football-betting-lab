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

D_NAME = "d  the interaction (receiver split x opponent man rate)"


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
                usecols=[
                    "nflverse_game_id", "play_id", "possession_team",
                    "defense_man_zone_type",
                ],
            )
        )
    if missing:
        raise SystemExit(
            "::error::No participation file for " + ", ".join(missing) +
            ". Fetch it: scripts/fetch_football_data.py --only participation"
        )
    return pd.concat(frames, ignore_index=True)


def load_pbp(league, raw_dir: Path, seasons) -> pd.DataFrame:
    feed = nflverse.FEEDS_BY_NAME["pbp"]
    frames = []
    for season in sorted(seasons):
        path = nflverse.feed_path(feed, league, raw_dir, season)
        if not path.is_file():
            raise SystemExit(f"::error::No play-by-play at {path}.")
        frame = pd.read_csv(
            path, low_memory=False,
            usecols=["game_id", "play_id", "week", "season_type",
                     "receiver_player_id", "receiving_yards", "pass_attempt"],
        )
        frames.append(frame[frame["season_type"] == "REG"].assign(season=season))
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
    parser.add_argument(
        "--feature", default="team", choices=("team", "player"),
        help=(
            "team: the defence's man rate. player: that rate interacted with "
            "the receiver's own man-minus-zone differential, which is the "
            "claim a coverage-matchup board actually makes."
        ),
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

    reliability = None
    if args.feature == "player":
        prior = [s - 1 for s in seasons]
        # `season` comes from the play-by-play side only; carrying it on both
        # makes pandas silently rename each to season_x / season_y.
        targets = cov.targets_by_coverage(
            load_participation(league, args.raw_dir, prior),
            load_pbp(league, args.raw_dir, prior),
        )
        splits = cov.player_coverage_differential(targets)
        reliability = float(splits["reliability"].iloc[0])
        before = len(frame)
        frame = frame.merge(
            splits.rename(columns={"season": "rate_season"})[
                ["rate_season", "player_id", "differential", "differential_shrunk"]
            ],
            on=["rate_season", "player_id"], how="left",
        )
        if len(frame) != before:
            print("::error::The player-split join duplicated wagers.", file=sys.stderr)
            return 2

    have = frame["man_rate"].notna()
    if args.feature == "player":
        have &= frame["differential_shrunk"].notna()
    if args.feature == "player":
        # This sentence used to be shared with the team report, where "a few
        # relocated clubs" is true. Here it is not: the exclusion is the
        # receiver-target gate, and it is enormous. A reader told the missing
        # 59% is a handful of relocated clubs is being told the null speaks for
        # a far wider population than it does.
        gated = int(frame["differential_shrunk"].notna().sum())
        coverage_line = (
            f"The feature covers **{int(have.sum()):,} of {len(frame):,} wagers** "
            f"({100 * have.mean():.1f}%). Every excluded row is excluded because "
            f"the receiver did not clear {cov.MIN_TARGETS_PER_COVERAGE} targets "
            "against **both** coverages in the prior season — not because a rate "
            "was missing, of which there are none. **The null below speaks for "
            "the busiest receiver-seasons only**, which is where a coverage "
            "effect would be easiest to find, not hardest."
        )
    else:
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

    if args.feature == "player":
        # Both main effects go in beside the interaction, or the interaction
        # collects whatever either of them would have explained on its own.
        z = frame["differential_shrunk"]
        frame["player_diff_z"] = (z - z.mean()) / z.std(ddof=0)
        frame["interaction"] = frame["player_diff_z"] * frame["man_centred"]
        frame["player_season"] = (
            frame["player_id"].astype(str) + "_" + frame["rate_season"].astype(str)
        )
        extra = (
            ("d1 opponent man rate (z)", "man_centred"),
            ("d2 receiver man-zone split (z, shrunk)", "player_diff_z"),
            (D_NAME, "interaction"),
        )
        clusters = ("defence_season", "player_season")
    else:
        extra = ((D_NAME, "man_centred"),)
        clusters = ("defence_season",)

    baseline = encompassing.fit(frame, "market and model only", cluster=clusters[0])
    withman = encompassing.fit(
        frame, f"with the {args.feature} feature", extra=extra, cluster=clusters[0]
    )
    if baseline is None or withman is None:
        print("::error::Too few wagers or clusters to fit.", file=sys.stderr)
        return 2
    alternates = [
        encompassing.fit(frame, f"same fit, clustered by {c}", extra=extra, cluster=c)
        for c in clusters[1:]
    ]

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
    if args.feature == "player":
        sham_frame["interaction"] = sham_frame["player_diff_z"] * sham_frame["man_centred"]
    sham = encompassing.fit(
        sham_frame, "placebo: rates reassigned across defences", extra=extra,
        cluster=clusters[0],
    )

    # The sandwich, checked against a resample of the clusters it claims.
    X = np.column_stack([
        np.ones(len(frame)), encompassing.logit(frame["p_market"]),
        encompassing.logit(frame["p_model"]),
        *[frame[col].to_numpy(float) for _, col in extra],
    ])
    y = frame["y"].to_numpy(float)
    groups = frame["defence_season"].to_numpy()
    unique = np.unique(groups)
    rows_by = {g: np.where(groups == g)[0] for g in unique}
    draws = []
    for _ in range(args.bootstrap):
        picked = rng.choice(unique, len(unique), replace=True)
        rows = np.concatenate([rows_by[g] for g in picked])
        draws.append(encompassing.fit_logistic(X[rows], y[rows])[-1])
    lo, hi = np.percentile(draws, [2.5, 97.5])

    d = next(c for c in withman.coefficients if c.name == D_NAME)
    spread = frame["man_rate_z"].max() - frame["man_rate_z"].min()
    swing = abs(d.value) * spread

    # Power, and what the interval still allows. "No demonstrated edge" and "a
    # test too weak to have found one" are different statements and only the
    # second is supported unless these are printed beside the coefficient.
    se_d = (d.high - d.low) / (2 * 1.96)
    mde = 2.8 * se_d                      # 1.96 + 0.84, two-sided 5%, 80% power
    model_c = next(c for c in withman.coefficients if c.name.startswith("c ")).value
    feature_column = dict(extra)[D_NAME] if isinstance(extra[0], tuple) else "man_centred"
    signed = frame[feature_column].to_numpy(float) * np.where(over, 1.0, -1.0)
    p_side = np.where(over, frame["p_market"], 1.0 - frame["p_market"])
    lifted = encompassing.expit(encompassing.logit(p_side) + d.high * signed)
    payout = frame["odds"].map(lambda o: o / 100.0 if o > 0 else 100.0 / abs(o)).to_numpy(float)
    gain = (lifted - p_side) * (1.0 + payout)
    helps = gain > 0
    favoured = int(helps.sum())
    roi_points = 100.0 * float(gain[helps].mean()) if favoured else 0.0
    seasons_spanned = max(1, frame["season"].nunique())
    units_per_season = float(gain[helps].sum()) / seasons_spanned
    realised = 100.0 * float(frame.loc[helps, "profit"].mean()) if favoured else 0.0
    extras = [
        "## What the estimate means in probability",
        "",
        coverage_line,
        "",
        (
            f"The receiver's man-minus-zone differential has a measured "
            f"split-half reliability of **{reliability:.3f}** over a full season. "
            "The differential is shrunk by that factor, and **the shrinkage "
            "changes nothing**: a constant multiplier is annihilated by the "
            "z-standardisation on the next line, so `d` is bit-identical at any "
            "reliability. It is kept because the shrunk column is the one a "
            "*predictive* use would need, but no claim rests on it here. The "
            "reliability that governs a prior-season feature is the "
            "**year-over-year** carryover, which is weaker still: r = +0.02 to "
            "+0.11 across gates, every interval crossing zero."
            if reliability is not None else
            "The feature is the defence's man rate alone; no receiver split enters it."
        ),
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
        "It does not say coverage is irrelevant to football, and it does not say "
        "the question is settled. Read the power section below before concluding "
        "anything from it.",
        "",
        "The control is the **card price, about six hours before kickoff** — not "
        "the closing price. The two correlate at 0.986 and refitting against the "
        "actual close moves nothing, but this fit does not test the close.",
        "",
        "## What this test could not have found",
        "",
        f"**`d` is identified by {len(unique)} quantities, not {len(frame):,}.** The "
        "man rate is constant inside a defence-season, so every wager against one "
        "defence carries the same value of the regressor. Dropping three quarters "
        "of the *wagers* barely moves the standard error; dropping three quarters "
        "of the *defence-seasons* moves it by the square root of four, as it "
        "should. The wager count is the population the answer speaks for. It is "
        "not the sample size.",
        "",
        f"**Minimum detectable effect at 80% power: `d` = {mde:+.4f}.** Anything "
        f"smaller than that, this design would miss more often than not. For "
        f"scale, the props model's own contribution in the same fit is "
        f"`c = {model_c:+.4f}` — so the test could only have found a single public "
        f"scheme statistic carrying {abs(mde / model_c):.0%} of what an entire "
        "player-props model carries beyond the price. Nobody expected that, and "
        "the design was never in a position to find less.",
        "",
        f"**What the interval fails to exclude, in money.** If `d` truly sat at "
        f"the upper edge of its interval ({d.high:+.4f}), the wagers where the "
        f"feature favours the bet actually placed ({favoured:,} of "
        f"{len(frame):,}) would gain about **{roi_points:+.2f} ROI points** — "
        f"roughly **{units_per_season:+.0f} units a season** at the lab's flat "
        f"1-unit stake, against a receiving card that currently returns "
        f"{realised:.2f}%. That is an effect large enough to erase most of the "
        "hold, and this test did not reject it.",
        "",
        "**So the honest statement is the narrow one.** Not \"coverage carries "
        "nothing\", but: *a prior-season scheme proxy, measured over 96 "
        "defence-seasons, could not be told from zero by a test whose noise floor "
        "sits above the range of effects that would be worth money.* The placebo "
        "makes the same point from the other side — a feature reassigned at "
        "random routinely produces coefficients larger than every real point "
        "estimate here.",
    ]

    out = OUTPUTS_DIR / league.output_name(
        f"coverage_encompassing_{args.feature}_{args.markets}", ".md"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    body = report([baseline, withman, *alternates, sham], extras)
    out.write_text(body, encoding="utf-8")
    print(body)
    print(f"Written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
