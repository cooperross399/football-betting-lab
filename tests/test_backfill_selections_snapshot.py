"""The 2026-10-04 card ran before `write_selections_snapshot` existed, so its
selections are reconstructed from `card.md` rather than lost. This has to be
exact — joined back to the priced snapshot, never guessed — and it has to
fail loudly rather than write a partial file when a row cannot be matched.
"""

from __future__ import annotations

import importlib.util

import pandas as pd

from football_betting_lab.config import PROJECT_ROOT
from football_betting_lab.forward_evidence import SNAPSHOT_COLUMNS

_spec = importlib.util.spec_from_file_location(
    "_backfill_selections_snapshot",
    PROJECT_ROOT / "scripts" / "backfill_selections_snapshot.py",
)
_backfill = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_backfill)
build_snapshot = _backfill.build_snapshot
parse_selections_table = _backfill.parse_selections_table

CARD_MD = """# NFL card — 2026-10-04

## Selections

| Game | Market | Selection | Line | Price | Book | Edge |
|:-----|:-------|:----------|-----:|------:|:-----|-----:|
| Miami Dolphins @ Minnesota Vikings | `alternate_team_total` | away_over | 17.5 | +210 | fanduel | +27.9% |
| Los Angeles Rams @ Philadelphia Eagles | `moneyline` | home | — | +170 | draftkings | +26.5% |

## Markets, and why each is excluded
"""


def _priced_snapshot() -> pd.DataFrame:
    rows = [
        {
            "snapshot_date": "2026-10-04",
            "commence_time": "2026-10-04T20:05:00Z",
            "home_team": "Minnesota Vikings",
            "away_team": "Miami Dolphins",
            "market": "alternate_team_total",
            "player": None,
            "selection": "away_over",
            "line": 17.5,
            "american_odds": 210,
            "book": "fanduel",
            "model_probability": 0.42,
            "edge": 0.279,
            "calibrated_probability": None,
            "calibrated_edge": None,
            "gates_in_force": "60 market(s) allowlisted",
        },
        {
            "snapshot_date": "2026-10-04",
            "commence_time": "2026-10-04T17:00:00Z",
            "home_team": "Philadelphia Eagles",
            "away_team": "Los Angeles Rams",
            "market": "moneyline",
            "player": None,
            "selection": "home",
            "line": None,
            "american_odds": 170,
            "book": "draftkings",
            "model_probability": 0.60,
            "edge": 0.265,
            "calibrated_probability": None,
            "calibrated_edge": None,
            "gates_in_force": "60 market(s) allowlisted",
        },
        # A row the card never selected — present to prove the join does not
        # pick up extras.
        {
            "snapshot_date": "2026-10-04",
            "commence_time": "2026-10-04T17:00:00Z",
            "home_team": "Philadelphia Eagles",
            "away_team": "Los Angeles Rams",
            "market": "moneyline",
            "player": None,
            "selection": "away",
            "line": None,
            "american_odds": -200,
            "book": "draftkings",
            "model_probability": 0.40,
            "edge": -0.05,
            "calibrated_probability": None,
            "calibrated_edge": None,
            "gates_in_force": "60 market(s) allowlisted",
        },
    ]
    return pd.DataFrame(rows)


def test_parses_every_row_of_the_selections_table() -> None:
    picks = parse_selections_table(CARD_MD)
    assert len(picks) == 2
    assert picks[0]["game"] == "Miami Dolphins @ Minnesota Vikings"
    assert picks[0]["market"] == "alternate_team_total"
    assert picks[0]["line"] == 17.5
    assert picks[1]["line"] is None  # the moneyline's "—"


def test_the_reconstruction_matches_shape_and_content() -> None:
    frame, unmatched = build_snapshot(CARD_MD, _priced_snapshot(), "2026-10-04")
    assert unmatched == []
    assert list(frame.columns) == list(SNAPSHOT_COLUMNS)
    assert len(frame) == 2

    row = frame[frame["market"] == "alternate_team_total"].iloc[0]
    assert row["home_team"] == "Minnesota Vikings"
    assert row["away_team"] == "Miami Dolphins"
    assert row["commence_time"] == "2026-10-04T20:05:00Z"
    assert row["model_probability"] == 0.42
    assert row["edge"] == 0.279

    # Only the selected side of the moneyline, never the unselected "away".
    moneyline_rows = frame[frame["market"] == "moneyline"]
    assert len(moneyline_rows) == 1
    assert moneyline_rows.iloc[0]["selection"] == "home"


def test_an_unmatched_pick_fails_loudly_rather_than_writing_a_partial_file() -> None:
    picks_only_priced = _priced_snapshot().iloc[:1]  # drop the moneyline row
    frame, unmatched = build_snapshot(CARD_MD, picks_only_priced, "2026-10-04")
    assert len(unmatched) == 1
    assert unmatched[0]["market"] == "moneyline"
    # The matched row is still returned — main() is the one that refuses to
    # write anything when unmatched is non-empty.
    assert len(frame) == 1
