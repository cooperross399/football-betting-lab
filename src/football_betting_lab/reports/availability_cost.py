"""What does not knowing who will play actually cost?

## The gate this re-examines

This lab has refused to let any player prop produce a selection, on the
grounds that inactives are declared ninety minutes before kickoff and no
available feed publishes them. The reasoning was the NHL lab's goalie-saves
rule: a market you cannot confirm is a market you cannot bet.

**Measured, that reasoning does not hold for player props, and the reason is
the settlement rule rather than anything about the model.**

A player who does not take a snap does not lose the bet. The book **voids** it
and returns the stake — read from the rule text on 2026-09-23 rather than
assumed, `docs/did_not_play_rules.md`, with Bovada the one exception in this
lab's feed. So the question "will he play?" is not a question about
whether the bet wins — it is a question about whether there is a bet at all,
and a bet that never existed costs nothing.

Over three bought seasons, **2.2% of the model's selections voided**. That is
a large number and it is financially a non-event.

## The assumption this rests on, and what it is worth

**Everything above assumes the book voids a did-not-play prop rather than
grading it a loss.** That is the standard rule — no action if the player does
not take a snap — and it is a rule, not a law of nature. Books differ, and a
book that graded those as losses would turn the same record from **−3.7% into
−5.8%** across all markets.

An earlier version of this docstring quoted +13.0% against −0.8% and called
that the difference between a strategy and a disaster. It was, and the numbers
were computed on cross-season-settled bets. The clause still deserves an
answer before a live card; nothing waits on it any more.

`void_rule_sensitivity` computes that number rather than asserting it. It is
the single largest assumption in this lab and it is one a human can settle in
a minute by reading a book's prop rules, which is why it is surfaced rather
than buried.

**It was settled on 2026-09-23 and it is no longer an assumption.**
`docs/did_not_play_rules.md` holds the rule text, book by book, from state
regulator filings where the operator files one. Books void, symmetrically.
The one exception is **Bovada**, which keys on the game-day active roster and
grades a player who is active and never plays — so the figures here describe
every book in the feed except the one they are most likely to be acted on at.

## How the designation is joined, and the failure it used to have

`run_availability_cost.py` built this table by joining
`injuries["full_name"].casefold()` to the bet's player string until
2026-09-23 — the same name-string join the hardening audit condemned in
`props_backtest.py` and that was fixed there. It missed every suffix and
punctuation variant the two feeds spell differently, 228 bets on 10 players,
34 of them **Questionable**. It also failed **open**: `measure` fills a missed
join with `NOT_LISTED`, so a player who was on the report became a player who
looked unencumbered — the exact bucket
`props_selectable_when_undesignated` would make selectable. It joins on
`gsis_id` now. Questionable was +6.2% before the fix and is +3.3% after it.

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


REGULAR_SEASON = "REG"
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


def regular_season_rows(injuries: pd.DataFrame) -> pd.DataFrame:
    """Injury rows for regular-season weeks, across files that disagree on schema.

    `season_type` is absent from injuries_2022/2023/2024.csv and present in
    2025/2026 — nflverse added it partway through. Concatenating them and then
    writing `injuries[injuries["season_type"] == "REG"]` drops every row from
    the older files, because theirs is NaN and NaN never equals "REG". That is
    what `run_availability_cost.py` did until 2026-09-23: **5,794 rows survived
    of 23,575**, the lookup saw 2025 and 2026 only, and the bets span 2023-2025.

    It failed in the direction that hides it. An unmatched bet fills as
    `NOT_LISTED`, so two entire seasons landed in "not on the report" — the
    largest bucket, and the one a shipped `props_selectable_when_undesignated`
    would open. The table looked plausible and its only positive cell, a
    Questionable ROI of +3.3%, was computed on a third of the population; on
    the whole of it that cell is -6.0%.

    An absent value means the file predates the column, not that the row is
    postseason, so it is kept. A row that says `POST` is dropped.
    """
    if injuries.empty or "season_type" not in injuries.columns:
        return injuries
    kind = injuries["season_type"]
    return injuries[kind.isna() | (kind.astype(str).str.strip() == REGULAR_SEASON)]


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


def render(
    result: AvailabilityResult, *, market: str = "all markets", coverage: str = ""
) -> str:
    lines: list[str] = []
    add = lines.append
    add(f"# What does not knowing who will play cost? — {market}")
    add("")
    if coverage:
        add(coverage)
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
        "**That question has been answered.** `docs/did_not_play_rules.md`, "
        "2026-09-23: books void a did-not-play prop and void it symmetrically, "
        "on the over and the under alike. The rule text was read from "
        "state-regulator house-rules filings for DraftKings, FanDuel, BetMGM, "
        "Caesars, Fanatics and ESPN Bet, and from the operators' own pages for "
        "Pinnacle and Bovada. bet365 and BetRivers could not be obtained and "
        "are recorded as unverified rather than assumed."
    )
    add("")
    add(
        "**Bovada is the exception, and it is in this lab's feed.** It keys on "
        "the game-day active roster rather than on snaps: a player who is "
        "active and never takes a snap is **graded**, so an over loses and an "
        "under at zero wins. The void arithmetic above does not describe a "
        "Bovada card. Of the eleven books in the quote store, five were read "
        "directly — **four void and Bovada grades**. Three more match a "
        "researched operator only under a legacy provider key, on a mapping "
        "that is an assumption rather than a checked fact. Three are "
        "unresearched."
    )
    return "\n".join(lines) + "\n"
