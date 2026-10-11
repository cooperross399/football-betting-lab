#!/usr/bin/env python3
"""What being "due" for a touchdown has been worth. Spends nothing.

    PYTHONPATH=src python scripts/run_td_due_list_backtest.py \
        [--logs data/processed/player_game_logs.csv] [--prices-dir DIR]

Two questions, asked of the rule in `football_betting_lab.td_due_list` exactly
as the card applies it, with its parameters fixed before either was asked:

1. **Hit rate (free, every season the logs hold).** Do listed players score
   more often than the same qualifiers when they are not due, and more often
   than their own last-season rate? The gambler's-fallacy reading of "due" says
   yes; a drought that means a lost role says no. Interval: bootstrap over
   season-weeks, because every row of one week shares its slate.

2. **Price (the bought 2023-25 anytime prices, card-time snapshot).** Betting
   every listed player's anytime over at the best posted price, flat stake,
   and at the median book's price. Beside it, the same qualifiers when not
   listed and every priced anytime over, so the vig has a baseline. Intervals
   are clustered by game (`props_backtest._interval`). An interval that
   includes zero is "no demonstrated edge", in those words.

The bought prices live in the Historical Purchase artifact, not in git, so the
priced half runs in the `TD Due List Backtest` workflow, which restores them.
Without them the script writes the hit-rate half and says the priced half did
not run.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from football_betting_lab import td_due_list as due
from football_betting_lab.config import OUTPUTS_DIR, PROCESSED_DIR, RAW_DIR
from football_betting_lab.data.build_datasets import PLAYER_LOGS_FILENAME
from football_betting_lab.forward_evidence import profit_on_win
from football_betting_lab.leagues import NFL
from football_betting_lab.providers.historical import CACHE_DIRNAME
from football_betting_lab.providers.team_names import name_to_abbreviation, resolve_team
from football_betting_lab.reports.props_backtest import (
    CARD_TIME,
    _game_id,
    _game_weeks,
    _interval,
    best_price_per_selection,
    events_in_season,
    label_snapshots,
    load_bought_prices,
)
from football_betting_lab.rosters import Rosters

BOOTSTRAP_DRAWS = 2000
SEED = 20261011
PRICED_SEASONS = (2023, 2024, 2025)


def _bootstrap_diff(frame: pd.DataFrame, value, *, draws: int = BOOTSTRAP_DRAWS) -> tuple[float, float]:
    """95% interval of `value(frame)` resampling whole season-weeks."""
    groups = [g for _, g in frame.groupby(["season", "week"])]
    if len(groups) < 2:
        return float("-inf"), float("inf")
    rng = np.random.default_rng(SEED)
    stats = []
    for _ in range(draws):
        pick = rng.integers(0, len(groups), len(groups))
        stats.append(value(pd.concat([groups[i] for i in pick], ignore_index=True)))
    low, high = np.nanpercentile(stats, [2.5, 97.5])
    return float(low), float(high)


def hit_rate_half(prepared: pd.DataFrame) -> dict:
    qualified = prepared[prepared["bar"].notna()].copy()
    seasons = sorted(qualified["season"].unique())
    if not seasons:
        return {}

    def gap(frame: pd.DataFrame) -> float:
        listed = frame[frame["listed"]]["scored"]
        others = frame[~frame["listed"]]["scored"]
        if listed.empty or others.empty:
            return float("nan")
        return float(listed.mean() - others.mean())

    def own_gap(frame: pd.DataFrame) -> float:
        listed = frame[frame["listed"]]
        return float((listed["scored"].astype(float) - listed["prior_rate"]).mean()) if len(listed) else float("nan")

    listed = qualified[qualified["listed"]]
    others = qualified[~qualified["listed"]]
    low, high = _bootstrap_diff(qualified, gap)
    own_low, own_high = _bootstrap_diff(qualified, own_gap)
    by_band = []
    for floor, bar in due.TIERS:
        band = due.band_label(floor)
        rows = qualified[qualified["prior_tds"].map(due.band_label) == band]
        b_listed = rows[rows["listed"]]
        b_others = rows[~rows["listed"]]
        by_band.append(
            {
                "band": band,
                "bar": bar,
                "listed_n": int(len(b_listed)),
                "listed_rate": float(b_listed["scored"].mean()) if len(b_listed) else None,
                "others_n": int(len(b_others)),
                "others_rate": float(b_others["scored"].mean()) if len(b_others) else None,
                "prior_rate": float(rows["prior_rate"].mean()) if len(rows) else None,
            }
        )
    by_drought = []
    for lo, hi, label in ((0, 0, "0"), (1, 1, "1"), (2, 2, "2"), (3, 3, "3"), (4, 4, "4"), (5, 6, "5-6"), (7, 999, "7+")):
        rows = qualified[qualified["drought"].between(lo, hi)]
        by_drought.append(
            {
                "drought": label,
                "n": int(len(rows)),
                "rate": float(rows["scored"].mean()) if len(rows) else None,
                "prior_rate": float(rows["prior_rate"].mean()) if len(rows) else None,
            }
        )
    return {
        "first_season": int(seasons[0]),
        "last_season": int(seasons[-1]),
        "listed_n": int(len(listed)),
        "listed_rate": float(listed["scored"].mean()) if len(listed) else None,
        "listed_prior_rate": float(listed["prior_rate"].mean()) if len(listed) else None,
        "others_n": int(len(others)),
        "others_rate": float(others["scored"].mean()) if len(others) else None,
        "gap": gap(qualified),
        "gap_low": low,
        "gap_high": high,
        "own_gap": own_gap(qualified),
        "own_gap_low": own_low,
        "own_gap_high": own_high,
        "by_band": by_band,
        "by_drought": by_drought,
    }


def _summary(bets: pd.DataFrame, price_column: str) -> dict:
    staked = bets.dropna(subset=[price_column])
    if staked.empty:
        return {"bets": 0}
    profit = np.where(staked["scored"], staked[price_column].map(profit_on_win), -1.0)
    frame = staked.assign(profit=profit)
    per_game = frame.groupby("event_id").agg(profit=("profit", "sum"), bets=("profit", "size"))
    roi, low, high = _interval(per_game)
    return {
        "bets": int(len(frame)),
        "games": int(len(per_game)),
        "hits": int(frame["scored"].sum()),
        "hit_rate": float(frame["scored"].mean()),
        "implied": float(frame[price_column].map(_implied).mean()),
        "roi": roi,
        "low": low,
        "high": high,
    }


def _implied(odds: float) -> float:
    return 100.0 / (odds + 100.0) if odds > 0 else -odds / (-odds + 100.0)


def priced_half(prepared: pd.DataFrame, logs: pd.DataFrame, prices_dir: Path) -> tuple[dict, pd.DataFrame]:
    raw = load_bought_prices(prices_dir, NFL)
    if raw.empty:
        return {}, pd.DataFrame()
    raw = label_snapshots(raw)
    raw = raw[(raw["phase"] == CARD_TIME) & (raw["market"] == due.MARKET) & (raw["selection"] == "over")].copy()
    raw["line"] = pd.to_numeric(raw["line"], errors="coerce")
    raw["american_odds"] = pd.to_numeric(raw["american_odds"], errors="coerce")
    raw = raw[(raw["line"] == due.LINE)].dropna(subset=["american_odds"])
    best = best_price_per_selection(raw)
    lookup = name_to_abbreviation(NFL)
    state = prepared.set_index(["game_id", "player_id"])
    rows: list[dict] = []
    unresolved = 0
    for season in PRICED_SEASONS:
        sub = events_in_season(raw, NFL, season)
        if sub.empty:
            continue
        weeks = _game_weeks(logs, sub, NFL, season)
        rosters = Rosters.load(NFL, RAW_DIR, season=season)
        best_season = best[best["event_id"].isin(sub["event_id"].unique())]
        for event_id, frame in sub.groupby("event_id"):
            week = weeks.get(str(event_id))
            if week is None:
                continue
            first = frame.iloc[0]
            home = resolve_team(first["home_team"], NFL, lookup) or ""
            away = resolve_team(first["away_team"], NFL, lookup) or ""
            game_id = _game_id(logs, season, week, home, away)
            medians = frame.groupby("player")["american_odds"].median()
            for quote in best_season[best_season["event_id"] == event_id].itertuples():
                resolution = rosters.resolve(quote.player, home=home, away=away)
                if not resolution.resolved:
                    unresolved += 1
                    continue
                key = (game_id, resolution.entry.player_id)
                if key not in state.index:
                    # He did not appear: a void, the stake comes back.
                    continue
                entry = state.loc[key]
                if isinstance(entry, pd.DataFrame):
                    entry = entry.iloc[0]
                rows.append(
                    {
                        "season": season,
                        "week": week,
                        "event_id": str(event_id),
                        "player_id": resolution.entry.player_id,
                        "player": quote.player,
                        "best": float(quote.american_odds),
                        "consensus": float(medians.get(quote.player, np.nan)),
                        "scored": bool(entry["scored"]),
                        "qualified": bool(pd.notna(entry["bar"])),
                        "listed": bool(entry["listed"]),
                        "band": due.band_label(entry["prior_tds"]) or "",
                        "drought": int(entry["drought"]),
                    }
                )
    bets = pd.DataFrame(rows)
    if bets.empty:
        return {"unresolved": unresolved}, bets
    listed = bets[bets["listed"]]
    others = bets[bets["qualified"] & ~bets["listed"]]
    result = {
        "seasons": f"{PRICED_SEASONS[0]}-{str(PRICED_SEASONS[-1])[2:]}",
        "unresolved": unresolved,
        "listed_best": _summary(listed, "best"),
        "listed_consensus": _summary(listed, "consensus"),
        "others_best": _summary(others, "best"),
        "everyone_best": _summary(bets, "best"),
        "by_season": [
            {"season": int(s), **_summary(listed[listed["season"] == s], "best")}
            for s in PRICED_SEASONS
        ],
        "by_band": [
            {"band": due.band_label(floor), **_summary(listed[listed["band"] == due.band_label(floor)], "best")}
            for floor, _ in due.TIERS
        ],
    }
    return result, bets


def _pct(value) -> str:
    return "—" if value is None or (isinstance(value, float) and np.isnan(value)) else f"{value:+.1%}"


def _rate(value) -> str:
    return "—" if value is None else f"{value:.1%}"


def _verdict(low: float, high: float) -> str:
    if low <= 0.0 <= high:
        return "no demonstrated edge"
    return "interval excludes zero, " + ("positive" if low > 0 else "negative")


def render(payload: dict) -> str:
    hits = payload.get("hit_rate") or {}
    priced = payload.get("priced_detail") or {}
    out = ["# NFL TD Due List backtest", ""]
    out.append(
        f"The rule: {due.THRESHOLD}+ touchdowns scored last regular season, listed on a "
        "drought of " + ", ".join(f"{bar}+ games for {due.band_label(f)}" for f, bar in due.TIERS)
        + ". Parameters fixed before any outcome or price was compared "
        "(`src/football_betting_lab/td_due_list.py`). Generated by "
        "`scripts/run_td_due_list_backtest.py`; data from nflverse under CC-BY-4.0."
    )
    out.append("")
    out.append("## 1. Do due players score more often?")
    out.append("")
    if hits:
        out.append(
            f"Regular seasons {hits['first_season']}-{hits['last_season']}, every logged game of a qualifier."
        )
        out.append("")
        out.append("| | Games | Scored | Their last-season rate |")
        out.append("|:--|--:|--:|--:|")
        out.append(f"| Listed (due) | {hits['listed_n']:,} | {_rate(hits['listed_rate'])} | {_rate(hits['listed_prior_rate'])} |")
        out.append(f"| Same qualifiers, not due | {hits['others_n']:,} | {_rate(hits['others_rate'])} | — |")
        out.append("")
        out.append(
            f"Due minus not due: **{_pct(hits['gap'])}** (95% {_pct(hits['gap_low'])} to "
            f"{_pct(hits['gap_high'])}, bootstrap over season-weeks). Due minus his own "
            f"last-season rate: **{_pct(hits['own_gap'])}** ({_pct(hits['own_gap_low'])} to "
            f"{_pct(hits['own_gap_high'])})."
        )
        out.append("")
        out.append("| Drought entering | Games | Scored | Last-season rate |")
        out.append("|:--|--:|--:|--:|")
        for row in hits["by_drought"]:
            out.append(f"| {row['drought']} | {row['n']:,} | {_rate(row['rate'])} | {_rate(row['prior_rate'])} |")
        out.append("")
        out.append("| Band | Bar | Listed games | Listed scored | Not due games | Not due scored |")
        out.append("|:--|--:|--:|--:|--:|--:|")
        for row in hits["by_band"]:
            out.append(
                f"| {row['band']} | {row['bar']} | {row['listed_n']:,} | {_rate(row['listed_rate'])} | "
                f"{row['others_n']:,} | {_rate(row['others_rate'])} |"
            )
    else:
        out.append("No qualifier rows: the logs hold too few seasons.")
    out.append("")
    out.append("## 2. Against the price")
    out.append("")
    if not priced or not priced.get("listed_best", {}).get("bets"):
        out.append(
            "**Did not run here**: the bought prices are not in this checkout. The "
            "`TD Due List Backtest` workflow restores them from the Historical Purchase artifact."
        )
        return "\n".join(out) + "\n"
    out.append(
        f"Bought anytime prices {priced['seasons']}, card-time snapshot, over {due.LINE}, flat 1u stake. "
        "A player who did not appear is a void. Intervals clustered by game."
    )
    out.append("")
    out.append("| Wagers | Bets | Games | Scored | Price implied | ROI | 95% | Verdict |")
    out.append("|:--|--:|--:|--:|--:|--:|:--|:--|")
    for label, key in (
        ("Listed, best price", "listed_best"),
        ("Listed, median book", "listed_consensus"),
        ("Qualifiers not due, best price", "others_best"),
        ("Every priced anytime over, best price", "everyone_best"),
    ):
        s = priced.get(key) or {}
        if not s.get("bets"):
            out.append(f"| {label} | 0 | | | | | | |")
            continue
        out.append(
            f"| {label} | {s['bets']:,} | {s['games']:,} | {s['hit_rate']:.1%} | {s['implied']:.1%} | "
            f"{s['roi']:+.1%} | {s['low']:+.1%} to {s['high']:+.1%} | {_verdict(s['low'], s['high'])} |"
        )
    out.append("")
    out.append("| Listed, by season | Bets | ROI | 95% |")
    out.append("|:--|--:|--:|:--|")
    for s in priced["by_season"]:
        if s.get("bets"):
            out.append(f"| {s['season']} | {s['bets']:,} | {s['roi']:+.1%} | {s['low']:+.1%} to {s['high']:+.1%} |")
    out.append("")
    out.append("| Listed, by band | Bets | ROI | 95% |")
    out.append("|:--|--:|--:|:--|")
    for s in priced["by_band"]:
        if s.get("bets"):
            out.append(f"| {s['band']} | {s['bets']:,} | {s['roi']:+.1%} | {s['low']:+.1%} to {s['high']:+.1%} |")
    out.append("")
    out.append(f"Price names the roster could not resolve: {priced.get('unresolved', 0):,}.")
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--logs", type=Path, default=PROCESSED_DIR / PLAYER_LOGS_FILENAME)
    parser.add_argument("--prices-dir", type=Path, default=RAW_DIR / NFL.data_dir_segment / CACHE_DIRNAME)
    parser.add_argument("--outputs-dir", type=Path, default=OUTPUTS_DIR)
    args = parser.parse_args(argv)

    if not args.logs.is_file():
        print(f"No player logs at {args.logs}. Build them with scripts/build_datasets.py.", file=sys.stderr)
        return 2
    logs = pd.read_csv(args.logs, low_memory=False)
    prepared = due.prepare_logs(logs)
    hits = hit_rate_half(prepared)
    priced, bets = priced_half(prepared, logs, args.prices_dir)

    payload: dict = {"rule": {"threshold": due.THRESHOLD, "tiers": [list(t) for t in due.TIERS]}}
    payload["hit_rate"] = hits
    if priced.get("listed_best", {}).get("bets"):
        payload["priced"] = {"seasons": priced["seasons"], **priced["listed_best"]}
    payload["priced_detail"] = priced or None

    args.outputs_dir.mkdir(parents=True, exist_ok=True)
    (args.outputs_dir / due.backtest_json_name(NFL)).write_text(
        json.dumps(payload, indent=2, default=float) + "\n", encoding="utf-8"
    )
    report = render(payload)
    (args.outputs_dir / NFL.output_name(due.BACKTEST_STEM, ".md")).write_text(report, encoding="utf-8")
    if not bets.empty:
        bets.to_csv(args.outputs_dir / NFL.output_name("td_due_list_backtest_bets", ".csv"), index=False)
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
