#!/usr/bin/env python3
"""Does each candidate feature correlate with itself? Spends nothing.

    PYTHONPATH=src python scripts/run_feature_reliability.py --raw-dir <dir>

Run this BEFORE testing anything against a price. Three matchup features were
measured against the closing line before they were measured against themselves,
and all three returned nothing that was predictable in minutes from free data.

A season value is the weight-weighted mean of the per-game values, so a
two-target game does not count as much as a twelve-target one. Where a feed
publishes no natural denominator the weight is one per game, and the table says
so — that adds noise and therefore understates reliability, which is the safe
direction for a screen whose job is to decide what deserves a real test.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from football_betting_lab.config import OUTPUTS_DIR, RAW_DIR
from football_betting_lab.data import nflverse
from football_betting_lab.leagues import DEFAULT_LEAGUE_KEY, league_for
from football_betting_lab.reports import coverage_feature as cov
from football_betting_lab.reports import reliability as rel

PFR_SEASONS = (2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025)
PARTICIPATION_SEASONS = (2022, 2023, 2024, 2025)

#: (label, feed, value column, weight column or None, minimum, half minimum).
#: `None` weight means one per game — no denominator is published.
PFR_FEATURES = (
    ("passer rating allowed (defender)", "pfr_def", "def_passer_rating_allowed", "def_targets", 40, 20),
    ("yards allowed per target (defender)", "pfr_def", "def_yards_allowed_per_tgt", "def_targets", 40, 20),
    ("completion % allowed (defender)", "pfr_def", "def_completion_pct", "def_targets", 40, 20),
    ("average depth of target faced (defender)", "pfr_def", "def_adot", "def_targets", 40, 20),
    ("missed tackle % (defender)", "pfr_def", "def_missed_tackle_pct", None, 8, 4),
    ("pressures per game (defender)", "pfr_def", "def_pressures", None, 8, 4),
    ("yards before contact per rush", "pfr_rush", "rushing_yards_before_contact_avg", "carries", 60, 30),
    ("yards after contact per rush", "pfr_rush", "rushing_yards_after_contact_avg", "carries", 60, 30),
    ("broken tackles per game (rusher)", "pfr_rush", "rushing_broken_tackles", None, 8, 4),
    ("drop % (receiver)", "pfr_rec", "receiving_drop_pct", None, 8, 4),
    ("passer rating when targeted (receiver)", "pfr_rec", "receiving_rat", None, 8, 4),
    ("broken tackles per game (receiver)", "pfr_rec", "receiving_broken_tackles", None, 8, 4),
    ("pressure rate faced (quarterback)", "pfr_pass", "times_pressured_pct", None, 8, 4),
    ("bad throw % (quarterback)", "pfr_pass", "passing_bad_throw_pct", None, 8, 4),
    ("times blitzed per game (quarterback)", "pfr_pass", "times_blitzed", None, 8, 4),
    ("sacks taken per game (quarterback)", "pfr_pass", "times_sacked", None, 8, 4),
)


def load_pfr(league, raw_dir: Path, feed_name: str) -> pd.DataFrame:
    feed = nflverse.FEEDS_BY_NAME[feed_name]
    frames = []
    for season in PFR_SEASONS:
        path = nflverse.feed_path(feed, league, raw_dir, season)
        if path.is_file():
            frames.append(pd.read_csv(path, low_memory=False))
    if not frames:
        raise SystemExit(f"::error::No {feed_name} files under {raw_dir}.")
    frame = pd.concat(frames, ignore_index=True)
    return frame[frame["game_type"] == "REG"] if "game_type" in frame else frame


def participation_features(league, raw_dir: Path) -> list[rel.Reliability]:
    feed = nflverse.FEEDS_BY_NAME["participation"]
    frames = []
    for season in PARTICIPATION_SEASONS:
        path = nflverse.feed_path(feed, league, raw_dir, season)
        if path.is_file():
            frames.append(pd.read_csv(
                path, low_memory=False,
                usecols=["nflverse_game_id", "possession_team", "defense_man_zone_type",
                         "number_of_pass_rushers", "was_pressure", "defenders_in_box",
                         "time_to_throw"],
            ))
    if not frames:
        return []
    plays = pd.concat(frames, ignore_index=True)
    parts = plays["nflverse_game_id"].astype(str).str.split("_")
    plays["season"] = parts.str[0].astype(int)
    plays["week"] = parts.str[1].astype(int)
    plays["entity"] = cov.defence_of_each_play(plays)

    out = []
    charted = plays[plays["defense_man_zone_type"].isin(cov.MAN_LABELS)]
    definitions = (
        ("man coverage rate (defence)", charted,
         (charted["defense_man_zone_type"] == cov.MAN).astype(float)),
        ("blitz rate, 5+ rushers (defence)", plays,
         (pd.to_numeric(plays["number_of_pass_rushers"], errors="coerce") >= 5).astype(float)),
        ("pressure rate generated (defence)", plays,
         pd.to_numeric(plays["was_pressure"], errors="coerce")),
        ("defenders in box (defence)", plays,
         pd.to_numeric(plays["defenders_in_box"], errors="coerce")),
        ("time to throw allowed (defence)", plays,
         pd.to_numeric(plays["time_to_throw"], errors="coerce")),
    )
    for label, source, values in definitions:
        frame = pd.DataFrame({
            "entity": source["entity"], "season": source["season"],
            "week": source["week"], "value": values.to_numpy(float),
            "weight": 1.0,
        })
        out.append(rel.measure(frame, label, minimum=300, half_minimum=150))
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", default=DEFAULT_LEAGUE_KEY)
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    args = parser.parse_args(argv)
    league = league_for(args.league)

    results: list[rel.Reliability] = []
    cache: dict[str, pd.DataFrame] = {}
    unweighted: list[str] = []
    for label, feed_name, column, weight_column, minimum, half in PFR_FEATURES:
        if feed_name not in cache:
            cache[feed_name] = load_pfr(league, args.raw_dir, feed_name)
        source = cache[feed_name]
        if column not in source.columns:
            print(f"  skipped {label}: no column {column}")
            continue
        weight = (
            pd.to_numeric(source[weight_column], errors="coerce")
            if weight_column else pd.Series(1.0, index=source.index)
        )
        if weight_column is None:
            unweighted.append(label)
        frame = pd.DataFrame({
            "entity": source["pfr_player_id"].astype(str),
            "season": source["season"].astype(int),
            "week": source["week"].astype(int),
            "value": pd.to_numeric(source[column], errors="coerce"),
            "weight": weight,
        })
        results.append(rel.measure(frame, label, minimum=minimum, half_minimum=half))

    results += participation_features(league, args.raw_dir)

    body = "\n".join([
        "# Does each feature correlate with itself?",
        "",
        "Run before any feature is tested against a price. **Year over year is "
        "the column that governs**: a live card can only ever hold the prior "
        "season, so a feature that does not persist cannot help however "
        "precisely it is measured. Split-half says how noisy the measurement "
        "is; the two answer different questions and a high split-half beside a "
        "zero carryover means *we measure last year's team perfectly, and last "
        "year's team has left*.",
        "",
        rel.render(results),
        "",
        f"Player features span {PFR_SEASONS[0]}-{PFR_SEASONS[-1]} "
        f"({len(PFR_SEASONS) - 1} year-over-year transitions); defence features "
        f"span {PARTICIPATION_SEASONS[0]}-{PARTICIPATION_SEASONS[-1]} "
        f"({len(PARTICIPATION_SEASONS) - 1}), because participation charting "
        "is 47 MB a season and earlier ones are not cached.",
        "",
        "Features weighted one-per-game rather than by a published denominator, "
        "because the feed does not publish one — this adds noise and so "
        "**understates** their reliability: "
        + ", ".join(f"*{name}*" for name in unweighted) + ".",
        "",
        "A correlation near zero is not proof the underlying thing is "
        "irrelevant to football. It is proof that this measurement of it, at "
        "this sample size, carries almost nothing — which is the only question "
        "worth answering before spending a season's credits on it.",
    ]) + "\n"

    out = OUTPUTS_DIR / league.output_name("feature_reliability", ".md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")
    print(body)
    print(f"Written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
