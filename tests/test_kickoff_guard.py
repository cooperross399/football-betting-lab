"""A started game can never appear as a play, and ambiguity is not a play.

These tests are named after what they protect rather than what they call. A
failing name here should tell a reader what broke without opening the file.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from football_betting_lab.kickoff import (
    PLAYABLE,
    QUARANTINE_HEADING,
    STARTED,
    UNCONFIRMED,
    judge,
    parse_commence_time,
    partition,
)


NOW = datetime(2026, 9, 13, 17, 0, tzinfo=timezone.utc)


def test_a_game_still_ahead_of_us_plays() -> None:
    verdict = judge("2026-09-13T20:25:00Z", now=NOW)

    assert verdict.state == PLAYABLE
    assert verdict.plays


def test_a_game_that_has_kicked_off_does_not_play() -> None:
    verdict = judge("2026-09-13T13:00:00Z", now=NOW)

    assert verdict.state == STARTED
    assert not verdict.plays


def test_a_game_kicking_off_this_exact_second_does_not_play() -> None:
    """No grace period. A game that started sixty seconds ago is started, and
    so is one starting now."""
    verdict = judge(NOW.isoformat().replace("+00:00", "Z"), now=NOW)

    assert verdict.state == STARTED


def test_a_game_kicking_off_one_second_from_now_still_plays() -> None:
    """The boundary is `<=`, and it is asserted from both sides so a future
    change to `<` cannot pass unnoticed."""
    later = (NOW + timedelta(seconds=1)).isoformat().replace("+00:00", "Z")

    assert judge(later, now=NOW).plays


@pytest.mark.parametrize(
    "value",
    ["", "   ", None, "not a time", "2026-09-13", "13/09/2026 20:25"],
)
def test_a_start_time_that_cannot_be_confirmed_does_not_play(value: object) -> None:
    verdict = judge(value, now=NOW)

    assert verdict.state == UNCONFIRMED
    assert not verdict.plays


def test_a_naive_timestamp_is_unconfirmed_rather_than_assumed_utc() -> None:
    """A naive timestamp is not "probably UTC".

    Assuming a zone would move a Sunday-night kickoff across a date boundary,
    which is the same class of error that discarded 69% of the NHL lab's
    bought prices.
    """
    verdict = judge("2026-09-13T20:25:00", now=NOW)

    assert verdict.state == UNCONFIRMED


def test_an_offset_that_is_not_utc_is_compared_correctly() -> None:
    """20:25 Eastern on the 13th is 00:25 UTC on the 14th — still ahead."""
    assert judge("2026-09-13T20:25:00-04:00", now=NOW).plays
    # ...and 12:00 Eastern the same day is 16:00 UTC, already gone.
    assert not judge("2026-09-13T12:00:00-04:00", now=NOW).plays


def test_a_naive_now_is_refused_rather_than_coerced() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        judge("2026-09-13T20:25:00Z", now=datetime(2026, 9, 13, 17, 0))


def test_a_quarantined_selection_is_never_a_no_value_call() -> None:
    """The distinction the whole card rests on: an unavailable bet is not a
    model judgement about the bet's value."""
    for value in ("2026-09-13T13:00:00Z", "", "nonsense"):
        assert judge(value, now=NOW).is_no_value_call is False


def test_the_quarantine_heading_says_availability_not_value() -> None:
    lowered = QUARANTINE_HEADING.lower()

    assert "no longer plays" in lowered
    for word in ("pass", "avoid", "no value", "fade"):
        assert word not in lowered


def test_partition_removes_the_started_ones_and_keeps_their_reasons() -> None:
    selections = [
        {"id": "ahead", "commence_time": "2026-09-13T20:25:00Z"},
        {"id": "gone", "commence_time": "2026-09-13T13:00:00Z"},
        {"id": "unknown", "commence_time": ""},
    ]

    plays, quarantined = partition(selections, now=NOW)

    assert [item["id"] for item in plays] == ["ahead"]
    assert [item["id"] for item, _ in quarantined] == ["gone", "unknown"]
    # Every quarantined selection carries a stated reason. A quarantine with
    # no reason is indistinguishable from a pick silently dropped.
    assert all(verdict.reason for _, verdict in quarantined)


def test_parse_returns_utc_so_downstream_comparisons_cannot_drift() -> None:
    moment = parse_commence_time("2026-09-13T20:25:00-04:00")

    assert moment is not None
    assert moment.tzinfo is timezone.utc
    assert moment.hour == 0 and moment.day == 14
