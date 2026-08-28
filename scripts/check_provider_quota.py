#!/usr/bin/env python3
"""Report the provider quota remaining, without spending any of it.

The `/v4/sports` listing is documented as costing nothing and returns the
`x-requests-remaining` and `x-requests-used` headers, so this is the cheapest
possible way to answer "how much is left".

    PYTHONPATH=src python scripts/check_provider_quota.py

It also answers a question this lab does not otherwise know: **when the
monthly quota resets.** The reset shows up as `x-requests-used` falling, and
watching for that costs nothing. Until it is observed, any purchase needing
most of a month is planned as though the reset were the least convenient day
it could be.

Prints the numbers and nothing about the credential beyond whether one is
present.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from football_betting_lab.config import OUTPUTS_DIR
from football_betting_lab.leagues import DEFAULT_LEAGUE_KEY, league_for
from football_betting_lab.providers.env_file import load_provider_env, redact
from football_betting_lab.providers.odds_api import OddsApiProvider, ProviderError


HISTORY_FILENAME = "quota_history.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", default=DEFAULT_LEAGUE_KEY)
    parser.add_argument(
        "--fail-under",
        type=int,
        default=0,
        help="Exit non-zero when fewer than this many credits remain.",
    )
    args = parser.parse_args(argv)

    load_provider_env()
    try:
        headers = OddsApiProvider(league_for(args.league)).quota()
    except ProviderError as exc:
        print(redact(f"Could not reach the provider: {exc}"), file=sys.stderr)
        return 2

    remaining = str(headers.get("x-requests-remaining", "")).strip()
    used = str(headers.get("x-requests-used", "")).strip()
    now = datetime.now(timezone.utc).isoformat()
    print(
        f"Quota: {remaining or 'unknown'} remaining, {used or 'unknown'} used. "
        "This check itself is documented as free."
    )

    # Append to a history file so the reset day becomes observable rather than
    # assumed. A fall in `used` between two readings is the reset, and knowing
    # the day turns a purchase that spans two months from a guess into a plan.
    path = OUTPUTS_DIR / HISTORY_FILENAME
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    history = []
    if path.is_file():
        try:
            history = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            history = []
    if history and used.isdigit():
        previous = history[-1].get("used")
        if isinstance(previous, int) and int(used) < previous:
            print(
                f"::notice::The quota reset between {history[-1]['at']} and "
                f"{now}: used fell from {previous} to {used}."
            )
    history.append(
        {
            "at": now,
            "remaining": int(remaining) if remaining.isdigit() else None,
            "used": int(used) if used.isdigit() else None,
        }
    )
    path.write_text(json.dumps(history[-200:], indent=2) + "\n", encoding="utf-8")

    if args.fail_under and remaining.isdigit() and int(remaining) < args.fail_under:
        print(
            f"::error::Only {remaining} credits remain, below the "
            f"{args.fail_under} this run wanted. Nothing was bought.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
