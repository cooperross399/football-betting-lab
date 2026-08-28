"""What the card says when it has nothing to recommend — which is always, now.

The failure this file guards is a card that goes quiet. A slate with no
selections, a day with no games, and a run that broke are three different
things, and a card that renders them the same way is lying by omission.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from football_betting_lab.leagues import NFL
from football_betting_lab.reports.card_pricing import PricingDiagnostics
from football_betting_lab.reports.gameday_card import (
    ACCUMULATING_NOTE,
    build_card,
    render,
)
from football_betting_lab.staging_provider_policy import StagingProviderPolicy


NOW = datetime(2026, 9, 9, 15, 0, tzinfo=timezone.utc)


def _prices(commence: str = "2026-09-10T00:20:00Z") -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "market": market,
                "home_team": "Seattle Seahawks",
                "away_team": "New England Patriots",
                "commence_time": commence,
            }
            for market in ("moneyline", "spread", "pass_yards")
        ]
    )


def _card(prices=None, diagnostics=None, preseason=None, now=NOW):
    return build_card(
        _prices() if prices is None else prices,
        NFL,
        policy=StagingProviderPolicy.load(),
        diagnostics=diagnostics or PricingDiagnostics(),
        now=now,
        slate_date="2026-09-09",
        preseason_excluded=preseason or [],
    )


def test_the_card_says_it_is_accumulating_evidence_not_recommending() -> None:
    """Not modesty. The accurate description of a lab whose evidence base is
    empty, and it must never soften into something that reads like a tip."""
    text = render(_card())

    assert ACCUMULATING_NOTE in text
    assert "accumulating evidence, not making recommendations" in text


def test_no_market_is_allowlisted_so_there_are_no_selections() -> None:
    card = _card()

    assert card.selections == []
    text = render(card)
    assert "**None.**" in text
    assert "not a pass, not an avoid" in text.lower()


def test_an_excluded_market_is_never_called_a_pass_or_a_no_value_call() -> None:
    text = render(_card()).lower()

    assert "no-value call" in text  # ...only ever as the thing it is not.
    for phrase in ("no value found", "avoid this market", "we pass on"):
        assert phrase not in text


def test_every_priced_market_is_listed_with_a_reason() -> None:
    card = _card()

    assert set(card.market_states) == {"moneyline", "spread", "pass_yards"}
    for reason in card.market_states.values():
        assert reason and reason != "eligible"


def test_a_day_with_no_games_is_an_absence_and_says_so() -> None:
    """Different from a run that failed, and different from a slate with no
    qualifying bet."""
    card = _card(prices=pd.DataFrame(columns=["market", "home_team", "away_team"]))

    text = render(card)

    assert card.decision == "no-slate"
    assert "absence, not a fault" in text


def test_a_slate_with_games_and_no_selections_is_reported_as_that() -> None:
    card = _card()

    assert card.decision == "no-selections"
    assert card.games


def test_preseason_exclusions_are_counted_and_named() -> None:
    """Books post exhibition lines and the provider does not flag them. An
    opinion frozen on one rots in the ledger as unsettleable noise."""
    card = _card(
        prices=pd.DataFrame(columns=["market", "home_team", "away_team"]),
        preseason=["2026-08-22 KC @ SEA (not in the regular-season schedule)"],
    )

    text = render(card)

    assert "excluded as preseason" in text
    assert "2026-08-22 KC @ SEA" in text


def test_a_started_game_is_quarantined_with_its_reason() -> None:
    card = _card(prices=_prices(commence="2026-09-09T12:00:00Z"))

    text = render(card)

    assert card.quarantined
    assert "Already started — no longer plays" in text
    assert "no longer available at the price shown" in text


def test_the_accounting_identity_is_printed_every_run() -> None:
    diagnostics = PricingDiagnostics(priced=10, no_opinion=3, opinions=7)

    text = render(_card(diagnostics=diagnostics))

    assert "priced 10 = no_opinion 3" in text
    assert "reconciles" in text


def test_an_identity_that_does_not_reconcile_shouts() -> None:
    """A row fell out for a reason nobody counted. Silent attrition is how a
    card ends up recommending from a sixth of a slate."""
    diagnostics = PricingDiagnostics(priced=10, no_opinion=1, opinions=2)

    text = render(_card(diagnostics=diagnostics))

    assert "DOES NOT RECONCILE" in text
    assert "does not reconcile" in text.lower()


def test_the_card_tells_the_reader_why_props_cannot_be_selected() -> None:
    text = render(_card())

    assert "cannot produce a selection" in text
    assert "no available feed publishes them" in text


def test_the_card_states_the_forward_ledger_position() -> None:
    card = _card()
    card.frozen_rows = 1903
    card.ledger_rows = 0

    text = render(card)

    assert "1,903 opinion(s) frozen" in text
    assert "cannot be back-dated" in text
