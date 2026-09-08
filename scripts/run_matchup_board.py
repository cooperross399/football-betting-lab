#!/usr/bin/env python3
"""The matchup board for one week. Spends no credits.

    PYTHONPATH=src python scripts/run_matchup_board.py --season 2026 --week 1

Context, not a card. Six features built from these same feeds have been tested
against the closing line and every one returned no demonstrated edge, so a
layer agreeing with another layer is a description of a matchup and not a
reason to bet it. The board prints the reliability of every layer beside it for
that reason: the reader can see which rows describe the same team a year later
and which are close to noise.

The spread, the total and both implied totals come from the nflverse schedule
and cost nothing. Player prop prices come from a paid provider and are not
fetched.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from football_betting_lab.config import OUTPUTS_DIR, RAW_DIR
from football_betting_lab.data import nflverse
from football_betting_lab.leagues import DEFAULT_LEAGUE_KEY, league_for
from football_betting_lab.reports import matchup_board as mb


def _feed(league, raw_dir: Path, name: str, season: int | None) -> pd.DataFrame:
    path = nflverse.feed_path(nflverse.FEEDS_BY_NAME[name], league, raw_dir, season)
    if not path.is_file():
        raise SystemExit(
            f"::error::No {name} at {path}. Fetch it first; it is free."
        )
    return pd.read_csv(path, low_memory=False)


def render(frame: pd.DataFrame, *, season: int, week: int, profile_season: int,
           injuries_filed: int) -> str:
    lines = [
        f"# Week {week}, {season} — matchup board",
        "",
        f"Profiles are the **{profile_season} season**, which for Week {week} is "
        "what exists. Every figure is a z-score across the league that season, "
        "never a raw rate: league-wide levels move between seasons and a raw "
        "number is two different rulers.",
        "",
        "**This is context, not a card.** Six features built from these feeds "
        "have been tested against the closing line and all six returned no "
        "demonstrated edge. A layer agreeing with another layer describes a "
        "matchup; it does not price one. The layers are also correlated with "
        "each other by construction, so four of them agreeing is closer to one "
        "opinion than to four.",
        "",
        "## What each layer is worth",
        "",
        "Carryover of relative position, measured by "
        "`scripts/run_feature_reliability.py`: how well the statistic describes "
        "the same club a year later. **A layer near zero cannot carry a read "
        "however confident the prose around it sounds.**",
        "",
        "| layer | carryover | |",
        "|:--|--:|:--|",
    ]
    for layer in sorted(mb.LAYERS, key=lambda l: -l.reliability):
        verdict = (
            "usable" if layer.reliability >= 0.40
            else "weak" if layer.reliability >= 0.20 else "**close to noise**"
        )
        lines.append(f"| {layer.label} | {layer.reliability:+.3f} | {verdict} |")

    lines += [
        "",
        "## The games",
        "",
        "`spread` is from the home side: positive means the home club is "
        "favoured by it. Implied totals are `(total ± spread) / 2`.",
        "",
        "| kickoff | game | spread | total | implied (A/H) | pass-rush edge A | pass-rush edge H |",
        "|:--|:--|--:|--:|:--|--:|--:|",
    ]
    for row in frame.itertuples():
        def show(value: float, digits: int = 2) -> str:
            return "—" if pd.isna(value) else f"{value:+.{digits}f}"
        implied = (
            "—" if pd.isna(row.away_implied)
            else f"{row.away_implied:.2f} / {row.home_implied:.2f}"
        )
        lines.append(
            f"| {row.kickoff} | {row.away} @ {row.home} | "
            f"{'—' if pd.isna(row.spread_line) else f'{row.spread_line:+.1f}'} | "
            f"{'—' if pd.isna(row.total_line) else f'{row.total_line:.1f}'} | "
            f"{implied} | {show(row.away_rush_edge)} | {show(row.home_rush_edge)} |"
        )

    lines += [
        "",
        "**Pass-rush edge** adds a club's own pressure rate generated to the "
        "pressure its opponent's line allowed, both as z-scores, because the "
        "two halves point the same way. Both halves are CLUB-level and carry "
        "+0.439 and +0.391 — not the +0.884 that belongs to an individual "
        "defender's pressures per game, which is a different statistic and is "
        "not what this column is built from. Even that stronger one was **no "
        "demonstrated edge** against the price when tested directly on sack "
        "markets.",
        "",
        "## The per-club profiles",
        "",
        "| club | " + " | ".join(l.label for l in mb.LAYERS) + " |",
        "|:--|" + "--:|" * len(mb.LAYERS),
    ]
    seen: dict[str, dict] = {}
    for row in frame.itertuples():
        for side in ("home", "away"):
            club = getattr(row, side)
            seen[club] = {l.key: getattr(row, f"{side}_{l.key}") for l in mb.LAYERS}
    for club in sorted(seen):
        cells = " | ".join(
            "—" if pd.isna(seen[club][l.key]) else f"{seen[club][l.key]:+.2f}"
            for l in mb.LAYERS
        )
        lines.append(f"| {club} | {cells} |")

    lines += [
        "",
        "## What is not here",
        "",
        f"- **Player prop prices.** Paid provider; not fetched. Nothing above "
        "prices a player market.",
        f"- **The role and injury layer.** {injuries_filed} report rows carry a "
        f"status for Week {week} so far — clubs file on the Wednesday. An empty "
        "layer is shown empty rather than filled with zeroes that would read as "
        "\"nobody is hurt\".",
        "- **Coach and player quotes.** Proprietary, with no free equivalent, "
        "and the layer with the least behind it: a feed that scores almost "
        "every team positive cannot discriminate between them.",
        "",
        nflverse.ATTRIBUTION,
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", default=DEFAULT_LEAGUE_KEY)
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--week", type=int, default=1)
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    args = parser.parse_args(argv)
    league = league_for(args.league)
    prior = args.season - 1

    profiles = mb.team_profiles(
        _feed(league, args.raw_dir, "participation", prior),
        _feed(league, args.raw_dir, "pfr_pass", prior),
        _feed(league, args.raw_dir, "pfr_def", prior),
        _feed(league, args.raw_dir, "pfr_rush", prior),
    )
    schedule = _feed(league, args.raw_dir, "schedules", None)
    frame = mb.board(schedule, profiles, season=args.season, week=args.week)
    if frame.empty:
        print(f"::error::No Week {args.week} games for {args.season}.", file=sys.stderr)
        return 2

    try:
        injuries = _feed(league, args.raw_dir, "injuries", args.season)
        filed = int(
            injuries[(injuries["week"] == args.week)]["report_status"].notna().sum()
        )
    except SystemExit:
        filed = 0

    body = render(
        frame, season=args.season, week=args.week,
        profile_season=prior, injuries_filed=filed,
    )
    out = OUTPUTS_DIR / league.output_name(f"matchup_board_{args.season}_wk{args.week}", ".md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")
    frame.to_csv(out.with_suffix(".csv"), index=False)
    print(body)
    print(f"Written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
