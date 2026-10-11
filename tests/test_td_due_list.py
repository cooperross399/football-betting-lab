"""The NFL TD Due List: who is due, and that the list never becomes a selection."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from football_betting_lab import td_due_list as due
from football_betting_lab.leagues import NFL


def _logs(rows: list[tuple[str, int, int, int]], *, name: str = "") -> pd.DataFrame:
    """(player_id, season, week, touchdowns) -> a minimal player-log frame."""
    return pd.DataFrame(
        {
            "player_id": [r[0] for r in rows],
            "player_name": [name or r[0] for r in rows],
            "season": [r[1] for r in rows],
            "week": [r[2] for r in rows],
            "game_id": [f"{r[1]}_{r[2]:02d}_{r[0]}" for r in rows],
            "anytime_td_count": [r[3] for r in rows],
        }
    )


def _season(pid: str, season: int, tds: list[int]) -> list[tuple[str, int, int, int]]:
    return [(pid, season, week, td) for week, td in enumerate(tds, start=1)]


@pytest.mark.parametrize(
    "prior, bar, band",
    [(None, None, None), (7, None, None), (8, 5, "8-9"), (9, 5, "8-9"), (10, 4, "10-11"),
     (11, 4, "10-11"), (12, 3, "12+"), (20, 3, "12+")],
)
def test_the_bar_scales_with_last_seasons_touchdowns(prior, bar, band) -> None:
    assert due.tier_bar(prior) == bar
    assert due.band_label(prior) == band


def test_the_drought_counts_games_entering_and_carries_across_the_season() -> None:
    # 12 TDs last season (one a game, then two blanks to end it), then two
    # blanks to open this season: entering week 3 he has gone 4 without one.
    last = _season("A", 2025, [1] * 12 + [0, 0])
    this = _season("A", 2026, [0, 0, 1, 0])
    prepared = due.prepare_logs(_logs(last + this))
    rows = prepared[prepared["season"] == 2026].set_index("week")
    assert rows.loc[1, "drought"] == 2
    assert rows.loc[2, "drought"] == 3
    assert rows.loc[3, "drought"] == 4
    assert rows.loc[4, "drought"] == 0  # he scored in week 3
    assert rows.loc[1, "prior_tds"] == 12 and rows.loc[1, "bar"] == 3
    assert not rows.loc[1, "listed"] and rows.loc[2, "listed"] and rows.loc[3, "listed"]
    assert rows.loc[3, "prior_rate"] == pytest.approx(12 / 14)


def test_a_missing_touchdown_count_is_not_a_game_without_one() -> None:
    logs = _logs(_season("A", 2025, [1] * 10) + _season("A", 2026, [0, 0]))
    logs.loc[logs.index[-1], "anytime_td_count"] = None
    prepared = due.prepare_logs(logs)
    assert len(prepared[prepared["season"] == 2026]) == 1


def test_entering_reads_tonight_without_leaking_it() -> None:
    logs = _logs(_season("A", 2025, [1] * 12) + _season("A", 2026, [0, 0, 0, 1]))
    # Week 4 is already in the table (a rebuilt table can hold it); entering
    # week 4 must not see its touchdown.
    state = due.entering(logs, season=2026, week=4)
    assert list(state["player_id"]) == ["A"]
    assert state.iloc[0]["drought"] == 3 and bool(state.iloc[0]["listed"])


def test_only_qualifiers_are_considered() -> None:
    logs = _logs(_season("B", 2025, [1] * 7 + [0] * 10) + _season("B", 2026, [0] * 9))
    assert due.entering(logs, season=2026, week=10).empty


def test_the_list_uses_the_current_club_and_never_invents_a_price() -> None:
    logs = _logs(_season("A", 2025, [1] * 12) + _season("A", 2026, [0, 0, 0]), name="Joe Runner")
    fixtures = [("NE", "BUF", "13:00 ET")]
    # His last logged club does not matter; the roster says BUF.
    rows = due.build_due_list(logs, season=2026, week=4, teams={"A": "BUF"}, fixtures=fixtures)
    assert len(rows) == 1
    row = rows[0]
    assert (row.team, row.opponent, row.drought, row.bar) == ("BUF", "NE", 3, 3)
    assert row.price is None
    assert "not posted" in due.render_section(rows, headline=None)
    # A club not on the slate lists nobody.
    assert due.build_due_list(logs, season=2026, week=4, teams={"A": "KC"}, fixtures=fixtures) == []


def test_the_price_is_the_best_posted_anytime_over() -> None:
    logs = _logs(_season("A", 2025, [1] * 12) + _season("A", 2026, [0, 0, 0]), name="Joe Runner Jr.")
    prices = pd.DataFrame(
        {
            "market": ["anytime_td", "anytime_td", "anytime_td", "rush_yards"],
            "player": ["Joe Runner", "Joe Runner", "Joe Runner", "Joe Runner"],
            "selection": ["over", "over", "under", "over"],
            "american_odds": [110, 135, 400, 900],
            "book": ["a", "b", "c", "d"],
        }
    )
    rows = due.build_due_list(
        logs, season=2026, week=4, teams={"A": "BUF"}, fixtures=[("NE", "BUF", "")], prices=prices
    )
    assert (rows[0].price, rows[0].book) == (135, "b")


def test_the_section_is_context_and_says_so() -> None:
    text = due.render_section([], headline=None)
    assert text.startswith(f"## {due.SECTION_TITLE}")
    assert "Context only" in text and "no units" in text
    assert "## Selections" not in text
    assert "No backtest is committed" in text


def test_the_headline_is_read_never_invented(tmp_path: Path) -> None:
    assert due.load_headline(tmp_path, NFL) is None
    payload = {
        "hit_rate": {"first_season": 2016, "listed_n": 700, "listed_rate": 0.3,
                     "others_n": 4000, "others_rate": 0.4},
        "priced": {"seasons": "2023-25", "bets": 250, "roi": -0.05, "low": -0.2, "high": 0.1},
    }
    (tmp_path / due.backtest_json_name(NFL)).write_text(json.dumps(payload))
    sentence = due.headline_sentence(due.load_headline(tmp_path, NFL))
    assert "30.0% of 700 games" in sentence
    assert "-5.0% over 250 bets" in sentence and "no demonstrated edge" in sentence


def test_a_day_without_nfl_games_adds_nothing(tmp_path: Path) -> None:
    logs = _logs(_season("A", 2025, [1] * 12))
    games = pd.DataFrame(
        {"season": [2026], "week": [1], "game_date": ["2026-09-09"], "home_team": ["SEA"],
         "away_team": ["NE"], "gametime": ["20:20"]}
    )
    kwargs = dict(season=2026, outputs_dir=tmp_path, league=NFL)
    assert due.card_section(logs, games, {}, None, slate_date="2026-09-10", **kwargs) == ""
    assert due.card_section(pd.DataFrame(), games, {}, None, slate_date="2026-09-09", **kwargs) == ""
    text = due.card_section(logs, games, {"A": "SEA"}, None, slate_date="2026-09-09", **kwargs)
    assert text.startswith(f"## {due.SECTION_TITLE}")


def test_a_sunday_card_lists_the_whole_rest_of_the_week() -> None:
    # Week 6 of 2026: Thursday 10-15, Sunday 10-18, Monday 10-19.
    games = pd.DataFrame(
        {
            "season": [2026] * 3,
            "week": [6] * 3,
            "game_date": ["2026-10-15", "2026-10-18", "2026-10-19"],
            "home_team": ["KC", "BUF", "DAL"],
            "away_team": ["LV", "NE", "NYG"],
            "gametime": ["20:15", "13:00", "20:15"],
        }
    )
    week, fixtures = due.slate_fixtures(games, season=2026, slate_date="2026-10-18")
    assert week == 6
    # Thursday is already played; Monday night is in, with its day shown.
    assert fixtures == [("BUF", "NE", "13:00 ET"), ("DAL", "NYG", "Mon 20:15 ET")]
    # Any other day stays its own slate.
    assert due.slate_fixtures(games, season=2026, slate_date="2026-10-15")[1] == [("KC", "LV", "20:15 ET")]

    logs = _logs(_season("A", 2025, [1] * 12) + _season("A", 2026, [0] * 5), name="Monday Back")
    rows = due.build_due_list(logs, season=2026, week=6, teams={"A": "NYG"}, fixtures=fixtures)
    assert [(r.team, r.kickoff) for r in rows] == [("NYG", "Mon 20:15 ET")]
