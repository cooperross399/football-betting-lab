"""Is the model's JOINT distribution better than its marginals?

Every other instrument here measures **marginal** forecasting skill: can the
model beat the price on one leg. The answer is a flat no — Brier 0.26106
against the market's 0.22782 over 78,253 bets, and 0 of 12 markets better than
the price after calibration.

This measures a different quantity. The compound simulation draws opportunities
once and reads receptions, yards and longest off **the same draws**, so it
produces a joint distribution as a byproduct of how it is built. A joint can be
right while the marginals are wrong, and the two are priced by different parts
of a sportsbook: marginals by the trading model, combinations by a
same-game-parlay correlation model that is a different and usually cruder thing.

**The number this produces is the size of the correlation, NOT the size of an
edge.** Modern books apply correlation adjustments to same-game parlays; they
do not price independence. What the independence column shows is how much a
book's SGP model has to be doing, not how much it is getting wrong. The edge, if
there is one, is the gap between their correlation model and the true one, and
that gap cannot be measured without same-game-parlay prices, which this lab has
never bought.

So this instrument answers one question honestly — *is our joint accurate?* —
and refuses the one it cannot answer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations

import numpy as np
import pandas as pd

#: Combinations a leg pair needs before its realised joint rate is reported.
#: Below this the joint is estimated from a handful of games and the ratio is
#: dominated by which ones.
MINIMUM_PAIRS = 300

#: A correlation this close to the model's is "matched". Wider than it looks:
#: a copula accurate to a tenth is far better than these marginals.
CORRELATION_TOLERANCE = 0.10


@dataclass(frozen=True)
class JointPair:
    """One pair of legs on the same player, priced together."""

    legs: str
    side: str
    pairs: int
    realised: float
    independence: float

    @property
    def ratio(self) -> float:
        return self.realised / self.independence if self.independence else float("nan")


@dataclass(frozen=True)
class CorrelationCheck:
    """The model's simulated correlation against the realised one."""

    pair: str
    realised: float
    model: float
    games: int

    @property
    def error(self) -> float:
        return self.model - self.realised

    @property
    def is_matched(self) -> bool:
        return abs(self.error) <= CORRELATION_TOLERANCE


@dataclass
class CorrelationResult:
    checks: list[CorrelationCheck] = field(default_factory=list)
    joints: list[JointPair] = field(default_factory=list)

    @property
    def matched(self) -> list[CorrelationCheck]:
        return [c for c in self.checks if c.is_matched]

    @property
    def joint_is_accurate(self) -> bool:
        return bool(self.checks) and all(c.is_matched for c in self.checks)


def implied(odds) -> np.ndarray:
    value = np.asarray(odds, dtype=float)
    neg = np.where(value < 0, value, -100.0)
    pos = np.where(value < 0, 100.0, value)
    return np.where(value < 0, -neg / (-neg + 100.0), 100.0 / (pos + 100.0))


def joint_pairs(bets: pd.DataFrame) -> list[JointPair]:
    """Realised P(both legs win) against the independence product.

    Pairs are same player, same game, same side — the shape a same-game parlay
    actually takes.
    """
    frame = bets[bets["outcome"].isin(["won", "lost"])].copy()
    if frame.empty:
        return []
    frame["_p"] = implied(frame["odds"])
    frame["_win"] = (frame["outcome"] == "won").astype(int)

    rows: list[dict] = []
    for (_, _, side), group in frame.groupby(["event_id", "player", "selection"]):
        if len(group) < 2:
            continue
        for i, j in combinations(range(len(group)), 2):
            a, b = group.iloc[i], group.iloc[j]
            if a["market"] == b["market"]:
                continue
            legs = " + ".join(sorted((str(a["market"]), str(b["market"]))))
            rows.append({
                "legs": legs,
                "side": str(side),
                "both": int(a["_win"] and b["_win"]),
                "independence": float(a["_p"] * b["_p"]),
            })
    if not rows:
        return []
    table = pd.DataFrame(rows)
    out: list[JointPair] = []
    for (legs, side), group in table.groupby(["legs", "side"]):
        if len(group) < MINIMUM_PAIRS:
            continue
        out.append(
            JointPair(
                legs=str(legs), side=str(side), pairs=len(group),
                realised=float(group["both"].mean()),
                independence=float(group["independence"].mean()),
            )
        )
    out.sort(key=lambda p: -p.pairs)
    return out


def render(result: CorrelationResult) -> str:
    lines: list[str] = []
    add = lines.append
    add("# Is the model's joint better than its marginals?")
    add("")
    add(
        "Every other instrument here measures **marginal** skill — can the "
        "model beat the price on one leg — and the answer is a flat no. This "
        "measures a different quantity. The compound simulation draws "
        "opportunities once and reads receptions, yards and longest off **the "
        "same draws**, so a joint distribution falls out of how it is built. "
        "A joint can be right while the marginals are wrong."
    )
    add("")
    if not result.checks:
        add(
            "**Nothing was checked.** That is an absence, not a pass, and no "
            "claim about the joint should rest on it."
        )
        return "\n".join(lines) + "\n"

    add("## Does the simulated correlation match the realised one?")
    add("")
    add("| Pair | Realised | Model | Error | Games | Matched? |")
    add("|:---|---:|---:|---:|---:|:---|")
    for check in result.checks:
        add(
            f"| {check.pair} | {check.realised:.3f} | {check.model:.3f} | "
            f"{check.error:+.3f} | {check.games:,} | "
            f"{'yes' if check.is_matched else '**no**'} |"
        )
    add("")
    if result.joint_is_accurate:
        add(
            f"**All {len(result.checks)} pair(s) matched within "
            f"{CORRELATION_TOLERANCE:.2f}.** The joint is accurate where the "
            "marginals are not, which is the one asymmetry this lab has found."
        )
    else:
        missed = len(result.checks) - len(result.matched)
        add(
            f"**{missed} of {len(result.checks)} pair(s) missed.** The joint "
            "is not uniformly better than the marginals, and a parlay priced "
            "off it inherits both errors at once."
        )
    add("")

    if result.joints:
        add("## How far is reality from independence?")
        add("")
        add("| Legs | Side | Combinations | Realised P(both) | Independence | Ratio |")
        add("|:---|:---|---:|---:|---:|---:|")
        for pair in result.joints[:12]:
            add(
                f"| {pair.legs} | {pair.side} | {pair.pairs:,} | "
                f"{pair.realised:.3f} | {pair.independence:.3f} | "
                f"{pair.ratio:.2f}x |"
            )
        add("")

    add("## What this is not")
    add("")
    add(
        "**This is the size of the correlation, not the size of an edge.** "
        "Modern books apply correlation adjustments to same-game parlays; they "
        "do not price independence. The independence column shows how much "
        "work a book's SGP model has to do, not how much of it that model gets "
        "wrong."
    )
    add("")
    add(
        "The edge, if there is one, is the gap between a book's correlation "
        "model and the true one — and **that gap cannot be measured without "
        "same-game-parlay prices, which this lab has never bought.** Until "
        "those exist, an accurate joint is a promising asset and not a "
        "demonstrated edge, in those words."
    )
    add("")
    add(
        "**And the marginals still have to be fixed.** A parlay's price is "
        "P(A) x P(B|A): a perfect copula on overconfident marginals still "
        "produces a wrong joint probability. The calibration maps exist for "
        "exactly that, and a joint built on raw model probabilities would "
        "inherit a 0.3 overconfidence at every leg."
    )
    return "\n".join(lines) + "\n"
