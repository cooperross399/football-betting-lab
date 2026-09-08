"""What is line shopping worth on its own, with no model at all?

Every model this lab has built loses to the price. But one thing in the
evidence is consistently positive, and it is not a model: the same wagers,
settled the same way, return more at the best of N books than at the consensus.
`rush_yards` is +1.2% best-of-N against -0.6% at the median quote — a gap of
1.8 points that requires the model to know nothing.

That gap deserves its own measurement rather than a story, because there is a
boring explanation and an interesting one and they look identical in an ROI
table.

## The arithmetic that decides it

If a book prices a two-sided market with hold `h`, and prices both sides
proportionally to the fair probability, then betting **either** side blind
returns `-h / (1 + h)`. **The hold is the model-free expected loss.** Shopping
does not add anything to a bet; it lowers the hold you pay, and it lowers it by
letting you take the best over at one book and the best under at another.

So the whole question reduces to one curve: **how far does the effective hold
fall as the number of books rises, and does it reach zero?**

- If it falls but stays positive, shopping is a **cost reduction**. It makes a
  losing strategy lose less, and it cannot make a losing strategy win. The
  observed ROI gap is then fully explained by the hold difference and there is
  no residual to chase.
- If it reaches zero or below on a real share of wagers, that is arbitrage, and
  it needs no model at all.

The second answer would be extraordinary and is the one to disbelieve hardest.
A best-over and a best-under pulled from a snapshot cache can appear to cross
for reasons that have nothing to do with a free bet: the two quotes may sit at
different lines, in different markets, at different moments, or at a stale
price no one could still take. So the pairing here is exact on event, market,
player, line **and snapshot**, and the arbitrage share is reported beside the
count of wagers it rests on rather than as a headline.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from football_betting_lab.forward_evidence import american_to_implied

#: A wager is the same product only when all of these match. Pairing a best
#: over at one line against a best under at another is not a market, it is two
#: markets, and it manufactures a hold that nobody quoted.
WAGER_KEY = ("event_id", "market", "identity", "line", "phase")


@dataclass(frozen=True)
class HoldCurve:
    """Effective hold as the number of books shopped rises."""

    books: list[int]
    median_hold: list[float]
    mean_hold: list[float]
    share_non_positive: list[float]
    wagers: list[int]


def two_sided(prices: pd.DataFrame) -> pd.DataFrame:
    """One row per wager per book, carrying both sides' implied probabilities."""
    frame = prices.copy()
    frame["line"] = pd.to_numeric(frame["line"], errors="coerce")
    frame["american_odds"] = pd.to_numeric(frame["american_odds"], errors="coerce")
    frame = frame.dropna(subset=["line", "american_odds"])
    frame["side"] = frame["selection"].astype(str).str.lower()
    frame = frame[frame["side"].isin(["over", "under"])]
    wide = frame.pivot_table(
        index=[*WAGER_KEY, "book"], columns="side", values="american_odds",
        aggfunc="max",
    ).reset_index()
    if "over" not in wide.columns or "under" not in wide.columns:
        raise ValueError("No two-sided quotes in this population.")
    wide = wide.dropna(subset=["over", "under"])
    wide["p_over"] = wide["over"].map(american_to_implied)
    wide["p_under"] = wide["under"].map(american_to_implied)
    wide["hold"] = wide["p_over"] + wide["p_under"] - 1.0
    return wide


def hold_curve(quotes: pd.DataFrame, *, seed: int = 3, draws: int = 40) -> HoldCurve:
    """Effective hold when the best over and best under come from N books.

    N books are drawn at random from those quoting each wager, repeatedly, so
    the curve answers "what if I held accounts at N books" rather than "what if
    I held accounts at the N books that happened to be best" — which is a
    question nobody can act on, and which would understate the hold at every N.
    """
    rng = np.random.default_rng(seed)
    grouped = quotes.groupby(list(WAGER_KEY))
    per_wager = [
        (group["p_over"].to_numpy(float), group["p_under"].to_numpy(float))
        for _, group in grouped
    ]
    widest = max((len(over) for over, _ in per_wager), default=0)
    books, median, mean, share, counts = [], [], [], [], []
    for n in range(1, widest + 1):
        holds: list[float] = []
        for over, under in per_wager:
            if len(over) < n:
                continue
            for _ in range(draws if n < len(over) else 1):
                pick = rng.choice(len(over), n, replace=False)
                holds.append(float(over[pick].min() + under[pick].min() - 1.0))
        if not holds:
            continue
        values = np.asarray(holds, dtype=float)
        books.append(n)
        median.append(float(np.median(values)))
        mean.append(float(values.mean()))
        share.append(float((values <= 0).mean()))
        counts.append(int(sum(1 for over, _ in per_wager if len(over) >= n)))
    return HoldCurve(books, median, mean, share, counts)


def blind_return(hold: float) -> float:
    """What betting either side blind returns at that hold.

    A book pricing both sides proportionally to the fair probability leaves
    `-h / (1 + h)` on either side, so this is not a model of anything — it is
    what the hold means expressed as a return.
    """
    return -hold / (1.0 + hold)


#: A quote this far from the median across books quoting the same wager is not
#: a disagreement, it is a bad row. Measured over 1.4M quotes with three or more
#: books: **9 exceed it, every one FanDuel on `alternate_total_points`**, where
#: three books had the over at +366 to +400 and the fourth at -295. Nine rows in
#: 1.4M is provider noise rather than a parsing fault, but they land entirely in
#: the crossed population and would otherwise be its headline.
IMPLAUSIBLE_DEVIATION = 0.35


def implausible(quotes: pd.DataFrame) -> pd.Series:
    """Quotes whose over-price disagrees wildly with the other books' median.

    Only computable where three or more books quote the wager: with two, there
    is no majority to be the odd one out of.
    """
    grouped = quotes.groupby(list(WAGER_KEY))["p_over"]
    median = grouped.transform("median")
    books = quotes.groupby(list(WAGER_KEY))["book"].transform("nunique")
    return (books >= 3) & ((quotes["p_over"] - median).abs() > IMPLAUSIBLE_DEVIATION)


def crossed(quotes: pd.DataFrame) -> pd.DataFrame:
    """Wagers where the best over and best under across ALL books cross.

    Returned rather than counted, because a crossed pair is a claim about free
    money and has to be looked at one row at a time before it is believed.
    """
    best = quotes.groupby(list(WAGER_KEY)).agg(
        best_over=("p_over", "min"), best_under=("p_under", "min"),
        books=("book", "nunique"),
    ).reset_index()
    best["hold"] = best["best_over"] + best["best_under"] - 1.0
    return best[best["hold"] <= 0].sort_values("hold")
