"""Every rate here is a numerator over a denominator, and the denominator is
the part that goes wrong.

A pressure rate taken over all plays is the rate multiplied by how often that
defence faced a pass — a fact about its opponents, not its rush — and that
error moved the league's best pass rush from CLE to SEA in the first matchup
board. These tests pin the denominator of every family: dropbacks for passing
rates, rushes for rushing rates, drives counted once rather than once per play,
and targets for a Next Gen average taken across a club's receivers.
"""

from __future__ import annotations

import pandas as pd
import pytest

from football_betting_lab.reports import team_metrics as tm


def _play(**kw):
    row = {
        "season": 2025, "week": 1, "season_type": "REG", "game_id": "g1",
        "posteam": "AAA", "defteam": "BBB", "epa": 0.0, "success": 0.0,
        "qb_dropback": 0.0, "rush_attempt": 0.0, "pass_attempt": 0.0,
        "sack": 0.0, "qb_hit": 0.0, "cpoe": None, "pass_oe": None,
        "air_yards": None, "xpass": None, "down": 1, "shotgun": 0.0,
        "no_huddle": 0.0, "yards_gained": 0.0, "complete_pass": 0.0,
        "third_down_converted": 0.0, "third_down_failed": 0.0,
        "tackled_for_loss": 0.0, "interception": 0.0, "fumble_forced": 0.0,
        "yardline_100": 75, "fixed_drive": 1, "fixed_drive_result": "Punt",
        "drive_play_count": 3,
    }
    row.update(kw)
    return row


def _value(out, metric, side, team="AAA"):
    row = out[(out["metric"] == metric) & (out["side"] == side) & (out["team"] == team)]
    return None if row.empty else float(row["value"].iloc[0])


def test_epa_per_dropback_is_over_dropbacks_and_not_over_all_plays() -> None:
    """Two dropbacks worth +1.0 and six runs worth 0 average +1.0 per dropback,
    not +0.25 per play. The second number is mostly a statement about how often
    the club runs."""
    plays = [_play(qb_dropback=1.0, epa=1.0) for _ in range(2)]
    plays += [_play(rush_attempt=1.0, epa=0.0) for _ in range(6)]
    out = tm.team_week_metrics(pd.DataFrame(plays))
    assert _value(out, "epa_dropback", "offence") == pytest.approx(1.0)
    assert _value(out, "epa_play", "offence") == pytest.approx(0.25)


def test_a_kick_is_not_a_scrimmage_play() -> None:
    """A punt carries EPA and would otherwise dilute every efficiency rate."""
    plays = [_play(qb_dropback=1.0, epa=1.0),
             _play(epa=-5.0)]          # neither a dropback nor a rush
    out = tm.team_week_metrics(pd.DataFrame(plays))
    assert _value(out, "epa_play", "offence") == pytest.approx(1.0)


def test_the_same_play_is_credited_to_both_sides_of_the_ball() -> None:
    """A defence's EPA allowed is not a separate measurement."""
    out = tm.team_week_metrics(pd.DataFrame([_play(qb_dropback=1.0, epa=0.7)]))
    assert _value(out, "epa_dropback", "offence", "AAA") == pytest.approx(0.7)
    assert _value(out, "epa_dropback", "defence", "BBB") == pytest.approx(0.7)


def test_explosive_thresholds_differ_between_the_pass_and_the_run() -> None:
    """One threshold for both would make every rushing offence look
    inexplosive by construction."""
    plays = [_play(qb_dropback=1.0, yards_gained=15.0),
             _play(rush_attempt=1.0, yards_gained=15.0)]
    out = tm.team_week_metrics(pd.DataFrame(plays))
    assert _value(out, "explosive_pass", "offence") == pytest.approx(0.0)
    assert _value(out, "explosive_rush", "offence") == pytest.approx(1.0)


def test_a_drive_is_counted_once_and_not_once_per_play_in_it() -> None:
    """Six plays on one scoring drive is one drive worth of points, and
    counting per play would make a long drive look like six good ones."""
    plays = [_play(fixed_drive=1, fixed_drive_result="Touchdown",
                   drive_play_count=6, qb_dropback=1.0) for _ in range(6)]
    out = tm.team_week_metrics(pd.DataFrame(plays))
    row = out[(out["metric"] == "points_per_drive") & (out["side"] == "offence")]
    assert float(row["weight"].iloc[0]) == 1.0
    assert float(row["value"].iloc[0]) == pytest.approx(6.94)


def test_a_three_and_out_needs_both_the_punt_and_the_short_drive() -> None:
    plays = [_play(fixed_drive=1, fixed_drive_result="Punt", drive_play_count=3),
             _play(fixed_drive=2, fixed_drive_result="Punt", drive_play_count=9),
             _play(fixed_drive=3, fixed_drive_result="Touchdown", drive_play_count=3)]
    out = tm.team_week_metrics(pd.DataFrame(plays))
    assert _value(out, "three_and_out_rate", "offence") == pytest.approx(1 / 3)


def test_stuff_rate_counts_a_no_gain_and_not_only_a_loss() -> None:
    plays = [_play(rush_attempt=1.0, yards_gained=0.0),
             _play(rush_attempt=1.0, yards_gained=4.0)]
    out = tm.team_week_metrics(pd.DataFrame(plays))
    assert _value(out, "stuff_rate", "offence") == pytest.approx(0.5)


def test_third_down_rate_ignores_every_other_down() -> None:
    plays = [_play(third_down_converted=1.0), _play(third_down_failed=1.0),
             _play(qb_dropback=1.0)]
    out = tm.team_week_metrics(pd.DataFrame(plays))
    assert _value(out, "third_down_rate", "offence") == pytest.approx(0.5)


def test_every_metric_emitted_is_described_in_the_catalogue() -> None:
    """A metric that reaches a report without a label is one nobody can read."""
    plays = [_play(qb_dropback=1.0, epa=0.3, pass_attempt=1.0, cpoe=2.0,
                   pass_oe=10.0, air_yards=8.0),
             _play(rush_attempt=1.0, epa=-0.1, yards_gained=3.0)]
    out = tm.team_week_metrics(pd.DataFrame(plays))
    described = {key for key, _l, _f in tm.CATALOGUE}
    assert set(out["metric"]) <= described
    for metric in sorted(set(out["metric"])):
        assert tm.label_for(metric) != metric or metric == tm.label_for(metric)
        assert tm.family_for(metric) != "other"


# -- Next Gen Stats ----------------------------------------------------------

def _ngs(rows) -> pd.DataFrame:
    return pd.DataFrame(
        [{"season": 2025, "season_type": "REG", "week": w, "team_abbr": t,
          "avg_separation": s, "targets": n} for w, t, s, n in rows]
    )


def test_a_club_separation_is_target_weighted_not_a_mean_of_means() -> None:
    """A receiver with four targets must not count as much as one with eleven."""
    frame = _ngs([(1, "AAA", 1.0, 2), (1, "AAA", 4.0, 18)])
    out = tm.ngs_team_metrics({"receiving": frame})
    row = out[out["metric"] == "separation"]
    assert float(row["value"].iloc[0]) == pytest.approx((1.0 * 2 + 4.0 * 18) / 20)
    assert float(row["weight"].iloc[0]) == 20.0


def test_the_week_zero_season_aggregate_never_enters_a_weekly_frame() -> None:
    """Week 0 in this feed is the season total. Kept, it counts every
    club-season twice and doubles the weight of whoever played most."""
    frame = _ngs([(0, "AAA", 9.9, 200), (1, "AAA", 3.0, 10)])
    out = tm.ngs_team_metrics({"receiving": frame})
    assert list(out["week"]) == [1]
    assert float(out["value"].iloc[0]) == pytest.approx(3.0)
