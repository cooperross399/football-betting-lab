"""Freeze the card's SELECTIONS specifically, settle them, track a record.

`forward_evidence.py` already freezes and settles every priced opinion — all
57,031 of them on a normal slate. `select()`'s own bars (allowlist, edge,
price, availability, kickoff) narrow that down to the subset that actually
printed on `card.md`, but nothing kept a copy of *that* narrower list once it
was rendered to markdown. So the one thing Cooper asked for after the first
`selections` day — a running record and ROI for what the card actually
selected, not the whole forward ledger — had no file to read it from.

This module is deliberately thin. It reuses `forward_evidence.settle_snapshot`,
`append_ledger`, `interval_by_game` and `render_ledger` unchanged rather than
re-implementing settlement a second time — a second copy of that logic is
exactly how the lab's past settlement bugs started (the cross-season join, the
tackles_assists summation, the sqrt(games) interval). The only new code here
is turning `select()`'s output into the same `SNAPSHOT_COLUMNS` shape
`forward_evidence` already knows how to settle.

**Correlated selections are not deduplicated here.** CLAUDE.md's hard rule is
"never stake correlated selections as independent, and never sum their
edges" — which `interval_by_game` already honours by clustering the interval
on the game, not the bet. Collapsing the alternate-line ladder down to one
row per game would throw away real, distinct propositions (a -3 alternate
spread and a -7 alternate spread settle differently) to make the *count*
smaller, which is a cosmetic fix that would make the record harder to audit,
not more honest.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from football_betting_lab.config import ARCHIVE_DIR, PROCESSED_DIR
from football_betting_lab.forward_evidence import SNAPSHOT_COLUMNS, render_ledger

SELECTIONS_LEDGER_FILENAME = "selections_ledger.csv"
SELECTIONS_SNAPSHOT_DIRNAME = "selections_snapshots"


def selections_ledger_path(processed_dir: Path | None = None) -> Path:
    base = PROCESSED_DIR if processed_dir is None else Path(processed_dir)
    return base / SELECTIONS_LEDGER_FILENAME


def selections_snapshots_dir(archive_dir: Path | None = None) -> Path:
    base = ARCHIVE_DIR if archive_dir is None else Path(archive_dir)
    return base / SELECTIONS_SNAPSHOT_DIRNAME


def _is_empty(path: Path) -> bool:
    try:
        return len(pd.read_csv(path)) == 0
    except (OSError, UnicodeError, pd.errors.EmptyDataError, pd.errors.ParserError):
        return True


def write_selections_snapshot(
    selections: list[dict],
    *,
    snapshot_date: str,
    archive_dir: Path | None = None,
) -> Path | None:
    """Freeze today's selections exactly as `card.md` printed them.

    Same "first opinion of the day stands" rule as `forward_evidence.
    write_snapshot`, for the same reason: two snapshots for one day would let
    whichever one settles better be the one that counts, and this ledger
    cannot be back-dated to fix that after the fact. An empty list is not an
    opinion either — a `no-selections` day must not lock the date against a
    later run that found something, so it is simply not written.
    """
    if not selections:
        return None
    directory = selections_snapshots_dir(archive_dir)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{snapshot_date}.csv"
    if target.exists() and not _is_empty(target):
        return None

    rows = [
        {
            "snapshot_date": snapshot_date,
            "commence_time": pick.get("commence_time", ""),
            "home_team": pick.get("home_team", ""),
            "away_team": pick.get("away_team", ""),
            "market": pick.get("market", ""),
            "player": pick.get("player", ""),
            "selection": pick.get("selection", ""),
            "line": pick.get("line"),
            "american_odds": pick.get("odds"),
            "book": pick.get("book", ""),
            "model_probability": pick.get("model_probability"),
            "edge": pick.get("edge"),
            # select() does not carry a calibrated probability; this ledger
            # records what the card actually staked on, not a reread of it.
            "calibrated_probability": None,
            "calibrated_edge": None,
            "gates_in_force": "selection: cleared select()'s bars",
        }
        for pick in selections
    ]
    frame = pd.DataFrame(rows, columns=list(SNAPSHOT_COLUMNS))
    frame.to_csv(target, index=False)
    return target


def render_selections_record(ledger: pd.DataFrame, league) -> str:
    """The season record for what the card actually selected, in the house vocabulary.

    A thin wrapper around `forward_evidence.render_ledger`: same clustered
    interval, same "no demonstrated edge" wording, same family correction —
    because a second report format for the same question is how the two
    quietly drift, the way `CLAUDE.md` already records happening four times
    with the interval formula alone.
    """
    return render_ledger(ledger, league, heading="Selections record")
