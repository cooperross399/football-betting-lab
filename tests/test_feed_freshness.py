"""A stale feed does not fail — it answers, with last week's truth.

The card prices that answer and freezes it into the forward ledger, and the
ledger is never revised. So a stale feed does not cost a run; it writes a wrong
opinion into the one record this lab cannot correct.
"""

from __future__ import annotations

from datetime import date

import pytest

from football_betting_lab.reports.feed_freshness import (
    MISSING,
    NOT_YET,
    OK,
    STALE,
    FeedState,
    FreshnessResult,
    expected_week,
    render,
)


def _feed(**kw) -> FeedState:
    base = dict(
        name="rosters", consequence="a player priced against the club he left",
        present=True, covers_season=True, reaches_week=5, expected_week=5,
        clubs=32, expected_clubs=32, due=True,
    )
    return FeedState(**{**base, **kw})


def test_expected_week_is_a_week_not_a_count_of_game_days() -> None:
    """The first version returned the number of days played, so a full season
    asked every feed to reach "week 57" and all of them read as stale.
    Counting the wrong unit produces a plausible number, not an error."""
    day_to_week = {
        "2026-09-09": 1, "2026-09-13": 1, "2026-09-17": 2, "2026-09-20": 2,
    }

    assert expected_week(day_to_week, date(2026, 9, 18)) == 2
    assert expected_week(day_to_week, date(2026, 9, 10)) == 1


def test_a_season_that_has_not_started_owes_nothing() -> None:
    assert expected_week({"2026-09-09": 1}, date(2026, 8, 31)) is None


def test_a_feed_that_stops_short_of_the_played_week_is_stale() -> None:
    """The ordinary failure: a fetch that succeeded against an upstream which
    had not published yet. The file's timestamp says fresh."""
    assert _feed(reaches_week=3, expected_week=5).state == STALE


def test_a_feed_missing_clubs_is_stale_even_when_it_reaches_the_week() -> None:
    """Thirty-one clubs is a feed missing a team, not a thin one, and the
    missing team's players would price against nothing."""
    assert _feed(clubs=31).state == STALE


def test_a_current_feed_is_current() -> None:
    assert _feed().state == OK
    assert not _feed().blocks_an_opinion


def test_an_absent_feed_is_missing_rather_than_silently_passing() -> None:
    assert _feed(present=False).state == MISSING
    assert _feed(present=False).blocks_an_opinion


def test_a_feed_whose_season_has_not_started_is_not_stale() -> None:
    """Before Week 1 a weekly feed has nothing to publish. Reading that as
    staleness would block every preseason run — an absence before kickoff and
    an absence after it are different facts."""
    feed = _feed(present=False, due=False)

    assert feed.state == NOT_YET
    assert not feed.blocks_an_opinion


def test_a_feed_with_no_week_column_is_judged_on_clubs_alone() -> None:
    """Depth charts carry no week. Requiring one would mark them stale forever;
    the live path guards their age separately in `gates.py`."""
    assert _feed(name="depth_charts", reaches_week=None).state == OK


def test_the_report_names_what_each_stale_feed_would_cost() -> None:
    """"Refresh the feeds" is not an instruction anyone can act on at 07:00 on
    a game day."""
    result = FreshnessResult(as_of="2026-09-14", week=1, feeds=[
        _feed(name="depth_charts", present=False,
              consequence="QB1 unknown, so the passing tree cannot be quarantined"),
    ])

    text = render(result)

    assert "Not ready" in text
    assert "QB1 unknown" in text
    assert "names its own consequence" in text


def test_checking_nothing_is_an_absence_not_a_pass() -> None:
    """The same failure the settlement screen once had: an empty table above a
    sentence that reads as a clean bill of health."""
    text = render(FreshnessResult(as_of="2026-09-14", week=1, feeds=[]))

    assert "absence, not a pass" in text
    assert "Ready." not in text
