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
   and the policy loader refuses it.

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
