"""Is the model a better forecaster than the market it bets into?

Every other instrument here asks whether a return is real. This one asks the
question underneath, and it is the cleaner question: it needs no settlement
rule, no vig assumption and no minimum-edge threshold — just a probability, an
outcome, and the price's own implied probability.

A model that loses money might be unlucky. **A model with a worse Brier score
than the market is not unlucky, it is uninformed**, and no betting rule,
subgroup or filter can rescue it, because every wager it places is an opinion
worse than the price it pays for.
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from football_betting_lab.reports.settlement_agreement import suspects_and_screened

def settlement_suspects(report_path) -> set[str]:
    """Markets to exclude, read from the settlement screen's own output.

    This was a module constant naming `tackles_assists`, and the constant was
    true when it was written and false a day later: the market was flagged
    because our tackle column dropped `def_tackles_with_assist` and undercounted
    by 7%, and once that was fixed the screen cleared it. A hardcoded exclusion
    cannot notice that. Scoring a forecast against outcomes that are not the
    quantity the books settled measures the gap rather than the skill — but so
    does excluding a market that no longer has a gap.

    A missing report is an error rather than an empty set: "nothing is
    excluded" and "nothing was screened" must not look the same.
    """
    path = pathlib.Path(report_path)
    if not path.is_file():
        raise FileNotFoundError(
            f"No settlement screen at {path}. Run "
            "scripts/run_settlement_agreement.py first: without it nothing "
            "here knows which markets settle on what they were priced on."
        )
    suspects, _ = suspects_and_screened(path.read_text(encoding="utf-8"))
    return suspects


def implied(odds: pd.Series) -> np.ndarray:
    """The price's own probability, vig included.

    Vig makes this an over-estimate, which biases the comparison **in the
    model's favour**: the market is being scored with a handicap. A model that
    still loses on Brier has lost the argument twice.
    """
    value = odds.astype(float).to_numpy()
    # Both branches of np.where are evaluated, so the unused one must still be
    # safe to compute: at odds of exactly -100 the positive branch divides by
    # zero and warns, even though its result is discarded.
    negative = np.where(value < 0, value, -100.0)
    positive = np.where(value < 0, 100.0, value)
    return np.where(
        value < 0,
        -negative / (-negative + 100.0),
        100.0 / (positive + 100.0),
    )


def isotonic_fit(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Pool-adjacent-violators, sorted by `x`.

    Hand-rolled because the venv has no scikit-learn and one honest
    implementation of a monotone step fit is smaller than the dependency.
    """
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


def apply_map(xs: np.ndarray, fitted: np.ndarray, query: pd.Series) -> np.ndarray:
    return np.clip(np.interp(query.astype(float).to_numpy(), xs, fitted), 0.01, 0.99)


def brier(probability: np.ndarray, won: np.ndarray) -> float:
    return float(np.mean((probability - won) ** 2))


@dataclass
class SeasonSkill:
    """One held-out season, scored three ways."""

    season: int
    bets: int
    model_brier: float
    calibrated_brier: float
    market_brier: float

    @property
    def beats_the_price(self) -> bool:
        """Necessary for an edge, and nowhere near sufficient."""
        return self.calibrated_brier < self.market_brier


@dataclass
class SkillResult:
    bets: int = 0
    model_brier: float = 0.0
    market_brier: float = 0.0
    seasons: list[SeasonSkill] = field(default_factory=list)

    @property
    def ever_beats_the_price(self) -> bool:
        return any(s.beats_the_price for s in self.seasons)


def measure(bets: pd.DataFrame) -> SkillResult:
    """Score the model, its walk-forward calibration, and the price."""
    if bets.empty:
        return SkillResult()
    frame = bets.copy()
    frame["won"] = (frame["outcome"] == "won").astype(float)
    frame["market_probability"] = implied(frame["odds"])
    result = SkillResult(
        bets=len(frame),
        model_brier=brier(
            frame["model_probability"].to_numpy(), frame["won"].to_numpy()
        ),
        market_brier=brier(
            frame["market_probability"].to_numpy(), frame["won"].to_numpy()
        ),
    )
    seasons = sorted(int(s) for s in frame["season"].dropna().unique())
    for season in seasons[1:]:
        prior = frame[frame["season"] < season]
        current = frame[frame["season"] == season]
        if prior.empty or current.empty:
            continue
        xs, fitted = isotonic_fit(
            prior["model_probability"].to_numpy(), prior["won"].to_numpy()
        )
        calibrated = apply_map(xs, fitted, current["model_probability"])
        won = current["won"].to_numpy()
        result.seasons.append(
            SeasonSkill(
                season=season,
                bets=len(current),
                model_brier=brier(current["model_probability"].to_numpy(), won),
                calibrated_brier=brier(calibrated, won),
                market_brier=brier(current["market_probability"].to_numpy(), won),
            )
        )
    return result


def render(result: SkillResult, bets: pd.DataFrame, *, coverage: str = "") -> str:
    """The report, whose last paragraph is the finding."""
    lines: list[str] = []
    add = lines.append
    add("# Does the model know anything the price does not?")
    add("")
    if coverage:
        add(coverage)
        add("")
    add(
        "Every other instrument here asks whether a return is real. This one "
        "asks the question underneath. A model that loses money might be "
        "unlucky; **a model with a worse Brier score than the market is not "
        "unlucky, it is uninformed** — and no betting rule, subgroup or filter "
        "can rescue it, because every wager it places is an opinion worse than "
        "the price it pays for."
    )
    add("")
    add(
        "The market's implied probability **includes the vig**, so it is an "
        "over-estimate and it is being scored with a handicap. The comparison "
        "is tilted in the model's favour throughout."
    )
    add("")
    if not bets.empty:
        frame = bets.copy()
        frame["won"] = (frame["outcome"] == "won").astype(float)
        frame["market_probability"] = implied(frame["odds"])
        add("## Is the model's probability honest?")
        add("")
        buckets = pd.cut(
            frame["model_probability"],
            [0, 0.35, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.8, 1.0],
        )
        add(
            "| Model says | Bets | Actually happens | Market says | "
            "Model error | Market error |"
        )
        add("|:---|---:|---:|---:|---:|---:|")
        for bucket, group in frame.groupby(buckets, observed=True):
            add(
                f"| {bucket} | {len(group):,} | {group['won'].mean():.3f} | "
                f"{group['market_probability'].mean():.3f} | "
                f"{group['won'].mean() - group['model_probability'].mean():+.3f} | "
                f"{group['won'].mean() - group['market_probability'].mean():+.3f} |"
            )
        add("")
    add(
        f"**Brier: model {result.model_brier:.5f}, market "
        f"{result.market_brier:.5f}** over {result.bets:,} bets. Lower is better."
    )
    add("")
    add("## Walk-forward calibration")
    add("")
    add(
        "The map is fitted on prior seasons only. A calibration fitted on the "
        "season it scores is not a forecast, it is a description."
    )
    add("")
    add(
        "| Season | Bets | Model Brier | **Calibrated** Brier | Market Brier | "
        "Better than the price? |"
    )
    add("|:---|---:|---:|---:|---:|:---|")
    for entry in result.seasons:
        add(
            f"| {entry.season} | {entry.bets:,} | {entry.model_brier:.5f} | "
            f"**{entry.calibrated_brier:.5f}** | {entry.market_brier:.5f} | "
            f"{'**yes**' if entry.beats_the_price else 'no'} |"
        )
    add("")
    if result.seasons and not result.ever_beats_the_price:
        add(
            "**The model is never a better forecaster than the price, on any "
            "held-out season, even after calibration and even with the vig "
            "handicapping the market.** That is the whole answer. The problem "
            "is not the betting rule, the threshold or the choice of market: "
            "there is no information here that the price does not already "
            "carry, so there is no subgroup of it that can be profitable "
            "except by chance."
        )
        add("")
        add(
            "Calibration is still worth having — it cuts the loss materially "
            "— but a smaller loss is not a profit, and this table is the "
            "reason no filter will turn one into the other."
        )
    elif result.seasons:
        add(
            "**The calibrated model beats the price on at least one held-out "
            "season.** That is necessary for an edge and nowhere near "
            "sufficient: it must beat it by more than the vig, and on a season "
            "it was not selected on. Take it to the priced test, which decides."
        )
    else:
        add(
            "**No season could be scored**, because calibration needs a prior "
            "season to fit on. That is an absence, not a result."
        )
    add("")
    add(
        "Calibration can rule a model out and never rule one in. Where this "
        "report rules one out, it is decisive; where it does not, it has only "
        "failed to."
    )
    return "\n".join(lines) + "\n"
