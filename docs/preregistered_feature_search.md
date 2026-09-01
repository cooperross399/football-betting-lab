# Pre-registered feature search — does anything predict what the price got wrong?

**Written before any feature was measured.** Second pre-registration in this
repository; the first (`preregistered_subgroup_search.md`) found nothing in
twelve directions, and its stated defect — three hypotheses written without a
predicted direction — is corrected here: every family below has one.

## The question, and why it is not the obvious one

Cooper's instruction: use every stat, record and analytic available to find an
edge. The obvious reading is "add opponent strength, role and game context to
the model." That reading is wrong on its own, and the reason matters.

**The market already knows the opponent.** It knows the spread, the total, the
weather, the injury report and the depth chart. A feature that predicts a
player's yards is not an edge — it is a feature the price already carries. The
only thing that produces an edge is a signal that predicts **the part the price
got wrong.**

So the target is the residual:

    residual = won − market_implied_probability

A feature that moves the residual is information the market does not have. A
feature that predicts the outcome but not the residual is one it does. This is
the difference between a better model and a profitable one, and this lab has
already spent four days learning what happens when the two are confused.

## What is measured

* **78,253 staked bets**, 2023-2025, the complete bought population.
* Every feature is **knowable before kickoff**: defensive strength and player
  role are fitted on games strictly earlier than the one priced, shrunk toward
  the league (6 prior games for a defence, 4 for a role).
* **Discovery on 2023-2024. 2025 is held out** and is not looked at until
  discovery is closed.
* **Intervals clustered by game.** One game supplies many correlated bets.
* **Bonferroni across the 9 families below.**
* Minimum 500 bets before any verdict.

## The nine families, each with a direction stated in advance

1. **Opponent defensive strength.** Rushing yards allowed vary **2.25×**
   between the best and worst defence, receiving 1.43×, and the model uses
   none of it. *Predicts:* residual is positive on overs against weak defences
   — **if** the market under-adjusts for opponent.
2. **Player role level.** Target share and recent volume. *Predicts:* the
   model prices recent volume, so the residual should be flat here if the
   market prices it too.
3. **Role trend.** Last three games against the season. *Predicts:* a rising
   role the market has not yet repriced shows a positive residual on overs.
4. **Game script.** Team spread and total. *Predicts:* residual positive on
   unders for heavy underdogs, whose days end early.
5. **Rest and schedule.** Short weeks and byes.
6. **Weather.** Wind and temperature, on passing and kicking only.
7. **Position.** Whether any position is systematically mispriced.
8. **Defence × role interaction.** A workhorse against a soft run defence is
   the case where a missing opponent term should bite hardest.
9. **All features together**, in one held-out predictive model. If nine
   families each carry a little, a combined fit finds it; if none does, this
   is the strongest single statement that the price already has everything.

## What a finding must clear

1. ≥500 bets, residual effect with a corrected interval excluding zero on
   discovery;
2. the stated direction holding;
3. **replication on held-out 2025**;
4. an effect large enough to overcome the vig — a residual edge under about
   2.5 points is not a bet at these prices;
5. and it must survive as **ROI at the consensus price**, not only as a
   residual.

Anything clearing fewer than all five is **no demonstrated edge**, in those
words.
