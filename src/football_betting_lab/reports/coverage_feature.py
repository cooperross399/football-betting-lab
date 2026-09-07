"""Man-coverage rate faced: the first opponent term the props model has ever had.

`fit_rates` builds a player's rates from his own history and `simulate` draws
from them, so today the model gives the same distribution for a receiver facing
the league's heaviest man defence and its heaviest zone one. This module builds
the simplest opponent term there is — the share of charted dropbacks a defence
played in man — so that `run_coverage_encompassing.py` can ask the only
question that decides whether it is worth wiring in: does it carry anything the
closing price does not already hold?

## Three rules this file exists to enforce

**The rate is the PRIOR season's, always.** nflverse publishes participation
once, after the post-season, so a live card could never have the current
season's rate anyway — but the reason to enforce it is leakage, not
availability. A same-season rate is computed partly from the game being
predicted. `attach_prior_season_man_rate` raises rather than trusts a caller.

**The opponent is read from rosters and the schedule, never from a stat line.**
Joining through `stats_player_week` looks equivalent and matched 96.7% of
receiving wagers here — but the 3.3% it misses are players who recorded no
receiving line that week, which is exactly the population whose unders won.
Deriving a join key from a table conditioned on the outcome selects on the
outcome. Rosters and the schedule know who played whom regardless of what
happened, and match 100%.

**A missing rate is reported, never dropped quietly.** A feature that silently
covers three quarters of the rows is a feature measured on a subpopulation
nobody named.

## The raw rate is not comparable across seasons, and that is not football

League-mean man rate by season, measured 2026-09-07 from the participation
files: **2022 0.286, 2023 0.423, 2024 0.492, 2025 0.318** — swings of +13.7,
+6.9 and **-17.4** percentage points between consecutive seasons. Thirty-two
defences do not collectively abandon seventeen points of man coverage in one
offseason. That is drift in how the NGS charting classifies coverage, not a
change in how football is played.

So the feature is the **within-season z-score**, never the raw rate. A raw
prior-season rate compared against a current-season one is read off two
different rulers, and centring it globally would make the regressor partly an
indicator of which season the wager came from — which would then be picked up
as coverage information. `man_rate_z` asks the football question instead: how
man-heavy was this defence relative to the defences charted beside it.

Anyone using these coverage rates across seasons — including a vendor quoting
"this defence plays 76% zone" — inherits this. Compare within a season only.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


MAN = "MAN_COVERAGE"
ZONE = "ZONE_COVERAGE"

#: A defence-season below this many charted dropbacks gives a rate too noisy to
#: be a feature. Every 2025 club charted between 553 and 867, so this excludes
#: nothing in practice and refuses a partial file rather than averaging it in.
MIN_CHARTED_DROPBACKS = 200

RECEIVING_MARKETS = ("reception_yards", "receptions", "reception_longest")


def defence_of_each_play(participation: pd.DataFrame) -> np.ndarray:
    """The defending club: the side of the game id that is not in possession.

    `nflverse_game_id` is `{season}_{week}_{away}_{home}`.
    """
    parts = participation["nflverse_game_id"].astype(str).str.split("_")
    away, home = parts.str[2], parts.str[3]
    return np.where(participation["possession_team"].astype(str) == away, home, away)


def man_rate_by_defence(participation: pd.DataFrame) -> pd.DataFrame:
    """Man share of charted dropbacks, per defence per season.

    The denominator is charted dropbacks, not plays. Coverage is charted on
    dropbacks only — 22,055 of 45,184 rows in 2025 — so dividing by plays
    would halve every rate while looking perfectly reasonable.
    """
    charted = participation[
        participation["defense_man_zone_type"].isin([MAN, ZONE])
    ].copy()
    if charted.empty:
        raise ValueError("No charted man/zone plays. Wrong file, or an empty column.")
    charted["defence"] = defence_of_each_play(charted)
    charted["season"] = (
        charted["nflverse_game_id"].astype(str).str.split("_").str[0].astype(int)
    )
    charted["is_man"] = (charted["defense_man_zone_type"] == MAN).astype(float)
    rates = (
        charted.groupby(["season", "defence"])
        .agg(charted_dropbacks=("is_man", "size"), man_rate=("is_man", "mean"))
        .reset_index()
    )
    rates = rates[rates["charted_dropbacks"] >= MIN_CHARTED_DROPBACKS].copy()
    # Standardised WITHIN season. See the module docstring: the league mean
    # moves up to 17 points between consecutive seasons, which is the charting
    # changing rather than the football.
    grouped = rates.groupby("season")["man_rate"]
    rates["man_rate_z"] = (rates["man_rate"] - grouped.transform("mean")) / grouped.transform(
        "std", ddof=0
    )
    return rates


def opponent_of_each_wager(
    bets: pd.DataFrame, rosters: pd.DataFrame, schedule: pd.DataFrame
) -> pd.DataFrame:
    """Attach the club a wager's player played for and the club he faced.

    Neither source knows anything about how the wager settled.
    """
    roster = (
        rosters.dropna(subset=["gsis_id"])
        .rename(columns={"gsis_id": "player_id"})
        .drop_duplicates(["player_id", "season", "week"])[
            ["player_id", "season", "week", "team"]
        ]
    )
    regular = schedule[schedule["game_type"] == "REG"]
    both_ways = pd.concat(
        [
            regular.rename(columns={"home_team": "team", "away_team": "opponent"}),
            regular.rename(columns={"away_team": "team", "home_team": "opponent"}),
        ]
    )[["season", "week", "team", "opponent"]]
    before = len(bets)
    out = bets.merge(roster, on=["player_id", "season", "week"], how="left").merge(
        both_ways, on=["season", "week", "team"], how="left"
    )
    if len(out) != before:
        raise ValueError(
            f"The opponent join changed the row count ({before} -> {len(out)}). "
            "A duplicated wager makes every interval below too narrow."
        )
    return out


def attach_prior_season_man_rate(
    frame: pd.DataFrame, rates: pd.DataFrame
) -> pd.DataFrame:
    """Attach the opponent defence's man rate from the season BEFORE the wager.

    Raises rather than trusting the caller, because a same-season rate is
    computed partly from the game being predicted and the resulting `d` would
    be a measurement of the leak.
    """
    wanted = frame.copy()
    wanted["rate_season"] = wanted["season"].astype(int) - 1
    if not (wanted["rate_season"] < wanted["season"]).all():
        raise ValueError("A man rate must come from a season before the wager.")
    before = len(wanted)
    out = wanted.merge(
        rates.rename(columns={"season": "rate_season", "defence": "opponent"}),
        on=["rate_season", "opponent"],
        how="left",
    )
    if len(out) != before:
        raise ValueError(
            f"The man-rate join changed the row count ({before} -> {len(out)})."
        )
    return out
