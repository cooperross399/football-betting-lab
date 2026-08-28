"""The policy allows nothing until a human says otherwise, and fails closed.

Every one of these is a way the policy could accidentally start permitting
something. A loader that returns a permissive default on an unreadable file is
a loader that stops existing the moment something goes wrong, which is exactly
when it matters.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from football_betting_lab.leagues import NFL, League
from football_betting_lab.staging_provider_policy import (
    POLICY_FILENAME,
    RECEIPTS_DIRNAME,
    StagingProviderPolicy,
    write_starter_policy,
)


NCAAF = League(
    key="ncaaf",
    title="NCAAF",
    provider_sport_key="americanfootball_ncaaf",
    data_adapter="x",
    market_registry="y",
    timezone=NFL.timezone,
    daily_credit_cap=1,
)


def _write(tmp_path: Path, payload: dict, *, receipt: str | None = None) -> Path:
    (tmp_path / POLICY_FILENAME).write_text(json.dumps(payload), encoding="utf-8")
    if receipt:
        receipts = tmp_path / RECEIPTS_DIRNAME
        receipts.mkdir(parents=True, exist_ok=True)
        (receipts / f"{receipt}.md").write_text("signed", encoding="utf-8")
    return tmp_path / POLICY_FILENAME


def _approval(markets: list[str], receipt: str = "r-1") -> dict:
    return {
        "provider_allowlist_entries": {
            NFL.policy_key(): {
                "allowlist_status": "allowed",
                "approved_at": "2026-09-01T12:00:00-04:00",
                "reviewer_name": "cooperross399",
                "evidence_receipt_id": receipt,
                "required_markets": markets,
            }
        }
    }


def test_the_shipped_policy_allowlists_nothing(tmp_path: Path) -> None:
    write_starter_policy(tmp_path / POLICY_FILENAME)

    policy = StagingProviderPolicy.load(manual_dir=tmp_path)

    assert policy.allowed_markets(NFL) == ()
    assert not policy.market_allowed(NFL, "moneyline")


def test_a_missing_policy_file_allows_nothing(tmp_path: Path) -> None:
    policy = StagingProviderPolicy.load(manual_dir=tmp_path)

    assert not policy.market_allowed(NFL, "moneyline")
    assert "No policy file" in policy.refusal_reason(NFL, "moneyline")


def test_an_unreadable_policy_file_allows_nothing(tmp_path: Path) -> None:
    (tmp_path / POLICY_FILENAME).write_text("{not json", encoding="utf-8")

    policy = StagingProviderPolicy.load(manual_dir=tmp_path)

    assert not policy.market_allowed(NFL, "moneyline")
    assert "could not be read" in policy.refusal_reason(NFL, "moneyline")


def test_a_policy_file_that_is_not_an_object_allows_nothing(tmp_path: Path) -> None:
    (tmp_path / POLICY_FILENAME).write_text("[]", encoding="utf-8")

    policy = StagingProviderPolicy.load(manual_dir=tmp_path)

    assert not policy.market_allowed(NFL, "moneyline")


def test_a_complete_approval_allows_exactly_the_markets_it_names(
    tmp_path: Path,
) -> None:
    _write(tmp_path, _approval(["moneyline", "spread"]), receipt="r-1")

    policy = StagingProviderPolicy.load(manual_dir=tmp_path)

    assert policy.market_allowed(NFL, "moneyline")
    assert policy.market_allowed(NFL, "spread")
    assert not policy.market_allowed(NFL, "total_points")
    assert "not named in the reviewed approval" in policy.refusal_reason(
        NFL, "total_points"
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("allowlist_status", "pending"),
        ("reviewer_name", ""),
        ("evidence_receipt_id", ""),
    ],
)
def test_an_incomplete_approval_is_not_an_approval(
    tmp_path: Path, field: str, value: str
) -> None:
    """A status of "allowed" with no reviewer is what a half-finished edit
    looks like, and it must not read as an approval."""
    payload = _approval(["moneyline"])
    payload["provider_allowlist_entries"][NFL.policy_key()][field] = value
    _write(tmp_path, payload, receipt="r-1")

    policy = StagingProviderPolicy.load(manual_dir=tmp_path)

    assert not policy.market_allowed(NFL, "moneyline")
    assert "not a complete approval" in policy.refusal_reason(NFL, "moneyline")


def test_an_approval_naming_a_receipt_that_does_not_exist_allows_nothing(
    tmp_path: Path,
) -> None:
    """An id pointing at nothing is the shape a fabricated approval takes."""
    _write(tmp_path, _approval(["moneyline"], receipt="r-missing"))

    policy = StagingProviderPolicy.load(manual_dir=tmp_path)

    assert not policy.market_allowed(NFL, "moneyline")
    assert "no such file exists" in policy.refusal_reason(NFL, "moneyline")


def test_an_approval_naming_a_market_this_lab_cannot_settle_allows_nothing(
    tmp_path: Path,
) -> None:
    """The policy grants permission. It does not confer the ability to settle
    a bet, so it cannot make an unwired market usable."""
    _write(tmp_path, _approval(["moneyline", "player_wickets"]), receipt="r-1")

    policy = StagingProviderPolicy.load(manual_dir=tmp_path)

    assert not policy.market_allowed(NFL, "player_wickets")
    assert "not a market this lab knows" in policy.refusal_reason(NFL, "player_wickets")


def test_approving_a_market_in_one_league_never_approves_it_in_another(
    tmp_path: Path,
) -> None:
    """The distribution, the roster churn and the books' coverage are all
    different. One receipt, one league."""
    _write(tmp_path, _approval(["moneyline"]), receipt="r-1")

    policy = StagingProviderPolicy.load(manual_dir=tmp_path)

    assert policy.market_allowed(NFL, "moneyline")
    assert not policy.market_allowed(NCAAF, "moneyline")
    assert "Approval in another league never carries across" in (
        policy.refusal_reason(NCAAF, "moneyline")
    )


def test_every_refusal_gives_a_reason_a_card_can_print(tmp_path: Path) -> None:
    """A market excluded with no stated reason is indistinguishable from one
    silently dropped."""
    policy = StagingProviderPolicy.load(manual_dir=tmp_path)

    for market in ("moneyline", "pass_yards", "not_a_market"):
        reason = policy.refusal_reason(NFL, market)
        assert reason and not reason.endswith(" ")


def test_a_market_that_is_allowed_has_no_refusal_reason(tmp_path: Path) -> None:
    """Otherwise a card could print an approval and a refusal for one market."""
    _write(tmp_path, _approval(["moneyline"]), receipt="r-1")

    policy = StagingProviderPolicy.load(manual_dir=tmp_path)

    assert policy.refusal_reason(NFL, "moneyline") == ""


def test_the_repositorys_own_policy_file_still_allowlists_nothing() -> None:
    """The state that ships. If this ever fails, a market was allowlisted
    without a receipt being reviewed, and the card must not run."""
    policy = StagingProviderPolicy.load()

    assert policy.allowed_markets(NFL) == ()
    assert "No market is allowlisted" in policy.summary_line(NFL)
