"""Invariants that would have caught this lab's actual failure class.

Every defect found here produced a **plausible number rather than an error**: a
cross-season settlement that looked like replication, a walk-forward leak that
looked like a mechanism, a tackle column short by 7% that looked like a +11.6%
edge. None of them raised. Each was caught by a human disbelieving a good
result, which does not scale and did not always happen quickly.

These are the properties that must hold whatever the inputs, so a future defect
of the same shape trips a test rather than waiting to be disbelieved.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from football_betting_lab.forward_evidence import interval_by_game
from football_betting_lab.markets import MARKETS_BY_KEY
from football_betting_lab.models.scoring import GameDistribution


def _certain(home: int, away: int) -> GameDistribution:
    return GameDistribution(home={home: 1.0}, away={away: 1.0})


def _spread_distribution() -> GameDistribution:
    """A real-ish scoring distribution, lumpy at the football numbers."""
    home = {0: .02, 3: .10, 7: .12, 10: .14, 14: .14, 17: .14, 20: .12, 21: .10, 24: .07, 28: .05}
    away = dict(home)
    return GameDistribution(home=home, away=away)


# -- pricing invariants ------------------------------------------------------

@pytest.mark.parametrize("side", ["over", "under"])
def test_a_total_is_monotone_in_its_line(side: str) -> None:
    """P(over) must fall as the line rises, and P(under) must climb.

    A sign error anywhere in the ladder pricing breaks this, and a ladder that
    is not monotone prices two rungs of the same market inconsistently — which
    is a mispricing the model creates rather than finds.
    """
    distribution = _spread_distribution()
    lines = [30.5, 35.5, 40.5, 45.5, 50.5]
    wins = [distribution.total(line, side=side)[0] for line in lines]

    if side == "over":
        assert all(a >= b - 1e-12 for a, b in zip(wins, wins[1:])), wins
    else:
        assert all(a <= b + 1e-12 for a, b in zip(wins, wins[1:])), wins


def test_a_spread_is_monotone_in_its_line() -> None:
    """More points of handicap can only help the side receiving them."""
    distribution = _spread_distribution()
    lines = [-7.5, -3.5, -0.5, 3.5, 7.5]
    wins = [distribution.spread(line, side="home")[0] for line in lines]

    assert all(a <= b + 1e-12 for a, b in zip(wins, wins[1:])), wins


@pytest.mark.parametrize("line", [0.5, 3.0, 3.5, 7.0, 10.5])
def test_both_sides_of_a_spread_plus_the_push_account_for_everything(line) -> None:
    """home win + away win + push == 1. If it does not, some mass is being
    counted twice or dropped — and both sides could win the same game, which
    this repository has already shipped once (+21.6% on 1,695 bets)."""
    distribution = _spread_distribution()
    home_win, push = distribution.spread(line, side="home")
    away_win, away_push = distribution.spread(-line, side="away")

    assert push == pytest.approx(away_push)
    assert home_win + away_win + push == pytest.approx(1.0)


@pytest.mark.parametrize("line", [41.0, 44.5, 45.0])
def test_both_sides_of_a_total_plus_the_push_account_for_everything(line) -> None:
    distribution = _spread_distribution()
    over, push = distribution.total(line, side="over")
    under, under_push = distribution.total(line, side="under")

    assert push == pytest.approx(under_push)
    assert over + under + push == pytest.approx(1.0)


def test_a_whole_number_line_can_push_and_a_half_point_line_cannot() -> None:
    """The lumpiness at 3 and 7 is the whole reason this model tilts an
    empirical distribution rather than fitting a smooth one. If a whole number
    stopped pushing, that machinery would be silently doing nothing."""
    distribution = _spread_distribution()

    assert distribution.spread(3.0, side="home")[1] > 0
    assert distribution.spread(3.5, side="home")[1] == 0


@pytest.mark.parametrize("line", [0.5, 3.0, 7.0])
def test_no_probability_ever_leaves_the_unit_interval(line) -> None:
    distribution = _spread_distribution()
    for side in ("home", "away"):
        win, push = distribution.spread(line, side=side)
        assert 0.0 <= win <= 1.0
        assert 0.0 <= push <= 1.0
        assert win + push <= 1.0 + 1e-12


# -- the market registry -----------------------------------------------------

def test_every_market_says_what_it_settles_on() -> None:
    """A market with no settlement rule is one that will be settled by whatever
    the reader assumes. `anytime_td` was nearly settled on `passing_tds`, which
    would have made every quarterback the likeliest scorer on the field."""
    for key, market in MARKETS_BY_KEY.items():
        assert market.settles_on.strip(), key


# -- interval invariants -----------------------------------------------------

def _ledger(rows: list[dict]) -> pd.DataFrame:
    base = {"snapshot_date": "2026-09-13", "home_team": "SEA", "away_team": "NE",
            "outcome": "won", "profit_units": 1.0}
    return pd.DataFrame([{**base, **r} for r in rows])


def test_an_interval_always_contains_its_own_point_estimate() -> None:
    rows = [{"home_team": f"H{i}", "away_team": f"A{i}",
             "profit_units": 1.0 if i % 2 else -1.0,
             "outcome": "won" if i % 2 else "lost"} for i in range(40)]

    roi, low, high, bets, games = interval_by_game(_ledger(rows))

    assert low <= roi <= high
    assert bets == 40
    assert games == 40


def test_clustering_widens_the_interval_against_a_naive_per_bet_one() -> None:
    """The whole point of clustering. Twenty games of twenty identical bets
    carry twenty games of information, not four hundred bets of it — and a
    naive interval is roughly sqrt(20) too narrow, which is how "no
    demonstrated edge" quietly becomes a claim.
    """
    rows = [{"home_team": f"H{g}", "away_team": f"A{g}",
             "profit_units": 1.0 if g < 10 else -1.0,
             "outcome": "won" if g < 10 else "lost"}
            for g in range(20) for _ in range(20)]

    roi, low, high, bets, games = interval_by_game(_ledger(rows))

    assert bets == 400
    assert games == 20
    naive = 1.96 * np.std([1.0] * 200 + [-1.0] * 200, ddof=1) / np.sqrt(400)
    assert (high - low) / 2 > naive * 2


def test_one_game_offers_no_interval_rather_than_a_narrow_one() -> None:
    """A single cluster cannot support a variance estimate. Reporting one
    anyway would be the narrowest and most confident number in the file."""
    roi, low, high, bets, games = interval_by_game(
        _ledger([{"profit_units": 1.0} for _ in range(50)])
    )

    assert games == 1
    assert low == float("-inf") and high == float("inf")


def test_voids_never_reach_the_return() -> None:
    """A voided prop had no outcome. Counting it as a zero-profit bet drags the
    ROI toward zero and inflates the bet count — and 6.2% of selections void."""
    rows = [{"profit_units": 1.0, "home_team": f"H{i}", "away_team": f"A{i}"}
            for i in range(10)]
    rows += [{"profit_units": 0.0, "outcome": "void",
              "home_team": f"V{i}", "away_team": f"W{i}"} for i in range(10)]

    roi, _, _, bets, _ = interval_by_game(_ledger(rows))

    assert bets == 10
    assert roi == pytest.approx(1.0)


def test_a_push_is_counted_as_a_staked_bet_at_zero_profit() -> None:
    """A push is a bet that happened and returned the stake. Dropping it would
    overstate ROI by removing the flat outcomes; grading it a loss would
    manufacture a negative result out of the sport's lumpiness at 3 and 7."""
    rows = [{"profit_units": 1.0, "home_team": f"H{i}", "away_team": f"A{i}"}
            for i in range(10)]
    rows += [{"profit_units": 0.0, "outcome": "push",
              "home_team": f"P{i}", "away_team": f"Q{i}"} for i in range(10)]

    roi, _, _, bets, _ = interval_by_game(_ledger(rows))

    assert bets == 20
    assert roi == pytest.approx(0.5)


# -- the three clustered intervals must not drift apart -----------------------
#
# `interval_by_game` was sqrt(games) too narrow while `props_backtest._interval`
# and `closing_line_backtest._interval` were correct. Three copies of one
# formula is how that happens, and a comment saying "these must agree" is not a
# guard. This is.

def test_every_clustered_interval_in_the_repository_agrees_with_the_others() -> None:
    """One pooled ROI, three implementations, one answer.

    They read different frames — the ledger, the props bets file, the
    closing-line bets file — so they cannot share a call site without a
    refactor nothing else needs. What they can share is an assertion.
    """
    import pandas as pd

    from football_betting_lab.reports.closing_line_backtest import (
        _interval as closing_interval,
    )
    from football_betting_lab.reports.props_backtest import _interval as props_interval

    # The ladder backtest lives in scripts/, takes a raw bets frame rather than
    # a per-game frame, and was the fourth divergent copy of this formula.
    import importlib.util

    from football_betting_lab.config import PROJECT_ROOT

    spec = importlib.util.spec_from_file_location(
        "_ladder", PROJECT_ROOT / "scripts" / "run_team_ladder_backtest.py"
    )
    ladder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ladder)

    # Deliberately unequal bets per game: a ratio estimator and a mean-of-ratios
    # estimator agree when every cluster is the same size and diverge when they
    # are not, so equal sizes would let a wrong implementation pass.
    per_game = pd.DataFrame(
        {
            "profit": [3.4, -2.0, 0.0, 11.7, -6.25, 1.0, -0.5, 8.0],
            "bets": [4, 2, 7, 19, 11, 1, 3, 9],
        }
    )
    rows = []
    for game, row in enumerate(per_game.itertuples(index=False)):
        # One bet carries the game's whole profit and the rest carry zero, so
        # the per-game totals match `per_game` exactly. The ledger groups on
        # snapshot_date + away@home, so the clubs are what separate the games.
        for bet in range(int(row.bets)):
            rows.append(
                {
                    "home_team": f"H{game}",
                    "away_team": f"A{game}",
                    "outcome": "won" if bet == 0 else "lost",
                    "profit_units": float(row.profit) if bet == 0 else 0.0,
                }
            )
    ledger = _ledger(rows)

    roi_l, low_l, high_l, bets_l, games_l = interval_by_game(ledger)
    roi_p, low_p, high_p = props_interval(per_game)
    roi_c, low_c, high_c = closing_interval(per_game)

    assert bets_l == int(per_game["bets"].sum())
    assert games_l == len(per_game)
    # The ladder takes one row per bet, so expand the per-game frame back out.
    ladder_rows = []
    for game, row in enumerate(per_game.itertuples(index=False)):
        for bet in range(int(row.bets)):
            ladder_rows.append(
                {
                    "event_id": f"g{game}",
                    "outcome": "won" if bet == 0 else "lost",
                    "profit": float(row.profit) if bet == 0 else 0.0,
                }
            )
    roi_L, low_L, high_L = ladder._interval(pd.DataFrame(ladder_rows))

    for name, (roi, low, high) in (
        ("props_backtest", (roi_p, low_p, high_p)),
        ("closing_line_backtest", (roi_c, low_c, high_c)),
        ("run_team_ladder_backtest", (roi_L, low_L, high_L)),
    ):
        assert roi == pytest.approx(roi_l), (
            f"{name} and forward_evidence.interval_by_game disagree on the "
            f"pooled ROI: {roi} vs {roi_l}."
        )
        assert (low, high) == pytest.approx((low_l, high_l)), (
            f"{name} and forward_evidence.interval_by_game disagree on the "
            f"clustered interval: ({low}, {high}) vs ({low_l}, {high_l}). "
            "One of them has drifted. `interval_by_game` was already wrong "
            "once, by a factor of sqrt(games), on the forward ledger."
        )
