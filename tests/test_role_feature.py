"""A role change is the one thing the props model cannot see, and the one
thing whose feature can most easily see forward.

`fit_rates` builds a player's rates from his own history, and that history was
recorded while somebody else held the role — so a team-mate's absence is
invisible to the model by construction. The risk runs the other way: an injury
feed that is edited after kickoff would hand the fit tomorrow's news, and a
share table built on appearances gives an absent player no baseline at all,
which silently zeroes the very quantity being measured.
"""

from __future__ import annotations

import pandas as pd
import pytest

from football_betting_lab.reports import role_feature as role


def _schedule(kick: str = "2024-10-06", time: str = "13:00") -> pd.DataFrame:
    return pd.DataFrame([{
        "season": 2024, "week": 5, "home_team": "AAA", "away_team": "BBB",
        "game_type": "REG", "gameday": kick, "gametime": time,
    }])


def _injury(modified: str, status: str = "Out", position: str = "WR") -> pd.DataFrame:
    return pd.DataFrame([{
        "season": 2024, "week": 5, "team": "AAA", "gsis_id": "00-0001",
        "position": position, "report_status": status, "game_type": "REG",
        "date_modified": modified,
    }])


def test_an_injury_row_edited_after_kickoff_is_hindsight_and_is_dropped() -> None:
    late = role.ruled_out_by_card_time(_injury("2024-10-06T18:00:00Z"), _schedule())
    assert late.empty


def test_a_row_edited_inside_the_card_window_is_dropped_too() -> None:
    """The card prices about six hours out. Anything the feed learned later
    was not knowable when the wager was placed."""
    inside = role.ruled_out_by_card_time(_injury("2024-10-06T10:00:00Z"), _schedule())
    assert inside.empty


def test_a_row_filed_the_day_before_is_kept() -> None:
    early = role.ruled_out_by_card_time(_injury("2024-10-05T12:00:00Z"), _schedule())
    assert list(early["player_id"]) == ["00-0001"]


def test_a_row_with_no_timestamp_cannot_be_shown_to_precede_the_card() -> None:
    assert role.ruled_out_by_card_time(_injury(""), _schedule()).empty


def test_only_out_counts_and_only_at_a_position_that_frees_targets() -> None:
    assert role.ruled_out_by_card_time(
        _injury("2024-10-05T12:00:00Z", status="Questionable"), _schedule()
    ).empty
    assert role.ruled_out_by_card_time(
        _injury("2024-10-05T12:00:00Z", position="CB"), _schedule()
    ).empty


def _pbp(rows) -> pd.DataFrame:
    return pd.DataFrame(
        [{"season": 2024, "season_type": "REG", "pass_attempt": 1, "week": w,
          "posteam": t, "receiver_player_id": r} for w, t, r in rows]
    )


def test_a_player_who_missed_a_week_still_has_a_baseline_that_week() -> None:
    """The grid is built on club-weeks, not appearances. Keyed on appearances,
    a player who is OUT has no row at all, so the vacated share built from that
    join is silently zero for every absence it exists to measure — which is
    exactly what the first version of this did."""
    rows = [(1, "AAA", "00-0001")] * 6 + [(1, "AAA", "00-0002")] * 4
    rows += [(2, "AAA", "00-0002")] * 5          # 00-0001 absent in week 2
    shares = role.target_shares(_pbp(rows))
    absent = shares[(shares["week"] == 2) & (shares["player_id"] == "00-0001")]
    assert len(absent) == 1
    assert absent["baseline_share"].iloc[0] == pytest.approx(0.6)


def test_the_vacated_share_is_what_the_absent_players_used_to_hold() -> None:
    rows = [(1, "AAA", "00-0001")] * 6 + [(1, "AAA", "00-0002")] * 4
    rows += [(2, "AAA", "00-0002")] * 5
    shares = role.target_shares(_pbp(rows))
    out = pd.DataFrame([{"season": 2024, "week": 2, "club": "AAA", "player_id": "00-0001"}])
    vacated = role.vacated_share(shares, out)
    assert vacated["vacated"].iloc[0] == pytest.approx(0.6)


def _bets(player: str = "00-0002") -> pd.DataFrame:
    return pd.DataFrame([{
        "season": 2024, "week": 2, "team": "AAA", "player_id": player, "line": 3.5,
    }])


def _shares() -> pd.DataFrame:
    return pd.DataFrame([
        {"season": 2024, "week": 2, "club": "AAA", "player_id": "00-0002",
         "baseline_share": 0.25, "weeks_before": 4},
        {"season": 2024, "week": 2, "club": "AAA", "player_id": "00-0001",
         "baseline_share": 0.50, "weeks_before": 4},
    ])


def test_the_expected_gain_is_the_pro_rata_share_of_what_was_vacated() -> None:
    vacated = pd.DataFrame([{"season": 2024, "week": 2, "club": "AAA", "vacated": 0.5}])
    out = pd.DataFrame([{"season": 2024, "week": 2, "club": "AAA", "player_id": "00-0001"}])
    attached = role.attach(_bets(), _shares(), vacated, out)
    assert attached["expected_gain"].iloc[0] == pytest.approx(0.25 * 0.5 / 0.5)


def test_a_wager_on_a_player_his_own_club_ruled_out_is_not_a_role_change_bet() -> None:
    vacated = pd.DataFrame([{"season": 2024, "week": 2, "club": "AAA", "vacated": 0.5}])
    out = pd.DataFrame([{"season": 2024, "week": 2, "club": "AAA", "player_id": "00-0001"}])
    assert role.attach(_bets("00-0001"), _shares(), vacated, out).empty


def test_a_join_that_duplicates_a_wager_is_refused() -> None:
    doubled = pd.concat([_shares(), _shares()], ignore_index=True)
    vacated = pd.DataFrame([{"season": 2024, "week": 2, "club": "AAA", "vacated": 0.5}])
    with pytest.raises(ValueError, match="changed the row count"):
        role.attach(_bets(), doubled, vacated, pd.DataFrame(
            columns=["season", "week", "club", "player_id"]
        ))


def test_a_club_with_nobody_out_has_nothing_vacated_rather_than_nothing_at_all() -> None:
    empty = pd.DataFrame(columns=["season", "week", "club", "vacated"])
    attached = role.attach(_bets(), _shares(), empty, pd.DataFrame(
        columns=["season", "week", "club", "player_id"]
    ))
    assert attached["vacated"].iloc[0] == 0.0
    assert attached["expected_gain"].iloc[0] == 0.0


# -- the rushing replication sample -------------------------------------------


def test_a_missing_receiver_frees_no_carries() -> None:
    """The two volumes take different positions. A receiver out of the game
    does not hand anybody a rushing attempt, and counting him as vacated
    carries would put noise into the replication sample on purpose."""
    receiver = _injury("2024-10-05T12:00:00Z", position="WR")
    assert role.ruled_out_by_card_time(
        receiver, _schedule(), volume=role.CARRIES
    ).empty
    assert not role.ruled_out_by_card_time(
        receiver, _schedule(), volume=role.TARGETS
    ).empty


def test_the_carry_volume_reads_the_rusher_columns() -> None:
    assert role.CARRIES.actor == "rusher_player_id"
    assert role.CARRIES.attempt == "rush_attempt"
    assert role.CARRIES.positions == role.RUSHING_POSITIONS


def test_shares_are_computed_the_same_way_for_either_volume() -> None:
    rows = [(1, "AAA", "00-0001")] * 6 + [(1, "AAA", "00-0002")] * 4
    rows += [(2, "AAA", "00-0002")] * 5
    carries = pd.DataFrame(
        [{"season": 2024, "season_type": "REG", "rush_attempt": 1, "week": w,
          "posteam": t, "rusher_player_id": r} for w, t, r in rows]
    )
    shares = role.volume_shares(carries, role.CARRIES)
    absent = shares[(shares["week"] == 2) & (shares["player_id"] == "00-0001")]
    assert absent["baseline_share"].iloc[0] == pytest.approx(0.6)


def test_the_two_market_sets_do_not_overlap() -> None:
    assert not set(role.RECEIVING_MARKETS) & set(role.RUSHING_MARKETS)
