"""One compound simulation per player, serving every market he is priced in.

## Why a simulation rather than four fitted distributions

A receiver's receptions, receiving yards, longest reception and touchdowns are
not four independent quantities. They are one afternoon, seen four ways. Fit
them separately and the model will happily price a player for 8 receptions,
40 yards and a 55-yard long — a set of numbers that cannot all happen.

So each player-game is simulated once:

1. draw **opportunities** (targets converted to receptions, or carries) from a
   negative binomial fitted to his own recent volume;
2. draw that many **per-play yardages** from the league's empirical
   distribution, tilted to his own yards-per-opportunity;
3. read every market off the same draws — the **sum** is his yardage, the
   **maximum** is his longest, and a per-opportunity touchdown rate gives the
   scoring markets.

Everything is consistent by construction, and **every alternate rung prices
from the same distribution** as the featured line, so the ladder and the main
market can never disagree.

## Why yards are not a count model

Yards are a compound outcome — opportunities times yards-per-opportunity —
heavily right-skewed and zero-inflated. Measured over 2022-2025: 11.2% of
carries lose yards and 8.2% gain none; the completion tail reaches 98. A
Poisson or a negative binomial fitted to total yards has none of that shape,
prices the 40-yard tail as nearly impossible, and cannot produce a "longest"
market at all.

Receptions and attempts **are** counts, and are modelled as counts. That
distinction is the point: a count model is right for the count and wrong for
the yardage that comes out of it.

## What this model does not know, stated rather than hidden

**Usage is fitted from recent volume, not from snap share.** Snap and target
share are available in the feeds and are not used yet. A model pricing a
receiver from his volume alone is pricing his recent role, which is a weaker
claim than pricing his current one.

**Game script is not modelled.** Leads change play-calling and blowouts empty
benches, so a prop conditioned on a game state that does not happen is a bet
on the script. Nothing here conditions on the game state at all, which is a
different and more honest failure: the model is unconditional and says so.

**Correlation across players is not modelled.** Within a player everything is
consistent; between a quarterback and his receiver nothing is. Never stake
those as independent — that accounting belongs to the card, not here.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from football_betting_lab.models.scoring import tilt_to_mean


#: Draws per player-game. Enough that a 1-in-500 tail rung is estimated from
#: about 40 draws, which is coarse but honest; the alternative is a smooth
#: parametric tail nobody measured.
DEFAULT_DRAWS = 20_000

#: Games of a player's own history before his rate stops being shrunk toward
#: his position's. Football seasons are 17 games, so this is deliberately
#: heavy: a receiver with three games is mostly his position.
PRIOR_GAMES = 6.0

#: The three per-play families the yardage file holds.
YARDAGE_KINDS = ("completion", "rush", "reception")


@dataclass(frozen=True)
class PlayerRates:
    """One player's fitted volume and efficiency, from games before a date."""

    player_id: str
    name: str
    games: int
    opportunities_mean: float
    opportunities_variance: float
    yards_per_opportunity: float
    touchdown_rate: float

    @property
    def is_usable(self) -> bool:
        """Whether there is enough history to hold an opinion at all.

        A player with no logged opportunities has no rate, and a model that
        invented one would produce a confident price for someone it has never
        seen play.
        """
        return self.games > 0 and self.opportunities_mean > 0


@dataclass
class Simulation:
    """The draws, and the markets read off them."""

    opportunities: np.ndarray
    yards: np.ndarray
    longest: np.ndarray
    touchdowns: np.ndarray

    def probability_over(self, quantity: str, line: float) -> float:
        """P(quantity > line). Strict, because a line is a half-point or a push.

        On a whole-number line this returns the over side only; the push mass
        is `probability_push`, and the card must use both or it is pricing a
        two-way market as though it had no third outcome.
        """
        values = getattr(self, quantity)
        return float((values > line).mean())

    def probability_under(self, quantity: str, line: float) -> float:
        values = getattr(self, quantity)
        return float((values < line).mean())

    def probability_push(self, quantity: str, line: float) -> float:
        """The mass exactly on the line.

        Zero on a half-point line and real on a whole one. A card that priced
        over and under without it would have them sum to less than one and
        would read the shortfall as vig.
        """
        values = getattr(self, quantity)
        return float((values == line).mean())


def load_play_yardage(processed_dir: Path) -> dict[str, dict[int, float]]:
    path = Path(processed_dir) / "play_yardage.json"
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        kind: {int(yards): float(p) for yards, p in pmf.items()}
        for kind, pmf in payload.items()
    }


def fit_rates(
    logs: pd.DataFrame,
    *,
    before: str,
    opportunity_column: str,
    yards_column: str,
    touchdown_column: str,
) -> dict[str, PlayerRates]:
    """Fit every player from games strictly earlier than `before`.

    `before` is a season-week ordering key, not a date, because the logs are
    weekly. Same-week data never touches its own fit: in a sixteen-game week
    the rest of the week is not history.
    """
    if logs.empty:
        return {}
    ordered = logs.assign(
        _key=logs["season"].astype(int) * 100 + logs["week"].astype(int)
    )
    history = ordered[ordered["_key"] < int(before)]
    if history.empty:
        return {}

    league_yards_per = (
        history[yards_column].sum() / max(history[opportunity_column].sum(), 1.0)
    )
    league_td_rate = (
        history[touchdown_column].sum() / max(history[opportunity_column].sum(), 1.0)
    )

    rates: dict[str, PlayerRates] = {}
    for player_id, frame in history.groupby("player_id"):
        opportunities = frame[opportunity_column].astype(float)
        played = opportunities[opportunities > 0]
        if played.empty:
            continue
        games = len(played)
        weight = games / (games + PRIOR_GAMES)
        total_opportunities = max(played.sum(), 1.0)
        rates[str(player_id)] = PlayerRates(
            player_id=str(player_id),
            name=str(frame["player_name"].iloc[-1]),
            games=games,
            opportunities_mean=float(played.mean()),
            # A single game has no variance; fall back to the mean, which is
            # the Poisson assumption and the least confident one available.
            opportunities_variance=float(
                played.var(ddof=1) if games > 1 else played.mean()
            ),
            yards_per_opportunity=float(
                weight * (frame[yards_column].sum() / total_opportunities)
                + (1 - weight) * league_yards_per
            ),
            touchdown_rate=float(
                weight * (frame[touchdown_column].sum() / total_opportunities)
                + (1 - weight) * league_td_rate
            ),
        )
    return rates


def _draw_opportunities(
    rates: PlayerRates, draws: int, generator: np.random.Generator
) -> np.ndarray:
    """Negative binomial where the data is overdispersed, Poisson where not.

    Volume is overdispersed in football — a running back's carries swing with
    the game script — so Poisson understates both tails. But a variance below
    the mean is not evidence of underdispersion at these sample sizes, it is
    noise, and forcing a negative binomial onto it produces nonsense
    parameters.
    """
    mean = max(rates.opportunities_mean, 1e-6)
    variance = rates.opportunities_variance
    if variance <= mean * 1.05:
        return generator.poisson(mean, size=draws)
    # Mean = n(1-p)/p, Var = n(1-p)/p^2  ->  p = mean/var
    probability = mean / variance
    number = mean * probability / (1 - probability)
    return generator.negative_binomial(max(number, 1e-6), probability, size=draws)


def simulate(
    rates: PlayerRates,
    per_play: dict[int, float],
    *,
    draws: int = DEFAULT_DRAWS,
    seed: int = 0,
) -> Simulation:
    """Simulate one player-game `draws` times.

    The seed is explicit and defaulted, so a card built twice from the same
    fit produces the same prices. A model whose opinion moves when nothing
    else did cannot be argued with, and the forward ledger would be recording
    the sampler rather than the model.
    """
    generator = np.random.default_rng(seed)
    counts = _draw_opportunities(rates, draws, generator)
    tilted = tilt_to_mean(per_play, rates.yards_per_opportunity)
    if not tilted:
        zeros = np.zeros(draws)
        return Simulation(counts, zeros, zeros, np.zeros(draws, dtype=int))

    support = np.array(sorted(tilted), dtype=float)
    weights = np.array([tilted[int(value)] for value in support], dtype=float)
    weights = weights / weights.sum()

    longest_run = int(counts.max()) if counts.size else 0
    yards = np.zeros(draws)
    longest = np.zeros(draws)
    if longest_run:
        # One rectangular draw, masked by each simulation's own count. Far
        # faster than looping, and identical in distribution.
        sampled = generator.choice(support, size=(draws, longest_run), p=weights)
        mask = np.arange(longest_run)[None, :] < counts[:, None]
        yards = np.where(mask, sampled, 0.0).sum(axis=1)
        masked = np.where(mask, sampled, -np.inf)
        longest = np.where(counts > 0, masked.max(axis=1), 0.0)

    touchdowns = generator.binomial(
        counts, min(max(rates.touchdown_rate, 0.0), 1.0)
    )
    return Simulation(counts.astype(float), yards, longest, touchdowns)
