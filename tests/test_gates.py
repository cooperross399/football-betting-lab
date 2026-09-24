"""A gate that cannot answer must quarantine, and absence is not health.

The states here are kept apart because collapsing them is how a card starts
lying. In particular: "no injury report exists" and "the player is not on the
injury report" look identical in a total and mean opposite things.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from football_betting_lab import gates as _gates
from football_betting_lab.gates import (
    Availability,
    DOUBTFUL,
    EXCLUDED,
    MAX_DEPTH_CHART_AGE_HOURS,
    NO_REPORT,
    QB_CHANGED,
    QB_DEPENDENT_MARKETS,
    QB_UNCHANGED,
    QB_UNKNOWN,
    QUESTIONABLE,
    REQUIRED_INJURY_COLUMNS,
    SELECTABLE_STATES,
    SELECTABLE_WITH_VERDICT,
    UNDESIGNATED,
    UNKNOWN,
    assess_availability,
    assess_slate,
    check_quarterback,
    missing_injury_columns,
    report_coverage,
    selection_blocked_note,
)


NOW = datetime(2026, 9, 13, 15, 0, tzinfo=timezone.utc)

#: Every state a `report_status` can map to, read off the gate's own table.
_STATUS_TO_STATE_VALUES = tuple(_gates._STATUS_TO_STATE.values())


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


# -- the two fail-opens, closed ----------------------------------------------
#
# Both of these answered `UNDESIGNATED` — the ONE non-confirmed state a
# recorded verdict can make selectable — with a reason string that
# affirmatively asserted availability. They were harmless only while the gate
# had no caller.


def test_the_required_columns_are_named_here_and_not_only_derived() -> None:
    """The parametrized test below iterates `REQUIRED_INJURY_COLUMNS`, so it
    would go on passing with fewer cases if a column were quietly dropped from
    the constant — a roster only guards what it names. This names them.

    Each is read unconditionally somewhere in `assess_availability`, and each
    was conditional before: `season` and `week` were filtered "if present",
    so a frame without them answered every week from whatever rows it held;
    `gsis_id` emptied the rows and answered UNDESIGNATED; `team` and
    `report_status` are what the coverage set and the designation are read
    from.
    """
    assert set(REQUIRED_INJURY_COLUMNS) == {
        "season", "week", "team", "gsis_id", "report_status"
    }


@pytest.mark.parametrize("column", REQUIRED_INJURY_COLUMNS)
def test_a_frame_missing_a_column_this_gate_reads_cannot_answer(column: str) -> None:
    """Every required column, dropped one at a time.

    The failure each one used to produce differs, and neither is acceptable:
    dropping `gsis_id` emptied the row filter and took the "absent from a
    filed report" branch, while dropping `team` produced an empty coverage
    set and answered `NO_REPORT` — a state whose reason sentence says an
    injury report does not exist, about a feed that may well hold one.
    """
    injuries = _injuries([_report(report_status="Out")]).drop(columns=[column])

    verdict = assess_availability("00-0000001", "BUF", injuries, season=2026, week=1)

    assert verdict.state == UNKNOWN
    assert verdict.state != UNDESIGNATED
    assert not verdict.may_select
    assert column in verdict.reason


def test_the_schema_check_runs_BEFORE_the_team_lookup() -> None:
    """The correction that makes the guard reachable at all.

    Hoisting a column check to just above the row filtering looks like a fix
    and is dead code: `assess_availability` returns `NO_REPORT` on the team
    lookup above it, so an unreadable frame never arrives. Dropping `team`
    is the case that proves the ordering — with the check in the wrong place
    the answer is `NO_REPORT`, not `UNKNOWN`.
    """
    injuries = _injuries([_report()]).drop(columns=["team"])

    assert assess_availability(
        "00-0000001", "BUF", injuries, season=2026, week=1
    ).state == UNKNOWN


def test_an_unrecognised_report_status_is_not_the_absence_of_one() -> None:
    """`injuries_2024.csv` carries six rows whose status is `Note`.

    A designation this gate does not understand used to fall out of the
    bottom of the function into `UNDESIGNATED` — answered as *not
    designated*, which is the opposite of what an unread designation means.
    """
    injuries = _injuries([_report(report_status="Note")])

    verdict = assess_availability("00-0000001", "BUF", injuries, season=2026, week=1)

    assert verdict.state == UNKNOWN
    assert not verdict.may_select
    assert "note" in verdict.reason.lower()


@pytest.mark.parametrize("blank", ["", "   ", None, float("nan"), "nan"])
def test_a_blank_report_status_is_still_undesignated(blank: object) -> None:
    """The guard against over-correcting the line above.

    3,386 of 6,215 rows in 2024 carry no game-status designation, and a blank
    cell arrives from pandas as float NaN. Reading those as unrecognised
    would put the most common row in the feed into `UNKNOWN` and quarantine
    a whole slate over a correctly-read blank.
    """
    injuries = _injuries([_report(report_status=blank)])

    assert assess_availability(
        "00-0000001", "BUF", injuries, season=2026, week=1
    ).state == UNDESIGNATED


def test_an_empty_frame_is_still_no_report_rather_than_unknown() -> None:
    """No file yet is the documented preseason state and has a true sentence
    to offer. A non-empty frame that cannot be parsed does not, which is the
    whole distinction between the two."""
    for empty in (_injuries([]), pd.DataFrame()):
        verdict = assess_availability("00-0000001", "BUF", empty, season=2026, week=1)
        assert verdict.state == NO_REPORT, empty.columns


def test_report_coverage_fails_closed_on_a_frame_it_cannot_read() -> None:
    """The empty set means NO_REPORT, which blocks. Returning the teams it
    could still see would clear players on a frame this gate cannot scope to
    a week."""
    filed = _injuries([_report(team="BUF")])

    assert report_coverage(filed, season=2026, week=1) == {"BUF"}
    for column in REQUIRED_INJURY_COLUMNS:
        assert report_coverage(
            filed.drop(columns=[column]), season=2026, week=1
        ) == set(), column


def test_the_two_functions_agree_on_what_a_readable_frame_is() -> None:
    """One list, read by both. Two hand-kept lists is how a frame becomes
    readable to one of them and not the other."""
    filed = _injuries([_report()])

    assert missing_injury_columns(filed) == ()
    assert missing_injury_columns(filed.drop(columns=["week"])) == ("week",)
    assert set(REQUIRED_INJURY_COLUMNS) <= set(filed.columns)


def test_an_unreadable_feed_can_never_select_even_under_the_verdict() -> None:
    """`UNKNOWN` is outside both selectable sets, so a shipped verdict cannot
    reach it. This is the property the two fail-opens defeated by answering
    `UNDESIGNATED` instead."""
    assert UNKNOWN not in SELECTABLE_STATES
    assert UNKNOWN not in SELECTABLE_WITH_VERDICT
    assert not Availability(
        player_id="p", state=UNKNOWN, reason="", undesignated_allowed=True
    ).may_select


def test_an_unreadable_feed_still_prices_so_the_ledger_keeps_accruing() -> None:
    """Same as `NO_REPORT`. Forward evidence cannot be back-dated, so
    refusing to freeze an opinion over a column name would lose a day of the
    only evidence this lab can still gather. Pricing is not betting."""
    assert Availability(player_id="p", state=UNKNOWN, reason="").may_price


def test_two_rows_that_disagree_are_reduced_to_the_most_restrictive() -> None:
    """File order is not authority, and it used to be.

    `rows.iloc[-1]` took whichever row happened to sit last. Measured on the
    real feed: 2 player-weeks in `injuries_2024.csv` carry two rows that
    disagree, both `Out` beside `Questionable`, and positional last picks
    **Questionable** in both. Neither is selectable so those two cost
    nothing — but `Out` beside a blank is the same shape and answers
    `UNDESIGNATED`, which a recorded verdict can open.
    """
    out_last = _injuries(
        [_report(report_status="Questionable"), _report(report_status="Out")]
    )
    out_first = _injuries(
        [_report(report_status="Out"), _report(report_status="Questionable")]
    )

    for injuries in (out_last, out_first):
        assert assess_availability(
            "00-0000001", "BUF", injuries, season=2026, week=1
        ).state == EXCLUDED


def test_a_blank_row_cannot_wash_out_a_designation() -> None:
    """The case that would actually have cost something: `Out` beside a row
    with no game-status designation. Positional last answers `UNDESIGNATED` —
    the one state a shipped verdict makes selectable — about a player listed
    Out in the same week's report."""
    injuries = _injuries(
        [_report(report_status="Out"), _report(report_status="")]
    )

    verdict = assess_availability("00-0000001", "BUF", injuries, season=2026, week=1)

    assert verdict.state == EXCLUDED
    assert not Availability(
        player_id="p", state=verdict.state, reason="", undesignated_allowed=True
    ).may_select


def test_an_unreadable_row_is_not_masked_by_a_readable_one() -> None:
    """One row of this player's week could not be read, so the week could not
    be read. A `Questionable` beside it does not make that go away."""
    injuries = _injuries(
        [_report(report_status="Questionable"), _report(report_status="Note")]
    )

    assert assess_availability(
        "00-0000001", "BUF", injuries, season=2026, week=1
    ).state == UNKNOWN


def test_a_definitive_out_outranks_an_unreadable_row() -> None:
    """`Out` is the only state that stops pricing as well as selection, so it
    is the most restrictive answer available and it is a fact the feed
    actually stated."""
    injuries = _injuries(
        [_report(report_status="Note"), _report(report_status="Out")]
    )

    assert assess_availability(
        "00-0000001", "BUF", injuries, season=2026, week=1
    ).state == EXCLUDED


def test_the_restrictiveness_order_covers_every_state_it_reduces() -> None:
    """A state missing from the order raises `ValueError` inside `min` on a
    live card rather than answering. Pinning it here makes a new state a
    failing test instead."""
    from football_betting_lab.gates import _RESTRICTIVENESS

    assert set(_RESTRICTIVENESS) == {
        EXCLUDED, UNKNOWN, DOUBTFUL, QUESTIONABLE, UNDESIGNATED
    }
    assert set(_STATUS_TO_STATE_VALUES) <= set(_RESTRICTIVENESS)
    # Most restrictive first, and the two that matter most at the front.
    assert _RESTRICTIVENESS[0] == EXCLUDED
    assert _RESTRICTIVENESS.index(UNKNOWN) < _RESTRICTIVENESS.index(UNDESIGNATED)


# -- the gate has a caller now ------------------------------------------------


def _slate() -> dict[str, tuple[str, str]]:
    return {
        "a back": ("00-0000001", "BUF"),
        "a receiver": ("00-0000002", "BUF"),
        "a kicker": ("00-0000003", "KC"),
    }


def test_assess_slate_gives_each_player_his_own_state() -> None:
    """The defect this closes: one boolean stood in for six states, so a
    player listed Out and a player on a team that never filed both became
    selectable on the single flag `select()` read."""
    injuries = _injuries(
        [_report(gsis_id="00-0000001", report_status="Out"), _report(gsis_id="00-0000009")]
    )

    verdicts = assess_slate(
        _slate(), injuries, season=2026, week=1, undesignated_allowed=True
    )

    assert verdicts["a back"].state == EXCLUDED
    assert verdicts["a receiver"].state == UNDESIGNATED
    assert verdicts["a kicker"].state == NO_REPORT
    # The verdict opens ONE of those three.
    assert [key for key, v in verdicts.items() if v.may_select] == ["a receiver"]


def test_assess_slate_without_the_verdict_selects_nothing_at_all() -> None:
    injuries = _injuries([_report(gsis_id="00-0000009")])

    verdicts = assess_slate(_slate(), injuries, season=2026, week=1)

    assert verdicts["a receiver"].state == UNDESIGNATED
    assert not any(verdict.may_select for verdict in verdicts.values())


def test_a_slate_whose_week_cannot_be_read_is_unanswerable_not_healthy() -> None:
    """`week=None` means the schedule could not say which week this slate is,
    so there is no report to look anybody up in. Reading that as "no
    injuries" is the `NO_REPORT`/`UNDESIGNATED` collapse in a third place."""
    injuries = _injuries([_report(gsis_id="00-0000009")])

    verdicts = assess_slate(
        _slate(), injuries, season=2026, week=None, undesignated_allowed=True
    )

    assert {verdict.state for verdict in verdicts.values()} == {UNKNOWN}
    assert not any(verdict.may_select for verdict in verdicts.values())


def test_assess_slate_keeps_the_card_key_it_was_given() -> None:
    """The map is looked up by `player_key` in `select()`. A function that
    re-keyed on the id would return verdicts the card can never find, which
    fails closed — and silently."""
    injuries = _injuries([_report(gsis_id="00-0000009")])

    verdicts = assess_slate(_slate(), injuries, season=2026, week=1)

    assert set(verdicts) == set(_slate())


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


# -- what measurement changed about this gate --------------------------------


def test_an_undesignated_player_may_select_only_when_a_verdict_says_so() -> None:
    """The original reasoning — a market you cannot confirm is a market you
    cannot bet — does not survive measurement: a did-not-play prop is voided
    by the book, not lost. But that is a fact about a book's rules, so it
    goes through the verdicts door rather than being switched on."""
    injuries = _injuries([_report()])

    without = assess_availability("00-0000999", "BUF", injuries, season=2026, week=1)
    with_verdict = Availability(
        player_id=without.player_id,
        state=without.state,
        reason=without.reason,
        undesignated_allowed=True,
    )

    assert without.state == UNDESIGNATED
    assert not without.may_select
    assert with_verdict.may_select


def test_the_verdict_never_unblocks_a_player_listed_out() -> None:
    """Measured: every player listed Out or Doubtful voided 100% of the time.
    There is nothing to unblock and pricing them would be noise."""
    for state in (EXCLUDED, DOUBTFUL, QUESTIONABLE, NO_REPORT):
        verdicted = Availability(
            player_id="p", state=state, reason="", undesignated_allowed=True
        )
        assert not verdicted.may_select, state


def test_the_void_assumption_cites_the_rules_that_were_read() -> None:
    """Four files now assert "the book voids" as fact rather than assumption.

    That assertion is only as good as `docs/did_not_play_rules.md`, which holds
    the rule text and the date it was read. If the document goes and the
    sentences stay, the lab is back to asserting a settlement rule it has not
    checked — which is the state this whole change was made to leave.

    It also pins the exception. Bovada is the one book in the feed that
    **grades** a player who is active and never plays, and it is the book the
    card is most likely to run against, so a summary that drops it is worse
    than no summary.
    """
    from football_betting_lab.config import PROJECT_ROOT

    doc = PROJECT_ROOT / "docs" / "did_not_play_rules.md"
    assert doc.is_file(), "the rules document the code cites does not exist"
    text = doc.read_text(encoding="utf-8")
    for book in ("DraftKings", "FanDuel", "BetMGM", "Caesars", "Fanatics", "Bovada"):
        assert book in text, f"{book} is not in the rules document"
    assert "Bovada is the exception" in text
    # Unverified must stay named as unverified rather than quietly dropped.
    assert "bet365" in text and "BetRivers" in text

    citing = [
        PROJECT_ROOT / "src" / "football_betting_lab" / "verdicts.py",
        PROJECT_ROOT / "src" / "football_betting_lab" / "gates.py",
        PROJECT_ROOT / "src" / "football_betting_lab" / "reports" / "availability_cost.py",
    ]
    for path in citing:
        assert "did_not_play_rules.md" in path.read_text(encoding="utf-8"), (
            f"{path.name} states the void rule and cites no source for it"
        )


def test_the_verdict_for_this_gate_is_not_in_force() -> None:
    """It does not ship, and the reason has changed.

    This used to say the verdict waited on one line in a book's prop rules,
    "which turns +13.0% into -0.8%". Both halves are superseded:

    * The +13.0%/-0.8% pair is retracted — computed on cross-season-settled
      bets, see `reports/availability_cost.py`. The pair is -3.7%/-5.8%.
    * The rules were read on 2026-09-23 from state-regulator filings:
      `docs/did_not_play_rules.md`. Books void, symmetrically; Bovada grades.

    So the stated blocker is gone and the verdict still must not be in force,
    because the population it opens measures -3.7% and
    `scripts/run_gameday_card.py` wires it straight into live selection."""
    from football_betting_lab.leagues import NFL
    from football_betting_lab.verdicts import ships

    assert not ships("props_selectable_when_undesignated", NFL)
