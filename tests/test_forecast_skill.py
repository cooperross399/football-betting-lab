"""The question underneath every return: is the model better than the price?

This instrument exists because three headline findings in this repository were
artefacts, and every one of them was chased as a *return* before anyone asked
whether the model knew anything. A Brier comparison needs no settlement rule,
no vig assumption and no edge threshold, so it is the cheapest question to ask
and the hardest to fool.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from football_betting_lab.reports.forecast_skill import (
    apply_map,
    brier,
    implied,
    isotonic_fit,
    measure,
    render,
)


def _bets(rows: list[dict]) -> pd.DataFrame:
    base = {
        "season": 2023,
        "market": "rush_yards",
        "outcome": "won",
        "odds": -110,
        "model_probability": 0.6,
    }
    return pd.DataFrame([{**base, **row} for row in rows])


def test_implied_reads_both_sides_of_the_american_convention() -> None:
    got = implied(pd.Series([-110, 100, 150, -200]))

    assert got[0] == 110 / 210
    assert got[1] == 0.5
    assert got[2] == 100 / 250
    assert got[3] == 200 / 300


def test_the_market_is_scored_with_the_vig_still_in_it() -> None:
    """Deliberate, and it handicaps the market rather than the model.

    Both sides of an even wager imply 0.524, summing to 1.048. Leaving that in
    makes the market's probabilities worse than its true opinion, so a model
    that still loses the comparison has lost it twice.
    """
    assert implied(pd.Series([-110]))[0] > 0.5


def test_isotonic_is_monotone_and_pools_violations() -> None:
    xs, fitted = isotonic_fit(
        np.array([0.1, 0.2, 0.3, 0.4]), np.array([0.0, 1.0, 0.0, 1.0])
    )

    assert list(xs) == [0.1, 0.2, 0.3, 0.4]
    assert all(a <= b + 1e-9 for a, b in zip(fitted, fitted[1:]))


def test_a_calibration_map_never_returns_a_certainty() -> None:
    """A forecast of 0 or 1 is infinitely punished by any proper score, and a
    step fit will happily produce one from a bucket that went 0 for 8."""
    xs, fitted = isotonic_fit(np.array([0.1, 0.9]), np.array([0.0, 1.0]))

    got = apply_map(xs, fitted, pd.Series([0.0, 0.5, 1.0]))

    assert got.min() >= 0.01
    assert got.max() <= 0.99


def test_brier_rewards_the_forecaster_who_is_closer() -> None:
    won = np.array([1.0, 1.0, 0.0, 0.0])

    assert brier(np.array([0.9, 0.9, 0.1, 0.1]), won) < brier(
        np.array([0.6, 0.6, 0.4, 0.4]), won
    )


def test_calibration_is_fitted_on_prior_seasons_only() -> None:
    """A map fitted on the season it scores is a description, not a forecast,
    and it would report skill the model does not have."""
    rows = [{"season": s, "outcome": "won" if i % 2 else "lost"}
            for s in (2023, 2024) for i in range(50)]

    result = measure(_bets(rows))

    # 2023 has no prior season to fit on, so it is not scored at all.
    assert [s.season for s in result.seasons] == [2024]


def test_a_model_that_never_beats_the_price_is_told_so_in_those_words() -> None:
    # Model says 0.6 on every bet; outcomes land at 0.5. The price says 0.524,
    # which is closer, so the market wins every season.
    rows = [{"season": s, "outcome": "won" if i % 2 else "lost"}
            for s in (2023, 2024) for i in range(200)]
    bets = _bets(rows)

    result = measure(bets)
    text = render(result, bets)

    assert not result.ever_beats_the_price
    assert "never a better forecaster than the price" in text
    assert "no subgroup of it that can be profitable" in text


def test_no_scoreable_season_is_an_absence_not_a_result() -> None:
    """One season of bets cannot be calibrated walk-forward at all, and an
    empty table must not read as the model having failed the test."""
    bets = _bets([{"season": 2023} for _ in range(20)])

    text = render(measure(bets), bets)

    assert "absence, not a result" in text
    assert "never a better forecaster" not in text


def test_the_excluded_markets_come_from_the_screen_not_a_constant(tmp_path):
    """A hardcoded exclusion cannot notice that it stopped being true.

    `tackles_assists` was a module constant here. It was flagged because our
    tackle column dropped `def_tackles_with_assist` and undercounted by 7%;
    once that was fixed the screen cleared it, and the constant would have gone
    on excluding a market with nothing wrong with it.
    """
    from football_betting_lab.reports.forecast_skill import settlement_suspects

    report = tmp_path / "screen.md"
    report.write_text(
        "| Market | Gap |\n"
        "|:---|---:|\n"
        "| `tackles_assists` | -1% | agrees with the price |\n"
        "| `sacks` | -9% | **settlement suspect** — outcomes land below |\n",
        encoding="utf-8",
    )

    assert settlement_suspects(report) == {"sacks"}


def test_a_missing_screen_is_an_error_not_an_empty_exclusion(tmp_path):
    """"Nothing is excluded" and "nothing was screened" must not look alike."""
    from football_betting_lab.reports.forecast_skill import settlement_suspects

    with pytest.raises(FileNotFoundError, match="settlement"):
        settlement_suspects(tmp_path / "absent.md")
