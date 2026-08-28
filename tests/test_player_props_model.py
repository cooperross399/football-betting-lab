"""One simulation, every market, consistent by construction.

A receiver's receptions, receiving yards, longest reception and touchdowns are
one afternoon seen four ways. Fitted separately, a model will happily price 8
receptions, 40 yards and a 55-yard long — a set of numbers that cannot all
happen. These tests are what stops that.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from football_betting_lab.models.player_props import (
    PlayerRates,
    fit_rates,
    simulate,
)


#: A right-skewed, zero-inflated per-play distribution, like the real one.
PER_PLAY = {-5: 0.05, 0: 0.10, 3: 0.25, 7: 0.25, 12: 0.20, 25: 0.10, 60: 0.05}


def _rates(**overrides) -> PlayerRates:
    values = {
        "player_id": "p1",
        "name": "A Player",
        "games": 20,
        "opportunities_mean": 6.0,
        "opportunities_variance": 6.0,
        "yards_per_opportunity": 10.0,
        "touchdown_rate": 0.08,
    }
    values.update(overrides)
    return PlayerRates(**values)


def _logs(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


# -- one simulation, many markets --------------------------------------------

def test_the_same_seed_gives_the_same_prices() -> None:
    """A card built twice from one fit must price identically. A model whose
    opinion moves when nothing else did cannot be argued with, and the ledger
    would be recording the sampler rather than the model."""
    first = simulate(_rates(), PER_PLAY, draws=2000, seed=3)
    second = simulate(_rates(), PER_PLAY, draws=2000, seed=3)

    assert np.array_equal(first.yards, second.yards)
    assert np.array_equal(first.longest, second.longest)


def test_a_game_with_no_opportunities_has_no_yards_and_no_longest() -> None:
    """The consistency four separate models cannot guarantee."""
    simulation = simulate(_rates(), PER_PLAY, draws=5000, seed=1)
    idle = simulation.opportunities == 0

    if idle.any():
        assert (simulation.yards[idle] == 0).all()
        assert (simulation.longest[idle] == 0).all()


def test_the_longest_play_never_exceeds_the_largest_possible_one() -> None:
    simulation = simulate(_rates(), PER_PLAY, draws=5000, seed=1)

    assert simulation.longest.max() <= max(PER_PLAY)


def test_the_mean_yards_follow_the_players_own_efficiency() -> None:
    """Volume times efficiency, which is what a compound outcome is."""
    rates = _rates(opportunities_mean=8.0, yards_per_opportunity=12.0)

    simulation = simulate(rates, PER_PLAY, draws=40000, seed=2)

    assert simulation.yards.mean() == pytest.approx(96.0, rel=0.06)


def test_a_more_efficient_player_is_priced_higher_at_every_rung() -> None:
    """The tilt moves the whole distribution, not just its centre."""
    modest = simulate(_rates(yards_per_opportunity=7.0), PER_PLAY, draws=20000, seed=4)
    elite = simulate(_rates(yards_per_opportunity=14.0), PER_PLAY, draws=20000, seed=4)

    for line in (40.5, 70.5, 100.5):
        assert elite.probability_over("yards", line) > modest.probability_over(
            "yards", line
        )


def test_every_alternate_rung_comes_from_one_distribution_and_is_monotone() -> None:
    """The ladder and the featured line can never disagree, because they are
    the same simulation read at different points."""
    simulation = simulate(_rates(), PER_PLAY, draws=20000, seed=5)

    rungs = [simulation.probability_over("yards", line) for line in range(10, 140, 10)]

    assert rungs == sorted(rungs, reverse=True)


# -- the accounting identity, at one market ----------------------------------

def test_over_under_and_push_account_for_all_the_mass() -> None:
    simulation = simulate(_rates(), PER_PLAY, draws=20000, seed=6)

    over = simulation.probability_over("opportunities", 6.0)
    under = simulation.probability_under("opportunities", 6.0)
    push = simulation.probability_push("opportunities", 6.0)

    assert over + under + push == pytest.approx(1.0)


def test_a_whole_number_line_has_push_mass_and_a_half_point_line_has_none() -> None:
    simulation = simulate(_rates(), PER_PLAY, draws=20000, seed=6)

    assert simulation.probability_push("opportunities", 6.0) > 0
    assert simulation.probability_push("opportunities", 6.5) == 0


# -- the count model ---------------------------------------------------------

def test_overdispersed_volume_is_drawn_from_a_negative_binomial() -> None:
    """A running back's carries swing with the game script, so Poisson
    understates both tails."""
    rates = _rates(opportunities_mean=6.0, opportunities_variance=18.0)

    simulation = simulate(rates, PER_PLAY, draws=40000, seed=7)

    assert simulation.opportunities.var() > simulation.opportunities.mean() * 1.5


def test_variance_at_or_below_the_mean_falls_back_to_poisson() -> None:
    """A variance below the mean is noise at these sample sizes, not evidence
    of underdispersion, and forcing a negative binomial onto it produces
    nonsense parameters."""
    rates = _rates(opportunities_mean=6.0, opportunities_variance=3.0)

    simulation = simulate(rates, PER_PLAY, draws=40000, seed=8)

    assert simulation.opportunities.var() == pytest.approx(6.0, rel=0.15)


def test_touchdowns_can_never_exceed_opportunities() -> None:
    simulation = simulate(_rates(touchdown_rate=0.9), PER_PLAY, draws=5000, seed=9)

    assert (simulation.touchdowns <= simulation.opportunities).all()


# -- the fit -----------------------------------------------------------------

def _history(player: str, weeks: list[tuple[int, int, int, int, int]]) -> pd.DataFrame:
    return _logs(
        [
            {
                "player_id": player,
                "player_name": player,
                "season": season,
                "week": week,
                "receptions": receptions,
                "reception_yards": yards,
                "reception_tds": tds,
            }
            for season, week, receptions, yards, tds in weeks
        ]
    )


def test_the_fit_never_sees_the_week_it_is_pricing_or_any_later_one() -> None:
    logs = _history("p1", [(2025, 1, 4, 40, 0), (2025, 2, 10, 150, 2)])

    early = fit_rates(
        logs,
        before="202502",
        opportunity_column="receptions",
        yards_column="reception_yards",
        touchdown_column="reception_tds",
    )
    late = fit_rates(
        logs,
        before="202503",
        opportunity_column="receptions",
        yards_column="reception_yards",
        touchdown_column="reception_tds",
    )

    assert early["p1"].games == 1
    assert late["p1"].games == 2
    assert late["p1"].opportunities_mean > early["p1"].opportunities_mean


def test_a_player_with_no_history_is_not_usable_rather_than_league_average() -> None:
    """Inventing a rate produces a confident price for someone the model has
    never seen play, and the row looks exactly like a correct one."""
    logs = _history("p1", [(2025, 1, 4, 40, 0)])

    rates = fit_rates(
        logs,
        before="202501",
        opportunity_column="receptions",
        yards_column="reception_yards",
        touchdown_column="reception_tds",
    )

    assert "p1" not in rates


def test_games_with_no_opportunities_do_not_drag_the_rate_to_zero() -> None:
    """A receiver who did not play is not a receiver who caught nothing."""
    logs = _history("p1", [(2025, 1, 6, 70, 1), (2025, 2, 0, 0, 0)])

    rates = fit_rates(
        logs,
        before="202503",
        opportunity_column="receptions",
        yards_column="reception_yards",
        touchdown_column="reception_tds",
    )

    assert rates["p1"].games == 1
    assert rates["p1"].opportunities_mean == pytest.approx(6.0)


def test_a_thin_record_is_shrunk_toward_the_league_rate() -> None:
    """One 200-yard game does not make a 33-yards-per-catch receiver."""
    logs = _history("star", [(2025, 1, 6, 200, 3)]) 
    logs = pd.concat(
        [logs, _history("rest", [(2025, w, 6, 60, 0) for w in range(1, 15)])]
    )

    rates = fit_rates(
        logs,
        before="202516",
        opportunity_column="receptions",
        yards_column="reception_yards",
        touchdown_column="reception_tds",
    )

    assert rates["star"].yards_per_opportunity < 33.3
    assert rates["star"].yards_per_opportunity > 10.0
