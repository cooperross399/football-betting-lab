#!/usr/bin/env python3
"""Ask the provider which markets it actually retains historically.

**This spends credits.** It refuses to do so without `--live`, and it refuses
to spend more than `--credit-cap`, which is checked before every request
against the pessimistic bound rather than after the fact.

    # What it would cost, spending nothing:
    PYTHONPATH=src python scripts/run_retention_probe.py

    # The real thing, in CI where the secret lives:
    PYTHONPATH=src python scripts/run_retention_probe.py --live --credit-cap 9500

The credential is read from the environment or a gitignored `.env`. It is
never accepted as a command-line argument: a process list is world-readable on
a shared machine and CI logs echo commands.

Why a probe before a purchase: a market that cannot be bought historically
cannot be measured historically, and finding that out by spending 125,120
credits is an expensive way to learn something this answers for a fraction of
it. See `src/football_betting_lab/reports/retention_probe.py` for the two
rules that came out of the NHL lab getting this wrong.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from football_betting_lab.config import OUTPUTS_DIR, RAW_DIR
from football_betting_lab.leagues import DEFAULT_LEAGUE_KEY, league_for
from football_betting_lab.markets import per_event_provider_keys
from football_betting_lab.providers.env_file import load_provider_env, redact
from football_betting_lab.providers.odds_api import (
    HISTORICAL_EVENTS_LIST_COST,
    HISTORICAL_MULTIPLIER,
    OddsApiProvider,
    ProviderError,
)
from football_betting_lab.reports import retention_probe as probe_module
from football_betting_lab.season import schedule_path


DEFAULT_EVENTS = 20
DEFAULT_SEASONS = (2024, 2025)


def cost_note(events: int, markets: int) -> str:
    """The bound, stated before a credit is spent."""
    per_event = HISTORICAL_MULTIPLIER * markets + HISTORICAL_EVENTS_LIST_COST
    upper = events * per_event
    return (
        f"{events} event(s) x {markets} market(s): at most **{upper:,} "
        f"credits** ({per_event:,} per event — {HISTORICAL_MULTIPLIER} per "
        f"market historically, plus {HISTORICAL_EVENTS_LIST_COST} for the "
        "slate listing). The endpoint bills per market *returned*, so real "
        "spend will be lower by exactly the markets nobody retained — which "
        "is the thing being measured. The cap is enforced against the upper "
        "bound and therefore cannot be breached."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", default=DEFAULT_LEAGUE_KEY)
    parser.add_argument("--events", type=int, default=DEFAULT_EVENTS)
    parser.add_argument(
        "--seasons",
        type=int,
        nargs="+",
        default=list(DEFAULT_SEASONS),
        help="Seasons to sample from. Never earlier than 2023-05-03.",
    )
    parser.add_argument(
        "--tier",
        type=int,
        default=1,
        help="Market tier to probe. Tier 1 is the launch set.",
    )
    parser.add_argument(
        "--credit-cap",
        type=int,
        default=0,
        help="Hard cap. Required with --live; zero means unlimited and is refused.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Actually spend credits. Without this nothing is requested.",
    )
    args = parser.parse_args(argv)

    league = league_for(args.league)
    markets = per_event_provider_keys(args.tier)
    path = schedule_path(league, RAW_DIR)
    if not path.is_file():
        print(f"No cached schedule at {path}.", file=sys.stderr)
        return 2
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    targets = probe_module.select_targets(
        rows, league, seasons=args.seasons, count=args.events
    )
    if not targets:
        print("No probe targets. Check the seasons requested.", file=sys.stderr)
        return 2

    print(f"Probing {league.title}, tier {args.tier}.")
    print(cost_note(len(targets), len(markets)))
    print()
    for target in targets:
        print(f"  {target.label} @ {target.snapshot}")
    print()

    if not args.live:
        print(
            "Dry run: nothing was requested and no credit was spent. Re-run "
            "with --live and a --credit-cap to probe for real."
        )
        return 0

    if args.credit_cap <= 0:
        print(
            "::error::--live requires a positive --credit-cap. An uncapped "
            "spend against a shared quota is not something this script will "
            "do.",
            file=sys.stderr,
        )
        return 2

    load_provider_env()
    try:
        provider = OddsApiProvider(league)
        result = probe_module.run_probe(
            provider,
            league,
            targets,
            markets,
            credit_cap=args.credit_cap,
            cache_dir=RAW_DIR / league.data_dir_segment / probe_module.CACHE_DIRNAME,
        )
    except ProviderError as exc:
        print(redact(f"The probe could not run: {exc}"), file=sys.stderr)
        return 2

    report = probe_module.render(result, league)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    markdown = OUTPUTS_DIR / league.output_name("retention_probe", ".md")
    payload = OUTPUTS_DIR / league.output_name("retention_probe", ".json")
    markdown.write_text(report, encoding="utf-8")
    payload.write_text(
        json.dumps(probe_module.to_json(result, league), indent=2) + "\n",
        encoding="utf-8",
    )

    print(report)
    print(f"Wrote {markdown} and {payload}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
