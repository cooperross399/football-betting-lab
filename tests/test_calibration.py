"""The calibration maps the card freezes beside every raw probability.

This is a forecasting improvement, not an edge — calibration closed most of the
model's Brier gap and never crossed the market's. It is built before Week 1 for
a different reason: **a calibrated probability cannot be back-dated.** The
ledger records what was believed before kickoff, so a season frozen without one
can never be scored on it, and the bought population is complete.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from football_betting_lab.models.calibration import (
    CEILING,
    FLOOR,
    MINIMUM_ROWS,
    Calibration,
    MarketCalibration,
    fit,
    load,
    save,
)


def _bets(market: str, n: int, season: int = 2024, says: float = 0.8,
          truth: float = 0.5) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "season": season,
                "market": market,
                "model_probability": says,
                "outcome": "won" if i < round(truth * n) else "lost",
            }
            for i in range(n)
        ]
    )


def test_a_map_pulls_an_overconfident_model_toward_what_happened() -> None:
    """The model says 0.8 and the outcome lands 0.5. That is the whole defect
    this corrects: measured, it says 0.861 and gets 0.547."""
    calibration = fit(_bets("rush_yards", 800))

    assert calibration.apply("rush_yards", 0.8) == pytest.approx(0.5, abs=0.02)


def test_a_market_with_no_map_returns_none_not_the_raw_probability() -> None:
    """None, never a silent fallback.

    A market with no map and a market that calibrates to itself must not look
    the same in the ledger: one is a measurement and the other is an absence,
    and a year later nobody remembers which markets had maps.
    """
    calibration = fit(_bets("rush_yards", 800))

    assert calibration.apply("sacks", 0.8) is None


def test_a_thin_market_gets_no_map_at_all() -> None:
    """Below the floor the fit is a step function through noise, and it would
    flatter the model by memorising its earlier mistakes."""
    calibration = fit(_bets("thin", MINIMUM_ROWS - 1))

    assert "thin" not in calibration.markets


def test_the_map_is_fitted_only_on_earlier_seasons() -> None:
    """The same walk-forward rule the rest of the lab keeps. A map fitted on the
    season it scores is not a forecast, it is a description."""
    frame = pd.concat(
        [_bets("rush_yards", 400, season=2024), _bets("rush_yards", 400, season=2026)],
        ignore_index=True,
    )

    calibration = fit(frame, before_season=2026)

    assert calibration.markets["rush_yards"].seasons == (2024,)
    assert calibration.markets["rush_yards"].rows == 400


def test_no_map_ever_returns_a_certainty() -> None:
    """A forecast of 0 or 1 is infinitely punished by any proper score, and a
    step fit will produce one from a bucket that went nought for eight."""
    calibration = fit(_bets("rush_yards", 800, says=0.9, truth=0.0))

    got = calibration.apply("rush_yards", 0.9)

    assert FLOOR <= got <= CEILING


def test_a_constant_model_calibrates_to_the_pooled_rate() -> None:
    """A model that says the same number every time gives the fit no increasing
    x to interpolate along. A count market fitted to a near-constant rate is
    exactly that shape."""
    entry = MarketCalibration(
        market="sacks", rows=500, seasons=(2024,),
        x=(0.6, 0.6, 0.6), y=(0.2, 0.4, 0.6),
    )

    assert entry.apply(0.9) == pytest.approx(0.4)


def test_a_map_survives_the_round_trip_to_disk(tmp_path) -> None:
    """The card loads this artifact rather than refitting, so what is written
    has to be what is read."""
    original = fit(_bets("rush_yards", 800))
    path = save(original, tmp_path / "calibration.json")

    restored = load(path)

    assert restored is not None
    assert restored.fitted_on == original.fitted_on
    assert restored.apply("rush_yards", 0.8) == pytest.approx(
        original.apply("rush_yards", 0.8)
    )


def test_a_missing_artifact_loads_as_none_not_as_an_empty_calibration(tmp_path) -> None:
    """"No artifact on disk" and "every market calibrates to itself" are
    different facts and must not share a representation."""
    assert load(tmp_path / "absent.json") is None


def test_an_empty_fit_offers_no_maps_rather_than_identity() -> None:
    calibration = fit(pd.DataFrame(columns=["season", "market", "model_probability", "outcome"]))

    assert calibration.markets == {}
    assert calibration.apply("rush_yards", 0.8) is None


def test_void_rows_never_reach_the_fit() -> None:
    """A voided prop had no outcome. Scoring it as a loss would drag every map
    down by the void rate, which is 6.2% of selections."""
    frame = _bets("rush_yards", 800)
    frame.loc[frame.index[:400], "outcome"] = "void"

    calibration = fit(frame)

    assert calibration.markets["rush_yards"].rows == 400
