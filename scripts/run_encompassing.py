#!/usr/bin/env python3
"""Does the model know anything the price does not? Spends nothing.

    PYTHONPATH=src python scripts/run_encompassing.py

Fits `logit P(over) = a + b*logit(p_market_devigged) + c*logit(p_model)` over the
bought population. If `c` cannot be told from zero the model adds nothing to the
price, and no feature, threshold or subgroup built on it can be profitable
except by chance — which makes this the cheapest test of whether any of the rest
of the modelling has a point.

The market probability is devigged PER BOOK before the books are combined.
Devigging a best-of-N over against a best-of-N under invents a market with far
less hold than any book actually quoted, and the hold is the thing a wager has
to beat.
"""

from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd

from football_betting_lab.config import OUTPUTS_DIR, RAW_DIR
from football_betting_lab.forward_evidence import american_to_implied
from football_betting_lab.leagues import DEFAULT_LEAGUE_KEY, league_for
from football_betting_lab.reports import encompassing
from football_betting_lab.reports.props_backtest import (
    label_snapshots,
    load_bought_prices,
    normalise_name,
)

CACHE_DIRNAME = "historical_prices"


def devigged_market(league, raw_dir) -> pd.DataFrame:
    """Per-book devigged P(over) for every two-sided wager, then combined."""
    prices = label_snapshots(load_bought_prices(raw_dir / league.data_dir_segment / CACHE_DIRNAME, league))
    if "phase" in prices.columns:
        prices = prices[prices["phase"] == "card"]
    prices = prices.copy()
    prices["line"] = pd.to_numeric(prices["line"], errors="coerce")
    prices["american_odds"] = pd.to_numeric(prices["american_odds"], errors="coerce")
    prices = prices.dropna(subset=["line", "american_odds"])
    prices["identity"] = prices["player"].map(normalise_name)
    sides = prices.pivot_table(
        index=["event_id", "market", "identity", "line", "book"],
        columns="selection",
        values="american_odds",
        aggfunc="max",
    ).reset_index()
    if "over" not in sides.columns or "under" not in sides.columns:
        raise SystemExit("::error::No two-sided featured prices in the cache.")
    sides = sides.dropna(subset=["over", "under"])
    over = sides["over"].map(american_to_implied)
    under = sides["under"].map(american_to_implied)
    sides["hold"] = over + under - 1.0
    sides["p_over_fair"] = over / (over + under)
    return (
        sides.groupby(["event_id", "market", "identity", "line"])
        .agg(p_market=("p_over_fair", "median"), hold=("hold", "median"), books=("p_over_fair", "size"))
        .reset_index()
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", default=DEFAULT_LEAGUE_KEY)
    parser.add_argument("--holdout-season", type=int, default=2025)
    parser.add_argument(
        "--bootstrap", type=int, default=200,
        help="Resamples of GAMES used to check the clustered interval. 0 skips it.",
    )
    args = parser.parse_args(argv)
    league = league_for(args.league)

    bets_path = OUTPUTS_DIR / league.output_name("props_backtest_bets", ".csv")
    if not bets_path.is_file():
        print(f"::error::No scored bets at {bets_path}.", file=sys.stderr)
        return 2
    bets = pd.read_csv(bets_path, low_memory=False)
    bets["identity"] = bets["player"].map(normalise_name)
    bets["line"] = pd.to_numeric(bets["line"], errors="coerce")

    market = devigged_market(league, RAW_DIR)
    frame = bets.merge(market, on=["event_id", "market", "identity", "line"], how="inner")
    frame = frame.dropna(subset=["actual", "line", "model_probability", "p_market", "profit"])
    # A push decides nothing and carries no information about direction.
    frame = frame[frame["actual"] != frame["line"]].copy()
    if frame.empty:
        print("::error::Nothing merged. The bets file and the price cache disagree.", file=sys.stderr)
        return 2

    # The cross-season defect, guarded at runtime rather than argued in a
    # comment. This script never maps an event to a season — it inherits the
    # season from an already-settled bet — but that is exactly the kind of
    # reasoning that was wrong twice before, so it is checked on the real
    # frame every run. CI cannot check it: the price cache is not committed.
    spanning = frame.groupby("event_id")["season"].nunique()
    if int((spanning > 1).sum()):
        offenders = spanning[spanning > 1].index.tolist()[:5]
        print(
            f"::error::{int((spanning > 1).sum())} event(s) map to more than one "
            f"season, e.g. {offenders}. A priced event settled against another "
            "season's game is the defect that produced every positive result "
            "this repository has retracted.",
            file=sys.stderr,
        )
        return 2
    widest = frame.groupby(["event_id", "market", "identity", "line"]).size().max()
    if int(widest) > 1:
        print(
            f"::error::The price join duplicated wagers ({widest} rows on one "
            "wager key). Every interval below would be too narrow.",
            file=sys.stderr,
        )
        return 2

    frame["y"] = (frame["actual"] > frame["line"]).astype(float)
    over = frame["selection"].astype(str).str.lower().eq("over")
    # Both regressors must describe the SAME side, or `c` measures the flip.
    frame["p_model"] = np.where(over, frame["model_probability"], 1.0 - frame["model_probability"])
    frame["side_over"] = over.astype(float)

    pooled = encompassing.fit(frame, "pooled, in sample")
    if pooled is None:
        print("::error::Too few wagers or games to fit.", file=sys.stderr)
        return 2
    sham = encompassing.placebo(frame)
    with_side = encompassing.fit(frame, "pooled, with a bet-side dummy", side=True)

    train = frame[frame["season"] != args.holdout_season]
    test = frame[frame["season"] == args.holdout_season].copy()
    out = encompassing.fit(train, f"fitted without {args.holdout_season}")
    if out is None or test.empty:
        print("::error::No usable train/test split.", file=sys.stderr)
        return 2

    beta = np.array([c.value for c in out.coefficients])
    X_test = np.column_stack(
        [np.ones(len(test)), encompassing.logit(test["p_market"]), encompassing.logit(test["p_model"])]
    )
    market_only = encompassing.fit_logistic(
        np.column_stack([np.ones(len(train)), encompassing.logit(train["p_market"])]),
        train["y"].to_numpy(dtype=float),
    )
    X_test_market = X_test[:, :2]
    y_test = test["y"].to_numpy(dtype=float)
    briers = {
        "the raw model": encompassing.brier(test["p_model"], y_test),
        "the devigged market price": encompassing.brier(test["p_market"], y_test),
        "market alone, refitted": encompassing.brier(encompassing.expit(X_test_market @ market_only), y_test),
        "market + model": encompassing.brier(encompassing.expit(X_test @ beta), y_test),
    }

    test["p_blend_over"] = encompassing.expit(X_test @ beta)
    over_test = test["selection"].astype(str).str.lower().eq("over")
    test["p_blend"] = np.where(over_test, test["p_blend_over"], 1.0 - test["p_blend_over"])
    test["implied_vig"] = test["odds"].map(american_to_implied)
    test["edge_blend"] = test["p_blend"] - test["implied_vig"]
    test["edge_model"] = test["model_probability"] - test["implied_vig"]

    rules = [(f"the card as it stands, {args.holdout_season}", encompassing.roi_interval(test))]
    for threshold in (0.0, 0.01, 0.02, 0.03, 0.05):
        rules.append(
            (f"blend edge >= {threshold:.2f}", encompassing.roi_interval(test[test["edge_blend"] >= threshold]))
        )

    per_season = [f for f in (encompassing.fit(g, f"season {s}") for s, g in frame.groupby("season")) if f]
    per_market = [
        f for f in (encompassing.fit(g, f"`{m}`") for m, g in frame.groupby("market") if len(g) >= 1000) if f
    ]

    # edge_blend is already net of the vigged price actually bought. It must
    # NOT be compared to a half-hold: that charges the vig twice, and an earlier
    # version of this script did exactly that.
    positive = test["edge_blend"] > 0
    boot = (
        encompassing.bootstrap_c(frame, draws=args.bootstrap)
        if args.bootstrap
        else None
    )
    report = encompassing.render(
        pooled, out, sham, per_season, per_market, bootstrap=boot, with_side=with_side,
        briers=briers,
        rules=rules,
        median_hold=float(frame["hold"].median()),
        share_positive=float(positive.mean()),
        positive_count=int(positive.sum()),
        blend_edge_mean=float(test["edge_blend"].mean()),
        blend_edge_median=float(test["edge_blend"].median()),
        model_edge_median=float(test["edge_model"].median()),
    )
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUTS_DIR / league.output_name("encompassing", ".md")
    path.write_text(report, encoding="utf-8")

    c = pooled.c
    print(f"{pooled.wagers:,} wagers, {pooled.games:,} games. c={c.value:+.4f} [{c.low:+.4f}, {c.high:+.4f}]")
    if sham and sham.c:
        print(f"placebo c={sham.c.value:+.4f} [{sham.c.low:+.4f}, {sham.c.high:+.4f}]")
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
