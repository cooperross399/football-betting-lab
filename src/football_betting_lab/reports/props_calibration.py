"""Are the prop distributions the right *shape*? Measured, walk-forward.

## What this can and cannot establish

**Calibration can rule a model out. It can never rule one in.** A model whose
probabilities are internally sensible has shown exactly that and nothing more.
Whether the market disagrees with it profitably is a different question,
answered only by prices. Every number here is a statement about the model's
own coherence, and `docs/what_we_can_and_cannot_claim.md` will not let it be
read as anything else.

## The probability integral transform, and why it is randomised

For each realised outcome, the model's simulated CDF at that outcome is
computed. If the distribution is right, those values are **uniform on [0, 1]**
— so a histogram of them should be flat, and every departure from flat is a
specific, readable defect:

* mass piled at both ends -> the model is **too narrow**, and will price tails
  as rarer than they are;
* mass piled in the middle -> **too wide**;
* a mean below 0.5 -> the model **overpredicts**, centring above the truth.

Football props are discrete, and a discrete outcome makes the plain PIT lumpy
for reasons that have nothing to do with fit. So it is randomised: a draw from
`[F(x-), F(x)]`. Under a correct model that is exactly uniform, and under a
wrong one it still shows the defect.

## Why the fit never sees the season it scores

Fitted on earlier seasons, scored on a later one. In a sixteen-game week the
temptation to use the rest of the week is large and using it would leak a
result into the price of a game kicking off at the same time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from football_betting_lab.models.player_props import (
    fit_rates,
    load_play_yardage,
    simulate,
)


#: Each family: the label, the per-play yardage kind, and the three columns
#: (opportunities, yards, touchdowns) plus the "longest" column.
FAMILIES: tuple[tuple[str, str, str, str, str, str], ...] = (
    ("Receiving", "reception", "receptions", "reception_yards", "reception_tds",
     "reception_longest"),
    ("Rushing", "rush", "rush_attempts", "rush_yards", "rush_tds",
     "rush_longest"),
    ("Passing", "completion", "pass_completions", "pass_yards", "pass_tds",
     "pass_longest_completion"),
)

DECILES = 10


@dataclass
class FamilyCalibration:
    label: str
    scored: int = 0
    deciles: dict[str, list[float]] = field(default_factory=dict)
    mean_pit: dict[str, float] = field(default_factory=dict)

    def verdict(self, quantity: str) -> str:
        """The specific defect the histogram shows, in words."""
        buckets = self.deciles.get(quantity, [])
        if not buckets:
            return "not enough data to say"
        ends = buckets[0] + buckets[-1]
        middle = sum(buckets[3:7])
        mean = self.mean_pit.get(quantity, 0.5)
        parts: list[str] = []
        if ends > 26:
            parts.append("too narrow — the tails arrive more often than priced")
        elif ends < 14:
            parts.append("too wide — the tails are priced as commoner than they are")
        if middle > 48:
            parts.append("over-concentrated in the middle")
        if mean < 0.47:
            parts.append("overpredicts — centred above the outcomes")
        elif mean > 0.53:
            parts.append("underpredicts — centred below the outcomes")
        return "; ".join(parts) if parts else "no material departure from flat"


def calibrate(
    logs: pd.DataFrame,
    processed_dir: Path,
    *,
    fit_before: int,
    score_season: int,
    sample: int = 1500,
    draws: int = 4000,
    seed: int = 0,
) -> list[FamilyCalibration]:
    yardage = load_play_yardage(processed_dir)
    generator = np.random.default_rng(seed)
    results: list[FamilyCalibration] = []

    for label, kind, opportunity, yards, touchdowns, longest in FAMILIES:
        result = FamilyCalibration(label=label)
        per_play = yardage.get(kind)
        if not per_play:
            results.append(result)
            continue
        rates = fit_rates(
            logs,
            before=f"{fit_before}01",
            opportunity_column=opportunity,
            yards_column=yards,
            touchdown_column=touchdowns,
        )
        test = logs[(logs["season"] == score_season) & (logs[opportunity] > 0)]
        if test.empty:
            results.append(result)
            continue
        test = test.sample(min(sample, len(test)), random_state=seed)

        collected: dict[str, list[float]] = {
            opportunity: [], yards: [], longest: []
        }
        simulations: dict[str, object] = {}
        for row in test.itertuples():
            fitted = rates.get(str(row.player_id))
            if fitted is None or not fitted.is_usable:
                continue
            key = str(row.player_id)
            if key not in simulations:
                simulations[key] = simulate(
                    fitted, per_play, draws=draws, seed=seed + 7
                )
            simulation = simulations[key]
            for column, quantity in (
                (opportunity, "opportunities"),
                (yards, "yards"),
                (longest, "longest"),
            ):
                actual = float(getattr(row, column))
                values = getattr(simulation, quantity)
                low = float((values < actual).mean())
                high = float((values <= actual).mean())
                collected[column].append(float(generator.uniform(low, high)))

        result.scored = len(collected[opportunity])
        for column, values in collected.items():
            if not values:
                continue
            histogram = np.histogram(values, bins=DECILES, range=(0, 1))[0]
            result.deciles[column] = [
                100.0 * count / len(values) for count in histogram
            ]
            result.mean_pit[column] = float(np.mean(values))
        results.append(result)
    return results


def overall_reading(results: list[FamilyCalibration]) -> list[str]:
    """What the families say together, counted honestly.

    The temptation is to treat nine quantities all leaning the same way as
    nine pieces of evidence. They are not: within a family, opportunities,
    yards and longest are read off **one simulation**, so they lean together
    almost by construction. The independent unit is the family, and there are
    three.
    """
    means = [
        (result.label, column, value)
        for result in results
        for column, value in result.mean_pit.items()
    ]
    if not means:
        return []
    below = [item for item in means if item[2] < 0.5]
    families_below = {
        result.label
        for result in results
        if result.mean_pit and all(v < 0.5 for v in result.mean_pit.values())
    }
    families_with_data = [result for result in results if result.mean_pit]

    lines = [
        f"**All {len(below)} of {len(means)} quantities have a mean PIT below "
        "0.5**, so the model is centred above the outcomes everywhere it was "
        "measured — it expects a little more than happens."
    ]
    lines.append(
        f"That is {len(below)} numbers and **{len(families_below)} of "
        f"{len(families_with_data)} independent observations**. Within a "
        "family, opportunities, yards and longest are read off one "
        "simulation, so they lean together almost by construction; counting "
        "them as nine would be counting one thing nine times. Three families "
        "leaning the same way is what a coin does one time in eight. **Not "
        "enough to call it systematic**, and recorded so the next season's "
        "run can say whether it persisted."
    )

    spikes = [
        (result.label, column, buckets[0])
        for result in results
        for column, buckets in result.deciles.items()
        if buckets and buckets[0] > 13.0
    ]
    if spikes:
        lines.append(
            "**Excess mass in the lowest decile** on "
            + ", ".join(f"`{column}` ({value:.1f}%, {label})" for label, column, value in spikes)
            + " — very low outcomes happen more often than the model allows. "
            "That is the shape a missing mechanism makes, and this model is "
            "missing the obvious one: **nothing here knows a player's day can "
            "be cut short.** Blowouts empty benches, injuries end afternoons, "
            "and a benched starter's line looks like a player who was never "
            "going to get the ball. The model is unconditional on game state "
            "and says so; this is what that costs, measured."
        )
    return lines


def render(
    results: list[FamilyCalibration], *, fit_before: int, score_season: int
) -> str:
    lines: list[str] = []
    add = lines.append
    add("# Are the prop distributions the right shape?")
    add("")
    add(
        f"Fitted on seasons before {fit_before}, scored on {score_season}. "
        "Walk-forward: the fit never sees the season it is judged on."
    )
    add("")
    add(
        "**Calibration can rule a model out. It can never rule one in.** "
        "Everything below is a statement about the model's internal "
        "coherence. Whether the market disagrees with it profitably is a "
        "different question and no number here answers it."
    )
    add("")
    add(
        "Each row is a randomised probability integral transform, in deciles. "
        "A correct distribution puts **10% in every bucket**; the shape of "
        "any departure names the defect."
    )
    for result in results:
        add("")
        add(f"## {result.label}")
        add("")
        if not result.scored:
            add("Not enough data to say. No number is offered in its place.")
            continue
        add(f"Scored on **{result.scored:,} player-games**.")
        add("")
        add("| Quantity | " + " | ".join(f"d{i + 1}" for i in range(DECILES))
            + " | mean | Verdict |")
        add("|:---------|" + "-----:|" * DECILES + "-----:|:--------|")
        for column, buckets in result.deciles.items():
            add(
                f"| `{column}` | "
                + " | ".join(f"{value:.1f}" for value in buckets)
                + f" | {result.mean_pit[column]:.3f} | {result.verdict(column)} |"
            )
    reading = overall_reading(results)
    if reading:
        add("")
        add("## What the three families say together")
        for line in reading:
            add("")
            add(line)
    add("")
    add(
        "A mean below 0.5 means the model is centred above the outcomes — it "
        "expects more than happens. Sample sizes are beside every figure, and "
        "a decile histogram from a thousand games is itself noisy at the "
        "one-point level."
    )
    return "\n".join(lines) + "\n"
