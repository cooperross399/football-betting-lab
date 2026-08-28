"""The two sides of a market are opposites, and a missing column is not a
finding.

Both rules here are regression tests for defects this backtest shipped, each
reproduced before it was fixed.
"""

from __future__ import annotations

import pandas as pd
import pytest

from football_betting_lab.reports.closing_line_backtest import (
    MINIMUM_BETS,
    MissingPriceColumns,
    _price_game,
    require_price_columns,
    run,
)
from football_betting_lab.models.scoring import empirical_pmf, fit_ratings


COLUMNS = [
    "game_id", "season", "week", "game_date", "home_team", "away_team",
    "home_score", "away_score", "spread_line", "home_spread_odds",
    "away_spread_odds", "total_line", "over_odds", "under_odds",
    "home_moneyline", "away_moneyline",
]


def _game(**overrides) -> pd.Series:
    row = {
        "game_id": "g1",
        "season": 2025,
        "week": 1,
        "game_date": "2025-09-07",
        "home_team": "SEA",
        "away_team": "NE",
        "home_score": 24,
        "away_score": 20,
        "spread_line": 3.0,
        "home_spread_odds": -110,
        "away_spread_odds": -110,
        "total_line": 44.0,
        "over_odds": -110,
        "under_odds": -110,
        "home_moneyline": -150,
        "away_moneyline": 130,
    }
    row.update(overrides)
    return pd.DataFrame([row], columns=COLUMNS)


def _priced(game_frame: pd.DataFrame, min_edge: float = -1.0) -> list[dict]:
    """Price one game with the edge bar removed, so every side appears."""
    history = pd.concat(
        [
            _game(home_score=score, away_score=score - 3, game_date="2024-09-01")
            for score in (17, 20, 24, 27, 31)
        ],
        ignore_index=True,
    )
    pmf = empirical_pmf(
        list(history["home_score"].astype(int)) + list(history["away_score"].astype(int))
    )
    ratings = fit_ratings(history, before="9999-99-99")
    return _price_game(
        next(game_frame.itertuples()), ratings, pmf, min_edge=min_edge, max_juice=-1000
    )


# -- the two sides are opposites --------------------------------------------


def test_both_sides_of_a_spread_can_never_win_the_same_game() -> None:
    """The defect, reproduced.

    Deriving both sides from one `spread_line` and forgetting to negate for
    the away side produced a market where both could win — 147 of 402 games
    where both were bet — and a +21.6% "edge" over 1,695 bets whose interval
    excluded zero even after the family correction.
    """
    for margin in (-14, -7, -3, 0, 3, 7, 14):
        priced = _priced(_game(home_score=20 + margin, away_score=20))
        spreads = [bet for bet in priced if bet["market"] == "spread"]

        assert len(spreads) == 2
        outcomes = sorted(bet["outcome"] for bet in spreads)
        assert outcomes in (["lost", "won"], ["push", "push"]), (margin, outcomes)


def test_the_two_spread_sides_take_opposite_handicaps() -> None:
    priced = _priced(_game(spread_line=3.0))
    spreads = {bet["selection"]: bet["line"] for bet in priced if bet["market"] == "spread"}

    assert spreads["home"] == pytest.approx(-spreads["away"])


def test_the_two_spread_probabilities_sum_to_one_net_of_the_push() -> None:
    """If they do not, the two sides are not describing the same bet."""
    priced = _priced(_game(spread_line=3.5))
    spreads = {
        bet["selection"]: bet["model_probability"]
        for bet in priced
        if bet["market"] == "spread"
    }

    assert spreads["home"] + spreads["away"] == pytest.approx(1.0, abs=1e-6)


def test_both_sides_of_a_total_can_never_win_the_same_game() -> None:
    for combined in (30, 43, 44, 45, 60):
        priced = _priced(_game(home_score=combined, away_score=0, total_line=44.0))
        totals = [bet for bet in priced if bet["market"] == "total_points"]

        outcomes = sorted(bet["outcome"] for bet in totals)
        assert outcomes in (["lost", "won"], ["push", "push"]), (combined, outcomes)


def test_home_covers_when_the_margin_beats_the_line() -> None:
    """`spread_line > 0` means the home side is favoured by that many —
    verified against the data, not read off the documentation."""
    priced = _priced(_game(spread_line=3.0, home_score=24, away_score=20))
    home = next(b for b in priced if b["market"] == "spread" and b["selection"] == "home")

    assert home["outcome"] == "won"

    priced = _priced(_game(spread_line=3.0, home_score=22, away_score=20))
    home = next(b for b in priced if b["market"] == "spread" and b["selection"] == "home")

    assert home["outcome"] == "lost"


def test_a_margin_exactly_on_a_whole_line_pushes_both_sides() -> None:
    priced = _priced(_game(spread_line=4.0, home_score=24, away_score=20))
    spreads = [bet for bet in priced if bet["market"] == "spread"]

    assert all(bet["outcome"] == "push" for bet in spreads)


# -- a missing column is not a finding ---------------------------------------


def test_a_missing_price_column_is_an_error_not_a_market_with_no_bets() -> None:
    """The first run reported zero bets on the spread and the total. That read
    as "the model never disagrees with the close by enough", which is a
    finding. It was not: the columns had never been built, and a
    `getattr(..., None)` default turned a missing column into a quietly
    skipped market — an absence dressed as a measurement."""
    thin = _game().drop(columns=["home_spread_odds", "over_odds"])

    with pytest.raises(MissingPriceColumns) as excinfo:
        run(thin, seasons=(2025,))

    assert "home_spread_odds" in str(excinfo.value)
    assert "over_odds" in str(excinfo.value)


def test_a_complete_table_passes_the_column_check() -> None:
    require_price_columns(_game())


def test_the_minimum_sample_is_declared_in_advance() -> None:
    """Below it the verdict is "not enough evidence" and not a number,
    however good the number looks."""
    assert MINIMUM_BETS == 200
