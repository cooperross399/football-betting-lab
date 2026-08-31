#!/usr/bin/env python3
"""Is a book's same-game-parlay price better or worse than fair? Spends nothing.

    PYTHONPATH=src python scripts/check_parlay_pricing.py --quotes my_sgp.csv

**The provider does not serve parlay prices.** The Odds API offers no parlay or
same-game-parlay markets for any sport, so this cannot be bought with credits at
any price. The only way to get them is to record what a book actually offers.

The good news is that the test needs almost no data, because **it is a pricing
comparison, not a betting test.** Given a book's own single-leg prices and a
measured correlation, the fair two-leg price is arithmetic. Comparing it to what
the book offers needs no settlement, no variance and no sample-size argument —
fifty quotes will show a systematic gap as clearly as five thousand.

The prior is strongly against finding an edge, and it should be stated before
anyone spends an evening recording quotes: straight bets hold about 4-5%, and
same-game parlays hold **15-30%** because margin compounds across legs and books
already apply their own correlation adjustment. This lab's copula is accurate to
about 0.02-0.04 in correlation, which is not worth twenty points of hold. The
expected finding is that SGPs are priced worse than fair, not better.

Record quotes as CSV with these columns:

    legs,p1,p2,offered_decimal,correlation

`p1`/`p2` are the book's own single-leg DECIMAL prices for each leg (or its
implied probabilities — either is accepted), `offered_decimal` is the parlay
price it shows, and `correlation` is the measured realised correlation for that
leg pair from `data/outputs/nfl_correlation_check.md`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

#: Below this a "probability" column is read as a probability; at or above it,
#: as decimal odds. A decimal price is never under 1.0 and a probability is
#: never over 1.0, so the two cannot be confused.
DECIMAL_FLOOR = 1.0


def _as_probability(value: float) -> float:
    return 1.0 / value if value >= DECIMAL_FLOOR else value


def fair_joint(p1: float, p2: float, correlation: float) -> float:
    """P(both) for two binary legs with a given correlation.

    The Pearson correlation of two indicators pins their joint exactly:

        P(A and B) = P(A)P(B) + rho * sqrt(P(A)(1-P(A)) P(B)(1-P(B)))

    No copula choice is needed for two binaries — the correlation IS the
    dependence. Clipped to the Frechet bounds, because a correlation that
    implies an impossible joint is a measurement error rather than a price.
    """
    independent = p1 * p2
    spread = np.sqrt(p1 * (1 - p1) * p2 * (1 - p2))
    joint = independent + correlation * spread
    return float(np.clip(joint, max(0.0, p1 + p2 - 1.0), min(p1, p2)))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quotes", required=True, help="CSV of recorded SGP quotes.")
    args = parser.parse_args(argv)

    path = Path(args.quotes)
    if not path.is_file():
        print(
            f"No quotes at {path}. The provider does not serve parlay prices, "
            "so these have to be recorded from a book by hand — see this "
            "script's docstring for the columns.",
            file=sys.stderr,
        )
        return 2
    quotes = pd.read_csv(path)
    required = {"legs", "p1", "p2", "offered_decimal", "correlation"}
    missing = required - set(quotes.columns)
    if missing:
        print(f"Missing column(s): {', '.join(sorted(missing))}.", file=sys.stderr)
        return 2

    rows = []
    for row in quotes.itertuples():
        p1 = _as_probability(float(row.p1))
        p2 = _as_probability(float(row.p2))
        joint = fair_joint(p1, p2, float(row.correlation))
        fair_price = 1.0 / joint if joint else float("inf")
        offered = float(row.offered_decimal)
        rows.append({
            "legs": row.legs,
            "fair_joint": joint,
            "independent": p1 * p2,
            "fair_decimal": fair_price,
            "offered_decimal": offered,
            # What the book pays as a share of what it should. Above 1.0 the
            # parlay is generous; below it, the correlation haircut is more
            # than the correlation is worth.
            "value": offered / fair_price if fair_price else float("nan"),
        })
    table = pd.DataFrame(rows)

    print(f"{len(table):,} quote(s) from {path}\n")
    print(
        "Every number below is only as real as that file. These must be prices "
        "a book actually showed,\nrecorded BEFORE the games were played. An "
        "invented `offered_decimal` produces an invented edge,\nand a "
        "plausible one: this lab has retracted four findings that were "
        "arithmetic on bad inputs.\n"
    )
    print(f"{'legs':<44}{'fair':>9}{'offered':>10}{'value':>9}")
    print("-" * 72)
    for r in table.itertuples():
        print(f"{str(r.legs)[:43]:<44}{r.fair_decimal:>9.2f}{r.offered_decimal:>10.2f}"
              f"{r.value:>9.2f}")
    edge = float(table["value"].mean()) - 1.0
    print(f"\nMean value: {table['value'].mean():.3f}  ->  {edge:+.1%}")
    if edge > 0:
        print(
            "\n**Positive**, which is necessary and not sufficient. It has to "
            "survive on quotes recorded BEFORE the outcome was known, across "
            "more than one book, and it has to beat the straight-bet "
            "alternative — a parlay is only worth taking if it beats betting "
            "the legs separately."
        )
    else:
        print(
            f"\n**Negative: the book's correlation haircut costs more than the "
            f"correlation is worth.** That is the expected result — SGPs hold "
            f"15-30% against 4-5% on straights — and it closes the parlay route "
            f"rather than leaving it open on a hunch."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
