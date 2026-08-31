"""Settlement must agree with pricing, rung by rung.

The team model prices a ladder through `GameDistribution.spread`/`total`/
`team_total`; this backtest settles the same rungs from the final score. If
the two conventions disagree by a sign or an edge case, the result is a
plausible number rather than an error — which is how this repository lost
three headline findings. So each rule below is checked against the pricing
function it must mirror, not against my memory of the convention.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd
import pytest

from football_betting_lab.models.scoring import GameDistribution

_SPEC = importlib.util.spec_from_file_location(
    "run_team_ladder_backtest",
    Path(__file__).resolve().parents[1] / "scripts" / "run_team_ladder_backtest.py",
)
ladder = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(ladder)


class _Row:
    def __init__(self, market: str, selection: str, line: float) -> None:
        self.market = market
        self.selection = selection
        self.line = line


def _certain(home: int, away: int) -> GameDistribution:
    """A distribution with all its mass on one scoreline.

    Then `spread(...)` returns win=1 or push=1, and the pricing function's own
    answer is the settlement the backtest must produce.
    """
    return GameDistribution(home={home: 1.0}, away={away: 1.0})


@pytest.mark.parametrize(
    "home,away,line,side",
    [
        (24, 21, -3.0, "home"),   # exactly on the number: a push
        (24, 21, -3.5, "home"),   # favourite fails to cover
        (24, 21, -2.5, "home"),   # favourite covers
        (21, 24, 3.0, "away"),    # the same push seen from the other side
        (17, 20, 3.5, "home"),    # underdog covers
        (30, 10, -13.0, "away"),  # blowout, dog buried
    ],
)
def test_spread_settlement_matches_spread_pricing(home, away, line, side) -> None:
    distribution = _certain(home, away)
    win, push = distribution.spread(line, side=side)

    got = ladder._settle(_Row("alternate_spread", side, line), home, away)

    expected = "push" if push == 1.0 else ("won" if win == 1.0 else "lost")
    assert got == expected


@pytest.mark.parametrize(
    "home,away,line,side",
    [
        (24, 21, 45.0, "over"),   # exactly on the total: a push
        (24, 21, 44.5, "over"),
        (24, 21, 45.5, "over"),
        (24, 21, 45.0, "under"),  # a push is a push from either side
        (3, 0, 41.5, "under"),
    ],
)
def test_total_settlement_matches_total_pricing(home, away, line, side) -> None:
    distribution = _certain(home, away)
    win, push = distribution.total(line, side=side)

    got = ladder._settle(_Row("alternate_total_points", side, line), home, away)

    expected = "push" if push == 1.0 else ("won" if win == 1.0 else "lost")
    assert got == expected


@pytest.mark.parametrize(
    "home,away,line,side",
    [
        (24, 21, 24.0, "home_over"),   # exactly on it
        (24, 21, 23.5, "home_over"),
        (24, 21, 23.5, "home_under"),
        (24, 21, 21.0, "away_under"),  # the away pmf, not the home one
        (24, 21, 20.5, "away_over"),
    ],
)
def test_team_total_settlement_matches_team_total_pricing(
    home, away, line, side
) -> None:
    distribution = _certain(home, away)
    win, push = distribution.team_total(line, side=side)

    got = ladder._settle(_Row("alternate_team_total", side, line), home, away)

    expected = "push" if push == 1.0 else ("won" if win == 1.0 else "lost")
    assert got == expected


def test_a_missing_line_is_void_and_never_a_loss() -> None:
    """A rung with no line cannot be settled. Grading it a loss would invent a
    result; grading it a win would invent a better one."""
    assert ladder._settle(_Row("alternate_spread", "home", None), 24, 21) == "void"
    assert (
        ladder._settle(_Row("alternate_spread", "home", float("nan")), 24, 21)
        == "void"
    )


def test_an_unknown_market_is_void_rather_than_guessed() -> None:
    assert ladder._settle(_Row("moneyline", "home", -150.0), 24, 21) == "void"


def test_the_interval_is_clustered_by_game() -> None:
    """One game supplies many rungs of the same ladder, and they settle on one
    final score. Treating them as independent narrows the interval by roughly
    the square root of the rungs per game."""
    rows = [
        {"event_id": f"e{g}", "outcome": "won", "profit": 1.0}
        for g in range(10)
        for _ in range(20)
    ]
    rows += [
        {"event_id": f"e{g}", "outcome": "lost", "profit": -1.0}
        for g in range(10, 20)
        for _ in range(20)
    ]
    roi, low, high = ladder._interval(pd.DataFrame(rows))

    assert roi == pytest.approx(0.0)
    # 20 games of +-1, not 400 independent bets: the half-width is ~0.46, not
    # the ~0.10 a per-bet interval would report.
    assert high - low > 0.6


def test_void_rows_are_excluded_from_the_return() -> None:
    frame = pd.DataFrame(
        [
            {"event_id": "a", "outcome": "won", "profit": 1.0},
            {"event_id": "b", "outcome": "void", "profit": 0.0},
        ]
    )

    roi, _, _ = ladder._interval(frame)

    assert roi == pytest.approx(1.0)
