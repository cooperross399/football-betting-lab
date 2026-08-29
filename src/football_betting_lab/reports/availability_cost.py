"""What does not knowing who will play actually cost?

## The gate this re-examines

This lab has refused to let any player prop produce a selection, on the
grounds that inactives are declared ninety minutes before kickoff and no
available feed publishes them. The reasoning was the NHL lab's goalie-saves
rule: a market you cannot confirm is a market you cannot bet.

**Measured, that reasoning does not hold for player props, and the reason is
the settlement rule rather than anything about the model.**

A player who does not take a snap does not lose the bet. The book **voids** it
and returns the stake. So the question "will he play?" is not a question about
whether the bet wins — it is a question about whether there is a bet at all,
and a bet that never existed costs nothing.

Over three bought seasons, **12.6% of the model's selections voided**. That is
a large number and it is financially a non-event.

## The assumption this rests on, and what it is worth

**Everything above assumes the book voids a did-not-play prop rather than
grading it a loss.** That is the standard rule — no action if the player does
not take a snap — and it is a rule, not a law of nature. Books differ, and a
book that graded those as losses would turn the same record from **+4.1% into
−9.0%**.

`void_rule_sensitivity` computes that number rather than asserting it. It is
the single largest assumption in this lab and it is one a human can settle in
a minute by reading a book's prop rules, which is why it is surfaced rather
than buried.

## Where the edge actually lives

Split by the player's injury designation that week, the return is not uniform.
It concentrates in the players who are **not on the injury report at all** —
which is also the population whose availability is least in doubt. So the gate
and the edge want the same thing, and a rule of "bet only undesignated
players, and let the voids void" is both the safer policy and the more
profitable one.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


NOT_LISTED = "not on the report"
LISTED_NO_DESIGNATION = "listed, no designation"

#: Designations that are a definite exclusion rather than a risk to price.
EXCLUDING = frozenset({"Out"})


@dataclass
class DesignationResult:
    designation: str
    bets: int = 0
    voids: int = 0
    roi: float = 0.0

    @property
    def void_share(self) -> float:
        total = self.bets + self.voids
        return self.voids / total if total else 0.0


@dataclass
class AvailabilityResult:
    designations: list[DesignationResult] = field(default_factory=list)
    staked: int = 0
    voids: int = 0
    roi: float = 0.0

    @property
    def void_share(self) -> float:
        total = self.staked + self.voids
        return self.voids / total if total else 0.0

    def void_rule_sensitivity(self) -> float:
        """The pooled return **if a did-not-play were graded a loss**.

        Not a hypothetical worth skipping. It is the difference between a
        strategy and a disaster, it turns on one line in a book's rules, and
        no amount of modelling can settle it.
        """
        total = self.staked + self.voids
        if not total:
            return 0.0
        return (self.staked * self.roi - self.voids) / total


def measure(bets: pd.DataFrame, designations: pd.Series) -> AvailabilityResult:
    """`designations` maps each bet's index to that week's injury designation."""
    result = AvailabilityResult()
    if bets.empty:
        return result
    frame = bets.assign(designation=designations.fillna(NOT_LISTED))
    staked = frame[frame["outcome"] != "void"]
    voided = frame[frame["outcome"] == "void"]
    result.staked = len(staked)
    result.voids = len(voided)
    result.roi = float(staked["profit"].mean()) if len(staked) else 0.0

    for designation in sorted(frame["designation"].unique()):
        rows = staked[staked["designation"] == designation]
        result.designations.append(
            DesignationResult(
                designation=str(designation),
                bets=len(rows),
                voids=int((voided["designation"] == designation).sum()),
                roi=float(rows["profit"].mean()) if len(rows) else 0.0,
            )
        )
    result.designations.sort(key=lambda d: -d.bets)
    return result


def render(result: AvailabilityResult, *, market: str = "all markets") -> str:
    lines: list[str] = []
    add = lines.append
    add(f"# What does not knowing who will play cost? — {market}")
    add("")
    add(
        "This lab has refused to let any player prop produce a selection, "
        "because inactives are declared ninety minutes before kickoff and no "
        "available feed publishes them. Measured, that reasoning does not "
        "hold — and the reason is the settlement rule, not the model."
    )
    add("")
    add(
        f"**{result.void_share:.1%} of selections voided** — the player did "
        "not appear in the box score. A book returns the stake on those, so "
        "the question 'will he play?' is not a question about whether the bet "
        "wins. It is a question about whether there is a bet at all, and a bet "
        "that never existed costs nothing."
    )
    add("")
    add("| Designation that week | Bets | Voids | Void share | ROI |")
    add("|:----------------------|-----:|------:|-----------:|----:|")
    for entry in result.designations:
        add(
            f"| {entry.designation} | {entry.bets:,} | {entry.voids:,} | "
            f"{entry.void_share:.1%} | {entry.roi:+.1%} |"
        )
    add(
        f"| **all** | {result.staked:,} | {result.voids:,} | "
        f"{result.void_share:.1%} | {result.roi:+.1%} |"
    )
    add("")
    add("## The assumption this all rests on")
    add("")
    add(
        "**Everything above assumes a book voids a did-not-play prop rather "
        "than grading it a loss.** That is the standard rule — no action if "
        "the player does not take a snap — and it is a rule, not a law of "
        "nature."
    )
    add("")
    add(
        f"If a book graded those {result.voids:,} as losses, this record would "
        f"be **{result.void_rule_sensitivity():+.1%}** rather than "
        f"**{result.roi:+.1%}**."
    )
    add("")
    add(
        "That is the difference between a strategy and a disaster, it turns "
        "on one line in a book's rules, and no amount of modelling can settle "
        "it. **It is a question for a human with an account**, and it should "
        "be answered before anything here is acted on."
    )
    return "\n".join(lines) + "\n"
