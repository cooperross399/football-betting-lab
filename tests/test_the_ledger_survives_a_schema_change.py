"""`pd.concat` fills a column disagreement with NaN, silently, in both directions.

This is the defect that cost this repository two of three seasons of injury
designations on 2026-09-23. `run_availability_cost.py` filtered
`injuries["season_type"] == "REG"` after concatenating per-season CSVs;
`season_type` is absent from the 2022/2023/2024 files, so those rows arrived as
NaN, and NaN never equals "REG". **5,794 rows survived of 23,575.** Nothing
failed: the unmatched bets fell into a fail-open default, and the report that
consumed them agreed with itself perfectly because both sides were computed
from the same third of the input.

`append_ledger` had the same shape and a far worse consequence. It read the
ledger CSV, concatenated it with freshly built rows, and referred to
`LEDGER_COLUMNS` nowhere. The forward ledger **cannot be back-dated** —
`CLAUDE.md` calls it "the only evidence that can still grow" — and it already
holds 132,856 rows across seven game days. Add a column to `LEDGER_COLUMNS`
and every one of those rows gets NaN for it; the next reader to filter on that
column then reports on recent rows only, wrong in whichever direction the
column correlates with time.

The four readers today all filter on `outcome`, declared since the start, so
nothing is wrong right now. That is exactly why the guard goes in now: the
file's columns still match `LEDGER_COLUMNS`, so the check passes on the live
ledger and costs nothing, and every game day makes it more expensive to add.

Ported from the golf lab, where the same function had the same hole and the
ledger was still empty.
"""

from __future__ import annotations

import pandas as pd
import pytest

from football_betting_lab.forward_evidence import LEDGER_COLUMNS, append_ledger


def _row(day: str) -> dict:
    return {column: f"{column}-value" for column in LEDGER_COLUMNS} | {
        "snapshot_date": day,
        "outcome": "won",
        "profit_units": 0.9,
    }


def _frame(*days: str) -> pd.DataFrame:
    return pd.DataFrame([_row(d) for d in days], columns=list(LEDGER_COLUMNS))


def test_a_column_added_since_the_old_rows_is_nan_by_decision_not_by_accident(tmp_path):
    """The `season_type` shape: rows written before a column existed.

    They must still be in the file, still readable, and the new column empty
    for them — rather than the rows silently leaving every later filter.
    """
    path = tmp_path / "forward_evidence.csv"
    _frame("2026-09-09").drop(columns=["actual"]).to_csv(path, index=False)

    assert append_ledger(_frame("2026-09-13"), path) == 1

    back = pd.read_csv(path)
    assert list(back.columns) == list(LEDGER_COLUMNS), "the file's columns drifted"
    assert len(back) == 2, "the row written under the older schema was dropped"
    assert set(back["snapshot_date"].astype(str)) == {"2026-09-09", "2026-09-13"}
    assert pd.isna(back.loc[back["snapshot_date"].astype(str) == "2026-09-09", "actual"]).all()


def test_a_column_the_schema_no_longer_declares_is_refused_when_it_holds_data(tmp_path):
    """The other direction, which would destroy frozen evidence.

    Writing the union back either drops the column or keeps one nothing
    maintains. Both are wrong for a record that cannot be back-dated.
    """
    path = tmp_path / "forward_evidence.csv"
    older = _frame("2026-09-09")
    older["a_column_nobody_declares"] = "evidence"
    older.to_csv(path, index=False)

    with pytest.raises(ValueError, match="back-dated"):
        append_ledger(_frame("2026-09-13"), path)

    # And it refused BEFORE writing: the file is untouched.
    unchanged = pd.read_csv(path)
    assert "a_column_nobody_declares" in unchanged.columns
    assert len(unchanged) == 1


def test_an_empty_leftover_column_is_not_refused(tmp_path):
    """A header carrying nothing is not evidence.

    Refusing on it would make a harmless leftover a hard stop on every card,
    which is how a guard acquires an exemption list.
    """
    path = tmp_path / "forward_evidence.csv"
    older = _frame("2026-09-09")
    older["a_column_nobody_declares"] = None
    older.to_csv(path, index=False)

    assert append_ledger(_frame("2026-09-13"), path) == 1
    assert list(pd.read_csv(path).columns) == list(LEDGER_COLUMNS)


def test_column_order_cannot_drift(tmp_path):
    """`concat` keeps the first frame's order, so a reordered file would
    propagate its order forever."""
    path = tmp_path / "forward_evidence.csv"
    _frame("2026-09-09")[list(reversed(list(LEDGER_COLUMNS)))].to_csv(path, index=False)

    append_ledger(_frame("2026-09-13"), path)
    assert list(pd.read_csv(path).columns) == list(LEDGER_COLUMNS)


def test_the_day_level_append_only_property_still_holds(tmp_path):
    """The behaviour the guard must not have broken.

    This ledger dedupes by DAY, not by row: a day already recorded is never
    written twice, because a second run of the same slate would otherwise
    double every opinion frozen that morning.
    """
    path = tmp_path / "forward_evidence.csv"
    assert append_ledger(_frame("2026-09-09"), path) == 1
    assert append_ledger(_frame("2026-09-09"), path) == 0
    assert append_ledger(_frame("2026-09-09", "2026-09-13"), path) == 1
    back = pd.read_csv(path)
    assert len(back) == 2
    assert back["snapshot_date"].astype(str).is_unique


def test_a_fresh_ledger_is_written_in_the_declared_schema(tmp_path):
    """The first write sets the file's shape, so it is reindexed too."""
    path = tmp_path / "forward_evidence.csv"
    extra = _frame("2026-09-09")
    extra["not_declared"] = "x"
    assert append_ledger(extra, path) == 1
    assert list(pd.read_csv(path).columns) == list(LEDGER_COLUMNS)


def test_the_guard_passes_on_a_ledger_shaped_like_the_live_one(tmp_path):
    """The check must be free on the record that already exists.

    The live ledger on `card-feed` holds 132,856 rows and its columns match
    `LEDGER_COLUMNS` exactly, which is the whole argument for adding this now
    rather than after another season of game days. A fixture of the same shape
    stands in, so the test needs no network and no branch checkout.
    """
    path = tmp_path / "forward_evidence.csv"
    live_shaped = pd.concat(
        [_frame(f"2026-09-{day:02d}") for day in (9, 10, 13, 14, 17, 20, 21)],
        ignore_index=True,
    )
    live_shaped.to_csv(path, index=False)
    assert list(pd.read_csv(path).columns) == list(LEDGER_COLUMNS)

    assert append_ledger(_frame("2026-09-27"), path) == 1
    back = pd.read_csv(path)
    assert len(back) == 8, "an existing, schema-correct ledger lost rows"
    assert list(back.columns) == list(LEDGER_COLUMNS)
