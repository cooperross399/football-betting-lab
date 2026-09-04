"""The settlement columns are named for what they are, and mean it.

The NHL lab has a standing rule from a real bug: no column called
`power_play_points` holding a count of goals, because naming a goals count
"points" is a lie the model inherits and every report repeats. The football
version of that trap is `anytime_td`, and it is the first test here.

Every test in this module used to sit under a module-level `skipif` on the
processed tables, which `.gitignore` keeps out of every checkout CI sees. So
in CI all twenty were skipped, on every run, forever, and pytest reported
green. A skip that cannot resolve is a test that does not exist, wearing a
test's name.

They now run against tables the REAL builder produces from a synthetic raw
feed written into `tmp_path` — the same `build_player_logs` and
`build_team_games`, fed the same nflverse file shapes, four players and three
games. That exercises the arithmetic and the joins, which is what these tests
were about. Three facts about the real data that no fixture can carry are
deleted rather than skipped, and named here so they are not rediscovered:
2022 has 271 games (Buffalo-Cincinnati was abandoned); the weekly stats and
play-by-play disagree on 0.21% of single-reception games; and the free
closing line is present for every 2024-25 game. CLAUDE.md records all three.
"""

from __future__ import annotations

import gzip
from pathlib import Path

import pandas as pd
import pytest

from football_betting_lab.data import nflverse
from football_betting_lab.data.build_datasets import (
    MAX_SHRINK,
    PBP_COLUMNS,
    BuildReport,
    _guard_shrink,
    build_player_logs,
    build_team_games,
)
from football_betting_lab.leagues import NFL


SEASON = 2024

#: Four players in one game and one game elsewhere: a quarterback who throws
#: four touchdowns and scores none, a back with one carry, a receiver whose
#: catches include a loss of yards, a kicker, and a defender.
PLAYER_STATS = [
    # season_type, game_id, player_id, name, position, team, opp, week, stats...
    dict(player_id="00-QB", player_display_name="Quinn Back", position="QB",
         completions=22, attempts=30, passing_yards=280, passing_tds=4,
         passing_interceptions=1, carries=0, rushing_yards=0, rushing_tds=0,
         receptions=0, targets=0, receiving_yards=0, receiving_tds=0),
    dict(player_id="00-RB", player_display_name="Rex Back", position="RB",
         completions=0, attempts=0, passing_yards=0, passing_tds=0,
         passing_interceptions=0, carries=1, rushing_yards=7, rushing_tds=1,
         receptions=0, targets=0, receiving_yards=0, receiving_tds=0),
    dict(player_id="00-WR", player_display_name="Wes Receiver", position="WR",
         completions=0, attempts=0, passing_yards=0, passing_tds=0,
         passing_interceptions=0, carries=0, rushing_yards=0, rushing_tds=0,
         receptions=2, targets=3, receiving_yards=25, receiving_tds=0),
    dict(player_id="00-K", player_display_name="Kip Kicker", position="K",
         fg_made=2, pat_made=3),
    dict(player_id="00-LB", player_display_name="Len Backer", position="LB",
         def_tackles_solo=5, def_tackles_with_assist=2, def_tackle_assists=3,
         def_sacks=1.5, def_interceptions=1, def_tds=1),
]

#: The plays behind the maxima: the receiver's 35 and -10 (AJ Dillon, 2023
#: week 14, is the real case that made "longest never exceeds total" false),
#: the back's single carry, and the quarterback's completions.
PLAYS = [
    dict(play_id=1, posteam="AAA", complete_pass=1, passer_player_id="00-QB",
         passing_yards=35, receiver_player_id="00-WR", receiving_yards=35),
    dict(play_id=2, posteam="AAA", complete_pass=1, passer_player_id="00-QB",
         passing_yards=-10, receiver_player_id="00-WR", receiving_yards=-10),
    dict(play_id=3, posteam="AAA", complete_pass=1, passer_player_id="00-QB",
         passing_yards=61, receiver_player_id="00-TE", receiving_yards=61),
    dict(play_id=4, posteam="AAA", complete_pass=0, rusher_player_id="00-RB",
         rushing_yards=7, touchdown=1, td_player_id="00-RB"),
    dict(play_id=5, posteam="AAA", complete_pass=0, passer_player_id="00-QB",
         passing_yards=0),
]

SCHEDULE_COLUMNS = [
    "game_id", "season", "game_type", "week", "gameday", "weekday", "gametime",
    "away_team", "away_score", "home_team", "home_score", "location", "result",
    "total", "overtime", "away_rest", "home_rest", "away_moneyline",
    "home_moneyline", "spread_line", "away_spread_odds", "home_spread_odds",
    "total_line", "under_odds", "over_odds", "div_game", "roof", "surface",
    "temp", "wind", "stadium",
]


def _write_raw(raw_dir: Path) -> None:
    """The three nflverse files the builder reads, in the shapes it reads."""
    stats_path = nflverse.feed_path(nflverse.FEEDS_BY_NAME["player_stats"], NFL, raw_dir, SEASON)
    stats_path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for row in PLAYER_STATS:
        rows.append({
            "season": SEASON, "week": 1, "season_type": "REG",
            "game_id": f"{SEASON}_01_BBB_AAA", "team": "AAA", "opponent_team": "BBB",
            **row,
        })
    # A post-season row that must be dropped, and a second game.
    rows.append({**rows[0], "season_type": "POST", "week": 19, "game_id": f"{SEASON}_19_AAA_CCC"})
    rows.append({**rows[1], "week": 2, "game_id": f"{SEASON}_02_AAA_CCC", "carries": 5,
                 "rushing_yards": 40, "rushing_tds": 0})
    pd.DataFrame(rows).to_csv(stats_path, index=False)

    pbp_path = nflverse.feed_path(nflverse.FEEDS_BY_NAME["pbp"], NFL, raw_dir, SEASON)
    pbp_path.parent.mkdir(parents=True, exist_ok=True)
    plays = []
    for play in PLAYS:
        plays.append({column: None for column in PBP_COLUMNS} | {
            "game_id": f"{SEASON}_01_BBB_AAA", "season_type": "REG", "qtr": 1,
            "home_team": "AAA", "away_team": "BBB", "total_home_score": 0,
            "total_away_score": 0, **play,
        })
    plays.append({**plays[0], "play_id": 9, "passing_yards": 99, "receiving_yards": 99,
                  "season_type": "POST", "game_id": f"{SEASON}_19_AAA_CCC"})
    plays.append({**plays[3], "play_id": 10, "game_id": f"{SEASON}_02_AAA_CCC",
                  "rushing_yards": 22})
    with gzip.open(pbp_path, "wt", encoding="utf-8") as handle:
        pd.DataFrame(plays)[list(PBP_COLUMNS)].to_csv(handle, index=False)

    schedule_path = nflverse.feed_path(nflverse.FEEDS_BY_NAME["schedules"], NFL, raw_dir, None)
    schedule_path.parent.mkdir(parents=True, exist_ok=True)
    games = [
        dict(game_id=f"{SEASON}_01_BBB_AAA", season=SEASON, game_type="REG", week=1,
             gameday="2024-09-08", location="Home", roof="outdoors", spread_line=-3.0,
             total_line=44.5, home_team="AAA", away_team="BBB"),
        dict(game_id=f"{SEASON}_02_AAA_CCC", season=SEASON, game_type="REG", week=2,
             gameday="2024-09-15", location="Neutral", roof="dome", spread_line=1.5,
             total_line=41.0, home_team="CCC", away_team="AAA"),
        dict(game_id=f"{SEASON}_03_DDD_EEE", season=SEASON, game_type="REG", week=3,
             gameday="2024-09-22", location="Home", roof="", spread_line=-7.0,
             total_line=47.0, home_team="EEE", away_team="DDD"),
        dict(game_id=f"{SEASON}_19_AAA_CCC", season=SEASON, game_type="POST", week=19,
             gameday="2025-01-12", location="Home", roof="dome", spread_line=-1.0,
             total_line=50.0, home_team="AAA", away_team="CCC"),
        dict(game_id=f"{SEASON - 1}_01_AAA_BBB", season=SEASON - 1, game_type="REG", week=1,
             gameday="2023-09-10", location="Home", roof="outdoors", spread_line=-2.0,
             total_line=42.0, home_team="AAA", away_team="BBB"),
    ]
    frame = pd.DataFrame(games)
    for column in SCHEDULE_COLUMNS:
        if column not in frame.columns:
            frame[column] = None
    frame[SCHEDULE_COLUMNS].to_csv(schedule_path, index=False)


@pytest.fixture(scope="module")
def raw_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    directory = tmp_path_factory.mktemp("raw")
    _write_raw(directory)
    return directory


@pytest.fixture(scope="module")
def logs(raw_dir: Path) -> pd.DataFrame:
    report = BuildReport()
    built = build_player_logs(NFL, raw_dir, (SEASON,), report)
    assert not built.empty, report.notes
    return built


@pytest.fixture(scope="module")
def games(raw_dir: Path) -> pd.DataFrame:
    return build_team_games(NFL, raw_dir, (SEASON,))


def _row(logs: pd.DataFrame, player_id: str, week: int = 1) -> pd.Series:
    found = logs[(logs["player_id"] == player_id) & (logs["week"] == week)]
    assert len(found) == 1, (player_id, week, len(found))
    return found.iloc[0]


def test_the_fixture_is_the_builders_own_output(logs: pd.DataFrame) -> None:
    """The positive control: the builder ran, dropped the post-season row,
    and kept one row per player-game. A fixture built by hand would prove
    nothing about the builder."""
    assert len(logs) == 6
    assert set(logs["week"]) == {1, 2}
    assert (logs["season"] == SEASON).all()


def test_a_quarterback_who_threw_touchdowns_has_not_scored_them(logs: pd.DataFrame) -> None:
    """`anytime_td` settles on touchdowns SCORED — rushing, receiving, return,
    defensive. Reading `passing_tds` would credit every scoring drive to the
    quarterback and price him as the likeliest scorer on the field."""
    quarterback = _row(logs, "00-QB")

    assert quarterback["pass_tds"] == 4
    assert quarterback["anytime_td"] == 0
    assert quarterback["anytime_td_count"] == 0


def test_anytime_td_is_a_flag_and_its_count_agrees_with_it(logs: pd.DataFrame) -> None:
    assert set(logs["anytime_td"].unique()) <= {0, 1}
    assert (logs.loc[logs["anytime_td"] == 1, "anytime_td_count"] > 0).all()
    assert (logs.loc[logs["anytime_td"] == 0, "anytime_td_count"] == 0).all()
    # A rushing score and a defensive score both count; a thrown one does not.
    assert _row(logs, "00-RB")["anytime_td"] == 1
    assert _row(logs, "00-LB")["anytime_td"] == 1


def test_kicking_points_is_three_per_field_goal_and_one_per_extra_point(
    logs: pd.DataFrame,
) -> None:
    kicker = _row(logs, "00-K")

    assert kicker["field_goals"] == 2 and kicker["pats"] == 3
    assert kicker["kicking_points"] == 9
    assert (logs["kicking_points"] == 3 * logs["field_goals"] + logs["pats"]).all()


def test_a_combined_tackle_sums_all_three_defensive_columns(logs: pd.DataFrame) -> None:
    """Verified against a published box score, not argued from the column
    names: Zack Baun's 2024 season is 82 solo + 11 with-assist + 58 assists,
    which the official box score reports as 93 solo and 151 combined. An
    earlier version summed only solo and assists and undercounted every
    defensive line by about 7%, which was the whole of a +12% tackles "edge"
    this lab reported for four days."""
    defender = _row(logs, "00-LB")

    assert defender["solo_tackles"] == 5 + 2
    assert defender["tackle_assists"] == 3
    assert defender["tackles_assists"] == 5 + 2 + 3
    assert (logs["tackles_assists"] == logs["solo_tackles"] + logs["tackle_assists"]).all()
    assert defender["sacks"] == 1.5 and defender["defensive_interceptions"] == 1


def test_the_longest_markets_are_maxima_from_play_by_play(logs: pd.DataFrame) -> None:
    """A maximum cannot be recovered from a weekly total, which is the only
    reason play-by-play is read at all — and the post-season 99-yarder must
    not leak into a regular-season maximum."""
    assert _row(logs, "00-QB")["pass_longest_completion"] == 61
    assert _row(logs, "00-WR")["reception_longest"] == 35
    assert _row(logs, "00-RB")["rush_longest"] == 7
    assert _row(logs, "00-RB", week=2)["rush_longest"] == 22
    for column in ("pass_longest_completion", "rush_longest", "reception_longest"):
        assert logs[column].max() <= 99, column


def test_a_single_play_makes_the_maximum_equal_the_total(logs: pd.DataFrame) -> None:
    """With exactly one play there is nothing to cancel, so the maximum is the
    total. A per-play join that matched the wrong player breaks this
    immediately, and that join is the bug family that cost the NHL lab weeks."""
    back = _row(logs, "00-RB")

    assert back["rush_attempts"] == 1
    assert back["rush_longest"] == back["rush_yards"] == 7


def test_the_maximum_may_legitimately_exceed_the_total(logs: pd.DataFrame) -> None:
    """Recorded as a fact so nobody "fixes" it later: a reception behind the
    line of scrimmage loses yards, so a player's longest catch can be larger
    than his total. 35 and -10 is 25 total, 35 longest."""
    receiver = _row(logs, "00-WR")

    assert receiver["receptions"] == 2
    assert receiver["reception_yards"] == 25
    assert receiver["reception_longest"] == 35
    assert receiver["reception_longest"] > receiver["reception_yards"]


def test_a_player_with_no_carries_has_no_longest_rush(logs: pd.DataFrame) -> None:
    never_ran = logs[logs["rush_attempts"] == 0]

    assert not never_ran.empty
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


def test_team_games_keep_only_the_regular_season_of_the_seasons_asked_for(
    games: pd.DataFrame,
) -> None:
    assert len(games) == 3
    assert set(games["game_id"]) == {
        f"{SEASON}_01_BBB_AAA", f"{SEASON}_02_AAA_CCC", f"{SEASON}_03_DDD_EEE",
    }
    assert games["spread_line"].notna().all() and games["total_line"].notna().all()


def test_roof_is_never_treated_as_known_at_a_neutral_site(games: pd.DataFrame) -> None:
    """The column is blank for retractable venues and populated-and-wrong for
    three 2026 international fixtures labelled `dome` at open-air stadiums, so
    a neutral-site fixture is roof-unknown regardless of what it says."""
    neutral = games[games["neutral_site"]]
    assert len(neutral) == 1
    assert neutral.iloc[0]["roof_stated"] == "dome"
    assert not neutral["roof_known"].any()

    domestic = games[~games["neutral_site"]].set_index("game_id")
    assert bool(domestic.loc[f"{SEASON}_01_BBB_AAA", "roof_known"])
    # Blank is unknown, whatever the venue.
    assert not bool(domestic.loc[f"{SEASON}_03_DDD_EEE", "roof_known"])


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
    assert _guard_shrink(
        "t.csv", tmp_path / "missing.csv", 5, BuildReport(), allow_shrink=False
    )


def test_the_shrink_threshold_is_a_half_and_is_stated_rather_than_inlined() -> None:
    assert MAX_SHRINK == 0.5
