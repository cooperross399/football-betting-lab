# What the evidence actually supports

This file is written **before the first measurement**, on purpose. In the EPL
lab the equivalent document arrived late, after months of numbers had already
been quoted without their intervals. In the NHL lab it was written first and
every number since has landed in a place that already knew how to read it.
This is the third time, and it is written first again.

## The current position, stated plainly

**Nothing has been measured. There is no model, no fitted parameter, no
backtest, and no evidence of any kind about whether this works.** The only
numbers in this repository today are counts of games and counts of credits.
Anything this lab says before Week 1 that sounds like a finding is a bug.

The card, when it exists, will say in those words that it is accumulating
evidence rather than making recommendations. That is not modesty. It is the
accurate description of a lab whose entire evidence base is empty.

## The rules this document enforces

These are carried over from the NHL lab unchanged, because they were earned
and nothing about football weakens them.

**A number without a sample size is not a result.** Every measured figure in
this repository is written next to the count of bets, games, or player-games
behind it. A report that omits one is a bug.

**An interval that includes zero means "no demonstrated edge".** Those exact
words. Not "promising", not "trending positive", not "small but positive". A
+12% ROI over 40 bets and a coin flip are the same claim at that sample size.

**Calibration can rule a model out. It can never rule one in.** A well
calibrated model that has never been priced against a real market has shown
only that its probabilities are internally sensible.

**Where a price-based test exists, it decides.** A change that improves
calibration and loses the priced test does not ship. This is not theoretical:
in the EPL lab a change that improved calibration on every market cost about
140 units; in the NHL lab the by-TOI correction straightened every volume
bucket and lost 37.6 units in the only form a card could apply it.

**"Conditioned on what, known when?"** runs on every adjustment before it is
believed. The NHL lab found a correction worth +162.8u indexed on *actual* ice
time that lost −37.6u on *expected* ice time — the only version a card can
use. Hindsight leaks look exactly like edges. Football is worse for this than
hockey, not better: game script, snap share and target share are all
enormously predictive **after** the fact.

**Walk-forward only.** A model prices a game using games strictly earlier than
it. Same-week data never touches its own fit. In football this bites harder
than in hockey, because a week is sixteen games rather than a hundred, and the
temptation to use "the rest of the week" is correspondingly larger.

**Family-wise correction across every market tested, reported beside the raw
figure.** With sixty wired markets, something will look profitable by chance.
Assume it is until it replicates.

**Minimum sample thresholds per market, declared in advance**, below which the
verdict is "not enough evidence" — not a number.

**Replication on held-out seasons before any claim survives.**

## The sample-size problem, which is much worse here than in hockey

The detection arithmetic does not depend on the sport. Separating a true edge
from zero at 95% confidence, flat stakes at roughly even money, takes about:

| If the true edge were | Bets needed to separate it from zero |
|----------------------:|-------------------------------------:|
| +5%                   | ~1,540 |
| +8%                   | ~600 |
| +10%                  | ~385 |
| +15%                  | ~171 |

What changes is how long it takes to get there.

| League | Regular-season games | Game days |
|:-------|---------------------:|----------:|
| NHL    | 1,344 | 185 |
| NFL (2026) | **272** | **57** |

**An NFL season is 272 games. One season cannot establish an edge, and every
report this lab produces will say so out loud.** At three qualifying bets a
game — which would be a busy card — a full season is roughly 800 bets: enough
to separate a +8% edge from zero, and nowhere near enough for +5%. At one bet
a game it is 272, which separates nothing smaller than +12%.

That is the honest ceiling on what a single NFL season can ever say. It is not
a reason to skip the season; it is a reason to start collecting on time and to
refuse to over-read the first hundred bets.

Props are the volume lever, exactly as in hockey: sixty wired markets over 272
games is a large number of priced opinions. But volume in *opinions* is not
volume in *independent* evidence, which is the next section.

## Correlation is a first-order accounting problem here

In hockey the lab could mostly treat one game's selections as independent. In
football it cannot, and pretending otherwise would inflate every interval in
every report.

A quarterback's passing yards, his top receiver's receiving yards, that team's
total, and the game total are **the same event seen four ways**. So:

- Correlated selections are never staked as independent.
- Their edges are never summed.
- Exposure is reported **per game**, correlation-aware, not per selection.
- Every interval in every report accounts for clustering by game. A naive
  binomial interval over 800 correlated bets is narrower than the truth, and a
  narrow interval is how "no demonstrated edge" turns into a claim.

The composite props — pass+rush yards, rush+reception yards, anytime
touchdown — are the sharpest version of this, because the composite and its
parts can both appear on one card. They are wired at tier 2 partly for that
reason.

## Key numbers, and the half-point that is most of any edge

Football margins pile up on 3 and 7. A half-point across a key number is worth
more than anywhere in hockey.

- Pushes on whole numbers are modelled exactly, never approximated away.
- Every claimed edge on a spread or total is reported **alongside how much of
  it is line value at a key number**. An "edge" that is entirely a half-point
  of line value is a statement about the price shopped, not about the model,
  and the report will say which it is.

## What yardage is, and what it is not

**Yards are not Poisson.** A count model is right for receptions and defensible
for carries. It is wrong for yardage, which is a compound outcome —
opportunities times yards per opportunity — heavily right-skewed and
zero-inflated. Longest-completion and longest-rush are worse still: they are
maxima, and their distribution is an extreme-value one.

Every distribution choice in this lab is stated, justified, and then
**measured against the empirical distribution it claims to describe**. A fitted
shape that has not been shown against the data it was fitted to is an
assertion.

## Closing-line value is a first-class metric here, not a footnote

With samples this thin, CLV is the fastest honest signal available. The
closing price is tracked for every frozen opinion and CLV is reported per
market **beside** ROI.

**A winning record with negative CLV is variance**, and the reports will say
that in those words. So is a losing record with positive CLV — in the other
direction, and equally worth saying.

## The priced instruments this lab has

In the NHL lab, the price-based backtest is what decided everything: what
ships, what does not, which corrections are real. **That instrument is
available here too**, and this section previously said the opposite.

The reversal is worth stating precisely, because it is the kind of mistake
this document exists to catch. The first draft computed the historical
purchase against a 100,000-credit **annual** pool, found it cost twice the
entire football budget, and concluded there would be no bought-price backtest.
The quota resets **monthly** (confirmed 2026-08-28). One season of tier-1
markets is 125,120 credits — 1.25 months — against a season whose heaviest
month uses about 10% of one. See `docs/credit_cost.md`.

Three priced instruments, then, in the order they become available:

1. **The free closing-line series.** `spread_line`, `total_line` and both
   moneylines for every game back to 1999, in the nflverse schedule file,
   complete for 2024 and 2025. One consensus closing line — no book, no
   ladder, no props — so it measures the **team model** and nothing else. It
   costs nothing and goes back twenty-seven seasons, which no purchase at any
   price does.
2. **Forward evidence.** The opinion the card actually held, frozen before
   kickoff, settled after, never repriced. The only priced evidence for any
   market the provider does not retain, and the accumulating out-of-sample
   test for every market and every shipped policy at once. It arrives at 272
   games a season, which is slow, and **it cannot be back-dated** — which is
   why it is built first regardless of what else is affordable.
3. **Bought historical prices.** A retention probe first (~9,200 credits, to
   find out per market and per book whether any historical price exists at
   all), then a purchase sized from what it finds. A credit spend, and
   therefore Cooper's decision, and nothing is bought without the number
   agreed first.

None of this changes what any of them can *establish*. A bought backtest on
272 games a season is still 272 games a season, the family-wise correction
still applies across sixty markets, and an interval including zero still means
"no demonstrated edge" in those words.

## What can and cannot be measured historically — probed, 2026-08-28

The retention probe has run: 20 events, stratified across kickoff windows and
split evenly between the 2024 and 2025 seasons, 46 provider keys each, at a
snapshot 60 minutes before kickoff. It cost **7,280 credits** against a
pessimistic bound of 9,220 — the shortfall being exactly the keys no book
retained, which is the thing it was measuring.

**All 27 tier-1 markets have historical prices. 25 have enough to measure
against.** Nine books appear across the sample. Full table:
`data/outputs/nfl_retention_probe.md`.

Two are retained but **too thin to support a measurement**: `reception_tds`
and `rush_tds`, each priced on 2 of 20 events by a single book, with six and
four priced outcomes respectively. "Retained" and "measurable" are different
claims and this document will not let them be confused: a measurement against
one book measures that book's pricing, not the market's.

**The probe also reproduced the `total_2_5` mistake before it could be made.**
Read by provider key, three markets returned nothing across all twenty events
— `player_rush_tds`, `player_reception_tds`,
`player_defensive_interceptions` — and the first rendering of the report
called them unmeasurable. Their alternate ladders had all three, on 2, 2 and 9
events. The featured key and its ladder are one market everywhere else in this
repository, so a conclusion drawn per key was the wrong unit. The report now
rolls up to the market and says so.

The reverse case is in the same data and is why the rollup cannot simply
prefer ladders: `pass_longest_completion` is retained on all 20 events and its
ladder on none.

Tier 2 has not been probed. Its markets are wired and settleable and their
retention is **unknown** — not "retained", and not "absent".

## The gates that will produce nothing, and why that is correct

Several markets will be modelled, calibrated, and still unable to produce a
selection. That is the same standard the NHL lab holds for goalie saves, which
is priced and tracked and cannot reach a card because there is no
confirmed-starter feed.

Here the equivalents are: **player availability** (inactives land about ninety
minutes before kickoff and no free feed publishes them), **quarterback
changes**, and **weather above a measured wind threshold**. Where the feed does
not exist, the market is priced and tracked and **cannot produce a selection**,
and the card says so in those words.

An excluded market is never reported as a pass, an avoid, or a no-value call.

## The first priced results, and how to read them

Two priced tests have now run. Both say the same thing about the models as a
whole, and one of them raises a question.

**The team model does not beat the closing line.** Moneyline −6.2% over 1,923
bets, spread −1.9% over 1,886, total −1.8% over 1,708, every interval
including zero. Free, back to 2016, and conservative in two directions:
it bets into the close and uses one consensus line rather than the best of
nine books.

**The prop models lose against real bought prices.** Pooled −6.7% over 24,470
bets, family-corrected interval −12.4% to −1.1%. The interval excludes zero
and it is **negative**. That is a result, not an absence of one.

**`tackles_assists` returned +16.2% over 941 bets and is not a finding.**

This document exists to make that last sentence stick, so the reasoning is
spelled out rather than summarised:

* It survives every check that can be run for free. The halves agree, 223
  distinct players are involved, the best single game is 7% of the profit, and
  removing that game leaves +15.1%.
* Settlement was suspected first and cleared: at the featured line the Over
  hits 47.7%, so what nflverse records and what the books settle are not
  drifting apart.
* The count model it uses was calibrated afterwards and is roughly centred.

And none of that is replication. It is **one season, 67% sampled, one of
eighteen markets tested**. A market selected because it looked good in a sample
is exactly the market most likely to have looked good by chance, and the
correction for that is not a wider interval — it is a season the market was
not selected on. Until that exists, the honest word is **candidate**.

The failure mode this guards against is specific and this repository has
watched it happen elsewhere: a suggestive cell survives every test anyone
thinks to run, gets described as "promising" once, and is a shipped policy
three sessions later with nobody able to say when it stopped being a
candidate.

## The one thing that is certain

Every claim this project will ever make about the NFL rests on evidence that
does not exist yet. The first of it arrives on 2026-09-09. That is worth more
than any amount of reasoning done before then, which is why the build order
puts the evidence organ first and the models second.
