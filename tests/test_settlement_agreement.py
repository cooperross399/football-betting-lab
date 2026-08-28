"""The one defect a backtest cannot catch by checking itself.

A settlement offset is constant, so it replicates perfectly across seasons,
survives split-half, survives a family correction, and looks exactly like a
stable edge. `tackles_assists` returned +16.3% across three seasons and passed
every one of those checks. The screen here found it in one number.
"""

from __future__ import annotations

import pandas as pd
import pytest

from football_betting_lab.reports.settlement_agreement import (
    CHARTING_DEPENDENT,
    IMPLIED_GAP_TOLERANCE,
    MINIMUM_WAGERS,
    MarketAgreement,
    measure,
    render,
)


def _wagers(market: str, n: int, priced: float, realised: float) -> pd.DataFrame:
    """`n` wagers on a 0.5 line, priced at `priced`, landing over `realised`."""
    overs = int(n * realised)
    return pd.DataFrame(
        [
            {"market": market, "line": 0.5, "actual": 1.0 if i < overs else 0.0,
             "implied_over": priced}
            for i in range(n)
        ]
    )


def test_a_market_settled_on_what_was_priced_agrees() -> None:
    result = measure(_wagers("receptions", 1000, 0.50, 0.50))

    assert not result.markets[0].suspect
    assert "agrees" in result.markets[0].reading()


def test_a_market_settled_on_a_smaller_quantity_is_caught() -> None:
    """`tackles_assists`: priced 50% over, realised 42%."""
    result = measure(_wagers("tackles_assists", 7_144, 0.50, 0.42))

    entry = result.markets[0]
    assert entry.suspect
    assert entry.gap == pytest.approx(-0.08, abs=0.005)
    assert "settlement suspect" in entry.reading()
    assert "charted quantity" in entry.reading()


def test_a_longshot_market_is_not_flagged_for_being_a_longshot() -> None:
    """The naive screen compared the over rate to a half and flagged
    `anytime_td`, where 13% is exactly right because the line is 0.5 and most
    players do not score. Comparing to the price fixes that."""
    result = measure(_wagers("anytime_td", 1_219, 0.19, 0.18))

    assert not result.markets[0].suspect


def test_a_yardage_market_is_not_flagged_for_being_skewed() -> None:
    """The naive screen also flagged the yardage markets on an absolute median
    gap of 2.5 yards against a 37-yard line, which is nothing."""
    result = measure(_wagers("reception_yards", 40_798, 0.47, 0.47))

    assert not result.markets[0].suspect


def test_a_thin_market_is_not_screened_rather_than_passed() -> None:
    """A rate computed on a handful of lines says nothing, and saying it
    agrees would be a claim."""
    entry = measure(_wagers("rush_tds", MINIMUM_WAGERS - 1, 0.5, 0.2)).markets[0]

    assert not entry.suspect
    assert not entry.screened
    assert "not screened" in entry.reading()


# -- what a gap is worth -----------------------------------------------------


def test_a_gap_is_translated_into_what_it_hands_a_one_sided_model() -> None:
    """The tackles gap is 8 points and the measured "edge" was +16.3%. Those
    are the same number, and the report has to make that visible."""
    entry = MarketAgreement(
        market="tackles_assists", wagers=7_144, over_rate=0.42, implied_over=0.50
    )

    assert entry.worth_to_one_side == pytest.approx(0.16, abs=0.005)


def test_passing_the_screen_is_not_a_clean_bill_of_health() -> None:
    """A three-point gap is inside the tolerance and worth six points of
    return, which can be most of a market's measured edge."""
    entry = MarketAgreement(
        market="rush_yards", wagers=18_971, over_rate=0.45, implied_over=0.47
    )

    assert not entry.suspect
    assert entry.worth_to_one_side > 0.03
    assert "not a clean bill of health" in render(measure(
        _wagers("rush_yards", 1000, 0.47, 0.45)
    ))


def test_the_charting_dependent_markets_are_named_in_advance() -> None:
    """Named before the data was looked at, so "the suspect market is the
    charted one" is a prediction rather than a story told afterwards."""
    assert "tackles_assists" in CHARTING_DEPENDENT
    assert "sacks" in CHARTING_DEPENDENT
    assert "receptions" not in CHARTING_DEPENDENT
    assert "reception_yards" not in CHARTING_DEPENDENT


def test_the_tolerance_is_larger_than_any_plausible_edge() -> None:
    """A screen tighter than the effect it is screening for fires on
    everything and gets ignored."""
    assert IMPLIED_GAP_TOLERANCE >= 0.03
