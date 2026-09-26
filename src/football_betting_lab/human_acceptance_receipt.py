"""The receipt: a transcription of a human act, never a substitute for one.

`staging_provider_policy.py` will not let a market reach the card unless the
allowlist entry names a receipt id AND that receipt exists on disk, because
"an id pointing at nothing is the shape a fabricated approval takes". This
module is how such a file comes to exist, and it has exactly one input: a
`VerifiedApproval`, minted by `github_approval.approval_from_github` after it
has fetched the pull request's activity from GitHub itself.

It refuses to build anything from a dictionary. That is a change: a mapping
used to be enough, and a hand-written one naming an allowed reviewer produced
a receipt file with the verifier never called — measured, not supposed. The
decision, the approval phrase and the reviewer's GitHub login are all still
re-checked here against the same constants the verifier used, because two
readings of the allow-list is the point; what is new is that passing those
checks is no longer sufficient. A mapping carries no trace of where it came
from, so one that was typed and one that was fetched read identically.

## The id

Derived from the human act — pull request, repository, review or comment id,
author, timestamp, provider, league, market scope — and from nothing else.
Two consequences, both deliberate:

* transcribing the same approval twice produces the same id, so a re-run of
  the gate does not mint a second receipt for one signature;
* an id cannot be chosen. A receipt id in a policy entry that no approval
  hashes to is a receipt id that names nothing.

## The file

Markdown, because that is what the policy loader looks for and what a person
reads. The full binding is carried inside it in a fenced JSON block so the
gate can read back exactly what was approved rather than parse prose.
"""

from __future__ import annotations

from collections.abc import Mapping
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from football_betting_lab.config import MANUAL_DIR
from football_betting_lab.github_approval import (
    ALLOWED_REVIEWERS,
    APPROVAL_DECISION,
    APPROVAL_PHRASE,
    VerifiedApproval,
)
from football_betting_lab.staging_provider_policy import RECEIPTS_DIRNAME


#: The fence the binding is written inside, and the one the reader looks for.
BINDING_FENCE = "```json"

#: What this file is, recorded in the receipt so a reader of one file knows
#: what they are holding.
RECEIPT_KIND = "provider_human_acceptance_receipt"


class ReceiptError(RuntimeError):
    """A receipt could not be built, written or read back."""


def receipt_id(approval: Mapping[str, Any]) -> str:
    """A deterministic id for one human act.

    The digest covers the identity of the approval only — not the evidence
    checksums and not the verification time — so re-running the gate over an
    unchanged approval writes the same id, while a different signature, a
    different scope or a different pull request cannot collide with it.
    """
    identity = {
        "pr_number": int(approval.get("pr_number") or 0),
        "repository": str(approval.get("repository") or ""),
        "source_kind": str(approval.get("source_kind") or ""),
        "source_id": str(approval.get("source_id") or ""),
        "reviewer_github_login": str(approval.get("reviewer_github_login") or ""),
        "approved_at": str(approval.get("approved_at") or ""),
        "provider_name": str(approval.get("provider_name") or ""),
        "policy_key": str(approval.get("policy_key") or ""),
        "approved_markets": sorted(approval.get("approved_markets") or []),
    }
    digest = sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:12]
    stamp = str(approval.get("approved_at") or "")
    compact = "".join(
        character for character in stamp if character.isalnum()
    )[:15] or "undated"
    return f"{identity['provider_name']}-{approval.get('league', '')}-{compact}-{digest}"


def build_receipt(approval: "VerifiedApproval") -> dict[str, Any]:
    """Turn a verified approval into the receipt record.

    Takes a `VerifiedApproval` — the object `github_approval.approval_from_github`
    mints after fetching a pull request's activity from GitHub itself — and
    nothing else. A mapping is refused, and it is refused *last*, after every
    content check below has had its say, so the error a caller gets names the
    first thing actually wrong with what they handed over.

    A mapping used to be enough, and that was the whole hole: a hand-written
    dictionary naming an allowed reviewer produced a receipt file with the
    verifier never called. The content checks below stay regardless — the
    allow-list is read here as well as in the verifier, because two readings
    of it is the point — but passing them is no longer sufficient. Where the
    approval came from is now part of what is checked, and a mapping cannot
    answer that question about itself.
    """
    if isinstance(approval, VerifiedApproval):
        approval = approval.as_dict()
        minted = True
    elif isinstance(approval, Mapping):
        minted = False
    else:
        raise ReceiptError("A receipt is built from a verified approval, not from nothing.")
    if approval.get("decision") != APPROVAL_DECISION:
        raise ReceiptError(
            f"This is not a verified approval: its decision is "
            f"{approval.get('decision')!r}, not {APPROVAL_DECISION!r}."
        )
    if approval.get("approval_phrase") != APPROVAL_PHRASE:
        raise ReceiptError(
            "This is not a verified approval: it does not carry the approval "
            "phrase the verifier stamps into its result."
        )
    login = str(approval.get("reviewer_github_login") or "").strip()
    if login.lower() not in {name.lower() for name in ALLOWED_REVIEWERS}:
        raise ReceiptError(
            f"`{login or 'nobody'}` is not an allowed reviewer, so there is no "
            "human act here to transcribe."
        )
    for field in ("pr_number", "repository", "policy_key", "provider_name", "league"):
        if not str(approval.get(field) or "").strip():
            raise ReceiptError(f"The approval records no {field}; it binds to nothing.")
    if not approval.get("approved_markets"):
        raise ReceiptError("The approval grants no markets; there is nothing to receipt.")
    if not minted:
        raise ReceiptError(
            "This mapping is well-formed and it is still not an approval. A "
            "receipt is minted only from one this process fetched from GitHub "
            "and verified itself — `github_approval.approval_from_github`. A "
            "mapping carries no trace of where it came from, so one that was "
            "typed and one that was fetched read identically, which is why "
            "reading it is no longer enough."
        )

    record = {
        "kind": RECEIPT_KIND,
        "receipt_id": receipt_id(approval),
        "decision": APPROVAL_DECISION,
        "policy_key": str(approval["policy_key"]),
        "league": str(approval["league"]),
        "provider_name": str(approval["provider_name"]),
        "reviewer_github_login": login,
        "approved_markets": sorted(approval["approved_markets"]),
        "markets_not_approved": sorted(approval.get("markets_not_approved") or []),
        "github_approval": dict(approval),
        "evidence_checksums_sha256": dict(
            approval.get("evidence_checksums_sha256") or {}
        ),
    }
    return record


def render_receipt(receipt: Mapping[str, Any]) -> str:
    """The markdown the policy loader looks for and a person reads."""
    approval = receipt.get("github_approval") or {}
    lines = [
        f"# Provider human acceptance receipt — {receipt['policy_key']}",
        "",
        "**This records an approval; it does not make one.** The reviewer "
        "below is the author GitHub reported for the review or comment that "
        "carried the approval block. No argument, environment variable or "
        "configuration field can put a name here, and no flag produces this "
        "file without an approval from an account on the allow-list in "
        "`src/football_betting_lab/github_approval.py`.",
        "",
        f"- Receipt id: `{receipt['receipt_id']}`",
        f"- Decision: `{receipt['decision']}`",
        f"- Policy key: `{receipt['policy_key']}`",
        f"- Provider: `{receipt['provider_name']}`",
        f"- Reviewer (GitHub): `{receipt['reviewer_github_login']}`",
        f"- Pull request: `{approval.get('repository', '')}#{approval.get('pr_number', '')}`",
        f"- Approved by {approval.get('source_kind', '')} "
        f"`{approval.get('source_id', '')}` at `{approval.get('approved_at', '')}`",
        f"- Head commit: `{approval.get('head_sha', '')}`",
        f"- Transcribed at: `{approval.get('verified_at', '')}`",
        "",
        f"## Markets approved ({len(receipt['approved_markets'])})",
        "",
    ]
    lines.extend(f"- `{market}`" for market in receipt["approved_markets"])
    lines.extend(
        [
            "",
            f"## Markets NOT approved ({len(receipt['markets_not_approved'])})",
            "",
            "Named rather than left to a diff: what an approval withheld is "
            "part of what it said.",
            "",
        ]
    )
    lines.extend(f"- `{market}`" for market in receipt["markets_not_approved"])
    lines.extend(
        [
            "",
            "## Evidence this approval is bound to",
            "",
            "| Report | SHA-256 | Committed |",
            "|:-------|:--------|:----------|",
        ]
    )
    committed = approval.get("evidence_committed_at") or {}
    for name, checksum in sorted(receipt["evidence_checksums_sha256"].items()):
        lines.append(f"| `{name}` | `{checksum}` | `{committed.get(name, '')}` |")
    lines.extend(
        [
            "",
            "## The binding, verbatim",
            "",
            "Read by `scripts/check_provider_policy_pr_gate.py`. Editing it "
            "changes what the gate reads, not what was approved.",
            "",
            BINDING_FENCE,
            json.dumps(receipt, indent=2, sort_keys=True),
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def receipts_directory(manual_dir: Path | None = None) -> Path:
    return (Path(manual_dir) if manual_dir else MANUAL_DIR) / RECEIPTS_DIRNAME


def write_receipt(
    receipt: Mapping[str, Any], *, receipts_dir: Path
) -> tuple[Path, bool]:
    """Write the receipt. Returns its path and whether this call created it.

    An existing receipt for the same id is left exactly as it is. Re-running
    the gate over one approval must not move a byte of the record it already
    made, because the file is what the policy entry names and what anything
    downstream checksums.
    """
    directory = Path(receipts_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{receipt['receipt_id']}.md"
    if path.exists():
        return path, False
    path.write_text(render_receipt(receipt), encoding="utf-8")
    return path, True


def read_receipt(path: Path) -> dict[str, Any]:
    """The binding out of a receipt file, or a refusal.

    Deliberately strict. A receipt that cannot be read is not a receipt that
    might be fine.
    """
    target = Path(path)
    if not target.is_file():
        raise ReceiptError(f"No receipt at {target}.")
    try:
        text = target.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ReceiptError(f"The receipt at {target} could not be read: {exc}.") from exc
    start = text.find(BINDING_FENCE)
    if start < 0:
        raise ReceiptError(
            f"The receipt at {target} carries no `{BINDING_FENCE}` binding "
            "block, so nothing in it can be checked."
        )
    body = text[start + len(BINDING_FENCE):]
    end = body.find("```")
    if end < 0:
        raise ReceiptError(f"The binding block in {target} is not closed.")
    try:
        payload = json.loads(body[:end])
    except json.JSONDecodeError as exc:
        raise ReceiptError(
            f"The binding block in {target} is not readable JSON: {exc}."
        ) from exc
    if not isinstance(payload, dict) or payload.get("kind") != RECEIPT_KIND:
        raise ReceiptError(
            f"The binding block in {target} is not a {RECEIPT_KIND}."
        )
    return payload
