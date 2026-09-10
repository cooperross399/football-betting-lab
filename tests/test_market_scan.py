"""Predicting the margin is easy and worthless. The line already does it.

Everything here guards the one thing that could manufacture an edge that is not
there: a rating that saw the game it is pricing, or a mapping fitted on the
season it is scoring. A club-week must never contribute to its own rating, and
a sixteen-game Sunday must not leak fifteen results into the sixteenth.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from football_betting_lab.reports import market_scan as ms


def _long(rows) -> pd.DataFrame:
    """(team, season, week, metric, side, value, weight)."""
    return pd.DataFrame(
        [{"team": t, "season": s, "week": w, "metric": m, "side": sd,
          "value": v, "weight": g} for t, s, w, m, sd, v, g in rows]
    )


def test_a_club_week_never_contributes_to_its_own_rating() -> None:
    """The whole result rests on this. A rating that includes today's game
    predicts today's game, and the backtest reports an edge that is a leak."""
    rows = [("AAA", 2024, w, "epa_dropback", "offence", 0.0, 30) for w in range(1, 6)]
    rows.append(("AAA", 2024, 6, "epa_dropback", "offence", 99.0, 30))
    form = ms.club_form(_long(rows))
    week_six = form[(form["team"] == "AAA") & (form["week"] == 6)]
    assert float(week_six["epa_dropback_offence"].iloc[0]) == pytest.approx(0.0)


def test_early_season_form_is_empty_columns_and_not_missing_ones() -> None:
    """`pivot_table` drops a column that is entirely NaN, and `scan` then fails
    on a KeyError that says nothing about the real cause — which is only that
    no club has played enough games yet."""
    rows = [("AAA", 2024, w, "epa_dropback", "offence", 1.0, 30) for w in range(1, 4)]
    form = ms.club_form(_long(rows))
    for metric, side in ms.RATING_METRICS:
        assert f"{metric}_{side}" in form.columns
    assert form["epa_dropback_offence"].isna().all()


def test_form_is_weighted_by_the_plays_behind_it() -> None:
    """A three-play week must not count as much as a sixty-play one."""
    rows = [("AAA", 2024, w, "epa_dropback", "offence", 0.0, 60) for w in range(1, 5)]
    rows.append(("AAA", 2024, 5, "epa_dropback", "offence", 10.0, 3))
    rows.append(("AAA", 2024, 6, "epa_dropback", "offence", 0.0, 60))
    form = ms.club_form(_long(rows))
    value = float(form[(form["team"] == "AAA") & (form["week"] == 6)]["epa_dropback_offence"].iloc[0])
    assert value == pytest.approx((10.0 * 3) / (60 * 4 + 3))
    assert value < 0.2          # the three-play week barely moves it


def _games(rows) -> pd.DataFrame:
    return pd.DataFrame(
        [{"season": s, "week": w, "game_id": f"{s}_{w}_{a}_{h}", "home_team": h,
          "away_team": a, "result": r, "total": t, "spread_line": sl,
          "total_line": tl}
         for s, w, h, a, r, t, sl, tl in rows]
    )


def _flat_form(seasons, teams, weeks=19) -> pd.DataFrame:
    rows = []
    for season in seasons:
        for team in teams:
            for week in range(1, weeks + 1):
                for metric, side in ms.RATING_METRICS:
                    rows.append((team, season, week, metric, side,
                                 1.0 if team == teams[0] else -1.0, 40))
    return ms.club_form(_long(rows))


def test_a_season_is_scored_only_from_seasons_before_it() -> None:
    """Refitting on the season being scored is the second way this leaks."""
    teams = [f"T{i:02d}" for i in range(32)]
    rng = np.random.default_rng(1)
    rows = []
    for season in (2020, 2021, 2022):
        for week in range(5, 18):
            for index in range(0, len(teams), 2):
                home, away = teams[index], teams[index + 1]
                rows.append((season, week, home, away,
                             float(rng.normal(3, 10)), 45.0, 3.0, 44.0))
    out = ms.scan(_games(rows), _flat_form((2020, 2021, 2022), teams))
    assert not out.frame.empty
    # 2020 has no prior season, so it can never be scored.
    assert 2020 not in set(out.frame["season"])


def test_a_game_with_no_prior_form_is_dropped_rather_than_imputed() -> None:
    teams = ["AAA", "BBB"]
    rows = [(2021, w, teams[0], teams[1], 3.0, 45.0, 3.0, 44.0) for w in range(5, 18)]
    rows += [(2022, w, teams[0], teams[1], 3.0, 45.0, 3.0, 44.0) for w in range(5, 18)]
    games = _games(rows)
    games.loc[len(games)] = {
        "season": 2022, "week": 9, "game_id": "orphan", "home_team": "ZZZ",
        "away_team": "YYY", "result": 40.0, "total": 60.0, "spread_line": 0.0,
        "total_line": 44.0,
    }
    out = ms.scan(games, _flat_form((2021, 2022), teams))
    assert "orphan" not in set(out.frame["game_id"])


# -- settlement --------------------------------------------------------------

def _scanned(model_margin, spread_line, result):
    return pd.DataFrame([{
        "season": 2024, "game_id": "g1", "model_margin": model_margin,
        "spread_line": spread_line, "result": result,
        "model_total": 44.0, "total_line": 44.0, "total": 44.0,
    }])


def test_a_correct_side_pays_the_minus_110_price_and_not_even_money() -> None:
    """At a fair price every number in this report would be about four points
    better and none of them would be a strategy."""
    settled = ms.settle(_scanned(7.0, 3.0, 10.0), threshold=1.0)
    spread = settled[settled["market"] == "spread"]
    assert float(spread["profit"].iloc[0]) == pytest.approx(100 / 110)


def test_a_wrong_side_loses_the_whole_stake() -> None:
    settled = ms.settle(_scanned(7.0, 3.0, -10.0), threshold=1.0)
    assert float(settled[settled["market"] == "spread"]["profit"].iloc[0]) == -1.0


def test_a_push_returns_the_stake_rather_than_counting_as_a_loss() -> None:
    settled = ms.settle(_scanned(7.0, 3.0, 3.0), threshold=1.0)
    assert float(settled[settled["market"] == "spread"]["profit"].iloc[0]) == 0.0


def test_the_threshold_excludes_a_game_the_model_agrees_with() -> None:
    assert ms.settle(_scanned(3.2, 3.0, 10.0), threshold=1.0).empty


def test_a_total_is_read_from_both_clubs_and_a_margin_from_their_difference() -> None:
    """A total is about how much both sides do; a margin about who wins. Using
    one design for both would make every good offence raise the spread."""
    frame = pd.DataFrame([{"home_a": 2.0, "away_a": 1.0}])
    assert ms._design(frame, ["a"]).tolist() == [[1.0, 1.0]]
    assert ms._design_total(frame, ["a"]).tolist() == [[1.0, 3.0]]
