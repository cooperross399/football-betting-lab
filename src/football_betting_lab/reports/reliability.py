"""Does a feature correlate with itself? Ask before asking whether it beats a price.

Three matchup features were measured against the closing line before anyone
measured them against themselves, and all three returned nothing. Every one of
those nulls was predictable in minutes from free data: a receiver's man-minus-
zone differential carries r = +0.13 season to season, and a defence's man rate
r = +0.44. **A feature that cannot reproduce itself cannot predict anything**,
and no amount of shrinkage, interaction or clustering rescues it.

So this runs first. It is cheap, it involves no price, and it puts a ceiling on
what any downstream test could possibly find.

## Two questions, and they are not the same

**Split-half** (odd weeks against even, same season) asks how noisy the
*measurement* is. Spearman-Brown lifts it to a full season, because a
half-season correlation understates what a whole one would give.

**Year over year** asks how much of the thing *persists* — and for a feature
built from the prior season, which is all a live card can have, this is the one
that governs. It is always the lower of the two and often much lower: a
statistic can be measured precisely and still describe a team that no longer
exists.

Report both. A high split-half with a zero carryover means "we measure last
year's team perfectly, and last year's team has left".

## What a reader must not do with these numbers

A correlation near zero is not proof the underlying thing is irrelevant to
football. It is proof that *this measurement of it, at this sample size*,
carries almost nothing — which is the only question that matters before
spending a season's credits on it.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


#: Carryover of RELATIVE position, measured 2026-09-07 by
#: `scripts/run_feature_reliability.py` and pinned here so a board cannot quote
#: a weight the report no longer supports. A test checks these against the
#: committed report; they are not to be edited by hand.
MEASURED: dict[str, float] = {
    "pressures per game (defender)": 0.884,
    "average depth of target faced (defender)": 0.782,
    "yards before contact per rush": 0.674,
    "broken tackles per game (rusher)": 0.645,
    "blitz rate, 5+ rushers (defence)": 0.548,
    "yards after contact per rush": 0.500,
    "completion % allowed (defender)": 0.458,
    "pressure rate generated (defence)": 0.439,
    "man coverage rate (defence)": 0.435,
    "bad throw % (quarterback)": 0.435,
    "broken tackles per game (receiver)": 0.414,
    "pressure rate faced (quarterback)": 0.391,
    "times blitzed per game (quarterback)": 0.372,
    "sacks taken per game (quarterback)": 0.372,
    "time to throw allowed (defence)": 0.327,
    "passer rating when targeted (receiver)": 0.251,
    "missed tackle % (defender)": 0.210,
    "yards allowed per target (defender)": 0.172,
    "defenders in box (defence)": 0.152,
    "passer rating allowed (defender)": 0.125,
    "drop % (receiver)": 0.078,
}


@dataclass(frozen=True)
class Reliability:
    """One feature's self-agreement. `None` means it could not be measured."""

    name: str
    entity_seasons: int
    split_half: float | None
    full_season: float | None
    half_pairs: int
    year_over_year: float | None
    year_pairs: int
    #: The same carryover after standardising within season — whether a team or
    #: player keeps its RELATIVE position, with any league-wide shift removed.
    year_over_year_ranked: float | None

    @property
    def ceiling(self) -> float | None:
        """The number that governs a prior-season feature.

        The ranked one, not the raw one. A live card carries the prior season's
        value and a model's intercept absorbs any league-wide level change, so
        what has to persist is a team's position relative to its peers.
        """
        return self.year_over_year_ranked

    @property
    def drifts(self) -> bool:
        """Whether the league-wide level moved enough to hide the persistence.

        `man coverage rate` measures +0.017 raw and +0.435 ranked: the league
        mean went 0.286, 0.423, 0.492, 0.318 across four seasons, so the raw
        correlation is reading a rule or charting change rather than the teams.
        Any feature where these two disagree is being measured with two
        different rulers, and only the ranked number means anything.
        """
        if self.year_over_year is None or self.year_over_year_ranked is None:
            return False
        return abs(self.year_over_year_ranked - self.year_over_year) >= 0.15

    @property
    def verdict(self) -> str:
        governing = self.ceiling
        if governing is None:
            return "not measurable"
        if governing < 0.20:
            return "**too noisy to carry a signal**"
        if governing < 0.40:
            return "weak"
        return "usable"


def _aggregate(frame: pd.DataFrame, keys: list[str], minimum: float) -> pd.DataFrame:
    """Weighted mean of `value` per group, dropping groups below `minimum`."""
    grouped = frame.groupby(keys, dropna=True)
    weight = grouped["weight"].sum()
    total = grouped.apply(
        lambda part: float((part["value"] * part["weight"]).sum()), include_groups=False
    )
    out = pd.DataFrame({"weight": weight, "total": total}).reset_index()
    out = out[out["weight"] >= minimum].copy()
    out["value"] = out["total"] / out["weight"]
    return out


def _correlate(left: pd.Series, right: pd.Series) -> tuple[float | None, int]:
    paired = pd.DataFrame({"a": left, "b": right}).dropna()
    # Two points always correlate perfectly and say nothing. Ten is already
    # generous for a number this load-bearing.
    if len(paired) < 10 or paired["a"].std() == 0 or paired["b"].std() == 0:
        return None, len(paired)
    return float(paired["a"].corr(paired["b"])), len(paired)


def measure(
    frame: pd.DataFrame,
    name: str,
    *,
    minimum: float,
    half_minimum: float | None = None,
) -> Reliability:
    """`frame` carries entity, season, week, value, weight — one row per game.

    `weight` is the denominator the rate was measured over: targets, dropbacks,
    plays. A season value is the weight-weighted mean, never the mean of the
    per-game rates, because a two-target game must not count as much as a
    twelve-target one.
    """
    needed = {"entity", "season", "week", "value", "weight"}
    missing = needed - set(frame.columns)
    if missing:
        raise ValueError(f"{name}: missing {sorted(missing)}")
    frame = frame.dropna(subset=["value", "weight"])
    frame = frame[frame["weight"] > 0]
    if frame.empty:
        return Reliability(name, 0, None, None, 0, None, 0, None)

    seasonal = _aggregate(frame, ["entity", "season"], minimum)

    halved = frame.assign(half=np.where(frame["week"] % 2 == 1, "odd", "even"))
    halves = _aggregate(
        halved, ["entity", "season", "half"],
        half_minimum if half_minimum is not None else minimum / 2,
    )
    wide = halves.pivot_table(index=["entity", "season"], columns="half", values="value")
    half_r, half_pairs = (
        _correlate(wide["odd"], wide["even"])
        if {"odd", "even"} <= set(wide.columns) else (None, 0)
    )
    # Spearman-Brown. Undefined at r = -1, and meaningless below zero: a
    # negative half-correlation does not become a positive whole one.
    full = None
    if half_r is not None and half_r > 0:
        full = 2.0 * half_r / (1.0 + half_r)

    # Standardised within season as well as raw. A league-wide shift — a rule
    # change, a charting change — moves every team at once and destroys the raw
    # correlation while every team holds its place. Only the ranked number
    # answers "does the prior season tell me who is who".
    grouped = seasonal.groupby("season")["value"]
    spread = grouped.transform("std")
    seasonal["ranked"] = np.where(
        spread > 0, (seasonal["value"] - grouped.transform("mean")) / spread, np.nan
    )

    def carryover(column: str) -> tuple[float | None, int]:
        lookup = {
            (row.entity, row.season): getattr(row, column)
            for row in seasonal.itertuples()
        }
        earlier, later = [], []
        for (entity, season), value in lookup.items():
            following = lookup.get((entity, season + 1))
            if following is not None:
                earlier.append(value)
                later.append(following)
        return _correlate(pd.Series(earlier), pd.Series(later))

    yoy, year_pairs = carryover("value")
    ranked, _ = carryover("ranked")

    return Reliability(
        name=name,
        entity_seasons=len(seasonal),
        split_half=half_r,
        full_season=full,
        half_pairs=half_pairs,
        year_over_year=yoy,
        year_pairs=year_pairs,
        year_over_year_ranked=ranked,
    )


def render(results: list[Reliability]) -> str:
    """Ranked worst-last, because the point is which features are worth a test."""
    ordered = sorted(results, key=lambda r: (r.ceiling is None, -(r.ceiling or 0.0)))
    lines = [
        "| feature | entity-seasons | split-half | full season | carryover, raw | "
        "carryover, ranked | pairs | verdict |",
        "|:--|--:|--:|--:|--:|--:|--:|:--|",
    ]
    for r in ordered:
        def show(value: float | None) -> str:
            return "—" if value is None else f"{value:+.3f}"
        flag = " ⚠︎" if r.drifts else ""
        lines.append(
            f"| {r.name}{flag} | {r.entity_seasons:,} | {show(r.split_half)} | "
            f"{show(r.full_season)} | {show(r.year_over_year)} | "
            f"**{show(r.year_over_year_ranked)}** | {r.year_pairs:,} | {r.verdict} |"
        )
    drifting = [r.name for r in ordered if r.drifts]
    if drifting:
        lines += [
            "",
            "⚠︎ **The two carryover columns disagree by 0.15 or more**, which "
            "means the league-wide level moved between seasons and the raw "
            "number is reading that shift rather than the teams: "
            + ", ".join(f"*{name}*" for name in drifting)
            + ". Only the ranked column means anything for these.",
        ]
    return "\n".join(lines)
