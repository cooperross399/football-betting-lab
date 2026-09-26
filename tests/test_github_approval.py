"""One way to approve, and every other way fails closed.

The mechanism under test takes the reviewer's identity from GitHub's API. So
the tests that matter most are not the happy path — they are the ones that
show a receipt cannot be produced by naming a reviewer, by editing a policy
file, by quoting somebody else's comment, or by approving a state that has
since changed.

Nothing here writes into `data/manual/human_acceptance_receipts/`. Every path
a test touches is under `tmp_path`.
"""

from __future__ import annotations

import ast
from datetime import datetime, timedelta, timezone
import inspect
import json
import os
from pathlib import Path
import subprocess
from unittest import mock

import pytest

from football_betting_lab import github_approval
from football_betting_lab.github_approval import (
    ACCEPTED_REVIEW_STATE,
    ALLOWED_REVIEWERS,
    APPROVAL_PHRASE,
    EVIDENCE_REPORTS,
    MAX_APPROVAL_AGE_HOURS,
    REFUSED_REVIEW_STATES,
    REQUIRED_EVIDENCE_REPORT,
    REVOCATION_PHRASE,
    TRUSTED_GH_PATHS,
    GitHubApprovalError,
    VerifiedApproval,
    approval_from_github,
    approval_template,
    evidence_checksums,
    parse_approval_block,
    proposed_markets,
    resolve_gh,
    unquoted_lines,
    verify_github_approval,
)
from football_betting_lab.leagues import NFL
from football_betting_lab.markets import MARKETS_BY_KEY
from football_betting_lab.staging_provider_policy import POLICY_FILENAME


NOW = datetime(2026, 9, 26, 18, 0, tzinfo=timezone.utc)
APPROVED_AT = NOW - timedelta(hours=2)
HEAD_COMMITTED_AT = APPROVED_AT - timedelta(hours=3)
EVIDENCE_AT = APPROVED_AT - timedelta(hours=6)
PR = 54
HEAD = "headsha0011feedface22"
SCOPE = ("moneyline", "spread", "total_points")
REVIEWER = ALLOWED_REVIEWERS[0]


# -- building a checkout ----------------------------------------------------


def _run_git(repo: Path, arguments: list[str], when: datetime | None = None) -> None:
    environment = dict(os.environ)
    environment.update(
        {
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@example.invalid",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@example.invalid",
        }
    )
    if when is not None:
        stamp = when.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+0000")
        environment["GIT_AUTHOR_DATE"] = stamp
        environment["GIT_COMMITTER_DATE"] = stamp
    subprocess.run(
        ["git", "-C", str(repo), *arguments],
        check=True,
        capture_output=True,
        env=environment,
    )


def _policy(markets=SCOPE, *, key: str | None = None, **overrides) -> dict:
    entry = {
        "allowlist_status": "proposed",
        "approved_at": "",
        "reviewer_name": "",
        "evidence_receipt_id": "",
        "required_markets": list(markets),
    }
    entry.update(overrides)
    return {
        "allowed_provider_names": [],
        "provider_allowlist_entries": {key or NFL.policy_key(): entry},
    }


def _checkout(
    tmp_path: Path,
    *,
    policy: dict | None = None,
    reports: tuple[tuple[str, str], ...] = EVIDENCE_REPORTS,
    evidence_at: datetime = EVIDENCE_AT,
) -> Path:
    """A repository holding a proposed policy and committed evidence.

    Every evidence report by default, because an approval now binds to the
    whole bundle: a report that is absent used to narrow the binding in
    silence, so the fixture that stands for "a normal pull request" has to be
    a complete one. The tests that are about a missing report pass `reports`.
    """
    repo = tmp_path / "checkout"
    outputs = repo / "data" / "outputs"
    manual = repo / "data" / "manual"
    outputs.mkdir(parents=True, exist_ok=True)
    manual.mkdir(parents=True, exist_ok=True)
    (manual / POLICY_FILENAME).write_text(
        json.dumps(policy if policy is not None else _policy(), indent=2),
        encoding="utf-8",
    )
    for stem, suffix in reports:
        (outputs / NFL.output_name(stem, suffix)).write_text(
            f"# {stem}\n\nMeasured, not assumed.\n", encoding="utf-8"
        )
    _run_git(repo, ["init", "-q"])
    _run_git(repo, ["add", "-f", "data"])
    _run_git(repo, ["commit", "-q", "-m", "evidence"], when=evidence_at)
    return repo


def _paths(repo: Path) -> dict:
    return {
        "policy_path": repo / "data" / "manual" / POLICY_FILENAME,
        "output_dir": repo / "data" / "outputs",
        "repo_root": repo,
    }


# -- building GitHub activity ----------------------------------------------


def _body(
    *,
    phrase: str = APPROVAL_PHRASE,
    pr: int | None = PR,
    provider: str = NFL.policy_provider_name,
    league: str | None = NFL.key,
    markets: str | None = ", ".join(SCOPE),
) -> str:
    lines = [phrase]
    if pr is not None:
        lines.append(f"pr: {pr}")
    if provider:
        lines.append(f"provider: {provider}")
    if league:
        lines.append(f"league: {league}")
    if markets is not None and markets != "":
        lines.append(f"markets: {markets}")
    return "\n".join(lines)


def _activity(
    *,
    author: str = REVIEWER,
    body: str | None = None,
    kind: str = "review",
    submitted: datetime = APPROVED_AT,
    commit_id: str = HEAD,
    pr_number: int = PR,
    head_committed_at: datetime | None = HEAD_COMMITTED_AT,
) -> dict:
    entry = {
        "user": {"login": author},
        "body": _body() if body is None else body,
        "id": 900001,
    }
    activity: dict = {
        "pr_number": pr_number,
        "repository": "cooperross399/football-betting-lab",
        "head_sha": HEAD,
        "head_committed_at": (
            head_committed_at.isoformat() if head_committed_at else ""
        ),
        "reviews": [],
        "comments": [],
    }
    if kind == "review":
        entry.update(
            {
                "submitted_at": submitted.isoformat(),
                "commit_id": commit_id,
                "state": "APPROVED",
            }
        )
        activity["reviews"] = [entry]
    else:
        entry["created_at"] = submitted.isoformat()
        activity["comments"] = [entry]
    return activity


def _verify(activity: dict, repo: Path, **overrides):
    parameters = dict(pr_number=PR, league=NFL, now=NOW, **_paths(repo))
    parameters.update(overrides)
    return verify_github_approval(activity, **parameters)


# -- minting, which is a different act from verifying -----------------------


def recent_moments() -> tuple[datetime, datetime, datetime, datetime]:
    """Now, the approval, the head commit and the evidence commit.

    Anchored to the real clock because the minting path reads it: it takes no
    `now`, on purpose, so a fixture dated 2026 would be stale against a window
    measured in hours.
    """
    now = datetime.now(timezone.utc)
    return (
        now,
        now - timedelta(hours=1),
        now - timedelta(hours=2),
        now - timedelta(hours=3),
    )


def mint(activity: dict, repo: Path, **overrides):
    """A `VerifiedApproval` from activity this test wrote.

    The one seam a test gets, and it is a patched *fetch* rather than a
    supplied *activity*: `approval_from_github` has no activity parameter and
    must not grow one, because a mapping a caller passes is a mapping a caller
    wrote. Standing in for the network is a thing only in-process code can do,
    which is the line this mechanism draws.
    """
    parameters = dict(
        pr_number=PR,
        repository=activity.get("repository") or "cooperross399/football-betting-lab",
        league=NFL,
        **_paths(repo),
    )
    parameters.update(overrides)
    with mock.patch.object(
        github_approval, "fetch_pr_activity", return_value=activity
    ):
        return github_approval.approval_from_github(**parameters)


def signed_manual(tmp_path: Path, markets=SCOPE, **entry_overrides) -> Path:
    """A `data/manual` directory whose entry is backed by a genuine receipt.

    Used wherever a test needs `market_allowed()` to say yes. There is no
    shortcut any more: the loader opens the receipt, checks the reviewer, the
    digest and the evidence checksums, so a file reading "signed" is not one.
    """
    from football_betting_lab.human_acceptance_receipt import (
        build_receipt,
        write_receipt,
    )
    from football_betting_lab.staging_provider_policy import RECEIPTS_DIRNAME

    now, approved, head_at, evidence_at = recent_moments()
    repo = _checkout(tmp_path, policy=_policy(markets), evidence_at=evidence_at)
    approval = mint(
        _activity(
            body=_body(markets=", ".join(markets)),
            submitted=approved,
            head_committed_at=head_at,
        ),
        repo,
    )
    receipt = build_receipt(approval)
    manual = repo / "data" / "manual"
    write_receipt(receipt, receipts_dir=manual / RECEIPTS_DIRNAME)
    entry = {
        "allowlist_status": "allowed",
        "approved_at": receipt["github_approval"]["approved_at"],
        "reviewer_name": receipt["reviewer_github_login"],
        "evidence_receipt_id": receipt["receipt_id"],
        "required_markets": list(markets),
    }
    entry.update(entry_overrides)
    (manual / POLICY_FILENAME).write_text(
        json.dumps(
            {
                "allowed_provider_names": [NFL.policy_provider_name],
                "provider_allowlist_entries": {NFL.policy_key(): entry},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return manual


# -- the happy path ---------------------------------------------------------


def test_a_review_carrying_the_block_verifies(tmp_path: Path) -> None:
    repo = _checkout(tmp_path)

    approval = _verify(_activity(), repo)

    assert approval["decision"] == "approved_for_allowlist_pr"
    assert approval["reviewer_github_login"] == REVIEWER
    assert approval["pr_number"] == PR
    assert approval["policy_key"] == NFL.policy_key()
    assert approval["provider_name"] == NFL.policy_provider_name
    assert approval["approved_markets"] == sorted(SCOPE)
    assert approval["source_kind"] == "review"
    assert approval["evidence_checksums_sha256"]


def test_a_comment_carrying_the_block_verifies(tmp_path: Path) -> None:
    """Cooper opens most of these pull requests, and GitHub will not let an
    author review their own. A comment has to count or the mechanism is
    unusable by the one person it is for."""
    repo = _checkout(tmp_path)

    approval = _verify(_activity(kind="comment"), repo)

    assert approval["source_kind"] == "comment"
    assert approval["reviewer_github_login"] == REVIEWER


def test_the_receipt_names_what_was_withheld_as_well(tmp_path: Path) -> None:
    repo = _checkout(tmp_path)

    approval = _verify(_activity(), repo)

    assert set(approval["markets_not_approved"]) == set(MARKETS_BY_KEY) - set(SCOPE)
    assert not set(approval["approved_markets"]) & set(approval["markets_not_approved"])


# -- the reviewer -----------------------------------------------------------


def test_a_missing_phrase_is_refused(tmp_path: Path) -> None:
    repo = _checkout(tmp_path)

    with pytest.raises(GitHubApprovalError, match=APPROVAL_PHRASE):
        _verify(_activity(body=_body(phrase="looks good to me")), repo)


def test_an_author_off_the_allow_list_is_refused(tmp_path: Path) -> None:
    repo = _checkout(tmp_path)

    with pytest.raises(GitHubApprovalError, match="allowed reviewer"):
        _verify(_activity(author="someone-else"), repo)


def test_quoting_the_approval_does_not_sign_it(tmp_path: Path) -> None:
    """A bot or a collaborator repeating the block must not approve."""
    repo = _checkout(tmp_path)

    with pytest.raises(GitHubApprovalError, match="allowed reviewer"):
        _verify(_activity(author="helpful-bot", body="> " + _body()), repo)


def test_the_reviewer_cannot_be_supplied_by_a_caller() -> None:
    """The identity comes from GitHub. No parameter may offer another source.

    This is the property the whole mechanism rests on, so it is asserted
    against the signature rather than trusted to review.
    """
    parameters = set(inspect.signature(verify_github_approval).parameters)

    assert parameters == {
        "activity",
        "pr_number",
        "league",
        "policy_path",
        "output_dir",
        "repo_root",
        "now",
    }
    for forbidden in ("reviewer", "reviewer_name", "allowed_reviewers", "author"):
        assert forbidden not in parameters


def test_the_freshness_window_is_not_a_parameter() -> None:
    """A window a caller can widen is not a window."""
    assert "max_age_hours" not in inspect.signature(verify_github_approval).parameters
    assert MAX_APPROVAL_AGE_HOURS > 0


def test_no_identity_is_read_from_the_machine_running_this() -> None:
    """Not `git config user.name`, not an environment variable.

    Read off the syntax tree rather than the text, because the module's own
    docstring says what it does not do and a substring search cannot tell the
    promise from the breach.
    """
    module = ast.parse(
        Path(inspect.getsourcefile(verify_github_approval) or "").read_text(
            encoding="utf-8"
        )
    )
    docstrings = {
        id(node.body[0].value)
        for node in ast.walk(module)
        if isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        )
        and getattr(node, "body", None)
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
        and isinstance(node.body[0].value.value, str)
    }
    literals = [
        node.value
        for node in ast.walk(module)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in docstrings
    ]
    names = [
        node.attr for node in ast.walk(module) if isinstance(node, ast.Attribute)
    ] + [
        node.id for node in ast.walk(module) if isinstance(node, ast.Name)
    ]

    assert not [text for text in literals if "user.name" in text or "config" in text]
    assert "environ" not in names and "getenv" not in names


# -- what the approval declares --------------------------------------------


def test_an_approval_naming_another_pull_request_is_refused(tmp_path: Path) -> None:
    repo = _checkout(tmp_path)

    with pytest.raises(GitHubApprovalError, match="names PR"):
        _verify(_activity(body=_body(pr=55)), repo)


def test_an_approval_with_no_pull_request_is_refused(tmp_path: Path) -> None:
    repo = _checkout(tmp_path)

    with pytest.raises(GitHubApprovalError, match="must declare `pr:`"):
        _verify(_activity(body=_body(pr=None)), repo)


def test_activity_fetched_for_another_pull_request_is_refused(tmp_path: Path) -> None:
    repo = _checkout(tmp_path)

    with pytest.raises(GitHubApprovalError, match="activity is for PR"):
        _verify(_activity(pr_number=55), repo)


def test_an_approval_naming_another_provider_is_refused(tmp_path: Path) -> None:
    repo = _checkout(tmp_path)

    with pytest.raises(GitHubApprovalError, match="provider"):
        _verify(_activity(body=_body(provider="some_other_book_feed")), repo)


def test_an_approval_with_no_provider_is_refused(tmp_path: Path) -> None:
    repo = _checkout(tmp_path)

    with pytest.raises(GitHubApprovalError, match="must declare `provider:`"):
        _verify(_activity(body=_body(provider="")), repo)


def test_an_approval_naming_another_league_is_refused(tmp_path: Path) -> None:
    """The policy is keyed `{provider}:{league}` precisely so that one
    approval cannot travel. The comment has to say which league it is."""
    repo = _checkout(tmp_path)

    with pytest.raises(GitHubApprovalError, match="One receipt, one league"):
        _verify(_activity(body=_body(league="ncaaf")), repo)


def test_an_approval_with_no_league_is_refused(tmp_path: Path) -> None:
    repo = _checkout(tmp_path)

    with pytest.raises(GitHubApprovalError, match="must declare `league:`"):
        _verify(_activity(body=_body(league="")), repo)


def test_an_approval_with_no_markets_is_refused(tmp_path: Path) -> None:
    repo = _checkout(tmp_path)

    with pytest.raises(GitHubApprovalError, match="must declare `markets:`"):
        _verify(_activity(body=_body(markets="")), repo)


def test_a_market_the_registry_does_not_hold_is_refused(tmp_path: Path) -> None:
    """The market registry is the single source of what can be approved."""
    repo = _checkout(tmp_path, policy=_policy((*SCOPE, "first_basket_scorer")))

    with pytest.raises(GitHubApprovalError, match="registry does not hold"):
        _verify(
            _activity(body=_body(markets=", ".join((*SCOPE, "first_basket_scorer")))),
            repo,
        )


def test_there_is_no_shorthand_for_every_market(tmp_path: Path) -> None:
    """`markets: all` would be a scope nobody read."""
    repo = _checkout(tmp_path)

    with pytest.raises(GitHubApprovalError, match="registry does not hold"):
        _verify(_activity(body=_body(markets="all")), repo)


def test_a_scope_narrower_than_the_proposal_is_refused(tmp_path: Path) -> None:
    repo = _checkout(tmp_path)

    with pytest.raises(GitHubApprovalError, match="proposed but not named"):
        _verify(_activity(body=_body(markets=SCOPE[0])), repo)


def test_a_scope_wider_than_the_proposal_is_refused(tmp_path: Path) -> None:
    """A market the pull request does not propose cannot ride in on the
    comment: the diff and the signature have to agree."""
    repo = _checkout(tmp_path)
    wider = ", ".join((*SCOPE, "team_total"))

    with pytest.raises(GitHubApprovalError, match="Named but not proposed"):
        _verify(_activity(body=_body(markets=wider)), repo)


# -- the proposed policy ----------------------------------------------------


def test_a_missing_policy_is_refused(tmp_path: Path) -> None:
    repo = _checkout(tmp_path)
    (repo / "data" / "manual" / POLICY_FILENAME).unlink()

    with pytest.raises(GitHubApprovalError, match="No policy file"):
        _verify(_activity(), repo)


def test_a_malformed_policy_is_refused(tmp_path: Path) -> None:
    repo = _checkout(tmp_path)
    (repo / "data" / "manual" / POLICY_FILENAME).write_text("{not json", encoding="utf-8")

    with pytest.raises(GitHubApprovalError, match="could not be read"):
        _verify(_activity(), repo)


def test_a_policy_that_is_not_an_object_is_refused(tmp_path: Path) -> None:
    repo = _checkout(tmp_path)
    (repo / "data" / "manual" / POLICY_FILENAME).write_text("[]", encoding="utf-8")

    with pytest.raises(GitHubApprovalError, match="not a JSON object"):
        _verify(_activity(), repo)


def test_a_policy_with_no_entry_for_this_league_is_refused(tmp_path: Path) -> None:
    repo = _checkout(
        tmp_path, policy={"provider_allowlist_entries": {}}
    )

    with pytest.raises(GitHubApprovalError, match="no entry for"):
        _verify(_activity(), repo)


def test_an_entry_keyed_without_the_league_is_not_this_leagues_scope(
    tmp_path: Path,
) -> None:
    """The lab this came from keys its entries by provider alone. Reading one
    of those as an NFL scope is how an approval crosses a league boundary, so
    the bare provider key is not found at all rather than fallen back to."""
    repo = _checkout(
        tmp_path, policy=_policy(key=NFL.policy_provider_name)
    )

    with pytest.raises(GitHubApprovalError, match="no entry for"):
        _verify(_activity(), repo)


def test_an_entry_proposing_no_markets_is_refused(tmp_path: Path) -> None:
    repo = _checkout(tmp_path, policy=_policy(()))

    with pytest.raises(GitHubApprovalError, match="proposes no markets"):
        _verify(_activity(), repo)


def test_an_entry_proposing_an_unknown_market_is_refused(tmp_path: Path) -> None:
    repo = _checkout(tmp_path, policy=_policy((*SCOPE, "coin_toss")))

    with pytest.raises(GitHubApprovalError, match="registry does not hold"):
        _verify(_activity(), repo)


def test_the_policys_own_reviewer_name_is_never_the_approval(tmp_path: Path) -> None:
    """An entry can be edited to say `allowed`, name a reviewer and name a
    receipt id. None of that is an approval, and the verifier reads none of
    it: the scope comes from `required_markets` and the reviewer from GitHub.

    This is the shape a fabricated approval takes in this lab, because the
    policy file is the one place where a name and a status sit next to each
    other in a file anyone can edit.
    """
    repo = _checkout(
        tmp_path,
        policy=_policy(
            allowlist_status="allowed",
            reviewer_name="Somebody Else",
            evidence_receipt_id="receipt-i-made-up",
        ),
    )

    approval = _verify(_activity(), repo)

    assert approval["reviewer_github_login"] == REVIEWER
    assert "Somebody Else" not in json.dumps(approval)
    assert "receipt-i-made-up" not in json.dumps(approval)


def test_a_self_signed_policy_with_no_github_approval_produces_nothing(
    tmp_path: Path,
) -> None:
    """The same entry, with nobody having approved anything on GitHub."""
    repo = _checkout(
        tmp_path,
        policy=_policy(
            allowlist_status="allowed",
            reviewer_name=REVIEWER,
            evidence_receipt_id="receipt-i-made-up",
        ),
    )
    empty = _activity()
    empty["reviews"] = []

    with pytest.raises(GitHubApprovalError, match="No review or comment"):
        _verify(empty, repo)


# -- the state that was approved -------------------------------------------


def test_a_review_of_a_superseded_commit_is_refused(tmp_path: Path) -> None:
    repo = _checkout(tmp_path)

    with pytest.raises(GitHubApprovalError, match="Re-approve the current head"):
        _verify(_activity(commit_id="oldcommitsha99"), repo)


def test_a_commit_pushed_after_the_approval_is_refused(tmp_path: Path) -> None:
    """Covers the comment case too, which carries no commit of its own: a
    head that landed after the signature is a state the reviewer never saw."""
    repo = _checkout(tmp_path)
    pushed_later = APPROVED_AT + timedelta(minutes=30)

    with pytest.raises(GitHubApprovalError, match="after the approval"):
        _verify(_activity(kind="comment", head_committed_at=pushed_later), repo)


def test_a_head_with_no_timestamp_is_refused(tmp_path: Path) -> None:
    repo = _checkout(tmp_path)

    with pytest.raises(GitHubApprovalError, match="no readable timestamp"):
        _verify(_activity(head_committed_at=None), repo)


def test_evidence_recommitted_after_the_approval_is_refused(tmp_path: Path) -> None:
    repo = _checkout(tmp_path)
    report = repo / "data" / "outputs" / NFL.output_name(*REQUIRED_EVIDENCE_REPORT)
    report.write_text("# rebuilt\n\nnew numbers\n", encoding="utf-8")
    _run_git(repo, ["add", "-f", "data"])
    _run_git(
        repo,
        ["commit", "-q", "-m", "regenerated"],
        when=APPROVED_AT + timedelta(minutes=10),
    )

    with pytest.raises(GitHubApprovalError, match="after the approval"):
        _verify(_activity(), repo)


def test_evidence_changed_in_the_workspace_is_refused(tmp_path: Path) -> None:
    """A report regenerated by the job is a report nobody reviewed, whatever
    its checksum now is."""
    repo = _checkout(tmp_path)
    report = repo / "data" / "outputs" / NFL.output_name(*REQUIRED_EVIDENCE_REPORT)
    report.write_text("# rebuilt in the runner\n", encoding="utf-8")

    with pytest.raises(GitHubApprovalError, match="differs from its committed"):
        _verify(_activity(), repo)


def test_an_uncommitted_evidence_report_is_refused(tmp_path: Path) -> None:
    repo = _checkout(tmp_path)
    (repo / "data" / "outputs" / NFL.output_name("slate_coverage", ".md")).write_text(
        "# coverage\n", encoding="utf-8"
    )

    with pytest.raises(GitHubApprovalError, match="differs from its committed"):
        _verify(_activity(), repo)


def test_a_missing_evidence_bundle_is_refused(tmp_path: Path) -> None:
    repo = _checkout(tmp_path, reports=(("slate_coverage", ".md"),))

    with pytest.raises(GitHubApprovalError, match="is not present"):
        _verify(_activity(), repo)


def test_evidence_outside_the_checkout_is_refused(tmp_path: Path) -> None:
    """Evidence with no commit behind it cannot be shown to a reviewer."""
    repo = _checkout(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / NFL.output_name(*REQUIRED_EVIDENCE_REPORT)).write_text(
        "# unrelated\n", encoding="utf-8"
    )

    with pytest.raises(GitHubApprovalError, match="not inside the repository"):
        _verify(_activity(), repo, output_dir=elsewhere)


# -- time -------------------------------------------------------------------


def test_a_stale_approval_is_refused(tmp_path: Path) -> None:
    repo = _checkout(
        tmp_path, evidence_at=NOW - timedelta(days=30)
    )
    old = NOW - timedelta(hours=MAX_APPROVAL_AGE_HOURS + 1)

    with pytest.raises(GitHubApprovalError, match="stale"):
        _verify(
            _activity(submitted=old, head_committed_at=old - timedelta(hours=1)),
            repo,
        )


def test_an_approval_just_inside_the_window_verifies(tmp_path: Path) -> None:
    """The window is a limit, not a mood."""
    repo = _checkout(tmp_path, evidence_at=NOW - timedelta(days=30))
    recent = NOW - timedelta(hours=MAX_APPROVAL_AGE_HOURS - 1)

    approval = _verify(
        _activity(submitted=recent, head_committed_at=recent - timedelta(hours=1)),
        repo,
    )

    assert approval["approved_markets"] == sorted(SCOPE)


def test_a_future_dated_approval_is_refused(tmp_path: Path) -> None:
    repo = _checkout(tmp_path)

    with pytest.raises(GitHubApprovalError, match="in the future"):
        _verify(_activity(submitted=NOW + timedelta(hours=5)), repo)


def test_the_most_recent_approval_is_the_one_read(tmp_path: Path) -> None:
    repo = _checkout(tmp_path)
    activity = _activity()
    activity["comments"] = [
        {
            "user": {"login": REVIEWER},
            "body": _body(markets=SCOPE[0]),
            "created_at": (APPROVED_AT - timedelta(hours=5)).isoformat(),
            "id": 900002,
        }
    ]

    approval = _verify(activity, repo)

    assert approval["approved_markets"] == sorted(SCOPE)
    assert approval["source_kind"] == "review"


# -- the lab's own scale ----------------------------------------------------


def test_the_whole_registry_can_be_approved_when_it_is_named_exactly(
    tmp_path: Path,
) -> None:
    """The open proposal on this repository names all sixty markets.

    Sixty is a lot to type, which is exactly the pressure that produces a
    shorthand. There is none: the block names them, and the gate prints the
    block.
    """
    everything = tuple(sorted(MARKETS_BY_KEY))
    repo = _checkout(tmp_path, policy=_policy(everything))

    approval = _verify(
        _activity(body=_body(markets=", ".join(everything))), repo
    )

    assert approval["approved_markets"] == sorted(everything)
    assert approval["markets_not_approved"] == []


def test_one_market_dropped_from_a_sixty_market_approval_is_refused(
    tmp_path: Path,
) -> None:
    everything = tuple(sorted(MARKETS_BY_KEY))
    repo = _checkout(tmp_path, policy=_policy(everything))

    with pytest.raises(GitHubApprovalError, match="proposed but not named"):
        _verify(_activity(body=_body(markets=", ".join(everything[1:]))), repo)


# -- helpers and invariants -------------------------------------------------


def test_the_verifier_writes_nothing(tmp_path: Path) -> None:
    repo = _checkout(tmp_path)
    before = {
        path: path.read_bytes()
        for path in sorted(repo.rglob("*"))
        if path.is_file() and ".git" not in path.parts
    }

    _verify(_activity(), repo)

    after = {
        path: path.read_bytes()
        for path in sorted(repo.rglob("*"))
        if path.is_file() and ".git" not in path.parts
    }
    assert before == after


def test_the_proposed_scope_is_read_from_the_policy(tmp_path: Path) -> None:
    repo = _checkout(tmp_path, policy=_policy(("moneyline", "team_total")))

    assert proposed_markets(NFL, _paths(repo)["policy_path"]) == (
        "moneyline",
        "team_total",
    )


def test_the_template_carries_every_line_the_verifier_requires() -> None:
    text = approval_template(PR, league=NFL, markets=SCOPE)

    assert APPROVAL_PHRASE in text
    assert f"pr: {PR}" in text
    assert f"provider: {NFL.policy_provider_name}" in text
    assert f"league: {NFL.key}" in text
    assert f"markets: {', '.join(SCOPE)}" in text


def test_the_template_round_trips_through_the_verifier(tmp_path: Path) -> None:
    repo = _checkout(tmp_path)

    approval = _verify(
        _activity(body=approval_template(PR, league=NFL, markets=SCOPE)), repo
    )

    assert approval["approved_markets"] == sorted(SCOPE)


def test_the_block_parses_through_markdown_and_capitalisation() -> None:
    parsed = parse_approval_block(
        "\n".join(
            [
                APPROVAL_PHRASE,
                f"- PR: {PR}",
                "* Provider: The_Odds_API",
                "> League: NFL",
                "  markets: Moneyline; SPREAD",
            ]
        )
    )

    assert parsed["pr"] == PR
    assert parsed["provider"] == "the_odds_api"
    assert parsed["league"] == NFL.key
    assert parsed["markets"] == ["moneyline", "spread"]


def test_the_checksums_move_when_the_evidence_moves(tmp_path: Path) -> None:
    repo = _checkout(tmp_path)
    outputs = _paths(repo)["output_dir"]
    before = evidence_checksums(NFL, outputs)

    (outputs / NFL.output_name(*REQUIRED_EVIDENCE_REPORT)).write_text(
        "# different\n", encoding="utf-8"
    )

    assert evidence_checksums(NFL, outputs) != before


def test_the_evidence_reports_are_named_per_league() -> None:
    """Two leagues must never bind an approval to one file."""
    names = {NFL.output_name(stem, suffix) for stem, suffix in EVIDENCE_REPORTS}

    assert names
    assert all(name.startswith(f"{NFL.key}_") for name in names)
    assert NFL.output_name(*REQUIRED_EVIDENCE_REPORT) in names


# -- the nine ways a receipt was minted without a signature -----------------
#
# Each of these fails without the change it is paired with. They are grouped
# here rather than filed among the checks above because what they have in
# common is the finding, not the field: every one of them was RUN against this
# lab and produced a verified approval, or a receipt, with nobody having
# signed anything.


def test_the_gh_this_module_runs_is_named_and_not_searched_for() -> None:
    """FINDING 1. `subprocess.run(["gh", ...])` asks PATH which program that is.

    A forty-line script called `gh` earlier on PATH answers every API call in
    `fetch_pr_activity` — exit 0, JSON on stdout, whatever login it likes —
    and mints a receipt with no edit to any tracked file. Read off the syntax
    tree, because the property is "no call in this module spells the bare
    name", which a reader can miss and a search cannot.
    """
    tree = ast.parse(
        Path(inspect.getsourcefile(verify_github_approval) or "").read_text(
            encoding="utf-8"
        )
    )
    bare_invocations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for argument in node.args:
            if not isinstance(argument, ast.List) or not argument.elts:
                continue
            first = argument.elts[0]
            if isinstance(first, ast.Constant) and first.value == "gh":
                bare_invocations.append(ast.dump(node)[:80])

    assert bare_invocations == [], bare_invocations
    assert all(path.startswith("/") for path in TRUSTED_GH_PATHS)


def test_a_gh_earlier_on_the_path_is_refused_rather_than_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FINDING 1, run. The shim is reported, not silently stepped over."""
    binaries = tmp_path / "bin"
    binaries.mkdir()
    shim = binaries / "gh"
    shim.write_text("#!/bin/sh\necho '[]'\n", encoding="utf-8")
    shim.chmod(0o755)
    monkeypatch.setenv("PATH", f"{binaries}{os.pathsep}{os.environ['PATH']}")

    with pytest.raises(GitHubApprovalError, match="earlier on PATH"):
        resolve_gh()


def test_a_gh_at_no_trusted_location_at_all_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FINDING 1. No trusted binary is a refusal, never a fallback to PATH."""
    monkeypatch.setattr(github_approval, "TRUSTED_GH_PATHS", ("/nowhere/at/all/gh",))
    monkeypatch.setattr(github_approval.shutil, "which", lambda name: None)

    with pytest.raises(GitHubApprovalError, match="trusted location"):
        resolve_gh()


def test_a_program_that_is_not_the_github_cli_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FINDING 1. Being at the right path is not the same as being the tool."""
    impostor = tmp_path / "gh"
    impostor.write_text("#!/bin/sh\necho 'definitely gh, honest'\n", encoding="utf-8")
    impostor.chmod(0o755)
    monkeypatch.setattr(github_approval, "TRUSTED_GH_PATHS", (str(impostor),))
    monkeypatch.setattr(github_approval.shutil, "which", lambda name: None)

    with pytest.raises(GitHubApprovalError, match="does not answer"):
        resolve_gh()


def test_a_verified_approval_cannot_be_built_by_hand() -> None:
    """FINDING 2. The type is the claim "this module fetched this".

    A public constructor makes an `isinstance` check decorative: the forger
    builds one naming an allowed reviewer and hands it over. The construction
    token is held in a closure, so there is no data path to one.
    """
    with pytest.raises(GitHubApprovalError, match="minted by this module"):
        VerifiedApproval(object(), {"reviewer_github_login": REVIEWER})

    with pytest.raises(GitHubApprovalError, match="minted by this module"):
        VerifiedApproval(None, {})

    assert not [
        name
        for name, value in vars(github_approval).items()
        if type(value) is object and not name.startswith("__")
    ], "the construction token must not be reachable as a module attribute"


def test_the_minting_path_fetches_its_own_activity(tmp_path: Path) -> None:
    """FINDING 3. An activity a caller supplies is a mapping a caller wrote."""
    parameters = set(inspect.signature(approval_from_github).parameters)

    assert parameters == {
        "pr_number",
        "repository",
        "league",
        "policy_path",
        "output_dir",
        "repo_root",
    }
    for forbidden in ("activity", "now", "reviewer", "reviewer_name", "max_age_hours"):
        assert forbidden not in parameters


def test_the_pure_verifier_still_verifies_and_can_no_longer_mint(
    tmp_path: Path,
) -> None:
    """FINDING 3, run. The seam stays open for tests and closed for receipts."""
    from football_betting_lab.human_acceptance_receipt import ReceiptError, build_receipt

    repo = _checkout(tmp_path)
    fabricated = _verify(_activity(), repo)

    assert fabricated["reviewer_github_login"] == REVIEWER
    with pytest.raises(ReceiptError, match="fetched from GitHub"):
        build_receipt(fabricated)


@pytest.mark.parametrize("state", REFUSED_REVIEW_STATES + ("", "APPROVED_IN_SPIRIT"))
def test_a_review_in_any_state_but_approved_is_refused(
    tmp_path: Path, state: str
) -> None:
    """FINDING 4. The state was transcribed into the receipt and used for
    nothing, so a review GitHub itself reports as DISMISSED — withdrawn —
    verified, and so did a review with no state at all."""
    repo = _checkout(tmp_path)
    activity = _activity()
    activity["reviews"][0]["state"] = state

    with pytest.raises(GitHubApprovalError, match="not 'APPROVED'"):
        _verify(activity, repo)


def test_an_approved_review_still_verifies(tmp_path: Path) -> None:
    """The state check is a check, not a wall."""
    repo = _checkout(tmp_path)

    approval = _verify(_activity(), repo)

    assert approval["review_state"] == ACCEPTED_REVIEW_STATE


def test_a_newer_revocation_withdraws_the_approval(tmp_path: Path) -> None:
    """FINDING 5. There was no way to say no.

    Only entries carrying the approval phrase were ever looked at, so a later
    "I withdraw that" was invisible and the withdrawn signature went on
    verifying for as long as the freshness window allowed.
    """
    repo = _checkout(tmp_path)
    activity = _activity()
    activity["comments"] = [
        {
            "user": {"login": REVIEWER},
            "body": f"{REVOCATION_PHRASE}\nI withdraw that approval.",
            "created_at": (APPROVED_AT + timedelta(minutes=30)).isoformat(),
            "id": 900003,
        }
    ]

    with pytest.raises(GitHubApprovalError, match=REVOCATION_PHRASE):
        _verify(activity, repo)


def test_a_revocation_older_than_the_approval_does_not_bind(tmp_path: Path) -> None:
    """Approving after a revocation is approving. The newest word governs."""
    repo = _checkout(tmp_path)
    activity = _activity()
    activity["comments"] = [
        {
            "user": {"login": REVIEWER},
            "body": REVOCATION_PHRASE,
            "created_at": (APPROVED_AT - timedelta(hours=4)).isoformat(),
            "id": 900004,
        }
    ]

    approval = _verify(activity, repo)

    assert approval["approved_markets"] == sorted(SCOPE)


def test_a_quoted_block_is_not_a_fresh_approval(tmp_path: Path) -> None:
    """FINDING 5, the other half. Quoting an approval is repeating it.

    The parser strips `> ` so a reviewer typing into a quoted reply is still
    understood, and that tolerance made this comment — which says REVOKED at
    the top of it — verify as an approval newer than the one it quotes.
    """
    repo = _checkout(tmp_path)
    activity = _activity()
    activity["comments"] = [
        {
            "user": {"login": REVIEWER},
            "body": "REVOKED. Ignore this:\n> " + "\n> ".join(_body().splitlines()),
            "created_at": (APPROVED_AT + timedelta(hours=1)).isoformat(),
            "id": 900005,
        }
    ]

    with pytest.raises(GitHubApprovalError, match="only inside a quoted block"):
        _verify(activity, repo)


def test_the_parser_still_forgives_a_stray_marker_on_its_own_lines() -> None:
    """...and the tolerance it needs is kept where it belongs."""
    assert unquoted_lines("a\n> b\n  > c\nd") == "a\nd"
    assert parse_approval_block(f"- PR: {PR}")["pr"] == PR


def test_an_incomplete_evidence_bundle_is_refused(tmp_path: Path) -> None:
    """FINDING 7. A binding that narrows itself is not a binding.

    `evidence_checksums` returns what it found, so a report that is absent is
    simply not in the table: deleting artifacts produced an approval bound to
    fewer of them, with no warning anywhere.
    """
    repo = _checkout(tmp_path)
    dropped = NFL.output_name(*EVIDENCE_REPORTS[2])
    (repo / "data" / "outputs" / dropped).unlink()
    _run_git(repo, ["add", "-A"])
    _run_git(repo, ["commit", "-q", "-m", "drop one"], when=EVIDENCE_AT)

    with pytest.raises(GitHubApprovalError, match="is not present"):
        _verify(_activity(), repo)


def test_a_complete_bundle_binds_every_report(tmp_path: Path) -> None:
    """Stated positively: the count is the whole bundle, not whatever existed."""
    repo = _checkout(tmp_path)

    approval = _verify(_activity(), repo)

    assert set(approval["evidence_checksums_sha256"]) == {
        NFL.output_name(stem, suffix) for stem, suffix in EVIDENCE_REPORTS
    }


def test_the_minting_path_round_trips_a_real_approval(tmp_path: Path) -> None:
    """The happy path through the function that can actually produce one."""
    now, approved, head_at, evidence_at = recent_moments()
    repo = _checkout(tmp_path, evidence_at=evidence_at)

    approval = mint(
        _activity(submitted=approved, head_committed_at=head_at), repo
    )

    assert isinstance(approval, VerifiedApproval)
    assert approval.reviewer_github_login == REVIEWER
    assert approval.as_dict()["approved_markets"] == sorted(SCOPE)


def test_an_undated_revocation_is_refused_rather_than_ranked_last(
    tmp_path: Path,
) -> None:
    """FINDING 5, the edge the first fix left open.

    `max` over a sort key that reads an unreadable timestamp as the beginning
    of time ranks an undated withdrawal behind a dated one, so a revocation
    nothing can place would have been silently treated as the older word.
    """
    repo = _checkout(tmp_path)
    activity = _activity()
    activity["comments"] = [
        {
            "user": {"login": REVIEWER},
            "body": REVOCATION_PHRASE,
            "created_at": "",
            "id": 900006,
        },
        {
            "user": {"login": REVIEWER},
            "body": REVOCATION_PHRASE,
            "created_at": (APPROVED_AT - timedelta(hours=9)).isoformat(),
            "id": 900007,
        },
    ]

    with pytest.raises(GitHubApprovalError, match="no readable timestamp"):
        _verify(activity, repo)
