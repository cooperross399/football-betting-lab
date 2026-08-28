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
    parser.add_argument(
        "--seasons",
        type=int,
        nargs="+",
        required=True,
        help="Seasons to buy. Never earlier than 2023 — historical props, "
        "alternate lines and period markets exist only after 2023-05-03.",
    )
    parser.add_argument("--tier", type=int, default=1)
    parser.add_argument(
        "--leads",
        type=int,
        nargs="+",
        default=[CARD_TIME_LEAD_MINUTES],
        help="Minutes before kickoff. 60 is card time; 5 is the close. Both "
        "together give closing-line value on every historical bet.",
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

    per_event = HISTORICAL_MULTIPLIER * len(markets) + HISTORICAL_EVENTS_LIST_COST
    jobs: list[tuple[int, int, list]] = []
    for season in args.seasons:
        # `count` equal to the season size means no sampling here — the
        # stratified order inside the buyer is what makes a partial run
        # representative.
        targets = select_targets(rows, league, seasons=(season,), count=10_000)
        if not targets:
            print(f"No {season} events to buy; skipping.", file=sys.stderr)
            continue
        for lead in args.leads:
            jobs.append((season, lead, targets))

    if not jobs:
        print("Nothing to buy.", file=sys.stderr)
        return 2

    total_events = sum(len(targets) for _, _, targets in jobs)
    print(
        f"{league.title}: {len(jobs)} season-snapshot(s), {total_events} "
        f"events, {len(markets)} markets each.\n"
        f"At most **{total_events * per_event:,} credits** ({per_event:,} per "
        "event). The endpoint bills per market *returned*, and the retention "
        "probe measured actual spend at 79% of this bound, so expect nearer "
        f"{int(total_events * per_event * 0.79):,}. The cap is enforced "
        "against the bound, so it cannot be breached."
    )
    for season, lead, targets in jobs:
        print(f"  {season} at T-{lead}min: {len(targets)} events")
    if not args.live:
        print("\nDry run: nothing was requested and no credit was spent.")
        return 0
    if args.credit_cap <= 0:
        print("::error::--live requires a positive --credit-cap.", file=sys.stderr)
        return 2

    load_provider_env()
    cache_dir = RAW_DIR / league.data_dir_segment / CACHE_DIRNAME
    provider = OddsApiProvider(league)
    spent = 0
    summaries: list[str] = []
    for season, lead, targets in jobs:
        remaining_cap = args.credit_cap - spent
        if remaining_cap <= 0:
            summaries.append(
                f"{season} T-{lead}min: not started — the run's cap was "
                "already spent. Re-run to continue; everything bought is "
                "cached and costs nothing."
            )
            continue
        print(f"\n--- {season} at T-{lead}min (cap left {remaining_cap:,}) ---")
        try:
            progress = buy_season(
                provider, league, targets, markets,
                lead_minutes=lead, credit_cap=remaining_cap,
                cache_dir=cache_dir, season=season,
            )
        except ProviderError as exc:
            print(redact(f"{season} T-{lead}min failed: {exc}"), file=sys.stderr)
            summaries.append(f"{season} T-{lead}min: failed — {exc}")
            continue
        spent += progress.spend.credits_spent
        print(progress.summary_line())
        summaries.append(f"{season} T-{lead}min: {progress.summary_line()}")
        if progress.failures:
            print(f"  {len(progress.failures)} event(s) produced nothing.")
        if progress.stopped_early:
            print(f"  Stopped early: {progress.stopped_early}")

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    report = OUTPUTS_DIR / league.output_name("historical_purchase", ".md")
    report.write_text(
        "# Historical purchase\n\n"
        + f"{spent:,} credits spent across {len(jobs)} season-snapshot(s).\n\n"
        + "Events are bought in an order whose every prefix is spread across "
        "the season **and** holds each kickoff window at its true share, so a "
        "run that stops early leaves a sample rather than a prefix.\n\n"
        + "\n".join(f"- {line}" for line in summaries)
        + "\n",
        encoding="utf-8",
    )
    print(f"\nTotal: {spent:,} credits. Wrote {report}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
