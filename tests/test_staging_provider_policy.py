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

# A top-level module, the way pytest's prepend import mode puts `tests/` on
# the path. `signed_manual` mints a real receipt through the real minting
# path, which is what "a complete approval" now means.
from test_github_approval import signed_manual


NCAAF = League(
    key="ncaaf",
    title="NCAAF",
    provider_sport_key="americanfootball_ncaaf",
    data_adapter="x",
    market_registry="y",
    timezone=NFL.timezone,
    daily_credit_cap=1,
)


def _signed(tmp_path: Path, markets: list[str]) -> tuple[Path, str]:
    """A manual directory whose entry is backed by a genuine receipt.

    There is no shortcut any more, and that is the change this fixture
    records: `market_allowed()` used to stop at "a file with that name
    exists", so a file reading `signed` was a signature. It now opens the
    receipt and checks the reviewer, the digest and the evidence checksums,
    which means a fixture that wants a yes has to mint a real one.

    Returns the manual directory and the receipt id the entry names.
    """
    manual = signed_manual(tmp_path, tuple(markets))
    payload = json.loads((manual / POLICY_FILENAME).read_text(encoding="utf-8"))
    entry = payload["provider_allowlist_entries"][NFL.policy_key()]
    return manual, str(entry["evidence_receipt_id"])


def _write(
    tmp_path: Path,
    payload: dict,
    *,
    receipt: str | None = None,
    manual: Path | None = None,
) -> Path:
    directory = manual or tmp_path
    directory.mkdir(parents=True, exist_ok=True)
    (directory / POLICY_FILENAME).write_text(json.dumps(payload), encoding="utf-8")
    if receipt:
        receipts = directory / RECEIPTS_DIRNAME
        receipts.mkdir(parents=True, exist_ok=True)
        target = receipts / f"{receipt}.md"
        if not target.exists():
            target.write_text("signed", encoding="utf-8")
    return directory / POLICY_FILENAME


def _approval(
    markets: list[str], receipt: str = "r-1", reviewer: str = "cooperross399"
) -> dict:
    return {
        "provider_allowlist_entries": {
            NFL.policy_key(): {
                "allowlist_status": "allowed",
                "approved_at": "2026-09-01T12:00:00-04:00",
                "reviewer_name": reviewer,
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
    manual, _ = _signed(tmp_path, ["moneyline", "spread"])

    policy = StagingProviderPolicy.load(manual_dir=manual)

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
    manual, receipt = _signed(tmp_path, ["moneyline"])
    payload = json.loads((manual / POLICY_FILENAME).read_text(encoding="utf-8"))
    payload["provider_allowlist_entries"][NFL.policy_key()][field] = value
    _write(tmp_path, payload, manual=manual)

    policy = StagingProviderPolicy.load(manual_dir=manual)

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
    manual, receipt = _signed(tmp_path, ["moneyline"])
    _write(
        tmp_path,
        _approval(["moneyline", "player_wickets"], receipt=receipt),
        manual=manual,
    )

    policy = StagingProviderPolicy.load(manual_dir=manual)

    assert not policy.market_allowed(NFL, "player_wickets")
    assert "not a market this lab knows" in policy.refusal_reason(NFL, "player_wickets")


def test_approving_a_market_in_one_league_never_approves_it_in_another(
    tmp_path: Path,
) -> None:
    """The distribution, the roster churn and the books' coverage are all
    different. One receipt, one league."""
    manual, _ = _signed(tmp_path, ["moneyline"])

    policy = StagingProviderPolicy.load(manual_dir=manual)

    assert policy.market_allowed(NFL, "moneyline")
    assert not policy.market_allowed(NCAAF, "moneyline")
    reason = policy.refusal_reason(NCAAF, "moneyline")
    assert "none carries across" in reason
    # ...and it names the entry that does exist, because "nothing is approved
    # anywhere" and "approved next door" are different situations and only one
    # of them is a question for Cooper.
    assert NFL.policy_key() in reason


def test_every_refusal_gives_a_reason_a_card_can_print(tmp_path: Path) -> None:
    """A market excluded with no stated reason is indistinguishable from one
    silently dropped."""
    policy = StagingProviderPolicy.load(manual_dir=tmp_path)

    for market in ("moneyline", "pass_yards", "not_a_market"):
        reason = policy.refusal_reason(NFL, market)
        assert reason and not reason.endswith(" ")


def test_a_market_that_is_allowed_has_no_refusal_reason(tmp_path: Path) -> None:
    """Otherwise a card could print an approval and a refusal for one market."""
    manual, _ = _signed(tmp_path, ["moneyline"])

    policy = StagingProviderPolicy.load(manual_dir=manual)

    assert policy.refusal_reason(NFL, "moneyline") == ""


def test_the_repositorys_own_policy_file_still_allowlists_nothing() -> None:
    """The state that ships. If this ever fails, a market was allowlisted
    without a receipt being reviewed, and the card must not run."""
    policy = StagingProviderPolicy.load()

    assert policy.allowed_markets(NFL) == ()
    assert "No market is allowlisted" in policy.summary_line(NFL)


def test_a_policy_with_no_entries_at_all_says_so_rather_than_blaming_a_league(
    tmp_path: Path,
) -> None:
    """The state that ships. Telling a reader their approval "does not carry
    across" when there is no approval anywhere points at the wrong problem."""
    write_starter_policy(tmp_path / POLICY_FILENAME)

    reason = StagingProviderPolicy.load(manual_dir=tmp_path).refusal_reason(
        NFL, "moneyline"
    )

    assert "No market has a reviewed approval yet" in reason
    assert "carries across" not in reason


def test_a_file_with_the_right_name_is_not_a_signature(tmp_path: Path) -> None:
    """FINDING 9. `market_allowed()` used to stop at `receipt_path().is_file()`.

    It never opened the file, so this one — the word `signed`, in a file named
    after the id the entry happens to claim — was a complete approval as far
    as the card was concerned. The merge-time gate would have refused it, but
    the card runs on a schedule and "it would have been caught at merge" is
    not a check that runs when the card runs.
    """
    _write(tmp_path, _approval(["moneyline"]), receipt="r-1")

    policy = StagingProviderPolicy.load(manual_dir=tmp_path)

    assert not policy.market_allowed(NFL, "moneyline")
    assert "not a transcription" in policy.refusal_reason(NFL, "moneyline")


def test_a_receipt_crediting_somebody_off_the_allow_list_allows_nothing(
    tmp_path: Path,
) -> None:
    """FINDING 9. The reviewer is checked where the receipt is read, not only
    where it is written."""
    manual, receipt = _signed(tmp_path, ["moneyline"])
    path = manual / RECEIPTS_DIRNAME / f"{receipt}.md"
    binding = json.loads(
        path.read_text(encoding="utf-8").split("```json", 1)[1].split("```", 1)[0]
    )
    binding["reviewer_github_login"] = "someone-who-asked-nicely"
    path.write_text(
        "# Receipt\n\n```json\n" + json.dumps(binding) + "\n```\n", encoding="utf-8"
    )
    _write(
        tmp_path,
        _approval(["moneyline"], receipt=receipt, reviewer="someone-who-asked-nicely"),
        manual=manual,
    )

    policy = StagingProviderPolicy.load(manual_dir=manual)

    assert not policy.market_allowed(NFL, "moneyline")
    assert "allow-list" in policy.refusal_reason(NFL, "moneyline")
