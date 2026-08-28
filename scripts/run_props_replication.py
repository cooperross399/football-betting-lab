#!/usr/bin/env python3
"""Does anything replicate on a season it was not selected on?

    PYTHONPATH=src python scripts/run_props_replication.py --seasons 2023 2024 2025

`tackles_assists` returned +16.2% on 2025 and survived every check that could
be run for free: the halves agreed, 223 players were involved, the best game
was 7% of the profit. None of that is replication. **A market selected because
it looked good in a sample is exactly the market most likely to have looked
good by chance**, and the correction is not a wider interval — it is a season
the market was not selected on.

2025 is the selection season. 2023 and 2024 are held out. This script scores
all three the same way and reports them side by side, and the verdict for any
market rests on the held-out seasons alone.
"""

from __future__ import annotations

import argparse
import sys
from statistics import NormalDist

import pandas as pd

from football_betting_lab.config import OUTPUTS_DIR, PROCESSED_DIR, RAW_DIR
from football_betting_lab.data.build_datasets import PLAYER_LOGS_FILENAME
from football_betting_lab.leagues import DEFAULT_LEAGUE_KEY, league_for
from football_betting_lab.providers.historical import CACHE_DIRNAME
from football_betting_lab.reports import props_backtest
from football_betting_lab.reports.props_backtest import MINIMUM_BETS


#: The season the candidates were found in. Its numbers are reported and are
#: **not** evidence for anything that was selected on them.
SELECTION_SEASON = 2025


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", default=DEFAULT_LEAGUE_KEY)
    parser.add_argument("--seasons", type=int, nargs="+", default=[2023, 2024, 2025])
    parser.add_argument("--draws", type=int, default=4000)
    args = parser.parse_args(argv)

    league = league_for(args.league)
    cache = RAW_DIR / league.data_dir_segment / CACHE_DIRNAME
    logs_path = PROCESSED_DIR / PLAYER_LOGS_FILENAME
    if not cache.is_dir() or not logs_path.is_file():
        print("Bought prices or player logs are missing.", file=sys.stderr)
        return 2

    prices = props_backtest.load_bought_prices(cache, league)
    logs = pd.read_csv(logs_path, low_memory=False)

    per_season: dict[int, props_backtest.BacktestResult] = {}
    all_bets: list[pd.DataFrame] = []
    for season in args.seasons:
        print(f"scoring {season}...", flush=True)
        result = props_backtest.run(
            prices, logs, league, season=season, raw_dir=RAW_DIR,
            processed_dir=PROCESSED_DIR, draws=args.draws,
        )
        per_season[season] = result
        if not result.bets.empty:
            all_bets.append(result.bets.assign(season=season))
        print(f"  {season}: {result.pooled.bets:,} bets, {result.pooled.roi:+.1%}")

    held_out = [s for s in args.seasons if s != SELECTION_SEASON]
    markets = sorted({m.market for r in per_season.values() for m in r.markets})

    lines = ["# Does anything replicate?", ""]
    lines.append(
        f"**{SELECTION_SEASON} is the selection season.** `tackles_assists` "
        "was found there, and a market found in a sample is the market most "
        "likely to have looked good by chance. Its numbers are reported below "
        "and are not evidence for it. "
        + (
            f"The held-out seasons are {', '.join(str(s) for s in held_out)}."
            if held_out
            else "**No season is held out, so nothing here can replicate.**"
        )
    )
    lines.append("")
    header = "| Market | " + " | ".join(
        f"{s}{' (selection)' if s == SELECTION_SEASON else ''}" for s in args.seasons
    ) + " | Held-out verdict |"
    lines.append(header)
    lines.append("|:---|" + "---:|" * len(args.seasons) + ":---|")

    for market in markets:
        cells = []
        held_entries = []
        for season in args.seasons:
            entry = next(
                (m for m in per_season[season].markets if m.market == market), None
            )
            if entry is None or entry.bets < MINIMUM_BETS:
                cells.append(f"{entry.roi:+.1%} ({entry.bets})" if entry else "—")
            else:
                cells.append(f"**{entry.roi:+.1%}** ({entry.bets:,})")
            if entry is not None and season in held_out:
                held_entries.append(entry)
        lines.append(
            f"| `{market}` | " + " | ".join(cells) + " | "
            + _held_out_verdict(held_entries, len(markets)) + " |"
        )

    lines.append("")
    lines.append(
        f"Each cell is ROI with the bet count. **Bold** means the season "
        f"cleared the {MINIMUM_BETS}-bet minimum declared in advance; below it "
        "no verdict is offered however good the number looks."
    )
    lines.append("")
    lines.append(
        "The held-out verdict pools only the seasons a market was **not** "
        f"selected on, with a Bonferroni correction across the {len(markets)} "
        "markets tested. A market that cleared on the selection season and "
        "not here has not replicated, and that is the answer."
    )

    combined = pd.concat(all_bets, ignore_index=True) if all_bets else pd.DataFrame()
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUTS_DIR / league.output_name("props_replication", ".md")).write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    if not combined.empty:
        combined.to_csv(
            OUTPUTS_DIR / league.output_name("props_backtest_bets", ".csv"), index=False
        )
    print()
    print("\n".join(lines))
    return 0


def _held_out_verdict(entries: list, families: int) -> str:
    usable = [e for e in entries if e.bets >= MINIMUM_BETS]
    if not usable:
        return f"**not enough evidence** — {sum(e.bets for e in entries)} held-out bets"
    bets = sum(e.bets for e in usable)
    roi = sum(e.roi * e.bets for e in usable) / bets
    # Pool the per-season intervals conservatively: widen by the family
    # correction and take the union of the seasons' half-widths.
    factor = (
        NormalDist().inv_cdf(1 - (0.05 / max(families, 1)) / 2) / 1.96
        if families > 1
        else 1.0
    )
    half = max((e.high - e.low) / 2 for e in usable) * factor
    low, high = roi - half, roi + half
    if low <= 0 <= high:
        return f"**no demonstrated edge** — {roi:+.1%} over {bets:,} bets"
    direction = "positive" if low > 0 else "negative"
    return f"replicates {direction} — {roi:+.1%} over {bets:,} bets"


if __name__ == "__main__":
    raise SystemExit(main())
