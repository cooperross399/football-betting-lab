# Pre-registered feature search — NFL player props

**Nothing survived: no demonstrated edge in any of the nine pre-registered
feature families.** Survivors: **0 of 9**. Not one family cleared even the
first of the five bars declared in advance — a game-clustered,
Bonferroni-corrected interval excluding zero on discovery — so the held-out
2025 season was never opened, and the validation table is empty by outcome
rather than by omission.

The pre-registration is `docs/preregistered_feature_search.md`, written before
any feature was measured. Discovery on **2023-2024: 46,860 staked bets across
512 games**. Minimum 500 bets. Intervals clustered by `game_id`. Bonferroni
across the nine families.

---

## The point: the target was the residual, not the outcome

**Every number in this document is a residual — `won − market_implied` — and
that choice is the whole result.**

The market already knows the opponent. It knows the spread, the total, the
weather, the injury report and the depth chart, and it has known them since the
line was posted. So a feature that predicts a player's yards is not an edge; it
is a feature **the price already carries**. The only thing that can produce an
edge is a signal that predicts **the part the price got wrong**.

That distinction is not a technicality here. It is the difference between the
two answers this search produces:

| Question | Answer |
|:---|:---|
| Does opponent defensive strength predict a player's rushing yards? | **Yes.** Yards allowed vary **2.25×** between the best and worst defence, and the model uses none of it. |
| Does opponent defensive strength predict what the *price* got wrong? | **No.** Signed Q4-vs-Q1 residual contrast **+4.35pp over 20,915 bets / 484 games, CI [−0.93pp, +9.63pp]** — includes zero. The defensive ratio's correlation with actual/line is **r = 0.031**. |

The second row is the market doing its job. A feature can be strongly true
about football and worth exactly nothing at the window.

**You can watch this happen in the price.** In Family 3, `market_implied` rises
monotonically across role-trend quartiles — 0.410 → 0.426 on overs, 0.465 →
0.476 on unders — while `won` does not. The market is repricing last-three-game
usage in real time. What is left after that repricing is the residual, and the
residual is nothing.

### Why a subgroup search cannot be read as an edge hunt here

Read this before reading any number below. **The model is a worse forecaster
than the price it bets into.** Brier over 78,253 bets: model **0.26106**,
market **0.22782**. Walk-forward isotonic calibration closes most of that gap
and never crosses it — on held-out 2025, calibrated model **0.22573** against
market **0.22390**. **Per-market forecast skill is 0 of 12 markets.** And the
market's implied probability still has the vig in it, so it is an over-estimate
being scored with a handicap, and the model loses anyway.

If the model is not a better forecaster than the price, no slice of its bets
can be profitable except by chance. A pre-registered 12-hypothesis subgroup
search (`data/outputs/nfl_subgroup_search.md`) already found **0 survivors and
0 of 12 mechanisms holding**. This search is the second attempt from a
different direction, and it agrees.

---

## The nine families

Sample sizes are discovery bets; game-cluster counts are given where they are
the binding constraint. All residuals in percentage points.

| # | Family | Predicted direction | What was found | Direction held? | Worth building? |
|:--|:---|:---|:---|:---|:---|
| 1 | **Opponent defensive strength** (`def_yds_ratio`, `def_opp_ratio` quartiles × selection) | Residual **positive on overs against weak defences** | Sign held everywhere — overs +1.25pp vs weakest quartile (4,802) and −4.13pp vs strongest (6,160), unders mirroring at −3.26pp (5,631) and +0.05pp (4,322). Headline signed contrast **+4.35pp (20,915 bets / 484 games), CI [−0.93, +9.63]**. Fails its own sharpest test: RUSH family **+2.21pp (5,274)**, `rush_yards` **+0.02pp (3,758)**. Carried entirely by 2023 **+8.04pp (7,766)** against 2024 **+1.92pp (13,153)** | **Yes** | **No** |
| 2 | **Player role level** (`role_target_share`, `role_targets`, `role_rush_att`) | **Flat** — the model prices recent volume and the market should too | Flat, as predicted. None of 24 mandated bucket means or contrasts excludes zero. Best cell `role_target_share` Q4−Q1 overs **+6.86pp (10,236), CI [−0.55, +14.26]** dies on the direction test: WR-only it is **+9.97pp on overs (3,960) and +5.02pp on UNDERS (3,148)**, pooled **+7.69pp (7,108)** — both sides winning more, which no production signal can do | **Yes** (the null was the prediction) | **No** |
| 3 | **Role trend** (last three games vs season) | Rising role → **positive** residual on overs | Backwards. Rising role is the **worst** overs quartile (−1.68pp, 4,436); falling role is the **worst** unders quartile (−1.82pp, 3,387). The tradeable portfolio — over & rising, or under & falling — is **−2.40pp (7,823), CI [−6.34, +1.54]**, while the trend-*fading* side is +0.4pp | **No** | **No** |
| 4 | **Game script** (`team_spread` × `total_line`) | Residual **positive on unders for heavy underdogs** | Reversed. Heavy dogs (spread ≥ +7) on unders **−3.54pp (2,635 bets / 121 games)**; on overs **+2.66pp (3,048)**. Interaction slope **−0.38pp per point of spread (46,860), CI [−0.98, +0.21]**. Dose-response kill: at spread ≥ +10, where the effect must be largest, it collapses to **−0.86pp (2,044 / 45 games)**. `total_line` carries nothing: **+0.07pp per point, CI [−0.74, +0.87]** | **No** | **No** |
| 5 | **Rest and schedule** (rest buckets, `div_game`) | *Exploratory — none stated* | No cell excludes zero. Largest are rest 8-9 overs **+7.28pp (2,353, 60 game clusters)** and rest ≤4 unders **−4.33pp (1,663, 36 clusters)**. Rest 8-9 moves overs (+7.28pp) and unders (+3.69pp) the **same** direction — direction-corrected it collapses to **+0.6pp, CI [−5.5, +6.7]**. Only rest ≤4 has the correct signature (**ran-high +3.6pp**, jackknife-stable) and it lives on 36 clusters, CI [−2.3, +9.6] | **n/a** | **No** — re-test forward |
| 6 | **Weather** (wind, temperature; passing + kicking only) | Wind **suppresses**, so unders positive | Absent, and mostly **untestable**. High-wind unders **−0.64pp (460 bets / 45 games), CI [−17.15, +15.88]**. Suppression contrast (13+ vs 0-5 mph) **+4.35pp (827 bets / 46 games), CI [−10.10, +18.80]**. The one direction-consistent drift also appears in a **rushing placebo (−6.9pp)**, so it is not passing-specific. Coverage is 5,299 of 8,582 pass/kick bets (61.7%) and the missing rows are the 11 dome venues — an outdoor-stadium selection, not a random subset. **46 high-wind games against the ~774 needed** for a 2.5pp half-width | **No** | **No** — no power to test |
| 7 | **Position** (QB/RB/WR/TE/K × selection × market) | *Exploratory — none stated* | Nothing. Of 17 cells clearing 500 bets, **zero** exclude zero: WR −1.52pp (14,215), RB −0.98pp (13,506), QB −0.88pp (9,973), TE +1.12pp (5,239), K −0.35pp (751). Only TE/over clears the 2.5pp floor at **+2.52pp (3,360), CI [−3.06, +8.09]**, and it splits **+5.75pp in 2023 vs −0.78pp in 2024** and shrinks to +2.37pp once the odds-decile baseline is stripped | **n/a** | **No** |
| 8 | **Defence × role interaction** | Workhorse vs soft run defence → **largest** positive residual | The interaction runs the **wrong way**: low-usage players show the larger weak-defence effect, DiD **−7.31pp (4,734), CI [−26.31, +11.69]**. Headline cell (top role × weak D, overs) **+0.83pp (1,043 bets / 102 games), CI [−10.86, +12.52]** — below the 2.5pp floor before it is anything else, and it flips **−6.0pp in 2023 to +11.5pp in 2024**. The only coherent thing left is a plain defence main effect (**+4.01pp aligned, 17,001, CI [−1.73, +9.74]**), which belongs to Family 1 | **Partly** | **No** |
| 9 | **All features together** (ridge on every numeric pre-kickoff feature) | If nine families each carry a little, a combined fit finds it | **The cleanest statement in the search.** In-sample the rule looks bettable — predicted residual > 0.03 returns **ROI +8.6% on 5,721 bets / 411 games**, and > 0.05 returns **+16.0% on 2,238 / 286 games**. Honest out-of-fold (5-fold grouped by `game_id`), the same rules are **negative at every threshold**: > 0.02 **−3.5% (9,264 / 462 games)**, > 0.03 **−4.8% (6,694 / 429 games), residual −2.35pp CI [−6.76, +2.06]**, > 0.05 **−4.4% (3,041 / 327 games)**. Overs-only direction test out-of-fold: **−1.10pp (3,232 / 285 games), CI [−7.14, +4.94]** | **No** | **No** |

**Directions that held: 1 of 6 stated** (Family 1's sign, which then failed
every downstream test), plus Family 2's predicted null, which held in the sense
that the prediction was "nothing" and nothing is what there was. Three
reversed. Three families had no direction stated and remain exploratory —
the same defect the previous pre-registration recorded, now down from three
of twelve to three of nine and still not zero.

---

## The number that would have looked like an edge

Family 8's headline cell reads **+0.83pp** with the mandated game-clustered
interval. The **same cell, bet-weighted with a per-bet standard error, reads
+4.15pp with CI [−0.28, +8.58]** — a number that looks one rounding away from
publishable.

The per-bet SE is roughly **3× too narrow**; in Family 2 the mandated `game_id`
clustering is about **2.7×** the naive per-bet SE, and it is the only thing
keeping those intervals across zero. Inside that Family 8 cell, 10 games carry
23-44 bets each, only 56 distinct players appear, `reception_yards` is +10.4pp
while `rush_yards` is −11.8pp, and the sign flips by season.

**46,860 bets are 512 games.** That is the binding constraint on every number
above, and the pre-registration's clustering requirement is the only reason
this document does not contain a false finding.

---

## Which features to add to the model anyway

A better forecaster is worth having even when it is not a profitable one. The
model's Brier is 0.26106 against the market's 0.22782; closing part of that gap
is a real improvement even though this search says it will not open a gap on
the other side. But every feature is a degree of freedom spent against a
population of **816 games that cannot grow** — the provider serves props only
after 2023-05-03 — so the bar for adding one is that it predicts the
**outcome**, mechanically, for a reason stated before the fit.

| Feature | Predicts the outcome? | Predicts the residual? | Add? | Why |
|:---|:---|:---|:---|:---|
| **Opponent defensive strength** (`def_yds_ratio`, `def_opp_ratio`) | **Yes** — 2.25× spread in rushing yards allowed, 1.43× receiving, and the model currently uses **none** of it | No: +4.35pp (20,915 / 484 games), CI spans zero; r = 0.031 against actual/line | **Yes** | The clearest known omission in the model. Two features, mechanically motivated, already built and leak-checked (week-*t* update correlates 0.41 with week *t*'s realised allowance and **0.02** with week *t+1*'s). Expect a Brier gain toward the market and **no** edge. Ship it as a forecasting improvement or not at all. |
| **Player role level** (`role_target_share`, `role_targets`, `role_rush_att`) | **Yes** — `won` runs 0.317 → 0.409 across WR target-share quartiles on overs (3,960) | No, and the apparent signal is a mis-specification signature: unders rise too (+5.02pp, 3,148) while `market_implied` stays flat near 0.39 | **Marginally** | The model already fits usage from recent volume, so this mostly re-states what it has. Add `role_target_share` only if it measurably improves held-out Brier on its own; do not add all three. |
| **Role trend** (last three vs season) | **No** — `won` is flat across trend quartiles | No: tradeable form −2.40pp (7,823), CI [−6.34, +1.54], sign backwards | **No** | The market visibly prices it (`market_implied` 0.410 → 0.426) and the outcome does not vary with it. Pure degrees of freedom. |
| **Game script** (`team_spread`, `total_line`) | Not as tested | No, and reversed: −3.54pp on the pre-registered cell (2,635 / 121 games); dose-response dies at ≥ +10 | **No** | Two independent pre-registered searches now say the blowout mechanism runs backwards. **Do not build the game-script model.** The calibration defect it was meant to fix is real — excess mass in the lowest decile on `rush_yards`, `rush_longest`, `pass_completions`, `pass_yards` at 14.8-15.8% against 10% — but `team_spread` is not the variable that carries it, and that remains an open modelling problem rather than a feature. |
| **Rest / schedule** | Unknown at this power | Not demonstrated; the one correct-signature cell (rest ≤4) has **36 game clusters** | **No** | Not a null — an absence of power. The single hypothesis worth carrying forward, and it should be carried as a hypothesis, not a feature. |
| **Weather** (wind, temperature) | Plausibly, untested here | Untestable: 46 high-wind games against ~774 needed | **No** | Also confounded: "has weather" is an outdoor-stadium selection (11 dome venues missing), and retractable roofs are a game-time fact this lab cannot know before kickoff. Adding it would import a selection, not information. |
| **Position** | No, beyond what the player fit already carries | No: 0 of 17 cells | **No** | The apparent spread across positions is odds-mix and over/under-mix (WR mean odds +88 and 60% overs; SAF −4 and 25% overs), not information. |
| **Defence × role interaction** | No | No, and inverted (DiD −7.31pp, 4,734) | **No** | The main effect is Family 1. An interaction term here buys the artefact and not the signal. |
| **Combined ridge over all features** | — | **No**, and this is the decisive test: in-sample +8.6% ROI (5,721) becomes **−4.8% out-of-fold (6,694 / 429 games)** | **No** | The gap between the in-sample and out-of-fold columns is the size of the overfit available in this feature set. |

**Net recommendation: two features, both from Family 1, both as forecasting
improvements with no expectation of profit.** Everything else in this search is
not worth the degrees of freedom it would cost.

---

## What is actually left to try

Blunt, because the alternative is another four days spent re-finding this.

**1. The 2025 hold-out is unspent, and that is worth exactly one shot.**
Nothing reached validation, so the season is clean. It should be spent on one
pre-registered hypothesis, not on a re-run of these nine, and not on the
Family 1 contrast — that contrast is already known to live entirely in 2023 and
to be flat in the larger 2024 sample, so 2025 would be adjudicating a coin
flip that has already landed tails once.

**2. Two seasons cannot resolve the effect sizes worth betting, and there is
no more history to buy.** The constraint is not 46,860 bets, it is **512
games**. At the corrected interval a 2.5pp effect needs roughly **774 game
clusters**. The historical purchase is complete — 816 events, every NFL game
for which props exist — so discovery on this population is finished. Reaching
774 clusters means the forward ledger at 272 games a season: **about three more
seasons**. That is the honest timescale, and any plan that pretends otherwise
is a plan to overfit.

**3. The only untried thing with data already bought is the market itself, not
football.** Every feature tested here is public and pre-kickoff — precisely the
set the price contains by construction, which is why nine families of it found
nothing. What this lab holds and has never analysed is **two snapshots per
event on 815 of 816 games**: card time and the close. The disagreement between
those two prices, and the disagreement between nine books at one moment, is
information the card-time consensus does not contain by definition. That is a
different question — following the market rather than out-forecasting it — and
it must still be measured as **ROI at a price you can get**, because CLV is a
diagnostic here and never a criterion. It is not a promise. It is the one
remaining place where a signal is not ruled out a priori.

**4. Things that are not feature search and still matter more than feature
search:**

- **An independent settlement source.** `tackles_assists` is the only market
  that replicates and the only one the settlement screen flags, and those are
  the same fact. It cannot be measured at all until settlement can be checked.
- **The did-not-play grading question** — void or loss. It moves all-markets
  from −3.2% to −9.2% over 78,773 bets. It no longer decides anything, and it
  is still worth answering before anything is acted on.
- **Ship walk-forward calibration.** It cuts 2025 from −5.97% to −3.69% and
  2024 from −2.90% to −1.05%. A smaller loss is not a profit, and this document
  is the reason no filter turns one into the other.
- **The lowest-decile miss.** The model is unconditional on game state and pays
  for it. Family 4 says `team_spread` does not fix it. Something else might;
  that is a modelling question with a measurable Brier answer, not an edge
  hunt.

**5. The most likely true state of the world.** Nine feature families, twelve
subgroups, twelve markets of forecast skill, four independent instruments and
the complete bought population all return the same answer, and the combined
out-of-fold fit — the strongest single test available — returns **−4.8%**. The
straightforward reading is that **there is no edge in these markets at these
prices for this operation**, and that the price contains everything tested
because the price is built by people who also know it. The correct action is to
keep the machinery, ship the calibration, add the two defensive features as a
forecasting improvement, place nothing, and let the forward ledger run from
2026-09-09.

---

**Verdict: no demonstrated edge. Survivors 0 of 9. Validation set untouched.**