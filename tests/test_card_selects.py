"""The path that runs the day a receipt is signed, and had never run.

`build_card` recorded market states, ran the kickoff guard over the slate, and
returned an empty `selections` list that nothing ever filled. With nothing
allowlisted that is indistinguishable from "no market qualified" — so **the
first card after a signed receipt would have produced nothing and said so
confidently.**

Every test here allowlists a market in a temporary policy so the path is
exercised before it matters.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from football_betting_lab.config import MAX_DEFAULT_JUICE, MAX_DEFAULT_PRICE, MIN_EDGE
from football_betting_lab.gates import (
    Availability,
    DOUBTFUL,
    EXCLUDED,
    NO_REPORT,
    QUESTIONABLE,
    UNDESIGNATED,
    UNKNOWN,
)
from football_betting_lab.leagues import NFL
from football_betting_lab.reports.card_pricing import PricingDiagnostics
from football_betting_lab.reports.gameday_card import build_card, render, select
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
    (receipts / "r-1.md").write_text("signed", encoding="utf-8")
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


def test_an_approved_market_with_a_real_edge_produces_a_selection(
    tmp_path: Path,
) -> None:
    prices = _prices()
    picks, _ = select(
        prices,
        _probabilities(prices, 0.75),
        NFL,
        policy=_policy(tmp_path, ["moneyline"]),
        now=NOW,
    )

    assert len(picks) == 1
    assert picks[0]["market"] == "moneyline"
    assert picks[0]["edge"] > MIN_EDGE


def test_an_unapproved_market_produces_nothing_however_large_the_edge(
    tmp_path: Path,
) -> None:
    prices = _prices()
    picks, _ = select(
        prices,
        _probabilities(prices, 0.99),
        NFL,
        policy=_policy(tmp_path, ["spread"]),
        now=NOW,
    )

    assert picks == []


def test_an_edge_below_the_threshold_produces_nothing(tmp_path: Path) -> None:
    prices = _prices()
    picks, _ = select(
        prices, _probabilities(prices, 0.53), NFL,
        policy=_policy(tmp_path, ["moneyline"]), now=NOW,
    )

    assert picks == []


def test_a_market_the_model_has_no_opinion_on_produces_nothing(
    tmp_path: Path,
) -> None:
    """A missing key is *no opinion*, which is different from a probability of
    zero, and the card must treat it as different."""
    picks, _ = select(
        _prices(), {}, NFL, policy=_policy(tmp_path, ["moneyline"]), now=NOW
    )

    assert picks == []


@pytest.mark.parametrize("odds", [MAX_DEFAULT_JUICE - 1, MAX_DEFAULT_PRICE + 1])
def test_a_price_outside_the_bars_produces_nothing(
    tmp_path: Path, odds: int
) -> None:
    """Cooper does not lay heavy juice, and the model is not trusted on
    longshots — independent tails overstate rare counts and the market's
    favourite-longshot bias prices them short on top."""
    prices = _prices(american_odds=odds)
    picks, _ = select(
        prices, _probabilities(prices, 0.99), NFL,
        policy=_policy(tmp_path, ["moneyline"]), now=NOW,
    )

    assert picks == []


def test_a_started_game_is_quarantined_rather_than_selected(
    tmp_path: Path,
) -> None:
    prices = _prices(commence_time=STARTED)
    picks, quarantined = select(
        prices, _probabilities(prices, 0.75), NFL,
        policy=_policy(tmp_path, ["moneyline"]), now=NOW,
    )

    assert picks == []
    assert len(quarantined) == 1
    assert "moneyline" in quarantined[0][0]


def _availability(state: str = UNDESIGNATED, *, key: str = "a back") -> dict:
    """The map `gates.assess_slate` returns, keyed as `select()` looks up."""
    return {
        key: Availability(
            player_id="00-0000001",
            state=state,
            reason="",
            undesignated_allowed=True,
        )
    }


def _prop_prices(player: str = "A Back") -> pd.DataFrame:
    return _prices(
        market="rush_yards", selection="over", line=40.5, player=player
    )


def test_a_player_prop_cannot_select_without_the_verdict(tmp_path: Path) -> None:
    """Nothing reaches `confirmed`, so a prop selects only once a recorded
    verdict permits an undesignated player.

    **The verdict alone is no longer enough**, and the middle case is the
    whole change. `select()` used to decide every player prop on this one
    boolean, and `gates.assess_availability` had no caller anywhere in `src/`
    or `scripts/` — so the day the verdict shipped, a player listed Out and a
    player on a team that filed no report would both have selected on it.
    """
    prices = _prop_prices()
    policy = _policy(tmp_path, ["rush_yards"])
    probabilities = _probabilities(prices, 0.75)

    blocked, _ = select(prices, probabilities, NFL, policy=policy, now=NOW)
    no_map, _ = select(
        prices, probabilities, NFL, policy=policy, now=NOW,
        undesignated_allowed=True,
    )
    allowed, _ = select(
        prices, probabilities, NFL, policy=policy, now=NOW,
        undesignated_allowed=True, availability=_availability(),
    )

    assert blocked == []
    assert no_map == [], (
        "a shipped verdict with no availability map must select nothing: "
        "a card that cannot assess a player has not cleared him"
    )
    assert len(allowed) == 1


@pytest.mark.parametrize(
    "state", [EXCLUDED, DOUBTFUL, QUESTIONABLE, NO_REPORT, UNKNOWN]
)
def test_the_verdict_opens_one_state_and_not_the_other_five(
    tmp_path: Path, state: str
) -> None:
    """The defect stated as a test. `undesignated_allowed` names exactly one
    state; every other one stays shut with the verdict in force — including
    `UNKNOWN`, which is where an unreadable injury feed now lands instead of
    in the selectable one."""
    prices = _prop_prices()
    policy = _policy(tmp_path, ["rush_yards"])

    picks, _ = select(
        prices, _probabilities(prices, 0.75), NFL, policy=policy, now=NOW,
        undesignated_allowed=True, availability=_availability(state),
    )

    assert picks == []


def test_a_player_the_map_does_not_hold_cannot_select(tmp_path: Path) -> None:
    """A player who did not resolve, or whose row arrived after the map was
    built, is a player this lab could not assess. Absence from the map is not
    absence of a designation."""
    prices = _prop_prices()
    policy = _policy(tmp_path, ["rush_yards"])

    picks, _ = select(
        prices, _probabilities(prices, 0.75), NFL, policy=policy, now=NOW,
        undesignated_allowed=True,
        availability=_availability(key="somebody else"),
    )

    assert picks == []


def test_the_map_is_read_with_the_key_the_rest_of_the_lab_builds(
    tmp_path: Path,
) -> None:
    """Join-vocabulary member six, on the availability map this time.

    The provider ships names with stray whitespace. `player_key` is
    `clean_text(...).casefold()`, which is what `run_gameday_card` stores
    under and what `card_pricing` and `selection_key` read back. A lookup
    spelled `str(...).casefold()` here would miss the entry and quarantine a
    player who was assessed perfectly well — failing closed, and silently.
    """
    prices = _prop_prices(player="  A Back  ")
    policy = _policy(tmp_path, ["rush_yards"])

    picks, _ = select(
        prices, _probabilities(prices, 0.75), NFL, policy=policy, now=NOW,
        undesignated_allowed=True, availability=_availability(),
    )

    assert len(picks) == 1
    assert picks[0]["player"] == "A Back"


def test_a_team_market_never_consults_the_availability_map(
    tmp_path: Path,
) -> None:
    """The gate covers player props. A moneyline has no player to assess, and
    gating it on an empty map would quarantine the whole board the first time
    the injury feed was late."""
    prices = _prices()

    picks, _ = select(
        prices, _probabilities(prices, 0.75), NFL,
        policy=_policy(tmp_path, ["moneyline"]), now=NOW, availability={},
    )

    assert len(picks) == 1


def test_the_best_price_is_taken_after_every_bar_not_before(
    tmp_path: Path,
) -> None:
    """Otherwise a bar could be cleared by a price the card would not use —
    a longshot quote clearing the edge bar for a wager the card then takes at
    a shorter number."""
    rows = pd.concat([_prices(american_odds=-110, book="a"),
                      _prices(american_odds=120, book="b")], ignore_index=True)
    probabilities = _probabilities(rows, 0.75)

    picks, _ = select(rows, probabilities, NFL,
                      policy=_policy(tmp_path, ["moneyline"]), now=NOW)

    assert len(picks) == 1
    assert picks[0]["odds"] == 120
    assert picks[0]["book"] == "b"


def test_the_card_stops_saying_nothing_is_allowlisted_once_something_is(
    tmp_path: Path,
) -> None:
    """The sentence would have become a lie the moment a receipt was signed."""
    prices = _prices()
    card = build_card(
        prices, NFL, policy=_policy(tmp_path, ["moneyline"]),
        diagnostics=PricingDiagnostics(), now=NOW, slate_date="2026-09-13",
        preseason_excluded=[], probabilities=_probabilities(prices, 0.75),
    )

    text = render(card)

    assert "No market is allowlisted" not in text
    assert "1 market(s) have a reviewed approval" in text
    assert card.decision == "selections"


def test_an_approved_market_with_no_qualifying_bet_says_which_kind_of_none(
    tmp_path: Path,
) -> None:
    """"Nothing cleared" and "nothing was permitted" are different facts, and
    a card that renders them identically misrepresents itself."""
    prices = _prices()
    card = build_card(
        prices, NFL, policy=_policy(tmp_path, ["moneyline"]),
        diagnostics=PricingDiagnostics(), now=NOW, slate_date="2026-09-13",
        preseason_excluded=[], probabilities=_probabilities(prices, 0.51),
    )

    text = render(card)

    assert "nothing cleared every bar today" in text
    assert "genuine model judgement" in text
    assert card.decision == "no-selections"


def test_a_card_that_selected_a_prop_does_not_say_props_cannot_select(
    tmp_path: Path,
) -> None:
    """The card contradicting itself, in the one place a reader looks.

    `render` called `selection_blocked_note()` **unconditionally**, outside
    the if/elif/else that chooses what the Selections section says. Harmless
    while no player prop could select; wire the gate, ship the verdict, and
    the card prints "player props are priced and tracked and **cannot produce
    a selection**" directly beneath a table containing one.
    """
    prices = _prop_prices()
    card = build_card(
        prices, NFL, policy=_policy(tmp_path, ["rush_yards"]),
        diagnostics=PricingDiagnostics(), now=NOW, slate_date="2026-09-13",
        preseason_excluded=[], probabilities=_probabilities(prices, 0.75),
        undesignated_allowed=True, availability=_availability(),
    )

    text = render(card)

    assert len(card.selections) == 1
    assert "cannot produce a selection" not in text
    assert "evidence of availability and not confirmation" in text
    # The replacement must still name what was NOT cleared, or it is a
    # softer sentence rather than an honest one.
    assert "listed Out" in text


def test_a_card_with_no_prop_selection_still_says_why_props_are_blocked(
    tmp_path: Path,
) -> None:
    """The other side of the same branch. A team-market selection must not
    silence the sentence that explains the availability gate — that would
    make the note disappear on exactly the cards that still need it, which is
    every card today."""
    prices = _prices()
    card = build_card(
        prices, NFL, policy=_policy(tmp_path, ["moneyline"]),
        diagnostics=PricingDiagnostics(), now=NOW, slate_date="2026-09-13",
        preseason_excluded=[], probabilities=_probabilities(prices, 0.75),
    )

    text = render(card)

    assert len(card.selections) == 1
    assert "cannot produce a selection" in text
    assert "evidence of availability and not confirmation" not in text


def test_the_card_still_selects_nothing_under_the_shipped_policy() -> None:
    """The state that ships. If this fails, a market was allowlisted without a
    receipt being reviewed."""
    prices = _prices()
    picks, _ = select(
        prices, _probabilities(prices, 0.99), NFL,
        policy=StagingProviderPolicy.load(), now=NOW,
    )

    assert picks == []
