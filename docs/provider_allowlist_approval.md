# How a market becomes trusted

Nothing in this repository trusts a provider or a market by default. The
policy file `data/manual/staging_provider_policy.json` ships allowlisting
**nothing**, and the card refuses to select from any market not named in it.

Entries are keyed `{provider}:{league}` — `the_odds_api:nfl`. **Approving a
market in the NFL never approves it in NCAAF.** The distribution, the roster
churn and the books' own coverage are all different, and a policy file that
could express "allowed everywhere" would eventually be used that way.

## The sequence

1. **Shadow runs.** A live fetch writes to `data/staging/`, which the card
   cannot read. This proves the adapter parses the provider's real responses
   and produces the rows it claims to.
2. **Coverage discovery.** Per bookmaker, per market, **including alternate
   lines**, and **in season**. A market is not "unavailable" until this says
   so. The EPL lab excluded `total_2_5` for a season on a coverage check that
   only looked at the featured `totals` market; the line was in
   `alternate_totals` the whole time. The NFL retention probe reproduced that
   shape immediately — three featured prop keys returned nothing across
   twenty events while their ladders had them — which is why every report
   here rolls up to the market before it draws a conclusion.
3. **Measurement against real prices.** Historical prices where the provider
   retains them, and the free closing-line series in the nflverse schedule
   file for the team markets. Where neither exists, that is recorded by name
   as unmeasurable, and a calibration number is **not** offered as a
   substitute.
4. **Evidence bundle.** Shadow report, coverage report, retention probe and
   measurement reports, with their checksums, assembled into one reviewable
   artifact. Its honest default — the one every market in this repository
   currently gets — is **not supported**. A market with only a calibration
   number is never supported by it, however large the sample.
5. **PR gate.** `tests/test_policy_pr_gate.py::test_the_shipped_policy_passes_the_gate`
   runs `reports/policy_pr_gate.py` against the repository's own policy,
   receipts and evidence, inside the suite branch protection requires. Every
   entry whose status is `allowed` must cite a receipt that is complete — see
   below — and whose evidence checksums still match the files on disk, or the
   pull request cannot merge. It is a registered guard, so deleting or
   deselecting it is a red build.
6. **Human acceptance receipt.** Cooper reviews the evidence and signs. Only
   this step allowlists anything. The card opens the receipt on every run: a
   market is allowed only if the policy lists it **and** the receipt's own
   `approved_markets` does. An id naming a file that is not there, a receipt
   for another league, or a policy listing a market the receipt does not
   approve all allow nothing.

## The receipt

`data/manual/human_acceptance_receipts/{receipt_id}.json`, cited by
`evidence_receipt_id` in the policy entry:

```json
{
  "receipt_id": "the same id as the filename",
  "policy_key": "the_odds_api:nfl",
  "reviewer_name": "who signed",
  "reviewer_statement": "what was read, and why it is enough",
  "reviewed_at": "2026-09-01T12:00:00-04:00",
  "approved_markets": ["moneyline"],
  "evidence": [
    {"path": "data/outputs/nfl_allowlist_evidence.md", "sha256": "..."}
  ]
}
```

| checked | by the card, every run | by the PR gate |
| --- | --- | --- |
| file exists, is JSON, id is a safe filename | yes | yes |
| `receipt_id` matches the filename | yes | yes |
| `policy_key` is this league | yes | yes |
| `reviewer_name` present | yes | yes |
| market is in `approved_markets` | yes | yes, for every listed market |
| `reviewer_statement`, timezone-aware `reviewed_at` | | yes |
| every evidence file inside the repository, present, checksum matching | | yes |

**What neither can do is verify that a human wrote the receipt.** The checker
and the file live in the same repository, and whoever can edit one can edit
the other. Cooper's review of the pull request, enforced by branch protection,
is what carries that weight. The gate makes the record complete and current;
it does not make it authentic.

## What Claude may never do

- Write or edit a human acceptance receipt.
- Add a provider or a market to the policy file's allowlist.
- Weaken, skip, or work around the PR gate.
- Present shadow or probe evidence as though it had allowlisted something.

Claude prepares every one of the six steps and then stops. Step 6 is Cooper's.

## What approval does not buy

An allowlisted market still passes every other gate on every run: staging
validation, completeness, freshness, the availability gate, the
quarterback-change quarantine, the roof/weather exclusion, and the kickoff
guard. Allowlisting says "this market's prices may be used"; it does not say
"skip the checks".

## The record stays on the record

If Cooper approves a market against the measurement's own recommendation, both
the evidence and the decision are recorded, and any answer to "what do the
card's picks rest on" says so plainly. That happened in the EPL lab and again
in the NHL lab, and the record is the reason the answer in both is still
honest.
