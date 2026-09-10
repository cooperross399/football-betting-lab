"""Where do the metrics disagree with the line, and has that ever been worth it?

The board sets metrics beside a price. That is not the same as asking where the
price is wrong, and the difference is the whole question: a matchup read that
agrees with the line is worth nothing, and one that disagrees is worth
something only if the disagreement has historically pointed the right way.

So this builds a rating out of the metrics that survived the reliability screen,
turns it into a predicted margin and total, and subtracts the market's own
number. **The divergence is the object of interest, not the prediction.**

## Every part of it is fitted on games that had already been played

A rating comes from a club's prior games only. The mapping from rating to
points is refitted for each season on the seasons before it. Nothing here sees
the game it is pricing, and nothing sees the rest of the week it is in — a
sixteen-game Sunday would otherwise leak fifteen results into the sixteenth.

## Why the line is the right control and the result is not

Predicting the margin well is easy and worthless: the line already does it. The
only thing that matters is whether the residual — what the metrics say *beyond*
the line — carries anything. That is why the bet here is on the divergence and
never on the prediction, and why the null result to expect is "the market
already knows this", not "the metrics are wrong".
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

#: The metrics the reliability screen left standing, and the side they are read
#: from. A club's offence is rated on what it did; its defence on what it
#: allowed. Weights come from the screen, not from taste.
RATING_METRICS: tuple[tuple[str, str], ...] = (
    ("epa_dropback", "offence"),
    ("epa_rush", "offence"),
    ("success_pass", "offence"),
    ("success_rush", "offence"),
    ("epa_dropback", "defence"),
    ("epa_rush", "defence"),
    ("success_pass", "defence"),
    ("success_rush", "defence"),
)

#: Games of history a rating is built from. Seventeen is one season, which is
#: also the shrinkage prior the scoring model uses, so the two agree about how
#: much a club's own record is worth.
LOOKBACK_GAMES = 17


@dataclass(frozen=True)
class Scan:
    frame: pd.DataFrame
    trained_on: int


def club_form(long: pd.DataFrame) -> pd.DataFrame:
    """Trailing form per club per game-week, from games strictly earlier.

    Built by expanding through the season in kickoff order, so the value
    attached to a week is what was knowable the morning of it.
    """
    wanted = long[
        long.set_index(["metric", "side"]).index.isin(RATING_METRICS)
    ].copy()
    wanted["column"] = wanted["metric"] + "_" + wanted["side"]
    wanted = wanted.sort_values(["team", "season", "week"])
    rows = []
    for (team, column), group in wanted.groupby(["team", "column"], sort=False):
        group = group.sort_values(["season", "week"])
        weighted = group["value"] * group["weight"]
        # Shift first: a club-week must never contribute to its own rating.
        prior_value = weighted.shift(1).rolling(LOOKBACK_GAMES, min_periods=4).sum()
        prior_weight = group["weight"].shift(1).rolling(LOOKBACK_GAMES, min_periods=4).sum()
        rows.append(pd.DataFrame({
            "team": team, "column": column,
            "season": group["season"], "week": group["week"],
            "form": prior_value / prior_weight,
        }))
    expected = sorted({f"{metric}_{side}" for metric, side in RATING_METRICS})
    if not rows:
        return pd.DataFrame(columns=["team", "season", "week", *expected])
    form = pd.concat(rows, ignore_index=True)
    wide = form.pivot_table(
        index=["team", "season", "week"], columns="column", values="form",
        dropna=False,
    ).reset_index()
    # Early in a season every club's form is NaN, and `pivot_table` drops a
    # column that is entirely empty. Left alone, `scan` then fails on a missing
    # column with a KeyError that says nothing about the real cause, which is
    # simply that no club has played enough yet.
    for column in expected:
        if column not in wide.columns:
            wide[column] = np.nan
    return wide[["team", "season", "week", *expected]]


def _design(games: pd.DataFrame, columns: list[str]) -> np.ndarray:
    """Home minus away on every rating column, plus an intercept."""
    home = games[[f"home_{c}" for c in columns]].to_numpy(float)
    away = games[[f"away_{c}" for c in columns]].to_numpy(float)
    return np.column_stack([np.ones(len(games)), home - away])


def _design_total(games: pd.DataFrame, columns: list[str]) -> np.ndarray:
    """Home plus away: a total is about how much both sides do, not who wins."""
    home = games[[f"home_{c}" for c in columns]].to_numpy(float)
    away = games[[f"away_{c}" for c in columns]].to_numpy(float)
    return np.column_stack([np.ones(len(games)), home + away])


def scan(games: pd.DataFrame, form: pd.DataFrame) -> Scan:
    """Predicted margin and total against the market's own, walk-forward.

    The mapping is refitted for every season on the seasons before it, so the
    first season with any history is the first that can be scored.
    """
    columns = sorted({f"{m}_{s}" for m, s in RATING_METRICS})
    merged = games.copy()
    for side in ("home", "away"):
        joined = form.rename(columns={c: f"{side}_{c}" for c in columns})
        merged = merged.merge(
            joined.rename(columns={"team": f"{side}_team"}),
            on=[f"{side}_team", "season", "week"], how="left",
        )
    merged = merged.dropna(subset=[f"{side}_{c}" for side in ("home", "away") for c in columns])
    merged = merged.dropna(subset=["result", "total", "spread_line", "total_line"])
    if merged.empty:
        return Scan(merged, 0)

    out, trained = [], 0
    for season in sorted(merged["season"].unique()):
        history = merged[merged["season"] < season]
        current = merged[merged["season"] == season]
        if len(history) < 200:
            continue
        trained = max(trained, len(history))
        margin = np.linalg.lstsq(
            _design(history, columns), history["result"].to_numpy(float), rcond=None
        )[0]
        total = np.linalg.lstsq(
            _design_total(history, columns), history["total"].to_numpy(float), rcond=None
        )[0]
        priced = current.copy()
        priced["model_margin"] = _design(current, columns) @ margin
        priced["model_total"] = _design_total(current, columns) @ total
        out.append(priced)
    if not out:
        return Scan(merged.iloc[0:0], 0)
    frame = pd.concat(out, ignore_index=True)
    # The market's spread is quoted from the home side, same as `result`.
    frame["margin_divergence"] = frame["model_margin"] - frame["spread_line"]
    frame["total_divergence"] = frame["model_total"] - frame["total_line"]
    return Scan(frame, trained)


def settle(frame: pd.DataFrame, *, threshold: float, price: int = -110) -> pd.DataFrame:
    """Bet the side the divergence points at, at a realistic price.

    A push returns the stake. `-110` is the standard two-sided quote and is
    stated rather than assumed away: at a fair price every result here would
    be about four points better and none of them would be a strategy.
    """
    stake_return = 100.0 / abs(price)
    rows = []
    for kind, prediction, line, actual in (
        ("spread", "model_margin", "spread_line", "result"),
        ("total", "model_total", "total_line", "total"),
    ):
        part = frame[(frame[prediction] - frame[line]).abs() >= threshold].copy()
        if part.empty:
            continue
        side = np.sign(part[prediction] - part[line])
        edge = (part[actual] - part[line]) * side
        part["profit"] = np.where(edge > 0, stake_return, np.where(edge < 0, -1.0, 0.0))
        part["market"] = kind
        rows.append(part[["season", "game_id", "market", "profit"]])
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
