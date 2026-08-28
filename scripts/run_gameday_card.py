#!/usr/bin/env python3
"""Produce the card, freeze its opinions, and settle the days that are final.

    PYTHONPATH=src python scripts/run_gameday_card.py --live --credit-cap 1400

Without `--live` nothing is fetched and no credit is spent; the card is built
from whatever is already staged, which is how the whole path is exercised in
CI without a credential.

**The card produces no selections today**, and that is correct: no market has
a reviewed approval. What it does produce is a frozen record of what the model
believed before kickoff, which is the only evidence that cannot be created
later.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

from football_betting_lab.config import (
    ARCHIVE_DIR,
    OUTPUTS_DIR,
    PROCESSED_DIR,
    RAW_DIR,
    STAGING_DIR,
)
from football_betting_lab.data.build_datasets import (
    PLAYER_LOGS_FILENAME,
    TEAM_GAMES_FILENAME,
)
from football_betting_lab.forward_evidence import (
    LEDGER_FILENAME,
    append_ledger,
    settle_snapshot,
    snapshots_dir,
    write_snapshot,
)
from football_betting_lab.leagues import DEFAULT_LEAGUE_KEY, league_for
from football_betting_lab.models.player_props import load_play_yardage
from football_betting_lab.models.scoring import (
    distribution_for,
    empirical_pmf,
    fit_ratings,
)
from football_betting_lab.providers.env_file import load_provider_env, redact
from football_betting_lab.providers.odds_api import (
    STAGING_PRICES_FILENAME,
    OddsApiProvider,
    ProviderError,
)
from football_betting_lab.providers.team_names import name_to_abbreviation, resolve_team
from football_betting_lab.reports import gameday_card, provider_shadow
from football_betting_lab.reports.card_pricing import PlayerBook, price_slate
from football_betting_lab.rosters import Rosters
from football_betting_lab.season import game_date
from football_betting_lab.selection import selection_key


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", default=DEFAULT_LEAGUE_KEY)
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--tier", type=int, default=1)
    parser.add_argument("--horizon-days", type=int, default=1)
    parser.add_argument("--credit-cap", type=int, default=0)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--draws", type=int, default=20_000)
    parser.add_argument(
        "--slate-date",
        default="",
        help=(
            "Price a specific league date from what is already staged, rather "
            "than today. For replaying a board and for exercising the whole "
            "path offline; it never changes what a live run does."
        ),
    )
    args = parser.parse_args(argv)

    league = league_for(args.league)
    now = datetime.now(timezone.utc)
    slate_date = args.slate_date or game_date(now.isoformat(), league)
    preseason: list[str] = []

    # -- prices ----------------------------------------------------------
    if args.live:
        if args.credit_cap <= 0:
            print("::error::--live requires a positive --credit-cap.", file=sys.stderr)
            return 2
        load_provider_env()
        try:
            run = provider_shadow.run_shadow(
                OddsApiProvider(league),
                league,
                raw_dir=RAW_DIR,
                season=args.season,
                horizon_days=args.horizon_days,
                credit_cap=args.credit_cap,
                now=now,
                tier=args.tier,
            )
        except ProviderError as exc:
            print(redact(f"The fetch failed: {exc}"), file=sys.stderr)
            return 2
        provider_shadow.write_staging(run, STAGING_DIR)
        preseason = list(run.preseason_excluded)
        print(run.summary_line())

    staged = STAGING_DIR / STAGING_PRICES_FILENAME
    prices = (
        pd.read_csv(staged)
        if staged.is_file()
        else pd.DataFrame(columns=["market", "home_team", "away_team"])
    )
    # Only today's slate reaches the card. The staged file legitimately spans
    # days, and pricing tomorrow's games into today's snapshot would freeze
    # opinions the card never held.
    if not prices.empty and "date" in prices.columns:
        prices = prices[prices["date"].astype(str) == slate_date].copy()

    # -- models ----------------------------------------------------------
    games = _read(PROCESSED_DIR / TEAM_GAMES_FILENAME)
    logs = _read(PROCESSED_DIR / PLAYER_LOGS_FILENAME)
    lookup = name_to_abbreviation(league)
    distributions = {}
    player_ids: dict[str, str] = {}

    if not prices.empty and not games.empty:
        played = games.dropna(subset=["home_score", "away_score"])
        pmf = empirical_pmf(
            list(played["home_score"].astype(int))
            + list(played["away_score"].astype(int))
        )
        ratings = fit_ratings(games, before=slate_date)
        for home, away in (
            prices[["home_team", "away_team"]].drop_duplicates().itertuples(index=False)
        ):
            home_key = resolve_team(home, league, lookup)
            away_key = resolve_team(away, league, lookup)
            if home_key and away_key:
                distributions[(home, away)] = distribution_for(
                    ratings, pmf, home_team=home_key, away_team=away_key
                )
        rosters = Rosters.load(league, RAW_DIR, season=args.season)
        for row in prices.dropna(subset=["player"]).itertuples():
            resolution = rosters.resolve(
                row.player,
                home=resolve_team(row.home_team, league, lookup) or "",
                away=resolve_team(row.away_team, league, lookup) or "",
            )
            if resolution.resolved:
                player_ids[str(row.player).casefold()] = resolution.entry.player_id

    book = PlayerBook(
        logs,
        load_play_yardage(PROCESSED_DIR),
        before=f"{args.season}01",
        draws=args.draws,
    )
    probabilities, diagnostics = price_slate(
        prices, league, distributions=distributions, book=book, player_ids=player_ids
    )

    # -- the card --------------------------------------------------------
    from football_betting_lab.staging_provider_policy import StagingProviderPolicy

    policy = StagingProviderPolicy.load()
    card = gameday_card.build_card(
        prices,
        league,
        policy=policy,
        diagnostics=diagnostics,
        now=now,
        slate_date=slate_date,
        preseason_excluded=preseason,
    )

    # -- freeze, then settle --------------------------------------------
    frozen = write_snapshot(
        prices,
        probabilities,
        key_for=lambda row, *, market, selection, line: selection_key(
            row, market=market, selection=selection, line=line, league=league
        ),
        gates_in_force=policy.summary_line(league),
        snapshot_date=slate_date,
        archive_dir=ARCHIVE_DIR,
    )
    if frozen is None:
        card.notes.append(
            f"A snapshot for {slate_date} already stands and was not "
            "overwritten. The first opinion of the day is the one that settles."
        )
    else:
        card.frozen_rows = len(pd.read_csv(frozen)) if frozen.is_file() else 0

    ledger_path = PROCESSED_DIR / LEDGER_FILENAME
    settled_days = _settle_pending(
        league, games, logs, lookup, ledger_path, as_of=now.date()
    )
    if settled_days:
        card.notes.append(
            f"Settled {settled_days} snapshot day(s) into the ledger this run."
        )
    if ledger_path.is_file():
        card.ledger_rows = len(pd.read_csv(ledger_path))

    report = gameday_card.render(card)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUTS_DIR / league.output_name("gameday_card", ".md")).write_text(
        report, encoding="utf-8"
    )
    print()
    print(report)
    print(f"decision={card.decision}")
    return 0


def _read(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False) if path.is_file() else pd.DataFrame()


def _settle_pending(
    league, games, logs, lookup, ledger_path: Path, *, as_of: date
) -> int:
    """Settle every snapshot day that is not already in the ledger.

    Day-as-unit: a partially settled day would let the early games in and
    leave the late ones out, and the late window is a systematically
    different set of fixtures.
    """
    directory = snapshots_dir(ARCHIVE_DIR)
    if not directory.is_dir() or games.empty:
        return 0
    already: set[str] = set()
    if ledger_path.is_file():
        already = set(pd.read_csv(ledger_path)["snapshot_date"].astype(str))

    team_lookup = {name: resolve_team(name, league, lookup) for name in lookup}
    settled_days = 0
    for path in sorted(directory.glob("*.csv")):
        day = path.stem
        if day in already or day >= as_of.isoformat():
            continue
        snapshot = pd.read_csv(path)
        if snapshot.empty:
            continue
        names = set(snapshot["home_team"].astype(str)) | set(
            snapshot["away_team"].astype(str)
        )
        team_lookup.update(
            {name: resolve_team(name, league, lookup) or "" for name in names}
        )
        result = settle_snapshot(
            snapshot,
            games=games,
            logs=logs,
            league=league,
            team_lookup=team_lookup,
            as_of=as_of,
        )
        if append_ledger(result.settled, ledger_path):
            settled_days += 1
    return settled_days


if __name__ == "__main__":
    raise SystemExit(main())
