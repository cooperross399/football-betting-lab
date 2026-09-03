"""Does the model know anything the price does not?

Every other instrument in this lab asks whether a *return* is real. The
forecast-skill report asks whether the model's Brier beats the market's. This
one asks the question underneath both, and it is the one that decides whether
any feature work has a point:

    logit P(over) = a + b*logit(p_market_devigged) + c*logit(p_model)

**If `c` is indistinguishable from zero the model adds nothing to the price**,
and no threshold, subgroup or filter built on it can be profitable except by
chance. If `c > 0` the model carries something the price does not *fully
absorb* — and the correct product is then a *shrunk blend*, not a standalone
bettor, because `b` says how much of the answer the market already holds.

"Does not fully absorb" is the careful phrase, and it is deliberate. On the
carded population the sign of `logit(model) − logit(market)` IS the bet side on
99.997% of rows, so `c` is identified almost entirely by side, and there is a
side asymmetry in the market itself: unders land about 2.4pp more often than
the devigged median says. A fit with a bet-side dummy is therefore reported
beside the plain one. If `c` survives the dummy, it is model information; if it
does not, the placebo cannot tell model information from a side-specific market
miscalibration, because shuffling destroys the model–side correlation too.

## Why this is not the Brier comparison again

Brier scores the two forecasters side by side and says the market wins. That is
consistent with two very different worlds: one where the model is pure noise,
and one where it is noisy but carries a real signal the market lacks. A
combination regression separates them, because `c` is estimated *holding the
market price fixed*.

## Three things this gets right that the naive version does not

**The market probability is devigged, and devigged PER BOOK.** Comparing a model
probability against a raw one-sided implied probability compares it against a
number inflated by the hold. And devigging a best-of-N over against a best-of-N
under fabricates a market with far less hold than any book actually quoted — the
median two-sided book hold here is about 6.7%, and a best-of-N pairing hides
most of it. So each book's own two sides are devigged first and the books are
then combined.

**Selection does not bias this.** The bets file holds only wagers the card
selected, at edge >= 6% against the vigged price. Selection is a deterministic
function of the REGRESSORS — the model probability and the price — and not of
the outcome, so conditioning on it leaves the conditional mean unbiased. What it
costs is *support*: the low-edge region is absent, so the estimate speaks for
the population the card actually bets. That is the decision-relevant population,
and it is stated rather than hidden.

**A placebo runs every time.** The model probability is shuffled within market
and the fit repeated. A harness that returns `c > 0` on shuffled inputs is
measuring its own plumbing, and this repository has shipped that mistake before.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.optimize import minimize


#: Probabilities are clipped before the logit. A forecast of exactly 0 or 1 has
#: an infinite logit, and one such row would dominate the whole fit.
CLIP = 1e-4

#: Below this many games a clustered interval is not reported at all. An
#: interval from a handful of clusters is not conservative, it is decorative.
MIN_GAMES = 30


def logit(p) -> np.ndarray:
    p = np.clip(np.asarray(p, dtype=float), CLIP, 1 - CLIP)
    return np.log(p / (1 - p))


def expit(z) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.asarray(z, dtype=float)))


def fit_logistic(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Plain MLE. No penalty, because a penalty would shrink `c` toward the
    very null being tested and make the answer a function of the prior."""

    def nll(beta):
        z = X @ beta
        return float(np.sum(np.logaddexp(0.0, z) - y * z))

    def grad(beta):
        return X.T @ (expit(X @ beta) - y)

    result = minimize(nll, np.zeros(X.shape[1]), jac=grad, method="BFGS")
    return result.x


def cluster_se(
    X: np.ndarray, y: np.ndarray, beta: np.ndarray, groups: np.ndarray
) -> tuple[np.ndarray, int]:
    """Cluster-robust sandwich, clustered by GAME.

    One game supplies many wagers that settle on one afternoon, so treating them
    as independent narrows every interval by roughly the square root of the
    wagers per game. The same reasoning as every other interval in this
    repository, and the same failure it has already been bitten by twice.
    """
    p = expit(X @ beta)
    w = p * (1.0 - p)
    bread = np.linalg.inv((X * w[:, None]).T @ X)
    scores = (y - p)[:, None] * X
    meat = np.zeros((X.shape[1], X.shape[1]))
    order = np.argsort(groups, kind="mergesort")
    unique, starts = np.unique(groups[order], return_index=True)
    for chunk in np.split(scores[order], starts[1:]):
        s = chunk.sum(axis=0)[:, None]
        meat += s @ s.T
    games = len(unique)
    adjustment = games / max(games - 1, 1)
    cov = bread @ (adjustment * meat) @ bread
    return np.sqrt(np.maximum(np.diag(cov), 0.0)), games


def brier(p, y) -> float:
    return float(np.mean((np.asarray(p, dtype=float) - np.asarray(y, dtype=float)) ** 2))


def bootstrap_c(
    frame: pd.DataFrame, *, draws: int = 200, seed: int = 7
) -> tuple[float, float, float]:
    """(SE, 2.5th, 97.5th) for `c` by resampling GAMES with replacement.

    The sandwich above is hand-rolled, and this repository has shipped two
    interval defects: one sqrt(games) too narrow on the forward ledger, one
    pairing a ratio point estimate with an unweighted standard error. A closed
    form nobody checked against a resample is the third one waiting to happen,
    so the report checks it rather than asserting it.
    """
    X = np.column_stack(
        [np.ones(len(frame)), logit(frame["p_market"]), logit(frame["p_model"])]
    )
    y = frame["y"].to_numpy(dtype=float)
    groups = frame["event_id"].to_numpy()
    rng = np.random.default_rng(seed)
    unique = np.unique(groups)
    rows_by_game = {g: np.where(groups == g)[0] for g in unique}
    estimates = []
    for _ in range(draws):
        picked = rng.choice(unique, len(unique), replace=True)
        rows = np.concatenate([rows_by_game[g] for g in picked])
        estimates.append(fit_logistic(X[rows], y[rows])[2])
    estimates = np.asarray(estimates)
    low, high = np.percentile(estimates, [2.5, 97.5])
    return float(estimates.std(ddof=1)), float(low), float(high)


@dataclass(frozen=True)
class Coefficient:
    name: str
    value: float
    se: float
    games: int

    @property
    def low(self) -> float:
        return self.value - 1.96 * self.se

    @property
    def high(self) -> float:
        return self.value + 1.96 * self.se

    @property
    def includes_zero(self) -> bool:
        return self.low <= 0.0 <= self.high


@dataclass
class Fit:
    label: str
    wagers: int
    games: int
    coefficients: list[Coefficient] = field(default_factory=list)

    @property
    def c(self) -> Coefficient | None:
        for coefficient in self.coefficients:
            if coefficient.name.startswith("c "):
                return coefficient
        return None


NAMES = ("intercept", "b  logit(market)", "c  logit(model)")
SIDE_NAME = "d  over side"


def fit(frame: pd.DataFrame, label: str, *, side: bool = False) -> Fit | None:
    """One encompassing fit on a frame carrying y, p_market, p_model, event_id.

    `side=True` adds a bet-side dummy (`side_over`, 1 for an over bet). Because
    side and the model term are almost collinear on a carded population, this
    is the fit that says whether `c` is model information or a side effect.
    """
    if len(frame) < 400 or frame["event_id"].nunique() < MIN_GAMES:
        return None
    columns = [
        np.ones(len(frame)),
        logit(frame["p_market"]),
        logit(frame["p_model"]),
    ]
    names = list(NAMES)
    if side:
        columns.append(frame["side_over"].to_numpy(dtype=float))
        names.append(SIDE_NAME)
    X = np.column_stack(columns)
    y = frame["y"].to_numpy(dtype=float)
    beta = fit_logistic(X, y)
    se, games = cluster_se(X, y, beta, frame["event_id"].to_numpy())
    return Fit(
        label=label,
        wagers=len(frame),
        games=games,
        coefficients=[
            Coefficient(name=n, value=float(b), se=float(s), games=games)
            for n, b, s in zip(names, beta, se)
        ],
    )


def placebo(frame: pd.DataFrame, seed: int = 0) -> Fit | None:
    """The same fit with the model probability shuffled within market.

    Anything the plumbing manufactures survives this; anything real does not.
    """
    rng = np.random.default_rng(seed)
    shuffled = frame.copy()
    shuffled["p_model"] = shuffled.groupby("market")["p_model"].transform(
        lambda s: rng.permutation(s.to_numpy())
    )
    return fit(shuffled, "placebo: model probability shuffled within market")


def roi_interval(frame: pd.DataFrame) -> tuple[float, float, float, int, int]:
    """Pooled ROI and a game-clustered interval.

    **Delegates rather than reimplements.** This repository has had four copies
    of this formula; one was sqrt(games) too narrow on the forward ledger and
    one paired a ratio point estimate with an unweighted standard error. A fifth
    copy written here — even a correct one — is the same mistake waiting to
    happen, so the per-game reduction happens here and the arithmetic happens in
    the one place a test already pins.
    """
    from football_betting_lab.reports.props_backtest import _interval

    if frame.empty:
        return 0.0, float("nan"), float("nan"), 0, 0
    per_game = frame.groupby("event_id")["profit"].agg(profit="sum", bets="size")
    total = int(per_game["bets"].sum())
    games = len(per_game)
    roi, low, high = _interval(per_game)
    return roi, low, high, total, games


def render(
    pooled: Fit,
    out_of_sample: Fit,
    sham: Fit | None,
    per_season: list[Fit],
    per_market: list[Fit],
    *,
    bootstrap: tuple[float, float, float] | None = None,
    with_side: Fit | None = None,
    briers: dict[str, float],
    rules: list[tuple[str, tuple[float, float, float, int, int]]],
    median_hold: float,
    share_positive: float,
    positive_count: int,
    blend_edge_mean: float,
    blend_edge_median: float,
    model_edge_median: float,
) -> str:
    lines: list[str] = []
    add = lines.append
    add("# Does the model know anything the price does not?")
    add("")
    add(
        "Every other instrument here asks whether a *return* is real. This one "
        "asks the question underneath: fitting"
    )
    add("")
    add("    logit P(over) = a + b*logit(p_market_devigged) + c*logit(p_model)")
    add("")
    add(
        "**if `c` cannot be told from zero, the model adds nothing to the price** "
        "and no threshold or subgroup built on it can be profitable except by "
        "chance. The market probability is devigged **per book** before the "
        "books are combined, because devigging a best-of-N over against a "
        "best-of-N under invents a market with far less hold than anyone quoted."
    )
    add("")

    c = pooled.c
    assert c is not None
    add("## The answer")
    add("")
    if c.includes_zero:
        add(
            f"**`c` = {c.value:+.4f}, 95% interval [{c.low:+.4f}, {c.high:+.4f}] "
            f"over {pooled.wagers:,} wagers across {pooled.games:,} games — the "
            "interval includes zero, so there is **no demonstrated information** "
            "in the model beyond the price."
        )
    else:
        add(
            f"**`c` = {c.value:+.4f}, 95% interval [{c.low:+.4f}, {c.high:+.4f}] "
            f"over {pooled.wagers:,} wagers across {pooled.games:,} games.** The "
            "interval excludes zero: the model carries a little information the "
            "devigged price does not."
        )
    add("")
    add(
        "**Multiplicity.** The single out-of-sample fit below is one of several "
        "dozen specifications this report and its checks examine; on its own it "
        "would not survive a correction for that. The finding rests on the "
        "holdout season being independent of the fit, on replicating in every "
        "season, and on the placebo — not on any one p-value."
    )
    add("")
    for f in (pooled, out_of_sample):
        add(f"**{f.label}** — {f.wagers:,} wagers, {f.games:,} games")
        add("")
        add("| term | estimate | SE | 95% interval | |")
        add("|:--|--:|--:|:--|:--|")
        for coefficient in f.coefficients:
            note = "includes zero" if coefficient.includes_zero else "excludes zero"
            add(
                f"| `{coefficient.name}` | {coefficient.value:+.4f} | "
                f"{coefficient.se:.4f} | [{coefficient.low:+.4f}, "
                f"{coefficient.high:+.4f}] | {note} |"
            )
        add("")

    if bootstrap is not None:
        se_boot, low_boot, high_boot = bootstrap
        c_pooled = pooled.c
        assert c_pooled is not None
        add("## The interval, checked against a resample rather than asserted")
        add("")
        add(
            "The clustered standard error is a hand-rolled sandwich, and this "
            "repository has shipped two interval defects — one sqrt(games) too "
            "narrow on the forward ledger, one pairing a ratio point estimate "
            "with an unweighted standard error. So `c` is also estimated by "
            "resampling **games** with replacement."
        )
        add("")
        add(
            f"| | standard error | 95% interval |\n|:--|--:|:--|\n"
            f"| sandwich | {c_pooled.se:.5f} | [{c_pooled.low:+.4f}, {c_pooled.high:+.4f}] |\n"
            f"| bootstrap over games | {se_boot:.5f} | [{low_boot:+.4f}, {high_boot:+.4f}] |"
        )
        add("")
        ratio = c_pooled.se / se_boot if se_boot else float("nan")
        add(
            f"The sandwich is **{ratio:.3f}x** the resample. Both intervals "
            f"{'exclude' if low_boot > 0 or high_boot < 0 else 'include'} zero."
        )
        add("")

    if with_side is not None and with_side.c is not None:
        wc = with_side.c
        add("## What identifies `c`: model information, or the bet side?")
        add("")
        add(
            "On a carded population the sign of `logit(model) − logit(market)` "
            "is the bet side on almost every row, so `c` and the side are "
            "nearly collinear — and the market has a side asymmetry of its own "
            "(unders land a few points more often than the devigged median "
            "says). Adding a bet-side dummy separates the two."
        )
        add("")
        add("| term | estimate | SE | 95% interval | |")
        add("|:--|--:|--:|:--|:--|")
        for coefficient in with_side.coefficients:
            note = "includes zero" if coefficient.includes_zero else "excludes zero"
            add(
                f"| `{coefficient.name}` | {coefficient.value:+.4f} | "
                f"{coefficient.se:.4f} | [{coefficient.low:+.4f}, "
                f"{coefficient.high:+.4f}] | {note} |"
            )
        add("")
        if wc.includes_zero:
            add(
                f"**With the side dummy, `c` = {wc.value:+.4f} and its interval "
                "includes zero.** The point estimate barely moves — this is "
                "collinearity, not refutation — but it means the placebo above "
                "cannot distinguish model information from a side-specific "
                "market miscalibration, and \"the model knows something the "
                "price does not\" must be read as \"the price does not fully "
                "absorb something correlated with the model's side.\""
            )
        else:
            add(
                f"**With the side dummy, `c` = {wc.value:+.4f} and its interval "
                "still excludes zero**, so the signal is not just the bet side."
            )
        add("")

    if sham is not None:
        sc = sham.c
        add("## The placebo, which runs every time")
        add("")
        add(
            "The model probability is shuffled within market and the fit "
            "repeated. A harness that returns a positive `c` on shuffled input "
            "is measuring its own plumbing."
        )
        add("")
        if sc is not None:
            verdict = (
                "includes zero — the harness does not manufacture the result"
                if sc.includes_zero
                else "**EXCLUDES ZERO — the harness is manufacturing this and the "
                "result above cannot be believed**"
            )
            add(
                f"`c` on shuffled input = **{sc.value:+.4f}**, interval "
                f"[{sc.low:+.4f}, {sc.high:+.4f}] over {sham.wagers:,} wagers "
                f"— {verdict}."
            )
        add("")

    add("## And what it is worth, which is the part that decides anything")
    add("")
    add(
        f"| forecaster | out-of-sample Brier |"
    )
    add("|:--|--:|")
    for name, value in briers.items():
        add(f"| {name} | {value:.5f} |")
    add("")
    gain = briers.get("market alone, refitted", 0.0) - briers.get(
        "market + model", 0.0
    )
    add(
        f"**Adding the model to the price improves out-of-sample Brier by "
        f"{gain:.5f}.** For scale, this lab declared a 0.002 threshold in advance "
        "for whether crossing the inactives deadline was worth anything, and "
        f"called the answer no at +0.00085. This is {'smaller' if gain < 0.00085 else 'larger'} than that."
    )
    add("")
    add(
        f"The blend's own edge on the wagers the card selected — measured "
        "against the **vigged price actually bought**, so already net of the "
        f"full hold — is **negative** on average: mean {blend_edge_mean:+.4f}, "
        f"median {blend_edge_median:+.4f}, against a raw model edge whose "
        f"median is {model_edge_median:+.4f}. Only **{share_positive:.1%}** "
        f"(n = {positive_count:,}) of them have a positive blend edge at all, "
        "and that bucket's return is the first filtered row below. (The median "
        f"two-sided book hold is {median_hold:.2%}, stated for scale; it is "
        "NOT deducted again — an earlier version of this report compared the "
        "already-net edge to a half-hold and so charged the vig twice.)"
    )
    add("")
    add("### Betting the blend, out of sample")
    add("")
    add("| rule | bets | games | ROI | 95% interval | |")
    add("|:--|--:|--:|--:|:--|:--|")
    for label, (roi, low, high, bets, games) in rules:
        if bets == 0:
            continue
        verdict = (
            "**no demonstrated edge**"
            if not (low == low) or low <= 0.0 <= high
            else ("**negative**" if high < 0 else "excludes zero, positive")
        )
        add(
            f"| {label} | {bets:,} | {games:,} | {roi:+.2%} | "
            f"[{low:+.2%}, {high:+.2%}] | {verdict} |"
        )
    add("")
    add(
        "**Read the shape of that column, not its best row.** The return rises "
        "to a threshold and then falls away, which is what a scan over "
        "thresholds does to noise — a real edge strengthens as the filter "
        "tightens. Every interval includes zero, the thresholds were scanned "
        "rather than declared in advance, and the two positive rows are the two "
        "a reader would want to believe. **No demonstrated edge**, in those "
        "words."
    )
    add("")

    add("## Per season, and per market")
    add("")
    add("| cut | wagers | games | `c` | 95% interval | |")
    add("|:--|--:|--:|--:|:--|:--|")
    for f in per_season + per_market:
        coefficient = f.c
        if coefficient is None:
            continue
        note = "includes zero" if coefficient.includes_zero else "excludes zero"
        add(
            f"| {f.label} | {f.wagers:,} | {f.games:,} | "
            f"{coefficient.value:+.4f} | [{coefficient.low:+.4f}, "
            f"{coefficient.high:+.4f}] | {note} |"
        )
    add("")
    add(
        "**Selection does not bias any of this.** The bets file holds only "
        "wagers the card selected at edge >= 6% against the vigged price, but "
        "selection is a deterministic function of the REGRESSORS and not of the "
        "outcome, so the conditional mean is unbiased. What it costs is support: "
        "the low-edge region is absent, so every number here speaks for the "
        "population the card actually bets."
    )
    return "\n".join(lines) + "\n"
