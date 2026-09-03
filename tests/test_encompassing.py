"""The encompassing test, checked against data whose answer is known.

This instrument decides whether any feature work has a point, so the thing that
matters is that it can tell a real signal from none. Both directions are
asserted on synthetic data: a model that is pure noise must return `c` spanning
zero, and a model that genuinely carries information must return `c` above it.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from football_betting_lab.reports import encompassing as enc


def _synthetic(c_true: float, *, games: int = 400, per_game: int = 20, seed: int = 0):
    """A market forecast, a model forecast, and outcomes generated from both.

    `c_true = 0` means the model is noise the outcome does not depend on.
    """
    rng = np.random.default_rng(seed)
    n = games * per_game
    market_logit = rng.normal(0.0, 0.8, n)
    model_logit = rng.normal(0.0, 1.0, n)
    truth = enc.expit(market_logit + c_true * model_logit)
    return pd.DataFrame(
        {
            "event_id": np.repeat([f"g{i}" for i in range(games)], per_game),
            "market": "m",
            "p_market": enc.expit(market_logit),
            "p_model": enc.expit(model_logit),
            "y": rng.binomial(1, truth).astype(float),
        }
    )


def test_a_model_that_is_pure_noise_returns_c_spanning_zero() -> None:
    result = enc.fit(_synthetic(0.0, seed=1), "null")
    assert result is not None
    c = result.c
    assert c is not None
    assert c.includes_zero, (
        f"c = {c.value:+.4f}, interval [{c.low:+.4f}, {c.high:+.4f}] on a model "
        "the outcome does not depend on. The instrument invents information."
    )


def test_a_model_that_genuinely_informs_returns_c_above_zero() -> None:
    """The other direction. A test that only ever returns 'no signal' would pass
    the null case above and be worthless."""
    result = enc.fit(_synthetic(0.6, seed=2), "real")
    assert result is not None
    c = result.c
    assert c is not None
    assert not c.includes_zero and c.value > 0, (
        f"c = {c.value:+.4f}, interval [{c.low:+.4f}, {c.high:+.4f}] on a model "
        "that genuinely carries signal. The instrument cannot see one."
    )
    assert c.value == pytest.approx(0.6, abs=0.25)


def test_the_placebo_destroys_a_real_signal() -> None:
    """Shuffling within market must take a true c back to zero — that is what
    makes the placebo evidence rather than decoration."""
    frame = _synthetic(0.6, seed=3)
    real = enc.fit(frame, "real")
    sham = enc.placebo(frame, seed=3)
    assert real is not None and sham is not None
    assert real.c is not None and sham.c is not None
    assert not real.c.includes_zero
    assert sham.c.includes_zero, (
        f"shuffled c = {sham.c.value:+.4f}, interval [{sham.c.low:+.4f}, "
        f"{sham.c.high:+.4f}] — the placebo does not destroy the signal, so it "
        "cannot certify one."
    )


def test_clustered_standard_errors_are_wider_than_naive_ones() -> None:
    """One game supplies many wagers settling on one afternoon. If the sandwich
    does not widen against an independence assumption it is not clustering."""
    rng = np.random.default_rng(4)
    games, per_game = 200, 25
    n = games * per_game
    # A game-level shock every wager in the game shares: maximal clustering.
    shock = np.repeat(rng.normal(0, 1.2, games), per_game)
    market_logit = rng.normal(0, 0.8, n)
    frame = pd.DataFrame(
        {
            "event_id": np.repeat([f"g{i}" for i in range(games)], per_game),
            "market": "m",
            "p_market": enc.expit(market_logit),
            "p_model": enc.expit(rng.normal(0, 1.0, n)),
            "y": rng.binomial(1, enc.expit(market_logit + shock)).astype(float),
        }
    )
    X = np.column_stack(
        [np.ones(len(frame)), enc.logit(frame["p_market"]), enc.logit(frame["p_model"])]
    )
    y = frame["y"].to_numpy(dtype=float)
    beta = enc.fit_logistic(X, y)
    clustered, _ = enc.cluster_se(X, y, beta, frame["event_id"].to_numpy())
    each_row_its_own = np.arange(len(frame)).astype(str)
    naive, _ = enc.cluster_se(X, y, beta, each_row_its_own)
    assert (clustered >= naive).all()
    # The shock is a shared game-level INTERCEPT shift, so that is the term whose
    # standard error must inflate. Asserting on the slopes instead would pin a
    # number that is a property of this fixture rather than of the clustering:
    # measured here, the intercept inflates 2.50x, the market slope 1.21x and the
    # model slope 1.01x.
    assert clustered[0] > naive[0] * 2.0, (
        f"intercept SE {clustered[0]:.5f} clustered against {naive[0]:.5f} naive. "
        "A shared game-level shock must widen it; if it does not, the sandwich "
        "is not clustering."
    )


def test_a_frame_with_too_few_games_declines_rather_than_answering() -> None:
    tiny = _synthetic(0.0, games=5, per_game=5)
    assert enc.fit(tiny, "tiny") is None


def test_the_logit_clips_rather_than_returning_infinity() -> None:
    values = enc.logit([0.0, 1.0, 0.5])
    assert np.isfinite(values).all()
    assert values[2] == pytest.approx(0.0)


def test_roi_interval_delegates_to_the_pinned_implementation() -> None:
    """A fifth copy of the clustered-interval formula is the same mistake this
    repository already made four times."""
    from football_betting_lab.reports.props_backtest import _interval

    frame = pd.DataFrame(
        {
            "event_id": ["a", "a", "a", "b", "b", "c", "c", "c", "c"],
            "profit": [1.0, -1.0, 0.9, -1.0, 2.0, 0.5, -1.0, -1.0, 3.0],
        }
    )
    per_game = frame.groupby("event_id")["profit"].agg(profit="sum", bets="size")
    assert enc.roi_interval(frame)[:3] == pytest.approx(_interval(per_game))
