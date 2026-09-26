"""The receipt, the gate, and the command that cannot sign on Cooper's behalf.

`tests/test_github_approval.py` covers the verification. This covers what is
done with a verified approval: the receipt it becomes, the gate that re-reads
that receipt on every policy change, and the command-line entry point — run
against a stubbed `gh` that is really executed, because the claim being tested
is "the reviewer comes from the API" and only running it proves that.

The entry point used to be run as a subprocess with the stub first on PATH.
That is no longer possible and the reason is the point: a `gh` earlier on PATH
is now refused rather than run, because answering four API calls from a
forty-line script is how a receipt was minted here with no edit to any tracked
file. `test_the_entry_point_refuses_a_gh_earlier_on_the_path` is that attack,
still run as a subprocess, now red. The rest drive `main()` in process with
the resolved binary patched — the stub is still a program and is still really
executed; what a test may do that PATH may not is say which program it is.

Every receipt written by this module is written into `tmp_path`. Nothing here
creates `data/manual/human_acceptance_receipts/`.
"""

from __future__ import annotations

import argparse
import ast
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest import mock

import pytest

from football_betting_lab import github_approval
from football_betting_lab.config import PROJECT_ROOT
from football_betting_lab.github_approval import (
    ALLOWED_REVIEWERS,
    APPROVAL_DECISION,
    APPROVAL_PHRASE,
    REQUIRED_EVIDENCE_REPORT,
    GitHubApprovalError,
    VerifiedApproval,
    approval_template,
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
    mint,
    recent_moments,
)


SCRIPTS = PROJECT_ROOT / "scripts"
TRANSCRIBER = SCRIPTS / "create_receipt_from_github_approval.py"
GATE = SCRIPTS / "check_provider_policy_pr_gate.py"


def _moments() -> tuple[datetime, datetime, datetime, datetime]:
    """Now, the approval, the head commit and the evidence commit.

    Anchored to the real clock because the entry point reads it: a fixture
    dated 2026 would be stale against a window measured in hours. Shared with
    `test_github_approval`, which needs the same anchoring for the same reason.
    """
    return recent_moments()


def _approval(tmp_path: Path, **overrides) -> tuple[VerifiedApproval, Path]:
    """A minted approval, which is the only kind a receipt can be built from.

    `verify_github_approval` is not called here any more. It returns a plain
    mapping, and a mapping proves nothing about where it came from — which is
    exactly why `build_receipt` stopped accepting one. The seam is a patched
    *fetch* inside `mint`, so what is exercised below is the real minting path.
    """
    now, approved, head_at, evidence_at = _moments()
    repo = _checkout(tmp_path, evidence_at=evidence_at, **overrides)
    approval = mint(
        _activity(submitted=approved, head_committed_at=head_at), repo
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
    fields = approval.as_dict()

    first = build_receipt(approval)["receipt_id"]
    second = receipt_id(fields)
    other = receipt_id({**fields, "source_id": 111222})

    assert first == second
    assert first != other
    assert NFL.key in first and NFL.policy_provider_name in first
    # ...and the digest is a function a gate may call on a mapping it read out
    # of a file. Building the receipt from that mapping is a different act,
    # and it is refused.
    with pytest.raises(ReceiptError, match="fetched from GitHub"):
        build_receipt(fields)


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


def _arguments(repo: Path, receipts: Path, *extra: str) -> list[str]:
    return [
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
    ]


def _load_script(script: Path):
    specification = importlib.util.spec_from_file_location(script.stem, script)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def _transcribe(
    repo: Path, receipts: Path, binaries: Path, *extra: str
) -> subprocess.CompletedProcess:
    """Run the entry point with the stubbed `gh` as the resolved binary.

    It used to be a subprocess with the stub first on PATH, and that stopped
    working on purpose: a `gh` earlier on PATH is now refused rather than run,
    because answering these four API calls from a forty-line script is how a
    receipt was minted with no edit to any tracked file. The stub is still a
    real program and is still really executed — the login the entry point
    prints still comes out of its JSON — but the module has to be told this is
    the binary, which is something only in-process code can do.

    Returns a CompletedProcess-shaped result so the assertions below read the
    same as they did.
    """
    module = _load_script(TRANSCRIBER)
    arguments = _arguments(repo, receipts, *extra)
    printed = io.StringIO()
    with mock.patch.object(
        github_approval, "resolve_gh", return_value=str(binaries / "gh")
    ), mock.patch.object(sys, "argv", arguments), redirect_stdout(printed):
        code = module.main()
    return subprocess.CompletedProcess(
        args=arguments, returncode=code, stdout=printed.getvalue(), stderr=""
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


# -- the nine, at the receipt and at the gate ------------------------------


def test_the_entry_point_refuses_a_gh_earlier_on_the_path(tmp_path: Path) -> None:
    """FINDING 1, end to end and as a real subprocess.

    This is the attack that needs no source change at all: a script called
    `gh` on PATH answers the four API calls, and the entry point transcribes
    whatever login it chose to report. It used to work — every other entry
    point test in this module was written on top of it — and it now fails
    closed, with nothing written.
    """
    now, approved, head_at, evidence_at = _moments()
    repo = _checkout(tmp_path, evidence_at=evidence_at)
    binaries = _fake_gh(tmp_path, _activity(submitted=approved, head_committed_at=head_at))
    receipts = tmp_path / RECEIPTS_DIRNAME
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(PROJECT_ROOT / "src")
    environment["PATH"] = f"{binaries}{os.pathsep}{environment['PATH']}"

    result = subprocess.run(
        [sys.executable, *_arguments(repo, receipts, "--write-receipt")],
        capture_output=True,
        text=True,
        env=environment,
        cwd=PROJECT_ROOT,
    )

    assert result.returncode == 2, result.stdout + result.stderr
    assert "earlier on PATH" in result.stdout
    assert not receipts.exists()


def test_a_receipt_cannot_be_minted_from_a_mapping_that_says_everything_right(
    tmp_path: Path,
) -> None:
    """FINDING 2 and 3, run together, because they are one attack.

    Every field the checks above read, spelled correctly, with an allowed
    reviewer: this mapping used to walk through `build_receipt` and
    `write_receipt` and leave a receipt file behind, with the verifier never
    called. Nothing about its contents gives it away — that is the point of
    the finding — so what is checked is where it came from.
    """
    forged = {
        "decision": APPROVAL_DECISION,
        "approval_phrase": APPROVAL_PHRASE,
        "reviewer_github_login": REVIEWER,
        "pr_number": PR,
        "repository": "cooperross399/football-betting-lab",
        "policy_key": NFL.policy_key(),
        "provider_name": NFL.policy_provider_name,
        "league": NFL.key,
        "approved_markets": list(SCOPE),
        "source_kind": "comment",
        "source_id": 424242,
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "evidence_checksums_sha256": {},
    }
    receipts = tmp_path / RECEIPTS_DIRNAME

    with pytest.raises(ReceiptError, match="fetched from GitHub"):
        build_receipt(forged)

    assert not receipts.exists()


def test_the_loader_reads_the_receipt_it_used_only_to_count(tmp_path: Path) -> None:
    """FINDING 9. `market_allowed()` stopped at `is_file()`.

    It never opened the file: not the reviewer, not the markets, not the
    checksums it prints. So any file with the right name, plus a hand-edited
    entry, made it return True — the read-time half of the mechanism agreeing
    to something the merge-time half would have refused.
    """
    manual = tmp_path / "manual"
    (manual / RECEIPTS_DIRNAME).mkdir(parents=True)
    (manual / RECEIPTS_DIRNAME / "an-id-i-liked.md").write_text(
        "# Receipt\n\nCooper approved this.\n", encoding="utf-8"
    )
    (manual / POLICY_FILENAME).write_text(
        json.dumps(
            {
                "allowed_provider_names": [NFL.policy_provider_name],
                "provider_allowlist_entries": {
                    NFL.policy_key(): {
                        "allowlist_status": "allowed",
                        "reviewer_name": REVIEWER,
                        "evidence_receipt_id": "an-id-i-liked",
                        "required_markets": ["moneyline"],
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    policy = StagingProviderPolicy.load(manual_dir=manual)

    assert not policy.market_allowed(NFL, "moneyline")
    assert "not a transcription" in policy.refusal_reason(NFL, "moneyline")


def test_the_loader_refuses_a_genuine_receipt_with_a_swapped_reviewer(
    tmp_path: Path,
) -> None:
    """FINDING 9. The binding block is text in a file anybody can edit."""
    approval, repo = _approval(tmp_path)
    receipt = build_receipt(approval)
    manual = repo / "data" / "manual"
    path, _ = write_receipt(receipt, receipts_dir=manual / RECEIPTS_DIRNAME)
    binding = read_receipt(path)
    binding["reviewer_github_login"] = "someone-else"
    path.write_text(
        "# Receipt\n\n```json\n" + json.dumps(binding) + "\n```\n", encoding="utf-8"
    )
    (manual / POLICY_FILENAME).write_text(
        json.dumps(_allowed_policy(receipt, reviewer_name="someone-else")),
        encoding="utf-8",
    )

    policy = StagingProviderPolicy.load(manual_dir=manual)

    assert not policy.market_allowed(NFL, SCOPE[0])
    assert "allow-list" in policy.refusal_reason(NFL, SCOPE[0])


def test_the_loader_refuses_a_market_the_entry_names_and_the_receipt_does_not(
    tmp_path: Path,
) -> None:
    """FINDING 9. `required_markets` is what somebody typed; the receipt is
    what was signed."""
    approval, repo = _approval(tmp_path)
    receipt = build_receipt(approval)
    manual = repo / "data" / "manual"
    write_receipt(receipt, receipts_dir=manual / RECEIPTS_DIRNAME)
    (manual / POLICY_FILENAME).write_text(
        json.dumps(
            _allowed_policy(receipt, markets=[*SCOPE, "team_total"])
        ),
        encoding="utf-8",
    )

    policy = StagingProviderPolicy.load(manual_dir=manual)

    assert policy.market_allowed(NFL, SCOPE[0])
    assert not policy.market_allowed(NFL, "team_total")
    assert "named by the policy entry and not by the receipt" in policy.refusal_reason(
        NFL, "team_total"
    )


def test_the_loader_refuses_when_the_evidence_moved_after_the_approval(
    tmp_path: Path,
) -> None:
    """FINDING 9. The checksums the receipt prints are re-checked, not read."""
    approval, repo = _approval(tmp_path)
    receipt = build_receipt(approval)
    manual = repo / "data" / "manual"
    write_receipt(receipt, receipts_dir=manual / RECEIPTS_DIRNAME)
    (manual / POLICY_FILENAME).write_text(
        json.dumps(_allowed_policy(receipt)), encoding="utf-8"
    )
    (repo / "data" / "outputs" / NFL.output_name(*REQUIRED_EVIDENCE_REPORT)).write_text(
        "# rebuilt after the signature\n", encoding="utf-8"
    )

    policy = StagingProviderPolicy.load(manual_dir=manual)

    assert not policy.market_allowed(NFL, SCOPE[0])
    assert "evidence has changed" in policy.refusal_reason(NFL, SCOPE[0])


def test_a_genuine_receipt_still_allows_exactly_what_it_names(
    tmp_path: Path,
) -> None:
    """The read-time check is a check, not a wall: the whole point is that a
    real transcription still reads as one."""
    approval, repo = _approval(tmp_path)
    receipt = build_receipt(approval)
    manual = repo / "data" / "manual"
    write_receipt(receipt, receipts_dir=manual / RECEIPTS_DIRNAME)
    (manual / POLICY_FILENAME).write_text(
        json.dumps(_allowed_policy(receipt)), encoding="utf-8"
    )

    policy = StagingProviderPolicy.load(manual_dir=manual)

    assert sorted(policy.allowed_markets(NFL)) == sorted(SCOPE)
    assert policy.refusal_reason(NFL, SCOPE[0]) == ""


def test_the_gate_fails_a_receipt_bound_to_part_of_the_evidence(
    tmp_path: Path,
) -> None:
    """FINDING 7 at the gate. Absent-locally and absent-from-the-approval used
    to compare equal, so a binding that covered four artifacts of six passed
    a check whose whole job is to notice that."""
    repo, receipts, receipt = _signed(tmp_path)
    path = receipts / f"{receipt['receipt_id']}.md"
    binding = read_receipt(path)
    dropped = sorted(binding["evidence_checksums_sha256"])[0]
    del binding["evidence_checksums_sha256"][dropped]
    path.write_text(
        "# Receipt\n\n```json\n" + json.dumps(binding) + "\n```\n", encoding="utf-8"
    )

    result = _gate(repo, receipts)

    assert result.returncode == 1
    assert "binds to no checksum" in result.stdout
