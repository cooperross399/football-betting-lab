#!/usr/bin/env python3
"""Fetch the nflverse feeds into the local cache. Free, and spends no credits.

    PYTHONPATH=src python scripts/fetch_football_data.py --seasons 2022 2023 2024 2025 2026

A completed season's files are fetched once and never again, so a rebuild is
reproducible offline. The current season's are refetched, because the NFL
applies stat corrections between Monday and Wednesday and Thursday's copy is
the clean one.

Data from nflverse under CC-BY-4.0.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from football_betting_lab.config import RAW_DIR
from football_betting_lab.data import nflverse
from football_betting_lab.leagues import DEFAULT_LEAGUE_KEY, league_for


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", default=DEFAULT_LEAGUE_KEY)
    parser.add_argument("--seasons", type=int, nargs="+", required=True)
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument(
        "--only",
        nargs="+",
        default=None,
        help=f"Limit to these feeds. Known: {sorted(nflverse.FEEDS_BY_NAME)}",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Refetch even a completed season. Use when nflverse revises history.",
    )
    args = parser.parse_args(argv)

    league = league_for(args.league)
    wanted = args.only or list(nflverse.FEEDS_BY_NAME)
    unknown = [name for name in wanted if name not in nflverse.FEEDS_BY_NAME]
    if unknown:
        print(f"Unknown feed(s): {unknown}", file=sys.stderr)
        return 2

    entries: dict[str, object] = {}
    failures: list[str] = []
    for name in wanted:
        feed = nflverse.FEEDS_BY_NAME[name]
        seasons = args.seasons if feed.per_season else [None]
        for season in seasons:
            label = f"{feed.name}" + (f" {season}" if season is not None else "")
            try:
                path, what = nflverse.fetch_feed(
                    feed,
                    league,
                    raw_dir=args.raw_dir,
                    season=season,
                    refresh=args.refresh,
                )
            except nflverse.FetchError as exc:
                # A season the feed has not published yet is an absence, not a
                # fault: injuries and play-by-play do not exist before a snap
                # has been played. Recorded by name either way, because
                # "not published" and "the fetch broke" look identical in a
                # total and mean opposite things.
                failures.append(f"{label}: {exc}")
                print(f"  {label}: not available — {exc}")
                continue
            size = path.stat().st_size
            entries[label] = {
                "path": str(path.relative_to(args.raw_dir)),
                "bytes": size,
                "status": what,
            }
            print(f"  {label}: {what} ({size:,} bytes)")

    nflverse.write_manifest(
        league,
        args.raw_dir,
        entries,
        fetched_at=datetime.now(timezone.utc).isoformat(),
    )
    print()
    print(f"{len(entries)} feed-season(s) cached, {len(failures)} unavailable.")
    print(nflverse.ATTRIBUTION)
    # An unavailable feed is not a failure of this script. The manifest records
    # what landed, and the build step refuses to proceed on what did not.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
