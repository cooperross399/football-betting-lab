"""A winning record with negative CLV is variance, and it says so.

CLV is the fastest honest signal at these sample sizes — an NFL season is 272
games, and roughly six hundred bets separate a real +8% edge from zero. It is
also the check that stops a good run being mistaken for a good model.
"""

from __future__ import annotations

import pandas as pd
import pytest

from football_betting_lab.reports.clv import MarketCLV, closing_prices, measure, render
from football_betting_lab.reports.props_backtest import MINIMUM_BETS


def _prices(rows: list[dict]) -> pd.DataFrame:
    base = {
        "event_id": "e1",
        "market": "receptions",
        "player": "A Player",
        "selection": "over",
        "line": 4.5,
        "american_odds": -110,
        "book": "dk",
        "snapshot": "20250907T170000Z",
        "home_team": "Seattle Seahawks",
        "away_team": "New England Patriots",
    }
    return pd.DataFrame([{**base, **row} for row in rows])


def _bets(rows: list[dict]) -> pd.DataFrame:
    base = {
        "event_id": "e1",
        "market": "receptions",
        "player": "A Player",
        "selection": "over",
        "line": 4.5,
        "odds": -110,
        "outcome": "won",
        "profit": 0.91,
    }
    return pd.DataFrame([{**base, **row} for row in rows])


def test_no_closing_snapshot_is_an_absence_not_a_zero() -> None:
    result = measure(_bets([{}]), _prices([{}]))

    assert not result.closing_available
    assert result.unmatched == 1
    assert "not a zero" in render(result)


def test_a_price_that_shortened_is_positive_clv() -> None:
    """The bet was taken at +150 and the market closed at -110, so the price
    moved toward it."""
    prices = _prices(
        [
            {"american_odds": 150, "snapshot": "20250907T170000Z"},
            {"american_odds": -110, "snapshot": "20250907T175500Z"},
        ]
    )

    result = measure(_bets([{"odds": 150}]), prices)

    assert result.matched == 1
    assert result.markets[0].mean_clv > 0


def test_a_price_that_drifted_is_negative_clv() -> None:
    prices = _prices(
        [
            {"american_odds": -110, "snapshot": "20250907T170000Z"},
            {"american_odds": 150, "snapshot": "20250907T175500Z"},
        ]
    )

    result = measure(_bets([{"odds": -110}]), prices)

    assert result.markets[0].mean_clv < 0


def test_a_bet_with_no_closing_price_is_excluded_rather_than_counted_as_zero() -> None:
    """Counting it zero would drag every mean toward nothing and hide how much
    of the board could not be judged at all."""
    prices = _prices(
        [
            {"american_odds": -110, "snapshot": "20250907T170000Z"},
            {"american_odds": -110, "snapshot": "20250907T175500Z"},
        ]
    )
    bets = _bets([{}, {"player": "Nobody", "event_id": "e1"}])

    result = measure(bets, prices)

    assert result.matched == 1
    assert result.unmatched == 1


def test_the_closing_price_taken_is_the_best_available() -> None:
    """Comparing a best-of-nine entry against a single book's close would
    manufacture CLV out of shopping."""
    prices = _prices(
        [
            {"american_odds": -110, "snapshot": "20250907T170000Z"},
            {"american_odds": -130, "snapshot": "20250907T175500Z", "book": "a"},
            {"american_odds": 120, "snapshot": "20250907T175500Z", "book": "b"},
        ]
    )

    closes = closing_prices(prices)

    assert len(closes) == 1
    assert closes["american_odds"].iloc[0] == 120


# -- the readings the brief fixes --------------------------------------------


def test_a_winning_record_with_negative_clv_is_called_variance() -> None:
    entry = MarketCLV(
        market="x", bets=1000, matched=1000, mean_clv=-0.02, roi=0.08
    )

    assert "is variance" in entry.reading()


def test_a_losing_record_with_positive_clv_is_called_out_too() -> None:
    entry = MarketCLV(
        market="x", bets=1000, matched=1000, mean_clv=0.02, roi=-0.05
    )

    reading = entry.reading()

    assert "right side of the move" in reading
    assert "variance" not in reading


def test_below_the_declared_minimum_no_reading_is_offered() -> None:
    entry = MarketCLV(
        market="x", bets=10, matched=MINIMUM_BETS - 1, mean_clv=0.05, roi=0.40
    )

    assert "not enough evidence" in entry.reading()


def test_clv_and_return_are_reported_side_by_side_never_instead() -> None:
    prices = _prices(
        [
            {"american_odds": 150, "snapshot": "20250907T170000Z"},
            {"american_odds": -110, "snapshot": "20250907T175500Z"},
        ]
    )

    text = render(measure(_bets([{"odds": 150}]), prices))

    assert "ROI" in text
    assert "Mean CLV" in text
    assert "cannot make a losing model profitable" in text


def test_a_trivially_small_clv_reads_as_none_rather_than_positive() -> None:
    """With a hundred thousand bets almost any departure from zero is
    statistically distinguishable, and two hundredths of a probability point
    still cannot matter. The first version of this report called +0.02%
    "positive CLV, consistent with the return" — a sentence that reads like a
    confirmation and contains none."""
    entry = MarketCLV(market="x", bets=6_812, matched=6_568, mean_clv=0.0002, roi=0.163)

    reading = entry.reading()

    assert "no measurable CLV" in reading
    assert "did not move toward these bets" in reading


def test_a_material_clv_still_reads_as_positive() -> None:
    entry = MarketCLV(market="x", bets=1000, matched=1000, mean_clv=0.02, roi=0.08)

    assert "positive CLV" in entry.reading()


def test_a_market_that_moves_both_ways_equally_is_called_indifferent() -> None:
    """Over a six-hour window 70% of prices moved and 51% moved toward the
    bet. A mean CLV of +0.06 probability points is hard to read; "the line
    moved toward these bets 51% of the time" is not."""
    entry = MarketCLV(
        market="rush_yards", bets=16_829, matched=13_518, mean_clv=0.0004,
        roi=0.13, movers=10_072, moved_toward=0.48,
    )

    reading = entry.reading()

    assert "market is indifferent" in reading
    assert "48% moved toward" in reading


def test_a_market_that_moves_toward_the_bet_is_not_called_indifferent() -> None:
    entry = MarketCLV(
        market="x", bets=5_000, matched=5_000, mean_clv=0.02, roi=0.05,
        movers=4_000, moved_toward=0.62,
    )

    assert "indifferent" not in entry.reading()


def test_too_few_movers_to_judge_does_not_claim_indifference() -> None:
    entry = MarketCLV(
        market="x", bets=300, matched=300, mean_clv=0.0, roi=0.05,
        movers=10, moved_toward=0.50,
    )

    assert "indifferent" not in entry.reading()
