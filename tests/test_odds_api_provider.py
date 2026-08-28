"""The adapter's guards: the host, the credential, and the quota.

A run that starts with less than it could spend gets partway through the slate
and stops, leaving a snapshot holding the games it happened to reach — a
biased subset frozen into the ledger as though it were the day. Forward
evidence cannot be re-made, so refusing is the safe direction.
"""

from __future__ import annotations

import pytest

from football_betting_lab.leagues import NFL
from football_betting_lab.providers.odds_api import (
    ALLOWED_API_HOSTS,
    BULK_SAFE_MARKETS,
    CreditCapReached,
    MissingCredentialError,
    OddsApiProvider,
    ProviderError,
    Spend,
    _guard,
    sufficient_quota,
)


# -- the quota guard ---------------------------------------------------------


def test_a_run_with_less_than_its_cap_is_refused() -> None:
    ok, note = sufficient_quota({"x-requests-remaining": "500"}, 1400)

    assert not ok
    assert "Nothing was requested" in note
    assert "worse than no card" in note


def test_a_run_with_enough_is_allowed() -> None:
    ok, _ = sufficient_quota({"x-requests-remaining": "5000"}, 1400)

    assert ok


def test_exactly_the_cap_is_enough() -> None:
    """The boundary asserted from both sides so a later `<=` cannot slip in."""
    assert sufficient_quota({"x-requests-remaining": "1400"}, 1400)[0]
    assert not sufficient_quota({"x-requests-remaining": "1399"}, 1400)[0]


def test_an_unreadable_quota_header_does_not_block_the_run() -> None:
    """The guard catches a known shortfall. Making an unreadable response
    fatal would take the card down for a reason that is not about credits, and
    the per-request cap still cannot be breached."""
    for headers in ({}, {"x-requests-remaining": ""}, {"x-requests-remaining": "lots"}):
        ok, note = sufficient_quota(headers, 1400)
        assert ok, headers
        assert "did not report" in note


# -- the host and the credential ---------------------------------------------


def test_the_credential_is_never_sent_to_an_arbitrary_host() -> None:
    with pytest.raises(ProviderError, match="Refusing to send the credential"):
        OddsApiProvider(
            NFL, environment={"FOOTBALL_ODDS_API_BASE_URL": "https://evil.example.com"}
        )


def test_the_provider_hosts_are_allowed() -> None:
    for host in ALLOWED_API_HOSTS:
        OddsApiProvider(NFL, environment={"FOOTBALL_ODDS_API_BASE_URL": f"https://{host}"})


def test_a_localhost_mock_is_allowed_so_tests_can_run_offline() -> None:
    OddsApiProvider(NFL, environment={"FOOTBALL_ODDS_API_BASE_URL": "http://localhost:8080"})


def test_a_live_fetch_without_a_credential_is_refused_by_name() -> None:
    provider = OddsApiProvider(NFL, environment={})

    with pytest.raises(MissingCredentialError, match="FOOTBALL_ODDS_API_KEY"):
        provider.list_events()


def test_the_error_tells_the_operator_never_to_pass_the_key_as_an_argument() -> None:
    """A process list is world-readable and CI logs echo commands."""
    provider = OddsApiProvider(NFL, environment={})

    with pytest.raises(MissingCredentialError) as excinfo:
        provider.list_events()

    assert "never commit it" in str(excinfo.value)
    assert "command argument" in str(excinfo.value)


# -- the bulk endpoint -------------------------------------------------------


def test_the_bulk_endpoint_refuses_anything_but_the_featured_three() -> None:
    """The provider answers a bulk request containing a ladder or a period
    market with HTTP 422 for the whole request, which took down every team
    fetch in the NHL lab and looked like an off-season for two rounds of
    debugging."""
    provider = OddsApiProvider(NFL, environment={"FOOTBALL_ODDS_API_KEY": "x"})

    with pytest.raises(ProviderError, match="cannot be asked of the bulk endpoint"):
        provider.fetch_bulk(("h2h", "alternate_spreads"), spend=Spend(), credit_cap=100)


def test_the_featured_three_are_exactly_what_bulk_serves() -> None:
    assert BULK_SAFE_MARKETS == frozenset({"h2h", "spreads", "totals"})


# -- the cap -----------------------------------------------------------------


def test_the_cap_is_checked_before_the_request_and_leaves_the_spend_untouched() -> None:
    spend = Spend(credits_spent=900)

    with pytest.raises(CreditCapReached):
        _guard(spend, 1000, 200, "one more event")

    assert spend.credits_spent == 900


def test_a_zero_cap_means_unlimited_and_is_only_reachable_deliberately() -> None:
    """Every entry point refuses `--live` without a positive cap, so this path
    exists for tests and for nothing else."""
    _guard(Spend(credits_spent=10**9), 0, 10**9, "anything")
