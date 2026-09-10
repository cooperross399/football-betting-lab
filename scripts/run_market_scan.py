#!/usr/bin/env python3
"""Where do the metrics disagree with the line, and was that ever worth it?

    PYTHONPATH=src python scripts/run_market_scan.py --seasons 2010 ... 2025

The board sets metrics beside a price. This asks the different question: build a
rating from the metrics that survived the reliability screen, predict the margin
and the total, subtract the market's own number, and bet the difference.

Spends nothing. The closing spread and total come free with the schedule.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from football_betting_lab.config import OUTPUTS_DIR, RAW_DIR
from football_betting_lab.data import nflverse
from football_betting_lab.leagues import DEFAULT_LEAGUE_KEY, league_for
from football_betting_lab.reports import market_scan as ms
from football_betting_lab.reports import team_metrics as tm

PBP_COLUMNS = [
    "season", "week", "season_type", "game_id", "posteam", "defteam", "epa",
    "success", "qb_dropback", "rush_attempt", "pass_attempt", "sack", "qb_hit",
    "cpoe", "pass_oe", "air_yards", "xpass", "down", "shotgun", "no_huddle",
    "yards_gained", "complete_pass", "third_down_converted", "third_down_failed",
    "tackled_for_loss", "interception", "fumble_forced", "yardline_100",
    "fixed_drive", "fixed_drive_result", "drive_play_count",
]
THRESHOLDS = (0.0, 1.0, 2.0, 3.0, 4.0, 6.0)


def interval(profit: pd.Series, games: pd.Series, *, draws: int = 2000, seed: int = 5):
    """Bootstrap over GAMES, because a game supplies both its markets."""
    rng = np.random.default_rng(seed)
    keys = games.unique()
    rows = {k: np.where(games.to_numpy() == k)[0] for k in keys}
    values = profit.to_numpy(float)
    means = []
    for _ in range(draws):
        picked = rng.choice(keys, len(keys), replace=True)
        idx = np.concatenate([rows[k] for k in picked])
        means.append(values[idx].mean())
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", default=DEFAULT_LEAGUE_KEY)
    parser.add_argument("--seasons", type=int, nargs="+",
                        default=list(range(2010, 2026)))
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    args = parser.parse_args(argv)
    league = league_for(args.league)

    frames = []
    for season in args.seasons:
        path = nflverse.feed_path(nflverse.FEEDS_BY_NAME["pbp"], league, args.raw_dir, season)
        if path.is_file():
            frames.append(pd.read_csv(path, low_memory=False, usecols=PBP_COLUMNS))
    long = tm.team_week_metrics(pd.concat(frames, ignore_index=True))
    form = ms.club_form(long)

    schedule = pd.read_csv(
        nflverse.feed_path(nflverse.FEEDS_BY_NAME["schedules"], league, args.raw_dir, None),
        low_memory=False,
    )
    games = schedule[
        (schedule["game_type"] == "REG") & schedule["season"].isin(args.seasons)
    ].copy()
    games["total"] = games["home_score"] + games["away_score"]
    result = ms.scan(games, form)
    if result.frame.empty:
        print("::error::Nothing scored.")
        return 2

    frame = result.frame
    lines = [
        "# Where the metrics disagree with the line",
        "",
        f"{len(frame):,} games, {frame['season'].min()}-{frame['season'].max()}. "
        "A club's rating comes from its own prior games only; the mapping from "
        "rating to points is refitted for each season on the seasons before it. "
        "Nothing sees the game it is pricing, or the rest of the week it is in.",
        "",
        "## How far apart the two are",
        "",
        "| | mean absolute divergence | correlation with the result |",
        "|:--|--:|--:|",
    ]
    for kind, prediction, line_col, actual in (
        ("margin", "model_margin", "spread_line", "result"),
        ("total", "model_total", "total_line", "total"),
    ):
        divergence = frame[prediction] - frame[line_col]
        residual = frame[actual] - frame[line_col]
        lines.append(
            f"| {kind} | {divergence.abs().mean():.2f} points | "
            f"{np.corrcoef(divergence, residual)[0, 1]:+.4f} |"
        )
    lines += [
        "",
        "**The correlation is the whole result, and both are slightly "
        "NEGATIVE.** It asks whether the metrics point the right way about what "
        "the line got wrong. Near zero means the disagreement is noise however "
        "large it is — and the model disagrees by about three points a game, so "
        "the disagreement is not small. It is simply uninformative, and if "
        "anything it leans the wrong way.",
        "",
        "## Betting the disagreement, at -110",
        "",
        "| threshold | market | bets | ROI | 95% interval |",
        "|--:|:--|--:|--:|:--|",
    ]
    verdicts = []
    for threshold in THRESHOLDS:
        settled = ms.settle(frame, threshold=threshold)
        if settled.empty:
            continue
        for market, part in settled.groupby("market"):
            low, high = interval(part["profit"], part["game_id"])
            roi = float(part["profit"].mean())
            verdicts.append((threshold, market, roi, low, high, len(part)))
            lines.append(
                f"| {threshold:.0f} pts | {market} | {len(part):,} | "
                f"{100 * roi:+.2f}% | [{100 * low:+.2f}%, {100 * high:+.2f}%] |"
            )
    wins = [v for v in verdicts if v[3] > 0]
    losses = [v for v in verdicts if v[4] < 0]
    best = max(verdicts, key=lambda v: v[2]) if verdicts else None
    lines += [
        "",
        (
            f"**{len(wins)} of {len(verdicts)} rules return an interval "
            "excluding zero on the profitable side.**"
            if wins else
            f"**No rule is profitable at any threshold, in either market.** "
            f"All {len(verdicts)} rules tried are reported, so the count is "
            "the multiplicity."
        ),
        "",
        (
            f"**{len(losses)} of them exclude zero on the LOSING side**, so at "
            "those thresholds this is a demonstrated loss rather than a null. "
            "Betting where the metrics disagree with the line does worse than "
            "not betting."
            if losses else
            "No rule excludes zero in either direction."
        ),
        "",
        (
            f"The best point estimate is {100 * best[2]:+.2f}% on {best[5]:,} "
            f"{best[1]} bets at the {best[0]:.0f}-point threshold — with an "
            f"interval of [{100 * best[3]:+.2f}%, {100 * best[4]:+.2f}%]. That "
            "is what noise looks like when a filter has cut the sample to a few "
            "hundred, and it is the reason every threshold is printed rather "
            "than the flattering one."
            if best else ""
        ),
        "",
        "A bet at -110 needs **52.38%** to break even, so a rule has to be "
        "right more than half the time by a clear margin before the hold is "
        "paid. Line shopping recovers about 4.7 points of hold across thirteen "
        "books but never reaches zero (`nfl_shopping_value.md`), so a losing "
        "rule stays losing at every book count.",
        "",
        "## What this does and does not settle",
        "",
        "It is the direct form of the question the board could not answer: not "
        "*are these clubs different*, which they plainly are, but *does the "
        "difference the metrics see land anywhere the price has not already "
        "been*. The rating is deliberately simple — trailing form on the "
        "metrics that survived the screen, mapped to points by least squares — "
        "because a more elaborate one fitted on the same history would be "
        "measuring the elaboration.",
        "",
        f"The mapping trains on up to {result.trained_on:,} prior games, and "
        "the first scored season is the first with enough history behind it.",
    ]
    body = "\n".join(lines) + "\n"
    out = OUTPUTS_DIR / league.output_name("market_scan", ".md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")
    frame.to_csv(out.with_suffix(".csv"), index=False)
    print(body)
    print(f"Written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
