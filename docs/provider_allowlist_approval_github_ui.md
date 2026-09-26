# Approving from the GitHub UI

Step six of `docs/provider_allowlist_approval.md` — the human acceptance
receipt — is yours and nobody else's. This is the way to do it that takes one
comment and no terminal.

> **The approval is yours, not the automation's.** The reviewer's identity is
> read out of GitHub's API response. The tooling can verify an approval and
> write it down; it cannot author one, and there is no flag, environment
> variable or argument that makes it sign for you. The lab this came from
> accepted an activity file in place of the API call, which would have let
> anyone with a text editor name you as the reviewer. That was not ported.

---

## What you do

### 1. Read the evidence

On the pull request that changes `data/manual/staging_provider_policy.json`,
read the bundle it carries — `data/outputs/<league>_allowlist_evidence.md` —
and check that the markets the entry names are the markets you mean. Its
honest default is **not supported**, and approving against its own
recommendation is a decision you are allowed to make; it is recorded either
way.

### 2. Leave one comment

The **Provider Policy PR Gate** check on the pull request prints the exact
block to paste, with this pull request's proposed scope already in it. Copy it
from the check's summary, or run
`python scripts/create_receipt_from_github_approval.py --pr <N> --print-template`.

It looks like this:

```text
APPROVED_FOR_ALLOWLIST_PR
pr: 54
provider: the_odds_api
league: nfl
markets: moneyline, spread, total_points
```

Every line is load-bearing:

| Line | What it binds |
|:-----|:--------------|
| `APPROVED_FOR_ALLOWLIST_PR` | marks the comment as an approval at all |
| `pr:` | one pull request — an approval is not transferable |
| `provider:` | one provider |
| `league:` | one league. Approving a market in the NFL never approves it in NCAAF, and the receipt covers one league |
| `markets:` | the exact scope. Not "all", not a subset, not a superset |

Markdown bullets and any capitalisation parse (`- PR: 54`, `* League: NFL`).

**Your own lines, not quoted ones.** A block that is entirely inside a `>`
quotation is a repetition of an approval, not an approval, and it is refused.
This one mattered: a comment reading "REVOKED. Ignore this:" followed by the
block quoted underneath used to verify as a *fresh* approval, newer than the
one it was quoting.

A **review** (Files changed → Review changes) re-triggers the gate straight
away, and it has to be an **Approve** review — GitHub's own `DISMISSED`,
`Request changes`, `Comment` and pending states are refused by name, because a
review GitHub reports as dismissed is a signature GitHub says you withdrew. A
plain **comment** is read on the next run of the job — re-run the check, or
push.

### Taking it back

```text
REVOKED_FOR_ALLOWLIST_PR
```

One comment, and the newest word wins: an approval with a revocation at or
after it does not verify, and the gate refuses the entry that names its
receipt. Before this existed there was no way to say no — only comments
carrying the approval phrase were ever read, so "I withdraw that approval" was
invisible and the withdrawn signature kept verifying until the 72 hours ran
out. To approve again after revoking, paste the approval block again; it is
newer, and newer governs.

### 3. Let the check run

The gate reads your approval back from the API, verifies it, and writes the
receipt as a build artifact on the run. Nothing is committed by CI: a receipt
CI pushed would be a receipt CI authored.

### 4. Name the receipt in the policy

The last act is still a policy edit — set `allowlist_status`, put your GitHub
login in `reviewer_name`, and name the receipt id in `evidence_receipt_id`.
That edit carries **no authority by itself**: the gate re-reads the receipt
file and fails unless it records a real approval, on this pull request, by
you, for exactly the markets the entry names, bound to evidence that has not
moved. A receipt id that no approval hashes to is refused — the id is the
digest of the act, not a name somebody chose.

---

## What is refused

Every one of these produces **no receipt**, and the gate says which:

| Condition | Result |
|:----------|:-------|
| The approval phrase is absent | Refused |
| The author is not on the allow-list | Refused |
| Somebody else quotes your approval text | Refused |
| Your own approval block appears only inside a `>` quotation | Refused |
| `REVOKED_FOR_ALLOWLIST_PR` sits at or after the approval | Refused |
| The review is in any state but `APPROVED` | Refused |
| An evidence report is missing, so the binding would cover only part of the bundle | Refused |
| `gh` is not the real GitHub CLI at a trusted absolute path | Refused |
| `pr:` names another pull request | Refused |
| `provider:` is absent or names another provider | Refused |
| `league:` is absent or names another league | Refused |
| `markets:` is absent | Refused |
| `markets:` names a market the registry cannot price or settle | Refused |
| The scope is wider or narrower than the one the policy proposes | Refused |
| The review approved a commit that has since been superseded | Refused |
| A commit landed on the head after you approved | Refused |
| An evidence report was re-committed after you approved | Refused |
| An evidence report differs from its committed state | Refused |
| The evidence bundle is absent | Refused |
| The approval is older than 72 hours, or dated in the future | Refused |
| The policy file is missing, unreadable, malformed, or holds no entry for this league | Refused |

The last four matter most in practice. Approve, then push a commit or
regenerate a report, and the approval is void — you approved a state, and the
state changed.

## What the receipt records

- the pull request, the repository, and the head commit
- your GitHub login, as GitHub reported it
- whether it was a review or a comment, and its id
- when you approved, and how old that was when it was transcribed
- provider, league, policy key
- every market approved, and every market **not** approved, by name
- SHA-256 of every evidence report, and the commit that last carried it

## Checking without approving

```bash
# the block to paste, with this pull request's proposed scope in it
PYTHONPATH=src python scripts/create_receipt_from_github_approval.py --pr 54 --print-template

# verify an approval and write nothing
PYTHONPATH=src python scripts/create_receipt_from_github_approval.py --pr 54
```

Neither writes anything without `--write-receipt`.
