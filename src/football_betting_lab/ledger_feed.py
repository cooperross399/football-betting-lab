"""Keep the forward ledger push-sized: shard it by slate day on card-feed.

`forward_evidence.csv` is append-only and cannot be back-dated, and it grows
by a full slate's settled rows every week. By 2026-10-05 it had grown from
77MB to a push GitHub refused outright:

    remote: error: File forward_evidence.csv is 136.75 MB; this exceeds
    GitHub's file size limit of 100.00 MB

One blob cannot carry a season. The fix has to keep every row that was ever
settled — the forward ledger is "the only evidence this lab can still
gather" (CLAUDE.md) — so this is a reshape, never a truncation.

The unit the ledger already settles in is the slate day: `settle_snapshot`
settles "a day... as a unit", and `append_ledger` already refuses to
duplicate a day once it is recorded. So the branch stores one CSV per
`snapshot_date` under `ledger/`, the same shape `priced_snapshots/` already
uses for the frozen opinions themselves, and the workflow reconstructs the
single `data/processed/forward_evidence.csv` the rest of this lab reads and
writes by merging the shards back together after restoring them. Nothing
downstream of `forward_evidence.ledger_path()` changes: `append_ledger`,
`interval_by_game` and `render_ledger` never learn their file arrived in
pieces.

A day's settled rows never change once written (an unsettled day keeps
returning until the patience window closes; a settled one is immutable), so
`split_into_shards` can safely regenerate every shard from the full local
ledger on every publish — there is no bookkeeping of "which days are new" to
get wrong, because recomputing all of them is simpler and cannot drift from
what is actually on disk. Git hashes identical content to the identical
blob, so an unchanged day's shard costs nothing to "add" again.

Restoring shards back into one file is deliberately NOT done by parsing and
rewriting through this module (or through pandas at all): the workflow
concatenates the raw CSV text instead, because a parse-and-rewrite round
trip can reformat a float or a quoting choice differently from how it was
frozen, and a restored ledger that is merely value-equal to what was
written — rather than byte-identical — is a needless place for drift to
enter the one file in this lab that cannot be reconstructed if it is wrong.
See the workflow's "Restore the ledger" step for that half.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from football_betting_lab.forward_evidence import LEDGER_COLUMNS

#: Directory name on the card-feed branch, and under the local archive while
#: staging a publish — mirrors `forward_evidence.SNAPSHOT_DIRNAME`.
LEDGER_SHARD_DIRNAME = "ledger"

#: The name under which a restored pre-migration monolithic ledger is kept
#: among the shards, in the workflow's restore step. Not a real
#: `snapshot_date` (no NFL slate exists on that day), so it can never
#: collide with one, and it sorts before every ISO date.
LEGACY_SHARD_NAME = "0000-00-00-legacy.csv"


def shard_dir(archive_dir: Path) -> Path:
    return Path(archive_dir) / LEDGER_SHARD_DIRNAME


def shard_filename(snapshot_date: str) -> str:
    return f"{snapshot_date}.csv"


def split_into_shards(ledger: pd.DataFrame, directory: Path) -> list[Path]:
    """Write one CSV per `snapshot_date`, each holding only that day's rows.

    Every shard is reindexed to `LEDGER_COLUMNS` so its schema can never
    drift from the merged file's — the one invariant `append_ledger` already
    protects for the monolithic file. Grouped on the column's *string* value,
    matching how `append_ledger` itself compares dates, so a date is never
    quietly reparsed into a different spelling.

    Safe to call with the full ledger on every publish: a day whose rows are
    unchanged writes byte-identical content, so it hashes to the blob
    already on the branch and costs nothing extra to "add" again.
    """
    directory.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    if ledger.empty:
        return written
    grouped = ledger.reindex(columns=list(LEDGER_COLUMNS)).groupby(
        ledger["snapshot_date"].astype(str), sort=True
    )
    for day, rows in grouped:
        target = directory / shard_filename(str(day))
        rows.to_csv(target, index=False)
        written.append(target)
    return written
