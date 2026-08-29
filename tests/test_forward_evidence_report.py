"""Reading the ledger back, with every instrument the historical work earned.

The ledger is the only evidence this lab can still gather — the bought
population is complete — so it is the one place a mistake in reading it
compounds for a whole season.
"""

from __future__ import annotations

import pandas as pd

from football_betting_lab.forward_evidence import render_ledger
from football_betting_lab.leagues import NFL


def _ledger(rows: list[dict]) -> pd.DataFrame:
    base = {
        "snapshot_date": "2026-09-13",
        "home_team": "Seattle Seahawks",
        "away_team": "New England Patriots",
        "market": "rush_yards",
        "outcome": "won",
        "profit_units": 1.0,
    }
    return pd.DataFrame([{**base, **row} for row in rows])


def _many(market: str, n: int, profit: float, outcome: str = "won") -> list[dict]:
    return [
        {
            "market": market,
            "outcome": outcome,
            "profit_units": profit,
            "snapshot_date": f"2026-09-{13 + i % 15:02d}",
            "home_team": f"H{i % 30}",
            "away_team": f"A{i % 30}",
        }
        for i in range(n)
    ]


def test_an_empty_ledger_offers_no_number() -> None:
    text = render_ledger(pd.DataFrame(), NFL)

    assert "ledger is empty" in text
    assert "absence, not a result" in text


def test_a_settlement_suspect_is_reported_as_not_evidence() -> None:
    """`tackles_assists` returned +16% across three bought seasons on a
    settlement offset alone. The ledger must not repeat that reading."""
    ledger = _ledger(_many("tackles_assists", 400, 1.0))

    text = render_ledger(
        ledger, NFL, settlement_suspects=frozenset({"tackles_assists"})
    )

    assert "not evidence" in text
    assert "settlement suspect" in text


def test_a_settlement_suspect_is_excluded_from_the_pooled_number() -> None:
    """Pooling it would import the artefact into the headline."""
    ledger = _ledger(_many("tackles_assists", 400, 1.0) + _many("rush_yards", 400, -1.0))

    text = render_ledger(
        ledger, NFL, settlement_suspects=frozenset({"tackles_assists"})
    )

    assert "Pooled, excluding settlement suspects: -100.0%" in text


def test_a_thin_market_is_not_enough_evidence_rather_than_a_number() -> None:
    ledger = _ledger(_many("rush_yards", 20, 1.0))

    text = render_ledger(ledger, NFL, minimum_bets=200)

    assert "not enough evidence" in text


def test_an_interval_including_zero_says_no_demonstrated_edge() -> None:
    """In those words, every time."""
    rows = _many("rush_yards", 300, 1.0) + _many("rush_yards", 300, -1.0)
    text = render_ledger(_ledger(rows), NFL, minimum_bets=100)

    assert "no demonstrated edge" in text


def test_voids_are_excluded_from_the_return_and_the_assumption_is_stated() -> None:
    """A void returns the stake. Counting it as a loss would be a different
    strategy, and the assumption is the largest one in the lab."""
    rows = _many("rush_yards", 100, 1.0) + _many("rush_yards", 100, 0.0, "void")
    text = render_ledger(_ledger(rows), NFL, minimum_bets=50)

    assert "100 settled" in text
    assert "100 voided" in text
    assert "largest assumption" in text


def test_the_report_names_that_the_ledger_is_the_only_growing_evidence() -> None:
    text = render_ledger(_ledger(_many("rush_yards", 10, 1.0)), NFL)

    assert "bought population is complete" in text
