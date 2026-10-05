"""Splitting the forward ledger into day shards never loses or reshapes a row.

`forward_evidence.csv` hit GitHub's 100MB push limit on 2026-10-05. The fix
shards the ledger by `snapshot_date` on the card-feed branch instead of
publishing one ever-growing file; these tests hold the one property that
fix cannot get wrong — every row that went in comes back out, under the
column order `append_ledger` already declares — and that resharding the
same ledger twice costs nothing (identical bytes, so git never re-uploads
an unchanged day).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from football_betting_lab.forward_evidence import LEDGER_COLUMNS
from football_betting_lab.ledger_feed import (
    LEGACY_SHARD_NAME,
    shard_dir,
    shard_filename,
    split_into_shards,
)


def _row(**overrides) -> dict:
    row = {column: "" for column in LEDGER_COLUMNS}
    row.update(
        {
            "snapshot_date": "2026-09-13",
            "market": "spread",
            "model_probability": 0.55,
            "edge": 0.04,
            "outcome": "won",
            "profit_units": 0.91,
        }
    )
    row.update(overrides)
    return row


def test_split_writes_one_file_per_distinct_day(tmp_path: Path) -> None:
    ledger = pd.DataFrame(
        [
            _row(snapshot_date="2026-09-13", market="spread"),
            _row(snapshot_date="2026-09-13", market="total_points"),
            _row(snapshot_date="2026-09-14", market="moneyline"),
        ]
    )
    written = split_into_shards(ledger, tmp_path)

    assert sorted(p.name for p in written) == ["2026-09-13.csv", "2026-09-14.csv"]
    assert sorted(p.name for p in tmp_path.glob("*.csv")) == [
        "2026-09-13.csv",
        "2026-09-14.csv",
    ]


def test_split_preserves_every_row_and_every_column(tmp_path: Path) -> None:
    """The round trip this fix depends on: nothing recorded is ever dropped."""
    ledger = pd.DataFrame(
        [
            _row(snapshot_date="2026-09-13", market="spread", outcome="won"),
            _row(snapshot_date="2026-09-13", market="total_points", outcome="lost"),
            _row(snapshot_date="2026-09-20", market="moneyline", outcome="push"),
            _row(snapshot_date="2026-09-27", market="reception_yards", outcome="void"),
        ]
    )
    split_into_shards(ledger, tmp_path)

    merged = pd.concat(
        [pd.read_csv(p) for p in sorted(tmp_path.glob("*.csv"))], ignore_index=True
    )
    assert len(merged) == len(ledger)
    assert list(merged.columns) == list(LEDGER_COLUMNS)
    assert sorted(merged["outcome"]) == ["lost", "push", "void", "won"]


def test_split_reindexes_every_shard_to_the_declared_schema(tmp_path: Path) -> None:
    """A caller's column order (or a missing column) never reaches the branch:
    every shard is written in `LEDGER_COLUMNS` order, same as the monolithic
    file `append_ledger` writes."""
    scrambled = pd.DataFrame(
        [{"outcome": "won", "snapshot_date": "2026-09-13", "market": "spread"}]
    )
    split_into_shards(scrambled, tmp_path)

    shard = pd.read_csv(tmp_path / "2026-09-13.csv")
    assert list(shard.columns) == list(LEDGER_COLUMNS)
    assert shard.loc[0, "outcome"] == "won"


def test_split_on_an_empty_ledger_writes_nothing(tmp_path: Path) -> None:
    written = split_into_shards(pd.DataFrame(columns=list(LEDGER_COLUMNS)), tmp_path)
    assert written == []
    assert list(tmp_path.glob("*.csv")) == []


def test_resharding_the_same_ledger_is_byte_identical(tmp_path: Path) -> None:
    """Why it is safe to reshard the whole local ledger on every publish: an
    unchanged day hashes to the blob already on the branch, so "add" it
    again costs nothing. If this ever produced different bytes for the same
    rows, every publish would re-upload the whole season."""
    ledger = pd.DataFrame(
        [
            _row(snapshot_date="2026-09-13", market="spread"),
            _row(snapshot_date="2026-09-20", market="moneyline"),
        ]
    )
    split_into_shards(ledger, tmp_path)
    first = {p.name: p.read_bytes() for p in tmp_path.glob("*.csv")}

    other_dir = tmp_path / "again"
    split_into_shards(ledger, other_dir)
    second = {p.name: p.read_bytes() for p in other_dir.glob("*.csv")}

    assert first == second


def test_split_groups_on_the_string_value_of_the_date_column() -> None:
    """`append_ledger` compares `snapshot_date` as a string
    (`existing["snapshot_date"].astype(str)`); grouping here has to match
    that exactly or a date could be split under two different spellings."""
    ledger = pd.DataFrame(
        [_row(snapshot_date="2026-09-13"), _row(snapshot_date="2026-09-13")]
    )
    import tempfile

    with tempfile.TemporaryDirectory() as directory:
        written = split_into_shards(ledger, Path(directory))
        assert len(written) == 1
        assert written[0].name == "2026-09-13.csv"
        assert len(pd.read_csv(written[0])) == 2


def test_shard_filename_matches_the_snapshot_date_literally() -> None:
    assert shard_filename("2026-09-13") == "2026-09-13.csv"


def test_shard_dir_is_a_subdirectory_of_the_archive(tmp_path: Path) -> None:
    assert shard_dir(tmp_path) == tmp_path / "ledger"


def test_the_legacy_shard_name_cannot_collide_with_a_real_date() -> None:
    """It must sort before every ISO `snapshot_date` (so a human skimming the
    directory sees it first) and never equal one (an NFL slate never falls
    on 0000-00-00)."""
    assert LEGACY_SHARD_NAME < "2022-01-01.csv"
    with pytest.raises(ValueError):
        from datetime import date

        date.fromisoformat(LEGACY_SHARD_NAME.removesuffix(".csv"))
