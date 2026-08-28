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

## The historical price wall, and what it costs this lab

In the NHL lab, the price-based backtest is what decided everything: what
ships, what does not, which corrections are real. That instrument is **not
affordable here**.

The Odds API bills historical odds at ten times the live rate. One NFL season
of tier-1 markets at one snapshot per game is roughly **125,000 credits**,
against about 62,000 remaining for football after the NHL lab's committed
spend. See `docs/credit_cost.md`.

The consequences have to be stated rather than worked around:

1. **There will be no bought-price prop backtest before Week 1, and probably
   not at all at the current quota.** Any report implying otherwise is wrong.
2. **Forward evidence is not a cheaper substitute for it.** It is a different
   and in one way stronger instrument — the opinion the card actually held,
   frozen before kickoff, settled after, never repriced — and in another way a
   much weaker one, because it accumulates at 272 games a season instead of
   arriving all at once.
3. **A limited, targeted historical purchase is possible** — a few markets,
   one snapshot, one season — and would be a decision for Cooper with the
   arithmetic in front of him. Nothing is bought without that.
4. Until then, **calibration is the only instrument available for most
   markets, and calibration can only rule out.** So the honest state of nearly
   every market will be "modelled, calibrated, not priced" for some time, and
   that is what the reports will say.

There is one partial exception worth naming precisely: the nflverse schedule
file carries a historical closing spread, total and moneyline per game, free.
That is a real price series for three team markets, and it will be used. It is
**one consensus line, not a book quote, with no alternate ladder and no
props**, so it can measure the team model and nothing else, and it can never
answer a question about the price actually available at a book.

## What cannot be measured at all

To be filled in by the retention and coverage probes, market by market, with
the reason — and probed **in season**, because a market unquoted in August
establishes nothing. An entry here is a statement that no price exists to test
against, not a statement that the market is bad.

Until those probes have run, the honest state is **unknown**: not "the props
are all retained" and not "none are".

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

## The one thing that is certain

Every claim this project will ever make about the NFL rests on evidence that
does not exist yet. The first of it arrives on 2026-09-09. That is worth more
than any amount of reasoning done before then, which is why the build order
puts the evidence organ first and the models second.
