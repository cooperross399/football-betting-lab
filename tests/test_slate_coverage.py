"""The inventory of the only asset that can still grow.

The bought population is complete. What is left is 272 games a season across 57
game days, and it cannot be back-dated: a Sunday that was never frozen is
sample that does not exist. A run that dies quietly, a provider that returns
nothing, a guard that stands down on the wrong day — each costs a game day and
none announces itself, because the card feed looks the same afterwards either
way.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from football_betting_lab.reports.slate_coverage import (
    SETTLEMENT_GRACE_DAYS,
    THIN_SNAPSHOT_ROWS,
    measure,
    render,
    scheduled_days,
    settled_row_counts,
)


def _result(days, snapshots, settled, as_of="2026-10-01"):
    return measure(
        scheduled=days,
        snapshot_rows=snapshots,
        settled_rows=settled,
        as_of=date.fromisoformat(as_of),
    )


def test_a_scheduled_day_with_no_snapshot_is_lost() -> None:
    """The one failure this organ cannot survive. The games were played and no
    opinion was frozen before them; none can be now."""
    result = _result({"2026-09-13": 13}, {}, {})

    assert [d.state for d in result.days] == ["LOST"]
    assert len(result.lost) == 1
    assert not result.is_intact


def test_a_day_still_inside_the_grace_window_is_not_yet_lost() -> None:
    """Settlement lags on purpose — nflverse revises defensive counting stats
    between Monday and Wednesday — so a recent day is waiting, not missing."""
    result = _result({"2026-09-30": 13}, {}, {}, as_of="2026-10-01")

    assert result.days[0].state == "not yet frozen"
    assert not result.lost


def test_a_frozen_and_settled_day_is_intact() -> None:
    result = _result({"2026-09-13": 13}, {"2026-09-13": 1800}, {"2026-09-13": 1800})

    assert result.days[0].state == "settled"
    assert result.is_intact


def test_a_thin_day_is_flagged_rather_than_counted_as_a_slate() -> None:
    """A run that fetched almost nothing and wrote what it had. Not lost, but
    not a day's evidence either — and it reads as one in any pooled number."""
    result = _result(
        {"2026-09-13": 13}, {"2026-09-13": THIN_SNAPSHOT_ROWS - 1}, {"2026-09-13": 4}
    )

    assert result.days[0].state == "thin"
    assert len(result.thin) == 1
    assert not result.is_intact


def test_a_frozen_day_that_never_settled_is_flagged_past_the_window() -> None:
    result = _result({"2026-09-01": 13}, {"2026-09-01": 1800}, {}, as_of="2026-10-01")

    assert result.days[0].state == "UNSETTLED"
    assert len(result.unsettled) == 1


def test_a_future_game_day_is_owed_nothing() -> None:
    """Nothing is expected for a game that has not kicked off."""
    result = _result({"2026-12-25": 3}, {}, {}, as_of="2026-10-01")

    assert result.days == []


def test_coverage_is_read_against_the_schedule_not_the_ledger() -> None:
    """A check that compares the ledger to itself reports a day that never ran
    as a day that had nothing to say. The schedule is the authority."""
    # The ledger holds one day; the schedule knows two were played.
    result = _result(
        {"2026-09-13": 13, "2026-09-14": 1},
        {"2026-09-13": 1800},
        {"2026-09-13": 1800},
    )

    assert [d.day for d in result.days] == ["2026-09-13", "2026-09-14"]
    assert result.days[1].state == "LOST"


def test_the_report_names_a_lost_day_as_unrecoverable() -> None:
    text = render(_result({"2026-09-13": 13}, {}, {}), season=2026)

    assert "LOST" in text
    assert "cannot be back-dated" in text
    assert "not recoverable" in text


def test_no_played_day_yet_is_an_absence_not_an_intact_ledger() -> None:
    """An empty report must not read as a clean bill of health — the same
    failure the settlement screen once had."""
    text = render(_result({"2026-12-25": 3}, {}, {}, as_of="2026-10-01"), season=2026)

    assert "absence, not a fault" in text
    assert "Intact" not in text


def test_scheduled_days_counts_games_per_date() -> None:
    games = pd.DataFrame(
        {
            "season": [2026, 2026, 2026, 2025],
            "game_date": ["2026-09-13", "2026-09-13", "2026-09-14", "2025-09-07"],
        }
    )

    assert scheduled_days(games, season=2026) == {"2026-09-13": 2, "2026-09-14": 1}


def test_settled_counts_come_from_the_snapshot_date() -> None:
    ledger = pd.DataFrame({"snapshot_date": ["2026-09-13"] * 3 + ["2026-09-14"]})

    assert settled_row_counts(ledger) == {"2026-09-13": 3, "2026-09-14": 1}
