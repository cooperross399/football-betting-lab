"""The receipt, the gate, and the command that cannot sign on Cooper's behalf.

`tests/test_github_approval.py` covers the verification. This covers what is
done with a verified approval: the receipt it becomes, the gate that re-reads
that receipt on every policy change, and the command-line entry point — run
here as a real subprocess against a stubbed `gh`, because the claim being
tested is "the reviewer comes from the API" and only running it proves that.

Every receipt written by this module is written into `tmp_path`. Nothing here
creates `data/manual/human_acceptance_receipts/`.
"""

from __future__ import annotations

import argparse
import ast
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from football_betting_lab.config import PROJECT_ROOT
from football_betting_lab.github_approval import (
    ALLOWED_REVIEWERS,
    APPROVAL_DECISION,
    APPROVAL_PHRASE,
    REQUIRED_EVIDENCE_REPORT,
    approval_template,
    verify_github_approval,
)
from football_betting_lab.human_acceptance_receipt import (
    RECEIPT_KIND,
    ReceiptError,
    build_receipt,
    read_receipt,
    receipt_id,
    receipts_directory,
    render_receipt,
    write_receipt,
)
from football_betting_lab.leagues import NFL
from football_betting_lab.markets import MARKETS_BY_KEY
from football_betting_lab.staging_provider_policy import (
    POLICY_FILENAME,
    RECEIPTS_DIRNAME,
    StagingProviderPolicy,
)

# Imported as a top-level module, which is how pytest's prepend import mode
# puts `tests/` on the path. `from tests.…` would depend on the repository
# root being importable, which `PYTHONSAFEPATH=1` on the CI suite line is
# there to prevent.
from test_github_approval import (  # noqa: F401 - shared builders
    HEAD,
    PR,
    REVIEWER,
    SCOPE,
    _activity,
    _body,
    _checkout,
    _paths,
    _policy,
    _run_git,
)


SCRIPTS = PROJECT_ROOT / "scripts"
TRANSCRIBER = SCRIPTS / "create_receipt_from_github_approval.py"
GATE = SCRIPTS / "check_provider_policy_pr_gate.py"


def _moments() -> tuple[datetime, datetime, datetime, datetime]:
    """Now, the approval, the head commit and the evidence commit.

    Anchored to the real clock because the entry point reads it: a fixture
    dated 2026 would be stale against a window measured in hours.
    """
    now = datetime.now(timezone.utc)
    return now, now - timedelta(hours=1), now - timedelta(hours=2), now - timedelta(hours=3)


def _approval(tmp_path: Path, **overrides) -> tuple[dict, Path]:
    now, approved, head_at, evidence_at = _moments()
    repo = _checkout(tmp_path, evidence_at=evidence_at, **overrides)
    approval = verify_github_approval(
        _activity(submitted=approved, head_committed_at=head_at),
        pr_number=PR,
        league=NFL,
        now=now,
        **_paths(repo),
    )
    return approval, repo


# -- the receipt ------------------------------------------------------------


def test_a_verified_approval_becomes_a_receipt(tmp_path: Path) -> None:
    approval, _ = _approval(tmp_path)

    receipt = build_receipt(approval)

    assert receipt["kind"] == RECEIPT_KIND
    assert receipt["decision"] == APPROVAL_DECISION
    assert receipt["reviewer_github_login"] == REVIEWER
    assert receipt["policy_key"] == NFL.policy_key()
    assert receipt["approved_markets"] == sorted(SCOPE)
    assert receipt["github_approval"]["head_sha"] == HEAD


def test_the_receipt_id_is_the_digest_of_the_act_not_a_choice(tmp_path: Path) -> None:
    """A chosen id is a receipt anybody can name in a policy entry."""
    approval, _ = _approval(tmp_path)

    first = build_receipt(approval)["receipt_id"]
    second = build_receipt(dict(approval))["receipt_id"]
    other = build_receipt({**approval, "source_id": 111222})["receipt_id"]

    assert first == second
    assert first != other
    assert NFL.key in first and NFL.policy_provider_name in first


def test_a_receipt_cannot_be_built_from_a_handmade_dictionary() -> None:
    """The allow-list is read here as well as in the verifier, because the
    verifier can be bypassed simply by not calling it."""
    invented = {
        "decision": APPROVAL_DECISION,
        "approval_phrase": APPROVAL_PHRASE,
        "reviewer_github_login": "someone-who-asked-nicely",
        "pr_number": PR,
        "repository": "x/y",
        "policy_key": NFL.policy_key(),
        "provider_name": NFL.policy_provider_name,
        "league": NFL.key,
        "approved_markets": list(SCOPE),
    }

    with pytest.raises(ReceiptError, match="not an allowed reviewer"):
        build_receipt(invented)


def test_a_receipt_cannot_be_built_from_an_unverified_decision() -> None:
    with pytest.raises(ReceiptError, match="not a verified approval"):
        build_receipt({"decision": "looks_fine", "reviewer_github_login": REVIEWER})


def test_a_receipt_cannot_be_built_without_the_verifiers_own_stamp() -> None:
    with pytest.raises(ReceiptError, match="approval phrase"):
        build_receipt(
            {
                "decision": APPROVAL_DECISION,
                "reviewer_github_login": REVIEWER,
                "approval_phrase": "",
            }
        )


def test_the_receipt_reads_back_exactly_what_was_approved(tmp_path: Path) -> None:
    approval, _ = _approval(tmp_path)
    receipt = build_receipt(approval)

    path, created = write_receipt(receipt, receipts_dir=tmp_path / RECEIPTS_DIRNAME)

    assert created and path.is_file()
    assert read_receipt(path) == receipt


def test_a_second_transcription_of_one_approval_changes_nothing(
    tmp_path: Path,
) -> None:
    """The file is what the policy entry names and what anything downstream
    checksums. Re-running the gate must not move a byte of it."""
    approval, _ = _approval(tmp_path)
    receipts = tmp_path / RECEIPTS_DIRNAME
    path, _ = write_receipt(build_receipt(approval), receipts_dir=receipts)
    before = path.read_bytes()

    again, created = write_receipt(build_receipt(approval), receipts_dir=receipts)

    assert again == path and not created
    assert path.read_bytes() == before


def test_the_receipt_names_the_markets_it_withheld(tmp_path: Path) -> None:
    approval, _ = _approval(tmp_path)

    rendered = render_receipt(build_receipt(approval))

    assert "Markets NOT approved" in rendered
    for market in set(MARKETS_BY_KEY) - set(SCOPE):
        assert f"`{market}`" in rendered


def test_a_receipt_with_no_binding_block_is_refused(tmp_path: Path) -> None:
    handwritten = tmp_path / "handwritten.md"
    handwritten.write_text("# Receipt\n\nCooper said yes.\n", encoding="utf-8")

    with pytest.raises(ReceiptError, match="no `\\`\\`\\`json` binding block"):
        read_receipt(handwritten)


def test_a_receipt_whose_binding_is_not_a_receipt_is_refused(tmp_path: Path) -> None:
    forged = tmp_path / "forged.md"
    forged.write_text(
        "# Receipt\n\n```json\n{\"kind\": \"something_else\"}\n```\n", encoding="utf-8"
    )

    with pytest.raises(ReceiptError, match=RECEIPT_KIND):
        read_receipt(forged)


# -- the gate ---------------------------------------------------------------


def _gate(repo: Path, receipts: Path, *, pr: int | None = PR) -> subprocess.CompletedProcess:
    arguments = [
        sys.executable,
        str(GATE),
        "--policy",
        str(repo / "data" / "manual" / POLICY_FILENAME),
        "--receipts-dir",
        str(receipts),
        "--output-dir",
        str(repo / "data" / "outputs"),
    ]
    if pr is not None:
        arguments += ["--pr", str(pr)]
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(PROJECT_ROOT / "src")
    return subprocess.run(
        arguments, capture_output=True, text=True, env=environment, cwd=PROJECT_ROOT
    )


def _allowed_policy(receipt: dict, markets=SCOPE, **overrides) -> dict:
    entry = {
        "allowlist_status": "allowed",
        "approved_at": receipt["github_approval"]["approved_at"],
        "reviewer_name": receipt["reviewer_github_login"],
        "evidence_receipt_id": receipt["receipt_id"],
        "required_markets": list(markets),
    }
    entry.update(overrides)
    return {
        "allowed_provider_names": [NFL.policy_provider_name],
        "provider_allowlist_entries": {NFL.policy_key(): entry},
    }


def _signed(tmp_path: Path, **policy_overrides) -> tuple[Path, Path, dict]:
    """A checkout whose entry reads as allowed, with its receipt written."""
    approval, repo = _approval(tmp_path)
    receipt = build_receipt(approval)
    receipts = tmp_path / RECEIPTS_DIRNAME
    write_receipt(receipt, receipts_dir=receipts)
    policy = _allowed_policy(receipt, **policy_overrides)
    (repo / "data" / "manual" / POLICY_FILENAME).write_text(
        json.dumps(policy, indent=2), encoding="utf-8"
    )
    return repo, receipts, receipt


def test_the_gate_passes_when_nothing_is_proposed(tmp_path: Path) -> None:
    repo = _checkout(tmp_path, policy={"provider_allowlist_entries": {}})

    result = _gate(repo, tmp_path / RECEIPTS_DIRNAME)

    assert result.returncode == 0, result.stdout
    assert "PASS" in result.stdout


def test_the_gate_passes_a_proposal_that_allowlists_nothing(tmp_path: Path) -> None:
    """The open pull request on this repository is exactly this shape: sixty
    markets named, status `proposed`, no reviewer, no receipt. It allowlists
    nothing, so it is not a gate failure — and the gate prints the block that
    would approve it."""
    repo = _checkout(tmp_path, policy=_policy(tuple(sorted(MARKETS_BY_KEY))))

    result = _gate(repo, tmp_path / RECEIPTS_DIRNAME)

    assert result.returncode == 0, result.stdout
    assert "allowlists" in result.stdout
    assert APPROVAL_PHRASE in result.stdout
    assert f"league: {NFL.key}" in result.stdout


def test_the_gate_passes_a_signed_entry(tmp_path: Path) -> None:
    repo, receipts, receipt = _signed(tmp_path)

    result = _gate(repo, receipts)

    assert result.returncode == 0, result.stdout + result.stderr
    assert receipt["receipt_id"] in result.stdout


def test_the_gate_fails_an_allowed_entry_with_no_receipt_file(
    tmp_path: Path,
) -> None:
    repo, receipts, receipt = _signed(tmp_path)
    (receipts / f"{receipt['receipt_id']}.md").unlink()

    result = _gate(repo, receipts)

    assert result.returncode == 1
    assert "id pointing at nothing" in result.stdout


def test_the_gate_fails_when_the_policy_credits_someone_else(
    tmp_path: Path,
) -> None:
    """The reviewer is whoever GitHub reported. A policy file does not get a
    vote on that, and this is the edit that would give it one."""
    repo, receipts, _ = _signed(tmp_path, reviewer_name="Cooper Ross")

    result = _gate(repo, receipts)

    assert result.returncode == 1
    assert "does not get to name someone else" in result.stdout


def test_the_gate_fails_when_the_entry_widens_the_scope(tmp_path: Path) -> None:
    repo, receipts, _ = _signed(tmp_path, required_markets=[*SCOPE, "team_total"])

    result = _gate(repo, receipts)

    assert result.returncode == 1
    assert "disagree about the scope" in result.stdout


def test_the_gate_fails_when_the_receipt_id_was_chosen(tmp_path: Path) -> None:
    """A receipt renamed to an id somebody liked is a receipt that no
    approval hashes to."""
    repo, receipts, receipt = _signed(tmp_path, evidence_receipt_id="r-2026-week-1")
    (receipts / f"{receipt['receipt_id']}.md").rename(receipts / "r-2026-week-1.md")

    result = _gate(repo, receipts)

    assert result.returncode == 1
    assert "derived from the human act" in result.stdout


def test_the_gate_fails_when_the_receipt_is_for_another_pull_request(
    tmp_path: Path,
) -> None:
    repo, receipts, _ = _signed(tmp_path)

    result = _gate(repo, receipts, pr=PR + 1)

    assert result.returncode == 1
    assert "not transferable" in result.stdout


def test_the_gate_fails_when_the_evidence_moved_after_the_approval(
    tmp_path: Path,
) -> None:
    repo, receipts, _ = _signed(tmp_path)
    report = repo / "data" / "outputs" / NFL.output_name(*REQUIRED_EVIDENCE_REPORT)
    report.write_text("# rebuilt after the signature\n", encoding="utf-8")

    result = _gate(repo, receipts)

    assert result.returncode == 1
    assert "evidence has changed" in result.stdout


def test_the_gate_fails_on_an_unreadable_policy(tmp_path: Path) -> None:
    repo, receipts, _ = _signed(tmp_path)
    (repo / "data" / "manual" / POLICY_FILENAME).write_text("{not json", encoding="utf-8")

    result = _gate(repo, receipts)

    assert result.returncode == 1
    assert "FAILED" in result.stdout


def test_a_gate_pass_and_the_policy_loader_agree(tmp_path: Path) -> None:
    """The gate is not a second opinion: what it passes is what the card's own
    loader will read as allowed."""
    repo, receipts, _ = _signed(tmp_path)
    manual = repo / "data" / "manual"
    (manual / RECEIPTS_DIRNAME).mkdir(parents=True, exist_ok=True)
    for path in receipts.iterdir():
        (manual / RECEIPTS_DIRNAME / path.name).write_bytes(path.read_bytes())

    policy = StagingProviderPolicy.load(
        path=manual / POLICY_FILENAME, manual_dir=manual
    )

    assert _gate(repo, receipts).returncode == 0
    assert sorted(policy.allowed_markets(NFL)) == sorted(SCOPE)


# -- the entry point --------------------------------------------------------


def _fake_gh(tmp_path: Path, activity: dict) -> Path:
    """A `gh` that answers the four API calls and nothing else."""
    fixtures = tmp_path / "api"
    fixtures.mkdir(exist_ok=True)
    (fixtures / "pull.json").write_text(
        json.dumps({"head": {"sha": activity["head_sha"]}}), encoding="utf-8"
    )
    (fixtures / "reviews.json").write_text(
        json.dumps(activity["reviews"]), encoding="utf-8"
    )
    (fixtures / "comments.json").write_text(
        json.dumps(activity["comments"]), encoding="utf-8"
    )
    (fixtures / "commits.json").write_text(
        json.dumps(
            [{"commit": {"committer": {"date": activity["head_committed_at"]}}}]
        ),
        encoding="utf-8",
    )
    binaries = tmp_path / "bin"
    binaries.mkdir(exist_ok=True)
    script = binaries / "gh"
    script.write_text(
        "#!/usr/bin/env python3\n"
        "import pathlib, sys\n"
        f"fixtures = pathlib.Path({str(fixtures)!r})\n"
        "target = sys.argv[2] if len(sys.argv) > 2 else ''\n"
        "name = ('reviews.json' if target.endswith('/reviews')\n"
        "        else 'comments.json' if target.endswith('/comments')\n"
        "        else 'commits.json' if target.endswith('/commits')\n"
        "        else 'pull.json')\n"
        "sys.stdout.write((fixtures / name).read_text())\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
    return binaries


def _transcribe(
    repo: Path, receipts: Path, binaries: Path, *extra: str
) -> subprocess.CompletedProcess:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(PROJECT_ROOT / "src")
    environment["PATH"] = f"{binaries}{os.pathsep}{environment['PATH']}"
    return subprocess.run(
        [
            sys.executable,
            str(TRANSCRIBER),
            "--pr",
            str(PR),
            "--repository",
            "cooperross399/football-betting-lab",
            "--policy",
            str(repo / "data" / "manual" / POLICY_FILENAME),
            "--output-dir",
            str(repo / "data" / "outputs"),
            "--repo-root",
            str(repo),
            "--receipts-dir",
            str(receipts),
            *extra,
        ],
        capture_output=True,
        text=True,
        env=environment,
        cwd=PROJECT_ROOT,
    )


def test_the_entry_point_transcribes_a_real_approval(tmp_path: Path) -> None:
    now, approved, head_at, evidence_at = _moments()
    repo = _checkout(tmp_path, evidence_at=evidence_at)
    activity = _activity(submitted=approved, head_committed_at=head_at)
    receipts = tmp_path / RECEIPTS_DIRNAME

    result = _transcribe(repo, receipts, _fake_gh(tmp_path, activity), "--write-receipt")

    assert result.returncode == 0, result.stdout + result.stderr
    written = sorted(receipts.glob("*.md"))
    assert len(written) == 1
    assert read_receipt(written[0])["reviewer_github_login"] == REVIEWER


def test_the_entry_point_writes_nothing_for_an_author_off_the_allow_list(
    tmp_path: Path,
) -> None:
    """The one test that would matter if every other check were removed."""
    now, approved, head_at, evidence_at = _moments()
    repo = _checkout(tmp_path, evidence_at=evidence_at)
    activity = _activity(
        author="not-cooper", submitted=approved, head_committed_at=head_at
    )
    receipts = tmp_path / RECEIPTS_DIRNAME

    result = _transcribe(repo, receipts, _fake_gh(tmp_path, activity), "--write-receipt")

    assert result.returncode == 2
    assert "BLOCKED" in result.stdout
    assert not receipts.exists()


def test_the_entry_point_writes_nothing_without_being_asked(tmp_path: Path) -> None:
    now, approved, head_at, evidence_at = _moments()
    repo = _checkout(tmp_path, evidence_at=evidence_at)
    activity = _activity(submitted=approved, head_committed_at=head_at)
    receipts = tmp_path / RECEIPTS_DIRNAME

    result = _transcribe(repo, receipts, _fake_gh(tmp_path, activity))

    assert result.returncode == 0, result.stdout
    assert not receipts.exists()


def test_the_entry_point_prints_the_block_when_it_refuses(tmp_path: Path) -> None:
    """A refusal that does not say how to approve is a refusal nobody acts on."""
    now, approved, head_at, evidence_at = _moments()
    repo = _checkout(tmp_path, evidence_at=evidence_at)
    activity = _activity(
        body=_body(phrase="lgtm"), submitted=approved, head_committed_at=head_at
    )

    result = _transcribe(
        repo, tmp_path / RECEIPTS_DIRNAME, _fake_gh(tmp_path, activity), "--write-receipt"
    )

    assert result.returncode == 2
    assert APPROVAL_PHRASE in result.stdout
    assert f"pr: {PR}" in result.stdout


def test_the_template_the_entry_point_prints_is_the_proposed_scope(
    tmp_path: Path,
) -> None:
    everything = tuple(sorted(MARKETS_BY_KEY))
    repo = _checkout(tmp_path, policy=_policy(everything))

    result = _transcribe(
        repo, tmp_path / RECEIPTS_DIRNAME, _fake_gh(tmp_path, _activity()), "--print-template"
    )

    assert result.returncode == 0
    assert result.stdout.strip() == approval_template(
        PR, league=NFL, markets=everything
    )


# -- what no flag may do ----------------------------------------------------


def _options(script: Path) -> set[str]:
    """Every `--flag` the script's parser declares, read off its syntax tree."""
    tree = ast.parse(script.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        if not (isinstance(function, ast.Attribute) and function.attr == "add_argument"):
            continue
        for argument in node.args:
            if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                found.add(argument.value)
    return found


def test_no_flag_supplies_an_approval_or_a_reviewer() -> None:
    """The lab this came from took `--activity-json`, which reads the pull
    request's reviews from a file. A file is a thing a person can write, and
    the reviewer's login is a field in it — so that flag is a way to name
    yourself the approver. It was not ported, and this test is why it cannot
    come back by accident.
    """
    flags = _options(TRANSCRIBER) | _options(GATE)

    assert flags
    for forbidden in (
        "--activity-json",
        "--activity",
        "--reviewer",
        "--reviewer-name",
        "--allowed-reviewers",
        "--decision",
        "--offline",
        "--force",
        "--skip-verification",
        "--no-verify",
    ):
        assert forbidden not in flags, f"{forbidden} is a way to approve without GitHub"


def test_every_flag_is_a_path_a_number_or_a_league() -> None:
    """Stated positively, so a new flag has to be argued for rather than just
    not appear on a list of names somebody thought of."""
    allowed = {
        "--pr",
        "--repository",
        "--league",
        "--policy",
        "--output-dir",
        "--repo-root",
        "--receipts-dir",
        "--write-receipt",
        "--print-template",
    }

    assert _options(TRANSCRIBER) <= allowed
    assert _options(GATE) <= allowed


def test_the_transcriber_never_reads_an_environment_variable_for_identity() -> None:
    tree = ast.parse(TRANSCRIBER.read_text(encoding="utf-8"))
    names = [node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)]

    assert "environ" not in names and "getenv" not in names


def _not_a_transcription(path: Path) -> list[str]:
    """Every reason a file in the receipts directory is not a transcription."""
    problems: list[str] = []
    try:
        binding = read_receipt(path)
    except ReceiptError as exc:
        return [str(exc)]
    approval = binding.get("github_approval") or {}
    if binding.get("decision") != APPROVAL_DECISION:
        problems.append(f"{path.name}: decision {binding.get('decision')!r}")
    if str(binding.get("reviewer_github_login") or "").lower() not in {
        name.lower() for name in ALLOWED_REVIEWERS
    }:
        problems.append(f"{path.name}: reviewer off the allow-list")
    if receipt_id(approval) != binding.get("receipt_id"):
        problems.append(f"{path.name}: the id is not the digest of the approval")
    if path.stem != binding.get("receipt_id"):
        problems.append(f"{path.name}: the filename is not the receipt id")
    return problems


def test_this_repository_ships_no_receipt_that_no_approval_produced() -> None:
    """Every receipt on disk must read back as a transcription.

    Today there are none, and that is the correct state: nothing in this
    repository has been allowlisted. The day Cooper signs one, this test still
    holds — what it refuses is a file placed in that directory by hand, by a
    script, or by Claude, which is the shape a fabricated approval takes.
    """
    directory = receipts_directory()
    receipts = sorted(directory.glob("*.md")) if directory.is_dir() else []

    problems = [problem for path in receipts for problem in _not_a_transcription(path)]

    assert problems == [], problems


def test_the_guard_above_is_not_vacuous(tmp_path: Path) -> None:
    """A scan over an empty directory reports green, so the rule is put to
    three files that a scan which had stopped working would also accept."""
    approval, _ = _approval(tmp_path)
    receipts = tmp_path / RECEIPTS_DIRNAME
    genuine, _ = write_receipt(build_receipt(approval), receipts_dir=receipts)

    handwritten = receipts / "r-2026-week-1.md"
    handwritten.write_text("# Receipt\n\nCooper approved this.\n", encoding="utf-8")
    renamed = receipts / "an-id-i-liked.md"
    renamed.write_text(genuine.read_text(encoding="utf-8"), encoding="utf-8")
    reviewer_swapped = receipts / "swapped.md"
    binding = read_receipt(genuine)
    binding["reviewer_github_login"] = "someone-else"
    reviewer_swapped.write_text(
        "# Receipt\n\n```json\n" + json.dumps(binding) + "\n```\n",
        encoding="utf-8",
    )

    assert _not_a_transcription(genuine) == []
    assert _not_a_transcription(handwritten)
    assert _not_a_transcription(renamed)
    assert _not_a_transcription(reviewer_swapped)
