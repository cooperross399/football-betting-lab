#!/usr/bin/env python3
"""What a season of NFL prices costs, computed from the real schedule.

The Odds API quota is **shared with the NHL lab** — one account, one key pool,
two seasons that overlap from late September to January. So this script does
not report an NFL number in isolation; it reports NFL plus the NHL lab's
committed spend against the credits remaining, because that is the only
version of the arithmetic that can answer "does this fit".

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
from football_betting_lab import markets as market_registry


PROJECT_ROOT = Path(__file__).resolve().parents[1]
# The league supplies its own directory segment. A hardcoded "nfl" here is
# exactly the literal the registry exists to prevent, and the discipline
# test fails the build when one appears.
SCHEDULE_CSV = (
    PROJECT_ROOT / "data" / "raw" / NFL.data_dir_segment / "schedule"
    / "nflverse_games.csv"
)

#: The season this lab is being built for.
SEASON = 2026

#: One region. Every extra region multiplies every figure below, which is why
#: the number is named here rather than appearing inline in a URL.
REGIONS = 1

#: The NHL lab's committed season spend, read from its own operating file
#: (`nhl-betting-lab/CLAUDE.md`, "Current operating state"): 19 asked
#: per-event markets over 185 game days and 1,344 games, one fetch a day.
#: Recorded here rather than recomputed, and dated, because it is another
#: repository's measurement and this one must not silently drift from it.
NHL_COMMITTED_CREDITS = 26_091
NHL_COMMITTED_AS_OF = "2026-08-26"

#: Credits remaining on the shared account, same source, same date. Free to
#: re-check with the NHL lab's `scripts/check_provider_quota.py`, which reads
#: the `/v4/sports` headers and spends nothing.
QUOTA_REMAINING = 88_527
QUOTA_TOTAL = 100_000


@dataclass(frozen=True)
class Scenario:
    name: str
    detail: str
    bulk_markets: int
    per_event_markets: int


@dataclass
class Estimate:
    scenario: str
    detail: str
    bulk_markets: int
    per_event_markets: int
    game_days: int
    games: int
    bulk_credits: int
    per_event_credits_pessimistic: int
    scores_credits: int
    season_credits_pessimistic: int
    season_credits_optimistic: int
    worst_day_games: int
    worst_day_credits_pessimistic: int
    daily_cap_needed: int


def load_schedule(path: Path, season: int) -> list[dict[str, str]]:
    """Regular-season games for one season, from the cached nflverse file.

    Read from a cached copy on purpose. A schedule that is refetched on every
    run makes the arithmetic depend on when it was computed, and the whole
    point of this file is that Cooper can check the number later and get the
    same one.
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


def estimate(scenario: Scenario, games: list[dict[str, str]]) -> Estimate:
    per_day = Counter(row["gameday"] for row in games)
    game_days = len(per_day)
    worst_day_games = max(per_day.values())

    # One bulk call per game day, windowed to that day's slate. The NHL lab
    # learned this the expensive way: an unwindowed board spent the budget on
    # games four days out and starved the nearest nine.
    bulk = game_days * scenario.bulk_markets * REGIONS

    # Per-event: every game fetched once, on its own game day.
    per_event = len(games) * scenario.per_event_markets * REGIONS

    # Results. `scores?daysFrom` costs 2, once per day the lab settles.
    scores = game_days * 2

    pessimistic = bulk + per_event + scores
    # Optimistic: only the three featured markets are quoted anywhere. This is
    # a floor, not a forecast.
    optimistic = bulk + scores

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
        game_days=game_days,
        games=len(games),
        bulk_credits=bulk,
        per_event_credits_pessimistic=per_event,
        scores_credits=scores,
        season_credits_pessimistic=pessimistic,
        season_credits_optimistic=optimistic,
        worst_day_games=worst_day_games,
        worst_day_credits_pessimistic=worst_day,
        # Rounded up to the next hundred so a market added mid-season does not
        # silently clip a slate before anyone notices.
        daily_cap_needed=((worst_day + 99) // 100) * 100,
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
                "What a Week 1 fetch asks for: the bulk three, seven "
                "per-event team markets, twenty player props and their "
                "nineteen alternate ladders."
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
                "quarter alternate ladders this lab has not wired. Printed "
                "as the ceiling, not as a plan."
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
        f"one region (`us`), each game fetched once on its own game day."
    )
    add("")
    add(
        f"The shared account had **{QUOTA_REMAINING:,} of {QUOTA_TOTAL:,} "
        f"credits remaining** as of {NHL_COMMITTED_AS_OF}, and the NHL lab "
        f"has already committed **{NHL_COMMITTED_CREDITS:,}** of them to its "
        f"own season. So football is spending "
        f"**{QUOTA_REMAINING - NHL_COMMITTED_CREDITS:,}**, not "
        f"{QUOTA_REMAINING:,}."
    )
    add("")
    add("| Scenario | Markets/event | Season (pessimistic) | + NHL | Against "
        f"{QUOTA_REMAINING:,} | Worst slate | Daily cap |")
    add("|:---------|--------------:|---------------------:|------:|--------:"
        "|------------:|----------:|")
    for item in estimates:
        combined = item.season_credits_pessimistic + NHL_COMMITTED_CREDITS
        headroom = QUOTA_REMAINING - combined
        verdict = f"{headroom:+,}"
        add(
            f"| {item.scenario} | {item.per_event_markets} | "
            f"{item.season_credits_pessimistic:,} | {combined:,} | "
            f"{verdict} | {item.worst_day_games} games = "
            f"{item.worst_day_credits_pessimistic:,} | "
            f"{item.daily_cap_needed:,} |"
        )
    add("")
    for item in estimates:
        add(f"**{item.scenario}** — {item.detail}")
        add("")
        add(
            f"  {item.game_days} bulk calls x {item.bulk_markets} markets = "
            f"{item.bulk_credits:,}; {item.games} events x "
            f"{item.per_event_markets} markets = "
            f"{item.per_event_credits_pessimistic:,}; results "
            f"{item.scores_credits:,}. Pessimistic total "
            f"**{item.season_credits_pessimistic:,}**; optimistic floor "
            f"(nothing but the featured three quoted anywhere) "
            f"{item.season_credits_optimistic:,}."
        )
        add("")
    return "\n".join(lines)


def historical_note(estimates: list[Estimate]) -> str:
    """What buying history would cost. Printed because it is the real wall."""
    tier1 = next(e for e in estimates if e.scenario == "tier 1")
    per_season = tier1.games * tier1.per_event_markets * REGIONS * 10
    return (
        "\n## Buying history costs ten times as much\n\n"
        "The historical endpoints bill **10 x markets x regions**, and "
        "historical player props, alternate lines and period markets exist "
        "only after 2023-05-03.\n\n"
        f"One season of tier-1 markets at one snapshot per game: "
        f"{tier1.games} events x {tier1.per_event_markets} markets x 10 = "
        f"**{per_season:,} credits**. That is "
        f"{per_season / QUOTA_REMAINING:.1f}x the entire remaining quota, for "
        "one season, at one snapshot per game.\n\n"
        "This is the number that decides the build order. A price backtest on "
        "bought NFL prop history is not affordable at the current quota on any "
        "market set worth measuring, and no amount of care in the code changes "
        "that. Forward evidence — frozen before kickoff, settled after — is "
        "not a cheaper substitute for it; it is the only priced evidence this "
        "lab can afford to collect, and every week it is not running is a week "
        "of it gone permanently.\n"
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
                    "quota_remaining": QUOTA_REMAINING,
                    "nhl_committed_credits": NHL_COMMITTED_CREDITS,
                    "as_of": NHL_COMMITTED_AS_OF,
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
