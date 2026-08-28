"""A live fetch that the card cannot read.

Everything this writes lands in `data/staging/`, and the card reads only what
a reviewed policy allowlists. So a shadow run can be wrong, incomplete, or
surprising without a single pick changing. That separation is the whole point:
it lets the adapter be proven against the provider's real responses before
anything depends on it.

## The two screens that run before a credit is spent

**The horizon window.** The events list returns every upcoming game, which in
football means next week's Sunday slate alongside tonight's. Spending the
per-event budget on games four days out is how the NHL lab starved the nearest
nine games one August evening. So the per-event fetch is windowed to the days
being priced, and the window is stated in the report.

**The preseason screen.** Books post exhibition lines from early August and
the provider does not flag them. The models are never fitted on preseason —
nflverse publishes none — but the *card* is not safe by construction: an
unfiltered run would freeze opinions it has no business holding into the
forward ledger, where they would rot as unsettleable noise.

So every event is screened against the known regular-season schedule. The
failure direction matters more than the screen: **an incomplete schedule
cache abstains rather than reclassifying a real slate as preseason.** A
partial cache is not a smaller truth, it is the same truth with holes, and the
holes are indistinguishable from exhibition games to anything that only asks
"is this fixture in the set?".

Preseason events are **counted and named**, never quietly dropped.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from football_betting_lab.leagues import League
from football_betting_lab.markets import bulk_provider_keys, per_event_provider_keys
from football_betting_lab.providers.odds_api import (
    ROW_COLUMNS,
    STAGING_PRICES_FILENAME,
    CreditCapReached,
    OddsApiProvider,
    ProviderError,
    Spend,
    normalize_event,
)
from football_betting_lab.providers.team_names import name_to_abbreviation, resolve_team
from football_betting_lab.season import (
    game_date,
    known_regular_season_games,
    schedule_cache_is_complete,
)


@dataclass
class ShadowRun:
    """What one live fetch saw, spent, and refused."""

    league_key: str
    fetched_at: str
    horizon_days: int
    events_listed: int = 0
    events_in_window: int = 0
    events_priced: int = 0
    preseason_excluded: list[str] = field(default_factory=list)
    unresolved_clubs: set[str] = field(default_factory=set)
    schedule_complete: bool = True
    clubs_in_schedule: int = 0
    rows: list[dict[str, Any]] = field(default_factory=list)
    unparseable: int = 0
    reasons: Counter = field(default_factory=Counter)
    spend: Spend = field(default_factory=Spend)
    stopped_early: str = ""
    errors: list[str] = field(default_factory=list)

    @property
    def frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows, columns=list(ROW_COLUMNS))

    def summary_line(self) -> str:
        return (
            f"{len(self.rows):,} staged row(s) from {self.events_priced} of "
            f"{self.events_in_window} in-window event(s) "
            f"({self.events_listed} listed); "
            f"{len(self.preseason_excluded)} excluded as preseason; "
            f"{self.unparseable} unparseable. {self.spend.summary_line()}"
        )


def run_shadow(
    provider: OddsApiProvider,
    league: League,
    *,
    raw_dir: Path,
    season: int,
    horizon_days: int = 1,
    credit_cap: int,
    now: datetime | None = None,
    tier: int = 1,
) -> ShadowRun:
    moment = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    run = ShadowRun(
        league_key=league.key,
        fetched_at=moment.isoformat(),
        horizon_days=horizon_days,
    )
    complete, clubs = schedule_cache_is_complete(league, raw_dir, season=season)
    run.schedule_complete, run.clubs_in_schedule = complete, clubs
    known = known_regular_season_games(league, raw_dir, season=season)
    lookup = name_to_abbreviation(league)

    try:
        events = provider.list_events()
    except ProviderError as exc:
        run.errors.append(str(exc))
        return run
    run.events_listed = len(events)

    horizon = moment.date()
    in_window: list[dict[str, Any]] = []
    for event in events:
        commence = str(event.get("commence_time", "")).strip()
        day = game_date(commence, league)
        try:
            delta = (datetime.fromisoformat(f"{day}T00:00:00+00:00").date() - horizon).days
        except ValueError:
            continue
        if not 0 <= delta < horizon_days:
            continue
        in_window.append(event)
    run.events_in_window = len(in_window)

    playable: list[dict[str, Any]] = []
    for event in in_window:
        day = game_date(str(event.get("commence_time", "")), league)
        home = resolve_team(event.get("home_team"), league, lookup)
        away = resolve_team(event.get("away_team"), league, lookup)
        label = (
            f"{day} {event.get('away_team')} @ {event.get('home_team')}"
        )
        if home is None:
            run.unresolved_clubs.add(str(event.get("home_team", "")))
        if away is None:
            run.unresolved_clubs.add(str(event.get("away_team", "")))
        if not complete:
            # Abstain. An incomplete cache cannot tell preseason from a game
            # whose row never landed, and guessing would drop a real slate.
            playable.append(event)
            continue
        if home is None or away is None:
            run.preseason_excluded.append(f"{label} (club not in this league)")
            continue
        if (day, home, away) not in known:
            run.preseason_excluded.append(f"{label} (not in the regular-season schedule)")
            continue
        playable.append(event)

    if not playable:
        return run

    bulk_markets = bulk_provider_keys(tier)
    per_event_markets = per_event_provider_keys(tier)
    try:
        bulk = provider.fetch_bulk(
            bulk_markets, spend=run.spend, credit_cap=credit_cap
        )
    except CreditCapReached as exc:
        run.stopped_early = str(exc)
        return run
    except ProviderError as exc:
        run.errors.append(f"bulk fetch: {exc}")
        bulk = []

    wanted_ids = {str(event.get("id", "")) for event in playable}
    payloads = [event for event in bulk if str(event.get("id", "")) in wanted_ids]

    for event in playable:
        event_id = str(event.get("id", ""))
        try:
            extra = provider.fetch_event_odds(
                event_id, per_event_markets, spend=run.spend, credit_cap=credit_cap
            )
        except CreditCapReached as exc:
            run.stopped_early = str(exc)
            break
        except ProviderError as exc:
            run.errors.append(f"event {event_id}: {exc}")
            continue
        if extra:
            payloads.append(extra)

    seen_events: set[str] = set()
    for payload in payloads:
        parsed = normalize_event(payload, league, fetched_at=run.fetched_at)
        run.rows.extend(parsed.rows)
        run.unparseable += parsed.unparseable
        run.reasons.update(parsed.reasons)
        if parsed.rows:
            seen_events.add(str(payload.get("id", "")))
    run.events_priced = len(seen_events)
    return run


def write_staging(run: ShadowRun, staging_dir: Path) -> Path:
    """Write the staged table. The card cannot read this directory."""
    staging_dir = Path(staging_dir)
    staging_dir.mkdir(parents=True, exist_ok=True)
    path = staging_dir / STAGING_PRICES_FILENAME
    run.frame.to_csv(path, index=False)
    return path


def render(run: ShadowRun, league: League) -> str:
    lines: list[str] = []
    add = lines.append
    add(f"# Provider shadow run — {league.title}")
    add("")
    add(f"Fetched {run.fetched_at}, horizon {run.horizon_days} day(s).")
    add("")
    add(run.summary_line())
    add("")
    add(
        "**Nothing here can reach the card.** These rows are staged, and the "
        "card reads only markets a reviewed human acceptance receipt "
        "allowlists — which today is none."
    )
    if not run.schedule_complete:
        add("")
        add(
            f"> **The schedule cache names only {run.clubs_in_schedule} clubs, "
            "so the preseason screen abstained.** A partial cache is the same "
            "truth with holes, and the holes are indistinguishable from "
            "exhibition games. Every event was priced rather than risk "
            "dropping a real slate."
        )
    if run.preseason_excluded:
        add("")
        add(f"## Excluded as preseason ({len(run.preseason_excluded)})")
        add("")
        add(
            "Counted and named, never quietly dropped. Books post exhibition "
            "lines from early August and the provider does not flag them; an "
            "opinion frozen on one would rot in the ledger as unsettleable "
            "noise."
        )
        add("")
        for label in run.preseason_excluded:
            add(f"- {label}")
    if run.unresolved_clubs:
        add("")
        add("## Club names that did not resolve")
        add("")
        add(
            "Reported rather than guessed at: a fuzzy match produces a "
            "confident price for a bet nobody placed, and the row looks "
            "exactly like a correct one."
        )
        add("")
        for name in sorted(run.unresolved_clubs):
            add(f"- `{name}`")
    if run.rows:
        frame = run.frame
        add("")
        add("## What was staged")
        add("")
        add("| Market | Rows | Books | Events |")
        add("|:-------|-----:|------:|-------:|")
        for market, group in frame.groupby("market"):
            add(
                f"| `{market}` | {len(group):,} | {group['book'].nunique()} | "
                f"{group['event_id'].nunique()} |"
            )
    if run.reasons:
        add("")
        add("## Outcomes this lab could not parse")
        add("")
        add(
            "Counted rather than dropped: `unparseable` is a term in the "
            "accounting identity the card prints, and a parser that discards "
            "what it does not recognise makes that identity reconcile while "
            "hiding the thing it exists to surface."
        )
        add("")
        for reason, count in run.reasons.most_common():
            add(f"- {count} x {reason}")
    if run.stopped_early:
        add("")
        add(f"> **Stopped early.** {run.stopped_early}")
    for error in run.errors:
        add("")
        add(f"> {error}")
    return "\n".join(lines) + "\n"
