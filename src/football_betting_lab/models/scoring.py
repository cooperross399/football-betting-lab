"""Team scoring: an empirical distribution, tilted to a fitted mean.

## Why not a smooth distribution

NFL scores are lumpy. They pile up on 3, 7, 10, 14, 17, 20, 24 because points
arrive in threes and sevens, and margins pile up on **3 and 7** for the same
reason. A Poisson or a normal fitted to the mean is smooth, and a smooth
distribution prices a whole-number spread of 3 as though it were a spread of
2.5 — which is precisely where the value in a football line lives.

So the shape comes from the data and only the **mean** is fitted. The
empirical distribution of team scores is reweighted by exponential tilting
until its mean is the one the ratings predict:

    p'(x) ∝ p(x) · e^(θx)

θ is solved for numerically. Tilting preserves the lumpiness exactly — the
mass at 3, 7, 10 stays in proportion — while moving the centre wherever the
fit says. A model that smoothed that away would report a spread edge that was
really a statement about the smoothing.

## Pushes are exact, never approximated

A whole-number spread pushes on an exact margin and a whole-number total
pushes on an exact sum. Both are computed from the joint mass at those exact
integers, not by nudging the line half a point. That is the difference between
pricing the bet and pricing a bet like it.

## Independence, checked rather than assumed

The two sides are treated as independent given their means. The obvious
objection is that game script correlates them and a blowout suppresses both,
so the total would come out too wide.

**Measured over 1,087 games, that objection is wrong.** The correlation
between the two final scores is **-0.017** — indistinguishable from zero — and
the modelled standard deviation of the total is **13.88 against an observed
13.64**, a 1.8% overstatement. Independence is close to right for the total,
and the caveat this docstring originally carried was an assumption dressed as
a finding.

It is emphatically **not** right for the one quantity below.

## Overtime, because independence gets the tie badly wrong

Two independent discrete marginals land on exactly equal scores far more often
than two NFL teams do. The raw joint puts **3.54%** of its mass on a tie; the
observed rate is **0.28%**, a twelvefold overstatement. That is not a small
error in a small market: on a two-way moneyline a tie is a push, so 3.3
percentage points of misallocated mass distorts both sides' win probabilities.

The mechanism is not a mystery and it is not correlation. It is overtime, and
the arithmetic closes exactly (1,087 games, 2022-2025):

* **5.80%** of games are level at the end of regulation and go to overtime;
* overtime resolves **95.2%** of those (60 of 63);
* 0.0580 x 0.048 = **0.0028**, the observed tie rate to four decimal places.

So the joint's equality mass is read as *level after regulation*, and 95.2% of
it is redistributed to the two sides. Of the games overtime resolves, the home
side wins **55.0%** (33 of 60) — a sample far too small to mean much, stated
with its count wherever it is used.

**What the correction does not fix, and is not tuned to fix.** After
resolution the model puts **0.17%** on a tie against **0.28%** observed. The
residual is a second, smaller discrepancy: the independent joint puts 3.54% of
its mass on exact equality where 5.80% of real games are level after
regulation, so it understates the regulation-level rate by about a third.

That is left alone on purpose. Three ties in 1,087 games cannot support
calibration to the third decimal, and a second multiplicative constant chosen
to close the gap would be fitted to those three games and to nothing else.
The two numbers are reported; neither is tuned.

This is a mechanism measured from data, not a tuning constant. It makes the
model describe the sport rather than describe two independent dice, which is
why it lives in the distribution rather than in a policy the verdicts door has
to approve.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass

import pandas as pd


#: Scores above this are vanishingly rare and the tail is not informative.
MAX_SCORE = 70

#: How often overtime produces a winner, measured over 63 overtime games in
#: 2022-2025. Small sample, and stated with its count everywhere it appears.
OVERTIME_RESOLUTION_RATE = 0.952

#: The home side's share of overtime games that produce a winner: 33 of 60
#: in 2022-2025. Far too small to mean much on its own, and stated with its
#: count everywhere it appears; the alternative is assuming exactly 0.5, which
#: is also a claim and has less behind it.
OVERTIME_HOME_SHARE = 0.550

#: How strongly a team's own record is shrunk toward the league mean. With
#: `k` games played the team's rate gets weight `n / (n + PRIOR_GAMES)`.
#: Seventeen games is a whole season, so a full season is weighted about half
#: — deliberately heavy shrinkage, because one NFL season is 272 games and
#: nothing here has earned more confidence than that.
PRIOR_GAMES = 17.0


@dataclass(frozen=True)
class TeamRatings:
    """Fitted from games strictly earlier than the one being priced."""

    league_mean: float
    offence: dict[str, float]
    defence: dict[str, float]
    home_advantage: float
    games_used: int

    def expected_points(self, team: str, opponent: str, *, at_home: bool) -> float:
        """Points this side is expected to score. Never negative."""
        base = (
            self.league_mean
            + self.offence.get(team, 0.0)
            + self.defence.get(opponent, 0.0)
            + (self.home_advantage / 2 if at_home else -self.home_advantage / 2)
        )
        return max(base, 3.0)


def empirical_pmf(scores: list[int]) -> dict[int, float]:
    """The observed distribution of team scores, as a pmf over integers."""
    counts = Counter(int(score) for score in scores if 0 <= int(score) <= MAX_SCORE)
    total = sum(counts.values())
    if not total:
        return {}
    return {score: count / total for score, count in sorted(counts.items())}


def tilt_to_mean(pmf: dict[int, float], target: float) -> dict[int, float]:
    """Reweight a pmf so its mean is `target`, preserving its shape.

    Solved by bisection on θ. Bisection rather than Newton because the
    objective is monotone in θ and bisection cannot diverge — a fitted mean
    that failed to converge would silently return the untilted distribution,
    which is a plausible-looking answer to a different question.
    """
    if not pmf:
        return {}
    lowest, highest = min(pmf), max(pmf)
    if target <= lowest:
        return {lowest: 1.0}
    if target >= highest:
        return {highest: 1.0}

    def mean_at(theta: float) -> float:
        weights = {x: p * math.exp(theta * x) for x, p in pmf.items()}
        total = sum(weights.values())
        return sum(x * w for x, w in weights.items()) / total

    low, high = -5.0, 5.0
    for _ in range(200):
        middle = (low + high) / 2
        if mean_at(middle) < target:
            low = middle
        else:
            high = middle
    theta = (low + high) / 2
    weights = {x: p * math.exp(theta * x) for x, p in pmf.items()}
    total = sum(weights.values())
    return {x: w / total for x, w in weights.items()}


def fit_ratings(games: pd.DataFrame, *, before: str) -> TeamRatings:
    """Fit from games strictly earlier than `before`.

    Walk-forward is not a nicety here. In a sixteen-game week the temptation
    to use the rest of the week is large, and using it would leak the result
    of a game into the price of one played at the same time.
    """
    required = {"game_date", "home_team", "away_team", "home_score", "away_score"}
    if games.empty or not required <= set(games.columns):
        # No history at all is a real state in week one, not an error. An
        # empty frame also carries no columns, so this must be checked before
        # any column is touched.
        return TeamRatings(21.0, {}, {}, 2.0, 0)
    history = games[games["game_date"].astype(str) < str(before)]
    history = history.dropna(subset=["home_score", "away_score"])
    if history.empty:
        return TeamRatings(21.0, {}, {}, 2.0, 0)

    scored: dict[str, list[float]] = {}
    allowed: dict[str, list[float]] = {}
    for row in history.itertuples():
        for team, opponent, points, against in (
            (row.home_team, row.away_team, row.home_score, row.away_score),
            (row.away_team, row.home_team, row.away_score, row.home_score),
        ):
            scored.setdefault(str(team), []).append(float(points))
            allowed.setdefault(str(team), []).append(float(against))

    league_mean = float(
        (history["home_score"].sum() + history["away_score"].sum())
        / (2 * len(history))
    )
    home_advantage = float(
        history["home_score"].mean() - history["away_score"].mean()
    )

    def shrunk(values: list[float]) -> float:
        n = len(values)
        if not n:
            return 0.0
        weight = n / (n + PRIOR_GAMES)
        return weight * (sum(values) / n - league_mean)

    return TeamRatings(
        league_mean=league_mean,
        offence={team: shrunk(values) for team, values in scored.items()},
        defence={team: shrunk(values) for team, values in allowed.items()},
        home_advantage=home_advantage,
        games_used=len(history),
    )


@dataclass(frozen=True)
class GameDistribution:
    """The joint distribution of a game's two scores."""

    home: dict[int, float]
    away: dict[int, float]

    def joint(self) -> dict[tuple[int, int], float]:
        return {
            (h, a): ph * pa
            for h, ph in self.home.items()
            for a, pa in self.away.items()
        }

    # -- market probabilities, every push computed exactly ------------------

    def moneyline(self, *, resolve_overtime: bool = True) -> dict[str, float]:
        """Home, away and the tie, with overtime resolved.

        `resolve_overtime=False` returns the raw joint, which exists so the
        correction's size can be measured rather than taken on trust. Nothing
        that prices a bet should use it.
        """
        home = away = level = 0.0
        for (h, a), p in self.joint().items():
            if h > a:
                home += p
            elif a > h:
                away += p
            else:
                level += p
        if not resolve_overtime:
            return {"home": home, "away": away, "draw": level}
        resolved = level * OVERTIME_RESOLUTION_RATE
        return {
            "home": home + resolved * OVERTIME_HOME_SHARE,
            "away": away + resolved * (1 - OVERTIME_HOME_SHARE),
            "draw": level * (1 - OVERTIME_RESOLUTION_RATE),
        }

    def spread(self, line: float, *, side: str) -> tuple[float, float]:
        """`(win, push)` for a side at a line, the push exact on whole numbers.

        `line` is the handicap applied to that side, in the provider's sign
        convention: a home favourite of 3.5 is `-3.5`.
        """
        win = push = 0.0
        for (h, a), p in self.joint().items():
            margin = (h - a) if side == "home" else (a - h)
            adjusted = margin + line
            if adjusted > 0:
                win += p
            elif adjusted == 0:
                push += p
        return win, push

    def total(self, line: float, *, side: str) -> tuple[float, float]:
        win = push = 0.0
        for (h, a), p in self.joint().items():
            combined = h + a
            if combined == line:
                push += p
            elif (combined > line) == (side == "over"):
                win += p
        return win, push

    def team_total(self, line: float, *, side: str) -> tuple[float, float]:
        """`side` is one of `home_over`, `home_under`, `away_over`, `away_under`."""
        which, direction = side.rsplit("_", 1)
        pmf = self.home if which == "home" else self.away
        win = push = 0.0
        for score, p in pmf.items():
            if score == line:
                push += p
            elif (score > line) == (direction == "over"):
                win += p
        return win, push


def distribution_for(
    ratings: TeamRatings,
    pmf: dict[int, float],
    *,
    home_team: str,
    away_team: str,
) -> GameDistribution:
    return GameDistribution(
        home=tilt_to_mean(
            pmf, ratings.expected_points(home_team, away_team, at_home=True)
        ),
        away=tilt_to_mean(
            pmf, ratings.expected_points(away_team, home_team, at_home=False)
        ),
    )
