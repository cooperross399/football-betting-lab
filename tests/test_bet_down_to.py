"""Every pick carries a "bet down to" price (Cooper, 2026-11-01).

"Lets always include a 'bet down to' number." The card lists each selection's
price AND the worst price at which it would still be a selection, so a line
that moves before Cooper bets can be judged against the card's own bar
rather than guessed at.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from football_betting_lab.config import CARD_EDGE_FLOOR, MAX_DEFAULT_JUICE
from football_betting_lab.forward_evidence import american_to_implied
from football_betting_lab.leagues import NFL
from football_betting_lab.reports.card_pricing import PricingDiagnostics
from football_betting_lab.reports.gameday_card import (
    CardResult,
    bet_down_to,
    render,
    select,
)
from football_betting_lab.selection import selection_key
from football_betting_lab.staging_provider_policy import (
    POLICY_FILENAME,
    RECEIPTS_DIRNAME,
    StagingProviderPolicy,
)

NOW = datetime(2026, 9, 13, 15, 0, tzinfo=timezone.utc)
AHEAD = "2026-09-13T20:25:00Z"
STARTED = "2026-09-13T13:00:00Z"


def _policy(tmp_path: Path, markets: list[str]) -> StagingProviderPolicy:
    (tmp_path / POLICY_FILENAME).write_text(
        json.dumps(
            {
                "allowed_provider_names": ["the_odds_api"],
                "provider_allowlist_entries": {
                    NFL.policy_key(): {
                        "allowlist_status": "allowed",
                        "approved_at": "2026-09-01T12:00:00-04:00",
                        "reviewer_name": "cooperross399",
                        "evidence_receipt_id": "r-1",
                        "required_markets": markets,
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    receipts = tmp_path / RECEIPTS_DIRNAME
    receipts.mkdir(parents=True, exist_ok=True)
    (receipts / "r-1.json").write_text(
        json.dumps(
            {
                "receipt_id": "r-1",
                "policy_key": NFL.policy_key(),
                "reviewer_name": "cooperross399",
                "approved_markets": markets,
            }
        ),
        encoding="utf-8",
    )
    return StagingProviderPolicy.load(manual_dir=tmp_path)


def _prices(**overrides) -> pd.DataFrame:
    row = {
        "market": "moneyline",
        "selection": "home",
        "line": None,
        "player": "",
        "home_team": "Seattle Seahawks",
        "away_team": "New England Patriots",
        "commence_time": AHEAD,
        "american_odds": -110,
        "book": "draftkings",
    }
    row.update(overrides)
    return pd.DataFrame([row])


def _probabilities(prices: pd.DataFrame, probability: float) -> dict:
    row = next(prices.itertuples())
    return {
        selection_key(
            row,
            market=row.market,
            selection=row.selection,
            line=row.line,
            league=NFL,
        ): probability
    }


def _clears(probability: float, odds: int) -> bool:
    return probability - american_to_implied(odds) > CARD_EDGE_FLOOR


@pytest.mark.parametrize(
    "probability", [0.20, 0.33, 0.45, 0.50, 0.555, 0.56, 0.5601, 0.60, 0.62, 0.66, 0.70]
)
def test_the_bet_down_to_price_is_the_worst_price_that_still_clears(
    probability: float,
) -> None:
    odds = bet_down_to(probability)
    assert odds is not None
    if odds == MAX_DEFAULT_JUICE:
        # Floored: the card refuses anything worse whatever the edge.
        assert _clears(probability, odds)
        return
    assert _clears(probability, odds)
    # One cent worse no longer clears. -101 worse is -102; +100 worse is -101.
    worse = odds - 1 if odds > 100 or odds < -100 else -101
    assert not _clears(probability, worse)


def test_the_bet_down_to_price_never_passes_the_juice_bar() -> None:
    assert bet_down_to(0.90) == MAX_DEFAULT_JUICE


def test_no_price_clears_when_the_model_sits_under_the_bar() -> None:
    assert bet_down_to(CARD_EDGE_FLOOR) is None
    assert bet_down_to(0.01) is None


def test_a_selection_carries_its_bet_down_to_and_the_card_prints_it(
    tmp_path: Path,
) -> None:
    prices = _prices(american_odds=-110)
    picks, _ = select(
        prices,
        _probabilities(prices, 0.62),
        NFL,
        policy=_policy(tmp_path, ["moneyline"]),
        now=NOW,
    )
    assert len(picks) == 1
    pick = picks[0]
    assert pick["bet_down_to"] == bet_down_to(0.62)
    # Never better than the price the pick is listed at.
    assert american_to_implied(pick["bet_down_to"]) >= american_to_implied(pick["odds"])

    card = CardResult(
        league=NFL,
        generated_at=NOW.isoformat(),
        slate_date="2026-09-13",
        games=[pick["game"]],
        market_states={"moneyline": "eligible"},
        diagnostics=PricingDiagnostics(),
        selections=picks,
    )
    text = render(card)
    assert "| Bet down to |" in text
    assert f"| {pick['bet_down_to']:+d} |" in text
