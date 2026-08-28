"""First-half markets are priced by the half model, or by nothing — and
"nothing" is `no_opinion`, never `unparseable`.

A market with no model and a row this lab cannot parse are different facts.
Filing the first as the second reads as an adapter fault and hides a modelling
gap behind it, which this repository has already done once.
"""

from __future__ import annotations

import pandas as pd
import pytest

from football_betting_lab.leagues import NFL
from football_betting_lab.models.scoring import GameDistribution
from football_betting_lab.reports.card_pricing import (
    HALF_MARKETS,
    MODELLED_TEAM_MARKETS,
    PlayerBook,
    price_slate,
)


def _prices(market: str, selection: str, line) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "market": market,
                "selection": selection,
                "line": line,
                "player": "",
                "home_team": "Seattle Seahawks",
                "away_team": "New England Patriots",
                "commence_time": "2026-09-10T00:20:00Z",
            }
        ]
    )


def _book() -> PlayerBook:
    empty = pd.DataFrame(
        columns=[
            "player_id", "player_name", "season", "week",
            "pass_completions", "pass_yards", "pass_tds",
            "rush_attempts", "rush_yards", "rush_tds",
            "receptions", "reception_yards", "reception_tds",
        ]
    )
    return PlayerBook(empty, {}, before="202601", draws=10)


def _half() -> GameDistribution:
    return GameDistribution(
        home={10: 0.5, 14: 0.5}, away={7: 0.5, 10: 0.5}, resolves_ties=False
    )


def test_a_half_market_with_no_model_is_no_opinion_not_unparseable() -> None:
    probabilities, diagnostics = price_slate(
        _prices("total_points_h1", "over", 20.5),
        NFL,
        distributions={("Seattle Seahawks", "New England Patriots"): _half()},
        book=_book(),
        player_ids={},
    )

    assert not probabilities
    assert diagnostics.no_opinion == 1
    assert diagnostics.unparseable == 0
    assert any("first-half model" in reason for reason in diagnostics.reasons)


def test_a_half_market_is_priced_when_the_model_is_supplied() -> None:
    key = ("Seattle Seahawks", "New England Patriots")
    probabilities, diagnostics = price_slate(
        _prices("total_points_h1", "over", 20.5),
        NFL,
        distributions={key: _half()},
        book=_book(),
        player_ids={},
        half_distributions={key: _half()},
    )

    assert diagnostics.opinions == 1
    assert 0.0 <= next(iter(probabilities.values())) <= 1.0


def test_the_half_markets_map_onto_their_full_game_equivalents() -> None:
    for half_market, full_market in HALF_MARKETS.items():
        assert half_market.endswith("_h1")
        assert full_market in MODELLED_TEAM_MARKETS


def test_a_half_market_is_not_priced_by_the_full_game_model() -> None:
    """The full-game distribution would price a first-half total as though it
    were a whole game, which is wrong by about a factor of two."""
    for market in HALF_MARKETS:
        assert market not in MODELLED_TEAM_MARKETS


def test_the_identity_still_reconciles_when_a_half_market_is_skipped() -> None:
    _, diagnostics = price_slate(
        _prices("spread_h1", "home", -3.5),
        NFL,
        distributions={("Seattle Seahawks", "New England Patriots"): _half()},
        book=_book(),
        player_ids={},
    )

    assert diagnostics.reconciles()
