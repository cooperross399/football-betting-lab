"""The one asymmetry this lab has found: bad marginals, accurate joint.

Every other instrument measures marginal skill and the answer is no. This
measures the joint, which the compound simulation produces as a byproduct of
reading receptions, yards and longest off the same draws — and which a
sportsbook prices with a different and usually cruder model.

The tests below guard the claim's boundaries as much as its arithmetic. The
number this instrument produces is the size of a CORRELATION, and the standing
temptation is to read it as the size of an EDGE.
"""

from __future__ import annotations

import pandas as pd
import pytest

from football_betting_lab.reports.correlation import (
    CORRELATION_TOLERANCE,
    MINIMUM_PAIRS,
    CorrelationCheck,
    CorrelationResult,
    joint_pairs,
    render,
)


def _check(realised: float, model: float) -> CorrelationCheck:
    return CorrelationCheck(pair="a x b", realised=realised, model=model, games=2000)


def _legs(n: int, both: int, market_probability: float = 0.5) -> pd.DataFrame:
    """`n` two-leg combinations on one player, `both` of which win together."""
    odds = -100 if market_probability == 0.5 else -110
    rows = []
    for i in range(n):
        win = i < both
        for market in ("receptions", "reception_yards"):
            rows.append({
                "event_id": f"e{i}", "player": "A Player", "selection": "over",
                "market": market, "odds": odds,
                "outcome": "won" if win else "lost",
            })
    return pd.DataFrame(rows)


def test_a_simulated_correlation_close_to_the_realised_one_is_matched() -> None:
    assert _check(0.800, 0.814).is_matched
    assert _check(0.800, 0.814).error == pytest.approx(0.014)


def test_a_simulated_correlation_far_from_realised_is_not_matched() -> None:
    """A copula that misses is worse than no copula: a parlay priced off it
    inherits the marginal error AND the correlation error at once."""
    assert not _check(0.800, 0.400).is_matched


def test_the_tolerance_is_stated_and_generous_on_purpose() -> None:
    """A copula accurate to a tenth is far better than these marginals, which
    miss by 0.3 at the top of the range."""
    assert _check(0.80, 0.80 + CORRELATION_TOLERANCE - 0.001).is_matched
    assert not _check(0.80, 0.80 + CORRELATION_TOLERANCE + 0.001).is_matched


def test_realised_joint_is_measured_against_the_independence_product() -> None:
    """Two legs that always win together, priced at even money each. A book
    pricing independence would offer 0.25 where the truth is 0.50."""
    pairs = joint_pairs(_legs(MINIMUM_PAIRS + 100, both=(MINIMUM_PAIRS + 100) // 2))

    assert len(pairs) == 1
    assert pairs[0].realised == pytest.approx(0.5, abs=0.01)
    assert pairs[0].independence == pytest.approx(0.25, abs=0.01)
    assert pairs[0].ratio == pytest.approx(2.0, abs=0.05)


def test_a_thin_leg_pair_is_not_reported() -> None:
    """Below the floor the joint rate is estimated from a handful of games and
    the ratio is dominated by which ones."""
    assert joint_pairs(_legs(MINIMUM_PAIRS - 10, both=5)) == []


def test_two_legs_on_the_same_market_are_not_a_parlay() -> None:
    """`receptions over 4.5` and `receptions over 5.5` are the same market at
    two rungs, not a same-game parlay, and their joint is trivial."""
    frame = pd.DataFrame([
        {"event_id": "e1", "player": "A", "selection": "over",
         "market": "receptions", "odds": -110, "outcome": "won"},
        {"event_id": "e1", "player": "A", "selection": "over",
         "market": "receptions", "odds": -110, "outcome": "won"},
    ])

    assert joint_pairs(frame) == []


def test_the_report_refuses_the_claim_it_cannot_measure() -> None:
    """The standing temptation is to read a 1.65x correlation as a 65% edge.
    Books DO price SGP correlation; the edge is the gap between their model and
    the truth, and that needs SGP prices this lab has never bought."""
    result = CorrelationResult(checks=[_check(0.80, 0.81)])

    text = render(result)

    assert "size of the correlation, not the size of an edge" in text
    assert "cannot be measured without" in text
    assert "not a demonstrated edge" in text


def test_the_report_says_the_marginals_still_have_to_be_fixed() -> None:
    """A perfect copula on overconfident marginals still produces a wrong joint:
    a parlay's price is P(A) x P(B|A)."""
    text = render(CorrelationResult(checks=[_check(0.80, 0.81)]))

    assert "P(A) x P(B|A)" in text


def test_checking_nothing_is_an_absence_not_a_pass() -> None:
    text = render(CorrelationResult())

    assert "absence, not a pass" in text
    assert "asymmetry" not in text


def test_the_fair_joint_of_two_binaries_is_pinned_by_their_correlation() -> None:
    """No copula choice is needed for two binary legs — the correlation IS the
    dependence. P(A and B) = P(A)P(B) + rho*sqrt(P(A)(1-P(A))P(B)(1-P(B)))."""
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location(
        "check_parlay_pricing",
        Path(__file__).resolve().parents[1] / "scripts" / "check_parlay_pricing.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Independent legs: the joint is the product.
    assert module.fair_joint(0.5, 0.5, 0.0) == pytest.approx(0.25)
    # Perfectly correlated equal legs: the joint is the marginal.
    assert module.fair_joint(0.5, 0.5, 1.0) == pytest.approx(0.5)
    # Strongly correlated, the realised receiving figure.
    assert module.fair_joint(0.5, 0.5, 0.8) == pytest.approx(0.45)


def test_a_correlation_implying_an_impossible_joint_is_clipped() -> None:
    """A joint cannot exceed either marginal, nor fall below P(A)+P(B)-1. A
    correlation that implies otherwise is a measurement error, not a price."""
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location(
        "check_parlay_pricing",
        Path(__file__).resolve().parents[1] / "scripts" / "check_parlay_pricing.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.fair_joint(0.2, 0.9, 1.0) == pytest.approx(0.2)
    assert module.fair_joint(0.8, 0.9, -1.0) == pytest.approx(0.7)
