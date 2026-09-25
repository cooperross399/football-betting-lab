#!/usr/bin/env python3
"""Name what the weekly ledger check found, from each step's own status.

    SCHEDULE=success FEEDS=success COVERAGE_CODE=0 FRESHNESS_CODE=1 \\
        python scripts/classify_weekly_check.py

Two different alarms wearing one label is worse than no alarm. The workflow
used to pick its message by grepping the coverage report for "never frozen" —
and the report's own opening sentence says "a game day that was never frozen
is sample that does not exist", so the grep matched on every run that wrote a
report. A stale feed, a missing snapshot folder and a genuinely lost Sunday all
printed the same line: "That evidence cannot be recovered." It printed it on
2026-09-15 and 2026-09-22, when nothing had been lost.

So the verdict is read from exit statuses, never from prose. Each check owns
its numbers (see the docstrings of `run_slate_coverage.py` and
`run_feed_freshness.py`), and this maps them to words. It exits 0 whatever it
finds: it classifies, and the workflow's last step is the gate.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass

LOST = "lost"
WATCHDOG = "watchdog"
STALE = "stale"


@dataclass(frozen=True)
class Finding:
    kind: str
    message: str


def classify(
    *, schedule: str, feeds: str, coverage_code: str, freshness_code: str
) -> list[Finding]:
    """Every failure this run can name, most irreversible first.

    `schedule` and `feeds` are step outcomes (`success`, `failure`, ...);
    the codes are the exit statuses the two checks recorded, or empty when
    the step never recorded one.
    """
    if schedule != "success":
        # Checked first because the checks below can succeed against a stale
        # calendar and report a clean week: the one failure that looks like
        # good news. Nothing below it can be read, so nothing below it is.
        return [Finding(WATCHDOG, (
            "The schedule fetch failed, so every check below it ran against "
            "the committed calendar rather than the current one. The NFL flexes "
            "games between windows and dates all season. This is a broken "
            "watchdog, NOT evidence about the ledger or the feeds."
        ))]

    findings: list[Finding] = []
    if coverage_code == "1":
        findings.append(Finding(LOST, (
            "A scheduled game day has no frozen opinions. That evidence cannot "
            "be recovered."
        )))
    elif coverage_code == "3":
        findings.append(Finding(WATCHDOG, (
            "A game day settled without its snapshot. Its settled rows prove "
            "opinions were frozen before kickoff, so this is a broken restore "
            "or a damaged archive, NOT a lost game day."
        )))
    elif coverage_code != "0":
        findings.append(Finding(WATCHDOG, (
            f"The coverage check could not complete (exit {coverage_code or 'none'}). "
            "It failed to read or produce its own inputs. This is a broken "
            "watchdog, NOT evidence that a game day was lost."
        )))

    if feeds != "success":
        findings.append(Finding(WATCHDOG, (
            "The card's feeds could not be fetched, so the freshness check "
            "graded whatever the checkout already held. This is a broken "
            "watchdog, NOT evidence about the feeds."
        )))
    elif freshness_code == "1":
        findings.append(Finding(STALE, (
            "At least one feed the card reads is stale or missing. The next "
            "card would price last week's truth into a ledger that is never "
            "revised; the freshness table names each feed and what a stale "
            "copy costs."
        )))
    elif freshness_code != "0":
        findings.append(Finding(WATCHDOG, (
            f"The freshness check could not complete (exit {freshness_code or 'none'}). "
            "This is a broken watchdog, NOT evidence about the feeds."
        )))
    return findings


def main() -> int:
    findings = classify(
        schedule=os.environ.get("SCHEDULE", ""),
        feeds=os.environ.get("FEEDS", ""),
        coverage_code=os.environ.get("COVERAGE_CODE", ""),
        freshness_code=os.environ.get("FRESHNESS_CODE", ""),
    )
    for finding in findings:
        print(f"- **{finding.kind}**: {finding.message}")
    if not findings:
        print("Every game day played so far was frozen and settled, and every feed is current.")
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as handle:
            handle.write(f"failed={'true' if findings else 'false'}\n")
            handle.write(f"lost={'true' if any(f.kind == LOST for f in findings) else 'false'}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
