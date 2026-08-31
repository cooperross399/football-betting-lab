"""American odds cannot be averaged, and an edge that needs the best of
thirteen quotes is not the same thing as a disagreement with the market.
"""

from __future__ import annotations

import pandas as pd
import pytest

from football_betting_lab.reports.price_sensitivity import (
    BookResult,
    MarketSensitivity,
    from_implied,
    measure,
    profit,
    to_implied,
)


def test_american_odds_round_trip_through_probability() -> None:
    """Round-tripped as *payouts*, not as representations.

    +100 and -100 are the same price — even money — and the conversion picks
    the favourite spelling for a probability of exactly a half. Asserting the
    literal number back would be asserting a convention.
    """
    odds = pd.Series([-200.0, -110.0, 100.0, 150.0, 600.0])

    round_tripped = to_implied(from_implied(to_implied(odds)))

    assert list(round_tripped) == pytest.approx(list(to_implied(odds)), rel=1e-9)


def test_the_median_of_two_opposite_prices_is_a_real_price() -> None:
    """The bug this exists for: the median of [-110, +105] in American odds is
    -2.5, which is not a price, and the median of a symmetric pair is zero,
    which divided into a payout is infinity. The first version of this report
    printed `+inf%` in eight rows."""
    pair = pd.Series([-110.0, 105.0])

    consensus = from_implied(pd.Series([to_implied(pair).median()]))

    assert abs(consensus.iloc[0]) >= 100.0
    assert consensus.iloc[0] != 0


def test_profit_is_finite_for_every_valid_price() -> None:
    odds = pd.Series([-1000.0, -100.0, 100.0, 5000.0])
    outcome = pd.Series(["won", "won", "lost", "push"])

    assert profit(odds, outcome).abs().max() < float("inf")


def _frame(rows: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame]:
    bets = pd.DataFrame(
        [
            {
                "event_id": r["event"], "market": "rush_yards", "player": "P",
                "selection": "over", "line": 40.5, "outcome": r["outcome"],
                "profit": r["profit"],
            }
            for r in rows
        ]
    )
    prices = pd.DataFrame(
        [
            {
                "event_id": r["event"], "market": "rush_yards", "player": "P",
                "selection": "over", "line": 40.5, "american_odds": odds,
                "book": book,
            }
            for r in rows
            for book, odds in r["quotes"].items()
        ]
    )
    return bets, prices


def test_an_edge_that_only_exists_at_the_best_quote_is_named_a_shopping_premium() -> None:
    """One book pays +200 and the rest pay -150 on a bet that loses more often
    than not. Best-of-N looks fine; nobody could run it."""
    # 40% strike rate. At +200 that returns +20%; at the -150 consensus it
    # returns -33%. The bet is only good at the one book paying +200.
    rows = [
        {
            "event": f"e{i}", "outcome": "won" if i % 5 < 2 else "lost",
            "profit": 2.0 if i % 5 < 2 else -1.0,
            "quotes": {"soft": 200.0, "a": -150.0, "b": -150.0, "c": -150.0},
        }
        for i in range(500)
    ]
    bets, prices = _frame(rows)

    entry = measure(bets, prices)[0]

    assert entry.best_of_n_roi > 0
    assert entry.consensus_roi < 0
    assert "shopping premium" in entry.reading()


def test_an_edge_present_at_most_books_is_named_as_surviving() -> None:
    rows = [
        {
            "event": f"e{i}", "outcome": "won" if i % 2 == 0 else "lost",
            "profit": 1.0 if i % 2 == 0 else -1.0,
            "quotes": {b: 120.0 for b in ("a", "b", "c", "d")},
        }
        for i in range(500)
    ]
    bets, prices = _frame(rows)

    entry = measure(bets, prices)[0]

    assert entry.consensus_roi > 0
    assert "survives" in entry.reading()


def test_a_book_with_too_few_bets_is_not_reported() -> None:
    """A number computed on a handful of wagers is noise wearing a book's
    name."""
    rows = [
        {
            "event": f"e{i}", "outcome": "won", "profit": 1.0,
            "quotes": {"big": 100.0, "tiny": 100.0} if i < 5 else {"big": 100.0},
        }
        for i in range(500)
    ]
    bets, prices = _frame(rows)

    entry = measure(bets, prices)[0]

    assert [b.book for b in entry.books] == ["big"]


def test_no_books_means_no_claim() -> None:
    entry = MarketSensitivity(market="x", best_of_n_roi=0.2, consensus_roi=0.2)

    assert "no book quoted enough" in entry.reading()


def test_a_market_negative_at_every_price_is_not_called_a_shopping_premium() -> None:
    """"Shopping premium" claims the edge exists at the best of N quotes.

    That requires the best of N to be positive. Without the check, a market
    losing money at the consensus *and* at the best price available anywhere
    was still described as having an edge you could shop for — the most
    flattering possible reading of a market that loses at every price a human
    could take.
    """
    entry = MarketSensitivity(
        market="rush_attempts",
        best_of_n_roi=-0.078,
        consensus_roi=-0.110,
        books=[BookResult(book=f"b{i}", bets=500, roi=-0.05) for i in range(8)],
    )

    reading = entry.reading()

    assert "shopping premium" not in reading
    assert "loses at every price" in reading


def test_a_market_positive_only_at_the_best_of_n_is_still_a_shopping_premium() -> None:
    entry = MarketSensitivity(
        market="rush_yards",
        best_of_n_roi=0.009,
        consensus_roi=-0.010,
        books=[
            BookResult(book=f"b{i}", bets=500, roi=0.02 if i < 2 else -0.04)
            for i in range(10)
        ],
    )

    assert "shopping premium" in entry.reading()
