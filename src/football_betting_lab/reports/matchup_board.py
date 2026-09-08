"""A matchup board: the layers, on data this lab can audit, beside the price.

This is deliberately **not** an edge board, and the distinction is the whole
point. Six features built from exactly these feeds have been tested against the
closing line and every one returned no demonstrated edge. So a layer agreeing
with another layer here is context, not a signal, and the board says so on its
face rather than in a footnote.

## What it adds to the thing it is modelled on

**A price.** The board this was built from carries the line "no lines or prices
included", and a matchup read without a price is a lean, not an edge — there is
no way to tell a good team from a good bet without the number. The spread, the
total and both implied totals come from the nflverse schedule at no cost.

**A reliability weight on every layer.** Each row carries the carryover of
relative position measured for that statistic, so a reader can see that
`pressures per game` describes the same defender a year later at +0.884 while
`passer rating allowed` — the shadow-corner number every preview quotes — does
so at +0.125 and is close to noise. A board that prints its weakest layer in
the same typeface as its strongest is inviting the reader to average them.

## What is missing, and why

**Player prop prices.** They come from a paid provider and are not fetched
here. The game markets are free; the player markets are not, and nothing on
this board pretends to price them.

**The role and injury layer.** Week 1 report statuses are not filed until the
Wednesday. Until they are, the vacated-volume feature has nothing to read, and
an empty layer is shown as empty rather than filled with zeroes that would read
as "nobody is hurt".

**Coach and player quotes.** Proprietary to a vendor, with no free equivalent,
and the layer with the least evidence behind it — the source board notes its
own feed skews positive for every team, which is the shape of a signal that
cannot discriminate.

All profile statistics are the **prior season**, because for Week 1 that is
what exists. They are z-scored within the season, never raw: league-wide levels
move between seasons and a raw number is two different rulers.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from football_betting_lab.reports import coverage_feature as cov
from football_betting_lab.reports.reliability import MEASURED


@dataclass(frozen=True)
class Layer:
    """One column of the board, and how well it describes the same team twice."""

    key: str
    label: str
    reliability_of: str
    #: True when a high value favours the DEFENCE in the matchup arithmetic.
    helps_defence: bool

    @property
    def reliability(self) -> float:
        return MEASURED[self.reliability_of]


LAYERS: tuple[Layer, ...] = (
    Layer("pressure_gen", "pressure rate generated", "pressure rate generated (defence)", True),
    Layer("pressure_allowed", "pressure rate allowed", "pressure rate faced (quarterback)", False),
    Layer("man_rate", "man coverage rate", "man coverage rate (defence)", True),
    Layer("blitz_rate", "blitz rate, 5+", "blitz rate, 5+ rushers (defence)", True),
    Layer("comp_allowed", "completion % allowed", "completion % allowed (defender)", True),
    Layer("adot_faced", "average depth of target faced", "average depth of target faced (defender)", True),
    Layer("ybc", "rush yards before contact", "yards before contact per rush", False),
    Layer("yac_rush", "rush yards after contact", "yards after contact per rush", False),
)


def _z(frame: pd.DataFrame, column: str) -> pd.Series:
    values = pd.to_numeric(frame[column], errors="coerce")
    spread = values.std(ddof=0)
    return (values - values.mean()) / spread if spread else values * 0.0


def team_profiles(
    participation: pd.DataFrame, pfr_pass: pd.DataFrame,
    pfr_def: pd.DataFrame, pfr_rush: pd.DataFrame,
) -> pd.DataFrame:
    """One row per club: last season's profile, standardised across the league."""
    plays = participation.copy()
    plays["defence"] = cov.defence_of_each_play(plays)
    plays["rushers"] = pd.to_numeric(plays["number_of_pass_rushers"], errors="coerce")
    plays["pressure"] = pd.to_numeric(plays["was_pressure"], errors="coerce")
    # **Per dropback, never per play.** `was_pressure` is False on every run, so
    # a mean over all plays is the pressure rate multiplied by how often the
    # defence faced a pass — 0.147 against the true 0.301 in 2025 — and the
    # multiplier is a fact about the opposing offences, not about the rush.
    # The feed's own docstring says this and the first version of this board
    # still did it.
    dropbacks = plays[plays["defense_man_zone_type"].notna()]
    charted = plays[plays["defense_man_zone_type"].isin(cov.MAN_LABELS)]

    defence = pd.DataFrame({
        "pressure_gen": dropbacks.groupby("defence")["pressure"].mean(),
        "blitz_rate": dropbacks.groupby("defence")["rushers"].apply(
            lambda s: float((s >= 5).mean())
        ),
        "man_rate": charted.groupby("defence")["defense_man_zone_type"].apply(
            lambda s: float((s == cov.MAN).mean())
        ),
    })

    def weighted(frame: pd.DataFrame, value: str, weight: str | None) -> pd.Series:
        frame = frame.copy()
        frame[value] = pd.to_numeric(frame[value], errors="coerce")
        if weight is None:
            return frame.groupby("team")[value].mean()
        frame[weight] = pd.to_numeric(frame[weight], errors="coerce")
        frame = frame.dropna(subset=[value, weight])
        totals = frame.groupby("team").apply(
            lambda part: float((part[value] * part[weight]).sum() / part[weight].sum())
            if part[weight].sum() else np.nan,
            include_groups=False,
        )
        return totals

    # `pfr_def` rows are per DEFENDER, so the club column is the defence.
    profile = defence.join([
        weighted(pfr_pass, "times_pressured_pct", None).rename("pressure_allowed"),
        weighted(pfr_def, "def_completion_pct", "def_targets").rename("comp_allowed"),
        weighted(pfr_def, "def_adot", "def_targets").rename("adot_faced"),
        weighted(pfr_rush, "rushing_yards_before_contact_avg", "carries").rename("ybc"),
        weighted(pfr_rush, "rushing_yards_after_contact_avg", "carries").rename("yac_rush"),
    ], how="outer")
    profile.index.name = "team"
    profile = profile.reset_index().dropna(subset=["team"])
    for layer in LAYERS:
        profile[f"{layer.key}_z"] = _z(profile, layer.key)
    return profile.set_index("team")


def implied_totals(spread_line: float, total_line: float) -> tuple[float, float]:
    """(home, away). `spread_line > 0` means the home side is favoured by it."""
    return (total_line + spread_line) / 2.0, (total_line - spread_line) / 2.0


def board(schedule: pd.DataFrame, profiles: pd.DataFrame, *, season: int, week: int) -> pd.DataFrame:
    """One row per game, with both clubs' profiles and the market beside them."""
    games = schedule[
        (schedule["season"] == season)
        & (schedule["week"] == week)
        & (schedule["game_type"] == "REG")
    ].copy()
    rows = []
    for game in games.itertuples():
        spread = float(game.spread_line) if pd.notna(game.spread_line) else np.nan
        total = float(game.total_line) if pd.notna(game.total_line) else np.nan
        home_implied, away_implied = (
            implied_totals(spread, total) if pd.notna(spread) and pd.notna(total)
            else (np.nan, np.nan)
        )
        row = {
            "kickoff": f"{game.gameday} {game.gametime}",
            "away": game.away_team, "home": game.home_team,
            "spread_line": spread, "total_line": total,
            "home_implied": home_implied, "away_implied": away_implied,
        }
        for side, club, opponent in (
            ("home", game.home_team, game.away_team),
            ("away", game.away_team, game.home_team),
        ):
            for layer in LAYERS:
                column = f"{layer.key}_z"
                row[f"{side}_{layer.key}"] = (
                    float(profiles.loc[club, column])
                    if club in profiles.index and pd.notna(profiles.loc[club, column])
                    else np.nan
                )
            # The pass-rush matchup: this club's rush against the pressure the
            # opponent's line has allowed. Both halves point the same way, so
            # they add rather than cancel.
            row[f"{side}_rush_edge"] = (
                row[f"{side}_pressure_gen"]
                + (
                    float(profiles.loc[opponent, "pressure_allowed_z"])
                    if opponent in profiles.index else np.nan
                )
            )
        rows.append(row)
    return pd.DataFrame(rows).sort_values("kickoff").reset_index(drop=True)
