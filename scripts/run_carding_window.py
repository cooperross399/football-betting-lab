#!/usr/bin/env python3
"""When is each game actually carded? Spends nothing, touches no network.

    PYTHONPATH=src python scripts/run_carding_window.py --season 2026

`CLAUDE.md` carried this table written by hand and three of its numbers were
wrong: it assumed ET is UTC-4 across a season that runs into January, it took
the last run before kickoff rather than the first run of the day that the
standdown guard actually leaves standing, and it counted six uncardable games
where there are four. The rule this lab keeps rediscovering is that a number no
script generates is a number nothing catches, so this is the script.

The answer is read from the workflow's own cron expressions. A table that
restates a schedule is a table that can disagree with it.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from football_betting_lab.config import OUTPUTS_DIR, PROJECT_ROOT, RAW_DIR
from football_betting_lab.leagues import DEFAULT_LEAGUE_KEY, league_for
from football_betting_lab.reports import carding_window


CARD_WORKFLOW = PROJECT_ROOT / ".github" / "workflows" / "football-gameday-refresh.yml"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", default=DEFAULT_LEAGUE_KEY)
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--workflow", type=Path, default=CARD_WORKFLOW)
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    args = parser.parse_args(argv)
    league = league_for(args.league)

    if not args.workflow.is_file():
        print(
            f"::error::No workflow at {args.workflow}. The carding window is "
            "computed from the crons that actually run; it is not restated "
            "here and cannot be computed without them.",
            file=sys.stderr,
        )
        return 2

    crons = carding_window.parse_workflow_crons(
        args.workflow.read_text(encoding="utf-8")
    )
    if not crons:
        print(
            f"::error::{args.workflow} has no `schedule:` cron. Either the card "
            "no longer runs on a schedule — in which case nothing is carded "
            "without a human — or this parser has drifted from the file.",
            file=sys.stderr,
        )
        return 2

    rows = carding_window.carding_rows(
        league, args.raw_dir, season=args.season, crons=crons
    )
    if not rows:
        print(
            f"::error::The schedule cache knows no {args.season} regular-season "
            "games. That is an absence, not a season with nothing in it.",
            file=sys.stderr,
        )
        return 2

    dark = carding_window.days_without_any_run(rows, crons, league)
    report = carding_window.render(
        rows, crons, season=args.season, league=league, dark_days=dark
    )
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUTS_DIR / league.output_name("carding_window", ".md")
    path.write_text(report, encoding="utf-8")

    carded = [r for r in rows if r.carded]
    inside = [r for r in rows if r.inside_inactives]
    print(f"{len(rows)} games; {len(carded)} carded; {len(rows) - len(carded)} with no run before kickoff.")
    print(f"{len(inside)} carded inside the {carding_window.INACTIVES_LEAD_MINUTES}-minute inactives window.")
    for row in inside:
        print(f"  {row.game_id} {row.league_date} {row.kickoff_et} ET — {row.operative_lead_hours * 60:.0f} min")
    if dark:
        print(f"::warning::{len(dark)} game day(s) have no cron firing at all: {dark}")
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
