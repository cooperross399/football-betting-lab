"""The board is context beside a price, and its arithmetic has to be right.

Two things here have already been wrong once. `was_pressure` is False on every
run, so a mean over all plays is the pressure rate multiplied by how often the
defence faced a pass — a fact about the opposing offences, not about the rush —
and it moved the league's top pass rush from CLE to SEA when it was wrong. And
a board that quotes a reliability weight must quote the one the report actually
produced, not a number typed in beside a layer that needed help.
"""

from __future__ import annotations

import pandas as pd
import pytest

from football_betting_lab.reports import matchup_board as mb
from football_betting_lab.reports.reliability import MEASURED


def _participation(rows) -> pd.DataFrame:
    """(game, possession, man/zone or None, pressure, rushers)."""
    return pd.DataFrame(
        [{"nflverse_game_id": g, "possession_team": p,
          "defense_man_zone_type": mz, "was_pressure": pr,
          "number_of_pass_rushers": n} for g, p, mz, pr, n in rows]
    )


def test_pressure_is_a_rate_per_dropback_and_not_per_play() -> None:
    """Four dropbacks, two pressured, and six runs. The answer is 0.50, not
    0.20 — and the difference is entirely the defence's opponents' pass rate."""
    rows = [("2025_01_AAA_BBB", "AAA", "ZONE_COVERAGE", True, 4) for _ in range(2)]
    rows += [("2025_01_AAA_BBB", "AAA", "MAN_COVERAGE", False, 4) for _ in range(2)]
    rows += [("2025_01_AAA_BBB", "AAA", None, False, None) for _ in range(6)]
    profile = mb.team_profiles(
        _participation(rows), _pfr_pass(), _pfr_def(), _pfr_rush()
    )
    assert profile.loc["BBB", "pressure_gen"] == pytest.approx(0.5)


def test_the_blitz_rate_shares_that_denominator() -> None:
    rows = [("2025_01_AAA_BBB", "AAA", "ZONE_COVERAGE", False, 6) for _ in range(1)]
    rows += [("2025_01_AAA_BBB", "AAA", "ZONE_COVERAGE", False, 4) for _ in range(3)]
    rows += [("2025_01_AAA_BBB", "AAA", None, False, None) for _ in range(6)]
    profile = mb.team_profiles(
        _participation(rows), _pfr_pass(), _pfr_def(), _pfr_rush()
    )
    assert profile.loc["BBB", "blitz_rate"] == pytest.approx(0.25)


def _pfr_pass() -> pd.DataFrame:
    return pd.DataFrame([{"team": t, "times_pressured_pct": v}
                         for t, v in (("AAA", 0.20), ("BBB", 0.30))])


def _pfr_def() -> pd.DataFrame:
    return pd.DataFrame([{"team": t, "def_completion_pct": c, "def_adot": a,
                          "def_targets": n}
                         for t, c, a, n in (("AAA", 0.60, 8.0, 50),
                                            ("BBB", 0.70, 9.0, 50))])


def _pfr_rush() -> pd.DataFrame:
    return pd.DataFrame([{"team": t, "rushing_yards_before_contact_avg": b,
                          "rushing_yards_after_contact_avg": a, "carries": 100}
                         for t, b, a in (("AAA", 2.0, 3.0), ("BBB", 3.0, 2.0))])


# -- the price ---------------------------------------------------------------

def test_implied_totals_split_the_total_around_the_spread() -> None:
    home, away = mb.implied_totals(3.0, 44.5)
    assert (home, away) == pytest.approx((23.75, 20.75))
    assert home + away == pytest.approx(44.5)
    assert home - away == pytest.approx(3.0)


def test_a_positive_spread_line_favours_the_home_side() -> None:
    """The convention is documented in closing_line_backtest and confirmed
    against results: home margin averages +5.85 when spread_line is positive.
    Reading it the other way inverts every implied total on the board."""
    home, away = mb.implied_totals(7.0, 49.5)
    assert home > away


def test_a_missing_line_leaves_the_implied_totals_missing_not_zero() -> None:
    schedule = pd.DataFrame([{
        "season": 2026, "week": 1, "game_type": "REG", "gameday": "2026-09-13",
        "gametime": "13:00", "home_team": "AAA", "away_team": "BBB",
        "spread_line": None, "total_line": None,
    }])
    profiles = mb.team_profiles(
        _participation([("2025_01_AAA_BBB", "AAA", "ZONE_COVERAGE", True, 4)]),
        _pfr_pass(), _pfr_def(), _pfr_rush(),
    )
    row = mb.board(schedule, profiles, season=2026, week=1).iloc[0]
    assert pd.isna(row["home_implied"]) and pd.isna(row["away_implied"])


def test_a_club_with_no_profile_reports_nothing_rather_than_crashing() -> None:
    schedule = pd.DataFrame([{
        "season": 2026, "week": 1, "game_type": "REG", "gameday": "2026-09-13",
        "gametime": "13:00", "home_team": "ZZZ", "away_team": "YYY",
        "spread_line": 1.0, "total_line": 40.0,
    }])
    profiles = mb.team_profiles(
        _participation([("2025_01_AAA_BBB", "AAA", "ZONE_COVERAGE", True, 4)]),
        _pfr_pass(), _pfr_def(), _pfr_rush(),
    )
    row = mb.board(schedule, profiles, season=2026, week=1).iloc[0]
    assert pd.isna(row["home_pressure_gen"])


# -- the weights -------------------------------------------------------------

def test_every_layer_takes_its_weight_from_the_measured_table() -> None:
    """No layer may carry a hand-typed reliability. The dict is pinned against
    the committed report by test_feature_reliability."""
    for layer in mb.LAYERS:
        assert layer.reliability_of in MEASURED
        assert layer.reliability == MEASURED[layer.reliability_of]


def test_no_layer_is_quietly_repeated() -> None:
    keys = [layer.key for layer in mb.LAYERS]
    assert len(keys) == len(set(keys))
