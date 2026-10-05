"""The selections ledger freezes what the card actually selected, narrower
than the forward ledger, and settles it with the same machinery rather than a
second copy of it.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from football_betting_lab.forward_evidence import SNAPSHOT_COLUMNS
from football_betting_lab.leagues import NFL
from football_betting_lab.selections_ledger import (
    render_selections_record,
    write_selections_snapshot,
)


def _pick(**overrides) -> dict:
    base = {
        "game": "New England Patriots @ Seattle Seahawks",
        "home_team": "Seattle Seahawks",
        "away_team": "New England Patriots",
        "commence_time": "2026-09-10T00:20:00Z",
        "market": "moneyline",
        "player": "",
        "selection": "home",
        "line": None,
        "odds": -150,
        "book": "draftkings",
        "model_probability": 0.62,
        "edge": 0.03,
    }
    base.update(overrides)
    return base


def test_an_empty_selections_list_writes_nothing(tmp_path: Path) -> None:
    """A `no-selections` day must not lock the date, so a later run that finds
    something can still write it."""
    assert write_selections_snapshot(
        [], snapshot_date="2026-09-09", archive_dir=tmp_path
    ) is None
    assert not (tmp_path / "selections_snapshots").exists()


def test_the_first_opinion_of_the_day_stands(tmp_path: Path) -> None:
    first = write_selections_snapshot(
        [_pick()], snapshot_date="2026-09-09", archive_dir=tmp_path
    )
    assert first is not None
    assert len(pd.read_csv(first)) == 1

    second = write_selections_snapshot(
        [_pick(), _pick(market="spread")],
        snapshot_date="2026-09-09",
        archive_dir=tmp_path,
    )
    assert second is None
    assert len(pd.read_csv(first)) == 1


def test_the_snapshot_matches_the_shape_forward_evidence_already_settles(
    tmp_path: Path,
) -> None:
    """No new settlement logic: the snapshot has to be exactly the shape
    `settle_snapshot` already knows how to read, or this module would be
    re-implementing settlement a second time."""
    path = write_selections_snapshot(
        [_pick(line=-3.5, market="spread", odds=-110)],
        snapshot_date="2026-09-09",
        archive_dir=tmp_path,
    )
    frame = pd.read_csv(path)
    assert list(frame.columns) == list(SNAPSHOT_COLUMNS)
    row = frame.iloc[0]
    assert row["home_team"] == "Seattle Seahawks"
    assert row["away_team"] == "New England Patriots"
    assert row["market"] == "spread"
    assert row["line"] == -3.5
    assert row["american_odds"] == -110


def test_correlated_selections_are_not_collapsed(tmp_path: Path) -> None:
    """The same game's alternate-line ladder is several distinct
    propositions, not duplicates of one. Collapsing them would throw away
    evidence to make the row count smaller."""
    ladder = [_pick(market="alternate_spread", line=line) for line in (-3, -3.5, -4)]
    path = write_selections_snapshot(
        ladder, snapshot_date="2026-09-09", archive_dir=tmp_path
    )
    assert len(pd.read_csv(path)) == 3


def test_an_empty_ledger_reports_absence_not_a_result() -> None:
    text = render_selections_record(pd.DataFrame(), NFL)
    assert "Selections record" in text
    assert "empty" in text.lower()


def test_the_heading_distinguishes_it_from_the_forward_ledger() -> None:
    """Both reports share `render_ledger`; the heading is the only thing that
    tells a reader which question is being answered."""
    text = render_selections_record(pd.DataFrame(), NFL)
    assert text.startswith("# Selections record")
    assert "# Forward evidence" not in text
