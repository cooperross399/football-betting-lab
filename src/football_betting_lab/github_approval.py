"""The human acceptance receipt is transcribed from GitHub, never typed.

## Why this exists

A receipt allowlists a market (`staging_provider_policy.py`, step six of
`docs/provider_allowlist_approval.md`). Producing one used to mean typing a
reviewer name into a command, and a typed name attests to nothing: whoever
runs the command types it. The name in the record is then a claim about a
human act rather than a trace of one.

This module takes the attestation from GitHub instead. A pull-request review
or comment, authored by an account on an explicit allow-list and carrying an
approval block, **is** the human act. The automation verifies it and
transcribes it. It cannot author it, because the author's identity is read out
of GitHub's API response and from nowhere else — not an argument, not a
configuration field, not `git config user.name`, not the `reviewer_name`
already written in the policy file. There is no flag, no environment variable
and no argument that produces a receipt without one, and none was ported from
the lab this came from.

## What binds an approval

An approval that merely said the phrase would bind to whatever the repository
happened to hold when it was read. So the comment declares what it approves
and every declaration is checked against something the comment cannot change:

* `pr:` against the pull request being verified;
* `provider:` against the league registry's provider name;
* `league:` against the league being verified, because a receipt covers one
  league and approving a market in one never approves it in another;
* `markets:` against **the scope this pull request proposes** — read from the
  policy file at the checked-out head — and against the market registry,
  which is the only source of a market this lab can price and settle.

Widening and narrowing are both refused. An approval is not a direction of
travel, it is a scope.

## What fails closed

All of it. No approval phrase, an author off the allow-list, a body naming
another pull request, activity fetched for another pull request, another
provider, another league, a market the registry does not hold, a scope that
is not exactly the proposed one, a review of a superseded commit, a head
commit pushed after the approval, evidence modified or re-committed after the
approval, an approval older than the freshness window or dated in the future,
a policy file that is missing, unreadable, malformed or holds no entry for
this league — every one of them raises. Nothing returns a partial result, so
no caller can mistake an unverified approval for a verified one.

## What was added after the mechanism was attacked

Nine ways to mint a receipt without a signature were found in the lab this was
ported from, and six of them were live here. Five are closed in this file:

* the `gh` this module runs is named, not searched for (`resolve_gh`). A
  script called `gh` earlier on PATH used to answer every call below;
* a review's **state** is checked. `DISMISSED`, `CHANGES_REQUESTED`,
  `PENDING`, `COMMENTED` and `""` all used to verify;
* `REVOCATION_PHRASE` withdraws an approval, and the newest word wins. There
  was no way to say no;
* an approval phrase that appears only inside a quoted block is not a fresh
  approval (`unquoted_lines`). "REVOKED. Ignore this: > APPROVED..." used to
  parse as one, newer than the approval it was quoting;
* the evidence bundle must be **complete** (`check_evidence_complete`). A
  missing report used to narrow the binding in silence.

The sixth is the seam itself: `verify_github_approval` takes an activity
mapping, and a mapping proves nothing about where it came from. It stays, for
tests, and it can no longer produce a receipt. `approval_from_github` fetches
its own activity and mints a `VerifiedApproval`, which is the only thing
`human_acceptance_receipt.build_receipt` will build a file from.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any

from football_betting_lab.config import (
    OUTPUTS_DIR,
    PROJECT_ROOT,
    STAGING_PROVIDER_POLICY_PATH,
)
from football_betting_lab.leagues import League
from football_betting_lab.markets import MARKETS_BY_KEY


#: The token that marks a review or comment as an approval. Deliberately ugly
#: and deliberately shouted: nobody types it by accident, and it does not
#: appear in a sentence somebody meant as a remark.
APPROVAL_PHRASE = "APPROVED_FOR_ALLOWLIST_PR"

#: The token that withdraws an approval. Without one, "the newest comment
#: carrying the approval phrase" is the reviewer's last word forever: a later
#: "I withdraw that" is invisible to a parser looking for a phrase it does not
#: contain. This is the phrase that says no, and it wins whenever it is newer.
REVOCATION_PHRASE = "REVOKED_FOR_ALLOWLIST_PR"

#: The one review state that is an approval. GitHub reports the others for
#: reviews that were withdrawn (`DISMISSED`), that asked for changes, that were
#: never submitted (`PENDING`), or that were remarks (`COMMENTED`) — and a
#: review GitHub itself says was withdrawn is not a signature.
ACCEPTED_REVIEW_STATE = "APPROVED"

#: Named rather than left to "anything else": a state this module has not heard
#: of is refused too, but these are the ones that were measured verifying.
REFUSED_REVIEW_STATES: tuple[str, ...] = (
    "DISMISSED",
    "CHANGES_REQUESTED",
    "PENDING",
    "COMMENTED",
)

#: The name of the GitHub CLI. Never invoked by this name alone: a bare
#: `["gh", ...]` is resolved through PATH, and PATH is the cheapest thing on
#: this machine to change. See `resolve_gh`.
GH_EXECUTABLE_NAME = "gh"

#: Where a real `gh` lives. An allow-list of absolute paths rather than a
#: search, because the search is the hole: a forty-line script called `gh`
#: earlier on PATH answers every API call this module makes, with no edit to
#: any file here. Writing to one of these locations is writing to the system,
#: which is a different act from setting a variable.
TRUSTED_GH_PATHS: tuple[str, ...] = (
    "/opt/homebrew/bin/gh",
    "/usr/local/bin/gh",
    "/usr/bin/gh",
    "/bin/gh",
    "/home/linuxbrew/.linuxbrew/bin/gh",
    "/snap/bin/gh",
)

#: The accounts whose approval this mechanism will transcribe. A tuple, but
#: deliberately a short one, and read from here rather than taken as an
#: argument — a parameter that names the allowed reviewers is a parameter that
#: names a new one.
ALLOWED_REVIEWERS: tuple[str, ...] = ("cooperross399",)

#: How long an approval stays usable. Not a parameter and not a command-line
#: flag: a window that can be widened at the call site is not a window.
MAX_APPROVAL_AGE_HOURS = 72.0

#: How far into the future a timestamp may sit before it is a forgery rather
#: than a clock a little out of step.
MAXIMUM_CLOCK_SKEW = timedelta(minutes=15)

#: The evidence a receipt is bound to, by report stem and suffix. The bundle
#: is step four of `docs/provider_allowlist_approval.md` — the artifact a
#: human actually reads — and the rest are the measurements it rests on. Each
#: is named per league by `League.output_name`, so one league's approval can
#: never be bound to another league's evidence.
EVIDENCE_REPORTS: tuple[tuple[str, str], ...] = (
    ("allowlist_evidence", ".md"),
    ("provider_shadow", ".md"),
    ("slate_coverage", ".md"),
    ("retention_probe", ".json"),
    ("settlement_agreement", ".md"),
    ("null_baseline", ".md"),
    ("props_backtest", ".md"),
    ("team_ladder_backtest", ".md"),
)

#: The one report that must be present. Without the reviewable bundle there is
#: nothing for a human to have reviewed, so an approval binds to nothing and
#: is refused rather than transcribed against whatever else happens to exist.
REQUIRED_EVIDENCE_REPORT = ("allowlist_evidence", ".md")

#: What a verified approval decides. One value, so a receipt cannot record a
#: decision this flow never makes.
APPROVAL_DECISION = "approved_for_allowlist_pr"


class GitHubApprovalError(RuntimeError):
    """An approval could not be verified. Always raised, never returned."""


def _clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def _parse_time(value: object) -> datetime | None:
    text = _clean(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


# --------------------------------------------------------------------------
# Reading GitHub. The only source of a reviewer's identity.
# --------------------------------------------------------------------------


def _is_executable_file(candidate: str) -> bool:
    path = Path(candidate)
    return path.is_file() and os.access(path, os.X_OK)


def resolve_gh() -> str:
    """The absolute path of the real `gh`, or a refusal.

    `subprocess.run(["gh", ...])` asks PATH which program to run, and PATH is
    the cheapest thing on this machine to change. A script called `gh` placed
    earlier on it answers every call in `fetch_pr_activity` — exit 0, JSON on
    stdout, a login of its choosing — and defeats this whole mechanism with no
    edit to any tracked file. That attack was run against this lab and it
    worked, which is why the binary is now named rather than searched for.

    Three things have to hold, and each one refuses on its own:

    * the program sits at one of `TRUSTED_GH_PATHS`, absolute and system-owned;
    * PATH, if it offers a `gh` at all, offers that same one — a different one
      earlier on PATH is not ignored, it is reported, because it is the attack
      and a silent fallback would let it keep being tried;
    * the program answers `--version` the way the GitHub CLI does.

    None of this stops somebody who can write to `/usr/bin`. It stops
    everything that only needs to write a file and set a variable, which is
    the threat this mechanism exists for.
    """
    # The shim first, because it is the loudest thing that can be true and
    # because reporting it does not depend on a real `gh` being installed.
    on_path = shutil.which(GH_EXECUTABLE_NAME)
    resolved = str(Path(on_path)) if on_path else ""
    if resolved and resolved not in TRUSTED_GH_PATHS:
        raise GitHubApprovalError(
            f"PATH offers a GitHub CLI at `{resolved}`, which is not one of "
            f"the trusted locations {list(TRUSTED_GH_PATHS)}. A program called "
            "`gh` earlier on PATH is exactly how this mechanism is defeated "
            "without changing a line of it, so this is a refusal rather than "
            "a fallback."
        )

    trusted = [path for path in TRUSTED_GH_PATHS if _is_executable_file(path)]
    if not trusted:
        raise GitHubApprovalError(
            "No GitHub CLI was found at any trusted location "
            f"({list(TRUSTED_GH_PATHS)}). An approval is read from GitHub or "
            "it is not read at all; this command does not fall back to "
            "whatever PATH happens to offer."
        )
    chosen = resolved if resolved in trusted else trusted[0]

    target = Path(chosen).resolve()
    try:
        inside_repository = target.is_relative_to(Path(PROJECT_ROOT).resolve())
    except (OSError, ValueError):
        inside_repository = False
    if inside_repository:
        raise GitHubApprovalError(
            f"The GitHub CLI at `{chosen}` resolves to `{target}`, inside this "
            "repository. A tool the repository ships is a tool the repository "
            "controls, and it cannot be the source of an approval."
        )

    try:
        probe = subprocess.run(
            [chosen, "--version"], capture_output=True, text=True, timeout=30
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise GitHubApprovalError(
            f"The GitHub CLI at `{chosen}` could not be run: {exc}."
        ) from exc
    printed = (probe.stdout or "").strip()
    first_line = printed.splitlines()[0] if printed else ""
    if (
        probe.returncode != 0
        or not first_line.startswith("gh version")
        or "github.com/cli/cli" not in printed
    ):
        raise GitHubApprovalError(
            f"The program at `{chosen}` does not answer `--version` the way "
            f"the GitHub CLI does (it said {first_line[:60]!r}). It is not the "
            "tool this approval has to come through."
        )
    return chosen


def fetch_pr_activity(pr_number: int, *, repository: str) -> dict[str, Any]:
    """The pull request's reviews, comments, head and head commit time.

    Shells out to the `gh` that `resolve_gh` names — an absolute, trusted path,
    never the one PATH offers. It authenticates as whoever or whatever is
    running it. The result is plain data so the verifier can be tested without
    a network, but note that nothing in the command line reaches this function:
    the CLI has no way to supply activity from a file, because a file is a
    thing a person can write and an approval is not.
    """
    repository = _clean(repository)
    if not repository:
        raise GitHubApprovalError("A repository in owner/name form is required.")
    executable = resolve_gh()

    def api(path: str) -> Any:
        target = f"repos/{repository}/{path}"
        result = subprocess.run(
            [executable, "api", target, "--paginate"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise GitHubApprovalError(
                f"The GitHub API call for `{target}` failed: "
                f"{result.stderr.strip()[:200]}"
            )
        try:
            return json.loads(result.stdout or "[]")
        except json.JSONDecodeError as exc:
            raise GitHubApprovalError(
                f"The GitHub API returned unreadable JSON for `{target}`."
            ) from exc

    pull = api(f"pulls/{pr_number}")
    reviews = api(f"pulls/{pr_number}/reviews")
    comments = api(f"issues/{pr_number}/comments")
    commits = api(f"pulls/{pr_number}/commits")
    head = pull.get("head", {}) if isinstance(pull, Mapping) else {}
    committed_at = ""
    if isinstance(commits, list) and commits and isinstance(commits[-1], Mapping):
        commit = commits[-1].get("commit")
        if isinstance(commit, Mapping):
            committer = commit.get("committer")
            if isinstance(committer, Mapping):
                committed_at = _clean(committer.get("date"))
    return {
        "pr_number": int(pr_number),
        "repository": repository,
        "head_sha": _clean(head.get("sha")),
        "head_committed_at": committed_at,
        "reviews": reviews if isinstance(reviews, list) else [],
        "comments": comments if isinstance(comments, list) else [],
    }


def _candidate_entries(activity: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Reviews and comments, normalised into one shape.

    A comment counts as well as a review because a review cannot be left on
    one's own pull request, and Cooper opens most of them.
    """
    entries: list[dict[str, Any]] = []
    for review in activity.get("reviews") or []:
        if not isinstance(review, Mapping):
            continue
        user = review.get("user")
        entries.append(
            {
                "kind": "review",
                "author": _clean((user or {}).get("login") if isinstance(user, Mapping) else ""),
                "body": _clean(review.get("body")),
                "submitted_at": _clean(review.get("submitted_at")),
                "commit_id": _clean(review.get("commit_id")),
                "state": _clean(review.get("state")),
                "id": review.get("id"),
            }
        )
    for comment in activity.get("comments") or []:
        if not isinstance(comment, Mapping):
            continue
        user = comment.get("user")
        entries.append(
            {
                "kind": "comment",
                "author": _clean((user or {}).get("login") if isinstance(user, Mapping) else ""),
                "body": _clean(comment.get("body")),
                "submitted_at": _clean(comment.get("created_at")),
                "commit_id": "",
                "state": "",
                "id": comment.get("id"),
            }
        )
    return entries


def unquoted_lines(body: str) -> str:
    """The lines a comment's author wrote, with everything quoted removed.

    A line beginning `>` is GitHub's quotation marker: it is text being
    repeated, and repeating an approval is not giving one. This matters
    because `parse_approval_block` deliberately tolerates the marker — a
    reviewer pasting into a quoted reply should still be understood — and
    that tolerance is a forgery all by itself. Measured on this lab before the
    fix: a comment reading

        REVOKED. Ignore this:
        > APPROVED_FOR_ALLOWLIST_PR
        > pr: 54
        ...

    verified as a FRESH approval, newer than the real one, with the word
    REVOKED at the top of it. So the verifier reads the author's own lines and
    the parser keeps its tolerance for the lines that are one bullet or one
    stray marker away from being right.
    """
    return "\n".join(
        line
        for line in str(body or "").splitlines()
        if not line.strip().startswith(">")
    )


def parse_approval_block(body: str) -> dict[str, Any]:
    """The provider, league, markets and pull request an approval declares.

    Markdown bullets, blockquote markers and any capitalisation are tolerated,
    because the reviewer is typing into a comment box and GitHub will reflow
    what is pasted into a quoted reply.
    """
    declared: dict[str, Any] = {
        "provider": "",
        "league": "",
        "markets": [],
        "pr": None,
    }
    for raw_line in str(body or "").splitlines():
        line = raw_line.strip().lstrip("-*> ").strip()
        lowered = line.lower()
        if lowered.startswith("provider:"):
            declared["provider"] = line.split(":", 1)[1].strip().lower()
        elif lowered.startswith("league:"):
            declared["league"] = line.split(":", 1)[1].strip().lower()
        elif lowered.startswith("markets:"):
            values = line.split(":", 1)[1]
            declared["markets"] = [
                item.strip().lower()
                for item in values.replace(";", ",").split(",")
                if item.strip()
            ]
        elif lowered.startswith("pr:"):
            digits = "".join(
                character
                for character in line.split(":", 1)[1]
                if character.isdigit()
            )
            declared["pr"] = int(digits) if digits else None
    return declared


# --------------------------------------------------------------------------
# The reviewed scope: what this pull request proposes, not what it asks for.
# --------------------------------------------------------------------------


def proposed_markets(league: League, policy_path: Path | None = None) -> tuple[str, ...]:
    """The market scope the checked-out policy file proposes for one league.

    This is the scope an approval must name, and it is read from the pull
    request's own head rather than passed in, so the comment and the diff
    cannot disagree without the disagreement being visible.

    Every way of failing to read it raises. A policy that cannot be read
    allows nothing, and a scope that cannot be established is not an empty
    scope — it is an unanswered question.
    """
    target = Path(policy_path) if policy_path else STAGING_PROVIDER_POLICY_PATH
    if not target.is_file():
        raise GitHubApprovalError(
            f"No policy file at {target}. There is no proposed scope to "
            "approve, so nothing can be transcribed."
        )
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise GitHubApprovalError(
            f"The policy file at {target} could not be read: {exc}."
        ) from exc
    if not isinstance(payload, Mapping):
        raise GitHubApprovalError(
            f"The policy file at {target} is not a JSON object."
        )
    entries = payload.get("provider_allowlist_entries")
    if not isinstance(entries, Mapping):
        raise GitHubApprovalError(
            f"The policy file at {target} holds no "
            "`provider_allowlist_entries` object."
        )
    key = league.policy_key()
    entry = entries.get(key)
    if not isinstance(entry, Mapping):
        # Keyed `{provider}:{league}`. An entry under the bare provider name
        # is another lab's shape and must not be read as this league's scope.
        raise GitHubApprovalError(
            f"The policy file holds no entry for `{key}`. Entries present: "
            f"{sorted(str(name) for name in entries) or ['none']}. An "
            "approval covers one league, and an entry keyed for another one "
            "is not it."
        )
    markets = tuple(
        str(item).strip().lower()
        for item in (entry.get("required_markets") or [])
        if str(item).strip()
    )
    if not markets:
        raise GitHubApprovalError(
            f"The entry for `{key}` proposes no markets. An approval must "
            "have a scope to be an approval."
        )
    unknown = sorted(set(markets) - set(MARKETS_BY_KEY))
    if unknown:
        raise GitHubApprovalError(
            f"The entry for `{key}` proposes market(s) the registry does not "
            f"hold: {unknown}. A market this lab cannot price and settle "
            "cannot be approved, whatever a policy file names."
        )
    return markets


# --------------------------------------------------------------------------
# The evidence an approval is bound to.
# --------------------------------------------------------------------------


def evidence_paths(league: League, output_dir: Path | None = None) -> dict[str, Path]:
    outputs = Path(output_dir) if output_dir else OUTPUTS_DIR
    return {
        league.output_name(stem, suffix): outputs / league.output_name(stem, suffix)
        for stem, suffix in EVIDENCE_REPORTS
    }


def evidence_checksums(
    league: League, output_dir: Path | None = None
) -> dict[str, str]:
    """SHA-256 of every evidence report that is present, by file name."""
    checksums: dict[str, str] = {}
    for name, path in evidence_paths(league, output_dir).items():
        if not path.is_file():
            continue
        try:
            checksums[name] = sha256(path.read_bytes()).hexdigest()
        except OSError:
            continue
    return checksums


def check_evidence_complete(
    league: League, output_dir: Path | None = None
) -> dict[str, str]:
    """Every evidence report, present and readable, or a refusal.

    `evidence_checksums` returns what it found, which is the right answer to
    the question it is asked and the wrong one to build a binding on: a report
    that is absent is simply not in the table, so an approval silently binds to
    however many files happened to exist. Measured on the lab this came from:
    deleting two artifacts produced an approval bound to four of six, with no
    warning anywhere. A binding that narrows itself is not a binding.
    """
    paths = evidence_paths(league, output_dir)
    missing = sorted(name for name, path in paths.items() if not path.is_file())
    if missing:
        raise GitHubApprovalError(
            f"The evidence bundle is incomplete: {missing} is not present. An "
            "approval binds to every report this lab measures, and a report "
            "that is absent narrows the binding without saying so. Build the "
            "missing report and commit it, then approve on the whole bundle."
        )
    checksums = evidence_checksums(league, output_dir)
    unreadable = sorted(set(paths) - set(checksums))
    if unreadable:
        raise GitHubApprovalError(
            f"The evidence report(s) {unreadable} could not be read, so "
            "nothing can be bound to them. Unreadable evidence is refused, "
            "never skipped."
        )
    return checksums


def _git(arguments: list[str], repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_root), *arguments],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise GitHubApprovalError(
            f"`git {' '.join(arguments)}` failed in {repo_root}: "
            f"{result.stderr.strip()[:200]}. The evidence a receipt binds to "
            "has to be traceable to a commit; an untraceable one is refused, "
            "never assumed intact."
        )
    return result.stdout


def check_evidence_unchanged_since(
    moment: datetime,
    league: League,
    *,
    output_dir: Path | None = None,
    repo_root: Path | None = None,
) -> dict[str, str]:
    """Refuse evidence that moved after `moment`; return when each landed.

    Two ways it can have moved, and both are refused:

    * the file differs from the committed state, or is not committed at all —
      evidence regenerated in the workspace is evidence nobody reviewed in the
      pull request, whatever its content now says;
    * the commit that last touched it is newer than the approval — the
      reviewer approved a state, and the state changed underneath them.

    Measured against the commit record rather than a `generated_at` field,
    because the reports in this lab are rendered markdown and carry no
    timestamp of their own. A checksum with no provenance is a number, not
    evidence.
    """
    root = Path(repo_root) if repo_root else PROJECT_ROOT
    landed: dict[str, str] = {}
    for name, path in evidence_paths(league, output_dir).items():
        if not path.is_file():
            continue
        try:
            relative = path.resolve().relative_to(Path(root).resolve()).as_posix()
        except ValueError as exc:
            raise GitHubApprovalError(
                f"The evidence report {path} is not inside the repository at "
                f"{root}, so nothing can establish when it was reviewed."
            ) from exc
        status = _git(["status", "--porcelain", "--", relative], root).strip()
        if status:
            raise GitHubApprovalError(
                f"The evidence report `{name}` differs from its committed "
                f"state (`git status` says `{status[:40]}`). The approval was "
                "given on what the pull request holds, not on a file changed "
                "afterwards in the workspace."
            )
        stamp = _git(
            ["log", "-1", "--format=%cI", "--", relative], root
        ).strip()
        committed = _parse_time(stamp)
        if committed is None:
            raise GitHubApprovalError(
                f"No commit could be found for the evidence report `{name}`. "
                "Evidence with no commit behind it is not evidence a reviewer "
                "could have read."
            )
        if committed > moment:
            raise GitHubApprovalError(
                f"The evidence report `{name}` was committed at "
                f"{committed.isoformat()}, after the approval at "
                f"{moment.isoformat()}. Re-approve on the current evidence."
            )
        landed[name] = committed.isoformat()
    return landed


# --------------------------------------------------------------------------
# Verification.
# --------------------------------------------------------------------------


def verify_github_approval(
    activity: Mapping[str, Any],
    *,
    pr_number: int,
    league: League,
    policy_path: Path | None = None,
    output_dir: Path | None = None,
    repo_root: Path | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Verify one GitHub approval and return what it binds.

    Every parameter is a path, a clock or the thing being verified. None of
    them supplies a reviewer, a provider, a market scope or a decision: those
    come from GitHub, from the league registry, from the proposed policy and
    from this module, in that order, and a caller cannot substitute any of
    them.
    """
    moment = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    provider_name = league.policy_provider_name
    scope = set(proposed_markets(league, policy_path))

    activity_pr = activity.get("pr_number")
    if activity_pr is None:
        raise GitHubApprovalError(
            "The activity does not say which pull request it came from."
        )
    try:
        same_pull_request = int(activity_pr) == int(pr_number)
    except (TypeError, ValueError) as exc:
        raise GitHubApprovalError(
            f"The activity names PR {activity_pr!r}, which is not a pull "
            "request number."
        ) from exc
    if not same_pull_request:
        raise GitHubApprovalError(
            f"The activity is for PR #{activity_pr}, not PR #{pr_number}."
        )

    entries = [
        entry
        for entry in _candidate_entries(activity)
        if APPROVAL_PHRASE in entry["body"]
    ]
    if not entries:
        raise GitHubApprovalError(
            f"No review or comment on PR #{pr_number} contains "
            f"`{APPROVAL_PHRASE}`. There is no approval to transcribe."
        )

    allowed = {name.strip().lower() for name in ALLOWED_REVIEWERS}
    by_allowed = [entry for entry in entries if entry["author"].lower() in allowed]
    if not by_allowed:
        authors = sorted({entry["author"] for entry in entries if entry["author"]})
        raise GitHubApprovalError(
            f"`{APPROVAL_PHRASE}` is present on PR #{pr_number} but not from "
            f"an allowed reviewer. Authored by: {authors or ['unknown']}; "
            f"allowed: {sorted(allowed)}. Quoting the phrase is not signing it."
        )

    def submitted_key(entry: Mapping[str, Any]) -> datetime:
        return _parse_time(entry["submitted_at"]) or datetime.min.replace(
            tzinfo=timezone.utc
        )

    # The reviewer's latest word governs, and only that one is examined. An
    # earlier approval is not a fallback: if the most recent one is malformed
    # or names the wrong scope, that is what the reviewer last said and the
    # answer is a refusal, not a search back through the thread for something
    # that passes.
    by_allowed.sort(key=submitted_key, reverse=True)
    entry = by_allowed[0]

    submitted = _parse_time(entry["submitted_at"])
    if submitted is None:
        raise GitHubApprovalError("The approval carries no readable timestamp.")
    if submitted > moment + MAXIMUM_CLOCK_SKEW:
        raise GitHubApprovalError(
            f"The approval is dated {submitted.isoformat()}, in the future."
        )
    age_hours = (moment - submitted).total_seconds() / 3600.0
    if age_hours > MAX_APPROVAL_AGE_HOURS:
        raise GitHubApprovalError(
            f"The approval is stale: {age_hours:.1f}h old against a limit of "
            f"{MAX_APPROVAL_AGE_HOURS:.0f}h. Re-approve on the current "
            "evidence."
        )

    # The state GitHub reports for a review, checked rather than transcribed.
    # It used to be copied into the receipt and used for nothing, so a review
    # in state DISMISSED — one GitHub itself says was withdrawn — verified,
    # and so did CHANGES_REQUESTED, PENDING, COMMENTED and a state of "".
    # A comment carries no review state and is judged by its body alone.
    if entry["kind"] == "review":
        state = _clean(entry["state"]).upper()
        if state != ACCEPTED_REVIEW_STATE:
            unfamiliar = (
                ""
                if state in REFUSED_REVIEW_STATES
                else " — which is not a state this mechanism knows, and an "
                "unfamiliar state is refused rather than guessed at"
            )
            raise GitHubApprovalError(
                f"The most recent review by an allowed reviewer is in state "
                f"{state or '(none)'!r}, not {ACCEPTED_REVIEW_STATE!r}"
                f"{unfamiliar}. A review GitHub reports as anything else is "
                "not a signature, and a dismissed one is a signature GitHub "
                "says was withdrawn."
            )

    # A revocation that is newer than the approval wins. Without this, only
    # entries CARRYING THE APPROVAL PHRASE were ever looked at, so a later "I
    # withdraw that approval" was invisible and the withdrawn signature went on
    # verifying. Read liberally on purpose — the phrase anywhere in the body,
    # quoted or not — because the failure to prefer here is a refusal, and a
    # refusal is the safe way to be wrong.
    revocations = [
        candidate
        for candidate in _candidate_entries(activity)
        if candidate["author"].lower() in allowed
        and REVOCATION_PHRASE in candidate["body"]
    ]
    if revocations:
        # An undated revocation cannot be placed either side of the approval,
        # and "cannot be placed" is not "is older". Refused before the
        # comparison, because `max` by a sort key that reads an unreadable time
        # as the beginning of time would quietly rank it last.
        if any(_parse_time(item["submitted_at"]) is None for item in revocations):
            raise GitHubApprovalError(
                f"A `{REVOCATION_PHRASE}` from an allowed reviewer carries no "
                "readable timestamp, so nothing establishes whether it came "
                "before or after the approval. An unplaceable withdrawal is "
                "refused, never assumed to be the older word."
            )
        newest = max(revocations, key=submitted_key)
        revoked_at = _parse_time(newest["submitted_at"])
        if revoked_at is not None and revoked_at >= submitted:
            raise GitHubApprovalError(
                f"`{REVOCATION_PHRASE}` was posted by an allowed reviewer at "
                f"{revoked_at.isoformat()}, at or after the approval at "
                f"{submitted.isoformat()}. The reviewer's latest word governs, "
                "and the latest word is no."
            )

    # The author's own lines, not the ones they quoted. `parse_approval_block`
    # tolerates the `>` marker so a reviewer typing into a quoted reply is
    # still understood, and that tolerance turned a comment reading "REVOKED.
    # Ignore this: > APPROVED_FOR_ALLOWLIST_PR ..." into a fresh approval.
    own_words = unquoted_lines(entry["body"])
    if APPROVAL_PHRASE not in own_words:
        raise GitHubApprovalError(
            f"The most recent word from an allowed reviewer carries "
            f"`{APPROVAL_PHRASE}` only inside a quoted block. Quoting an "
            "approval is repeating it, not giving it. Paste the block "
            "unquoted to approve."
        )

    declared = parse_approval_block(own_words)

    if declared["pr"] is None:
        raise GitHubApprovalError(
            "The approval must declare `pr:` so it binds to one pull request."
        )
    if int(declared["pr"]) != int(pr_number):
        raise GitHubApprovalError(
            f"The approval names PR #{declared['pr']}, not PR #{pr_number}. "
            "An approval is not transferable between pull requests."
        )
    if not declared["provider"]:
        raise GitHubApprovalError(
            "The approval must declare `provider:` so it binds to one provider."
        )
    if declared["provider"] != provider_name.strip().lower():
        raise GitHubApprovalError(
            f"The approval names provider `{declared['provider']}`, but this "
            f"league's provider is `{provider_name}`."
        )
    if not declared["league"]:
        raise GitHubApprovalError(
            "The approval must declare `league:`. A receipt covers one "
            "league, and approving a market in one never approves it in "
            "another."
        )
    if declared["league"] != league.key.lower():
        raise GitHubApprovalError(
            f"The approval names league `{declared['league']}`, not "
            f"`{league.key}`. One receipt, one league."
        )
    if not declared["markets"]:
        raise GitHubApprovalError(
            "The approval must declare `markets:` so it binds to a scope. "
            "There is no shorthand for all of them."
        )

    granted = set(declared["markets"])
    unknown = sorted(granted - set(MARKETS_BY_KEY))
    if unknown:
        raise GitHubApprovalError(
            f"The approval names market(s) the registry does not hold: "
            f"{unknown}. The market registry is the only source of a market "
            "this lab can price and settle."
        )
    if granted != scope:
        raise GitHubApprovalError(
            "The approval does not name the scope this pull request "
            f"proposes. Named but not proposed: {sorted(granted - scope)}; "
            f"proposed but not named: {sorted(scope - granted)}. Widening and "
            "narrowing are both refused."
        )

    head_sha = _clean(activity.get("head_sha"))
    if entry["kind"] == "review":
        commit_id = _clean(entry["commit_id"])
        if head_sha and commit_id and head_sha != commit_id:
            raise GitHubApprovalError(
                "The review approved commit "
                f"{commit_id[:12]}, and the pull request now points at "
                f"{head_sha[:12]}. Re-approve the current head."
            )
    head_committed = _parse_time(activity.get("head_committed_at"))
    if head_committed is None:
        raise GitHubApprovalError(
            "The pull request's head commit has no readable timestamp, so "
            "nothing establishes whether it landed before or after the "
            "approval."
        )
    if head_committed > submitted:
        raise GitHubApprovalError(
            f"The head commit landed at {head_committed.isoformat()}, after "
            f"the approval at {submitted.isoformat()}. The reviewer approved "
            "a state that has since changed."
        )

    evidence_landed = check_evidence_unchanged_since(
        submitted, league, output_dir=output_dir, repo_root=repo_root
    )
    checksums = check_evidence_complete(league, output_dir)
    required = league.output_name(*REQUIRED_EVIDENCE_REPORT)
    if required not in checksums:
        raise GitHubApprovalError(
            f"The evidence bundle `{required}` is not present, so there is "
            "nothing an approval could have been given on."
        )

    return {
        "approval_phrase": APPROVAL_PHRASE,
        "decision": APPROVAL_DECISION,
        "pr_number": int(pr_number),
        "repository": _clean(activity.get("repository")),
        "reviewer_github_login": entry["author"],
        "source_kind": entry["kind"],
        "source_id": entry["id"],
        "review_state": entry["state"],
        "approved_at": submitted.isoformat(),
        "approval_age_hours": round(age_hours, 2),
        "head_sha": head_sha,
        "head_committed_at": head_committed.isoformat(),
        "reviewed_commit": _clean(entry["commit_id"]),
        "provider_name": provider_name,
        "league": league.key,
        "policy_key": league.policy_key(),
        "approved_markets": sorted(granted),
        # Named so the receipt records what was withheld as well as what was
        # given. A reader should not have to diff two lists to see it.
        "markets_not_approved": sorted(set(MARKETS_BY_KEY) - granted),
        "evidence_checksums_sha256": checksums,
        "evidence_committed_at": evidence_landed,
        "verified_at": moment.isoformat(),
    }


# --------------------------------------------------------------------------
# Minting: the only route from GitHub to a receipt.
# --------------------------------------------------------------------------


def _construction_token_holder():
    """The token that says "this module made this", held in a closure.

    Not a module attribute, so it is not something a caller can read off the
    module and pass in. The point is not that a token is unreachable from code
    running in this process — nothing in Python is — but that there is no
    *data* path to one: no argument, no file, no variable, no mapping.
    """
    token = object()

    def mint(fields: Mapping[str, Any]) -> "VerifiedApproval":
        return VerifiedApproval(token, dict(fields))

    def holds(candidate: object) -> bool:
        return candidate is token

    return mint, holds


@dataclass(frozen=True, eq=False)
class VerifiedApproval:
    """An approval this module fetched from GitHub and verified itself.

    `verify_github_approval` returns a plain mapping and always has. That is
    useful — it can be tested without a network — and it is exactly why a
    mapping must not be enough to mint a receipt: a fabricated one is
    indistinguishable from a fetched one, because a mapping carries no trace of
    where it came from. Measured on this lab before the fix: a hand-written
    dictionary naming `cooperross399` went straight through `build_receipt`
    and `write_receipt` and produced a receipt file, with the verifier never
    called at all.

    So this type exists, and it cannot be built from outside. The construction
    token is held in a closure by `_mint_verified_approval`, which is reached
    only through `approval_from_github` — the one function that fetches the
    pull request's activity itself and accepts none from a caller.
    """

    construction_token: object
    fields: dict[str, Any]

    def __post_init__(self) -> None:
        if not _holds_construction_token(self.construction_token):
            raise GitHubApprovalError(
                "A verified approval is minted by this module, when it has "
                "fetched a pull request's activity from GitHub and verified an "
                "approval in it. One built by hand is not one, whatever its "
                "fields say."
            )

    def as_dict(self) -> dict[str, Any]:
        """A copy of the verified fields. Mutating it changes nothing here."""
        return dict(self.fields)

    @property
    def reviewer_github_login(self) -> str:
        return str(self.fields.get("reviewer_github_login") or "")


_mint_verified_approval, _holds_construction_token = _construction_token_holder()


def approval_from_github(
    *,
    pr_number: int,
    repository: str,
    league: League,
    policy_path: Path | None = None,
    output_dir: Path | None = None,
    repo_root: Path | None = None,
) -> VerifiedApproval:
    """Fetch the pull request's activity and verify an approval in it.

    The receipt-producing path, and the only one. It takes no `activity`,
    because an activity a caller supplies is a mapping a caller wrote — the
    login is just a field in it. It takes no `now`, because a clock a caller
    supplies is a freshness window a caller widens. Every remaining parameter
    is a path, a number or a league.
    """
    activity = fetch_pr_activity(pr_number, repository=repository)
    fields = verify_github_approval(
        activity,
        pr_number=pr_number,
        league=league,
        policy_path=policy_path,
        output_dir=output_dir,
        repo_root=repo_root,
    )
    return _mint_verified_approval(fields)


def approval_template(
    pr_number: int, *, league: League, markets: tuple[str, ...] | list[str]
) -> str:
    """The exact text to paste into a review or comment.

    Printed by the gate when it finds no approval, so the scope in the block
    is the scope the pull request proposes rather than one typed from memory.
    """
    return "\n".join(
        [
            APPROVAL_PHRASE,
            f"pr: {pr_number}",
            f"provider: {league.policy_provider_name}",
            f"league: {league.key}",
            f"markets: {', '.join(markets)}",
        ]
    )


def policy_checksum(policy_path: Path | None = None) -> str:
    path = (
        STAGING_PROVIDER_POLICY_PATH
        if policy_path is None
        else Path(policy_path)
    )
    if not path.is_file():
        return ""
    try:
        return sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""
