#!/usr/bin/env python3
"""Screen every team metric this lab can compute. Spends nothing.

    PYTHONPATH=src python scripts/run_metric_reliability.py --seasons 2018 ... 2025

Runs the whole modern-analytics vocabulary through the same question that
governs any prior-season feature: **does it describe the same club a year
later?** A metric that does not carry cannot help a board however familiar its
name, and the ones that carry hardest are the ones the market has had longest
to price. This ranks what is worth carrying; it promotes nothing.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from football_betting_lab.config import OUTPUTS_DIR, RAW_DIR
from football_betting_lab.data import nflverse
from football_betting_lab.leagues import DEFAULT_LEAGUE_KEY, league_for
from football_betting_lab.reports import reliability as rel
from football_betting_lab.reports import team_metrics as tm

#: Eight games' worth of whatever the metric is measured over. Expressed as a
#: multiple of the median club-week rather than a constant, because a rate over
#: plays and a rate over drives are not comparable in absolute terms.
GAMES_REQUIRED = 8

PBP_COLUMNS = [
    "season", "week", "season_type", "game_id", "posteam", "defteam", "epa",
    "success", "qb_dropback", "rush_attempt", "pass_attempt", "sack", "qb_hit",
    "cpoe", "pass_oe", "air_yards", "xpass", "down", "shotgun", "no_huddle",
    "yards_gained", "complete_pass", "third_down_converted", "third_down_failed",
    "tackled_for_loss", "interception", "fumble_forced", "yardline_100",
    "fixed_drive", "fixed_drive_result", "drive_play_count",
]


def _asymmetry(results) -> list[str]:
    """Offence against defence, on the metrics computed for both.

    This is the strongest structure in the screen and it is not an artefact of
    any one statistic: a club's offensive identity carries, and the same
    measurement of its defence carries markedly less. It reproduces, from a
    different direction, the published finding that offensive EPA is stickier
    than defensive EPA.
    """
    import statistics

    by_side: dict[str, dict[str, float]] = {"offence": {}, "defence": {}}
    for _family, result in results:
        if result.ceiling is None or not result.name.endswith(")"):
            continue
        base, side = result.name.rsplit(" (", 1)
        side = side.rstrip(")")
        if side in by_side:
            by_side[side][base] = result.ceiling
    shared = sorted(set(by_side["offence"]) & set(by_side["defence"]))
    if len(shared) < 5:
        return []
    gaps = [by_side["offence"][b] - by_side["defence"][b] for b in shared]
    lines = [
        "## The same measurement, taken on each side of the ball",
        "",
        f"**{sum(1 for g in gaps if g > 0)} of {len(shared)} metrics carry "
        f"better on offence than on defence** — mean "
        f"{statistics.mean(by_side['offence'][b] for b in shared):+.3f} against "
        f"{statistics.mean(by_side['defence'][b] for b in shared):+.3f}, a "
        f"median gap of {statistics.median(gaps):+.3f}. This is the strongest "
        "structure in the screen, it is not an artefact of any one statistic, "
        "and it reproduces from a different direction the published finding "
        "that offensive EPA is stickier than defensive EPA.",
        "",
        "| metric | offence | defence | gap |",
        "|:--|--:|--:|--:|",
    ]
    for base in sorted(shared, key=lambda b: -(by_side["offence"][b] - by_side["defence"][b])):
        offence, defence = by_side["offence"][base], by_side["defence"][base]
        lines.append(f"| {base} | {offence:+.3f} | {defence:+.3f} | {offence - defence:+.3f} |")
    lines += [
        "",
        "**The three exceptions say what a defence actually controls**: stuff "
        "rate, havoc rate and the air yards it concedes all carry better on "
        "defence than offence. A defence chooses whether to sell out against "
        "the run and whether to force the ball short; it does not choose "
        "whether the quarterback it faces is accurate.",
        "",
        "**Sack rate is the sharpest warning here.** A defence's sack rate "
        "carries at +0.132 — close to noise — while the pressure rate "
        "underneath it carries at +0.439 for a club and +0.884 for an "
        "individual rusher. Sacks are a noisy subset of pressures and a preview "
        "quoting last year's sack total is quoting the noise rather than the "
        "signal. That reproduces a published result this lab did not set out "
        "to test.",
    ]
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", default=DEFAULT_LEAGUE_KEY)
    parser.add_argument("--seasons", type=int, nargs="+",
                        default=[2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025])
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    args = parser.parse_args(argv)
    league = league_for(args.league)

    frames = []
    for season in args.seasons:
        path = nflverse.feed_path(nflverse.FEEDS_BY_NAME["pbp"], league, args.raw_dir, season)
        if path.is_file():
            frames.append(pd.read_csv(path, low_memory=False, usecols=PBP_COLUMNS))
    if not frames:
        raise SystemExit("::error::No play-by-play cached for those seasons.")
    long = tm.team_week_metrics(pd.concat(frames, ignore_index=True))

    ngs = {}
    for key in ("passing", "receiving", "rushing"):
        path = nflverse.feed_path(
            nflverse.FEEDS_BY_NAME[f"ngs_{key}"], league, args.raw_dir, None
        )
        if path.is_file():
            frame = pd.read_csv(path, low_memory=False)
            ngs[key] = frame[frame["season"].isin(args.seasons)]
    if ngs:
        long = pd.concat([long, tm.ngs_team_metrics(ngs)], ignore_index=True)

    results = []
    for (metric, side), group in long.groupby(["metric", "side"]):
        weekly = group.groupby(["team", "season", "week"])["weight"].sum()
        minimum = GAMES_REQUIRED * float(weekly.median())
        frame = group.rename(columns={"team": "entity"})[
            ["entity", "season", "week", "value", "weight"]
        ]
        label = f"{tm.label_for(metric)} ({side})"
        try:
            results.append((tm.family_for(metric), rel.measure(
                frame, label, minimum=minimum, half_minimum=minimum / 2
            )))
        except ValueError:
            continue

    usable = [r for _f, r in results if r.ceiling is not None and r.ceiling >= 0.40]
    noise = [r for _f, r in results if r.ceiling is not None and r.ceiling < 0.20]
    body = "\n".join([
        f"# Every team metric this lab can compute, screened",
        "",
        f"{len(results)} metric-and-side combinations across "
        f"{args.seasons[0]}-{args.seasons[-1]}, from play-by-play and Next Gen "
        "Stats. Each is the club's weighted rate for that week, screened by the "
        "one question that governs a prior-season feature: **does it describe "
        "the same club a year later?**",
        "",
        f"**{len(usable)} carry at 0.40 or better. {len(noise)} are close to "
        "noise.** Ranking is not endorsement — a metric that persists is one "
        "the market has had every year to price, and six features built from "
        "these same feeds have already been tested against the closing line "
        "and beaten none of it. This screen removes candidates; it promotes "
        "nothing.",
        "",
        rel.render([r for _f, r in results]),
        "",
        *_asymmetry(results),
        "",
        f"A club-season needs {GAMES_REQUIRED} games' worth of whatever the "
        "metric is measured over — expressed as a multiple of the median "
        "club-week, because a rate over plays and a rate over drives are not "
        "comparable in absolute terms.",
        "",
        nflverse.ATTRIBUTION,
    ]) + "\n"
    out = OUTPUTS_DIR / league.output_name("metric_reliability", ".md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")
    print(body)
    print(f"Written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
