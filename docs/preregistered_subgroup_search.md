# Pre-registered subgroup search

**Written before any subgroup was measured.** This file exists so that nothing
below can be claimed after the fact, and so the number of hypotheses tested is
on the record — it sets the family correction, and a search whose width is
decided afterwards has no honest correction at all.

## The question

The model is worth **+4.28 percentage points** over betting the same cells
blind (78,773 staked bets, 2023-25, `tackles_assists` included and screened
out of every conclusion). It still returns **−3.22%**, because the price
structure costs more than that. So: **is there a subgroup where the model's
value-add is large enough to clear the local vig?**

## The measurement, fixed in advance

* **Value-add**, not ROI, is the model statistic: `profit − null_roi` for the
  same `(season, market, side)` cell. Raw subgroup ROI is uninterpretable —
  the null baseline is −12.4% on overs and −2.6% on unders, so "unders return
  −0.1%" reads as signal and is entirely a property of the prices.
* **Profit is the objective.** A subgroup with high value-add and negative ROI
  is a better model, not a bet. Both are reported; only ROI decides.
* **Discovery on 2023 + 2024. 2025 is held out** and is not looked at until
  the discovery set is closed.
* **Minimum 500 bets** in a subgroup before any verdict, declared here.
* **Intervals clustered by game**, because one game supplies many correlated
  bets.
* **Bonferroni across the 12 hypotheses below**, not across the number of
  cells that happened to look good.
* `tackles_assists` is excluded from every pooled figure. It is a settlement
  artefact and pooling it imports the artefact.

## The twelve hypotheses

Each has a mechanism stated in advance. A subgroup that wins without its
mechanism holding is a coincidence with a story attached.

1. **Blowout risk** (`|spread_line|`). The calibration found excess mass in
   the lowest decile: the model does not know a player's day can be cut short.
   *Predicts:* value-add rises on **unders** as the spread widens.
2. **Edge magnitude.** *Predicts:* value-add rises with the model's own
   disagreement, if the disagreement is information rather than noise.
3. **Odds range.** Longshot-favourite bias is the best-documented bias in
   these markets. *Predicts:* value-add falls at long prices.
4. **Line magnitude.** Compound simulation should be best where the count is
   large enough for its shape to matter. *Predicts:* value-add rises with line.
5. **Week of season.** The fit has less history early. *Predicts:* value-add
   rises through the season.
6. **Position.** QB/RB/WR/TE/K/DEF have different usage stability.
7. **Target share.** The model prices recent role, not current. *Predicts:*
   value-add is higher for high-target-share players, whose role is stable.
8. **Rest.** Short weeks and byes change usage the model cannot see.
9. **Weather** (wind, temperature), on passing and kicking markets only.
10. **Home / away.**
11. **Game total.** Pace and volume. *Predicts:* interacts with over/under.
12. **Book.** Which books are soft, and whether any survives at its own price.

## What a finding must clear

In this order, all of them:

1. ≥500 bets on the discovery set, ROI positive, interval excluding zero after
   the 12-way correction;
2. the stated mechanism holding in the direction predicted;
3. **replication on 2025**, which nothing was selected on;
4. positive at the **consensus** price, not only at the best of N;
5. not a settlement suspect;
6. surviving a null-baseline check inside the subgroup itself.

Anything clearing fewer than all six is reported as **no demonstrated edge**,
in those words, whatever the number is.
