#!/usr/bin/env python3
"""What a season of NFL prices costs, computed from the real schedule.

The Odds API quota is **shared with the NHL lab** — one account, one key pool,
two seasons that overlap from late September to April — and it **resets
monthly** (confirmed by Cooper, 2026-08-28). Both halves of that matter and
the second one was got wrong first: an earlier version of this script treated
100,000 as a single annual pool, concluded that buying historical prices was
impossible, and built a whole plan around the conclusion. It is not a pool. It
is 100,000 a month.

So the unit of this arithmetic is **the calendar month**, and the question is
not "does the season fit" but "does the worst month fit". It reports NFL and
NHL side by side per month, because a month is what they actually compete
for.

Billing rules, from the provider's own documentation (fetched 2026-08-28,
`https://the-odds-api.com/liveapi/guides/v4/#usage-quota-costs`):

* ``/v4/sports`` and ``/v4/sports/{sport}/events`` — **free**.
* ``/v4/sports/{sport}/odds`` (bulk) — ``markets x regions``, whole slate.
* ``/v4/sports/{sport}/events/{id}/odds`` (per event) — ``unique markets
  **returned** x regions``. An asked-for market nobody quotes costs nothing.
* ``/v4/sports/{sport}/scores?daysFrom=N`` — 2.
* Historical equivalents — **10x** the live rate.

Two bounds are printed for every scenario, and the difference between them is
the whole reason this script exists:

**Pessimistic** assumes every asked market is quoted and billed. This is what
the daily cap is set against, because a cap that trusts the optimistic bound
is not a cap.

**Optimistic** assumes only the featured markets are quoted. It is printed so
the gap is visible, never so it can be planned against.

    PYTHONPATH=src python scripts/estimate_credit_cost.py
    PYTHONPATH=src python scripts/estimate_credit_cost.py --json out.json

Nothing here touches the network or spends a credit.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from dataclasses import dataclass, asdict
from pathlib import Path

from football_betting_lab.leagues import NFL, league_for
from football_betting_lab.season import schedule_path
from football_betting_lab import markets as market_registry


PROJECT_ROOT = Path(__file__).resolve().parents[1]
# The league supplies its own directory segment. A hardcoded "nfl" here is
# exactly the literal the registry exists to prevent, and the discipline
# test fails the build when one appears.
# ...and the FILE comes from the same place every other reader gets it, which
# is the one the fetcher writes. This used to name a second, frozen copy that
# no fetch ever updated.
SCHEDULE_CSV = schedule_path(NFL, PROJECT_ROOT / "data" / "raw")

#: The season this lab is being built for.
SEASON = 2026

#: One region. Every extra region multiplies every figure below, which is why
#: the number is named here rather than appearing inline in a URL.
REGIONS = 1

#: The quota, **per calendar month**. Confirmed by Cooper on 2026-08-28.
#: The reset day itself is not yet known and is not assumed: the lab detects
#: it by watching `x-requests-used` fall in the response headers, which costs
#: nothing. Until it is known, a purchase that needs most of a month is
#: planned as though the reset were the least convenient day it could be.
MONTHLY_QUOTA = 100_000

#: The NHL lab's asked per-event market count, from its own operating file
#: (`nhl-betting-lab/CLAUDE.md`, "Current operating state").
NHL_MARKETS_PER_EVENT = 19

#: The NHL 2026-27 regular season by calendar month, derived on 2026-08-28
#: from the league's own club-schedule endpoint — 1,344 games over 185 game
#: days, maximum 16 in a night. Those three totals match the NHL lab's
#: recorded figures exactly, which is the cross-check that makes this table
#: safe to use: it is a re-derivation of their number, not a second guess at
#: it. The credits it implies (26,461) land within 1.4% of the 26,091 they
#: record, the difference being how each counts the per-day bulk and scores
#: calls.
NHL_SEASON_BY_MONTH: dict[str, tuple[int, int]] = {
    # month: (games, game days)
    "2026-09": (8, 2),
    "2026-10": (218, 31),
    "2026-11": (209, 28),
    "2026-12": (214, 28),
    "2027-01": (231, 31),
    "2027-02": (155, 24),
    "2027-03": (227, 31),
    "2027-04": (82, 10),
}
NHL_DERIVED_AS_OF = "2026-08-28"




@dataclass(frozen=True)
class Scenario:
    name: str
    detail: str
    bulk_markets: int
    per_event_markets: int


@dataclass
class MonthRow:
    month: str
    nfl_games: int
    nfl_days: int
    nfl_credits: int
    nhl_games: int
    nhl_days: int
    nhl_credits: int

    @property
    def combined(self) -> int:
        return self.nfl_credits + self.nhl_credits

    @property
    def headroom(self) -> int:
        return MONTHLY_QUOTA - self.combined


@dataclass
class Estimate:
    scenario: str
    detail: str
    bulk_markets: int
    per_event_markets: int
    game_days: int
    games: int
    season_credits: int
    months: list[MonthRow]
    worst_month: str
    worst_month_credits: int
    worst_day_games: int
    worst_day_credits: int
    daily_cap_needed: int
    spare_in_worst_month: int
    total_spare_over_the_overlap: int


def load_schedule(path: Path, season: int) -> list[dict[str, str]]:
    """Regular-season games for one season, from the cached nflverse file.

    Read from a cached copy on purpose. A schedule refetched on every run
    makes the arithmetic depend on when it was computed, and the point of
    this file is that Cooper can check the number later and get the same one.
    """
    if not path.is_file():
        raise SystemExit(
            f"No cached schedule at {path}. Fetch it first:\n"
            f"  curl -sSL -o {path} \\\n"
            "    https://github.com/nflverse/nflverse-data/releases/download/"
            "schedules/games.csv"
        )
    with path.open(newline="", encoding="utf-8") as handle:
        rows = [
            row
            for row in csv.DictReader(handle)
            if row.get("season") == str(season) and row.get("game_type") == "REG"
        ]
    if not rows:
        raise SystemExit(
            f"The cached schedule has no {season} regular-season games. "
            "It may predate the schedule release."
        )
    return rows


def _credits(games: int, days: int, markets_per_event: int, bulk_markets: int) -> int:
    """One day's bulk call, one per-event call per game, one scores call.

    The pessimistic bound: every asked market quoted and billed. The per-event
    endpoint bills only markets it actually returns, so real spend is lower —
    but a cap set against the optimistic bound is not a cap.
    """
    return (
        days * bulk_markets * REGIONS
        + games * markets_per_event * REGIONS
        + days * 2
    )


def estimate(scenario: Scenario, games: list[dict[str, str]]) -> Estimate:
    per_day = Counter(row["gameday"] for row in games)
    nfl_games_by_month = Counter(row["gameday"][:7] for row in games)
    nfl_days_by_month = Counter(day[:7] for day in per_day)

    months = sorted(set(nfl_games_by_month) | set(NHL_SEASON_BY_MONTH))
    rows: list[MonthRow] = []
    for month in months:
        nhl_games, nhl_days = NHL_SEASON_BY_MONTH.get(month, (0, 0))
        rows.append(
            MonthRow(
                month=month,
                nfl_games=nfl_games_by_month.get(month, 0),
                nfl_days=nfl_days_by_month.get(month, 0),
                nfl_credits=_credits(
                    nfl_games_by_month.get(month, 0),
                    nfl_days_by_month.get(month, 0),
                    scenario.per_event_markets,
                    scenario.bulk_markets,
                ),
                nhl_games=nhl_games,
                nhl_days=nhl_days,
                # The NHL lab asks 19 per-event markets and the same three
                # featured ones. Its own figure, not a re-modelling of it.
                nhl_credits=_credits(nhl_games, nhl_days, NHL_MARKETS_PER_EVENT, 3),
            )
        )

    worst = max(rows, key=lambda r: r.combined)
    worst_day_games = max(per_day.values())
    worst_day = (
        scenario.bulk_markets * REGIONS
        + worst_day_games * scenario.per_event_markets * REGIONS
        + 2
    )
    return Estimate(
        scenario=scenario.name,
        detail=scenario.detail,
        bulk_markets=scenario.bulk_markets,
        per_event_markets=scenario.per_event_markets,
        game_days=len(per_day),
        games=len(games),
        season_credits=sum(r.nfl_credits for r in rows),
        months=rows,
        worst_month=worst.month,
        worst_month_credits=worst.combined,
        worst_day_games=worst_day_games,
        worst_day_credits=worst_day,
        # Rounded up to the next hundred so a market added mid-season does not
        # silently clip a slate before anyone notices.
        daily_cap_needed=((worst_day + 99) // 100) * 100,
        spare_in_worst_month=worst.headroom,
        total_spare_over_the_overlap=sum(r.headroom for r in rows),
    )


def scenarios() -> tuple[Scenario, ...]:
    tier1_bulk = len(market_registry.bulk_provider_keys(1))
    tier1_per_event = len(market_registry.per_event_provider_keys(1))
    tier2_per_event = len(market_registry.per_event_provider_keys(2))
    return (
        Scenario(
            name="featured only",
            detail=(
                "Moneyline, spread and total from the bulk endpoint. No "
                "per-event call at all. The cheapest thing that can still "
                "freeze an opinion and settle it."
            ),
            bulk_markets=tier1_bulk,
            per_event_markets=0,
        ),
        Scenario(
            name="tier 1",
            detail=(
                "The bulk three, seven per-event team markets, twenty player "
                "props and their nineteen alternate ladders."
            ),
            bulk_markets=tier1_bulk,
            per_event_markets=tier1_per_event,
        ),
        Scenario(
            name="tier 1 + 2",
            detail=(
                "Everything this lab has wired and can settle: adds the "
                "quarter ladder, the second-half markets, the tie, the "
                "touchdown-order props and the composite yardage props."
            ),
            bulk_markets=tier1_bulk,
            per_event_markets=tier2_per_event,
        ),
        Scenario(
            name="full documented catalogue",
            detail=(
                "Every NFL market the provider documents, including the "
                "quarter alternate ladders this lab has not wired."
            ),
            bulk_markets=3,
            per_event_markets=111,
        ),
    )


def render(estimates: list[Estimate]) -> str:
    league = league_for(NFL.key)
    lines: list[str] = []
    add = lines.append
    add(f"# What a {SEASON} {league.title} season costs in Odds API credits")
    add("")
    add(
        f"Computed from the cached nflverse schedule: **{estimates[0].games} "
        f"regular-season games across {estimates[0].game_days} game days**, "
        f"one region (`{'us'}`), each game fetched once on its own game day."
    )
    add("")
    add(
        f"**The quota is {MONTHLY_QUOTA:,} per calendar month**, shared with "
        "the NHL lab, whose season overlaps this one from late September to "
        "January. So the unit here is the month, and the question is whether "
        "the *worst* month fits."
    )
    add("")
    add("| Scenario | Markets/event | NFL season | Worst month | NFL+NHL that "
        "month | Spare | Worst slate | Daily cap |")
    add("|:---------|--------------:|-----------:|:------------|-------------"
        "------:|------:|------------:|----------:|")
    for item in estimates:
        add(
            f"| {item.scenario} | {item.per_event_markets} | "
            f"{item.season_credits:,} | {item.worst_month} | "
            f"{item.worst_month_credits:,} | "
            f"{item.spare_in_worst_month:,} | {item.worst_day_games} games = "
            f"{item.worst_day_credits:,} | {item.daily_cap_needed:,} |"
        )
    add("")
    add("Every figure is the **pessimistic** bound: every asked market quoted "
        "and billed. The per-event endpoint bills only markets it returns, so "
        "real spend is lower — but a cap set against the optimistic bound is "
        "not a cap.")
    add("")

    chosen = next(e for e in estimates if e.scenario == "tier 1 + 2")
    add(f"## Month by month, at **{chosen.scenario}**")
    add("")
    add("| Month | NFL games | NFL credits | NHL games | NHL credits | "
        f"Combined | Spare of {MONTHLY_QUOTA:,} |")
    add("|:------|----------:|------------:|----------:|------------:|"
        "---------:|-----------:|")
    for row in chosen.months:
        add(
            f"| {row.month} | {row.nfl_games} | {row.nfl_credits:,} | "
            f"{row.nhl_games} | {row.nhl_credits:,} | {row.combined:,} | "
            f"{row.headroom:,} |"
        )
    add("")
    add(
        f"The heaviest month is **{chosen.worst_month}** at "
        f"{chosen.worst_month_credits:,} credits, leaving "
        f"**{chosen.spare_in_worst_month:,} spare**. Across the eight months "
        f"both seasons touch, the unused capacity totals "
        f"**{chosen.total_spare_over_the_overlap:,} credits**."
    )
    add("")
    for item in estimates:
        add(f"**{item.scenario}** — {item.detail}")
        add("")
    return "\n".join(lines)


def historical_note(estimates: list[Estimate]) -> str:
    """What buying history costs, now that the unit is a month."""
    tier1 = next(e for e in estimates if e.scenario == "tier 1")
    chosen = next(e for e in estimates if e.scenario == "tier 1 + 2")
    per_season = tier1.games * tier1.per_event_markets * REGIONS * 10
    featured_per_season = 272 * 3 * 10
    spare = chosen.spare_in_worst_month
    return (
        "\n## Buying history costs ten times as much — and now that is "
        "affordable\n\n"
        "The historical endpoints bill **10 x markets x regions**, and "
        "historical player props, alternate lines and period markets exist "
        "only after 2023-05-03.\n\n"
        f"One season of tier-1 markets at one snapshot per game: "
        f"{tier1.games} events x {tier1.per_event_markets} markets x 10 = "
        f"**{per_season:,} credits**.\n\n"
        f"Against a single annual pool that was impossible. Against "
        f"{MONTHLY_QUOTA:,} a month it is **{per_season / MONTHLY_QUOTA:.2f} "
        f"months of quota**, and the leanest month of the overlap still has "
        f"{spare:,} spare. Spread across two months it fits without touching "
        "the live fetch.\n\n"
        "Cheaper shapes, for comparison:\n\n"
        f"* Featured markets only (moneyline, spread, total), one season: "
        f"{featured_per_season:,} credits — under a fifth of one month.\n"
        f"* Twelve core props, one season: {272 * 12 * 10:,}.\n"
        f"* Two seasons of tier 1: {per_season * 2:,}, or about "
        f"{per_season * 2 / MONTHLY_QUOTA:.1f} months.\n\n"
        "**This reverses the earlier conclusion in this repository.** A "
        "price-based backtest on bought NFL prop history is affordable, so "
        "the instrument that decides everything in the NHL lab is available "
        "here too. Forward evidence is still built first and still cannot be "
        "back-dated — but it is no longer the only priced evidence this lab "
        "will ever have.\n\n"
        "It remains a credit-spend decision, and therefore Cooper's.\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, help="Also write the raw figures here.")
    parser.add_argument("--schedule", type=Path, default=SCHEDULE_CSV)
    args = parser.parse_args(argv)

    games = load_schedule(args.schedule, SEASON)
    estimates = [estimate(scenario, games) for scenario in scenarios()]

    report = render(estimates) + historical_note(estimates)
    print(report)

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(
                {
                    "season": SEASON,
                    "regions": REGIONS,
                    "monthly_quota": MONTHLY_QUOTA,
                    "nhl_season_by_month": {
                        month: {"games": g, "days": d}
                        for month, (g, d) in NHL_SEASON_BY_MONTH.items()
                    },
                    "nhl_derived_as_of": NHL_DERIVED_AS_OF,
                    "estimates": [asdict(e) for e in estimates],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
