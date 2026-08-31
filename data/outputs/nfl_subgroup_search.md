# Pre-registered subgroup search — NFL player props

**Nothing survived: no demonstrated edge in any of the twelve pre-registered
subgroups.** One subgroup cleared discovery, and it cleared it by reading a
post-game variable. On the held-out 2025 season its return was **+6.68% over
4,904 bets** with a family-corrected interval of **[-5.71%, +19.07%]** — an
interval that includes zero — and the variable that defined it (same-game
target share) is not knowable at bet time, so it could not have been bet
whatever the interval had said. **Survivors: 0 of 12.**

The pre-registration is `docs/preregistered_subgroup_search.md`, written before
any subgroup was measured. Discovery on 2023-2024, validation on 2025, minimum
500 bets, intervals clustered by game, Bonferroni x1.53 across the twelve.
`tackles_assists` is excluded from every figure below; it is a settlement
artefact and pooling it imports the artefact.

**Discovery slice:** 44,347 staked bets across 512 games, seasons 2023-2024.
Pooled ROI **-2.88%**, interval [-6.78%, +1.02%]; pooled value-add **+2.94%**,
interval [-0.96%, +6.84%]. (The lab's headline **+4.28 points of value-add
against -3.22%** is the 2023-25 figure over 78,773 bets with `tackles_assists`
included. Both are stated with their samples because they are different
populations.)

## Value-add and ROI are different questions, and only one of them is money

* **Value-add** = profit minus what betting the same `(season, market, side)`
  cell blind returns. It answers *is the model better here?*
* **ROI** = profit. It answers *is this a bet?*

The two disagree almost everywhere in this search, and they disagree in one
direction: **value-add is positive in most subgroups tested and ROI is negative
in most of the same subgroups.** The gap between them is the vig. A subgroup
with +5% value-add and -3% ROI is a better model facing a price that costs
about 8 points, and it loses money. Nothing in this document is a bet, and the
value-add column is not a consolation prize — it is the part that informs the
next model.

## The twelve hypotheses

| # | Hypothesis | Predicted | Found (bets in brackets) | Mechanism held? |
|:--|:---|:---|:---|:---|
| 1 | Blowout risk `\|spread\|` | value-add rises on **unders** as the spread widens | Reversed. Under value-add is **highest in the tightest bucket** — +7.39% (5,150) at `[0,3)` against -0.13% (8,344), -0.68% (5,757), -0.09% (1,524) in the three wider ones. Cluster-robust slope **-0.0071 of value-add per point of spread, z = -1.14** | **No** |
| 2 | Edge magnitude | value-add rises with the model's own edge, if disagreement is information | Not monotone; the ordering breaks twice. +3.05% (8,258), +0.91% (6,732), +3.48% (7,878), +4.51% (7,667), +0.77% (8,181), +5.48% (5,631). Slope on bucket index **+0.0036, bootstrap CI [-0.0116, +0.0185]**; 0.1% of 2,000 game-clustered replicates were strictly increasing | **No** |
| 3 | Odds range | value-add **falls** at long prices (longshot-favourite bias) | Reversed. Longest bucket `(+250,+600]` has the **highest** value-add, +4.06% (7,319); near-pick'em `(-110,+100]` the lowest, +0.34% (5,378). Slope +0.14pp per bucket step, t = +0.23. All seven buckets have negative ROI; short prices alone do not fix it — `odds <= -110` returns **-1.98% (17,518)**, CI [-5.5%, +1.5%] | **No** |
| 4 | Line magnitude | value-add rises with the size of the line | Flat and non-monotone. Within-market quartiles: +2.31% (12,047), +4.48% (10,552), +1.65% (9,639), +4.81% (9,136). Median split: +3.12% (24,235) below vs +2.91% (18,919) above | **No** |
| 5 | Week of season | value-add **rises** through the season (the fit has more history late) | Reversed. W1-4 +4.93% (8,729), W5-9 +6.01% (12,254), W10-13 +0.71% (11,029), W14-18 +0.48% (12,335). Early-minus-late difference **+4.97pp, CI [-2.80pp, +12.74pp]** — so the reversal is not demonstrated either. Survives season-balancing and market-mix standardisation | **No** |
| 6 | Position | *no direction pre-registered* | TE has the largest value-add, +10.79% (5,275); then RB +3.34% (13,492), QB +1.79% (10,000), WR +0.55% (14,275), K -0.04% (761). Every interval includes zero. Every defensive position is far below the 500-bet floor (DE 219, LB 141, DT 59) | **Untestable as written** |
| 7 | Target share | value-add higher for **high-target-share** players, whose role is stable | Monotone on the **contemporaneous** variable — Q1 -14.27% (7,808) to Q4 +15.94% (7,766) — but that is same-game usage, a post-game quantity. On the **lagged** version knowable at bet time it is not monotone: L1 +6.96% (6,001), L2 +0.50% (6,001), L3 +1.73% (6,007), L4 +8.47% (5,991), all intervals including zero. The stability half of the mechanism **reverses**: stable roles -0.29% (5,999), volatile roles +10.48% (5,999) | **No**, in the only form that can be bet |
| 8 | Rest | *no direction pre-registered* | No ordering. Short week (rest<=4) +5.99% (3,278), normal (5-7) +1.96% (30,711), rest 8-9 +11.45% (4,334), off a bye (rest>=10) +0.18% (6,024). Every interval includes zero | **Untestable as written** |
| 9 | Weather, passing and kicking only | *no direction pre-registered* | Value-add falls with wind: 0-5 mph +3.35% (1,773), 6-12 mph -8.26% (2,648), 13+ mph -10.05% (831). The 13+ minus 0-5 contrast is **-13.5pp, game-clustered bootstrap CI [-37.1pp, +10.9pp]**, and it flips by season — the calm bucket is -17.16% ROI (719) in 2023 and +12.48% (1,054) in 2024 | **No** |
| 10 | Home / away | *no direction pre-registered* | Home value-add +4.86% (22,139) vs away +1.03% (22,208); paired within-game ROI difference **+7.46pp over 509 games, CI [-1.23pp, +16.16pp]**. Favourite +5.54% (22,313) vs dog +0.31% (22,034); paired +3.69pp, CI [-5.05pp, +12.43pp]. Both flip sign by season | **No** |
| 11 | Game total | **interacts** with over/under | No interaction. At totals <=42 the two sides are the same: overs +5.33% (9,152), unders +5.77% (6,478). At >50: overs +13.24% (1,062), unders +8.66% (1,705) — across **29 games**. The highest-total bucket has the best value-add, +10.42% (2,767), and the predicted interaction is simply absent | **No** |
| 12 | Book | some book is soft enough to survive at **its own** price | None does. Each book's own card, gated on its own quote: best is **draftkings -2.02% (16,794 bets, 511 games), CI [-6.43%, +2.38%]**. Five of ten are negative with intervals excluding zero — betonlineag -8.95% (9,719), williamhill_us -6.31% (13,216), bovada -5.85% (8,473), fanduel -5.62% (14,566), betmgm -5.34% (10,188) | **No** |

**Mechanisms that held: 0 of 12.** Four were reversed (1, 3, 5, 7-in-its-
bettable-form), five were flat or non-monotone (2, 4, 9, 11, 12), and three
(6, 8, and the direction-free half of 9/10) had no direction stated in advance
and therefore could not fail one. **That last point is a defect in the
pre-registration, not a result**: a hypothesis with no predicted direction
cannot be falsified by direction, and three of twelve slots were spent that
way. Fix it before the next search.

The correction applied is Bonferroni x1.53 across the twelve hypotheses, as
declared. The search actually examined far more than twelve cells — eight in
H1, six in H2, seven in H3, four each in H5/H8/H11, ten in H12. **The declared
correction is therefore too generous, and nothing cleared it even so.**

## The one subgroup that cleared discovery, and what happened to it

**Q3 of contemporaneous target share, `(0.130434782608696, 0.205128205128205]`.**

Discovery, 2023-24: n=7,644, ROI **+10.69%**, value-add +16.84%, interval
excluding zero. **Those numbers are not evidence.** They are the output of a
search that looked at this cut precisely because it looked good.

Held out, 2025 — the only numbers that count:

| Statistic | 2025 | Interval (clustered by game, Bonferroni x1.53) | Verdict |
|:---|---:|:---|:---|
| **ROI** | **+6.68%** (4,904 bets, 246 games) | [-5.71%, +19.07%] | **no demonstrated edge** |
| **Value-add** | **+18.76%** (4,904 bets) | [+6.33%, +31.19%] | beats the blind baseline |

The ROI interval includes zero before the correction as well: plain 95%
[-1.42%, +14.78%], game-clustered bootstrap over 4,000 replicates
[-1.44%, +15.27%], P(ROI<=0) = 5.6%. ROI fell from +10.69% (7,644) on discovery
to +6.68% (4,904) held out. Clustering matters: the per-game SE is 4.13pp
against a naive per-bet SE of 1.86pp, so the naive interval is **2.2x too
narrow**.

**The value-add row is real and the ROI row is not a bet.** This cell is a
genuinely better model of the same cells — and it still cannot be staked,
because ROI decides and ROI's interval spans zero.

Three things kill it independently of the interval:

1. **It is a leak, confirmed mechanically.** Sorting 2025 by target-share bin
   gives a monotone gradient: zero share -13.98% (8,883 bets, 37.9% win rate);
   Q1-Q2 -13.51% (12,143, 38.8%); Q3 +6.68% (4,904, 46.7%); Q4 **+18.79%**
   (4,068, 47.8%). That is same-game target share telling you the player's
   usage in the game being bet — unknown at bet time. Q4 leaks harder than Q3,
   exactly as a leak should. Value-add rose from +16.84% on discovery to
   +18.76% held out, which is also what a leak does. **No amount of held-out
   ROI makes a post-game variable bettable.**
2. **An arbitrary boundary convention swings it 2.2 points.** On 2025,
   `(lo,hi]` gives +6.68% (4,904); `[lo,hi]` gives +4.45% (5,170);
   `[.132,.205]` +6.38% (4,791); `[.130,.210]` +5.49% (5,388). Every one of
   those intervals includes zero.
3. **Ten games of 246 supply 110% of the +327.5 unit total.** Remove them and
   the cell returns **-0.72% (4,718 bets)**.

No sub-slice rescues it — overs +8.74% (3,528), unders +1.38% (1,376),
`reception_yards` +10.42% (2,546), `receptions` +9.72% (863),
`reception_longest` +9.24% (746); every interval includes zero. Weekly ROI
alternates sign across all 17 weeks of 2025 (+31.0% week 7, -29.9% week 16).

Against the six bars declared in advance:

| Bar | Result |
|:---|:---|
| 1. ≥500 bets, positive ROI, corrected interval excluding zero on discovery | cleared (7,644 bets) |
| 2. Stated mechanism holds in the predicted direction | **failed** — the bettable, lagged form is not monotone and the role-stability half reverses |
| 3. Replication on 2025 | **failed** — +6.68% (4,904), interval [-5.71%, +19.07%] |
| 4. Positive at the consensus price | not reached |
| 5. Not a settlement suspect | not a settlement suspect; it is a **leakage** suspect, which is worse |
| 6. Survives a null-baseline check inside the subgroup | cleared — value-add +18.76% (4,904), interval [+6.33%, +31.19%] |

Two of six. **No demonstrated edge.**

## Discovery numbers are not evidence

Every 2023-24 figure in this document — every number in the twelve-row table —
is a description of the set the search was run on. Subgroups were chosen there
because they looked good there. A corrected interval on a discovery set
excludes zero as a matter of routine when twelve hypotheses and fifty-odd cells
have been examined, and that is why the pre-registration made the 2025 season
untouchable until discovery was closed. **The only evidential numbers here are
the 2025 ones**, and there is exactly one set of them: +6.68% ROI on 4,904 bets
with an interval that includes zero.

## What the search is worth to the next model

No mechanism held, so there is no mechanism to carry forward. Four results are
durable anyway, and they are the reason to have run this.

**1. Same-game usage explains the model's residual; the lab's lagged proxy
explains essentially none of it.** On `reception_yards`, contemporaneous target
share correlates **+0.404** with `actual - line`. The prior-weeks mean of the
same variable — the version knowable at bet time — correlates **+0.021**, over
24,000 bets with at least two prior observed weeks. The two variables correlate
+0.599 with each other, and that is not enough. The next model's job is to
**forecast** usage, not to lag it. The leak also bounds the prize: perfect
same-game usage knowledge is worth about **33 points of ROI** between the
bottom and top bins on 2025 (-13.98% on 8,883 against +18.79% on 4,068), which
is the value of a variable nobody has.

**2. The model's own `edge` column does not grade its information content.**
Value-add is flat in edge (slope +0.0036, bootstrap CI [-0.0116, +0.0185] over
44,347 bets), and the top bucket's positive ROI, +0.41% (5,631), rests on one
market in one season: drop `reception_yards` and it is -1.67%; split by season
it is -4.06% (1,827) in 2023 and +2.55% (3,804) in 2024. Do not use `edge` as a
ranking or staking signal.

**3. Positive value-add everywhere is partly a measurement artefact, and the
next search must fix it.** The null baseline is computed per
`(season, market, side)` over a universe 4.7x larger than the staked set
(207,628 quotes against 44,347 bets) and **does not condition on price**. The
staking gate truncates odds to exactly `[-160, +600]`, with pile-ups at both
bounds (162 bets at exactly -160, 259 at exactly +600). So value-add is
positive in all seven odds buckets partly because the gate itself selects
prices the blind baseline does not, not because the model is skilful at every
price band. Any future value-add statistic should condition the null on price.

**4. TE is the one position-shaped lead, and it is a lead for a model, not a
bet.** Value-add +10.79% (5,275 bets) against WR +0.55% (14,275); TE's own ROI
is +3.26% with an interval of [-9.63%, +16.14%]. Worth a mechanism and a
pre-registration of its own. It is not worth a stake.

## The plain answer

**At these prices the market is efficient with respect to this model.** That is
not a hedge and it is not a disappointment — it is the finding, and it is
consistent with the deepest result already in this repository: over 74,345
bets the model's Brier score is **0.26057** against the market's **0.22703**,
and walk-forward isotonic calibration closes most of that gap without ever
crossing it (2025: model 0.25710, calibrated 0.22524, market 0.22329). The
market's implied probability still carries the vig and is therefore being
scored with a handicap. The model loses anyway.

A subgroup search cannot repair a model that is a worse forecaster than the
price it bets into. It can only locate the slice where the noise happened to
run the right way. This search was pre-registered so that it could not do that
quietly, and the one slice it found is a post-game variable that fails to
replicate. **The +4.28 points of value-add are real and the vig is bigger. No
subgroup closes that gap. No demonstrated edge.**

### What this does not settle

* **Two discovery seasons and one validation season.** It is the full available
  population for 2023-25, not a sample of it, and it is still three seasons.
* **Twelve hypotheses is twelve.** Three of them were written without a
  direction and could not be falsified by one. A thirteenth cut, chosen now,
  would not be pre-registered and would not be evidence.
* **The consensus-price bar was never reached**, because nothing got past
  replication to need it.
* **The forward ledger is untouched by all of this.** It starts 2026-09-09 and
  is the only evidence that can still grow.