#!/usr/bin/env python3
"""Refuse to push a blob GitHub will refuse anyway — before `git push` runs.

    python scripts/check_push_blob_sizes.py FILE [FILE ...]

GitHub rejects a pushed object over 100.00 MB. `forward_evidence.csv` hit
that wall on 2026-10-05 at 136.75 MB, discovered only when `git push` was
rejected mid-publish — on a Monday, with a game day's opinions already
frozen locally and nowhere to land. This check runs over every file about
to be staged into the card-feed commit (ledger shards, snapshots, the card)
and fails loudly, before any `git hash-object` or `git push`, so the same
wall is never hit silently again.

The limit here is below GitHub's own (100 MB = 104,857,600 bytes) on
purpose: a margin to fail inside CI, with a clear message naming the file
and its size, rather than at the remote, where the error is a bare
`pre-receive hook declined` after the commit is already built.

Standard library only, matching `check_ledger_append_only.py`: both are
guard scripts a workflow step can run without `PYTHONPATH=src`.
"""

from __future__ import annotations

import sys
from pathlib import Path

#: Comfortably below GitHub's 100 MB hard limit (104,857,600 bytes), so this
#: fails well before a file is close enough to the wall that one more
#: settled day would cross it without warning.
MAX_BYTES = 90_000_000


def oversized(paths: list[Path], limit: int = MAX_BYTES) -> list[tuple[Path, int]]:
    """Every path in `paths` that exists and exceeds `limit`, with its size.

    Silent about a path that does not exist: a shell glob that matched
    nothing expands to its own literal pattern rather than to zero
    arguments unless `nullglob` is set, and the caller should not have to
    get that shell option right for this check to behave.
    """
    found = []
    for path in paths:
        if path.is_file():
            size = path.stat().st_size
            if size > limit:
                found.append((path, size))
    return found


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print("usage: check_push_blob_sizes.py FILE [FILE ...]", file=sys.stderr)
        return 2
    paths = [Path(arg) for arg in argv]
    existing = [path for path in paths if path.is_file()]
    problems = oversized(existing)
    if problems:
        for path, size in problems:
            print(
                f"Push check FAILED: {path} is {size:,} bytes, over the "
                f"{MAX_BYTES:,}-byte safety margin (GitHub's hard limit is "
                "104,857,600 bytes). Shard it further, or do not publish "
                "this file.",
                file=sys.stderr,
            )
        return 1
    print(f"{len(existing)} file(s) checked, all under {MAX_BYTES:,} bytes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
