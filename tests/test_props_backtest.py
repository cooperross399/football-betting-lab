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


# -- two snapshots of one event are not one wager ----------------------------


def _two_snapshots() -> pd.DataFrame:
    """The same wager at card time and at the close, with a better close."""
    return _prices(
        [
            {"snapshot": "20250907T170000Z", "american_odds": -110, "book": "dk"},
            {"snapshot": "20250907T175500Z", "american_odds": 150, "book": "dk"},
        ]
    )


def test_the_two_snapshots_of_one_event_are_labelled_card_and_close() -> None:
    from football_betting_lab.reports.props_backtest import (
        CARD_TIME,
        CLOSING,
        label_snapshots,
    )

    labelled = label_snapshots(_two_snapshots())

    assert list(labelled["phase"]) == [CARD_TIME, CLOSING]


def test_an_event_with_one_snapshot_is_all_card_time() -> None:
    """A single purchase was a card-time purchase, and calling half of it the
    close would invent a closing price."""
    from football_betting_lab.reports.props_backtest import CARD_TIME, label_snapshots

    one = _prices([{"snapshot": "20250907T170000Z"}])

    assert list(label_snapshots(one)["phase"]) == [CARD_TIME]


def test_the_best_price_is_never_taken_across_two_snapshots() -> None:
    """The better of a card-time price and a closing price is not a price
    anyone could have taken. It is the best of two moments, and collapsing
    them would quietly inflate every measured edge."""
    from football_betting_lab.reports.props_backtest import label_snapshots

    collapsed = best_price_per_selection(label_snapshots(_two_snapshots()))

    assert len(collapsed) == 2
    assert set(collapsed["american_odds"]) == {-110, 150}


def test_nine_books_still_collapse_within_one_snapshot() -> None:
    """The snapshot joins the key; it does not replace it."""
    from football_betting_lab.reports.props_backtest import label_snapshots

    prices = _prices(
        [
            {"snapshot": "20250907T170000Z", "book": f"b{i}", "american_odds": -120 + i}
            for i in range(9)
        ]
    )

    assert len(best_price_per_selection(label_snapshots(prices))) == 1


def test_three_snapshots_label_earliest_card_latest_close_and_the_rest_mid() -> None:
    """The first version labelled every non-earliest snapshot `close`, which
    was right for two snapshots and silently wrong for three: a T-60 and a T-5
    price would have landed in the same bucket and the best-price collapse
    would have chosen between two different moments."""
    from football_betting_lab.reports.props_backtest import (
        CARD_TIME,
        CLOSING,
        MID,
        label_snapshots,
    )

    prices = _prices(
        [
            {"snapshot": "20250907T120000Z"},
            {"snapshot": "20250907T170000Z"},
            {"snapshot": "20250907T175500Z"},
        ]
    )

    assert list(label_snapshots(prices)["phase"]) == [CARD_TIME, MID, CLOSING]


def test_a_single_snapshot_is_card_not_close() -> None:
    """Earliest and latest are the same row, and one purchase was a card-time
    purchase — calling it the close would invent a closing price."""
    from football_betting_lab.reports.props_backtest import CARD_TIME, label_snapshots

    one = _prices([{"snapshot": "20250907T170000Z"}])

    assert list(label_snapshots(one)["phase"]) == [CARD_TIME]
