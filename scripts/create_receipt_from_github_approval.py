#!/usr/bin/env python3
"""Transcribe a GitHub approval into the provider human acceptance receipt.

    python scripts/create_receipt_from_github_approval.py --pr 54
    python scripts/create_receipt_from_github_approval.py --pr 54 --write-receipt
    python scripts/create_receipt_from_github_approval.py --pr 54 --print-template

The human act is a pull-request review or comment, authored by an account on
the allow-list in `src/football_betting_lab/github_approval.py`, carrying the
approval block. This command verifies that approval and writes it down. It
cannot author one: the reviewer's identity is read from GitHub's API response,
and nothing on this command line can supply it.

**There is no offline mode, and that is the point.** The lab this mechanism
came from accepted a `--activity-json` file in place of the API call, which
would let anyone with a text editor write `{"user": {"login": "..."}}` and
mint a receipt. It was not ported. Every flag below is a path, a pull request
number or a league key; none of them is an approval, and none of them relaxes
a check.

**And there is no PATH either.** `gh` is run from an absolute, trusted
location (`github_approval.resolve_gh`), never from whatever PATH offers. A
forty-line script called `gh` earlier on PATH used to answer every API call
this command makes, which is a receipt minted with no source change anywhere.

Without `--write-receipt` this verifies and writes nothing. It never prints a
credential, never places a bet, never edits the policy file and never enables
a schedule.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess

from football_betting_lab.github_approval import (
    GitHubApprovalError,
    approval_from_github,
    approval_template,
    proposed_markets,
    resolve_gh,
)
from football_betting_lab.human_acceptance_receipt import (
    ReceiptError,
    build_receipt,
    receipts_directory,
    write_receipt,
)
from football_betting_lab.leagues import DEFAULT_LEAGUE_KEY, league_for


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pr", type=int, required=True, help="Pull request number.")
    parser.add_argument(
        "--repository",
        default="",
        help="owner/name. Resolved from `gh repo view` when omitted.",
    )
    parser.add_argument(
        "--league",
        default=DEFAULT_LEAGUE_KEY,
        help="The league whose policy entry is being approved.",
    )
    parser.add_argument(
        "--policy",
        type=Path,
        help="The policy file whose proposed scope the approval must name.",
    )
    parser.add_argument(
        "--output-dir", type=Path, help="Where the evidence reports live."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        help="The checkout the evidence reports are committed in.",
    )
    parser.add_argument(
        "--receipts-dir",
        type=Path,
        help="Where the receipt is written. Defaults to the directory the "
        "policy loader reads.",
    )
    parser.add_argument(
        "--write-receipt",
        action="store_true",
        help="Write the receipt. Without this the command only verifies.",
    )
    parser.add_argument(
        "--print-template",
        action="store_true",
        help="Print the approval block to paste into GitHub, then exit.",
    )
    return parser.parse_args()


def resolve_repository(explicit: str) -> str:
    """The repository, from the flag or from `gh` at a trusted absolute path.

    `["gh", ...]` used to be resolved through PATH here too. A shim answering
    this call names the repository the API is then read from, so it is asked
    for by absolute path like every other call to the tool.
    """
    if explicit.strip():
        return explicit.strip()
    try:
        executable = resolve_gh()
    except GitHubApprovalError:
        return ""
    result = subprocess.run(
        [
            executable,
            "repo",
            "view",
            "--json",
            "nameWithOwner",
            "-q",
            ".nameWithOwner",
        ],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def main() -> int:
    args = parse_args()
    try:
        league = league_for(args.league)
    except KeyError as exc:
        print(f"BLOCKED: {exc}")
        return 2

    try:
        scope = proposed_markets(league, args.policy)
    except GitHubApprovalError as exc:
        print(f"BLOCKED: {exc}")
        return 2

    template = approval_template(args.pr, league=league, markets=scope)
    if args.print_template:
        print(template)
        return 0

    print("Football Betting Lab — receipt from a GitHub approval")
    print(
        "The approval is a review or comment by an allowed reviewer. This "
        "command verifies one and cannot author one."
    )
    print(f"Proposed scope on this pull request: {len(scope)} market(s).")

    repository = resolve_repository(args.repository)
    if not repository:
        print("BLOCKED: the repository could not be resolved. Pass --repository.")
        return 2

    try:
        # Fetched here, by the function that mints. There is no seam between
        # "what GitHub said" and "what was verified" for anything to sit in:
        # this call takes no activity, and the verifier's own mapping-shaped
        # entry point can no longer produce a receipt.
        verified = approval_from_github(
            pr_number=args.pr,
            repository=repository,
            league=league,
            policy_path=args.policy,
            output_dir=args.output_dir,
            repo_root=args.repo_root,
        )
    except GitHubApprovalError as exc:
        print(f"BLOCKED: {exc}")
        print()
        print("No receipt was written. To approve, paste this into a review")
        print("or a comment on the pull request:")
        print("---")
        print(template)
        print("---")
        return 2

    # A copy, for printing only. `build_receipt` is handed the verified object
    # itself, because a copy of its fields is a mapping like any other.
    approval = verified.as_dict()
    print(
        f"Approval found: {approval['source_kind']} by "
        f"{approval['reviewer_github_login']} at {approval['approved_at']} "
        f"({approval['approval_age_hours']}h ago)."
    )
    print(f"Pull request: {approval['repository']}#{approval['pr_number']}")
    print(f"Policy key: {approval['policy_key']}")
    print(f"Markets approved: {len(approval['approved_markets'])}")
    print(f"Markets not approved: {len(approval['markets_not_approved'])}")
    print(f"Evidence reports bound: {len(approval['evidence_checksums_sha256'])}")

    try:
        receipt = build_receipt(verified)
    except ReceiptError as exc:
        print(f"BLOCKED: {exc}")
        return 2

    print(f"Receipt id: {receipt['receipt_id']}")

    if not args.write_receipt:
        print()
        print("Verified only; nothing was written. Re-run with --write-receipt.")
        return 0

    directory = args.receipts_dir or receipts_directory()
    path, created = write_receipt(receipt, receipts_dir=directory)
    print(f"{'Wrote' if created else 'Already transcribed'}: {path}")
    print(
        "The policy entry must name this receipt id in `evidence_receipt_id` "
        "before any market reaches the card; that edit carries no authority "
        "on its own, because the gate re-reads this file."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
