#!/usr/bin/env python3
"""Record hypotheses into the cumulative ledger. Spends nothing.

    PYTHONPATH=src python scripts/record_experiments.py --backfill

Every search this lab runs appends here, and the correction factor it hands
back grows with the count. Run with `--backfill` once to seed it with what has
already been tested; after that each search records its own.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import date
from pathlib import Path

from football_betting_lab.config import OUTPUTS_DIR, PROJECT_ROOT
from football_betting_lab.experiment_ledger import (
    LEDGER_FILENAME,
    Hypothesis,
    load,
    render,
    save,
)


def committed_entry_count(path: Path, *, repository: Path | None = None) -> int:
    """How many entries the ledger holds at `HEAD`, or 0 when git cannot say.

    The floor `save()` is handed is the count this run loaded, which is only
    a floor against the run's own edits. A ledger hand-edited *before* the run
    is already short when it is loaded, so the second floor is the copy git
    has committed. Zero — not an error — when there is no repository, no
    `HEAD`, or no tracked ledger: those are honest first-run states, and the
    diff-level guard in `.github/workflows/ledger-guard.yml` is what refuses a
    shrink that never passed through this script at all.
    """
    repository = PROJECT_ROOT if repository is None else repository
    try:
        relative = Path(path).resolve().relative_to(Path(repository).resolve())
    except ValueError:
        return 0
    completed = subprocess.run(
        ["git", "show", f"HEAD:{relative.as_posix()}"],
        cwd=repository,
        capture_output=True,
    )
    if completed.returncode != 0:
        return 0
    try:
        payload = json.loads(completed.stdout.decode("utf-8"))
        entries = payload.get("hypotheses", [])
    except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
        return 0
    return len(entries) if isinstance(entries, list) else 0

#: Everything put to the bought population before the ledger existed. Recorded
#: so the correction starts from the truth rather than from zero — a lab that
#: has tested forty things and counts one is worse off than one that never
#: corrected at all, because it reports a number that looks careful.
BACKFILL: tuple[tuple[str, tuple[str, ...], tuple[int, ...], str], ...] = (
    ("subgroup-search", (
        "blowout risk", "edge magnitude", "odds range", "line magnitude",
        "week of season", "position", "target share", "rest", "weather",
        "home/away", "game total", "book",
    ), (2023, 2024), "0 survivors"),
    ("feature-search", (
        "opponent defensive strength", "player role level", "role trend",
        "game script", "rest and schedule", "weather", "position",
        "defence x role interaction", "all features combined",
    ), (2023, 2024), "0 survivors"),
    ("props-replication", (
        "anytime_td", "defensive_interceptions", "field_goals", "kicking_points",
        "pass_attempts", "pass_completions", "pass_interceptions",
        "pass_longest_completion", "pass_tds", "pass_yards", "reception_longest",
        "reception_yards", "receptions", "rush_attempts", "rush_longest",
        "rush_yards", "sacks", "tackles_assists",
    ), (2023, 2024, 2025), "no demonstrated edge"),
    ("model-variants", (
        "recency weighting half-life 8", "first-half scoring model",
        "walk-forward isotonic calibration",
    ), (2023, 2024, 2025), "recency and half-model do not ship"),
    ("team-markets", (
        "moneyline into the close", "spread into the close", "total into the close",
        "alternate_spread at card time", "alternate_total_points at card time",
        "alternate_team_total at card time", "team_total at card time",
    ), (2023, 2024, 2025), "no demonstrated edge"),
    ("joint-distribution", (
        "receptions x reception_yards correlation",
        "reception_yards x reception_longest correlation",
        "rush_attempts x rush_yards correlation",
        "rush_yards x rush_longest correlation",
    ), (2025,), "joint accurate; not monetizable without parlay prices"),
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backfill", action="store_true")
    parser.add_argument("--search", default="")
    parser.add_argument("--hypotheses", nargs="*", default=[])
    parser.add_argument("--seasons", type=int, nargs="*", default=[])
    parser.add_argument("--outcome", default="")
    parser.add_argument("--tested-on", default=date.today().isoformat())
    args = parser.parse_args(argv)

    path = OUTPUTS_DIR / LEDGER_FILENAME
    ledger = load(path)
    before = ledger.count
    # The floor is measured BEFORE anything is recorded, and it is the larger
    # of what this run loaded and what git has committed. Measured here rather
    # than inside save(), which used to re-read the file it was about to
    # overwrite and so compared the ledger with itself.
    floor = max(len(ledger.hypotheses), committed_entry_count(path))

    if args.backfill:
        for search, names, seasons, outcome in BACKFILL:
            ledger.record(*[
                Hypothesis(search=search, name=name, tested_on=args.tested_on,
                           seasons=seasons, outcome=outcome)
                for name in names
            ])
    if args.search and args.hypotheses:
        ledger.record(*[
            Hypothesis(
                search=args.search, name=name, tested_on=args.tested_on,
                seasons=tuple(args.seasons), outcome=args.outcome or "recorded",
            )
            for name in args.hypotheses
        ])

    save(ledger, path, floor=floor)
    (OUTPUTS_DIR / "experiment_ledger.md").write_text(render(ledger), encoding="utf-8")
    print(
        f"{ledger.count} distinct hypotheses (+{ledger.count - before}). "
        f"Any new 95% interval widens by x{ledger.correction_factor():.2f}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
