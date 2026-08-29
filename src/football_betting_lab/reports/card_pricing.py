"""Turn fitted models and staged prices into the probability map the card reads.

Kept separate from the card on purpose. The card's job is gating and
presentation; this module's job is producing an opinion. Mixing them would
make it possible for a gate to be bypassed by a pricing path, which is exactly
the shape of bug that lets an unapproved market reach a selection.

The map is keyed by `selection_key(...)`. **A key that is absent means no
modelled opinion** — which is different from a probability of zero, and every
caller treats it as different.

## The accounting identity

Every priced row lands in exactly one bucket and the run prints the
reconciliation:

    priced = no_opinion + below_threshold + unparseable + ambiguous + bets

A row that fell out for a reason nobody counted makes the identity fail
loudly, which is the point. Silent attrition is how a card ends up
recommending from a sixth of a slate and reporting it as the whole one.

## Which model prices which market

Yardage, per-play maxima and the counts that generate them come off the
**compound simulation** — one per player per family, so they cannot disagree.
Everything else is a direct count: sacks, tackles, kicking points and
interceptions have no yardage to compound, and inventing one would add
structure the data does not have.

Anytime touchdown is the one market that spans families: a player scores if
either his rushing or his receiving simulation produces a touchdown, so it is
computed from both rather than from a fitted "anytime" rate that could
disagree with its own parts.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from football_betting_lab.leagues import League
from football_betting_lab.markets import MARKETS_BY_KEY
from football_betting_lab.models.player_props import (
    PlayerRates,
    Simulation,
    fit_rates,
    simulate,
)
from football_betting_lab.models.scoring import GameDistribution
from football_betting_lab.season import clean_text
from football_betting_lab.selection import normalise_line, selection_key


COMPOUND = "compound"
COUNT = "count"
SPANNING = "spanning"

#: market -> (how it is priced, family, quantity or settlement column)
MARKET_SOURCES: dict[str, tuple[str, str, str]] = {
    "pass_yards": (COMPOUND, "completion", "yards"),
    "pass_completions": (COMPOUND, "completion", "opportunities"),
    "pass_longest_completion": (COMPOUND, "completion", "longest"),
    "rush_yards": (COMPOUND, "rush", "yards"),
    "rush_attempts": (COMPOUND, "rush", "opportunities"),
    "rush_longest": (COMPOUND, "rush", "longest"),
    "reception_yards": (COMPOUND, "reception", "yards"),
    "receptions": (COMPOUND, "reception", "opportunities"),
    "reception_longest": (COMPOUND, "reception", "longest"),
    # Direct counts: nothing to compound, and inventing a per-play yardage for
    # a sack would add structure the data does not have.
    "pass_attempts": (COUNT, "", "pass_attempts"),
    "pass_tds": (COUNT, "", "pass_tds"),
    "pass_interceptions": (COUNT, "", "pass_interceptions"),
    "rush_tds": (COUNT, "", "rush_tds"),
    "reception_tds": (COUNT, "", "reception_tds"),
    "kicking_points": (COUNT, "", "kicking_points"),
    "field_goals": (COUNT, "", "field_goals"),
    "tackles_assists": (COUNT, "", "tackles_assists"),
    "sacks": (COUNT, "", "sacks"),
    "defensive_interceptions": (COUNT, "", "defensive_interceptions"),
    # Spans two families: a player scores if either simulation does.
    "anytime_td": (SPANNING, "", "anytime_td"),
}

#: The opportunity, yards and touchdown columns each compound family fits on.
FAMILY_COLUMNS: dict[str, tuple[str, str, str]] = {
    "completion": ("pass_completions", "pass_yards", "pass_tds"),
    "rush": ("rush_attempts", "rush_yards", "rush_tds"),
    "reception": ("receptions", "reception_yards", "reception_tds"),
}

#: Team markets the scoring model can actually price. Everything else in the
#: registry is wired and settleable and has **no model yet** — the half and
#: quarter markets need a within-game scoring model this lab does not have.
#:
#: The distinction is load-bearing. A market with no model is `no_opinion`;
#: only a row whose vocabulary this lab cannot read is `unparseable`. Filing
#: the first as the second was a real bug here: 42 first-half rows were
#: counted as parsing failures, which reads as an adapter fault and hides a
#: modelling gap behind it.
MODELLED_TEAM_MARKETS: frozenset[str] = frozenset(
    {
        "moneyline",
        "spread",
        "alternate_spread",
        "total_points",
        "alternate_total_points",
        "team_total",
        "alternate_team_total",
    }
)

#: First-half markets, priced from the half model when one is supplied and
#: the recorded verdict says it ships. Absent either, they stay `no_opinion`
#: with the reason stated — never `unparseable`, which would read as an
#: adapter fault.
HALF_MARKETS: dict[str, str] = {
    "moneyline_h1": "moneyline",
    "spread_h1": "spread",
    "total_points_h1": "total_points",
}

ProbabilityMap = dict[tuple, float]


@dataclass
class PricingDiagnostics:
    """Every priced row, in exactly one bucket."""

    priced: int = 0
    no_opinion: int = 0
    unparseable: int = 0
    ambiguous: int = 0
    opinions: int = 0
    reasons: Counter = field(default_factory=Counter)

    def note(self, bucket: str, reason: str) -> None:
        setattr(self, bucket, getattr(self, bucket) + 1)
        self.reasons[reason] += 1

    def reconciles(self) -> bool:
        return self.priced == (
            self.no_opinion + self.unparseable + self.ambiguous + self.opinions
        )

    def identity_line(self) -> str:
        state = "reconciles" if self.reconciles() else "DOES NOT RECONCILE"
        return (
            f"priced {self.priced:,} = no_opinion {self.no_opinion:,} + "
            f"unparseable {self.unparseable:,} + ambiguous {self.ambiguous:,} "
            f"+ opinions {self.opinions:,} — {state}."
        )


class PlayerBook:
    """Every simulation a player needs, built once and reused for every rung."""

    def __init__(
        self,
        logs: pd.DataFrame,
        per_play: dict[str, dict[int, float]],
        *,
        before: str,
        draws: int = 20_000,
        seed: int = 0,
        recency_half_life: float | None = None,
    ) -> None:
        self.per_play = per_play
        self.draws = draws
        self.seed = seed
        # Off unless a recorded verdict turns it on. The caller reads the
        # verdict; this class does not, so a model cannot quietly enable a
        # policy the card did not consult the door about.
        self.recency_half_life = recency_half_life
        self.rates: dict[str, dict[str, PlayerRates]] = {}
        for family, (opportunity, yards, touchdowns) in FAMILY_COLUMNS.items():
            self.rates[family] = fit_rates(
                logs,
                before=before,
                opportunity_column=opportunity,
                yards_column=yards,
                touchdown_column=touchdowns,
                recency_half_life=recency_half_life,
            )
        self.counts = _fit_counts(
            logs, before=before, recency_half_life=recency_half_life
        )
        self._cache: dict[tuple[str, str], Simulation | None] = {}

    def simulation(self, player_id: str, family: str) -> Simulation | None:
        key = (player_id, family)
        if key not in self._cache:
            rates = self.rates.get(family, {}).get(player_id)
            per_play = self.per_play.get(family)
            if rates is None or not rates.is_usable or not per_play:
                self._cache[key] = None
            else:
                self._cache[key] = simulate(
                    rates, per_play, draws=self.draws, seed=self.seed
                )
        return self._cache[key]

    def count_distribution(self, player_id: str, column: str) -> np.ndarray | None:
        rates = self.counts.get(column, {}).get(player_id)
        if rates is None or not rates.is_usable:
            return None
        generator = np.random.default_rng(self.seed + len(column))
        mean = max(rates.opportunities_mean, 1e-6)
        variance = rates.opportunities_variance
        if variance <= mean * 1.05:
            return generator.poisson(mean, size=self.draws).astype(float)
        probability = mean / variance
        number = mean * probability / (1 - probability)
        return generator.negative_binomial(
            max(number, 1e-6), probability, size=self.draws
        ).astype(float)

    def anytime_touchdown(self, player_id: str) -> float | None:
        """P(scores at least one touchdown), from both families at once.

        Not a fitted "anytime" rate: that would be a fourth number able to
        disagree with the rushing and receiving simulations it is supposed to
        summarise.
        """
        rushing = self.simulation(player_id, "rush")
        receiving = self.simulation(player_id, "reception")
        if rushing is None and receiving is None:
            return None
        total = np.zeros(self.draws)
        for simulation in (rushing, receiving):
            if simulation is not None:
                total = total + simulation.touchdowns
        return float((total > 0).mean())


def _fit_counts(
    logs: pd.DataFrame, *, before: str, recency_half_life: float | None = None
) -> dict[str, dict[str, PlayerRates]]:
    """Direct count rates for the markets with nothing to compound."""
    columns = sorted(
        {column for kind, _, column in MARKET_SOURCES.values() if kind == COUNT}
    )
    fitted: dict[str, dict[str, PlayerRates]] = {}
    for column in columns:
        if column not in logs.columns:
            continue
        fitted[column] = fit_rates(
            logs,
            before=before,
            opportunity_column=column,
            yards_column=column,
            touchdown_column=column,
            recency_half_life=recency_half_life,
            # The opportunity column IS the settlement column here, so
            # dropping the zero games would fit "mean sacks given a sack".
            condition_on_appearance=False,
        )
    return fitted


def price_slate(
    prices: pd.DataFrame,
    league: League,
    *,
    distributions: dict[tuple[str, str], GameDistribution],
    book: PlayerBook,
    player_ids: dict[str, str],
    half_distributions: dict[tuple[str, str], GameDistribution] | None = None,
) -> tuple[ProbabilityMap, PricingDiagnostics]:
    """A probability for every staged row this lab has an opinion on.

    `distributions` is keyed by the provider's own `(home, away)` strings, and
    `player_ids` maps a provider player name to a resolved id — both built by
    the caller, which is where club and identity resolution belongs. A name
    that did not resolve simply is not in the map, and its rows land in
    `no_opinion` rather than being guessed at.
    """
    probabilities: ProbabilityMap = {}
    diagnostics = PricingDiagnostics()
    if prices.empty:
        return probabilities, diagnostics

    for row in prices.itertuples():
        diagnostics.priced += 1
        market_key = clean_text(getattr(row, "market", ""))
        market = MARKETS_BY_KEY.get(market_key)
        selection = clean_text(getattr(row, "selection", "")).lower()
        line = normalise_line(getattr(row, "line", None))
        if market is None:
            diagnostics.note("unparseable", f"unknown market `{market_key}`")
            continue

        if market.kind == "team":
            home = str(getattr(row, "home_team", ""))
            away = str(getattr(row, "away_team", ""))
            distribution = distributions.get((home, away))
            if distribution is None:
                diagnostics.note("no_opinion", f"no fitted game for {away} @ {home}")
                continue
            if market.key in HALF_MARKETS:
                half = (half_distributions or {}).get((home, away))
                if half is None:
                    diagnostics.note(
                        "no_opinion",
                        f"`{market.key}` needs the first-half model, which is "
                        "not in force — see the recorded verdict",
                    )
                    continue
                probability = _team_probability(
                    half, HALF_MARKETS[market.key], selection, line
                )
                if probability is None:
                    diagnostics.note(
                        "unparseable", f"`{market.key}` selection `{selection}`"
                    )
                    continue
                probabilities[
                    selection_key(
                        row,
                        market=market.key,
                        selection=selection,
                        line=line,
                        league=league,
                    )
                ] = probability
                diagnostics.opinions += 1
                continue
            if market.key not in MODELLED_TEAM_MARKETS:
                diagnostics.note(
                    "no_opinion",
                    f"`{market.key}` is wired and settleable but has no model "
                    "yet — the half and quarter markets need a within-game "
                    "scoring model this lab does not have",
                )
                continue
            probability = _team_probability(distribution, market.key, selection, line)
            if probability is None:
                diagnostics.note(
                    "unparseable", f"`{market.key}` selection `{selection}`"
                )
                continue
        else:
            player = clean_text(getattr(row, "player", ""))
            player_id = player_ids.get(player.casefold())
            if not player_id:
                diagnostics.note("no_opinion", "player not on a current roster")
                continue
            probability = _player_probability(book, player_id, market.key, selection, line)
            if probability is None:
                diagnostics.note("no_opinion", f"no fitted rate for `{market.key}`")
                continue

        probabilities[
            selection_key(
                row,
                market=market.key,
                selection=selection,
                line=line,
                league=league,
            )
        ] = probability
        diagnostics.opinions += 1

    return probabilities, diagnostics


def _team_probability(
    distribution: GameDistribution, market: str, selection: str, line: float | None
) -> float | None:
    """P(this side wins), with the push mass removed from the denominator.

    A push returns the stake, so the bet is a two-outcome wager on the
    non-push mass. Pricing it against the full mass would understate every
    whole-number line by exactly the push probability — which on a spread of 3
    is 3.4 points of probability, the largest single mispricing available in
    this sport.
    """
    if market in {"moneyline"} and selection in {"home", "away", "draw"}:
        moneyline = distribution.moneyline()
        push = moneyline["draw"] if selection != "draw" else 0.0
        win = moneyline.get(selection, 0.0)
        return _without_push(win, push)
    if market in {"spread", "alternate_spread"} and selection in {"home", "away"}:
        if line is None:
            return None
        win, push = distribution.spread(line, side=selection)
        return _without_push(win, push)
    if market in {"total_points", "alternate_total_points"} and selection in {
        "over",
        "under",
    }:
        if line is None:
            return None
        win, push = distribution.total(line, side=selection)
        return _without_push(win, push)
    if market in {"team_total", "alternate_team_total"} and line is not None:
        if selection not in {"home_over", "home_under", "away_over", "away_under"}:
            return None
        win, push = distribution.team_total(line, side=selection)
        return _without_push(win, push)
    return None


def _without_push(win: float, push: float) -> float:
    remaining = 1.0 - push
    return win / remaining if remaining > 1e-9 else 0.0


def _player_probability(
    book: PlayerBook, player_id: str, market: str, selection: str, line: float | None
) -> float | None:
    source = MARKET_SOURCES.get(market)
    if source is None or line is None:
        return None
    kind, family, quantity = source

    if kind == SPANNING:
        probability = book.anytime_touchdown(player_id)
        if probability is None:
            return None
        return probability if selection == "over" else 1.0 - probability

    if kind == COMPOUND:
        simulation = book.simulation(player_id, family)
        if simulation is None:
            return None
        over = simulation.probability_over(quantity, line)
        push = simulation.probability_push(quantity, line)
    else:
        values = book.count_distribution(player_id, quantity)
        if values is None:
            return None
        over = float((values > line).mean())
        push = float((values == line).mean())

    if selection == "over":
        return _without_push(over, push)
    if selection == "under":
        return _without_push(1.0 - over - push, push)
    return None
