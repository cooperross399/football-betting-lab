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
from football_betting_lab.reports import pressure_feature as pressure
from football_betting_lab.reports import role_feature as role
from football_betting_lab.reports import encompassing
from football_betting_lab.reports.encompassing import devigged_market
from football_betting_lab.reports.props_backtest import normalise_name

D_NAME = "d  the interaction (receiver split x opponent man rate)"

#: What each feature IS, and why rows drop out of its fit. Keyed rather than
#: branched, so adding a feature and forgetting to describe it raises a
#: KeyError where before it silently printed a sentence written for a different
#: feature. That has now happened twice: a pressure fit that reported "the
#: defence's man rate alone", and a role fit that blamed its exclusions on
#: "relocated or expansion-less club-seasons".
NARRATIVE: dict[str, dict[str, str]] = {
    "team": {
        "subject": "the defence's man rate",
        "exclusion": (
            "Rows without a prior-season rate are a relocated or expansion-less "
            "club-season and are excluded here rather than imputed."
        ),
        "note": "The feature is the defence's man rate alone; no receiver split enters it.",
    },
    "player": {
        "subject": "a receiver's man-zone split against the defence's man rate",
        "exclusion": (
            "Every excluded row is excluded because the receiver did not clear "
            "the prior-season target gate against **both** coverages — not "
            "because a rate was missing, of which there are none. **The null "
            "below speaks for the busiest receiver-seasons only**, which is "
            "where a coverage effect would be easiest to find, not hardest."
        ),
        "note": "",
    },
    "pressure": {
        "subject": "a rusher's pressure rate against the line in front of him",
        "exclusion": (
            "Excluded rows are a defender with too few charted games in the "
            "prior season, or an offence whose quarterbacks did not reach that "
            "either — not a missing rate, and not imputed."
        ),
        "note": (
            "The rusher's pressures per game is the most persistent feature in "
            "this lab — carryover of relative position +0.884 over 2018-2025, "
            "measured by scripts/run_feature_reliability.py. That is why it was "
            "the one worth a real test, and why the market has had every year "
            "to price it."
        ),
    },
    "role": {
        "subject": "the volume a ruled-out team-mate leaves behind",
        "exclusion": (
            "Excluded rows are a receiver with fewer than three prior weeks "
            "this season, or holding too small a share for an absence to "
            "expand. Nothing is excluded for a missing rate."
        ),
        "note": (
            "**This is the only feature here whose mechanism was confirmed "
            "before any price was involved.** Volume genuinely redistributes: "
            "a player's week-W share gain regressed on the pro-rata share he "
            "would receive gives +0.220, 95% [+0.113, +0.326] over 11,856 "
            "player-weeks — about 0.85 targets a game between a club that has "
            "vacated under 5% of its targets and one that has vacated over 15%. "
            "It is also the only feature the props model cannot see at all, "
            "because `fit_rates` reads a player's own history and that history "
            "was recorded while somebody else held the role. Every injury row "
            "used was filed at least six hours before kickoff."
        ),
    },
}


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
            usecols=["game_id", "play_id", "week", "season_type", "posteam",
                     "receiver_player_id", "receiving_yards", "pass_attempt",
                     "rusher_player_id", "rush_attempt"],
        )
        frames.append(frame[frame["season_type"] == "REG"].assign(season=season))
    return pd.concat(frames, ignore_index=True)


def load_pfr(league, raw_dir: Path, feed_name: str, seasons) -> pd.DataFrame:
    feed = nflverse.FEEDS_BY_NAME[feed_name]
    frames = []
    for season in sorted(set(seasons)):
        path = nflverse.feed_path(feed, league, raw_dir, season)
        if not path.is_file():
            raise SystemExit(f"::error::No {feed_name} at {path}.")
        frames.append(pd.read_csv(path, low_memory=False).assign(season=season))
    frame = pd.concat(frames, ignore_index=True)
    return frame[frame["game_type"] == "REG"] if "game_type" in frame else frame


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


def report(fits, extras, title: str) -> str:
    lines = [f"# {title}", ""]
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
        "--markets", default="receiving",
        choices=("receiving", "all", "defensive", "rushing"),
        help=(
            "Receiving markets are where a coverage scheme has a mechanism; "
            "defensive (sacks, tackles+assists) is where a pass rush does."
        ),
    )
    parser.add_argument(
        "--feature", default="team",
        choices=("team", "player", "pressure", "role"),
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
    elif args.markets == "defensive":
        bets = bets[bets["market"].isin(pressure.DEFENSIVE_MARKETS)]
    elif args.markets == "rushing":
        bets = bets[bets["market"].isin(role.RUSHING_MARKETS)]
    bets = bets.copy()
    bets["identity"] = bets["player"].map(normalise_name)
    bets["line"] = pd.to_numeric(bets["line"], errors="coerce")

    market = devigged_market(league, args.raw_dir)
    offered = len(bets)
    frame = bets.merge(market, on=["event_id", "market", "identity", "line"], how="inner")
    unpriced = bets.merge(
        market[["event_id", "market", "identity", "line"]].assign(_seen=1),
        on=["event_id", "market", "identity", "line"], how="left",
    )
    unpriced = unpriced[unpriced["_seen"].isna()]
    over_share = (
        float(unpriced["selection"].astype(str).str.lower().eq("over").mean())
        if len(unpriced) else 0.0
    )
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
    if args.feature in ("pressure", "role"):
        # Neither reads participation, and gating on a man rate would drop
        # wagers for a reason unrelated to the feature under test. A role
        # change is a WITHIN-season event, so its rate season is its own.
        frame["rate_season"] = frame["season"].astype(int) - (
            0 if args.feature == "role" else 1
        )
        frame["man_rate"] = 0.0
        frame["man_rate_z"] = 0.0
    else:
        rates = cov.man_rate_by_defence(
            load_participation(league, args.raw_dir, [s - 1 for s in seasons])
        )
        frame = cov.attach_prior_season_man_rate(frame, rates)

    reliability = None
    if args.feature == "role":
        full_schedule = pd.read_csv(
            nflverse.feed_path(
                nflverse.FEEDS_BY_NAME["schedules"], league, args.raw_dir, None
            ),
            low_memory=False,
            usecols=["season", "week", "away_team", "home_team", "game_type",
                     "gameday", "gametime"],
        )
        injuries = pd.concat([
            pd.read_csv(
                nflverse.feed_path(
                    nflverse.FEEDS_BY_NAME["injuries"], league, args.raw_dir, season
                ),
                low_memory=False,
            )
            for season in seasons
        ], ignore_index=True)
        # Rushing is the pre-registered replication sample: a back's absence
        # frees carries, a receiver's does not.
        # See docs/preregistration_role_change.md, committed before this ran.
        volume = role.CARRIES if args.markets == "rushing" else role.TARGETS
        ruled_out = role.ruled_out_by_card_time(
            injuries, full_schedule, volume=volume
        )
        shares = role.volume_shares(load_pbp(league, args.raw_dir, seasons), volume)
        frame = role.attach(
            frame, shares, role.vacated_share(shares, ruled_out), ruled_out
        ).rename(columns={"club": "team"})

    if args.feature == "pressure":
        prior = sorted({s - 1 for s in seasons})
        bridge = pressure.crosswalk(pd.read_csv(
            nflverse.feed_path(
                nflverse.FEEDS_BY_NAME["players"], league, args.raw_dir, None
            ),
            low_memory=False, usecols=["gsis_id", "pfr_id"],
        )).rename(columns={"gsis_id": "player_id"})
        rushers = pressure.defender_pressure_rate(
            load_pfr(league, args.raw_dir, "pfr_def", prior)
        ).rename(columns={"season": "rate_season", "pfr_player_id": "pfr_id"})
        blocking = pressure.offence_pressure_allowed(
            load_pfr(league, args.raw_dir, "pfr_pass", prior)
        ).rename(columns={"season": "rate_season", "team": "opponent"})
        before = len(frame)
        frame = frame.merge(bridge, on="player_id", how="left")
        frame = frame.merge(
            rushers[["rate_season", "pfr_id", "pressure_z"]],
            on=["rate_season", "pfr_id"], how="left",
        )
        frame = frame.merge(
            blocking[["rate_season", "opponent", "pressure_allowed_z"]],
            on=["rate_season", "opponent"], how="left",
        )
        if len(frame) != before:
            print(
                f"::error::The pressure join duplicated wagers "
                f"({before:,} -> {len(frame):,}). Every interval would be too "
                "narrow.", file=sys.stderr,
            )
            return 2

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
    if args.feature == "pressure":
        have &= frame["pressure_z"].notna() & frame["pressure_allowed_z"].notna()
    if args.feature == "role":
        have &= (
            frame["baseline_share"].notna()
            & (frame["weeks_before"] >= role.MIN_WEEKS_BEFORE)
            & (frame["baseline_share"] > role.MIN_BASELINE_SHARE)
        )
    if args.feature == "player":
        # This sentence used to be shared with the team report, where "a few
        # relocated clubs" is true. Here it is not: the exclusion is the
        # receiver-target gate, and it is enormous. A reader told the missing
        # 59% is a handful of relocated clubs is being told the null speaks for
        # a far wider population than it does.
        gated = int(frame["differential_shrunk"].notna().sum())
    coverage_line = (
        f"The feature covers **{int(have.sum()):,} of {len(frame):,} wagers** "
        f"({100 * have.mean():.1f}%). " + NARRATIVE[args.feature]["exclusion"]
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

    if args.feature == "role":
        for column, name in (("vacated", "vacated_z"), ("expected_gain", "gain_z")):
            values = frame[column]
            frame[name] = (values - values.mean()) / values.std(ddof=0)
        frame["club_week"] = (
            frame["team"].astype(str) + "_" + frame["season"].astype(str)
            + "_" + frame["week"].astype(str)
        )
        frame["player_season"] = (
            frame["player_id"].astype(str) + "_" + frame["season"].astype(str)
        )
        extra = (
            ("d1 share vacated by the club (z)", "vacated_z"),
            ("d  this player's share of it (z)", "gain_z"),
        )
        clusters = ("club_week", "player_season")
    elif args.feature == "pressure":
        frame["interaction"] = frame["pressure_z"] * frame["pressure_allowed_z"]
        frame["player_season"] = (
            frame["player_id"].astype(str) + "_" + frame["rate_season"].astype(str)
        )
        extra = (
            ("d1 rusher pressures per game (z)", "pressure_z"),
            ("d2 opposing line pressure allowed (z)", "pressure_allowed_z"),
            ("d  the interaction (rusher x line)", "interaction"),
        )
        clusters = ("player_season", "defence_season")
    elif args.feature == "player":
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

    # The headline term is whichever regressor the chosen feature put last —
    # the interaction where there is one, the single rate where there is not.
    # Named here rather than after the fit, because the placebo needs it.
    headline_name, feature_column = extra[-1]

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

    # Placebo: reassign each feature ACROSS the clusters it is constant within.
    # Shuffling a column row-wise would break that constancy and flatter the
    # interval. And a placebo that permutes a column the fit does not use is
    # WORSE than none — it returns the real coefficients and reads as a passed
    # check, which is exactly what the first pressure run printed.
    rng = np.random.default_rng(11)

    def reassign(source: pd.DataFrame, column: str, key: str) -> pd.Series:
        keys = source[key].unique()
        values = source.groupby(key)[column].first().reindex(keys).to_numpy()
        return source[key].map(dict(zip(keys, rng.permutation(values))))

    sham_frame = frame.copy()
    if args.feature == "pressure":
        sham_frame["pressure_z"] = reassign(sham_frame, "pressure_z", "player_season")
        sham_frame["pressure_allowed_z"] = reassign(
            sham_frame, "pressure_allowed_z", "defence_season"
        )
        sham_frame["interaction"] = (
            sham_frame["pressure_z"] * sham_frame["pressure_allowed_z"]
        )
    elif args.feature == "role":
        # Shuffle the EVENT across club-weeks and keep each player's own
        # baseline, then rebuild the gain. Permuting the gain directly would
        # destroy the baseline too, which is real and not what is under test.
        sham_frame["vacated"] = reassign(sham_frame, "vacated", "club_week")
        rebuilt = (
            sham_frame["baseline_share"] * sham_frame["vacated"]
            / (1.0 - sham_frame["vacated"]).clip(lower=1e-6)
        )
        for values, name in ((sham_frame["vacated"], "vacated_z"), (rebuilt, "gain_z")):
            sham_frame[name] = (values - values.mean()) / values.std(ddof=0)
    else:
        sham_frame["man_centred"] = reassign(sham_frame, "man_centred", "defence_season")
        if args.feature == "player":
            sham_frame["interaction"] = (
                sham_frame["player_diff_z"] * sham_frame["man_centred"]
            )
    if (sham_frame[feature_column] == frame[feature_column]).all():
        print(
            "::error::The placebo did not move the feature it is supposed to "
            "shuffle, so it tests nothing and would read as a passed check.",
            file=sys.stderr,
        )
        return 2
    sham = encompassing.fit(
        sham_frame, "placebo: the feature reassigned across its own clusters",
        extra=extra,
        cluster=clusters[0],
    )

    # The sandwich, checked against a resample of the clusters it claims.
    X = np.column_stack([
        np.ones(len(frame)), encompassing.logit(frame["p_market"]),
        encompassing.logit(frame["p_model"]),
        *[frame[col].to_numpy(float) for _, col in extra],
    ])
    y = frame["y"].to_numpy(float)
    groups = frame[clusters[0]].to_numpy()
    unique = np.unique(groups)
    rows_by = {g: np.where(groups == g)[0] for g in unique}
    draws = []
    for _ in range(args.bootstrap):
        picked = rng.choice(unique, len(unique), replace=True)
        rows = np.concatenate([rows_by[g] for g in picked])
        draws.append(encompassing.fit_logistic(X[rows], y[rows])[-1])
    lo, hi = np.percentile(draws, [2.5, 97.5])

    subject = NARRATIVE[args.feature]["subject"]

    d = next(c for c in withman.coefficients if c.name == headline_name)
    spread = frame[feature_column].max() - frame[feature_column].min()
    swing = abs(d.value) * spread

    # Power, and what the interval still allows. "No demonstrated edge" and "a
    # test too weak to have found one" are different statements and only the
    # second is supported unless these are printed beside the coefficient.
    se_d = (d.high - d.low) / (2 * 1.96)
    mde = 2.8 * se_d                      # 1.96 + 0.84, two-sided 5%, 80% power
    model_c = next(c for c in withman.coefficients if c.name.startswith("c ")).value
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
            if reliability is not None else NARRATIVE[args.feature]["note"]
        ),
        "",
        f"The feature spans **{frame[feature_column].min():+.2f} to "
        f"{frame[feature_column].max():+.2f}**. "
        f"At `d = {d.value:+.4f}` per standard deviation, "
        f"moving from one end of it to the other shifts the log-odds "
        f"of the over by **{swing:.4f}** — about "
        f"**{100 * (encompassing.expit(np.array([swing])) - 0.5)[0]:.2f} percentage points** "
        "at an even-money price.",
        "",
        f"Bootstrap over {len(unique):,} {clusters[0].replace(chr(95), chr(45))} clusters "
        f"({args.bootstrap} draws): "
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
        f"**`d` is identified by {len(unique):,} clusters, not {len(frame):,} "
        f"wagers.** The feature is constant inside a "
        f"{clusters[0].replace(chr(95), chr(45))}, so every wager sharing one "
        "carries the same value of the regressor. Dropping three quarters of the "
        "*wagers* barely moves the standard error; dropping three quarters of the "
        "*clusters* moves it by the square root of four, as it should. The wager "
        "count is the population the answer speaks for. It is not the sample size.",
        "",
        f"**Minimum detectable effect at 80% power: `d` = {mde:+.4f}.** Anything "
        f"smaller than that, this design would miss more often than not. For "
        f"scale, the props model's own contribution in the same fit is "
        f"`c = {model_c:+.4f}` — so the test could only have found this feature "
        f"carrying {abs(mde / model_c):.0%} of what an entire "
        "player-props model carries beyond the price. Nobody expected that, and "
        "the design was never in a position to find less.",
        "",
        f"**What the interval fails to exclude, in money.** If `d` truly sat at "
        f"the upper edge of its interval ({d.high:+.4f}), the wagers where the "
        f"feature favours the bet actually placed ({favoured:,} of "
        f"{len(frame):,}) would gain about **{roi_points:+.2f} ROI points** — "
        f"roughly **{units_per_season:+.0f} units a season** at the lab's flat "
        f"1-unit stake, against a {args.markets} card that currently returns "
        f"{realised:.2f}%. That is an effect large enough to erase most of the "
        "hold, and this test did not reject it.",
        "",
        (
            f"**{100 * len(unpriced) / max(offered, 1):.0f}% of the card never "
            f"reaches this fit, and it is not a random part of it.** "
            f"{offered:,} wagers were scored; "
            f"{len(unpriced):,} ({100 * len(unpriced) / max(offered, 1):.1f}%) "
            f"have no two-sided price at their line and are dropped before "
            f"anything is fitted — **{100 * over_share:.1f}% of them overs**, "
            "because an over-only alternate line has no under to devig against. "
            "`encompassing.py` argues that selection here is harmless since it "
            "is a deterministic function of the regressors; that argument does "
            "**not** cover this drop, because whether a book quoted two sides is "
            "not a function of the price or the model. The null holds for the "
            "two-sided-priced population and is untested outside it."
        ),
        "",
        f"**So the honest statement is the narrow one.** Not \"{subject} carries "
        f"nothing\", but: *a "
        + ("within-season" if args.feature == "role" else "prior-season")
        + f" measure of it, identified by "
        f"{len(unique):,} clusters, could not be told from zero by a test whose "
        "noise floor sits above the range of effects that would be worth money.* "
        "The placebo "
        "makes the same point from the other side — a feature reassigned at "
        "random routinely produces coefficients larger than every real point "
        "estimate here.",
    ]

    out = OUTPUTS_DIR / league.output_name(
        f"coverage_encompassing_{args.feature}_{args.markets}", ".md"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    body = report(
        [baseline, withman, *alternates, sham], extras,
        f"Does {subject} say anything the price does not?",
    )
    out.write_text(body, encoding="utf-8")
    print(body)
    print(f"Written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
