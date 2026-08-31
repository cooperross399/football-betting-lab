"""Per-market probability calibration, fitted offline and frozen for the card.

The model is overconfident everywhere it was measured: it says 0.861 and the
outcome lands 0.547, against a market that says 0.523 and is within two points
of the truth in every bucket. Walk-forward isotonic calibration closes most of
that gap — it cut 2025 from -5.97% to -3.69% — and never crosses it. So this is
a **forecasting improvement, not an edge**, and nothing here should be read as
one.

It is built anyway, and built before Week 1, for a reason that has nothing to do
with profit: **a calibrated probability cannot be back-dated.** The forward
ledger freezes what was believed before kickoff. If the calibrated number is not
frozen alongside the raw one from the first game day, the 2026 season can never
be scored on it, and the bought population is complete so there is no other
source. A season's worth of evidence is lost by omission rather than by error.

The map is fitted on **seasons strictly before** the one being priced, the same
rule the rest of the lab applies, and it is fitted **per market**: a pooled map
would import one market's miscalibration into another's price.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

#: Rows a market needs before it gets a map of its own. Below this the fit is a
#: step function through noise, and it would flatter the model by memorising
#: its earlier mistakes rather than correcting them.
MINIMUM_ROWS = 300

#: Knots kept per market. The isotonic fit produces one step per observation;
#: storing every one would put tens of thousands of points in the artifact for
#: no accuracy, so it is thinned to a grid the card can interpolate.
KNOTS = 64

#: Never returned by a calibrated map. A forecast of 0 or 1 is infinitely
#: punished by any proper score, and a step fit will happily produce one from a
#: bucket that went nought for eight.
FLOOR, CEILING = 0.01, 0.99


@dataclass(frozen=True)
class MarketCalibration:
    """One market's monotone map from model probability to observed rate."""

    market: str
    rows: int
    seasons: tuple[int, ...]
    x: tuple[float, ...]
    y: tuple[float, ...]

    def apply(self, probability: float) -> float:
        if not self.x:
            return float(np.clip(probability, FLOOR, CEILING))
        if self.x[0] == self.x[-1]:
            # A model that says the same number every time gives the fit no
            # increasing x to walk along. The honest answer there is the pooled
            # outcome rate, not whatever an interpolator returns.
            return float(np.clip(float(np.mean(self.y)), FLOOR, CEILING))
        return float(
            np.clip(np.interp(float(probability), self.x, self.y), FLOOR, CEILING)
        )


@dataclass(frozen=True)
class Calibration:
    """Every market's map, plus what it was fitted on."""

    fitted_on: str
    markets: dict[str, MarketCalibration]

    def apply(self, market: str, probability: float) -> float | None:
        """The calibrated probability, or None when this market has no map.

        **None, never the raw probability.** A market with no map and a market
        that calibrates to itself must not look the same in the ledger: one is
        a measurement and the other is an absence, and a silent fallback would
        make a season of uncalibrated rows indistinguishable from calibrated
        ones a year later, when nobody remembers which markets had maps.
        """
        entry = self.markets.get(str(market))
        return None if entry is None else entry.apply(float(probability))


def _isotonic(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Pool-adjacent-violators, sorted by `x`."""
    order = np.argsort(x, kind="mergesort")
    xs = np.asarray(x, dtype=float)[order]
    ys = np.asarray(y, dtype=float)[order]
    values: list[float] = []
    weights: list[float] = []
    for point in ys:
        values.append(float(point))
        weights.append(1.0)
        while len(values) > 1 and values[-2] > values[-1]:
            merged = (values[-1] * weights[-1] + values[-2] * weights[-2]) / (
                weights[-1] + weights[-2]
            )
            weight = weights[-1] + weights[-2]
            values[-2:] = [merged]
            weights[-2:] = [weight]
    fitted = np.repeat(values, [int(round(w)) for w in weights])
    return xs, fitted


def _thin(xs: np.ndarray, ys: np.ndarray, knots: int = KNOTS) -> tuple[list, list]:
    if len(xs) <= knots:
        return [float(v) for v in xs], [float(v) for v in ys]
    idx = np.linspace(0, len(xs) - 1, knots).round().astype(int)
    return [float(xs[i]) for i in idx], [float(ys[i]) for i in idx]


def fit(bets: pd.DataFrame, *, before_season: int | None = None) -> Calibration:
    """Fit one map per market from settled bets.

    `before_season` keeps the rule the rest of the lab keeps: a map applied to
    2026 is fitted on 2025 and earlier, never on the season it scores.
    """
    frame = bets[bets["outcome"] != "void"].copy()
    if before_season is not None:
        frame = frame[frame["season"].astype(int) < int(before_season)]
    if frame.empty:
        return Calibration(fitted_on="nothing", markets={})
    frame["won"] = (frame["outcome"] == "won").astype(float)
    seasons = tuple(sorted({int(s) for s in frame["season"].dropna().unique()}))

    markets: dict[str, MarketCalibration] = {}
    for market, rows in frame.groupby("market"):
        if len(rows) < MINIMUM_ROWS:
            continue
        xs, ys = _isotonic(
            rows["model_probability"].to_numpy(), rows["won"].to_numpy()
        )
        x, y = _thin(xs, ys)
        markets[str(market)] = MarketCalibration(
            market=str(market),
            rows=len(rows),
            seasons=seasons,
            x=tuple(x),
            y=tuple(y),
        )
    span = f"{seasons[0]}-{seasons[-1]}" if seasons else "nothing"
    return Calibration(fitted_on=span, markets=markets)


def save(calibration: Calibration, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "fitted_on": calibration.fitted_on,
                "markets": {
                    name: {
                        "rows": entry.rows,
                        "seasons": list(entry.seasons),
                        "x": list(entry.x),
                        "y": list(entry.y),
                    }
                    for name, entry in sorted(calibration.markets.items())
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def load(path: Path) -> Calibration | None:
    """The frozen maps, or None when there are none.

    None rather than an empty Calibration, so a caller cannot mistake "no
    artifact on disk" for "every market calibrates to itself".
    """
    if not Path(path).is_file():
        return None
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    markets = {
        name: MarketCalibration(
            market=name,
            rows=int(entry.get("rows", 0)),
            seasons=tuple(int(s) for s in entry.get("seasons", [])),
            x=tuple(float(v) for v in entry.get("x", [])),
            y=tuple(float(v) for v in entry.get("y", [])),
        )
        for name, entry in payload.get("markets", {}).items()
    }
    return Calibration(fitted_on=str(payload.get("fitted_on", "")), markets=markets)
