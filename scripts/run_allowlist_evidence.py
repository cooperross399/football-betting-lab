#!/usr/bin/env python3
"""Assemble every measurement into one reviewable artifact, and stop.

    PYTHONPATH=src python scripts/run_allowlist_evidence.py

This allowlists nothing. It is step four of the six in
`docs/provider_allowlist_approval.md`; step six is Cooper's.
"""

from __future__ import annotations

import argparse
import math
import sys
from statistics import NormalDist

import pandas as pd

from football_betting_lab.config import OUTPUTS_DIR, RAW_DIR
from football_betting_lab.leagues import DEFAULT_LEAGUE_KEY, league_for
from football_betting_lab.providers.historical import CACHE_DIRNAME
from football_betting_lab.reports import allowlist_evidence as bundle_module
from football_betting_lab.reports.allowlist_evidence import (
    Bar,
    EvidenceBundle,
    MarketEvidence,
)
from football_betting_lab.reports.price_sensitivity import (
    from_implied,
    measure as measure_prices,
    profit,
    to_implied,
)
from football_betting_lab.reports.props_backtest import (
    MINIMUM_BETS,
    coverage_line,
    label_snapshots,
    load_bought_prices,
    load_scored_bets,
)
from football_betting_lab.reports.settlement_agreement import (
    IMPLIED_GAP_TOLERANCE,
)

#: Markets the compound simulation prices. The split between these and the
#: count-only markets is the strongest structure in the evidence.
COMPOUND = {
    "rush_yards", "rush_attempts", "rush_longest", "receptions",
    "reception_yards", "reception_longest", "pass_yards", "pass_completions",
    "pass_longest_completion",
}

#: Minimum share of quoting books at which a market must be positive.
MIN_BOOK_SHARE = 0.6

NULL_BASELINE_ROI = -0.0928


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", default=DEFAULT_LEAGUE_KEY)
    args = parser.parse_args(argv)
    league = league_for(args.league)

    bets_path = OUTPUTS_DIR / league.output_name("props_backtest_bets", ".csv")
    settle_path = OUTPUTS_DIR / league.output_name("settlement_agreement", ".md")
    if not bets_path.is_file():
        print(f"No backtest bets at {bets_path}.", file=sys.stderr)
        return 2

    bets = load_scored_bets(bets_path)
    staked = bets[bets["outcome"] != "void"].copy()
    staked["line"] = pd.to_numeric(staked["line"], errors="coerce")
    prices = label_snapshots(
        load_bought_prices(RAW_DIR / league.data_dir_segment / CACHE_DIRNAME, league)
    )
    prices = prices[prices["phase"] == "card"]
    sensitivity = {m.market: m for m in measure_prices(bets, prices)}

    # Settlement suspects, read from the screen's own output so the two
    # cannot drift apart.
    # Two sets, not one. `suspects` is what the screen FLAGGED; `screened` is
    # what it actually LOOKED AT. A market the screen never examined is
    # absent from both, and testing only `not in suspects` printed it as a
    # pass reading "agrees with the devigged price" — an approval bar cleared
    # by never having been measured, which is the shape of the tackles
    # artefact that already cost this lab its headline finding.
    suspects = set()
    screened = set()
    if settle_path.is_file():
        for line in settle_path.read_text(encoding="utf-8").splitlines():
            if not line.startswith("| `"):
                continue
            name = line.split("`")[1]
            screened.add(name)
            if "settlement suspect" in line:
                suspects.add(name)

    seasons = sorted(staked["season"].unique())
    families = staked["market"].nunique()
    factor = NormalDist().inv_cdf(1 - (0.05 / max(families, 1)) / 2) / 1.96

    evidence: list[MarketEvidence] = []
    for market in sorted(staked["market"].unique()):
        rows = staked[staked["market"] == market]
        entry = MarketEvidence(market=str(market), bets=len(rows))
        sens = sensitivity.get(str(market))

        entry.bars.append(
            Bar("harness", NULL_BASELINE_ROI < 0,
                f"betting everything returns {NULL_BASELINE_ROI:+.1%}")
        )
        if str(market) not in screened:
            entry.bars.append(
                Bar("settlement", False,
                    "never screened — the settlement report does not cover "
                    "this market, so nothing is known about whether it "
                    "settles on what it was priced on")
            )
        else:
            entry.bars.append(
                Bar("settlement", str(market) not in suspects,
                    "agrees with the devigged price"
                    if str(market) not in suspects
                    else f"realised rate sits more than {IMPLIED_GAP_TOLERANCE:.0%} from it")
            )
        if sens is None:
            entry.bars.append(Bar("consensus", False, "no consensus price computed"))
            entry.bars.append(Bar("books", False, "no book quoted enough"))
        else:
            entry.bars.append(
                Bar("consensus", sens.consensus_roi > 0,
                    f"{sens.consensus_roi:+.1%} at the median quote")
            )
            share = sens.books_positive / len(sens.books) if sens.books else 0.0
            entry.bars.append(
                Bar("books", share >= MIN_BOOK_SHARE,
                    f"positive at {sens.books_positive} of {len(sens.books)}")
            )
        # Replication: positive in every season with enough bets.
        per_season = rows.groupby("season")["profit"].agg(["size", "mean"])
        usable = per_season[per_season["size"] >= MINIMUM_BETS]
        replicated = len(usable) >= 2 and bool((usable["mean"] > 0).all())
        entry.bars.append(
            Bar("replication", replicated,
                ", ".join(
                    f"{int(s)} {row['mean']:+.1%} ({int(row['size'])})"
                    for s, row in per_season.iterrows()
                ) or "no season had enough bets")
        )
        entry.bars.append(
            Bar("sample", len(rows) >= MINIMUM_BETS,
                f"{len(rows):,} bets against a declared minimum of {MINIMUM_BETS}")
        )
        evidence.append(entry)

    result = EvidenceBundle(league=league.key, markets=evidence)
    result.inputs = {
        "Bought population": (
            f"816 games across {seasons[0]}-{seasons[-1]} — **every NFL game "
            "for which historical props exist.** The provider serves them "
            "only after 2023-05-03, so there is no more to buy."
        ),
        "Snapshots per game": "two priced (card time and the close), three bought",
        "Null baseline": f"{NULL_BASELINE_ROI:+.1%} betting everything — harness sound",
        "Family correction": f"Bonferroni across {families} markets (x{factor:.2f})",
        "Settlement screen": f"{len(suspects)} suspect(s): {', '.join(sorted(suspects)) or 'none'}",
        "Selection gate": (
            "no player prop can produce a selection until the verdict "
            "`props_selectable_when_undesignated` is in force, which waits on "
            "one line in a book's did-not-play rules"
        ),
    }
    result.caveats = [
        "**The did-not-play rule.** Every return here assumes a book voids a "
        "prop for a player who takes no snap. If it grades them as losses, "
        "`rush_yards` is −0.8% rather than +13.0%. One line in a book's rules, "
        "and no measurement can settle it.",
        "**The mechanism is not understood.** The compound-simulation markets "
        "pool to +3.5% at the consensus price (interval +1.4% to +5.7% over "
        "100,230 bets) and the count-only markets to −9.8%. That split is the "
        "strongest structure in the evidence and nothing here explains it.",
        "**The population cannot grow.** All 816 available games are bought. "
        "The only further evidence is forward, from 2026-09-09, at 272 games "
        "a season.",
        "**The NHL lab went the other way at scale**: +1.4% over 4,830 bets "
        "became −1.6% over 73,918 on its full population, and its approval was "
        "withdrawn. That is the direction of surprise to expect.",
    ]

    report = bundle_module.render(result)
    (OUTPUTS_DIR / league.output_name("allowlist_evidence", ".md")).write_text(
        report, encoding="utf-8"
    )
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
