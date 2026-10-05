#!/usr/bin/env python3
"""Split the forward ledger into one CSV per settled day, for card-feed.

    PYTHONPATH=src python scripts/run_ledger_shards.py \
        --ledger data/processed/forward_evidence.csv \
        --shard-dir SHARD_DIR

Run by the "Publish to the card-feed branch" step, after the card has run
and `append_ledger` has written the local ledger. The *restore* direction
(shards back into one file) is pure `cat`/`tail` in the workflow itself, not
here — see `football_betting_lab.ledger_feed` for why a parse-and-rewrite
round trip is the wrong tool for that half.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from football_betting_lab.forward_evidence import LEDGER_COLUMNS
from football_betting_lab.ledger_feed import split_into_shards


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--shard-dir", type=Path, required=True)
    args = parser.parse_args(argv)

    if not args.ledger.is_file():
        print(f"No ledger at {args.ledger}; nothing to split.")
        return 0
    ledger = pd.read_csv(args.ledger, low_memory=False)
    written = split_into_shards(ledger.reindex(columns=list(LEDGER_COLUMNS)), args.shard_dir)
    print(f"{len(written)} day shard(s) written to {args.shard_dir}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
