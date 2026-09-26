#!/usr/bin/env python3
"""Refuse a policy change that allowlists anything without a real approval.

    python scripts/check_provider_policy_pr_gate.py --pr 54

Step five of `docs/provider_allowlist_approval.md`. The policy loader already
refuses an entry that names a receipt id with no file behind it; this is the
half that runs in CI, where the question is not only "is there a file" but
"does that file record an approval **this** pull request actually received,
from an account on the allow-list, for exactly the markets the entry names".

Three outcomes, and only one of them is a failure:

* no entry for this league — nothing is allowlisted, nothing to check;
* an entry that is not a complete approval (a proposal, or a half-finished
  edit) — it allowlists nothing, and the gate says so and passes;
* an entry that reads as allowed — every binding below must hold, or the gate
  fails and the merge button stays grey.

A receipt cannot be written by this script, by any other script here, or by
Claude. It is written by `create_receipt_from_github_approval.py` out of a
verified GitHub approval, and by nothing else.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from football_betting_lab.config import MANUAL_DIR
from football_betting_lab.github_approval import (
    ALLOWED_REVIEWERS,
    APPROVAL_DECISION,
    GitHubApprovalError,
    approval_template,
    evidence_checksums,
    proposed_markets,
)
from football_betting_lab.human_acceptance_receipt import (
    ReceiptError,
    read_receipt,
    receipt_id,
    receipts_directory,
)
from football_betting_lab.leagues import DEFAULT_LEAGUE_KEY, League, league_for
from football_betting_lab.markets import MARKETS_BY_KEY
from football_betting_lab.staging_provider_policy import (
    AllowlistEntry,
    StagingProviderPolicy,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pr", type=int, help="The pull request the approval must name."
    )
    parser.add_argument("--league", default=DEFAULT_LEAGUE_KEY)
    parser.add_argument("--policy", type=Path, help="The policy file to read.")
    parser.add_argument(
        "--receipts-dir", type=Path, help="Where receipts are looked for."
    )
    parser.add_argument(
        "--output-dir", type=Path, help="Where the evidence reports live."
    )
    return parser.parse_args()


def check_entry(
    entry: AllowlistEntry,
    league: League,
    *,
    receipts_dir: Path,
    output_dir: Path | None,
    pr_number: int | None,
) -> list[str]:
    """Every reason this allowlist entry is not backed by a real approval."""
    problems: list[str] = []
    path = Path(receipts_dir) / f"{entry.evidence_receipt_id}.md"
    if not path.is_file():
        return [
            f"the entry names receipt `{entry.evidence_receipt_id}` and no "
            f"such file exists at {path}. An id pointing at nothing is not an "
            "approval"
        ]
    try:
        binding = read_receipt(path)
    except ReceiptError as exc:
        return [f"the receipt at {path} could not be read: {exc}"]

    approval = binding.get("github_approval")
    if not isinstance(approval, dict):
        return [
            f"the receipt at {path} records no GitHub approval, so nothing "
            "says a human signed it"
        ]

    if binding.get("decision") != APPROVAL_DECISION:
        problems.append(
            f"the receipt records decision {binding.get('decision')!r}, not "
            f"{APPROVAL_DECISION!r}"
        )
    if binding.get("policy_key") != league.policy_key():
        problems.append(
            f"the receipt covers `{binding.get('policy_key')}`, not "
            f"`{league.policy_key()}`. One receipt, one league"
        )
    if binding.get("provider_name") != league.policy_provider_name:
        problems.append(
            f"the receipt names provider `{binding.get('provider_name')}`, "
            f"not `{league.policy_provider_name}`"
        )

    login = str(binding.get("reviewer_github_login") or "").strip()
    if login.lower() not in {name.lower() for name in ALLOWED_REVIEWERS}:
        problems.append(
            f"the receipt's reviewer `{login or 'nobody'}` is not on the "
            "allow-list"
        )
    if entry.reviewer_name.strip().lower() != login.lower():
        problems.append(
            f"the policy credits `{entry.reviewer_name}` and the receipt "
            f"records `{login}`. The reviewer is whoever GitHub reported, and "
            "the policy does not get to name someone else"
        )

    approved = sorted(str(market) for market in binding.get("approved_markets") or [])
    required = sorted(entry.required_markets)
    if approved != required:
        problems.append(
            "the entry and the receipt disagree about the scope. In the "
            f"entry only: {sorted(set(required) - set(approved))}; in the "
            f"receipt only: {sorted(set(approved) - set(required))}"
        )
    unknown = sorted(set(required) - set(MARKETS_BY_KEY))
    if unknown:
        problems.append(
            f"the entry names market(s) the registry does not hold: {unknown}"
        )

    if pr_number is not None and int(approval.get("pr_number") or 0) != int(pr_number):
        problems.append(
            f"the receipt records an approval on PR "
            f"#{approval.get('pr_number')}, not PR #{pr_number}. An approval "
            "is not transferable between pull requests"
        )

    expected_id = receipt_id(approval)
    if expected_id != entry.evidence_receipt_id:
        problems.append(
            f"the receipt id `{entry.evidence_receipt_id}` is not the digest "
            f"of the approval it contains (`{expected_id}`). A receipt id is "
            "derived from the human act, not chosen"
        )

    stored = dict(binding.get("evidence_checksums_sha256") or {})
    current = evidence_checksums(league, output_dir)
    moved = sorted(
        name
        for name in set(stored) | set(current)
        if stored.get(name) != current.get(name)
    )
    if moved:
        problems.append(
            f"the evidence has changed since the approval: {moved}. The "
            "reviewer signed a state, and the state moved"
        )
    return problems


def main() -> int:
    args = parse_args()
    try:
        league = league_for(args.league)
    except KeyError as exc:
        print(f"Provider Policy PR Gate FAILED: {exc}")
        return 1

    manual_dir = Path(args.policy).parent if args.policy else MANUAL_DIR
    policy = StagingProviderPolicy.load(path=args.policy, manual_dir=manual_dir)
    print(f"## Provider Policy PR Gate — {league.policy_key()}")
    print()

    if policy.load_error:
        print(f"FAILED: {policy.load_error} A policy that cannot be read is")
        print("not a policy that allows nothing by accident — it is a gate")
        print("with nothing behind it.")
        return 1

    entry = policy.entry_for(league)
    if entry is None:
        print("PASS: the policy holds no entry for this league, so nothing is")
        print("allowlisted and there is no approval to check.")
        return 0

    print(f"Entry status: `{entry.status or '(none)'}`")
    print(f"Markets named: {len(entry.required_markets)}")
    print()

    if not entry.is_allowed:
        print("PASS: the entry is not a complete approval, so it allowlists")
        print("nothing. `market_allowed()` returns False for every market it")
        print("names. Four acts remain, and all four are Cooper's: sign in")
        print("GitHub, let the gate transcribe the receipt, name that receipt")
        print("id in the entry, and set the status.")
        print()
        try:
            scope = proposed_markets(league, args.policy)
        except GitHubApprovalError as exc:
            print(f"The proposed scope could not be read: {exc}")
            return 0
        if args.pr is None:
            print("Re-run with --pr to print the block that would approve it.")
            return 0
        print("To approve, paste this into a review or a comment:")
        print()
        print("```text")
        print(approval_template(args.pr, league=league, markets=scope))
        print("```")
        return 0

    receipts_dir = args.receipts_dir or receipts_directory(manual_dir)
    problems = check_entry(
        entry,
        league,
        receipts_dir=receipts_dir,
        output_dir=args.output_dir,
        pr_number=args.pr,
    )
    if problems:
        print("FAILED: this entry reads as allowed and is not backed by a")
        print("verified approval:")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print(f"PASS: receipt `{entry.evidence_receipt_id}` records a GitHub")
    print(f"approval by `{entry.reviewer_name}` for exactly the")
    print(f"{len(entry.required_markets)} market(s) this entry names, bound to")
    print("evidence that has not moved since.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
