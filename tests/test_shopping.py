"""Shopping lowers the hold. It cannot lower it past what the books quote.

The arithmetic that decides this whole question is one line: a book pricing
both sides proportionally to the fair probability leaves `-h / (1 + h)` on
either side, so the hold IS the model-free expected loss. Everything else here
guards the pairing, because a best over taken from one product and a best under
from another manufactures a hold nobody quoted — and the first run of this
report reported -48% arbitrage on exactly that shape before the bad quotes
were found.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from football_betting_lab.reports import shopping


def _prices(rows) -> pd.DataFrame:
    """(book, selection, odds, line, market, event, phase)."""
    return pd.DataFrame(
        [{"book": b, "selection": s, "american_odds": o, "line": ln,
          "market": m, "event_id": e, "identity": "", "phase": p}
         for b, s, o, ln, m, e, p in rows]
    )


def _pair(book: str, over: float, under: float, line: float = 10.5,
          market: str = "receptions", event: str = "e1", phase: str = "card"):
    return [(book, "over", over, line, market, event, phase),
            (book, "under", under, line, market, event, phase)]


def test_the_hold_is_the_two_implied_probabilities_less_one() -> None:
    quotes = shopping.two_sided(_prices(_pair("dk", -110, -110)))
    assert quotes["hold"].iloc[0] == pytest.approx(0.0476, abs=1e-4)


def test_betting_blind_returns_the_hold_back() -> None:
    """Not an approximation: a proportionally-vigged book leaves exactly this."""
    assert shopping.blind_return(0.0476) == pytest.approx(-0.0454, abs=1e-4)
    assert shopping.blind_return(0.0) == 0.0


def test_a_population_with_no_unders_at_all_is_refused() -> None:
    """One side across the whole cache is a broken input, not a thin market."""
    rows = [("dk", "over", -110, 10.5, "receptions", "e1", "card")]
    with pytest.raises(ValueError, match="two-sided"):
        shopping.two_sided(_prices(rows))


def test_a_single_one_sided_wager_is_dropped_and_the_rest_survive() -> None:
    rows = _pair("dk", -110, -110)
    rows += [("dk", "over", 250, 40.5, "receptions", "e2", "card")]
    quotes = shopping.two_sided(_prices(rows))
    assert list(quotes["event_id"]) == ["e1"]


def test_two_sides_at_different_lines_are_never_paired() -> None:
    """Pairing a best over at 10.5 against a best under at 12.5 invents a hold
    nobody quoted, and it is the shape that produced a -48% 'arbitrage'."""
    rows = [("dk", "over", -110, 10.5, "receptions", "e1", "card"),
            ("dk", "under", -110, 12.5, "receptions", "e1", "card")]
    assert shopping.two_sided(_prices(rows)).empty
    assert "line" in shopping.WAGER_KEY


def test_the_card_price_and_the_close_are_never_paired() -> None:
    rows = [("dk", "over", -110, 10.5, "receptions", "e1", "card"),
            ("dk", "under", -110, 10.5, "receptions", "e1", "close")]
    assert shopping.two_sided(_prices(rows)).empty
    assert "phase" in shopping.WAGER_KEY


def test_shopping_two_books_cannot_raise_the_hold() -> None:
    rows = _pair("dk", -120, -105) + _pair("fd", -105, -120)
    curve = shopping.hold_curve(shopping.two_sided(_prices(rows)), draws=1)
    assert curve.median_hold[1] < curve.median_hold[0]


def test_the_curve_samples_books_at_random_rather_than_taking_the_best() -> None:
    """`what if I held accounts at N books` is answerable; `what if I held the
    N that turned out best` is not, and would understate the hold at every N."""
    rows = _pair("a", -110, -110) + _pair("b", -110, -110) + _pair("c", 100, 100)
    curve = shopping.hold_curve(shopping.two_sided(_prices(rows)), draws=200)
    # One book at random is usually one of the two vigged ones, so the median
    # single-book hold is theirs, not the zero-hold outlier's.
    assert curve.median_hold[0] > 0.04
    assert curve.median_hold[-1] == pytest.approx(0.0, abs=1e-9)


def test_an_implausible_quote_needs_three_books_to_be_called_odd() -> None:
    """With two books there is no majority to be the odd one out of."""
    two = shopping.two_sided(_prices(_pair("a", 380, -594) + _pair("b", -295, 220)))
    assert not shopping.implausible(two).any()

    three = shopping.two_sided(_prices(
        _pair("a", 380, -594) + _pair("b", 400, -625) + _pair("c", -295, 220)
    ))
    flagged = shopping.implausible(three)
    assert flagged.sum() == 1
    assert three.loc[flagged, "book"].iloc[0] == "c"


def test_a_crossing_is_reported_with_the_books_behind_it() -> None:
    rows = _pair("a", 120, -105) + _pair("b", -105, 120)
    out = shopping.crossed(shopping.two_sided(_prices(rows)))
    assert len(out) == 1
    assert out["hold"].iloc[0] < 0
    assert out["books"].iloc[0] == 2


def test_an_ordinary_two_sided_market_never_crosses() -> None:
    rows = _pair("a", -110, -110) + _pair("b", -112, -108)
    assert shopping.crossed(shopping.two_sided(_prices(rows))).empty
