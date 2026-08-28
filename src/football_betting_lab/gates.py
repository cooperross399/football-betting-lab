"""The gates that fail closed, and the states they distinguish.

Each is the analogue of the NHL lab's goalie-saves rule: that market is
modelled, calibrated and measured, and still cannot produce a selection,
because the lab has no confirmed-starter feed. Being unable to bet a market
you can price is not a defect. Pretending you can is.

## Availability, and why no player prop can produce a selection today

**Inactives are declared about ninety minutes before kickoff and nflverse
publishes no inactives feed.** What it publishes is the weekly injury report,
which lists only players carrying a designation.

That supports exclusion and not confirmation, and the states have to stay
separate because collapsing them is how a card starts lying:

``EXCLUDED``
    Listed `Out`. Definitive. No opinion is offered at all.
``DOUBTFUL`` / ``QUESTIONABLE``
    Designated, not ruled out. Books reprice on the Sunday-morning news; this
    lab cannot.
``UNDESIGNATED``
    A report exists for this team and week and the player is not on it. That
    is *evidence* of availability and it is **not confirmation** — healthy
    scratches and game-time decisions are not injuries.
``NO_REPORT``
    No injury report exists for this team and week at all. **This is not the
    same as undesignated**, and the difference is the one that matters most:
    a missing feed makes every player look healthy. Before Week 1 there is no
    2026 injury file at all, so every player is in this state, and a gate that
    read it as "nobody is injured" would wave through an entire slate.

**None of these is `CONFIRMED`, because nothing here can produce that state.**
So a player prop is priced, frozen into the forward ledger, and settled — and
it cannot produce a selection, and the card says so in those words.

If a legitimate inactives source is found later, `CONFIRMED` becomes
reachable, this gate opens, and the change is judged by the priced test rather
than by whether it feels better.

## Quarterback changes

A backup quarterback invalidates the whole passing and receiving tree for that
team: every target share, every yards-per-attempt rate, every rate the model
learned. Detecting it is not optional, and repricing on the backup would be
worse than abstaining — the model has no fitted knowledge of him.

So a team whose current depth-chart QB1 differs from the QB1 its fitted
history assumed has that game's **passing and receiving props quarantined**,
not repriced.

Depth charts are timestamped rather than week-assigned from 2025 onward, so
the current chart is readable at card time. A chart older than
`MAX_DEPTH_CHART_AGE_HOURS` cannot answer the question, and an unanswerable
question quarantines — the same direction every other gate falls in.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pandas as pd


# -- availability ------------------------------------------------------------

CONFIRMED = "confirmed"
UNDESIGNATED = "undesignated"
QUESTIONABLE = "questionable"
DOUBTFUL = "doubtful"
EXCLUDED = "excluded"
NO_REPORT = "no_report"

#: The only state that may produce a selection. Nothing reaches it today.
SELECTABLE_STATES = frozenset({CONFIRMED})

#: States in which the model still holds and freezes an opinion, so forward
#: evidence accumulates for a market that cannot yet be bet.
PRICEABLE_STATES = frozenset({CONFIRMED, UNDESIGNATED, QUESTIONABLE, DOUBTFUL, NO_REPORT})


@dataclass(frozen=True)
class Availability:
    """One player's availability state, and why."""

    player_id: str
    state: str
    reason: str

    @property
    def may_select(self) -> bool:
        return self.state in SELECTABLE_STATES

    @property
    def may_price(self) -> bool:
        return self.state in PRICEABLE_STATES

    @property
    def is_no_value_call(self) -> bool:
        """Always False. A gated market is not a model opinion."""
        return False


_STATUS_TO_STATE = {
    "out": EXCLUDED,
    "doubtful": DOUBTFUL,
    "questionable": QUESTIONABLE,
}


def report_coverage(injuries: pd.DataFrame, *, season: int, week: int) -> set[str]:
    """Which teams filed an injury report for this week.

    The set exists so `NO_REPORT` and `UNDESIGNATED` can be told apart. Without
    it a team that simply has not filed yet is indistinguishable from a team
    with nobody injured, and the second reading waves a whole game through.
    """
    if injuries.empty:
        return set()
    frame = injuries
    for column, value in (("season", season), ("week", week)):
        if column in frame.columns:
            frame = frame[pd.to_numeric(frame[column], errors="coerce") == value]
    if "team" not in frame.columns:
        return set()
    return {str(team).strip().upper() for team in frame["team"].dropna()}


def assess_availability(
    player_id: str,
    team: str,
    injuries: pd.DataFrame,
    *,
    season: int,
    week: int,
    teams_reporting: set[str] | None = None,
) -> Availability:
    """One player's state for one game week."""
    club = str(team).strip().upper()
    reporting = (
        report_coverage(injuries, season=season, week=week)
        if teams_reporting is None
        else teams_reporting
    )
    if club not in reporting:
        return Availability(
            player_id=str(player_id),
            state=NO_REPORT,
            reason=(
                f"No injury report exists for {club} in {season} week {week}. "
                "That is a missing feed, not a clean bill of health, and it is "
                "recorded as its own state so it can never be read as one."
            ),
        )

    rows = injuries
    for column, value in (
        ("season", season),
        ("week", week),
    ):
        if column in rows.columns:
            rows = rows[pd.to_numeric(rows[column], errors="coerce") == value]
    if "gsis_id" in rows.columns:
        rows = rows[rows["gsis_id"].astype(str).str.strip() == str(player_id).strip()]
    else:
        rows = rows.iloc[0:0]

    if rows.empty:
        return Availability(
            player_id=str(player_id),
            state=UNDESIGNATED,
            reason=(
                f"{club} filed an injury report for week {week} and this "
                "player is not on it. That is evidence of availability and not "
                "confirmation: healthy scratches and game-time decisions are "
                "not injuries, and no feed publishes inactives."
            ),
        )

    status = str(rows.iloc[-1].get("report_status", "") or "").strip().lower()
    state = _STATUS_TO_STATE.get(status)
    if state == EXCLUDED:
        return Availability(
            player_id=str(player_id),
            state=EXCLUDED,
            reason=(
                f"Listed Out on {club}'s week {week} injury report. "
                "Definitive: no opinion is offered."
            ),
        )
    if state is not None:
        return Availability(
            player_id=str(player_id),
            state=state,
            reason=(
                f"Listed {status.title()} on {club}'s week {week} injury "
                "report. Books reprice on Sunday-morning news; this lab "
                "cannot, so the market is priced and tracked and cannot "
                "produce a selection."
            ),
        )
    return Availability(
        player_id=str(player_id),
        state=UNDESIGNATED,
        reason=(
            f"On {club}'s week {week} injury report with no game-status "
            "designation. Practice participation is not availability."
        ),
    )


def selection_blocked_note() -> str:
    """The sentence the card prints wherever a player prop would have gone."""
    return (
        "Player props are priced and tracked and **cannot produce a "
        "selection**. Inactives are declared about ninety minutes before "
        "kickoff and no available feed publishes them, so no player can be "
        "confirmed active. This is a missing source, not a judgement about "
        "any market's value."
    )


# -- quarterback changes -----------------------------------------------------

#: A depth chart older than this cannot answer "who is QB1 today". nflverse
#: updates daily at 07:00 UTC, so two days is already two missed updates.
MAX_DEPTH_CHART_AGE_HOURS = 48.0

QB_UNCHANGED = "unchanged"
QB_CHANGED = "changed"
QB_UNKNOWN = "unknown"

#: Markets a quarterback change invalidates. Not the whole card: a change
#: says nothing about the opposing kicker or either defence's tackle counts.
QB_DEPENDENT_MARKETS = frozenset(
    {
        "pass_yards",
        "pass_attempts",
        "pass_completions",
        "pass_tds",
        "pass_interceptions",
        "pass_longest_completion",
        "receptions",
        "reception_yards",
        "reception_tds",
        "reception_longest",
        "anytime_td",
    }
)


@dataclass(frozen=True)
class QuarterbackCheck:
    """Whether a team's QB1 is the one the fit assumed."""

    team: str
    state: str
    expected: str
    current: str
    reason: str

    @property
    def quarantines_props(self) -> bool:
        return self.state != QB_UNCHANGED


def current_qb1(
    depth_charts: pd.DataFrame, team: str, *, now: datetime
) -> tuple[str, str]:
    """`(player name, why)` for a team's current QB1, or `("", why not)`."""
    if depth_charts.empty or "dt" not in depth_charts.columns:
        return "", "No depth chart data at all."
    frame = depth_charts[
        (depth_charts["team"].astype(str).str.upper() == str(team).strip().upper())
        & (depth_charts["pos_abb"].astype(str).str.upper() == "QB")
    ].copy()
    if frame.empty:
        return "", f"No quarterback rows for {team} in the depth chart."
    frame["_dt"] = pd.to_datetime(frame["dt"], errors="coerce", utc=True)
    frame = frame.dropna(subset=["_dt"])
    if frame.empty:
        return "", f"No parseable depth-chart timestamps for {team}."
    latest = frame["_dt"].max()
    age_hours = (now.astimezone(timezone.utc) - latest.to_pydatetime()).total_seconds() / 3600
    if age_hours > MAX_DEPTH_CHART_AGE_HOURS:
        return "", (
            f"The newest depth chart for {team} is {age_hours:.0f} hours old, "
            f"past the {MAX_DEPTH_CHART_AGE_HOURS:.0f}-hour limit. It cannot "
            "answer who starts today."
        )
    snapshot = frame[frame["_dt"] == latest]
    ranked = snapshot[pd.to_numeric(snapshot["pos_rank"], errors="coerce") == 1]
    if ranked.empty:
        return "", f"The newest depth chart for {team} names no QB1."
    return str(ranked.iloc[0]["player_name"]).strip(), ""


def check_quarterback(
    team: str,
    expected_qb: str,
    depth_charts: pd.DataFrame,
    *,
    now: datetime,
) -> QuarterbackCheck:
    """Whether this team's props may be priced from the fitted history.

    A change quarantines rather than reprices. The model has no fitted
    knowledge of the backup, so repricing would be an invention dressed as a
    number — worse than abstaining, because it looks like an opinion.
    """
    current, why = current_qb1(depth_charts, team, now=now)
    expected_name = str(expected_qb or "").strip()
    if not current:
        return QuarterbackCheck(
            team=str(team),
            state=QB_UNKNOWN,
            expected=expected_name,
            current="",
            reason=(
                f"{why} An unanswerable question quarantines, the same "
                "direction every other gate falls in."
            ),
        )
    if not expected_name:
        return QuarterbackCheck(
            team=str(team),
            state=QB_UNKNOWN,
            expected="",
            current=current,
            reason=(
                f"{team} has no quarterback on record from the fitted history "
                "to compare against, so a change cannot be ruled out."
            ),
        )
    if current.casefold() != expected_name.casefold():
        return QuarterbackCheck(
            team=str(team),
            state=QB_CHANGED,
            expected=expected_name,
            current=current,
            reason=(
                f"{team} lists {current} at QB1; the fitted history assumed "
                f"{expected_name}. Every passing and receiving rate this model "
                "learned belongs to the other quarterback, so this game's "
                "passing and receiving props are quarantined rather than "
                "repriced."
            ),
        )
    return QuarterbackCheck(
        team=str(team),
        state=QB_UNCHANGED,
        expected=expected_name,
        current=current,
        reason=f"{team} still lists {current} at QB1.",
    )
