"""Pressure is the most persistent feature this lab measures. Joining it is the risk.

`pfr_advstats` is keyed by Pro Football Reference's own player id and every
other feed here by GSIS, so a crosswalk stands between the feature and the
wagers. A crosswalk that fans one wager into two makes every interval too
narrow, which is the defect class this repository has already retracted a
result over — so the ambiguous rows are dropped rather than guessed at.
"""

from __future__ import annotations

import pandas as pd
import pytest

from football_betting_lab.reports import pressure_feature as pf


def _players(rows: list[tuple[str, str]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["gsis_id", "pfr_id"])


def _def(rows: list[tuple[int, str, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        [{"season": s, "pfr_player_id": p, "def_pressures": v} for s, p, v in rows]
    )


def test_a_pfr_id_serving_two_players_is_dropped_rather_than_guessed_at() -> None:
    bridge = pf.crosswalk(_players([
        ("00-0001", "SmitJo00"), ("00-0002", "SmitJo00"), ("00-0003", "JoneAl00"),
    ]))
    assert set(bridge["pfr_id"]) == {"JoneAl00"}


def test_a_row_missing_either_identifier_never_enters_the_crosswalk() -> None:
    bridge = pf.crosswalk(pd.DataFrame(
        {"gsis_id": ["00-0001", None, "00-0003"], "pfr_id": ["A00", "B00", None]}
    ))
    assert list(bridge["gsis_id"]) == ["00-0001"]


def test_a_feed_without_both_identifiers_is_refused() -> None:
    with pytest.raises(ValueError, match="pfr_id"):
        pf.crosswalk(pd.DataFrame({"gsis_id": ["00-0001"]}))


def test_pressures_are_per_game_and_a_short_season_is_gated_out() -> None:
    rows = [(2024, "aaa", 3.0)] * pf.MIN_GAMES + [(2024, "bbb", 9.0)] * (pf.MIN_GAMES - 1)
    out = pf.defender_pressure_rate(_def(rows))
    assert list(out["pfr_player_id"]) == ["aaa"]
    assert out["pressures_per_game"].iloc[0] == pytest.approx(3.0)


def test_the_rate_is_standardised_within_season_and_not_across() -> None:
    """The league-wide level moves between seasons. A globally centred rate
    would make the regressor partly an indicator of which season it is."""
    rows = (
        [(2023, "aaa", 1.0)] * pf.MIN_GAMES + [(2023, "bbb", 3.0)] * pf.MIN_GAMES
        + [(2024, "aaa", 11.0)] * pf.MIN_GAMES + [(2024, "bbb", 13.0)] * pf.MIN_GAMES
    )
    out = pf.defender_pressure_rate(_def(rows))
    for season in (2023, 2024):
        part = out[out["season"] == season].sort_values("pfr_player_id")
        assert part["pressure_z"].iloc[0] < 0 < part["pressure_z"].iloc[1]
    early = out[(out["season"] == 2023) & (out["pfr_player_id"] == "aaa")]
    late = out[(out["season"] == 2024) & (out["pfr_player_id"] == "aaa")]
    assert early["pressure_z"].iloc[0] == pytest.approx(late["pressure_z"].iloc[0])


def test_a_club_whose_quarterbacks_barely_played_is_gated_out() -> None:
    frame = pd.DataFrame(
        [{"season": 2024, "team": "AAA", "times_pressured_pct": 20.0}] * pf.MIN_GAMES
        + [{"season": 2024, "team": "BBB", "times_pressured_pct": 40.0}] * pf.MIN_GAMES
        + [{"season": 2024, "team": "CCC", "times_pressured_pct": 99.0}]
    )
    out = pf.offence_pressure_allowed(frame)
    assert set(out["team"]) == {"AAA", "BBB"}
    assert out.loc[out["team"] == "AAA", "pressure_allowed_z"].iloc[0] < 0


def test_the_defensive_markets_are_the_ones_a_pass_rush_can_reach() -> None:
    """`defensive_interceptions` is excluded at 45 wagers — an interval from
    that many is decorative, and printing one invites it to be read."""
    assert pf.DEFENSIVE_MARKETS == ("sacks", "tackles_assists")
    assert "defensive_interceptions" not in pf.DEFENSIVE_MARKETS
