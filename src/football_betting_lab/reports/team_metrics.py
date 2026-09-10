"""Every team metric modern football analysis uses, computed the same way twice.

The point of this module is not that these metrics are new — they are the
standard vocabulary, and any public site quotes most of them. The point is that
each one arrives here **with a denominator that is stated** and then goes
through the reliability screen before anything is built on it, so the board can
show which of them describe the same club a year later and which are decoration.

## Denominators are the whole game

`was_pressure` is False on every run, so a pressure rate over all plays is the
rate multiplied by how often that defence faced a pass — a fact about its
opponents, not its rush. That error moved the league's best pass rush from CLE
to SEA in the first version of the matchup board. Every rate here therefore
carries the count it was measured over, and the reliability screen weights a
club-week by that count rather than treating a three-play week like a
sixty-play one.

## What is offence and what is defence

Every metric is computed for the club **with the ball** and again for the club
defending, from the same plays. A defence's EPA allowed is not a separate
measurement; it is the offence's EPA attributed to the other side. Keeping both
in one long frame is what lets a matchup subtract one from the other without
two pipelines disagreeing about what a play was.

## What this deliberately does not include

Metrics that need charting this lab cannot obtain — pass block win rate, PFF
grades, coverage grades by defender — are absent rather than approximated. An
approximation of a proprietary metric is a different metric with a borrowed
name, and it would be measured here as though it were the real one.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: A gain of this many yards or more is explosive. The pass and rush thresholds
#: differ because the distributions do; using one number for both would make
#: every rushing offence look inexplosive by construction.
EXPLOSIVE_PASS_YARDS = 20
EXPLOSIVE_RUSH_YARDS = 10

#: (key, label, family) for everything this module emits. The screen reads this
#: so a metric cannot be measured without being described.
CATALOGUE: tuple[tuple[str, str, str], ...] = (
    ("epa_play", "EPA per play", "efficiency"),
    ("epa_dropback", "EPA per dropback", "efficiency"),
    ("epa_rush", "EPA per rush", "efficiency"),
    ("success_rate", "success rate", "efficiency"),
    ("success_pass", "success rate, dropbacks", "efficiency"),
    ("success_rush", "success rate, rushes", "efficiency"),
    ("cpoe", "completion % over expected", "passing"),
    ("adot", "average depth of target", "passing"),
    ("air_yards_per_play", "air yards per dropback", "passing"),
    ("proe", "pass rate over expected", "tendency"),
    ("early_down_pass", "early-down pass rate", "tendency"),
    ("shotgun_rate", "shotgun rate", "tendency"),
    ("no_huddle_rate", "no-huddle rate", "tendency"),
    ("explosive_pass", "explosive pass rate", "explosiveness"),
    ("explosive_rush", "explosive rush rate", "explosiveness"),
    ("sack_rate", "sack rate", "trench"),
    ("qb_hit_rate", "quarterback hit rate", "trench"),
    ("stuff_rate", "stuff rate", "trench"),
    ("havoc_rate", "havoc rate", "trench"),
    ("third_down_rate", "third-down conversion rate", "situational"),
    ("red_zone_epa", "EPA per play inside the 20", "situational"),
    ("points_per_drive", "points per drive", "drive"),
    ("three_and_out_rate", "three-and-out rate", "drive"),
    ("plays_per_drive", "plays per drive", "drive"),
)

_DRIVE_POINTS = {
    "Touchdown": 6.94,          # the touchdown plus the conversion actually kicked
    "Field goal": 3.0,
    "Opp touchdown": -6.94,
}


def _rate(frame: pd.DataFrame, keys: list[str], value: str) -> pd.DataFrame:
    """Mean of `value` per group, carrying the count it was measured over."""
    grouped = frame.groupby(keys)[value]
    out = grouped.agg(["mean", "size"]).reset_index()
    return out.rename(columns={"mean": "value", "size": "weight"})


def _emit(frame: pd.DataFrame, side_column: str, side: str, metric: str) -> pd.DataFrame:
    out = frame.rename(columns={side_column: "team"}).copy()
    out["metric"] = metric
    out["side"] = side
    return out[["season", "week", "team", "metric", "side", "value", "weight"]]


def team_week_metrics(pbp: pd.DataFrame) -> pd.DataFrame:
    """Long frame: one row per club-week per metric per side of the ball."""
    plays = pbp[
        (pbp["season_type"] == "REG")
        & pbp["posteam"].notna()
        & pbp["defteam"].notna()
    ].copy()
    for column in ("epa", "yards_gained", "cpoe", "pass_oe", "air_yards", "xpass"):
        plays[column] = pd.to_numeric(plays[column], errors="coerce")
    for flag in ("qb_dropback", "rush_attempt", "sack", "qb_hit", "success",
                 "shotgun", "no_huddle", "complete_pass", "pass_attempt",
                 "tackled_for_loss", "interception", "fumble_forced",
                 "third_down_converted", "third_down_failed"):
        plays[flag] = pd.to_numeric(plays[flag], errors="coerce").fillna(0.0)

    # A "play" for efficiency is a dropback or a rush — never a kick, a kneel or
    # a penalty with no snap, which would otherwise dilute every rate.
    scrimmage = plays[(plays["qb_dropback"] == 1) | (plays["rush_attempt"] == 1)]
    dropbacks = scrimmage[scrimmage["qb_dropback"] == 1]
    rushes = scrimmage[scrimmage["rush_attempt"] == 1]
    attempts = plays[plays["pass_attempt"] == 1]

    keys = ["season", "week"]
    pieces: list[pd.DataFrame] = []

    def both(frame: pd.DataFrame, value: str, metric: str) -> None:
        """The same plays, credited to the offence and to the defence."""
        usable = frame.dropna(subset=[value])
        if usable.empty:
            return
        pieces.append(_emit(_rate(usable, keys + ["posteam"], value), "posteam", "offence", metric))
        pieces.append(_emit(_rate(usable, keys + ["defteam"], value), "defteam", "defence", metric))

    both(scrimmage, "epa", "epa_play")
    both(dropbacks, "epa", "epa_dropback")
    both(rushes, "epa", "epa_rush")
    both(scrimmage, "success", "success_rate")
    both(dropbacks, "success", "success_pass")
    both(rushes, "success", "success_rush")
    both(attempts, "cpoe", "cpoe")
    both(attempts.assign(adot=attempts["air_yards"]), "adot", "adot")
    both(dropbacks.assign(ayp=dropbacks["air_yards"].fillna(0.0)), "ayp", "air_yards_per_play")
    both(scrimmage, "pass_oe", "proe")
    early = scrimmage[scrimmage["down"].isin([1, 2])]
    both(early.assign(edp=early["qb_dropback"]), "edp", "early_down_pass")
    both(scrimmage, "shotgun", "shotgun_rate")
    both(scrimmage, "no_huddle", "no_huddle_rate")
    both(
        dropbacks.assign(ex=(dropbacks["yards_gained"] >= EXPLOSIVE_PASS_YARDS).astype(float)),
        "ex", "explosive_pass",
    )
    both(
        rushes.assign(ex=(rushes["yards_gained"] >= EXPLOSIVE_RUSH_YARDS).astype(float)),
        "ex", "explosive_rush",
    )
    both(dropbacks, "sack", "sack_rate")
    both(dropbacks, "qb_hit", "qb_hit_rate")
    both(
        rushes.assign(st=(rushes["yards_gained"] <= 0).astype(float)),
        "st", "stuff_rate",
    )
    havoc = scrimmage.assign(
        hv=((scrimmage["tackled_for_loss"] + scrimmage["interception"]
             + scrimmage["fumble_forced"]) > 0).astype(float)
    )
    both(havoc, "hv", "havoc_rate")
    thirds = plays[(plays["third_down_converted"] + plays["third_down_failed"]) > 0]
    both(thirds.assign(td=thirds["third_down_converted"]), "td", "third_down_rate")
    red = scrimmage[pd.to_numeric(scrimmage["yardline_100"], errors="coerce") <= 20]
    both(red, "epa", "red_zone_epa")

    # Drives are counted once, not once per play in them.
    drives = plays.dropna(subset=["fixed_drive"]).drop_duplicates(
        subset=["game_id", "posteam", "fixed_drive"]
    ).copy()
    drives["points"] = drives["fixed_drive_result"].map(_DRIVE_POINTS).fillna(0.0)
    both(drives, "points", "points_per_drive")
    drives["plays"] = pd.to_numeric(drives["drive_play_count"], errors="coerce")
    both(drives.dropna(subset=["plays"]), "plays", "plays_per_drive")
    drives["three_out"] = (
        (drives["plays"] <= 3) & (drives["fixed_drive_result"] == "Punt")
    ).astype(float)
    both(drives, "three_out", "three_and_out_rate")

    return pd.concat(pieces, ignore_index=True)


#: Next Gen Stats, aggregated from players to the club that employed them.
#: (file key, value column, weight column, metric key, label, side)
NGS_METRICS: tuple[tuple[str, str, str, str, str, str], ...] = (
    ("passing", "avg_time_to_throw", "attempts", "time_to_throw", "time to throw", "offence"),
    ("passing", "aggressiveness", "attempts", "aggressiveness", "aggressiveness", "offence"),
    ("passing", "avg_air_yards_to_sticks", "attempts", "air_to_sticks", "air yards to sticks", "offence"),
    ("passing", "avg_air_yards_differential", "attempts", "air_differential", "air yards differential", "offence"),
    ("passing", "completion_percentage_above_expectation", "attempts", "cpoe_ngs", "CPOE (Next Gen)", "offence"),
    ("passing", "expected_completion_percentage", "attempts", "expected_completion", "expected completion %", "offence"),
    ("receiving", "avg_separation", "targets", "separation", "receiver separation", "offence"),
    ("receiving", "avg_cushion", "targets", "cushion", "receiver cushion", "offence"),
    ("receiving", "avg_yac_above_expectation", "receptions", "yac_oe", "yards after catch over expected", "offence"),
    ("receiving", "avg_expected_yac", "receptions", "expected_yac", "expected yards after catch", "offence"),
    ("rushing", "rush_yards_over_expected_per_att", "rush_attempts", "ryoe", "rush yards over expected", "offence"),
    ("rushing", "percent_attempts_gte_eight_defenders", "rush_attempts", "eight_box", "carries against eight in the box", "offence"),
    ("rushing", "avg_time_to_los", "rush_attempts", "time_to_los", "time to the line of scrimmage", "offence"),
    ("rushing", "efficiency", "rush_attempts", "rush_efficiency", "rushing efficiency", "offence"),
)


def ngs_team_metrics(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Club-week Next Gen Stats, weighted from the players who produced them.

    A club's separation is the target-weighted mean of its receivers', not the
    mean of their averages: a receiver with four targets must not count as much
    as one with eleven. Week 0 rows are season aggregates in this feed and are
    dropped, or every club-season would be counted twice.
    """
    pieces: list[pd.DataFrame] = []
    for key, column, weight_column, metric, _label, side in NGS_METRICS:
        source = frames.get(key)
        if source is None or column not in source.columns:
            continue
        frame = source.copy()
        frame = frame[
            (frame["season_type"] == "REG") & (pd.to_numeric(frame["week"], errors="coerce") > 0)
        ]
        frame["value"] = pd.to_numeric(frame[column], errors="coerce")
        frame["weight"] = pd.to_numeric(frame[weight_column], errors="coerce")
        frame = frame.dropna(subset=["value", "weight"])
        frame = frame[frame["weight"] > 0]
        if frame.empty:
            continue
        grouped = frame.groupby(["season", "week", "team_abbr"])
        out = grouped.apply(
            lambda part: pd.Series({
                "value": float((part["value"] * part["weight"]).sum() / part["weight"].sum()),
                "weight": float(part["weight"].sum()),
            }),
            include_groups=False,
        ).reset_index().rename(columns={"team_abbr": "team"})
        out["metric"] = metric
        out["side"] = side
        pieces.append(out[["season", "week", "team", "metric", "side", "value", "weight"]])
    return pd.concat(pieces, ignore_index=True) if pieces else pd.DataFrame()


def label_for(metric: str) -> str:
    for key, label, _family in CATALOGUE:
        if key == metric:
            return label
    for _k, _c, _w, key, label, _s in NGS_METRICS:
        if key == metric:
            return label
    return metric


def family_for(metric: str) -> str:
    for key, _label, family in CATALOGUE:
        if key == metric:
            return family
    for _k, _c, _w, key, _label, _s in NGS_METRICS:
        if key == metric:
            return "next gen"
    return "other"
