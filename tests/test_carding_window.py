"""The carding window, pinned to the crons that actually run.

`CLAUDE.md` carried this table written by hand and three of its numbers were
wrong: it assumed ET is UTC−4 across a season running into January, it read the
last run before kickoff rather than the first run of the day the standdown
guard leaves standing, and it counted six uncardable games where there are four.

None of those were caught by a test, because there was no script and therefore
nothing to test. These assertions exist so that a cron edit, a DST assumption or
a schedule refetch that moves the answer fails the build instead of quietly
disagreeing with a document.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from football_betting_lab.config import PROJECT_ROOT, RAW_DIR
from football_betting_lab.leagues import NFL
from football_betting_lab.reports import carding_window as cw


CARD_WORKFLOW = PROJECT_ROOT / ".github" / "workflows" / "football-gameday-refresh.yml"
SEASON = 2026


@pytest.fixture(scope="module")
def crons() -> list[cw.Cron]:
    return cw.parse_workflow_crons(CARD_WORKFLOW.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def rows(crons: list[cw.Cron]) -> list[cw.CardingRow]:
    return cw.carding_rows(NFL, RAW_DIR, season=SEASON, crons=crons)


# -- the parser refuses to guess ----------------------------------------------

def test_a_restricted_day_field_raises_rather_than_being_approximated() -> None:
    """A day-of-week cron changes which days fire. Guessing yields a plausible
    table rather than an error, which is the failure this module prevents."""
    with pytest.raises(ValueError, match="day-of-month or day-of-week"):
        cw.parse_cron("0 14 * 9-12 0")


def test_a_wrapping_month_range_raises() -> None:
    """Cron has no wrapping range. `9-1` means nothing, and the workflow writes
    `9-12,1` precisely because of that."""
    with pytest.raises(ValueError, match="wraps"):
        cw.parse_cron("0 14 * 9-1 *")


def test_a_cron_with_the_wrong_field_count_raises() -> None:
    with pytest.raises(ValueError, match="not 5"):
        cw.parse_cron("0 14 * *")


def test_the_parser_reads_only_the_schedule_block() -> None:
    """A `cron` in a comment is not a trigger."""
    parsed = cw.parse_workflow_crons(
        "on:\n"
        "  schedule:\n"
        "    # - cron: \"0 3 * * *\"  <- this one is commented out\n"
        "    - cron: \"0 14 * 9-12,1 *\"\n"
        "  workflow_dispatch:\n"
    )
    assert [c.expression for c in parsed] == ["0 14 * 9-12,1 *"]


# -- the crons the card actually has ------------------------------------------

def test_the_workflow_has_a_schedule_this_module_can_read(crons) -> None:
    assert crons, (
        "No cron was parsed from the card workflow. Either the card no longer "
        "runs on a schedule — nothing is carded without a human — or this "
        "parser has drifted from the file."
    )


def test_every_cron_covers_the_whole_season(crons) -> None:
    """The crons name months, so a season reaching past them goes dark — and a
    dark day looks exactly like a bye week from the outside."""
    for cron in crons:
        assert {9, 10, 11, 12, 1} <= cron.months, (
            f"Cron {cron.expression!r} does not cover every month of an NFL "
            f"regular season (Sep–Jan); it covers {sorted(cron.months)}."
        )


def test_no_game_day_of_the_season_is_without_a_run(rows, crons) -> None:
    assert cw.days_without_any_run(rows, crons, NFL) == []


# -- DST, which the hand-written table got wrong ------------------------------

def test_the_season_spans_both_utc_offsets(rows) -> None:
    """The whole reason the hand-written table was wrong. If this ever fails,
    the schedule changed and every lead in the report has to be recomputed."""
    assert {r.offset_label for r in rows} == {"EDT", "EST"}


def test_the_same_kickoff_slot_has_two_different_leads_across_the_boundary(rows) -> None:
    """13:00 ET is 17:00 UTC in EDT and 18:00 UTC in EST, so the lead from a
    fixed UTC cron differs by an hour. Collapsing them into one row is exactly
    the error that produced '149 games, 3.0h'."""
    leads = {
        r.offset_label: r.operative_lead_hours
        for r in rows
        if r.kickoff_et == "13:00"
    }
    # The exact hours depend on which trigger fires first and are therefore not
    # pinned — the schedule is allowed to change. What is NOT allowed is the two
    # offsets collapsing to one number, which is how "149 games, 3.0h" was
    # written for a season that is 95 games in EST.
    assert leads["EST"] - leads["EDT"] == pytest.approx(1.0), (
        f"13:00 ET games show leads {leads}. A fixed UTC trigger must be "
        "exactly one hour further from an EST kickoff than an EDT one; equal "
        "leads mean the DST offset is being ignored."
    )


def test_a_run_belongs_to_its_league_date_not_its_utc_date() -> None:
    """The workflow stamps the slate with `TZ=America/New_York date +%F` in the
    guard, the card and the publish. A cron across UTC midnight would otherwise
    be assigned to the wrong slate."""
    late = cw.parse_cron("0 2 * 9-12,1 *")  # 02:00 UTC = 21:00/22:00 the previous ET day
    firings = cw.firings_on(date(2026, 9, 13), [late], NFL)
    assert firings == [datetime(2026, 9, 14, 2, 0, tzinfo=timezone.utc)]


# -- the standdown, which the hand-written table ignored ----------------------

def test_the_operative_run_is_the_first_firing_not_the_last_before_kickoff(rows) -> None:
    """The backup triggers stand down when the first run publishes cleanly, and
    the first run prices the whole league day at `--horizon-days 1`. So the
    night window is carded by the morning run."""
    night = [r for r in rows if r.kickoff_et in {"20:15", "20:20"} and r.carded]
    assert night, "the 2026 schedule has night games; this test needs one"
    for row in night:
        assert row.operative_lead_hours > 14.0, (
            f"{row.game_id} is carded {row.operative_lead_hours:.2f}h out. A "
            "night game carded a few hours out would mean a later trigger ran "
            "despite an earlier one having published cleanly."
        )
        assert row.naive_last_lead_hours < row.operative_lead_hours


def test_ignoring_the_standdown_understates_the_lead_it_never_overstates(rows) -> None:
    """The direction of the hand-written table's error, pinned as a property.

    The count itself is deliberately NOT pinned: it is a function of how many
    backup triggers exist, so adding one changes it without anything being
    wrong. What cannot change is the direction — the operative run is the
    first firing of the day, every other firing is later, so a reading that
    takes the last run before kickoff can only ever report a lead that is too
    short. A table built that way understates how early the card commits.
    """
    compared = [
        r for r in rows if r.carded and r.naive_last_lead_hours is not None
    ]
    assert compared, "the 2026 schedule has carded games; this test needs them"
    for row in compared:
        assert row.naive_last_lead_hours <= row.operative_lead_hours, (
            f"{row.game_id}: a last-run-before-kickoff reading gives "
            f"{row.naive_last_lead_hours:.2f}h against an operative "
            f"{row.operative_lead_hours:.2f}h. The operative run is the "
            "FIRST firing of the league date; nothing may be earlier than it."
        )
    disagree = [
        r for r in compared
        if r.naive_last_lead_hours != r.operative_lead_hours
    ]
    assert len(disagree) > len(compared) // 2, (
        "The standdown barely changes the answer, which would mean the backup "
        "triggers fire close enough to the first that they are not backups."
    )


# -- the numbers CLAUDE.md quotes ---------------------------------------------

def test_every_game_of_the_season_has_a_run_before_kickoff(rows) -> None:
    """Once the schedule became a net starting at 09:00 UTC, the six 09:30 ET
    internationals stopped being structurally uncardable — 13:30 UTC is after
    09:00 UTC. CLAUDE.md said six games a season could never be carded, then
    four; on this schedule it is none."""
    missed = [r.game_id for r in rows if not r.carded]
    assert missed == [], (
        f"{len(missed)} games have no trigger before kickoff: {missed}. On the "
        "13-trigger net every game should reach one."
    )


def test_no_game_is_carded_inside_the_inactives_window(rows) -> None:
    """`2026_09_CIN_ATL` and `2026_10_NE_DET` were carded 30 minutes out on the
    old three-trigger schedule, inside the 90-minute inactives window, which
    made them a different population from the other 270. The net's 09:00 UTC
    trigger reaches them 5.5 hours out, so the season is uniform again."""
    inside = [r.game_id for r in rows if r.inside_inactives]
    assert inside == [], (
        f"These are carded inside the inactives window: {inside}. Their rows "
        "are not comparable with the rest of the ledger."
    )


def test_the_net_survives_every_delay_yet_observed(rows, crons) -> None:
    """The property the schedule exists for.

    GitHub has fired none of this repository's crons on time — 11 firings,
    115 to 443 minutes late. A late trigger is not a later card: past kickoff
    the guard quarantines the game and the evidence is gone. On the old
    14:00/15:30/21:00 schedule a 304-minute delay lost 155 of 272 games,
    including the entire 149-game 13:00 ET slate.
    """
    for delay in cw.OBSERVED_DELAYS_MINUTES:
        carded, lost = cw.coverage_under_delay(rows, crons, NFL, delay)
        # Only the 09:30 ET internationals may fall off, and only at the
        # extreme tail. Anything else means the net starts too late.
        assert all(slot == "09:30" for slot in lost), (
            f"At the observed {delay}-minute delay the schedule loses "
            f"{lost}, which is more than the international slot. The first "
            "trigger is too late to absorb the delays GitHub actually applies."
        )
        assert carded >= len(rows) - 6, (
            f"At the observed {delay}-minute delay only {carded} of "
            f"{len(rows)} games are carded."
        )


def test_a_delay_past_the_first_kickoff_is_reported_as_loss_not_lateness(
    rows, crons
) -> None:
    """A sanity check on the model itself: push the delay absurdly far and the
    coverage must collapse. A function that always answers 'fine' would pass
    every test above without measuring anything."""
    carded, lost = cw.coverage_under_delay(rows, crons, NFL, 24 * 60)
    assert carded == 0 and sum(lost.values()) == len(rows)


# -- the backup has to be able to back up -------------------------------------

def test_a_dropped_first_run_still_cards_almost_the_whole_slate(rows) -> None:
    """The reason the 15:30 UTC trigger exists.

    With only the 14:00 and 21:00 UTC triggers, a dropped first run left 183 of
    272 games uncarded — every 13:00 ET game, 55% of the season — and carded 34
    more inside the inactives window. The backup has to arrive before the games
    it is backing up.
    """
    unreachable = [r for r in rows if r.fallback_lead_hours is None]
    tight = [
        r for r in rows
        if r.fallback_lead_hours is not None
        and r.fallback_lead_hours * 60 < cw.INACTIVES_LEAD_MINUTES
    ]
    assert len(unreachable) <= 6, (
        f"A dropped first run would leave {len(unreachable)} games uncarded. "
        "Only the six 09:30 ET internationals are structurally unreachable; "
        "anything more means the backup trigger fires too late."
    )
    assert tight == [], (
        "A dropped first run would card "
        f"{[r.game_id for r in tight]} inside the inactives window. That is a "
        "different population, not a rescue."
    )


def test_the_backup_does_not_change_a_healthy_day(crons) -> None:
    """A backup that moves the operative lead is not a backup, it is a
    reschedule. Removing every trigger but the first must leave every carded
    game exactly where it is."""
    first_only = [min(crons, key=lambda c: (sorted(c.hours)[0], sorted(c.minutes)[0]))]
    with_backups = cw.carding_rows(NFL, RAW_DIR, season=SEASON, crons=crons)
    without = cw.carding_rows(NFL, RAW_DIR, season=SEASON, crons=first_only)
    assert [
        (r.game_id, r.operative_lead_hours) for r in with_backups
    ] == [(r.game_id, r.operative_lead_hours) for r in without]


# -- the report is derived, never hand-edited ---------------------------------

def test_the_committed_report_matches_what_the_script_generates(rows, crons) -> None:
    """A report edited by hand is a report that can disagree with the crons —
    which is the entire defect this file was written for."""
    path = PROJECT_ROOT / "data" / "outputs" / NFL.output_name("carding_window", ".md")
    assert path.is_file(), f"{path} is not committed; run scripts/run_carding_window.py"
    expected = cw.render(
        rows,
        crons,
        season=SEASON,
        league=NFL,
        dark_days=cw.days_without_any_run(rows, crons, NFL),
    )
    assert path.read_text(encoding="utf-8") == expected, (
        "The committed carding-window report is not what the script produces. "
        "Regenerate it: PYTHONPATH=src python scripts/run_carding_window.py "
        f"--season {SEASON}"
    )
