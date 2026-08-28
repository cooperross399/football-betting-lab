"""A gate that cannot answer must quarantine, and absence is not health.

The states here are kept apart because collapsing them is how a card starts
lying. In particular: "no injury report exists" and "the player is not on the
injury report" look identical in a total and mean opposite things.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from football_betting_lab.gates import (
    DOUBTFUL,
    EXCLUDED,
    MAX_DEPTH_CHART_AGE_HOURS,
    NO_REPORT,
    QB_CHANGED,
    QB_DEPENDENT_MARKETS,
    QB_UNCHANGED,
    QB_UNKNOWN,
    QUESTIONABLE,
    SELECTABLE_STATES,
    UNDESIGNATED,
    assess_availability,
    check_quarterback,
    report_coverage,
    selection_blocked_note,
)


NOW = datetime(2026, 9, 13, 15, 0, tzinfo=timezone.utc)


def _injuries(rows: list[dict]) -> pd.DataFrame:
    columns = ["season", "week", "team", "gsis_id", "full_name", "report_status"]
    return pd.DataFrame(rows, columns=columns)


def _report(**overrides) -> dict:
    row = {
        "season": 2026,
        "week": 1,
        "team": "BUF",
        "gsis_id": "00-0000001",
        "full_name": "A Player",
        "report_status": "Questionable",
    }
    row.update(overrides)
    return row


# -- availability ------------------------------------------------------------


def test_nothing_can_reach_the_confirmed_state_today() -> None:
    """The whole point of this gate. Inactives land ninety minutes before
    kickoff and no available feed publishes them, so no player prop may
    produce a selection."""
    injuries = _injuries([_report(), _report(gsis_id="00-0000002", report_status="")])

    states = {
        assess_availability(pid, "BUF", injuries, season=2026, week=1).state
        for pid in ("00-0000001", "00-0000002", "00-0000999")
    }

    assert not (states & SELECTABLE_STATES)


def test_a_player_listed_out_is_excluded_and_not_priced() -> None:
    injuries = _injuries([_report(report_status="Out")])

    verdict = assess_availability("00-0000001", "BUF", injuries, season=2026, week=1)

    assert verdict.state == EXCLUDED
    assert not verdict.may_price
    assert not verdict.may_select


@pytest.mark.parametrize(
    ("status", "expected"),
    [("Questionable", QUESTIONABLE), ("Doubtful", DOUBTFUL)],
)
def test_a_designated_player_is_priced_and_tracked_but_never_selected(
    status: str, expected: str
) -> None:
    injuries = _injuries([_report(report_status=status)])

    verdict = assess_availability("00-0000001", "BUF", injuries, season=2026, week=1)

    assert verdict.state == expected
    assert verdict.may_price
    assert not verdict.may_select


def test_a_player_absent_from_a_filed_report_is_undesignated_not_confirmed() -> None:
    """Evidence of availability is not confirmation. Healthy scratches and
    game-time decisions are not injuries."""
    injuries = _injuries([_report()])

    verdict = assess_availability("00-0000999", "BUF", injuries, season=2026, week=1)

    assert verdict.state == UNDESIGNATED
    assert not verdict.may_select


def test_a_missing_report_is_its_own_state_and_never_reads_as_healthy() -> None:
    """The failure that would wave a whole slate through.

    Before Week 1 there is no 2026 injury file at all. A gate that read that
    as "nobody is injured" would clear every player on every team.
    """
    empty = _injuries([])

    verdict = assess_availability("00-0000001", "BUF", empty, season=2026, week=1)

    assert verdict.state == NO_REPORT
    assert verdict.state != UNDESIGNATED
    assert not verdict.may_select
    assert "not a clean bill of health" in verdict.reason


def test_a_team_that_has_not_filed_is_told_apart_from_one_with_nobody_injured() -> None:
    injuries = _injuries([_report(team="BUF")])

    filed = assess_availability("00-0000999", "BUF", injuries, season=2026, week=1)
    not_filed = assess_availability("00-0000999", "KC", injuries, season=2026, week=1)

    assert filed.state == UNDESIGNATED
    assert not_filed.state == NO_REPORT


def test_a_report_from_another_week_does_not_answer_this_week() -> None:
    """A stale designation is not this week's designation."""
    injuries = _injuries([_report(week=1, report_status="Out")])

    verdict = assess_availability("00-0000001", "BUF", injuries, season=2026, week=2)

    assert verdict.state == NO_REPORT


def test_report_coverage_counts_teams_not_rows() -> None:
    injuries = _injuries(
        [_report(team="BUF"), _report(team="BUF", gsis_id="x"), _report(team="KC")]
    )

    assert report_coverage(injuries, season=2026, week=1) == {"BUF", "KC"}


def test_a_gated_player_prop_is_never_a_no_value_call() -> None:
    injuries = _injuries([_report(report_status="Out")])

    verdict = assess_availability("00-0000001", "BUF", injuries, season=2026, week=1)

    assert verdict.is_no_value_call is False


def test_the_card_says_why_rather_than_going_quiet() -> None:
    note = selection_blocked_note().lower()

    assert "cannot produce a selection" in note
    assert "missing source" in note
    for word in ("pass", "avoid", "no value"):
        assert f" {word} " not in note


# -- quarterback changes -----------------------------------------------------


def _depth(team: str, qb1: str, *, age_hours: float = 1.0) -> pd.DataFrame:
    stamp = (NOW - timedelta(hours=age_hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return pd.DataFrame(
        [
            {"dt": stamp, "team": team, "player_name": qb1, "pos_abb": "QB", "pos_rank": 1},
            {"dt": stamp, "team": team, "player_name": "Backup", "pos_abb": "QB", "pos_rank": 2},
        ]
    )


def test_the_same_starter_does_not_quarantine() -> None:
    check = check_quarterback("BUF", "Josh Allen", _depth("BUF", "Josh Allen"), now=NOW)

    assert check.state == QB_UNCHANGED
    assert not check.quarantines_props


def test_a_different_starter_quarantines_rather_than_repricing() -> None:
    """The model has no fitted knowledge of the backup. Repricing on him
    would be an invention dressed as a number."""
    check = check_quarterback("BUF", "Josh Allen", _depth("BUF", "Backup"), now=NOW)

    assert check.state == QB_CHANGED
    assert check.quarantines_props
    assert "quarantined rather than repriced" in check.reason


def test_a_stale_depth_chart_cannot_answer_and_therefore_quarantines() -> None:
    stale = _depth("BUF", "Josh Allen", age_hours=MAX_DEPTH_CHART_AGE_HOURS + 1)

    check = check_quarterback("BUF", "Josh Allen", stale, now=NOW)

    assert check.state == QB_UNKNOWN
    assert check.quarantines_props


def test_a_fresh_depth_chart_just_inside_the_limit_still_answers() -> None:
    """The boundary asserted from both sides, so a future change cannot slip
    past unnoticed."""
    fresh = _depth("BUF", "Josh Allen", age_hours=MAX_DEPTH_CHART_AGE_HOURS - 1)

    assert check_quarterback("BUF", "Josh Allen", fresh, now=NOW).state == QB_UNCHANGED


def test_no_depth_chart_at_all_quarantines() -> None:
    check = check_quarterback("BUF", "Josh Allen", pd.DataFrame(), now=NOW)

    assert check.state == QB_UNKNOWN


def test_a_team_with_no_quarterback_on_record_cannot_be_cleared() -> None:
    check = check_quarterback("BUF", "", _depth("BUF", "Josh Allen"), now=NOW)

    assert check.state == QB_UNKNOWN


def test_the_quarantine_covers_the_passing_and_receiving_tree_and_not_the_kicker() -> None:
    """A quarterback change says nothing about the opposing kicker or either
    defence's tackle counts, and quarantining those would be a different lie."""
    assert "pass_yards" in QB_DEPENDENT_MARKETS
    assert "reception_yards" in QB_DEPENDENT_MARKETS
    assert "anytime_td" in QB_DEPENDENT_MARKETS
    for market in ("kicking_points", "field_goals", "tackles_assists", "sacks"):
        assert market not in QB_DEPENDENT_MARKETS
