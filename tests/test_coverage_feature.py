"""The man-coverage feature, and the three ways it could be quietly wrong.

Each test here exists because the corresponding mistake was actually made or
actually available while this was built, not because it rounds out a matrix.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from football_betting_lab.reports import coverage_feature as cov
from football_betting_lab.reports import encompassing


def participation(rows) -> pd.DataFrame:
    return pd.DataFrame(
        rows, columns=["nflverse_game_id", "possession_team", "defense_man_zone_type"]
    )


def test_the_defence_is_the_side_of_the_game_id_not_in_possession() -> None:
    frame = participation([
        ("2024_01_KC_BAL", "KC", cov.MAN),   # KC has the ball, BAL defends
        ("2024_01_KC_BAL", "BAL", cov.ZONE),  # and the other way round
    ])
    assert list(cov.defence_of_each_play(frame)) == ["BAL", "KC"]


def test_the_denominator_is_charted_dropbacks_and_not_plays() -> None:
    """Coverage is charted on dropbacks only — 22,055 of 45,184 rows in 2025.
    Dividing by plays would halve every rate while looking entirely sensible."""
    rows = [("2024_01_KC_BAL", "KC", cov.MAN)] * 150
    rows += [("2024_01_KC_BAL", "KC", cov.ZONE)] * 150
    rows += [("2024_01_KC_BAL", "KC", "")] * 400          # runs, never charted
    rates = cov.man_rate_by_defence(participation(rows))
    row = rates[rates["defence"] == "BAL"].iloc[0]
    assert row["charted_dropbacks"] == 300
    assert row["man_rate"] == pytest.approx(0.5)


def test_a_thin_defence_season_is_refused_rather_than_averaged_in() -> None:
    rows = [("2024_01_KC_BAL", "KC", cov.MAN)] * (cov.MIN_CHARTED_DROPBACKS - 1)
    assert cov.man_rate_by_defence(participation(rows)).empty


def test_the_rate_is_standardised_within_season_not_across() -> None:
    """League-mean man rate measured 2026-09-07: 2022 0.286, 2023 0.423, 2024
    0.492, 2025 0.318 — swings of +13.7, +6.9 and -17.4 points. Thirty-two
    defences do not abandon seventeen points of man coverage in an offseason,
    so the raw rate is two different rulers and only the within-season score
    is comparable. A globally centred raw rate would make this regressor
    partly an indicator of which season the wager came from."""
    rows = []
    # A season charted low, and a season charted high, with the SAME ordering.
    for defence, low, high in (("AAA", 0.20, 0.50), ("BBB", 0.30, 0.60)):
        for season, rate in ((2023, low), (2024, high)):
            n = 400
            man = int(round(rate * n))
            gid = f"{season}_01_OFF_{defence}"
            rows += [(gid, "OFF", cov.MAN)] * man
            rows += [(gid, "OFF", cov.ZONE)] * (n - man)
    rates = cov.man_rate_by_defence(participation(rows))
    # Raw rates differ wildly between the seasons...
    assert rates.groupby("season")["man_rate"].mean().diff().abs().max() > 0.25
    # ...while the z-score puts the two defences in the same places both times.
    wide = rates.pivot(index="defence", columns="season", values="man_rate_z")
    assert wide[2023].round(6).tolist() == wide[2024].round(6).tolist()
    for season, group in rates.groupby("season"):
        assert group["man_rate_z"].mean() == pytest.approx(0.0, abs=1e-9)


def test_a_same_season_rate_is_refused() -> None:
    """A rate computed partly from the game being predicted would make `d` a
    measurement of the leak rather than of coverage."""
    frame = pd.DataFrame({"season": [2024], "opponent": ["BAL"]})
    rates = pd.DataFrame(
        {"season": [2024], "defence": ["BAL"], "man_rate": [0.4], "man_rate_z": [0.5]}
    )
    attached = cov.attach_prior_season_man_rate(frame, rates)
    # It asked for 2023 and 2024 was all that existed, so nothing was attached.
    assert attached["rate_season"].tolist() == [2023]
    assert attached["man_rate"].isna().all()


def test_the_opponent_join_never_duplicates_a_wager() -> None:
    """A duplicated wager makes every interval too narrow, which is the defect
    shape this repository keeps finding."""
    bets = pd.DataFrame({
        "player_id": ["00-0001"], "season": [2024], "week": [1], "wager": ["x"],
    })
    rosters = pd.DataFrame({
        # The same player listed twice in one week, as rosters really do.
        "gsis_id": ["00-0001", "00-0001"], "season": [2024, 2024],
        "week": [1, 1], "team": ["KC", "KC"],
    })
    schedule = pd.DataFrame({
        "season": [2024], "week": [1], "away_team": ["KC"],
        "home_team": ["BAL"], "game_type": ["REG"],
    })
    out = cov.opponent_of_each_wager(bets, rosters, schedule)
    assert len(out) == 1
    assert out["opponent"].tolist() == ["BAL"]


def test_a_duplicating_join_raises_rather_than_returning_a_wider_frame() -> None:
    bets = pd.DataFrame({
        "player_id": ["00-0001"], "season": [2024], "week": [1], "wager": ["x"],
    })
    rosters = pd.DataFrame({
        "gsis_id": ["00-0001"], "season": [2024], "week": [1], "team": ["KC"],
    })
    # One club listed as playing two games in the same week.
    schedule = pd.DataFrame({
        "season": [2024, 2024], "week": [1, 1], "away_team": ["KC", "KC"],
        "home_team": ["BAL", "DEN"], "game_type": ["REG", "REG"],
    })
    with pytest.raises(ValueError, match="row count"):
        cov.opponent_of_each_wager(bets, rosters, schedule)


# --- the fit machinery this report leans on ---------------------------------

def synthetic(n: int = 1200, clusters: int = 40, seed: int = 3) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    cluster = rng.integers(0, clusters, n)
    return pd.DataFrame({
        "y": rng.integers(0, 2, n).astype(float),
        "p_market": rng.uniform(0.3, 0.7, n),
        "p_model": rng.uniform(0.3, 0.7, n),
        "side_over": rng.integers(0, 2, n).astype(float),
        "event_id": rng.integers(0, 300, n),
        "defence_season": cluster,
        "man_centred": rng.normal(0, 1, clusters)[cluster],
    })


def test_an_extra_regressor_is_named_and_estimated() -> None:
    fit = encompassing.fit(
        synthetic(), "x", extra=(("d  man", "man_centred"),), cluster="defence_season"
    )
    assert fit is not None
    assert [c.name for c in fit.coefficients][-1] == "d  man"


def test_clustering_coarsely_never_narrows_an_interval() -> None:
    """The reason the report clusters by defence-season. `man_centred` takes one
    value per cluster, so a game-level cluster would treat about ninety
    independent quantities as tens of thousands — the sqrt(n) error already
    shipped twice here."""
    frame = synthetic()
    extra = (("d  man", "man_centred"),)
    coarse = encompassing.fit(frame, "coarse", extra=extra, cluster="defence_season")
    fine = encompassing.fit(frame, "fine", extra=extra, cluster="event_id")
    assert coarse is not None and fine is not None
    d_coarse = next(c for c in coarse.coefficients if c.name == "d  man")
    d_fine = next(c for c in fine.coefficients if c.name == "d  man")
    assert d_coarse.se > d_fine.se


def test_the_default_fit_is_untouched_by_the_new_arguments() -> None:
    """`extra=()` and `cluster="event_id"` must reproduce the published report."""
    frame = synthetic()
    assert [c.name for c in encompassing.fit(frame, "x").coefficients] == list(
        encompassing.NAMES
    )


# --- the receiver's own man/zone split --------------------------------------

def plays(rows) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(participation, pbp) for a list of (game, play, man?, receiver, yards)."""
    part = pd.DataFrame(
        [(g, p, cov.MAN if man else cov.ZONE) for g, p, man, _, _ in rows],
        columns=["nflverse_game_id", "play_id", "defense_man_zone_type"],
    )
    pbp = pd.DataFrame(
        [(g, p, 1, r, y, 2024, 1) for g, p, _, r, y in rows],
        columns=["game_id", "play_id", "pass_attempt", "receiver_player_id",
                 "receiving_yards", "season", "week"],
    )
    return part, pbp


def test_the_target_join_does_not_collide_on_season() -> None:
    """Both frames carrying `season` makes pandas silently rename each to
    season_x / season_y, and every later groupby on `season` then raises —
    which is what happened the first time this was run."""
    part, pbp = plays([("2024_01_KC_BAL", 1, True, "00-0001", 12.0)])
    out = cov.targets_by_coverage(part, pbp)
    assert "season" in out.columns
    assert "season_x" not in out.columns and "season_y" not in out.columns


def test_only_targets_against_a_charted_coverage_survive() -> None:
    part, pbp = plays([
        ("2024_01_KC_BAL", 1, True, "00-0001", 10.0),
        ("2024_01_KC_BAL", 2, False, "00-0001", 4.0),
    ])
    part.loc[1, "defense_man_zone_type"] = ""      # a run, never charted
    assert len(cov.targets_by_coverage(part, pbp)) == 1


def test_the_differential_is_yards_per_target_man_minus_zone() -> None:
    rows = [("2024_01_KC_BAL", i, True, "00-0001", 10.0) for i in range(30)]
    rows += [("2024_01_KC_BAL", 100 + i, False, "00-0001", 4.0) for i in range(30)]
    targets = cov.targets_by_coverage(*plays(rows))
    out = cov._differential(targets, ["season", "receiver_player_id"], 25)
    assert out["differential"].iloc[0] == pytest.approx(6.0)


def test_a_player_short_of_targets_against_either_coverage_is_dropped() -> None:
    rows = [("2024_01_KC_BAL", i, True, "00-0001", 10.0) for i in range(30)]
    rows += [("2024_01_KC_BAL", 100 + i, False, "00-0001", 4.0) for i in range(5)]
    targets = cov.targets_by_coverage(*plays(rows))
    assert cov._differential(targets, ["season", "receiver_player_id"], 25).empty


def test_the_differential_is_shrunk_by_its_measured_reliability(monkeypatch) -> None:
    """Reliability measured 2026-09-07 is about 0.15-0.20, so four fifths of a
    man-versus-zone differential is noise. Using it unshrunk would hand the
    feature a number that is mostly a random draw wearing a player's name."""
    monkeypatch.setattr(cov, "split_half_reliability", lambda *a, **k: 0.20)
    rows = []
    for player, man_yards in (("00-0001", 12.0), ("00-0002", 2.0)):
        rows += [("2024_01_KC_BAL", hash((player, i)) % 10**6, True, player, man_yards)
                 for i in range(30)]
        rows += [("2024_01_KC_BAL", hash((player, i, "z")) % 10**6, False, player, 7.0)
                 for i in range(30)]
    out = cov.player_coverage_differential(cov.targets_by_coverage(*plays(rows)))
    # Raw differentials are +5 and -5; centred they stay +5 and -5; shrunk, +-1.
    assert sorted(out["differential"].round(3)) == [-5.0, 5.0]
    assert sorted(out["differential_shrunk"].round(3)) == [-1.0, 1.0]


def test_spearman_brown_lifts_the_half_season_correlation() -> None:
    """A half-season correlation understates a full season's reliability, and
    reporting the half as though it were the whole would overstate the noise."""
    rng = np.random.default_rng(5)
    n = 200
    truth = rng.normal(0, 1, n)
    odd = truth + rng.normal(0, 1, n)
    even = truth + rng.normal(0, 1, n)
    frame = pd.DataFrame({
        "season": 2024, "receiver_player_id": np.repeat(np.arange(n), 2),
        "half": np.tile(["odd", "even"], n),
        "differential": np.column_stack([odd, even]).ravel(),
    })
    wide = frame.pivot_table(index="receiver_player_id", columns="half", values="differential")
    half = wide["odd"].corr(wide["even"])
    assert 2 * half / (1 + half) > half


def test_reliability_refuses_a_sample_too_small_to_measure_it() -> None:
    part, pbp = plays([("2024_01_KC_BAL", 1, True, "00-0001", 10.0)])
    with pytest.raises(ValueError, match="Too few"):
        cov.split_half_reliability(cov.targets_by_coverage(part, pbp))
