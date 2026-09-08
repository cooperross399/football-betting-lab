"""Pressure is the most persistent thing this lab measures. Is any of it unpriced?

The reliability screen ranked twenty-one candidate features by whether they
describe the same player a year later. **Pressures per game by a defender came
first at +0.884**, in a different class from everything else — and the
receiver-grade layer that a matchup board leans on came last.

The hypothesis worth a real test is narrower than "pressure matters". It is:
**a sack line is priced off a defender's sack history, and sacks are a noisy
subset of pressures.** If pressures predict future sacks better than past sacks
do, and the market prices the noisier one, the difference is unpriced. That is
a mechanism, not a correlation, and it is the only reason to spend a
measurement here.

Two terms, because the mechanism has two sides: what the rusher does, and what
the line in front of him allows. Both come from the season BEFORE the wager,
which is all a live card could hold, and both are standardised within season
because the league-wide level moves and a raw carryover reads that shift
instead of the teams.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: Markets where a pass rush has a mechanism. `defensive_interceptions` is
#: excluded at 45 wagers: an interval from that is decorative.
DEFENSIVE_MARKETS = ("sacks", "tackles_assists")

#: A defender-season below this many games gives a per-game rate too noisy to
#: shrink usefully, and the gate is stated rather than discovered.
MIN_GAMES = 8


def crosswalk(players: pd.DataFrame) -> pd.DataFrame:
    """GSIS to PFR. Every other feed is GSIS-keyed; `pfr_advstats` is not.

    Rows without both are dropped rather than guessed at, and a PFR id serving
    two GSIS ids is dropped entirely — a crosswalk that silently fans out one
    wager into two is the join defect this repository has already retracted a
    result over.
    """
    needed = {"gsis_id", "pfr_id"}
    if not needed <= set(players.columns):
        raise ValueError(f"players feed is missing {sorted(needed - set(players.columns))}")
    pairs = players[["gsis_id", "pfr_id"]].dropna().drop_duplicates()
    counts = pairs.groupby("pfr_id")["gsis_id"].nunique()
    ambiguous = set(counts[counts > 1].index)
    return pairs[~pairs["pfr_id"].isin(ambiguous)].reset_index(drop=True)


def defender_pressure_rate(advstats: pd.DataFrame) -> pd.DataFrame:
    """Prior-season pressures per game, per defender, standardised in season."""
    frame = advstats.copy()
    frame["def_pressures"] = pd.to_numeric(frame["def_pressures"], errors="coerce")
    frame = frame.dropna(subset=["def_pressures", "pfr_player_id", "season"])
    grouped = frame.groupby(["season", "pfr_player_id"])
    out = grouped.agg(
        pressures=("def_pressures", "sum"), games=("def_pressures", "size")
    ).reset_index()
    out = out[out["games"] >= MIN_GAMES].copy()
    out["pressures_per_game"] = out["pressures"] / out["games"]
    return _standardise(out, "pressures_per_game", "pressure_z")


def offence_pressure_allowed(advstats: pd.DataFrame) -> pd.DataFrame:
    """Prior-season pressure rate allowed, per offence, standardised in season.

    Weighted by the games a quarterback started for the club, so a one-start
    backup does not carry the same weight as a season's starter.
    """
    frame = advstats.copy()
    frame["times_pressured_pct"] = pd.to_numeric(
        frame["times_pressured_pct"], errors="coerce"
    )
    frame = frame.dropna(subset=["times_pressured_pct", "team", "season"])
    out = (
        frame.groupby(["season", "team"])["times_pressured_pct"]
        .agg(["mean", "size"]).reset_index()
        .rename(columns={"mean": "pressure_allowed", "size": "quarterback_games"})
    )
    out = out[out["quarterback_games"] >= MIN_GAMES].copy()
    return _standardise(out, "pressure_allowed", "pressure_allowed_z")


def _standardise(frame: pd.DataFrame, column: str, name: str) -> pd.DataFrame:
    """Within season. The league-wide level moves; relative position is the
    thing a prior season can tell you about the next one."""
    grouped = frame.groupby("season")[column]
    spread = grouped.transform("std")
    frame[name] = np.where(
        spread > 0, (frame[column] - grouped.transform("mean")) / spread, np.nan
    )
    return frame
