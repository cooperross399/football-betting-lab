"""When a team-mate is ruled out, does the volume he leaves reach a price?

Every feature tested here before this one asked whether a STABLE TRAIT carries
information the closing line lacks — man coverage, a receiver's man/zone split,
EPA ratings, pass-rush pressure. All four returned nothing, and the pattern was
consistent enough to be the finding: **a trait that persists is a trait the
market has had years to price.**

This asks the opposite question. A role change is not a trait. It is an event,
it is absent from the player's own history by construction, and it is therefore
the one thing the props model **cannot** see: `fit_rates` builds a player's
rates from what he has done, and what he has done was measured while somebody
else was taking those targets.

## The mechanism, measured before any price was involved

Volume genuinely moves. Regressing a player's week-W share gain on the
proportional redistribution he would receive if the vacated share were split
pro rata gives **+0.220, 95% [+0.113, +0.326]** over 11,856 player-weeks.
Not the 1.0 of pure proportional redistribution — teams promote a specific
back-up and change what they run — but firmly above zero. In level terms, the
mean share gain is +0.0182 when almost nothing is vacated and +0.0425 when more
than 15% is, a difference of about **0.85 targets a game** on a 35-attempt
offence.

That is the first stage this lab now runs before any market test, and it is the
first feature to pass it.

## What could make it worthless anyway

The market is not blind. A starting receiver ruled out is public, on the wire,
48 hours early. So this measures whether the line moves *enough*, not whether
it moves — and a null here would be an ordinary result, not a surprise.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: Positions whose absence frees passing volume for the players who remain.
RECEIVING_POSITIONS = ("WR", "TE", "RB", "FB")

#: The card prices about six hours before kickoff, so anything the injury feed
#: learned later than that was not knowable when the wager was placed. Measured
#: over 2022-2025: 94.6% of `Out` designations are filed at least 24 hours out
#: and only 5 of 3,129 land inside this window, so the guard costs almost
#: nothing and removes the only path by which this feature could see forward.
CARD_LEAD_HOURS = 6.0

#: Below this many prior weeks a baseline share is a rumour, not a rate.
MIN_WEEKS_BEFORE = 3

#: A player holding under this share has no role for an absence to expand.
MIN_BASELINE_SHARE = 0.02


def kickoffs(schedule: pd.DataFrame) -> pd.DataFrame:
    """One kickoff per club-week, so an injury row can be timed against it."""
    regular = schedule[schedule["game_type"] == "REG"].copy()
    regular["kickoff"] = pd.to_datetime(
        regular["gameday"].astype(str) + " " + regular["gametime"].fillna("13:00"),
        errors="coerce",
    )
    return pd.concat([
        regular.rename(columns={"home_team": "team"})[["season", "week", "team", "kickoff"]],
        regular.rename(columns={"away_team": "team"})[["season", "week", "team", "kickoff"]],
    ], ignore_index=True).dropna(subset=["kickoff"])


def ruled_out_by_card_time(
    injuries: pd.DataFrame, schedule: pd.DataFrame, *, lead_hours: float = CARD_LEAD_HOURS
) -> pd.DataFrame:
    """Players listed `Out` early enough that a card could have known.

    A row the feed modified after the card priced is not information, it is
    hindsight, and this is the only place that distinction can be enforced.
    """
    frame = injuries[
        (injuries["game_type"] == "REG")
        & (injuries["report_status"] == "Out")
        & injuries["position"].isin(RECEIVING_POSITIONS)
    ].copy()
    frame["modified"] = pd.to_datetime(
        frame["date_modified"], errors="coerce", utc=True
    ).dt.tz_localize(None)
    frame = frame.merge(kickoffs(schedule), on=["season", "week", "team"], how="left")
    lead = (frame["kickoff"] - frame["modified"]).dt.total_seconds() / 3600.0
    # A missing timestamp cannot be shown to precede the card, and "cannot be
    # shown" is treated as "did not" everywhere else in this lab.
    frame = frame[lead >= lead_hours]
    return frame.rename(columns={"gsis_id": "player_id", "team": "club"})[
        ["season", "week", "club", "player_id"]
    ].dropna().drop_duplicates()


def target_shares(pbp: pd.DataFrame) -> pd.DataFrame:
    """Each receiver's share of his club's targets, and his share before today.

    Built on a full club-week grid rather than on the weeks a player was
    targeted. A player who is OUT has no target row at all, so a grid keyed on
    appearances gives him no baseline — and a vacated-share built from that
    join is silently zero for every absence it exists to measure. That is
    exactly what the first version of this did.
    """
    targets = pbp[
        (pbp["season_type"] == "REG")
        & (pbp["pass_attempt"] == 1)
        & pbp["receiver_player_id"].notna()
    ]
    played = (
        targets.groupby(["season", "week", "posteam", "receiver_player_id"])
        .size().rename("targets").reset_index()
    )
    club = (
        played.groupby(["season", "week", "posteam"])["targets"]
        .sum().rename("club_targets").reset_index()
    )
    everyone = played[["season", "posteam", "receiver_player_id"]].drop_duplicates()
    grid = everyone.merge(club, on=["season", "posteam"]).merge(
        played, on=["season", "week", "posteam", "receiver_player_id"], how="left"
    )
    grid["targets"] = grid["targets"].fillna(0.0)
    grid = grid.sort_values(["season", "posteam", "receiver_player_id", "week"])
    grouped = grid.groupby(["season", "posteam", "receiver_player_id"])
    grid["prior_targets"] = grouped["targets"].cumsum() - grid["targets"]
    grid["prior_club"] = grouped["club_targets"].cumsum() - grid["club_targets"]
    grid["weeks_before"] = grouped.cumcount()
    grid["baseline_share"] = np.where(
        grid["prior_club"] > 0, grid["prior_targets"] / grid["prior_club"], np.nan
    )
    return grid.rename(columns={"posteam": "club", "receiver_player_id": "player_id"})[
        ["season", "week", "club", "player_id", "baseline_share", "weeks_before"]
    ]


def vacated_share(shares: pd.DataFrame, ruled_out: pd.DataFrame) -> pd.DataFrame:
    """Share of a club's targets held by the players it has ruled out."""
    joined = ruled_out.merge(
        shares[["season", "week", "club", "player_id", "baseline_share"]],
        on=["season", "week", "club", "player_id"], how="inner",
    )
    return (
        joined.groupby(["season", "week", "club"])["baseline_share"]
        .sum().rename("vacated").reset_index()
    )


def attach(bets: pd.DataFrame, shares: pd.DataFrame, vacated: pd.DataFrame,
           ruled_out: pd.DataFrame) -> pd.DataFrame:
    """Add each wager's baseline share, its club's vacated share, and the gain.

    `expected_gain` is the share a pro-rata split would hand this player:
    `baseline * vacated / (1 - vacated)`. The measured redistribution is 0.22 of
    that rather than 1.0, but a constant multiple is annihilated by the
    standardisation the fit applies, so it is left unscaled.
    """
    before = len(bets)
    out = bets.rename(columns={"team": "club"}).merge(
        shares, on=["season", "week", "club", "player_id"], how="left"
    ).merge(vacated, on=["season", "week", "club"], how="left")
    if len(out) != before:
        raise ValueError(
            f"The role join changed the row count ({before} -> {len(out)}). "
            "A duplicated wager makes every interval too narrow."
        )
    out["vacated"] = out["vacated"].fillna(0.0)
    # A wager on a player his own club has ruled out is not a role-change bet.
    marked = ruled_out.assign(_out=1)
    out = out.merge(marked, on=["season", "week", "club", "player_id"], how="left")
    out = out[out["_out"].isna()].drop(columns=["_out"])
    out["expected_gain"] = (
        out["baseline_share"] * out["vacated"] / (1.0 - out["vacated"]).clip(lower=1e-6)
    )
    return out
