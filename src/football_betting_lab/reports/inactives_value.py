"""What is knowing the inactives actually worth?

This lab refuses to let any player prop produce a selection, and the stated
reason is that **inactives are declared ninety minutes before kickoff and the
card runs three hours out**. That reasoning has been argued about for weeks and
never measured, because measuring it needs two prices for the same wager on
opposite sides of the deadline — and it turns out this lab bought exactly that
and then never read it.

Three snapshots were bought per event:

    T-360   labelled `card`, blind to inactives, and what every backtest used
    T-60    labelled `mid`, INSIDE the inactives window, read by nothing
    T-6     labelled `close`

The middle one is a third of the snapshot spend. It is also the only direct
evidence about the gate's central premise, because the market at T-60 knows who
is playing and the market at T-360 does not. **Whatever the price does between
those two snapshots is the market pricing in the inactives**, plus whatever else
moved in five hours.

## What this can and cannot say

It measures how much the price moves across the deadline, and whether the later
price is a **better forecast** than the earlier one. If it is much better, the
card is giving up something real by running blind, and the gate is expensive.
If it is barely better, the gate costs little and the argument is settled the
other way.

It cannot separate inactives from everything else that moves a line in five
hours — steam, weather, late scratches that are not inactives. So a large gap is
an **upper bound** on what inactives are worth, not a measurement of them. A
small gap is the more informative result, because nothing else can be hiding
inside it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

#: Wagers a market needs before its movement is reported. Below this the mean
#: move is dominated by which games happened to land in the sample.
MINIMUM_WAGERS = 300

#: A Brier improvement smaller than this is not worth reorganising a card
#: around. Stated in advance so the answer cannot be graded after the fact.
MATERIAL_BRIER_GAIN = 0.002


@dataclass(frozen=True)
class MarketMovement:
    """One market, priced on both sides of the inactives deadline."""

    market: str
    wagers: int
    mean_abs_move: float
    early_brier: float
    late_brier: float

    @property
    def brier_gain(self) -> float:
        """How much better the post-deadline price forecasts. Positive is
        better, because a lower Brier is a better forecast."""
        return self.early_brier - self.late_brier

    @property
    def is_material(self) -> bool:
        return self.brier_gain >= MATERIAL_BRIER_GAIN


@dataclass
class InactivesValue:
    movements: list[MarketMovement] = field(default_factory=list)

    @property
    def material(self) -> list[MarketMovement]:
        return [m for m in self.movements if m.is_material]

    @property
    def gate_is_expensive(self) -> bool:
        """True when the later price is materially better in most markets."""
        if not self.movements:
            return False
        return len(self.material) > len(self.movements) / 2


def implied(odds) -> np.ndarray:
    value = np.asarray(odds, dtype=float)
    neg = np.where(value < 0, value, -100.0)
    pos = np.where(value < 0, 100.0, value)
    return np.where(value < 0, -neg / (-neg + 100.0), 100.0 / (pos + 100.0))


def measure(early: pd.DataFrame, late: pd.DataFrame, outcomes: pd.DataFrame) -> InactivesValue:
    """Compare the pre-deadline and post-deadline price as forecasts.

    `early` and `late` are one row per wager at each snapshot; `outcomes`
    carries the settled result for the same keys. Joined on the wager rather
    than the event, because a player who is scratched has a wager at T-360 and
    may have none at T-60, and dropping him is exactly the selection effect
    this measurement is about — so the join is inner and the report says how
    many rows it lost.
    """
    keys = ["event_id", "market", "player", "selection", "line"]
    if early.empty or late.empty or outcomes.empty:
        return InactivesValue()
    frame = (
        early[keys + ["american_odds"]]
        .rename(columns={"american_odds": "early_odds"})
        .merge(
            late[keys + ["american_odds"]].rename(
                columns={"american_odds": "late_odds"}
            ),
            on=keys,
            how="inner",
        )
        .merge(outcomes[keys + ["outcome"]], on=keys, how="inner")
    )
    frame = frame[frame["outcome"].isin(["won", "lost"])]
    if frame.empty:
        return InactivesValue()
    frame["won"] = (frame["outcome"] == "won").astype(float)
    frame["early_p"] = implied(frame["early_odds"])
    frame["late_p"] = implied(frame["late_odds"])

    result = InactivesValue()
    for market, rows in frame.groupby("market"):
        if len(rows) < MINIMUM_WAGERS:
            continue
        won = rows["won"].to_numpy()
        result.movements.append(
            MarketMovement(
                market=str(market),
                wagers=len(rows),
                mean_abs_move=float((rows["late_p"] - rows["early_p"]).abs().mean()),
                early_brier=float(np.mean((rows["early_p"].to_numpy() - won) ** 2)),
                late_brier=float(np.mean((rows["late_p"].to_numpy() - won) ** 2)),
            )
        )
    result.movements.sort(key=lambda m: -m.brier_gain)
    return result


def render(result: InactivesValue, *, dropped: int = 0) -> str:
    lines: list[str] = []
    add = lines.append
    add("# What is knowing the inactives worth?")
    add("")
    add(
        "This lab refuses to let any player prop produce a selection, because "
        "**inactives are declared ninety minutes before kickoff and the card "
        "runs three hours out**. That premise has been argued about for weeks "
        "and never measured — and it turns out the evidence was bought and "
        "then never read."
    )
    add("")
    add(
        "Three snapshots exist per event: **T-360** (blind to inactives, and "
        "what every backtest used), **T-60** (inside the window, labelled "
        "`mid`, read by nothing), and T-6. The middle one is a third of the "
        "snapshot spend and the only direct evidence about the gate's own "
        "premise."
    )
    add("")
    if not result.movements:
        add(
            "**Nothing could be compared.** That is an absence, not a finding: "
            "no market had enough wagers priced at both snapshots, so the gate's "
            "premise remains unmeasured rather than confirmed."
        )
        return "\n".join(lines) + "\n"

    add("| Market | Wagers | Mean price move | Brier T-360 | Brier T-60 | Gain |")
    add("|:---|---:|---:|---:|---:|---:|")
    for entry in result.movements:
        add(
            f"| `{entry.market}` | {entry.wagers:,} | "
            f"{entry.mean_abs_move:.4f} | {entry.early_brier:.5f} | "
            f"{entry.late_brier:.5f} | "
            f"{entry.brier_gain:+.5f}{' **material**' if entry.is_material else ''} |"
        )
    add("")
    if result.gate_is_expensive:
        add(
            f"**The later price is materially better in {len(result.material)} "
            f"of {len(result.movements)} markets.** The card gives up something "
            "real by running blind, and the availability gate is expensive "
            "rather than free."
        )
    else:
        add(
            f"**The later price is materially better in only "
            f"{len(result.material)} of {len(result.movements)} markets**, "
            f"against a threshold of {MATERIAL_BRIER_GAIN} declared in advance. "
            "Crossing the inactives deadline buys the market very little, so "
            "the gate costs very little — and the case for reorganising a card "
            "around it is weak."
        )
    add("")
    if dropped:
        add(
            f"**{dropped:,} wager(s) present at T-360 had no price at T-60** and "
            "were dropped by the join. That is not noise: a player who is "
            "scratched loses his market, so the dropped rows are enriched in "
            "exactly the players this question is about. Every figure above is "
            "therefore conditioned on the wager still existing an hour out."
        )
        add("")
    add(
        "**This is an upper bound on what inactives are worth, not a "
        "measurement of them.** Five hours of steam, weather and late news move "
        "a line too, and nothing here separates them. A large gap could be any "
        "of those; a small gap is the more informative result, because nothing "
        "can be hiding inside it."
    )
    return "\n".join(lines) + "\n"
