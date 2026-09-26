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
5. **PR gate.** A pull request that changes the policy file must carry a
   matching evidence bundle and a human acceptance receipt, or CI fails.
6. **Human acceptance receipt.** Cooper reviews the evidence and signs. Only
   this step allowlists anything, and the receipt must exist on disk — an id
   naming a file that is not there is the shape a fabricated approval takes,
   and the policy loader refuses it. The signature is one comment on the pull
   request, and the receipt is a transcription of it: see
   `docs/provider_allowlist_approval_github_ui.md`. The reviewer's identity
   comes from GitHub's API, so the automation can verify the approval and can
   never author one. The receipt is **read** every time it is used, not
   counted: the card's own loader parses it, checks the reviewer against the
   allow-list, checks that the market is one the receipt names, and re-checks
   the evidence checksums it prints. `REVOKED_FOR_ALLOWLIST_PR` in a later
   comment withdraws the approval.

## The threat model this is built against

Not a stranger on the internet — **an agent with code execution on this
machine**, which is what Claude is. "Only forgeable by somebody who can run
code here" is not a mitigation; it is the attack. So the mechanism does not
rely on any of the things such an agent can reach for free:

- `gh` is invoked by absolute path at a trusted location, never through PATH.
  A script called `gh` earlier on PATH answered every API call and minted a
  receipt with no edit to any tracked file.
- The receipt-producing path fetches the pull request's activity itself. It
  accepts no activity, because a mapping that was typed and a mapping that was
  fetched are indistinguishable by their contents.
- A receipt is built only from an object this code minted after that fetch. A
  hand-written dictionary naming Cooper used to be enough.

All three were **run** against this lab before they were closed.

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
