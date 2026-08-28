"""Do the prop models disagree with real prices profitably? Measured.

This is what the historical purchase was for. Calibration established that the
distributions are roughly the right shape; it establishes nothing about
whether the market disagrees with them profitably, and this module is the only
thing that can.

## One wager, not nine

A player, a market, a line and a side is **one bet**, quoted by up to nine
books. A card takes the best reachable price. So the rows are collapsed to the
best price per selection before anything is staked — counting each book
separately would multiply one wager by nine, inflate every sample size by
nearly an order of magnitude, and narrow every interval by a factor of three
while measuring nothing new.

Taking the best price is also the **optimistic** reading, and it is chosen
deliberately: if the model cannot beat the best of nine books it certainly
cannot beat the one a card actually reaches.

## What this measures, and what it does not

It measures **the model**. It does not measure a shippable policy, because no
player prop can reach a card at all — inactives are declared ninety minutes
before kickoff and no available feed publishes them. A positive result here
would be evidence that the model is good and that the availability gate is
what blocks shipping, which is exactly the position goalie saves occupies in
the NHL lab.

It also cannot measure closing-line value: these are card-time snapshots, and
CLV needs the closing snapshot too.

## The corrections that make a number readable

Intervals are **clustered by game** — a quarterback's yards, his receiver's
yards and that receiver's longest catch are one afternoon seen three ways, and
a naive per-bet interval over correlated bets is narrower than the truth.

The family-wise correction runs across **every market tested**, because with
twenty markets something will look profitable by chance. Below the minimum
sample declared in advance the verdict is "not enough evidence" and not a
number, however good the number looks.
"""

from __future__ import annotations

import glob
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from statistics import NormalDist

import pandas as pd

from football_betting_lab.config import (
    MAX_DEFAULT_JUICE,
    MAX_DEFAULT_PRICE,
    MIN_PROP_EDGE,
)
from football_betting_lab.forward_evidence import american_to_implied, profit_on_win
from football_betting_lab.leagues import League
from football_betting_lab.markets import MARKETS_BY_KEY
from football_betting_lab.models.player_props import load_play_yardage
from football_betting_lab.providers.odds_api import normalize_event
from football_betting_lab.providers.team_names import name_to_abbreviation, resolve_team
from football_betting_lab.reports.card_pricing import (
    MARKET_SOURCES,
    PlayerBook,
    _player_probability,
)
from football_betting_lab.rosters import Rosters


#: Declared in advance. The detection arithmetic says roughly 600 bets
#: separate a real +8% from zero; below 200 even a large edge is unreadable.
MINIMUM_BETS = 200

#: A market whose interval excludes zero gets these checks before it is
#: allowed to be called anything. They are free, they are run automatically,
#: and none of them can promote a candidate to a finding — only replication on
#: a season the market was not selected on can do that.
FRAGILITY_TOP_GAMES = (1, 3, 5, 10)


def load_bought_prices(cache_dir: Path, league: League) -> pd.DataFrame:
    """Every bought response, normalised. Free: the prices are already paid for."""
    rows: list[dict] = []
    for path in sorted(glob.glob(str(Path(cache_dir) / "*.json"))):
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        rows.extend(normalize_event(payload, league, fetched_at="historical").rows)
    return pd.DataFrame(rows)


def best_price_per_selection(prices: pd.DataFrame) -> pd.DataFrame:
    """Collapse nine books' quotes on one wager into the one a card would take.

    Keyed on everything that makes a bet a different bet — game, market,
    player, side and line — and **not** on the book, which is the whole point.
    """
    if prices.empty:
        return prices
    frame = prices.copy()
    frame["line"] = pd.to_numeric(frame["line"], errors="coerce")
    frame["american_odds"] = pd.to_numeric(frame["american_odds"], errors="coerce")
    frame = frame.dropna(subset=["american_odds"])
    # "Best" is the largest payout, which for American odds is the largest
    # signed number: +150 beats +120 beats -110 beats -200.
    frame = frame.sort_values("american_odds", ascending=False)
    return frame.drop_duplicates(
        subset=["event_id", "market", "player", "selection", "line"], keep="first"
    ).reset_index(drop=True)


@dataclass
class MarketResult:
    market: str
    bets: int = 0
    games: int = 0
    wins: int = 0
    pushes: int = 0
    voids: int = 0
    profit: float = 0.0
    roi: float = 0.0
    low: float = 0.0
    high: float = 0.0

    def verdict(self, *, corrected_low: float, corrected_high: float) -> str:
        if self.bets < MINIMUM_BETS:
            return (
                f"**not enough evidence** — {self.bets} bets, below the "
                f"{MINIMUM_BETS} declared in advance"
            )
        if corrected_low <= 0.0 <= corrected_high:
            return "**no demonstrated edge**"
        return "interval excludes zero, " + (
            "positive" if corrected_low > 0 else "negative"
        )


@dataclass
class BacktestResult:
    season: int
    events: int = 0
    priced_rows: int = 0
    collapsed_rows: int = 0
    markets: list[MarketResult] = field(default_factory=list)
    bets: pd.DataFrame = field(default_factory=pd.DataFrame)
    min_edge: float = MIN_PROP_EDGE
    unresolved_players: int = 0

    @property
    def families(self) -> int:
        return sum(1 for market in self.markets if market.bets >= MINIMUM_BETS)

    @property
    def pooled(self) -> MarketResult:
        pooled = MarketResult(market="all markets pooled")
        if self.bets.empty:
            return pooled
        staked = self.bets[self.bets["outcome"] != "void"]
        pooled.bets = len(staked)
        pooled.wins = int((staked["outcome"] == "won").sum())
        pooled.pushes = int((staked["outcome"] == "push").sum())
        pooled.voids = int((self.bets["outcome"] == "void").sum())
        pooled.profit = float(staked["profit"].sum())
        per_game = staked.groupby("event_id").agg(
            profit=("profit", "sum"), bets=("profit", "size")
        )
        pooled.games = len(per_game)
        pooled.roi, pooled.low, pooled.high = _interval(per_game)
        return pooled


def _interval(per_game: pd.DataFrame) -> tuple[float, float, float]:
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


def run(
    prices: pd.DataFrame,
    logs: pd.DataFrame,
    league: League,
    *,
    season: int,
    raw_dir: Path,
    processed_dir: Path,
    min_edge: float = MIN_PROP_EDGE,
    draws: int = 8_000,
) -> BacktestResult:
    result = BacktestResult(season=season, min_edge=min_edge)
    if prices.empty:
        return result
    result.priced_rows = len(prices)
    collapsed = best_price_per_selection(prices)
    collapsed = collapsed[
        collapsed["market"].map(lambda key: key in MARKET_SOURCES)
    ].copy()
    result.collapsed_rows = len(collapsed)
    result.events = collapsed["event_id"].nunique()
    if collapsed.empty:
        return result

    # Map each priced event to the season-week it belongs to, so the fit can
    # be walk-forward. Without it the model would be fitted on the season it
    # is pricing, which is not a backtest.
    game_week = _game_weeks(logs, collapsed, league, season)
    per_play = load_play_yardage(processed_dir)
    rosters = Rosters.load(league, raw_dir, season=season)
    lookup = name_to_abbreviation(league)

    books: dict[int, PlayerBook] = {}
    rows: list[dict] = []
    for event_id, frame in collapsed.groupby("event_id"):
        week = game_week.get(str(event_id))
        if week is None or week <= 1:
            # Week 1 has no in-season history, and the fit would be last
            # season's alone. Excluded and counted rather than priced badly.
            continue
        if week not in books:
            books[week] = PlayerBook(
                logs, per_play, before=f"{season}{week:02d}", draws=draws
            )
        book = books[week]
        first = frame.iloc[0]
        home = resolve_team(first["home_team"], league, lookup) or ""
        away = resolve_team(first["away_team"], league, lookup) or ""
        game_id = _game_id(logs, season, week, home, away)

        for row in frame.itertuples():
            resolution = rosters.resolve(row.player, home=home, away=away)
            if not resolution.resolved:
                result.unresolved_players += 1
                continue
            probability = _player_probability(
                book, resolution.entry.player_id, row.market, row.selection, row.line
            )
            if probability is None:
                continue
            odds = float(row.american_odds)
            if odds < MAX_DEFAULT_JUICE or odds > MAX_DEFAULT_PRICE:
                continue
            edge = probability - american_to_implied(odds)
            if edge < min_edge:
                continue
            outcome, actual = _settle(logs, game_id, row)
            rows.append(
                {
                    "event_id": str(event_id),
                    "week": week,
                    "market": row.market,
                    "player": row.player,
                    "selection": row.selection,
                    "line": row.line,
                    "odds": odds,
                    "model_probability": probability,
                    "edge": edge,
                    "outcome": outcome,
                    "actual": actual,
                    "profit": (
                        profit_on_win(odds)
                        if outcome == "won"
                        else (-1.0 if outcome == "lost" else 0.0)
                    ),
                }
            )

    result.bets = pd.DataFrame(rows)
    if result.bets.empty:
        return result

    for market in sorted(result.bets["market"].unique()):
        subset = result.bets[
            (result.bets["market"] == market) & (result.bets["outcome"] != "void")
        ]
        entry = MarketResult(market=market, bets=len(subset))
        entry.voids = int(
            ((result.bets["market"] == market) & (result.bets["outcome"] == "void")).sum()
        )
        if not subset.empty:
            entry.wins = int((subset["outcome"] == "won").sum())
            entry.pushes = int((subset["outcome"] == "push").sum())
            entry.profit = float(subset["profit"].sum())
            per_game = subset.groupby("event_id").agg(
                profit=("profit", "sum"), bets=("profit", "size")
            )
            entry.games = len(per_game)
            entry.roi, entry.low, entry.high = _interval(per_game)
        result.markets.append(entry)
    return result


def _game_weeks(
    logs: pd.DataFrame, prices: pd.DataFrame, league: League, season: int
) -> dict[str, int]:
    """Which season-week each priced event belongs to."""
    lookup = name_to_abbreviation(league)
    index: dict[tuple[str, str], int] = {}
    for row in logs[logs["season"] == season].itertuples():
        parts = str(row.game_id).split("_")
        if len(parts) == 4:
            index[(parts[2], parts[3])] = int(row.week)
    weeks: dict[str, int] = {}
    for event_id, frame in prices.groupby("event_id"):
        first = frame.iloc[0]
        home = resolve_team(first["home_team"], league, lookup)
        away = resolve_team(first["away_team"], league, lookup)
        week = index.get((str(away), str(home)))
        if week is not None:
            weeks[str(event_id)] = week
    return weeks


def _game_id(logs: pd.DataFrame, season: int, week: int, home: str, away: str) -> str:
    return f"{season}_{week:02d}_{away}_{home}"


def _settle(logs: pd.DataFrame, game_id: str, row) -> tuple[str, float | None]:
    market = MARKETS_BY_KEY.get(row.market)
    if market is None or row.market not in logs.columns:
        return "void", None
    entries = logs[
        (logs["game_id"].astype(str) == game_id)
        & (logs["player_name"].astype(str).str.casefold() == str(row.player).casefold())
    ]
    if entries.empty:
        # He did not dress, or did not appear in the box score. The stake
        # comes back; it is not a loss.
        return "void", None
    actual = float(entries.iloc[0][row.market])
    line = float(row.line)
    if actual == line:
        return "push", actual
    over = actual > line
    if row.selection == "over":
        return ("won" if over else "lost"), actual
    return ("lost" if over else "won"), actual


@dataclass
class Fragility:
    """Whether a non-zero interval survives the obvious ways to break it."""

    market: str
    first_half: float = 0.0
    second_half: float = 0.0
    first_half_bets: int = 0
    second_half_bets: int = 0
    without_best_game: float = 0.0
    top_game_share: float = 0.0
    top_ten_share: float = 0.0
    players: int = 0
    games: int = 0

    @property
    def halves_agree(self) -> bool:
        """Both halves the same sign and within a factor of two."""
        if self.first_half * self.second_half <= 0:
            return False
        ratio = abs(self.first_half / self.second_half)
        return 0.5 <= ratio <= 2.0


def fragility(bets: pd.DataFrame, market: str) -> Fragility:
    """Break the result the obvious ways and report what survives.

    None of this can turn a candidate into a finding. A result that survives
    every check is still one season, and the brief is explicit: **replication
    on a season the market was not selected on** is what a claim needs. These
    checks only rule out the cheap explanations — a hot fortnight, one absurd
    afternoon, one player.
    """
    subset = bets[(bets["market"] == market) & (bets["outcome"] != "void")]
    result = Fragility(market=market)
    if subset.empty:
        return result
    result.games = int(subset["event_id"].nunique())
    result.players = int(subset["player"].nunique())

    midpoint = subset["week"].median()
    for label, half in (
        ("first", subset[subset["week"] <= midpoint]),
        ("second", subset[subset["week"] > midpoint]),
    ):
        roi = float(half["profit"].sum() / len(half)) if len(half) else 0.0
        setattr(result, f"{label}_half", roi)
        setattr(result, f"{label}_half_bets", len(half))

    per_game = subset.groupby("event_id")["profit"].sum().sort_values(ascending=False)
    total = float(per_game.sum())
    if total:
        result.top_game_share = float(per_game.head(1).sum() / total)
        result.top_ten_share = float(per_game.head(10).sum() / total)
    without = subset[subset["event_id"] != per_game.index[0]]
    if len(without):
        result.without_best_game = float(without["profit"].sum() / len(without))
    return result


def _bonferroni_factor(families: int) -> float:
    if families <= 1:
        return 1.0
    return NormalDist().inv_cdf(1 - (0.05 / families) / 2) / 1.96


def render(result: BacktestResult) -> str:
    lines: list[str] = []
    add = lines.append
    add(f"# Do the prop models beat real prices? — {result.season}")
    add("")
    add(
        f"{result.priced_rows:,} bought price rows across {result.events} "
        f"events, collapsed to {result.collapsed_rows:,} distinct wagers — "
        "one player, market, line and side is **one bet**, quoted by up to "
        "nine books, and a card takes the best reachable price. Counting each "
        "book separately would multiply one wager by nine and narrow every "
        "interval by a factor of three while measuring nothing new."
    )
    add("")
    add(
        f"Betting only where the model disagrees by at least "
        f"{result.min_edge:.1%} at a price between {MAX_DEFAULT_JUICE} and "
        f"+{MAX_DEFAULT_PRICE}. Week 1 is excluded: it has no in-season "
        "history, so the fit would be last season's alone."
    )
    add("")
    add(
        "**This measures the model, not a shippable policy.** No player prop "
        "can reach a card at all — inactives are declared ninety minutes "
        "before kickoff and no available feed publishes them. A positive "
        "result here would be evidence that the model is good and that the "
        "availability gate is what blocks shipping."
    )
    add("")
    add(
        "**Closing-line value cannot be measured here.** These are card-time "
        "snapshots; CLV needs the closing snapshot too."
    )

    if result.bets.empty:
        add("")
        add("**No bet cleared the bar.** No number is offered in its place.")
        return "\n".join(lines) + "\n"

    families = max(result.families, 1)
    factor = _bonferroni_factor(families)
    add("")
    add("| Market | Bets | Games | Won | Push | Void | ROI | 95% interval | Family-corrected | Verdict |")
    add("|:-------|-----:|------:|----:|-----:|-----:|----:|:-------------|:-----------------|:--------|")

    def row(entry: MarketResult) -> str:
        if not entry.bets:
            return (
                f"| `{entry.market}` | 0 | 0 | 0 | 0 | {entry.voids} | — | — | "
                "— | no bets cleared the bar |"
            )
        width = (entry.high - entry.low) / 2 * factor
        low, high = entry.roi - width, entry.roi + width
        return (
            f"| `{entry.market}` | {entry.bets:,} | {entry.games:,} | "
            f"{entry.wins:,} | {entry.pushes:,} | {entry.voids:,} | "
            f"{entry.roi:+.1%} | {entry.low:+.1%} to {entry.high:+.1%} | "
            f"{low:+.1%} to {high:+.1%} | "
            f"{entry.verdict(corrected_low=low, corrected_high=high)} |"
        )

    for entry in sorted(result.markets, key=lambda m: -m.bets):
        add(row(entry))
    pooled = result.pooled
    add(row(pooled).replace(f"`{pooled.market}`", f"**{pooled.market}**"))
    add("")
    add(
        f"The family correction is Bonferroni across the {families} market(s) "
        f"with at least {MINIMUM_BETS} bets, applied because with twenty "
        "markets something will look profitable by chance. Intervals are "
        "clustered by game: the props on one afternoon are not independent."
    )
    if result.unresolved_players:
        add("")
        add(
            f"{result.unresolved_players:,} priced rows named a player who "
            "could not be resolved on that season's roster, and produced no "
            "opinion. Reported rather than guessed at: a fuzzy match produces "
            "a confident price for a bet nobody placed."
        )
    interesting = [
        entry
        for entry in result.markets
        if entry.bets >= MINIMUM_BETS
        and not (
            entry.roi - (entry.high - entry.low) / 2 * factor
            <= 0
            <= entry.roi + (entry.high - entry.low) / 2 * factor
        )
    ]
    if interesting:
        add("")
        add("## Markets whose interval excludes zero, and whether they survive")
        add("")
        add(
            "**None of what follows can make a candidate a finding.** A "
            "result that survives every check below is still one season, and "
            "the standard is replication on a season the market was not "
            "selected on. These checks only rule out the cheap explanations: "
            "a hot fortnight, one absurd afternoon, one player."
        )
        add("")
        add("| Market | ROI | First half | Second half | Halves agree | Top game | Top 10 games | Without the best game | Players |")
        add("|:-------|----:|-----------:|------------:|:-------------|---------:|-------------:|----------------------:|--------:|")
        for entry in interesting:
            check = fragility(result.bets, entry.market)
            add(
                f"| `{entry.market}` | {entry.roi:+.1%} | "
                f"{check.first_half:+.1%} ({check.first_half_bets}) | "
                f"{check.second_half:+.1%} ({check.second_half_bets}) | "
                f"{'yes' if check.halves_agree else '**no**'} | "
                f"{check.top_game_share:.0%} | {check.top_ten_share:.0%} | "
                f"{check.without_best_game:+.1%} | {check.players} |"
            )
        add("")
        add(
            "A result carried by one afternoon shows up as a large top-game "
            "share and collapses when it is removed. A result that is really "
            "one player shows up in the player count."
        )
        add("")
        add(
            "**What would settle it: a second season, bought and scored the "
            "same way.** That is roughly 99,000 credits — a credit-spend "
            "decision, and therefore Cooper's."
        )
    add("")
    add(
        "A void is a player who never appeared in the box score. The stake "
        "comes back; it is not a loss, and it is excluded from the return "
        "rather than counted as a zero."
    )
    return "\n".join(lines) + "\n"
