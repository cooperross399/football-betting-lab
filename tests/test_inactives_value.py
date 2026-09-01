"""The gate's own premise, measured with a snapshot nobody was reading.

This lab refuses to let any player prop produce a selection because inactives
drop ninety minutes out and the card runs three hours out. That premise was
argued about for weeks and never measured — while the evidence sat in the
cache, labelled `mid`, read by nothing.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from football_betting_lab.reports.inactives_value import (
    MATERIAL_BRIER_GAIN,
    MINIMUM_WAGERS,
    InactivesValue,
    MarketMovement,
    implied,
    measure,
    render,
)


def _frames(n: int, early_odds: int, late_odds: int, win_rate: float = 0.5):
    keys = [
        {"event_id": f"e{i}", "market": "rush_yards", "player": f"p{i}",
         "selection": "over", "line": 49.5}
        for i in range(n)
    ]
    early = pd.DataFrame([{**k, "american_odds": early_odds} for k in keys])
    late = pd.DataFrame([{**k, "american_odds": late_odds} for k in keys])
    outcomes = pd.DataFrame([
        {**k, "outcome": "won" if i < round(win_rate * n) else "lost"}
        for i, k in enumerate(keys)
    ])
    return early, late, outcomes


def test_a_later_price_closer_to_the_truth_scores_a_gain() -> None:
    """The whole question: does crossing the deadline make the price a better
    forecast? Here the truth is 0.5, the early price says ~0.69 and the late
    one says ~0.52."""
    early, late, outcomes = _frames(600, early_odds=-220, late_odds=-110)

    result = measure(early, late, outcomes)

    assert result.movements[0].brier_gain > 0
    assert result.movements[0].is_material


def test_a_price_that_barely_moves_buys_nothing() -> None:
    """The measured answer: 0 of 17 markets cleared the threshold, and the
    largest gain was +0.00085 against 0.002."""
    early, late, outcomes = _frames(600, early_odds=-110, late_odds=-110)

    result = measure(early, late, outcomes)

    assert result.movements[0].brier_gain == pytest.approx(0.0)
    assert not result.movements[0].is_material
    assert not result.gate_is_expensive


def test_a_thin_market_is_not_reported() -> None:
    early, late, outcomes = _frames(MINIMUM_WAGERS - 10, -220, -110)

    assert measure(early, late, outcomes).movements == []


def test_a_wager_with_no_late_price_is_dropped_by_the_join() -> None:
    """A scratched player loses his market entirely, so the dropped rows are
    enriched in exactly the players this question is about. The join is inner
    on purpose and the report says how many it lost."""
    early, late, outcomes = _frames(600, -110, -110)
    late = late.iloc[:400]

    result = measure(early, late, outcomes)

    assert result.movements[0].wagers == 400


def test_the_report_states_the_selection_effect_it_cannot_escape() -> None:
    early, late, outcomes = _frames(600, -110, -110)

    text = render(measure(early, late, outcomes), dropped=82_810)

    assert "82,810" in text
    assert "conditioned on the wager still existing" in text


def test_the_report_calls_itself_an_upper_bound() -> None:
    """Five hours of steam, weather and late news move a line too. A large gap
    could be any of them; only a small gap is informative."""
    early, late, outcomes = _frames(600, -110, -110)

    text = render(measure(early, late, outcomes))

    assert "upper bound" in text
    assert "small gap is the more informative" in text


def test_measuring_nothing_is_an_absence_not_a_confirmation() -> None:
    """An empty table must not read as "the gate is free" — the same failure
    the settlement screen once had."""
    text = render(InactivesValue())

    assert "absence, not a finding" in text
    assert "remains unmeasured rather than confirmed" in text


def test_a_gate_is_expensive_only_when_most_markets_move() -> None:
    better = [MarketMovement("a", 500, 0.02, 0.250, 0.240),
              MarketMovement("b", 500, 0.02, 0.250, 0.240)]
    flat = [MarketMovement("c", 500, 0.001, 0.250, 0.2500)]

    assert InactivesValue(movements=better).gate_is_expensive
    assert not InactivesValue(movements=better[:1] + flat + flat).gate_is_expensive


def test_implied_handles_both_sides_of_the_american_convention() -> None:
    got = implied([-110, 100, 150])

    assert got[0] == pytest.approx(110 / 210)
    assert got[1] == pytest.approx(0.5)
    assert got[2] == pytest.approx(100 / 250)
