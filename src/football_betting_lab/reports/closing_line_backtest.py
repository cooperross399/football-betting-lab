"""Does the team model beat the closing line? Free, and back to 2015.

The nflverse schedule file carries the **closing price on both sides** of the
spread, the total and the moneyline, complete for every regular-season game
from 2015 to 2025. That is 2,895 games of a real, two-sided, priced test,
costing nothing and reaching back further than any purchase at any price.

It is the first instrument this lab has that can rule a model *in* rather than
only out, and it decides the team model the way the bought backtest decides in
the NHL lab.

## Why this is a conservative test, in both directions at once

**It bets into the close.** The closing line is the sharpest price of the
week — the one the whole market has finished arguing about. A card does not
bet there; it bets hours earlier, into a softer number. So a model that breaks
even here would do better in practice.

**And it is one consensus line, not the best of nine books.** The retention
probe found nine books quoting these games. A card takes the best reachable
price; this test takes an average one.

Both understate. So a positive result here is stronger than it looks, and a
negative one is **not** proof that a card would lose — it is proof that the
model does not beat the closing consensus, which is a different and easier
claim to make honestly.

**Closing-line value cannot be measured here at all**, because the bet is
placed at the close. CLV needs the bought historical snapshots.

## What it cannot establish

The sign convention is `spread_line > 0` means the home side is favoured by
that many, verified against the data rather than the documentation: over
2,895 games the mean line is 1.76 against a mean margin of 1.74, and the home
side covers 48.8% of non-pushes.

Every interval is clustered by game, because the three markets on one game are
one afternoon seen three ways. Family-wise correction is applied across the
markets tested and reported beside the raw figure, because with three markets
something will look profitable by chance.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import pandas as pd

from football_betting_lab.config import MAX_DEFAULT_JUICE, MIN_EDGE
from football_betting_lab.forward_evidence import american_to_implied, profit_on_win
from football_betting_lab.models.scoring import (
    distribution_for,
    empirical_pmf,
    fit_ratings,
)


#: The markets this test can reach, and the columns that price them.
MARKETS = (
    ("moneyline", "home_moneyline", "away_moneyline"),
    ("spread", "home_spread_odds", "away_spread_odds"),
    ("total_points", "over_odds", "under_odds"),
)


@dataclass
class MarketResult:
    market: str
    bets: int = 0
    games: int = 0
    profit: float = 0.0
    wins: int = 0
    pushes: int = 0
    roi: float = 0.0
    low: float = 0.0
    high: float = 0.0

    @property
    def interval_includes_zero(self) -> bool:
        return self.low <= 0.0 <= self.high

    def verdict(self, *, corrected_low: float, corrected_high: float) -> str:
        """The one sentence this evidence supports. The words are fixed."""
        if self.bets < MINIMUM_BETS:
            return (
                f"**not enough evidence** — {self.bets} bets, below the "
                f"{MINIMUM_BETS} declared in advance"
            )
        if corrected_low <= 0.0 <= corrected_high:
            return "**no demonstrated edge**"
        direction = "positive" if corrected_low > 0 else "negative"
        return f"interval excludes zero, {direction}"


#: Declared in advance, before any number was computed. Below this the verdict
#: is "not enough evidence" and not a figure, however good the figure looks.
#: The detection arithmetic says roughly 600 bets separate a real +8% from
#: zero; 200 is the point below which even a large edge is unreadable.
MINIMUM_BETS = 200


@dataclass
class BacktestResult:
    seasons: tuple[int, ...]
    games_scored: int = 0
    markets: list[MarketResult] = field(default_factory=list)
    bets: pd.DataFrame = field(default_factory=pd.DataFrame)
    min_edge: float = MIN_EDGE

    @property
    def families(self) -> int:
        return sum(1 for market in self.markets if market.bets >= MINIMUM_BETS)


def _interval(per_game: pd.DataFrame) -> tuple[float, float, float]:
    """ROI and a 95% interval from between-game variation."""
    total = int(per_game["bets"].sum())
    games = len(per_game)
    if not total:
        return 0.0, float("-inf"), float("inf")
    roi = float(per_game["profit"].sum() / total)
    if games < 2:
        return roi, float("-inf"), float("inf")
    mean_bets = total / games
    variance = float(((per_game["profit"] - roi * per_game["bets"]) ** 2).sum())
    standard_error = math.sqrt(variance / (games * (games - 1))) / mean_bets
    return roi, roi - 1.96 * standard_error, roi + 1.96 * standard_error


class MissingPriceColumns(RuntimeError):
    """A market's price column is absent, so the test cannot reach it."""


def require_price_columns(games: pd.DataFrame) -> None:
    """Fail loudly when a market's prices are not in the table.

    The first run of this backtest reported **zero bets** on the spread and
    the total. That read as "the model never disagrees with the close by
    enough", which is a finding. It was not: `home_spread_odds`,
    `over_odds` and their partners had never been built into `team_games.csv`,
    and a `getattr(game, column, None)` default turned a missing column into a
    quietly skipped market.

    That is the exact silent-shortfall shape this repository exists to catch —
    an absence wearing the costume of a measurement. A missing column is now
    an error, and "no bets cleared the bar" can only ever mean what it says.
    """
    needed = {column for _, home, away in MARKETS for column in (home, away)}
    needed |= {"spread_line", "total_line"}
    missing = sorted(needed - set(games.columns))
    if missing:
        raise MissingPriceColumns(
            f"{games.shape[1]} columns and none of {missing}. This test cannot "
            "reach those markets, and reporting zero bets for them would be an "
            "absence dressed as a finding. Rebuild the tables with "
            "`scripts/build_datasets.py`."
        )


def run(
    games: pd.DataFrame,
    *,
    seasons: tuple[int, ...],
    min_edge: float = MIN_EDGE,
    max_juice: int = MAX_DEFAULT_JUICE,
) -> BacktestResult:
    """Price every game walk-forward and bet where the model disagrees enough."""
    require_price_columns(games)
    result = BacktestResult(seasons=tuple(sorted(seasons)), min_edge=min_edge)
    played = games.dropna(subset=["home_score", "away_score"]).copy()
    if played.empty:
        return result

    rows: list[dict] = []
    for season in result.seasons:
        slate = played[played["season"] == season]
        if slate.empty:
            continue
        # Fitted on everything before this season, and on the season's own
        # earlier weeks as it progresses. Same-week data never touches its own
        # fit: in a sixteen-game week the rest of the week is not history.
        history = played[played["season"] < season]
        pmf = empirical_pmf(
            list(history["home_score"].astype(int))
            + list(history["away_score"].astype(int))
        )
        if not pmf:
            continue
        for week in sorted(slate["week"].unique()):
            before = pd.concat(
                [history, slate[slate["week"] < week]], ignore_index=True
            )
            ratings = fit_ratings(
                before.assign(game_date=before["game_date"]), before="9999-99-99"
            )
            for game in slate[slate["week"] == week].itertuples():
                rows.extend(
                    _price_game(game, ratings, pmf, min_edge=min_edge, max_juice=max_juice)
                )
        result.games_scored += len(slate)

    result.bets = pd.DataFrame(rows)
    if result.bets.empty:
        return result

    for market, _, _ in MARKETS:
        subset = result.bets[result.bets["market"] == market]
        if subset.empty:
            result.markets.append(MarketResult(market=market))
            continue
        per_game = subset.groupby("game_id").agg(
            profit=("profit", "sum"), bets=("profit", "size")
        )
        roi, low, high = _interval(per_game)
        result.markets.append(
            MarketResult(
                market=market,
                bets=len(subset),
                games=len(per_game),
                profit=float(subset["profit"].sum()),
                wins=int((subset["outcome"] == "won").sum()),
                pushes=int((subset["outcome"] == "push").sum()),
                roi=roi,
                low=low,
                high=high,
            )
        )
    return result


def _price_game(game, ratings, pmf, *, min_edge: float, max_juice: int) -> list[dict]:
    distribution = distribution_for(
        ratings, pmf, home_team=str(game.home_team), away_team=str(game.away_team)
    )
    margin = float(game.home_score) - float(game.away_score)
    combined = float(game.home_score) + float(game.away_score)
    # `spread_line > 0` means the home side is favoured by that many, so the
    # handicap this model adds to the home margin is its negation. Verified
    # against the data, not read off the documentation.
    spread = -float(game.spread_line) if pd.notna(game.spread_line) else None
    total_line = float(game.total_line) if pd.notna(game.total_line) else None

    out: list[dict] = []
    moneyline = distribution.moneyline()
    for side, odds_column in (("home", "home_moneyline"), ("away", "away_moneyline")):
        odds = getattr(game, odds_column, None)
        if pd.isna(odds):
            continue
        tie = moneyline["draw"]
        probability = moneyline[side] / (1 - tie) if tie < 1 else 0.0
        outcome = (
            "push"
            if margin == 0
            else ("won" if (margin > 0) == (side == "home") else "lost")
        )
        out.append(
            _bet(game, "moneyline", side, None, odds, probability, outcome,
                 min_edge=min_edge, max_juice=max_juice)
        )

    if spread is not None:
        for side, odds_column in (
            ("home", "home_spread_odds"),
            ("away", "away_spread_odds"),
        ):
            odds = getattr(game, odds_column, None)
            if pd.isna(odds):
                continue
            # The two sides of a spread take OPPOSITE handicaps. Deriving both
            # from one number and forgetting to negate produced a market where
            # both sides could win — 147 of 402 games where both were bet —
            # and a +21.6% "edge" over 1,695 bets whose interval excluded zero
            # even after the family correction. The result was extraordinary
            # and extraordinary results in a betting backtest are bugs, which
            # is what the 61.5% cover rate said before anything else did.
            handicap = spread if side == "home" else -spread
            win, push = distribution.spread(handicap, side=side)
            probability = win / (1 - push) if push < 1 else 0.0
            adjusted = (margin if side == "home" else -margin) + handicap
            outcome = "push" if adjusted == 0 else ("won" if adjusted > 0 else "lost")
            out.append(
                _bet(game, "spread", side, handicap, odds, probability, outcome,
                     min_edge=min_edge, max_juice=max_juice)
            )

    if total_line is not None:
        for side, odds_column in (("over", "over_odds"), ("under", "under_odds")):
            odds = getattr(game, odds_column, None)
            if pd.isna(odds):
                continue
            win, push = distribution.total(total_line, side=side)
            probability = win / (1 - push) if push < 1 else 0.0
            outcome = (
                "push"
                if combined == total_line
                else ("won" if (combined > total_line) == (side == "over") else "lost")
            )
            out.append(
                _bet(game, "total_points", side, total_line, odds, probability,
                     outcome, min_edge=min_edge, max_juice=max_juice)
            )
    return [bet for bet in out if bet is not None]


def _bet(game, market, side, line, odds, probability, outcome, *, min_edge, max_juice):
    odds = float(odds)
    if odds < max_juice:
        # Cooper does not lay heavy juice, and the card will not select one on
        # its own. A backtest that ignored that bar would measure a policy
        # nobody would run.
        return None
    edge = probability - american_to_implied(odds)
    if edge < min_edge:
        return None
    profit = (
        profit_on_win(odds) if outcome == "won" else (0.0 if outcome == "push" else -1.0)
    )
    return {
        "game_id": str(game.game_id),
        "season": int(game.season),
        "week": int(game.week),
        "market": market,
        "selection": side,
        "line": line,
        "odds": odds,
        "model_probability": probability,
        "edge": edge,
        "outcome": outcome,
        "profit": profit,
    }


def render(result: BacktestResult) -> str:
    lines: list[str] = []
    add = lines.append
    add("# Does the team model beat the closing line?")
    add("")
    add(
        f"Walk-forward over {result.seasons[0]}-{result.seasons[-1]}, "
        f"{result.games_scored:,} games scored, betting only where the model "
        f"disagrees with the close by at least {result.min_edge:.1%} and the "
        f"price is no worse than {MAX_DEFAULT_JUICE}."
    )
    add("")
    add(
        "**This is a conservative test in two directions at once.** It bets "
        "into the close, which is the sharpest price of the week; and it uses "
        "one consensus line rather than the best of the nine books the "
        "retention probe found quoting these games. A card does neither. So a "
        "positive result here is stronger than it looks, and a negative one "
        "is not proof a card would lose — it is proof the model does not beat "
        "the closing consensus."
    )
    add("")
    add(
        "**Closing-line value cannot be measured here at all**, because the "
        "bet is placed at the close. CLV needs the bought snapshots."
    )
    add("")

    families = max(result.families, 1)
    add("| Market | Bets | Games | Won | Push | ROI | 95% interval | Family-corrected | Verdict |")
    add("|:-------|-----:|------:|----:|-----:|----:|:-------------|:-----------------|:--------|")
    for market in result.markets:
        if not market.bets:
            add(f"| `{market.market}` | 0 | 0 | 0 | 0 | — | — | — | no bets cleared the bar |")
            continue
        # Bonferroni across the markets tested. Crude, and crude in the safe
        # direction: it widens the interval, so it can only make a claim
        # harder to make.
        width = (market.high - market.low) / 2
        widened = width * _bonferroni_factor(families)
        low, high = market.roi - widened, market.roi + widened
        add(
            f"| `{market.market}` | {market.bets:,} | {market.games:,} | "
            f"{market.wins:,} | {market.pushes:,} | {market.roi:+.1%} | "
            f"{market.low:+.1%} to {market.high:+.1%} | "
            f"{low:+.1%} to {high:+.1%} | "
            f"{market.verdict(corrected_low=low, corrected_high=high)} |"
        )
    add("")
    add(
        f"Intervals are clustered by game — the three markets on one game are "
        "one afternoon seen three ways, and a naive per-bet interval over "
        "correlated bets is narrower than the truth. The family correction is "
        f"Bonferroni across the {families} market(s) with enough bets to "
        "report, applied because with three markets something will look "
        "profitable by chance."
    )
    add("")
    add(
        f"**{MINIMUM_BETS} bets** is the minimum declared in advance. Below "
        "it the verdict is *not enough evidence* and not a number, however "
        "good the number looks."
    )
    return "\n".join(lines) + "\n"


def _bonferroni_factor(families: int) -> float:
    """How much wider an interval must be to survive testing `families` of them."""
    from statistics import NormalDist

    if families <= 1:
        return 1.0
    alpha = 0.05 / families
    return NormalDist().inv_cdf(1 - alpha / 2) / 1.96
