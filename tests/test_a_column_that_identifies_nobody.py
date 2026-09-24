"""Two defects where a column was PRESENT and carried nothing usable.

Both shipped to `main`, four hours apart, in changes written to close exactly
this class of hole. They are kept in one file because they are one mistake:

* `gates.assess_availability` checked that `gsis_id` EXISTS. A column that
  exists and identifies nobody passed, matched no row, and the empty match took
  the "filed a report and this player is not on it" branch — `UNDESIGNATED`,
  the one state a recorded verdict makes selectable, with a reason sentence
  affirmatively asserting the player is absent from a report the gate never
  read. A feed saying every player on a club is **Out**, with its ids blanked,
  made every one of them selectable.

* `run_availability_cost.py` filtered `injuries["season_type"] == "REG"` after
  concatenating per-season files. `season_type` is absent from
  injuries_2022/2023/2024.csv, so those rows arrive as NaN, and NaN never
  equals "REG". **5,794 rows survived of 23,575.** The lookup saw 2025 and 2026
  against bets spanning 2023-2025, and because an unmatched bet fills as
  `NOT_LISTED`, two entire seasons landed in the fail-open bucket. The table's
  only positive cell, Questionable at +3.3% over 1,154 bets, was computed on a
  third of the population; on all of it that cell is -6.0% over 3,094.

The drift test (`test_claude_md_agrees_with_its_reports.py`) could not see the
second one. It pins CLAUDE.md to the report, and the report agreed with itself
perfectly — it was computed on a third of its input. **A consistency check
between two derived artifacts says nothing about what went into them.**
"""

from __future__ import annotations

import pandas as pd
import pytest

from football_betting_lab import gates
from football_betting_lab.reports import availability_cost

INJURY_COLUMNS = ["season", "week", "team", "gsis_id", "report_status"]


def _frame(rows: list[list]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=INJURY_COLUMNS)


def _assess(frame: pd.DataFrame, *, club: str = "SEA", pid: str = "00-0040648"):
    """One player's verdict with the verdict FORCED ON — the dangerous config.

    Every assertion here runs with `undesignated_allowed=True`. With it off
    nothing selects whatever the state is, so a test written that way passes
    with the gate deleted.
    """
    return gates.assess_slate(
        {"p": (pid, club)}, frame, season=2026, week=1, undesignated_allowed=True
    )["p"]


# --------------------------------------------------------------------------
# A column that identifies nobody.
# --------------------------------------------------------------------------

#: Every spelling a blank id arrives as. `None` and `float("nan")` are both
#: here on purpose: `astype(str)` renders them "None" and "nan" respectively,
#: so a check written as a blocklist of strings catches one and misses the
#: other depending on the column's dtype. The first draft of the fix did.
@pytest.mark.parametrize("blank", [None, "", "   ", "nan", "NaN", float("nan")])
def test_an_id_column_that_identifies_nobody_does_not_read_as_a_clean_report(blank):
    """The exact shipped defect: state was UNDESIGNATED and may_select True."""
    got = _assess(_frame([[2026, 1, "SEA", blank, "Out"]]))
    assert got.state == gates.UNKNOWN, (
        f"a gsis_id of {blank!r} produced {got.state}; the feed says this "
        "club's players are Out and the gate could not read it"
    )
    assert not got.may_select


def test_the_feed_saying_everyone_is_out_never_selects_anybody():
    """The blast radius, not just the single row.

    A whole club listed Out with blanked ids made every one of them selectable,
    because each player independently reached the `rows.empty` branch.
    """
    frame = _frame([[2026, 1, "SEA", None, "Out"]] * 5)
    graded = gates.assess_slate(
        {f"p{i}": (f"00-000000{i}", "SEA") for i in range(5)},
        frame, season=2026, week=1, undesignated_allowed=True,
    )
    assert {v.state for v in graded.values()} == {gates.UNKNOWN}
    assert not any(v.may_select for v in graded.values())


def test_a_usable_id_column_still_answers_normally():
    """The other direction, so the fix cannot be "return UNKNOWN always".

    One blank id beside real ones must not quarantine the readable rows.
    """
    frame = _frame([
        [2026, 1, "SEA", "00-0040648", "Out"],
        [2026, 1, "SEA", None, "Questionable"],
    ])
    assert _assess(frame).state == gates.EXCLUDED
    assert gates.usable_player_ids(frame)


def test_present_and_usable_are_different_questions():
    """`missing_injury_columns` answers the first and cannot answer the second."""
    blanked = _frame([[2026, 1, "SEA", "", "Out"]])
    assert gates.missing_injury_columns(blanked) == ()
    assert not gates.usable_player_ids(blanked)


def test_an_absent_feed_is_still_no_report_rather_than_unknown():
    """The preseason case must not be swept into UNKNOWN by the new check.

    There is no 2026 injury file until Week 1's practice week, so this is the
    ordinary state, and `NO_REPORT` has a reason sentence that is true of it.
    """
    got = _assess(pd.DataFrame())
    assert got.state == gates.NO_REPORT
    assert not got.may_select


# --------------------------------------------------------------------------
# A filter that dropped the files predating the column it filtered on.
# --------------------------------------------------------------------------

def _mixed_schema() -> pd.DataFrame:
    """Files that disagree on schema, concatenated — the real shape.

    2022-2024 carry no `season_type`; 2025-2026 do. `pd.concat` fills the
    older rows with NaN.
    """
    old = pd.DataFrame(
        [[2023, 1, "NE", "00-0000001", "Out"], [2024, 1, "NE", "00-0000002", "Out"]],
        columns=INJURY_COLUMNS,
    )
    new = pd.DataFrame(
        [[2025, 1, "NE", "00-0000003", "Out", "REG"],
         [2025, 20, "NE", "00-0000004", "Out", "POST"]],
        columns=INJURY_COLUMNS + ["season_type"],
    )
    return pd.concat([old, new], ignore_index=True)


def test_rows_from_files_predating_the_column_survive_the_filter():
    """The shipped defect dropped every one of them.

    `injuries[injuries["season_type"] == "REG"]` is False for NaN, so the two
    seasons whose files have no such column vanished — and the bets they were
    needed for filled as "not on the report" instead.
    """
    kept = availability_cost.regular_season_rows(_mixed_schema())
    assert sorted(kept["season"].unique().tolist()) == [2023, 2024, 2025]
    assert len(kept) == 3, "an absent season_type must be kept, not dropped"


def test_a_row_that_says_postseason_is_still_dropped():
    """The filter must keep doing its job; this is not "delete the filter"."""
    kept = availability_cost.regular_season_rows(_mixed_schema())
    assert "POST" not in set(kept.get("season_type", pd.Series(dtype=str)).dropna())
    assert 20 not in set(kept["week"])


def test_a_frame_with_no_season_type_column_at_all_is_untouched():
    frame = _frame([[2023, 1, "NE", "00-0000001", "Out"]])
    assert len(availability_cost.regular_season_rows(frame)) == 1


def test_the_filter_never_silently_empties_the_population():
    """The property the shipped code violated, stated as a property.

    Dropping 77% of the rows is not a filter doing its job, and nothing in the
    suite noticed because the report it fed agreed with itself.
    """
    frame = _mixed_schema()
    kept = availability_cost.regular_season_rows(frame)
    postseason = int((frame.get("season_type") == "POST").sum())
    assert len(kept) == len(frame) - postseason, (
        "the filter removed rows that are not postseason"
    )


def test_every_season_survives_the_read_concat_filter_path(tmp_path):
    """The whole path the script takes, on files that disagree on schema.

    Written against files on disk rather than an in-memory frame because the
    defect lived in the seam between them: `pd.read_csv` gives the older file
    no `season_type` column at all, `pd.concat` fills it with NaN, and only
    then does the comparison drop it. A frame built in one piece never has
    that NaN and cannot reproduce it.

    **It does not skip when the real archives are missing.** This repo's CI
    treats a skip as a gate that passed when it should have failed, and the
    first version of this test skipped in CI for exactly that reason: the
    archives are gitignored. The fixture below reproduces the real schema
    difference — 2022-2024 without `season_type`, 2025-2026 with it — so the
    guard runs everywhere, and the real archives are checked as well when a
    checkout happens to have them.
    """
    directory = tmp_path / "injuries"
    directory.mkdir()
    (directory / "injuries_2023.csv").write_text(
        "season,week,team,gsis_id,report_status\n2023,1,NE,00-0000001,Out\n",
        encoding="utf-8",
    )
    (directory / "injuries_2024.csv").write_text(
        "season,week,team,gsis_id,report_status\n2024,1,NE,00-0000002,Out\n",
        encoding="utf-8",
    )
    (directory / "injuries_2025.csv").write_text(
        "season,week,team,gsis_id,report_status,season_type\n"
        "2025,1,NE,00-0000003,Out,REG\n"
        "2025,20,NE,00-0000004,Out,POST\n",
        encoding="utf-8",
    )
    frames = [pd.read_csv(path, low_memory=False)
              for path in sorted(directory.glob("injuries_*.csv"))]
    kept = availability_cost.regular_season_rows(pd.concat(frames, ignore_index=True))
    seasons = {int(s) for s in kept["season"].dropna().unique()}
    assert seasons == {2023, 2024, 2025}, (
        f"seasons reaching the lookup: {sorted(seasons)}. The files without a "
        "`season_type` column were dropped, so every bet in those seasons "
        "fills as 'not on the report' — the bucket a shipped verdict opens"
    )
    assert 20 not in set(kept["week"]), "the postseason row survived"


def test_the_real_archives_all_reach_the_lookup_when_this_checkout_has_them():
    """The same property against the files that actually broke it.

    Conditional on the archives being present, and deliberately NOT a skip:
    with them absent this still asserts that the filter is a no-op on an
    empty population, which is true and cheap. The fixture test above is what
    guarantees coverage; this one adds the real data when it is there.
    """
    from football_betting_lab.config import RAW_DIR

    directory = RAW_DIR / "nfl" / "injuries"
    paths = sorted(directory.glob("injuries_*.csv")) if directory.is_dir() else []
    frames = [pd.read_csv(path, low_memory=False) for path in paths]
    population = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    kept = availability_cost.regular_season_rows(population)
    seasons = {int(s) for s in kept["season"].dropna().unique()} if len(kept) else set()
    for path, frame in zip(paths, frames):
        season = int(path.stem.split("_")[-1])
        if not len(frame):
            continue
        assert season in seasons, (
            f"{path.name} has {len(frame)} rows and contributes none after "
            "filtering, so every bet in that season fills as 'not on the "
            "report' — the bucket a shipped verdict would open"
        )
    # True with or without the archives, so there is no branch that asserts
    # nothing: the filter may only ever remove postseason rows.
    postseason = int((population.get("season_type") == "POST").sum()) if len(population) else 0
    assert len(kept) == len(population) - postseason
