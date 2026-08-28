"""One wager is one bet, and a result that excludes zero is still a candidate.

The two mistakes this file guards are the ones that would make a losing model
look like a winning one: counting the same wager once per book, and calling a
single season's non-zero interval a finding.
"""

from __future__ import annotations

import pandas as pd
import pytest

from football_betting_lab.reports.props_backtest import (
    MINIMUM_BETS,
    MarketResult,
    best_price_per_selection,
    fragility,
)


def _prices(rows: list[dict]) -> pd.DataFrame:
    base = {
        "event_id": "e1",
        "market": "receptions",
        "player": "A Player",
        "selection": "over",
        "line": 4.5,
        "american_odds": -110,
        "book": "dk",
        "home_team": "Seattle Seahawks",
        "away_team": "New England Patriots",
    }
    return pd.DataFrame([{**base, **row} for row in rows])


# -- one wager, not nine -----------------------------------------------------


def test_nine_books_quoting_one_wager_collapse_to_one_bet() -> None:
    """Counting each book separately multiplies one wager by nine, inflates
    every sample size by nearly an order of magnitude, and narrows every
    interval by a factor of three while measuring nothing new."""
    prices = _prices(
        [{"book": f"book{i}", "american_odds": -120 + i} for i in range(9)]
    )

    collapsed = best_price_per_selection(prices)

    assert len(collapsed) == 1


def test_the_price_kept_is_the_best_one_a_card_could_reach() -> None:
    """+150 beats +120 beats -110 beats -200. If the model cannot beat the
    best of nine books it certainly cannot beat the one a card reaches."""
    prices = _prices(
        [
            {"book": "a", "american_odds": -200},
            {"book": "b", "american_odds": 150},
            {"book": "c", "american_odds": -110},
        ]
    )

    collapsed = best_price_per_selection(prices)

    assert collapsed["american_odds"].iloc[0] == 150


def test_different_lines_are_different_bets() -> None:
    """The ladder is not one wager. Over 4.5 and over 8.5 are different bets
    and collapsing them would throw away most of the board."""
    prices = _prices([{"line": 4.5}, {"line": 8.5}])

    assert len(best_price_per_selection(prices)) == 2


def test_the_two_sides_are_different_bets() -> None:
    prices = _prices([{"selection": "over"}, {"selection": "under"}])

    assert len(best_price_per_selection(prices)) == 2


def test_the_same_player_in_two_games_is_two_bets() -> None:
    prices = _prices([{"event_id": "e1"}, {"event_id": "e2"}])

    assert len(best_price_per_selection(prices)) == 2


def test_a_row_with_no_usable_price_is_dropped_rather_than_staked() -> None:
    prices = _prices([{"american_odds": None, "book": "a"}])

    assert best_price_per_selection(prices).empty


# -- a candidate is not a finding --------------------------------------------


def _bets(rows: list[dict]) -> pd.DataFrame:
    base = {
        "event_id": "e1",
        "week": 5,
        "market": "tackles_assists",
        "player": "A Player",
        "outcome": "won",
        "profit": 1.0,
    }
    return pd.DataFrame([{**base, **row} for row in rows])


def test_a_result_carried_by_one_afternoon_shows_up_as_a_top_game_share() -> None:
    bets = _bets(
        [{"event_id": "big", "profit": 50.0}]
        + [{"event_id": f"g{i}", "profit": -1.0} for i in range(20)]
    )

    check = fragility(bets, "tackles_assists")

    assert check.top_game_share > 1.0  # the rest are negative, so it carries it all
    assert check.without_best_game < 0


def test_a_result_that_is_really_one_player_shows_up_in_the_player_count() -> None:
    bets = _bets([{"player": "One Man", "event_id": f"g{i}"} for i in range(30)])

    assert fragility(bets, "tackles_assists").players == 1


def test_halves_that_disagree_are_reported_as_disagreeing() -> None:
    """A hot fortnight looks like an edge until the season is split."""
    bets = _bets(
        [{"week": 2, "event_id": f"a{i}", "profit": 2.0} for i in range(20)]
        + [{"week": 15, "event_id": f"b{i}", "profit": -1.0} for i in range(20)]
    )

    check = fragility(bets, "tackles_assists")

    assert check.first_half > 0 > check.second_half
    assert not check.halves_agree


def test_halves_that_agree_are_reported_as_agreeing() -> None:
    bets = _bets(
        [{"week": 2, "event_id": f"a{i}", "profit": 0.2} for i in range(20)]
        + [{"week": 15, "event_id": f"b{i}", "profit": 0.15} for i in range(20)]
    )

    assert fragility(bets, "tackles_assists").halves_agree


def test_voids_are_excluded_from_the_fragility_arithmetic() -> None:
    """A void is not a zero-return bet; it is not a bet."""
    bets = _bets(
        [{"event_id": f"g{i}", "profit": 1.0} for i in range(10)]
        + [{"event_id": "v", "outcome": "void", "profit": 0.0}]
    )

    assert fragility(bets, "tackles_assists").games == 10


def test_below_the_declared_minimum_the_verdict_is_not_a_number() -> None:
    """However good the number looks."""
    entry = MarketResult(market="x", bets=MINIMUM_BETS - 1, roi=0.40)

    verdict = entry.verdict(corrected_low=0.30, corrected_high=0.50)

    assert "not enough evidence" in verdict
    assert "0.40" not in verdict


def test_an_interval_including_zero_is_no_demonstrated_edge_in_those_words() -> None:
    entry = MarketResult(market="x", bets=1000, roi=0.05)

    assert entry.verdict(corrected_low=-0.02, corrected_high=0.12) == (
        "**no demonstrated edge**"
    )
