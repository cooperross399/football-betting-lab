# Pre-registration: does the market under-adjust to a ruled-out team-mate?

**Written and committed before the fit was run.** Nothing below was chosen
after seeing a rushing coefficient. The point of this file is that it is in the
history with a timestamp earlier than the result.

## Why a pre-registration is needed at all

The receiving fit ([#43](https://github.com/cooperross399/football-betting-lab/pull/43))
returned a club-level term of **+0.0857, 95% [-0.0165, +0.1880]** — positive, in
the predicted direction, larger than its placebo (+0.0250), and including zero.
The pre-specified headline there was the *player-level* term, which was null.

Re-reading the club-level term on the same 25,968 wagers is not a retest. It is
the same number read twice, and calling it "pre-specified" afterwards is the
specification search this lab has already criticised in an adversarial review
of its own work. So the retest has to run on a sample that has not been looked
at.

## The sample

**Rushing markets** — `rush_yards`, `rush_attempts`, `rush_longest`, 17,905
scored wagers. No fit, no plot and no summary statistic involving prices has
been computed on these for this feature. The mechanism check below is the only
thing that has touched rushing, and it involves no price and no wager.

## What is already known, and was known before this file

Stage one for rushing, measured on volume alone with no market involved: a back's
week-W carry-share gain regressed on the pro-rata share he would receive gives
**+0.696, 95% [+0.553, +0.839]**, against +0.220 for receiving. Mean share gain
is +0.0412 when a club has vacated under 5% of its carries and +0.1256 when it
has vacated over 15% — about **2.19 carries a game**. A backfield is a smaller
room than a receiving corps, so carries transfer more nearly pro rata.

Sample sizes are the worry, and they are stated in advance: only **373**
player-weeks carry a vacated share above 5% and **243** above 15%, against
2,958 and 1,222 in receiving. A strong mechanism on a small treated group can
still produce a test too weak to conclude from.

## The prediction

**Primary.** `d1`, the club-level vacated carry share standardised within the
sample, entered in
`logit P(over) = a + b logit(p_market) + c logit(p_model) + d1 vacated + d2 gain`,
is **positive**. The reasoning is that a ruled-out back is public days early, and
if the line does not move far enough the remaining backs' lines sit too low, so
overs land more often than the price implies.

**Decision rule, fixed now.** The primary claim is upheld only if the 95%
game-clustered interval on `d1` **excludes zero on the positive side**. A
positive point estimate whose interval spans zero is reported as no
demonstrated edge, in those words, exactly as every previous null here has been.

**Secondary, and not the claim.** `d2`, the player's own pro-rata share of what
was vacated. It was the pre-specified headline in receiving and was null there.

**Reported regardless of outcome.** Including if `d1` comes back negative,
which would be evidence against the receiving result rather than silence about
it.

## What would make even a positive result uninteresting

The minimum detectable effect is printed beside the estimate. If the MDE
exceeds the receiving point estimate of +0.0857, then this sample could not
have confirmed that number even if it were exactly right, and a null here is
uninformative rather than contradictory. That possibility is acknowledged in
advance so it cannot be discovered afterwards and used either way.
