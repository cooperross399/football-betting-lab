"""The settlement columns are named for what they are, and mean it.

The NHL lab has a standing rule from a real bug: no column called
`power_play_points` holding a count of goals, because naming a goals count
"points" is a lie the model inherits and every report repeats. The football
version of that trap is `anytime_td`, and it is the first test here.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from football_betting_lab.config import PROCESSED_DIR
from football_betting_lab.data.build_datasets import (
    MAX_SHRINK,
    PLAYER_LOGS_FILENAME,
    TEAM_GAMES_FILENAME,
    BuildReport,
    _guard_shrink,
)


LOGS = PROCESSED_DIR / PLAYER_LOGS_FILENAME
GAMES = PROCESSED_DIR / TEAM_GAMES_FILENAME

pytestmark = pytest.mark.skipif(
    not LOGS.is_file() or not GAMES.is_file(),
    reason="processed tables not built in this checkout",
)


@pytest.fixture(scope="module")
def logs() -> pd.DataFrame:
    return pd.read_csv(LOGS, low_memory=False)


@pytest.fixture(scope="module")
def games() -> pd.DataFrame:
    return pd.read_csv(GAMES, low_memory=False)


def test_a_quarterback_who_threw_touchdowns_has_not_scored_them(
    logs: pd.DataFrame,
) -> None:
    """`anytime_td` settles on touchdowns SCORED — rushing, receiving, return,
    defensive. Reading `passing_tds` would credit every scoring drive to the
    quarterback and price him as the likeliest scorer on the field."""
    threw = logs[logs["pass_tds"] >= 4]

    assert len(threw) > 50, "not enough big passing games to make this meaningful"
    scored_without_running = threw[
        (threw["anytime_td"] == 1)
        & (threw["rush_tds"] == 0)
        & (threw["reception_tds"] == 0)
    ]

    assert scored_without_running.empty


def test_anytime_td_is_a_flag_and_its_count_agrees_with_it(logs: pd.DataFrame) -> None:
    assert set(logs["anytime_td"].unique()) <= {0, 1}
    assert (logs.loc[logs["anytime_td"] == 1, "anytime_td_count"] > 0).all()
    assert (logs.loc[logs["anytime_td"] == 0, "anytime_td_count"] == 0).all()


def test_kicking_points_is_three_per_field_goal_and_one_per_extra_point(
    logs: pd.DataFrame,
) -> None:
    expected = 3 * logs["field_goals"] + logs["pats"]

    assert (logs["kicking_points"] == expected).all()


def test_tackles_assists_is_solo_plus_assists(logs: pd.DataFrame) -> None:
    """Not `def_tackles_with_assist`, which counts tackles made *with* an
    assister and would double-count against the solo column."""
    assert (logs["tackles_assists"] == logs["solo_tackles"] + logs["tackle_assists"]).all()


def test_the_longest_markets_are_maxima_and_never_exceed_the_season_record(
    logs: pd.DataFrame,
) -> None:
    """A maximum cannot be recovered from a weekly total, which is the only
    reason play-by-play is read at all. 99 yards is the longest play possible
    from scrimmage."""
    for column in ("pass_longest_completion", "rush_longest", "reception_longest"):
        assert logs[column].max() <= 99, column


@pytest.mark.parametrize(
    ("count", "total", "longest"),
    [
        ("receptions", "reception_yards", "reception_longest"),
        ("rush_attempts", "rush_yards", "rush_longest"),
        ("pass_completions", "pass_yards", "pass_longest_completion"),
    ],
)
def test_a_single_play_makes_the_maximum_equal_the_total(
    logs: pd.DataFrame, count: str, total: str, longest: str
) -> None:
    """The tightest invariant the data actually supports.

    The obvious test — maximum never exceeds total — is **false**, and
    believing it cost a debugging pass. Yardage can be negative: AJ Dillon
    caught passes for 35 and -10 in 2023 week 14, so his total was 25 and his
    longest 35. That is 262 legitimate cases in four seasons, and a build that
    "fixed" them would be inventing data.

    With exactly one play there is nothing to cancel, so the maximum should be
    the total. A per-play join that matched the wrong player breaks this
    immediately, and that join is the bug family that cost the NHL lab weeks.

    "Should", not "must": the two sources disagree on a measured 0.21% of
    single-reception games. That is source noise, not a join fault, and the
    bound below is what tells them apart.
    """
    single = logs[logs[count] == 1]

    assert len(single) > 100, f"not enough single-{count} games to be meaningful"
    disagree = single[single[longest].fillna(0) != single[total]]
    rate = len(disagree) / len(single)

    # Not exact equality: the two sources genuinely disagree on a handful of
    # receptions (measured at 0.21% of single-reception games over four
    # seasons, 0.00% for rushes and completions). See the module docstring —
    # laterals and gamebook revisions, not a join fault. The bound is a
    # regression guard: a broken join would push this into the percents.
    assert rate < 0.01, (
        f"{len(disagree)} of {len(single)} single-{count} games disagree "
        f"({rate:.2%}). Above 1% this is a join fault, not source noise."
    )


def test_the_maximum_may_legitimately_exceed_the_total(logs: pd.DataFrame) -> None:
    """Recorded as a fact so nobody "fixes" it later.

    A reception behind the line of scrimmage loses yards, so a player's
    longest catch can be larger than his total. Asserting this holds is the
    only way the comment above stays true when the data is rebuilt.
    """
    caught = logs[(logs["receptions"] > 1) & (logs["reception_yards"] > 0)]
    exceeding = caught[caught["reception_longest"] > caught["reception_yards"]]

    assert not exceeding.empty


def test_a_player_with_no_carries_has_no_longest_rush(logs: pd.DataFrame) -> None:
    never_ran = logs[logs["rush_attempts"] == 0]

    assert (never_ran["rush_longest"].fillna(0) == 0).all()


def test_every_tier_one_settlement_column_exists(logs: pd.DataFrame) -> None:
    """A market wired with nothing to settle it is the one thing the market
    registry forbids. This is the other half of that promise."""
    from football_betting_lab.markets import PROP_MARKETS

    settled_here = {
        "pass_yards", "pass_attempts", "pass_completions", "pass_tds",
        "pass_interceptions", "pass_longest_completion", "rush_yards",
        "rush_attempts", "rush_tds", "rush_longest", "receptions",
        "reception_yards", "reception_tds", "reception_longest", "anytime_td",
        "kicking_points", "field_goals", "tackles_assists", "sacks",
        "defensive_interceptions",
    }
    tier_one = {market.key for market in PROP_MARKETS if market.tier == 1}

    assert tier_one == settled_here
    for column in sorted(settled_here):
        assert column in logs.columns, column


def test_the_2022_season_is_short_one_game_and_that_is_correct(
    games: pd.DataFrame,
) -> None:
    """Buffalo-Cincinnati was abandoned and never replayed. A build that
    "fixed" this to 272 would be inventing a game."""
    counts = games.groupby("season").size().to_dict()

    assert counts.get(2022) == 271
    for season in (2023, 2024, 2025, 2026):
        if season in counts:
            assert counts[season] == 272, season


def test_roof_is_never_treated_as_known_at_a_neutral_site(
    games: pd.DataFrame,
) -> None:
    """The column is blank for retractable venues and populated-and-wrong for
    three 2026 international fixtures labelled `dome` at open-air stadiums."""
    neutral = games[games["neutral_site"]]

    assert not neutral.empty
    assert not neutral["roof_known"].any()


def test_the_free_closing_line_series_is_present_for_completed_seasons(
    games: pd.DataFrame,
) -> None:
    """The team model's priced test, costing nothing and reaching back
    further than any purchase."""
    for season in (2024, 2025):
        rows = games[games["season"] == season]
        if rows.empty:
            continue
        assert rows["spread_line"].notna().all(), season
        assert rows["total_line"].notna().all(), season


# -- the shrink guard --------------------------------------------------------


def test_a_table_that_loses_most_of_its_rows_is_refused(tmp_path: Path) -> None:
    """An accumulated table that suddenly halves is a bug, not a season."""
    existing = tmp_path / "t.csv"
    existing.write_text("a\n" + "1\n" * 100, encoding="utf-8")
    report = BuildReport()

    assert not _guard_shrink("t.csv", existing, 10, report, allow_shrink=False)
    assert report.refused
    assert not report.ok


def test_a_table_that_grows_is_written(tmp_path: Path) -> None:
    existing = tmp_path / "t.csv"
    existing.write_text("a\n" + "1\n" * 100, encoding="utf-8")

    assert _guard_shrink("t.csv", existing, 120, BuildReport(), allow_shrink=False)


def test_the_shrink_guard_can_be_overridden_deliberately(tmp_path: Path) -> None:
    existing = tmp_path / "t.csv"
    existing.write_text("a\n" + "1\n" * 100, encoding="utf-8")

    assert _guard_shrink("t.csv", existing, 1, BuildReport(), allow_shrink=True)


def test_a_first_build_is_never_blocked_by_the_guard(tmp_path: Path) -> None:
    """Guarded on rows, not existence — but nothing to compare against is not
    a shrink."""
    assert _guard_shrink(
        "t.csv", tmp_path / "missing.csv", 5, BuildReport(), allow_shrink=False
    )


def test_the_shrink_threshold_is_a_half_and_is_stated_rather_than_inlined() -> None:
    assert MAX_SHRINK == 0.5


def test_a_combined_tackle_sums_all_three_defensive_columns():
    """Verified against a published box score, not argued from the column names.

    Zack Baun's 2024 regular season, 16 games:

        def_tackles_solo         82
        def_tackles_with_assist  11
        def_tackle_assists       58

    The official box score reports 93 solo and 151 combined. So the official
    *solo* figure is `solo + with_assist`, and *combined* is all three. An
    earlier version summed only solo and assists, reasoning that
    `def_tackles_with_assist` would "double-count against the solo column".
    It does not — the two are disjoint — and dropping it undercounted every
    defensive line by about 7%, which is the whole of the +12% tackles
    "edge" this lab reported for four days.
    """
    frame = pd.DataFrame(
        {
            "def_tackles_solo": [82.0],
            "def_tackles_with_assist": [11.0],
            "def_tackle_assists": [58.0],
        }
    )
    solo = frame["def_tackles_solo"] + frame["def_tackles_with_assist"]
    combined = solo + frame["def_tackle_assists"]

    assert float(solo.iloc[0]) == 93.0
    assert float(combined.iloc[0]) == 151.0
    # The old sum, kept here so the regression is named rather than implied.
    old = frame["def_tackles_solo"] + frame["def_tackle_assists"]
    assert float(old.iloc[0]) == 140.0
    assert float(combined.iloc[0]) - float(old.iloc[0]) == 11.0
