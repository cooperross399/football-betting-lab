#!/usr/bin/env python3
"""Buy a season of historical prices, resumably, under a hard cap.

**This spends credits — a lot of them.** Cooper approved the purchase on
2026-08-28: one season, two snapshots (the price a card could have acted on,
and the close), which gives a priced backtest and closing-line value on every
historical bet. At the measured rate that is roughly 198,000 credits against a
100,000-a-month quota, so it is deliberately several capped runs rather than
one.

    # What it would cost, spending nothing:
    PYTHONPATH=src python scripts/buy_historical_prices.py --season 2025

    # A capped slice, in CI where the secret lives:
    PYTHONPATH=src python scripts/buy_historical_prices.py \
        --season 2025 --lead-minutes 60 --live --credit-cap 70000

Every run resumes where the last stopped: a cached event costs nothing, and
the manifest is written after **every** event so a run killed by a timeout
cannot lose the record of what it already paid for.

Events are bought in an order whose every prefix is spread across the whole
season, so a run that stops at 40% has bought a 40% **sample** rather than the
first 40% of the schedule.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from football_betting_lab.config import OUTPUTS_DIR, RAW_DIR
from football_betting_lab.leagues import DEFAULT_LEAGUE_KEY, league_for
from football_betting_lab.markets import per_event_provider_keys
from football_betting_lab.providers.env_file import load_provider_env, redact
from football_betting_lab.providers.historical import (
    CACHE_DIRNAME,
    CARD_TIME_LEAD_MINUTES,
    buy_season,
)
from football_betting_lab.providers.odds_api import (
    HISTORICAL_EVENTS_LIST_COST,
    HISTORICAL_MULTIPLIER,
    OddsApiProvider,
    ProviderError,
)
from football_betting_lab.reports.retention_probe import select_targets
from football_betting_lab.season import schedule_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", default=DEFAULT_LEAGUE_KEY)
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--tier", type=int, default=1)
    parser.add_argument(
        "--lead-minutes",
        type=int,
        default=CARD_TIME_LEAD_MINUTES,
        help="Minutes before kickoff. 60 is card time; 5 is the close.",
    )
    parser.add_argument("--credit-cap", type=int, default=0)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args(argv)

    league = league_for(args.league)
    markets = per_event_provider_keys(args.tier)
    path = schedule_path(league, RAW_DIR)
    if not path.is_file():
        print(f"No cached schedule at {path}.", file=sys.stderr)
        return 2
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    # Every regular-season game of the season, in schedule order. `count`
    # equal to the season size means no sampling here — the van der Corput
    # order inside the buyer is what makes a partial run representative.
    targets = select_targets(rows, league, seasons=(args.season,), count=10_000)
    if not targets:
        print(f"No {args.season} events to buy.", file=sys.stderr)
        return 2

    per_event = HISTORICAL_MULTIPLIER * len(markets) + HISTORICAL_EVENTS_LIST_COST
    print(
        f"{league.title} {args.season}: {len(targets)} events x {len(markets)} "
        f"markets at T-{args.lead_minutes}min.\n"
        f"At most **{len(targets) * per_event:,} credits** ({per_event:,} per "
        f"event). The endpoint bills per market *returned*, and the retention "
        "probe measured actual spend at 79% of this bound, so expect nearer "
        f"{int(len(targets) * per_event * 0.79):,}. The cap is enforced "
        "against the bound, so it cannot be breached."
    )
    if not args.live:
        print("\nDry run: nothing was requested and no credit was spent.")
        return 0
    if args.credit_cap <= 0:
        print("::error::--live requires a positive --credit-cap.", file=sys.stderr)
        return 2

    load_provider_env()
    cache_dir = RAW_DIR / league.data_dir_segment / CACHE_DIRNAME
    try:
        progress = buy_season(
            OddsApiProvider(league),
            league,
            targets,
            markets,
            lead_minutes=args.lead_minutes,
            credit_cap=args.credit_cap,
            cache_dir=cache_dir,
            season=args.season,
        )
    except ProviderError as exc:
        print(redact(f"The purchase could not start: {exc}"), file=sys.stderr)
        return 2

    print()
    print(progress.summary_line())
    if progress.stopped_early:
        print(f"\nStopped early: {progress.stopped_early}")
        print(
            "This is the expected way a capped run ends. Re-run to continue; "
            "everything already bought is cached and costs nothing."
        )
    if progress.failures:
        print(f"\n{len(progress.failures)} event(s) produced nothing:")
        for failure in progress.failures[:20]:
            print(f"  - {failure}")

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    report = OUTPUTS_DIR / league.output_name(
        f"historical_purchase_{args.season}_t{args.lead_minutes}", ".md"
    )
    report.write_text(
        f"# Historical purchase — {league.title} {args.season}, "
        f"T-{args.lead_minutes}min\n\n"
        f"{progress.summary_line()}\n\n"
        f"Events are bought in an order whose every prefix is spread across "
        f"the whole season, so this **{progress.fraction_done:.0%} is a sample "
        "of the season rather than the first "
        f"{progress.fraction_done:.0%} of it**.\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
