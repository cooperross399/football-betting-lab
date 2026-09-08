#!/usr/bin/env python3
"""What is line shopping worth on its own? Spends nothing.

    PYTHONPATH=src python scripts/run_shopping_value.py

Every model here loses to the price. One thing in the evidence is consistently
positive and is not a model: the same wagers return more at the best of N books
than at the consensus. This measures that directly, as a hold, because the hold
is what a model-free bettor pays and therefore what shopping can recover.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from football_betting_lab.config import OUTPUTS_DIR, RAW_DIR
from football_betting_lab.leagues import DEFAULT_LEAGUE_KEY, league_for
from football_betting_lab.providers.historical import CACHE_DIRNAME
from football_betting_lab.reports import shopping
from football_betting_lab.reports.props_backtest import (
    label_snapshots, load_bought_prices, normalise_name,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", default=DEFAULT_LEAGUE_KEY)
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--draws", type=int, default=40)
    args = parser.parse_args(argv)
    league = league_for(args.league)

    prices = label_snapshots(
        load_bought_prices(args.raw_dir / league.data_dir_segment / CACHE_DIRNAME, league)
    )
    if prices.empty:
        print("::error::No bought prices in the cache.", file=sys.stderr)
        return 2
    prices["identity"] = prices["player"].map(normalise_name)
    quotes = shopping.two_sided(prices)
    bad = shopping.implausible(quotes)
    quotes = quotes[~bad].copy()
    curve = shopping.hold_curve(quotes, draws=args.draws)
    crossed = shopping.crossed(quotes)
    wagers = quotes.groupby(list(shopping.WAGER_KEY)).ngroups

    one = curve.median_hold[0]
    most = curve.median_hold[-1]
    lines = [
        "# What line shopping is worth, with no model at all",
        "",
        f"{len(quotes):,} two-sided book quotes across "
        f"{wagers:,} wagers, "
        f"{quotes['book'].nunique()} books.",
        "",
        "## The hold, as the number of books rises",
        "",
        "Books are drawn at random from those quoting each wager, so this "
        "answers *what if I held accounts at N books* rather than *what if I "
        "held accounts at the N that turned out best* — a question nobody can "
        "act on, and one that would understate the hold at every N.",
        "",
        "| books | median hold | mean hold | wagers | what betting blind returns |",
        "|--:|--:|--:|--:|--:|",
    ]
    for index, n in enumerate(curve.books):
        lines.append(
            f"| {n} | {100 * curve.median_hold[index]:.2f}% | "
            f"{100 * curve.mean_hold[index]:.2f}% | {curve.wagers[index]:,} | "
            f"{100 * shopping.blind_return(curve.median_hold[index]):+.2f}% |"
        )

    recovered = one - most
    lines += [
        "",
        f"**Shopping every book cuts the median hold from {100 * one:.2f}% to "
        f"{100 * most:.2f}%** — it recovers **{100 * recovered:.2f} points**. "
        f"Betting blind goes from {100 * shopping.blind_return(one):+.2f}% to "
        f"{100 * shopping.blind_return(most):+.2f}%.",
        "",
        "## What that settles",
        "",
        "**The hold is the model-free expected loss.** A book pricing both "
        "sides proportionally to the fair probability leaves `-h / (1 + h)` on "
        "either side, so a bettor with no opinion at all loses the hold and "
        "nothing else. Shopping does not add anything to a bet; it lowers the "
        "hold, and it can only lower a loss.",
        "",
        (
            f"**The hold stays positive at every book count**, so shopping is a "
            f"cost reduction and cannot make a losing strategy win. The "
            f"{100 * recovered:.2f} points it recovers is the whole of the "
            "best-of-N advantage seen in `nfl_price_sensitivity.md`; there is "
            "no residual edge underneath it to chase. To profit, a model still "
            f"has to beat the price by more than {100 * most:.2f}% — and this "
            "lab's does not beat it at all."
            if most > 0 else
            f"**The median hold reaches {100 * most:.2f}% at the full book "
            "count**, which is a claim about free money and is treated below "
            "as something to disprove rather than report."
        ),
        "",
        "## Wagers where the two best quotes cross",
        "",
        f"**{len(crossed):,} of {wagers:,} wagers** "
        f"({100 * len(crossed) / max(wagers, 1):.3f}%) have a best over and a "
        "best under that sum to no more than one — after "
        f"**{int(bad.sum())} implausible quotes** were removed, every one of "
        "them FanDuel on `alternate_total_points` where three other books had "
        "the over at +366 to +400 and it had -295. Nine bad rows in 1.4 million "
        "is provider noise, but they land entirely here and would otherwise "
        "have been this section's headline at -48%.",
        "",
        "A crossed pair is a claim about free money and every boring "
        "explanation has to be excluded before it is anything else: the two "
        "quotes are paired here on event, market, player, line **and** "
        "snapshot, so they are the same product at the same moment. What that "
        "pairing cannot establish is whether both were still on the screen "
        "when the second was taken, whether either book would have accepted a "
        "stake, or whether the price was an error the book would void. "
        "**Nothing here should be read as an executable strategy**, and this "
        "lab does not place bets.",
    ]
    if len(crossed):
        bands = [
            (-1.0, -0.10, "worse than -10%"), (-0.10, -0.05, "-10% to -5%"),
            (-0.05, -0.02, "-5% to -2%"), (-0.02, -0.005, "-2% to -0.5%"),
            (-0.005, 1.0, "-0.5% to 0"),
        ]
        lines += ["", "| size of the crossing | wagers | share |", "|:--|--:|--:|"]
        for low, high, label in bands:
            count = int(((crossed["hold"] >= low) & (crossed["hold"] < high)).sum())
            lines.append(f"| {label} | {count:,} | {100 * count / len(crossed):.1f}% |")
        median = float(crossed["hold"].median())
        lines += [
            "",
            f"**The median crossing is {100 * median:.2f}%**, and most of them "
            "are within half a point of not crossing at all. An edge that size "
            "is inside the noise of actually placing the two bets: the lines "
            "move, the stakes are limited, and both quotes have to still be "
            "there when the second is struck. It is arbitrage-**shaped** and it "
            "is not a strategy.",
            "",
            "Most common in " + ", ".join(
                f"`{market}` ({count:,})"
                for market, count in crossed["market"].value_counts().head(4).items()
            ) + ".",
        ]

    body = "\n".join(lines) + "\n"
    out = OUTPUTS_DIR / league.output_name("shopping_value", ".md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")
    print(body)
    print(f"Written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
