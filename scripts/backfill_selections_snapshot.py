#!/usr/bin/env python3
"""Reconstruct a selections snapshot for a day the card ran before the
selections ledger existed.

    PYTHONPATH=src python scripts/backfill_selections_snapshot.py \
        --card-md path/to/card.md \
        --priced-snapshot path/to/snapshots/2026-10-04.csv \
        --snapshot-date 2026-10-04 \
        --out data/archive/selections_snapshots/2026-10-04.csv

`card.md` renders exactly `result.selections`, sorted by edge — so re-parsing
its Selections table recovers the same list `write_selections_snapshot` would
have been handed live, with the game, market, selection, line, price and
book. What it does not print — `home_team`, `away_team`, `commence_time`, and
the unrounded `model_probability`/`edge` — is recovered by joining each row
back against that day's full priced snapshot (`snapshots/<date>.csv`), which
carries all of it and is keyed by the same (market, selection, line, book,
odds, game) a selection was taken from. Nothing here is invented: every field
either comes off `card.md` as printed or off the priced snapshot the live run
already froze before kickoff.

This is a one-time repair for a day that predates `write_selections_snapshot`,
not a second way to produce a selections snapshot going forward — a day
carded after the selections ledger existed writes its own, live, and never
needs this script.

**Player rows are not handled.** card.md prints a player pick's selection as
`"{player} {over/under}"` in the Selection column, with no separate player
column, so the join key below (which does not include player) would not match
a player row back to the priced snapshot — and an unmatched row fails the
whole backfill loudly rather than writing a wrong one. That is adequate for
every day this lab has carded so far: no player prop has ever cleared
`select()`'s bars, because the availability gate refuses every one of them.
A day with a player selection needs this script extended first, not run as is.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from football_betting_lab.forward_evidence import SNAPSHOT_COLUMNS

SELECTIONS_HEADER = "| Game | Market | Selection | Line | Price | Book | Edge |"


def parse_selections_table(card_md: str) -> list[dict]:
    """Every row of card.md's Selections table, in the order printed."""
    lines = card_md.splitlines()
    try:
        start = lines.index(SELECTIONS_HEADER) + 2
    except ValueError:
        return []
    rows = []
    for raw in lines[start:]:
        if not raw.startswith("|"):
            break
        cells = [c.strip() for c in raw.strip().strip("|").split("|")]
        if len(cells) != 7:
            continue
        game, market, selection, line_cell, price_cell, book, _edge_cell = cells
        rows.append(
            {
                "game": game,
                "market": market.strip("`"),
                "selection": selection,
                "line": None if line_cell in ("", "—") else float(line_cell),
                "odds": int(price_cell),
                "book": book,
            }
        )
    return rows


def build_snapshot(
    card_md: str, priced_snapshot: pd.DataFrame, snapshot_date: str
) -> tuple[pd.DataFrame, list[dict]]:
    """Returns (snapshot frame, unmatched picks) — unmatched is never silent."""
    picks = parse_selections_table(card_md)
    priced_snapshot = priced_snapshot.copy()
    priced_snapshot["player"] = priced_snapshot["player"].fillna("")
    priced_snapshot["line"] = pd.to_numeric(priced_snapshot["line"], errors="coerce")
    index: dict[tuple, pd.Series] = {}
    for row in priced_snapshot.itertuples():
        label = f"{row.away_team} @ {row.home_team}"
        key = (
            label,
            str(row.market),
            str(row.selection),
            None if pd.isna(row.line) else round(float(row.line), 3),
            str(row.book),
            int(row.american_odds),
        )
        index[key] = row

    rows: list[dict] = []
    unmatched: list[dict] = []
    for pick in picks:
        key = (
            pick["game"],
            pick["market"],
            pick["selection"],
            None if pick["line"] is None else round(pick["line"], 3),
            pick["book"],
            pick["odds"],
        )
        matched = index.get(key)
        if matched is None:
            unmatched.append(pick)
            continue
        rows.append(
            {
                "snapshot_date": snapshot_date,
                "commence_time": matched.commence_time,
                "home_team": matched.home_team,
                "away_team": matched.away_team,
                "market": pick["market"],
                "player": str(matched.player),
                "selection": pick["selection"],
                "line": pick["line"],
                "american_odds": pick["odds"],
                "book": pick["book"],
                "model_probability": matched.model_probability,
                "edge": matched.edge,
                "calibrated_probability": (
                    None
                    if "calibrated_probability" not in priced_snapshot.columns
                    or pd.isna(getattr(matched, "calibrated_probability", None))
                    else matched.calibrated_probability
                ),
                "calibrated_edge": (
                    None
                    if "calibrated_edge" not in priced_snapshot.columns
                    or pd.isna(getattr(matched, "calibrated_edge", None))
                    else matched.calibrated_edge
                ),
                "gates_in_force": (
                    "selection: cleared select()'s bars — backfilled "
                    f"2026-10-05 from card.md; no selections ledger existed "
                    f"when {snapshot_date} was carded"
                ),
            }
        )
    frame = pd.DataFrame(rows, columns=list(SNAPSHOT_COLUMNS))
    return frame, unmatched


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--card-md", required=True, type=Path)
    parser.add_argument("--priced-snapshot", required=True, type=Path)
    parser.add_argument("--snapshot-date", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    card_md = args.card_md.read_text(encoding="utf-8")
    priced_snapshot = pd.read_csv(args.priced_snapshot)
    frame, unmatched = build_snapshot(card_md, priced_snapshot, args.snapshot_date)

    if unmatched:
        print(
            f"::error::{len(unmatched)} selection(s) in {args.card_md} could not "
            "be matched back to the priced snapshot. Nothing was written — a "
            "partial backfill would silently drop evidence rather than report "
            "it as missing.",
            file=sys.stderr,
        )
        for pick in unmatched[:20]:
            print(f"  unmatched: {pick}", file=sys.stderr)
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.out, index=False)
    print(f"Wrote {len(frame)} selection(s) to {args.out}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
