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


def _informative_market(per_bucket: int, model_is_blind: bool) -> pd.DataFrame:
    """Games whose true probability varies, with a market that tracks it.

    A coin is the wrong fixture here. On a fair coin a perfectly calibrated
    0.5 scores 0.25000 while a -110 price scores 0.25057, so ANY calibrated
    model "beats" the price purely because the price carries vig. The market
    has to be genuinely informative before beating it means anything.

    So each bucket has a true rate, and exactly that fraction of its games are
    won — the realised rate equals the truth by construction rather than by
    luck. The market quotes the truth plus two points of vig. The model either
    quotes the truth ("sharp") or a constant ("blind").
    """
    rows = []
    for season in (2023, 2024):
        for bucket in range(10):
            truth = 0.30 + 0.40 * (bucket / 9.0)
            wins = round(truth * per_bucket)
            implied = min(truth + 0.02, 0.97)
            odds = (
                -round(100 * implied / (1 - implied))
                if implied >= 0.5
                else round(100 * (1 - implied) / implied)
            )
            for i in range(per_bucket):
                rows.append({
                    "season": season,
                    "market": "blind" if model_is_blind else "sharp",
                    "odds": odds,
                    "model_probability": 0.50 if model_is_blind else truth,
                    "outcome": "won" if i < wins else "lost",
                })
    return pd.DataFrame(rows)


def test_a_model_that_never_beats_the_price_is_told_so_in_those_words() -> None:
    """The market tracks the truth; the model does not. Calibration cannot
    recover information the model never had."""
    bets = _informative_market(90, model_is_blind=True)

    result = measure(bets)
    text = render(result, bets)

    assert not result.ever_beats_the_price
    assert "never a better forecaster than the price" in text
    assert "no subgroup of it that can be profitable" in text


def test_per_market_skill_can_find_a_good_family_inside_a_bad_average() -> None:
    """Pooled Brier answers "does this model know anything", not "does it know
    anything HERE". A model with no skill on average can carry skill in one
    family and noise everywhere else, and pooling hides that both ways."""
    bets = pd.concat(
        [_informative_market(90, model_is_blind=False),
         _informative_market(90, model_is_blind=True)],
        ignore_index=True,
    )

    result = measure(bets)

    by_name = {m.market: m for m in result.markets}
    assert set(by_name) == {"sharp", "blind"}
    assert by_name["sharp"].calibrated_brier < by_name["blind"].calibrated_brier
    assert by_name["sharp"].beats_the_price
    assert not by_name["blind"].beats_the_price


def test_a_market_below_the_minimum_is_not_reported_at_all() -> None:
    """Below the floor the difference between two Brier scores is dominated by
    which games happened to land in the sample."""
    bets = _informative_market(12, model_is_blind=True)

    assert [m.market for m in measure(bets).markets] == []


def test_no_market_beating_the_price_is_said_in_those_words() -> None:
    bets = _informative_market(90, model_is_blind=True)

    text = render(measure(bets), bets)

    assert "No market forecasts better than the price" in text
    assert "not hiding a good family inside a bad average" in text


def test_a_constant_model_calibrates_to_the_pooled_rate_not_to_noise() -> None:
    """An isotonic fit on a model that says the same number every time has no
    increasing x to interpolate along, and `np.interp` is degenerate there.
    A count market fitted to a near-constant rate is exactly that shape."""
    xs, fitted = isotonic_fit(np.full(200, 0.6), np.array([1.0, 0.0] * 100))

    got = apply_map(xs, fitted, pd.Series([0.6, 0.1, 0.9]))

    assert np.allclose(got, 0.5)


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


