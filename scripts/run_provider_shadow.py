#!/usr/bin/env python3
"""A live fetch into staging. The card cannot read what this writes.

**This spends credits.** It refuses without `--live` and refuses to exceed
`--credit-cap`, which is checked before every request against the pessimistic
bound.

    PYTHONPATH=src python scripts/run_provider_shadow.py                    # dry
    PYTHONPATH=src python scripts/run_provider_shadow.py --live --credit-cap 200

The credential comes from the environment or a gitignored `.env`, never from a
command-line argument.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from football_betting_lab.config import OUTPUTS_DIR, RAW_DIR, STAGING_DIR
from football_betting_lab.leagues import DEFAULT_LEAGUE_KEY, league_for
from football_betting_lab.markets import bulk_provider_keys, per_event_provider_keys
from football_betting_lab.providers.env_file import load_provider_env, redact
from football_betting_lab.providers.odds_api import OddsApiProvider, ProviderError
from football_betting_lab.reports import provider_shadow


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", default=DEFAULT_LEAGUE_KEY)
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--tier", type=int, default=1)
    parser.add_argument(
        "--horizon-days",
        type=int,
        default=1,
        help="Days ahead to price. Wider windows starve the nearest slate.",
    )
    parser.add_argument("--credit-cap", type=int, default=0)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args(argv)

    league = league_for(args.league)
    bulk = bulk_provider_keys(args.tier)
    per_event = per_event_provider_keys(args.tier)
    print(f"{league.title}, tier {args.tier}, horizon {args.horizon_days} day(s).")
    print(
        f"Bulk: {len(bulk)} market(s) for the whole slate. Per event: "
        f"{len(per_event)} market(s), billed only for those a book returns."
    )
    print(
        f"Pessimistic bound: {len(bulk)} + {len(per_event)} per in-window "
        f"event. The cap is enforced against that, so it cannot be breached."
    )
    if not args.live:
        print(
            "\nDry run: nothing was requested and no credit was spent. Re-run "
            "with --live and a --credit-cap."
        )
        return 0
    if args.credit_cap <= 0:
        print(
            "::error::--live requires a positive --credit-cap.", file=sys.stderr
        )
        return 2

    load_provider_env()
    try:
        provider = OddsApiProvider(league)
        run = provider_shadow.run_shadow(
            provider,
            league,
            raw_dir=RAW_DIR,
            season=args.season,
            horizon_days=args.horizon_days,
            credit_cap=args.credit_cap,
            now=datetime.now(timezone.utc),
            tier=args.tier,
        )
    except ProviderError as exc:
        print(redact(f"The shadow run could not start: {exc}"), file=sys.stderr)
        return 2

    path = provider_shadow.write_staging(run, STAGING_DIR)
    report = provider_shadow.render(run, league)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUTS_DIR / league.output_name("provider_shadow", ".md")).write_text(
        report, encoding="utf-8"
    )
    print()
    print(report)
    print(f"Staged to {path}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
