"""Pushes are exact, key numbers survive, and the fit never sees the future.

Football margins pile up on 3 and 7. A model that smooths that away reports a
spread edge that is really a statement about the smoothing, which is why the
shape comes from the data and only the mean is fitted.
"""

from __future__ import annotations

import pandas as pd
import pytest

from football_betting_lab.models.scoring import (
    OVERTIME_HOME_SHARE,
    OVERTIME_RESOLUTION_RATE,
    GameDistribution,
    distribution_for,
    empirical_pmf,
    fit_ratings,
    tilt_to_mean,
)


def _games(rows: list[tuple[str, str, str, int, int]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "game_date": day,
                "home_team": home,
                "away_team": away,
                "home_score": hs,
                "away_score": as_,
            }
            for day, home, away, hs, as_ in rows
        ]
    )


# -- tilting -----------------------------------------------------------------


def test_tilting_moves_the_mean_to_the_target() -> None:
    pmf = empirical_pmf([0, 3, 7, 10, 14, 17, 20, 24, 27, 31])

    tilted = tilt_to_mean(pmf, 20.0)
    mean = sum(x * p for x, p in tilted.items())

    assert mean == pytest.approx(20.0, abs=0.01)


def test_tilting_preserves_the_shape_that_makes_key_numbers_key() -> None:
    """Exponential tilting reweights by e^(theta*x), so the *ratio* between
    two adjacent scores changes smoothly and the lumps stay lumps. A smooth
    refit would flatten them, and flattening them is what misprices a 3."""
    pmf = {3: 0.4, 4: 0.1, 7: 0.4, 8: 0.1}

    tilted = tilt_to_mean(pmf, 6.0)

    assert tilted[3] > tilted[4]
    assert tilted[7] > tilted[8]


def test_a_tilted_distribution_is_still_a_distribution() -> None:
    pmf = empirical_pmf([0, 3, 7, 10, 14, 17, 20, 24])

    for target in (5.0, 12.0, 21.0):
        tilted = tilt_to_mean(pmf, target)
        assert sum(tilted.values()) == pytest.approx(1.0)
        assert all(p >= 0 for p in tilted.values())


def test_a_target_outside_the_support_collapses_rather_than_diverging() -> None:
    """Bisection cannot diverge, and the boundary answer is the honest one."""
    pmf = {10: 0.5, 20: 0.5}

    assert tilt_to_mean(pmf, 5.0) == {10: 1.0}
    assert tilt_to_mean(pmf, 99.0) == {20: 1.0}


def test_an_empty_distribution_stays_empty_rather_than_inventing_a_score() -> None:
    assert tilt_to_mean({}, 21.0) == {}


# -- pushes, computed exactly ------------------------------------------------


def _simple() -> GameDistribution:
    """Home scores 20 or 24, away scores 17 or 20, each equally likely."""
    return GameDistribution(home={20: 0.5, 24: 0.5}, away={17: 0.5, 20: 0.5})


def test_a_whole_number_spread_pushes_on_the_exact_margin() -> None:
    """Margins here are 0, 3, 4 and 7. A home line of -3 pushes on the 3."""
    win, push = _simple().spread(-3.0, side="home")

    assert push == pytest.approx(0.25)
    assert win == pytest.approx(0.5)


def test_a_half_point_removes_the_push_entirely() -> None:
    """The half-point across a key number is worth more than anywhere in
    hockey, and the model has to price it as worth something."""
    on_the_number, push_on = _simple().spread(-3.0, side="home")
    over_the_number, push_off = _simple().spread(-3.5, side="home")

    assert push_on > 0
    assert push_off == 0
    assert over_the_number == pytest.approx(on_the_number)


def test_a_whole_number_total_pushes_on_the_exact_sum() -> None:
    """Totals here are 37, 40, 41 and 44."""
    win, push = _simple().total(41.0, side="over")

    assert push == pytest.approx(0.25)


def test_over_and_under_and_push_account_for_all_the_mass() -> None:
    """The accounting identity, at the level of one market."""
    over, push = _simple().total(41.0, side="over")
    under, push_again = _simple().total(41.0, side="under")

    assert push == pytest.approx(push_again)
    assert over + under + push == pytest.approx(1.0)


def test_a_team_total_pushes_on_that_side_only() -> None:
    win, push = _simple().team_total(20.0, side="home_over")

    assert push == pytest.approx(0.5)
    assert win == pytest.approx(0.5)


def test_both_sides_of_a_team_total_and_its_push_sum_to_one() -> None:
    over, push = _simple().team_total(20.0, side="away_over")
    under, _ = _simple().team_total(20.0, side="away_under")

    assert over + under + push == pytest.approx(1.0)


# -- overtime ----------------------------------------------------------------


def test_the_raw_joint_overstates_the_tie_and_the_resolution_fixes_it() -> None:
    """3.54% raw against 0.28% observed. On a two-way moneyline a tie is a
    push, so the misallocated mass distorts both sides' win probabilities."""
    distribution = GameDistribution(home={20: 1.0}, away={20: 1.0})

    raw = distribution.moneyline(resolve_overtime=False)
    resolved = distribution.moneyline()

    assert raw["draw"] == pytest.approx(1.0)
    assert resolved["draw"] == pytest.approx(1 - OVERTIME_RESOLUTION_RATE)
    assert resolved["home"] == pytest.approx(
        OVERTIME_RESOLUTION_RATE * OVERTIME_HOME_SHARE
    )


def test_resolving_overtime_conserves_probability() -> None:
    distribution = GameDistribution(home={20: 0.5, 24: 0.5}, away={20: 0.5, 17: 0.5})

    assert sum(distribution.moneyline().values()) == pytest.approx(1.0)
    assert sum(
        distribution.moneyline(resolve_overtime=False).values()
    ) == pytest.approx(1.0)


def test_a_game_that_cannot_be_level_is_untouched_by_the_correction() -> None:
    distribution = GameDistribution(home={24: 1.0}, away={17: 1.0})

    assert distribution.moneyline() == distribution.moneyline(resolve_overtime=False)


# -- the fit -----------------------------------------------------------------


def test_the_fit_never_sees_the_game_it_is_pricing_or_any_later_one() -> None:
    """Walk-forward is not a nicety in a sixteen-game week: using the rest of
    the week leaks the result of a game into the price of one kicking off at
    the same time."""
    games = _games(
        [
            ("2025-09-07", "KC", "DEN", 30, 10),
            ("2025-09-14", "KC", "LV", 35, 7),
            ("2025-09-21", "KC", "LAC", 3, 40),
        ]
    )

    early = fit_ratings(games, before="2025-09-14")
    late = fit_ratings(games, before="2025-09-22")

    assert early.games_used == 1
    assert late.games_used == 3
    assert early.offence["KC"] != late.offence["KC"]


def test_a_fit_with_no_history_returns_a_league_average_rather_than_failing() -> None:
    ratings = fit_ratings(_games([]), before="2025-09-07")

    assert ratings.games_used == 0
    assert ratings.expected_points("KC", "DEN", at_home=True) > 0


def test_an_unknown_club_prices_as_league_average_rather_than_raising() -> None:
    """A club with no history is a real state in week one, not an error."""
    ratings = fit_ratings(
        _games([("2025-09-07", "KC", "DEN", 30, 10)]), before="2025-09-14"
    )

    assert ratings.expected_points("NEWCLUB", "OTHER", at_home=True) > 0


def test_expected_points_are_never_negative() -> None:
    """A tilt to a negative mean is not a distribution over scores."""
    ratings = fit_ratings(
        _games([("2025-09-07", "KC", "DEN", 70, 0)] * 5), before="2025-09-14"
    )

    assert ratings.expected_points("DEN", "KC", at_home=False) >= 3.0


def test_home_advantage_is_measured_rather_than_assumed() -> None:
    games = _games([("2025-09-07", "KC", "DEN", 30, 20)] * 10)

    assert fit_ratings(games, before="2025-09-14").home_advantage == pytest.approx(10.0)


def test_the_two_sides_price_differently_when_the_ratings_differ() -> None:
    games = _games(
        [("2025-09-07", "KC", "DEN", 35, 10)] * 8
        + [("2025-09-08", "DEN", "KC", 10, 35)] * 8
    )
    ratings = fit_ratings(games, before="2025-09-14")
    pmf = empirical_pmf([0, 3, 7, 10, 14, 17, 20, 24, 27, 31, 35])

    distribution = distribution_for(ratings, pmf, home_team="KC", away_team="DEN")
    moneyline = distribution.moneyline()

    assert moneyline["home"] > moneyline["away"]


# -- the first half ----------------------------------------------------------


def test_a_half_does_not_resolve_ties_because_there_is_no_overtime() -> None:
    """Measured over 1,087 games: 7.4% of first halves end level against
    0.35% of full games. Hardcoding the full-game rule priced a level half at
    0.4%, which is wrong by a factor of twenty."""
    level = {20: 1.0}
    full = GameDistribution(home=level, away=level, resolves_ties=True)
    half = GameDistribution(home=level, away=level, resolves_ties=False)

    assert full.moneyline()["draw"] == pytest.approx(1 - OVERTIME_RESOLUTION_RATE)
    assert half.moneyline()["draw"] == pytest.approx(1.0)


def test_a_half_still_conserves_probability() -> None:
    half = GameDistribution(
        home={10: 0.5, 14: 0.5}, away={10: 0.5, 7: 0.5}, resolves_ties=False
    )

    assert sum(half.moneyline().values()) == pytest.approx(1.0)


def test_a_full_game_resolves_ties_by_default() -> None:
    """The default must be the full-game rule: a segment is the special case,
    and a distribution built without thinking about it should be a game."""
    assert GameDistribution(home={20: 1.0}, away={20: 1.0}).resolves_ties


def test_the_half_model_scales_the_full_game_expectation() -> None:
    from football_betting_lab.models.scoring import HalfModel

    model = HalfModel(
        pmf=empirical_pmf([0, 3, 7, 10, 14, 17, 21]),
        share=0.5,
        home_advantage_share=1.5,
    )
    ratings = fit_ratings(
        _games([("2025-09-07", "KC", "DEN", 30, 10)] * 6), before="2025-09-14"
    )

    distribution = model.distribution(ratings, home_team="KC", away_team="DEN")
    home_mean = sum(x * p for x, p in distribution.home.items())
    full_mean = ratings.expected_points("KC", "DEN", at_home=True)

    assert home_mean == pytest.approx(full_mean * 0.5, rel=0.05)


def test_the_half_model_declines_to_fit_on_nothing() -> None:
    from football_betting_lab.models.scoring import fit_half_model

    assert fit_half_model(pd.DataFrame(), pd.DataFrame()) is None
