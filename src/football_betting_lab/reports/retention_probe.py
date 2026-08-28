"""Which markets the provider actually retains historically, measured.

A market that cannot be bought historically **cannot be measured
historically**, and the honest response is to record it by name as
unmeasurable — not to substitute a calibration number and let it read like a
backtest. This module answers that question for a bounded number of events at
a known cost, before anything larger is spent.

## Why a probe rather than just buying the season

The NHL lab bought first and probed second, and it cost them. A probe of a
single event returned five of six markets, `player_total_saves` was recorded
as unmeasurable, and the purchase that followed found it priced on 54 of 58
events across six books. The market was there all along and the sample of one
was not a sample.

So two rules are built in:

**`MINIMUM_PROBES_FOR_ABSENCE`.** Below it, a market that did not appear is
reported as *not seen in N events*, which is a different sentence from *cannot
be measured*, and the report refuses to write the second one.

**Stratified sampling by kickoff window.** Book coverage is not uniform across
the schedule: a Sunday-night national game and a 1pm Jaguars game are not the
same product, and a probe drawn only from marquee windows would measure
marquee retention and call it retention. Events are drawn across Thursday,
early Sunday, late Sunday, Sunday night and Monday in proportion to how the
season actually distributes them.

## Why a refused market list is bisected rather than reported as a failure

The provider answers an unsupported market key with HTTP 422 **for the whole
request**, so one bad key in a list of ten hides the other nine. A refused
chunk is therefore split in half and retried, down to single markets, until
the refusing keys are named individually.

That costs nothing: a 422 returns no markets, and the endpoint bills per
market **returned**. It is the difference between "the provider does not serve
this" and "we asked wrong", which have looked identical before and cost the
NHL lab a market for a season.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from football_betting_lab.leagues import League
from football_betting_lab.markets import market_for_provider_key
from football_betting_lab.providers.odds_api import (
    CreditCapReached,
    OddsApiProvider,
    ProviderError,
    Spend,
)
from football_betting_lab.providers.team_names import name_to_abbreviation, resolve_team


#: How many events must be probed before absence means anything.
MINIMUM_PROBES_FOR_ABSENCE = 5

#: Minutes before kickoff to take the snapshot. Late enough that books have
#: posted their prop boards, early enough to represent a price a card could
#: actually have acted on.
SNAPSHOT_LEAD_MINUTES = 60

#: Markets per request. One bad key refuses the whole list, so smaller chunks
#: mean a smaller blast radius before the bisection has to work.
MARKETS_PER_REQUEST = 10

#: Historical props, alternate lines and period markets exist only from this
#: date. Probing earlier would measure the provider's retention policy for a
#: period when the data never existed, and read as absence.
PROPS_AVAILABLE_FROM = "2023-05-03"

CACHE_DIRNAME = "historical_probe"


@dataclass(frozen=True)
class ProbeTarget:
    """One past game to probe, and the instant to probe it at."""

    season: int
    week: int
    game_id: str
    kickoff_utc: datetime
    home: str
    away: str
    window: str

    @property
    def snapshot(self) -> str:
        moment = self.kickoff_utc - timedelta(minutes=SNAPSHOT_LEAD_MINUTES)
        return moment.strftime("%Y-%m-%dT%H:%M:%SZ")

    @property
    def label(self) -> str:
        return f"{self.season} wk{self.week} {self.away}@{self.home} ({self.window})"


@dataclass
class EventProbe:
    """What one snapshot actually carried."""

    target: ProbeTarget
    event_id: str = ""
    markets_requested: tuple[str, ...] = ()
    #: provider market key -> set of book keys that quoted it
    books_by_market: dict[str, set[str]] = field(default_factory=dict)
    #: provider market key -> number of priced outcomes
    outcomes_by_market: dict[str, int] = field(default_factory=dict)
    refused_markets: tuple[str, ...] = ()
    credits_spent: int = 0
    error: str = ""

    @property
    def markets_returned(self) -> tuple[str, ...]:
        return tuple(sorted(self.books_by_market))

    @property
    def ok(self) -> bool:
        return not self.error and bool(self.event_id)


@dataclass
class ProbeResult:
    """Every probe, and what the set of them supports."""

    league_key: str
    snapshot_lead_minutes: int
    markets_requested: tuple[str, ...]
    probes: list[EventProbe] = field(default_factory=list)
    spend: Spend = field(default_factory=Spend)
    stopped_early: str = ""
    #: provider market key -> every book that quoted it, and how many priced
    #: outcomes it carried. Held here rather than recomputed from `probes` so
    #: a result rebuilt from the recorded run has one place to fill, and so
    #: the two paths cannot disagree about what the numbers mean.
    book_index: dict[str, set[str]] = field(default_factory=dict)
    outcome_index: dict[str, int] = field(default_factory=dict)

    def absorb_probe(self, probe: "EventProbe") -> None:
        for market, books in probe.books_by_market.items():
            self.book_index.setdefault(market, set()).update(books)
        for market, count in probe.outcomes_by_market.items():
            self.outcome_index[market] = self.outcome_index.get(market, 0) + count

    @property
    def successful(self) -> list[EventProbe]:
        return [probe for probe in self.probes if probe.ok]

    def events_seen(self, market: str) -> int:
        return sum(1 for probe in self.successful if market in probe.books_by_market)

    def books(self, market: str) -> tuple[str, ...]:
        return tuple(sorted(self.book_index.get(market, set())))

    def outcomes(self, market: str) -> int:
        return int(self.outcome_index.get(market, 0))

    def refused_everywhere(self) -> tuple[str, ...]:
        """Markets the provider refused by name in every probe that asked."""
        asked: Counter[str] = Counter()
        refused: Counter[str] = Counter()
        for probe in self.probes:
            for market in probe.markets_requested:
                asked[market] += 1
            for market in probe.refused_markets:
                refused[market] += 1
        return tuple(
            sorted(m for m in asked if refused.get(m, 0) >= asked[m] and asked[m])
        )

    def verdict(self, market: str) -> str:
        """The one sentence this evidence supports about one market.

        The wording is load-bearing. "Not seen in N events" and "cannot be
        measured historically" are different claims, and only the sample size
        decides which one is available.
        """
        seen = self.events_seen(market)
        n = len(self.successful)
        if market in self.refused_everywhere():
            return "refused by name — the provider does not serve this key"
        if seen:
            return f"retained — priced in {seen} of {n} events"
        if n < MINIMUM_PROBES_FOR_ABSENCE:
            return (
                f"not seen in {n} event(s) — below the {MINIMUM_PROBES_FOR_ABSENCE} "
                "needed before absence means anything"
            )
        return f"not seen in any of {n} events — no historical price to test against"


# -- choosing what to probe -------------------------------------------------


def kickoff_window(weekday: str, gametime: str) -> str:
    """The product a game is, not just the day it falls on.

    Book coverage differs between a national night game and a 1pm regional
    one, so the sample has to span them or it measures the wrong thing.
    """
    day = str(weekday or "").strip().lower()
    try:
        hour = int(str(gametime or "0:00").split(":")[0])
    except ValueError:
        hour = 0
    if day == "thursday":
        return "thursday night"
    if day == "monday":
        return "monday night"
    if day == "sunday":
        if hour < 14:
            return "sunday early"
        if hour < 19:
            return "sunday late"
        return "sunday night"
    return "other"


def select_targets(
    rows: Sequence[Mapping[str, str]],
    league: League,
    *,
    seasons: Sequence[int],
    count: int,
) -> list[ProbeTarget]:
    """A stratified, deterministic sample of past games.

    Deterministic on purpose: a probe that samples differently on every run
    cannot be re-run to check a number, and this one's whole job is to produce
    a number someone will act on. No randomness, no clock.
    """
    wanted = {str(season) for season in seasons}
    candidates: list[ProbeTarget] = []
    for row in rows:
        if row.get("season") not in wanted or row.get("game_type") != "REG":
            continue
        gameday = str(row.get("gameday", ""))
        gametime = str(row.get("gametime", ""))
        if not gameday or not gametime or gameday < PROPS_AVAILABLE_FROM:
            continue
        try:
            local = datetime.fromisoformat(f"{gameday}T{gametime}:00").replace(
                tzinfo=league.timezone
            )
        except ValueError:
            continue
        candidates.append(
            ProbeTarget(
                season=int(row["season"]),
                week=int(row.get("week", 0) or 0),
                game_id=str(row.get("game_id", "")),
                kickoff_utc=local.astimezone(ZoneInfo("UTC")),
                home=str(row.get("home_team", "")).strip().upper(),
                away=str(row.get("away_team", "")).strip().upper(),
                window=kickoff_window(row.get("weekday", ""), gametime),
            )
        )
    if not candidates:
        return []

    by_window: dict[str, list[ProbeTarget]] = defaultdict(list)
    for target in candidates:
        by_window[target.window].append(target)

    # Proportional allocation, with at least one from every window that
    # exists. A window represented in the season and absent from the sample is
    # a window whose retention this probe cannot speak about, and the report
    # would not know to say so.
    total = len(candidates)
    allocation: dict[str, int] = {}
    for window, items in by_window.items():
        allocation[window] = max(1, round(count * len(items) / total))
    while sum(allocation.values()) > count and len(allocation) > 1:
        widest = max(allocation, key=lambda w: (allocation[w], w))
        if allocation[widest] <= 1:
            break
        allocation[widest] -= 1
    while sum(allocation.values()) < count:
        widest = max(by_window, key=lambda w: (len(by_window[w]), w))
        allocation[widest] += 1

    chosen: list[ProbeTarget] = []
    for window in sorted(by_window):
        items = sorted(by_window[window], key=lambda t: (t.kickoff_utc, t.game_id))
        take = allocation.get(window, 0)
        if not take:
            continue
        # Even spread through the window's own calendar, anchored at both
        # ends. A `[::step]` slice looks like it does this and does not: it
        # truncates to the first `take` picks, which drew 13 of 20 events from
        # the earlier season and would have measured 2024's retention and
        # called it retention.
        if take >= len(items):
            picked = list(items)
        elif take == 1:
            picked = [items[len(items) // 2]]
        else:
            picked = [
                items[round(i * (len(items) - 1) / (take - 1))] for i in range(take)
            ]
        chosen.extend(picked)
    return sorted(chosen, key=lambda t: (t.kickoff_utc, t.game_id))[:count]


# -- running the probe ------------------------------------------------------


def markets_fingerprint(markets: Sequence[str]) -> str:
    """A short, stable tag for the market list a response was bought with.

    The cache key needs it, and the first version of this module did not have
    it: chunks were tagged with their *length*, so the four ten-market chunks
    of a forty-six-market request all wrote to one filename and three of them
    were lost. The live report was computed in memory and was correct; the
    cache it left behind held two chunks of five, and re-rendering from it
    reported thirty-one retained markets as absent.

    That is the NHL lab's own warning, ignored: a response holds the markets
    it was asked for and nothing else, so a key that does not name them will
    serve the wrong file and answer, quite confidently, that a market is not
    offered.
    """
    joined = ",".join(sorted(str(item) for item in markets))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:12]


def _cache_path(
    cache_dir: Path, event_id: str, snapshot: str, markets: Sequence[str]
) -> Path:
    stamp = str(snapshot).replace(":", "").replace("-", "")
    return Path(cache_dir) / f"{event_id}_{stamp}_{markets_fingerprint(markets)}.json"


def _chunks(items: Sequence[str], size: int) -> list[tuple[str, ...]]:
    return [tuple(items[i : i + size]) for i in range(0, len(items), size)]


def _fetch_chunk(
    provider: OddsApiProvider,
    event_id: str,
    snapshot: str,
    markets: tuple[str, ...],
    *,
    spend: Spend,
    credit_cap: int,
) -> tuple[dict[str, Any], tuple[str, ...]]:
    """One chunk, bisected on refusal until the refusing keys are named.

    Returns `(payload, refused_market_keys)`. A 422 costs nothing because the
    endpoint bills per market returned, so the bisection is free — which is
    what makes naming the bad key affordable rather than a luxury.
    """
    try:
        return (
            provider.historical_event_odds(
                event_id, snapshot, markets, spend=spend, credit_cap=credit_cap
            ),
            (),
        )
    except CreditCapReached:
        raise
    except ProviderError:
        if len(markets) == 1:
            return {}, markets
        middle = len(markets) // 2
        left, left_refused = _fetch_chunk(
            provider,
            event_id,
            snapshot,
            markets[:middle],
            spend=spend,
            credit_cap=credit_cap,
        )
        right, right_refused = _fetch_chunk(
            provider,
            event_id,
            snapshot,
            markets[middle:],
            spend=spend,
            credit_cap=credit_cap,
        )
        merged = dict(left)
        books = list(left.get("bookmakers", []) or [])
        books.extend(right.get("bookmakers", []) or [])
        if books:
            merged["bookmakers"] = books
        elif right:
            merged = dict(right)
        return merged, left_refused + right_refused


def _match_event(
    events: Sequence[Mapping[str, Any]], target: ProbeTarget, league: League
) -> tuple[str, str]:
    """The provider's id for one scheduled game, or a reason it was not found.

    Matched on **both** kickoff instant and clubs. Time alone would pick the
    wrong game out of a 1pm slate of nine; clubs alone would pick the wrong
    meeting of two clubs that play twice a year.
    """
    lookup = name_to_abbreviation(league)
    unresolved: set[str] = set()
    for event in events:
        commence = str(event.get("commence_time", "")).strip()
        try:
            moment = datetime.fromisoformat(commence.replace("Z", "+00:00"))
        except ValueError:
            continue
        if abs((moment - target.kickoff_utc).total_seconds()) > 900:
            continue
        home = resolve_team(event.get("home_team"), league, lookup)
        away = resolve_team(event.get("away_team"), league, lookup)
        if home is None:
            unresolved.add(str(event.get("home_team", "")))
        if away is None:
            unresolved.add(str(event.get("away_team", "")))
        if home == target.home and away == target.away:
            return str(event.get("id", "")), ""
    if unresolved:
        return "", (
            "no event matched, and these club names did not resolve: "
            f"{sorted(unresolved)}"
        )
    return "", "no event within 15 minutes of kickoff carried both clubs"


def run_probe(
    provider: OddsApiProvider,
    league: League,
    targets: Sequence[ProbeTarget],
    markets: Sequence[str],
    *,
    credit_cap: int,
    cache_dir: Path,
) -> ProbeResult:
    """Probe each target, stopping cleanly the moment the cap could be breached."""
    asked = tuple(dict.fromkeys(str(m) for m in markets))
    result = ProbeResult(
        league_key=league.key,
        snapshot_lead_minutes=SNAPSHOT_LEAD_MINUTES,
        markets_requested=asked,
    )
    Path(cache_dir).mkdir(parents=True, exist_ok=True)

    for target in targets:
        probe = EventProbe(target=target, markets_requested=asked)
        before = result.spend.credits_spent
        try:
            events = provider.list_historical_events(
                target.snapshot, spend=result.spend, credit_cap=credit_cap
            )
            event_id, why = _match_event(events, target, league)
            if not event_id:
                probe.error = why
                result.probes.append(probe)
                continue
            probe.event_id = event_id

            refused: list[str] = []
            for chunk in _chunks(asked, MARKETS_PER_REQUEST):
                payload, chunk_refused = _fetch_chunk(
                    provider,
                    event_id,
                    target.snapshot,
                    chunk,
                    spend=result.spend,
                    credit_cap=credit_cap,
                )
                refused.extend(chunk_refused)
                _absorb(probe, payload)
                if payload:
                    _cache_path(
                        cache_dir, event_id, target.snapshot, chunk
                    ).write_text(
                        json.dumps(payload, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8",
                    )
            probe.refused_markets = tuple(sorted(set(refused)))
        except CreditCapReached as exc:
            probe.error = str(exc)
            result.probes.append(probe)
            result.stopped_early = str(exc)
            break
        except ProviderError as exc:
            probe.error = str(exc)
        probe.credits_spent = result.spend.credits_spent - before
        result.absorb_probe(probe)
        result.probes.append(probe)

    return result


def _absorb(probe: EventProbe, payload: Mapping[str, Any]) -> None:
    """Fold one response into the probe's per-market tallies."""
    for bookmaker in payload.get("bookmakers", []) or []:
        if not isinstance(bookmaker, Mapping):
            continue
        book = str(bookmaker.get("key") or bookmaker.get("title") or "").strip()
        for market in bookmaker.get("markets", []) or []:
            if not isinstance(market, Mapping):
                continue
            key = str(market.get("key", "")).strip().lower()
            if not key:
                continue
            outcomes = [
                outcome
                for outcome in (market.get("outcomes", []) or [])
                if isinstance(outcome, Mapping)
                and outcome.get("price") is not None
            ]
            if not outcomes:
                continue
            probe.books_by_market.setdefault(key, set()).add(book)
            probe.outcomes_by_market[key] = (
                probe.outcomes_by_market.get(key, 0) + len(outcomes)
            )


# -- rebuilding the report from the evidence, without spending anything -----


def rebuild_from_record(
    payload: Mapping[str, Any], league: League, *, cache_dir: Path | None = None
) -> ProbeResult:
    """Reconstruct a probe result from the run's own recorded output.

    Historical prices never change, so a probe is evidence that can be
    re-read. That makes the *report* derived data: it can be improved — a
    better roll-up, a distinction nobody had thought of — without spending a
    credit and without trusting that a summary written by an older version of
    this module still says what the evidence says.

    That property is not a convenience. The first rendering of this report
    rolled up by provider key alone and read as though three markets could not
    be measured when their alternate ladders showed that they could. Fixing
    the wording would have been worthless if fixing it meant re-spending
    7,280 credits.

    **The JSON record is the source, not the cached responses**, and the
    reason is a bug this module shipped: chunks were cached under a filename
    tagged with the chunk's *length*, so four ten-market chunks collided and
    three were lost. The record was computed in memory and is complete; the
    cache from that run is not. Passing `cache_dir` corroborates the two and
    reports any disagreement rather than silently preferring either.
    """
    result = ProbeResult(
        league_key=league.key,
        snapshot_lead_minutes=int(
            payload.get("snapshot_lead_minutes", SNAPSHOT_LEAD_MINUTES)
        ),
        markets_requested=tuple(payload.get("markets", {})),
    )
    spend = result.spend
    spend.credits_spent = int(payload.get("credits_spent", 0) or 0)
    spend.credits_estimated = int(payload.get("credits_estimated", 0) or 0)
    spend.requests_made = int(payload.get("requests_made", 0) or 0)
    spend.quota_remaining = str(payload.get("quota_remaining", ""))
    spend.quota_used = str(payload.get("quota_used", ""))
    spend.notes = list(payload.get("notes", []) or [])
    result.stopped_early = str(payload.get("stopped_early", ""))

    for market, record in (payload.get("markets") or {}).items():
        if not isinstance(record, Mapping):
            continue
        books = {str(book) for book in (record.get("books") or [])}
        if books:
            result.book_index[str(market)] = books
        outcomes = int(record.get("outcomes", 0) or 0)
        if outcomes:
            result.outcome_index[str(market)] = outcomes

    for record in payload.get("events", []) or []:
        snapshot = str(record.get("snapshot", ""))
        try:
            taken = datetime.strptime(snapshot, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=ZoneInfo("UTC")
            )
        except ValueError:
            continue
        home, away = str(record.get("home", "")), str(record.get("away", ""))
        if not home or not away:
            # Older records carry only the label: "2024 wk1 ARI@BUF (window)".
            parts = str(record.get("label", "")).split(" ")
            fixture = parts[2] if len(parts) > 2 else ""
            away, _, home = fixture.partition("@")
        probe = EventProbe(
            target=ProbeTarget(
                season=int(record.get("season", 0) or 0),
                week=int(record.get("week", 0) or 0),
                game_id=str(record.get("game_id", "")),
                kickoff_utc=taken
                + timedelta(minutes=result.snapshot_lead_minutes),
                home=home,
                away=away,
                window=str(record.get("window", "other")),
            ),
            event_id=str(record.get("event_id", "")),
            markets_requested=result.markets_requested,
            refused_markets=tuple(record.get("refused", []) or []),
            credits_spent=int(record.get("credits_spent", 0) or 0),
            error=str(record.get("error", "")),
        )
        # Per-event membership only: which markets this snapshot carried. The
        # book and outcome totals come from the market index above, so they
        # are counted once rather than once per reconstruction path.
        for market in record.get("markets_returned", []) or []:
            probe.books_by_market.setdefault(str(market), set())
        result.probes.append(probe)

    if cache_dir is not None:
        result.spend.notes.extend(_corroborate(result, Path(cache_dir)))
    return result


def _corroborate(result: ProbeResult, cache_dir: Path) -> list[str]:
    """Check the cached responses against the record, and say so either way.

    A cache that disagrees with the record is not a reason to prefer one
    silently. It is a fact about the run, and the report prints it.
    """
    notes: list[str] = []
    if not cache_dir.is_dir():
        return [f"No cached responses at {cache_dir} to corroborate the record."]
    from_cache: set[str] = set()
    for path in sorted(cache_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        probe = EventProbe(target=result.probes[0].target if result.probes else None)  # type: ignore[arg-type]
        _absorb(probe, payload)
        from_cache |= set(probe.books_by_market)
    recorded = {
        market for market in result.markets_requested if result.events_seen(market)
    }
    missing = sorted(recorded - from_cache)
    if missing:
        notes.append(
            f"{len(missing)} market(s) present in the run record are absent "
            f"from the cached responses in {cache_dir.name}: the chunk cache "
            "of that run collided on filename and kept only the last chunk of "
            "each size. The record is complete and is what this report is "
            "built from; the cache is not, and a later probe will be."
        )
    return notes


# -- rolling up to the unit that actually gets approved ---------------------


@dataclass(frozen=True)
class MarketRollup:
    """One project market's retention across every provider key that feeds it."""

    project_key: str
    provider_keys: tuple[str, ...]
    events_seen: int
    events_probed: int
    books: tuple[str, ...]
    outcomes: int

    @property
    def retained(self) -> bool:
        return self.events_seen > 0

    @property
    def thin(self) -> bool:
        """Retained, but on too little to measure anything with.

        "Retained" and "measurable" are not the same claim, and collapsing
        them is the same failure as reporting a number without its sample
        size. In the first NFL probe `rush_tds` appeared on 2 of 20 events at
        one book with six priced outcomes, and `pass_yards` on 20 of 20 at
        eight books with 2,973. Both are "retained". Only one of them can
        support a backtest.

        Thin means either: the market appeared on fewer than a quarter of the
        probed events, or only one book quoted it. One book is not a market —
        it is a book, and a measurement against it measures that book's
        pricing rather than the market's.
        """
        if not self.retained:
            return False
        return (
            self.events_seen * 4 < self.events_probed or len(self.books) < 2
        )

    def verdict(self) -> str:
        if self.thin:
            return (
                f"retained but thin — priced in only {self.events_seen} of "
                f"{self.events_probed} events across {len(self.books)} book(s)"
            )
        if self.retained:
            return (
                f"retained — priced in {self.events_seen} of "
                f"{self.events_probed} events"
            )
        if self.events_probed < MINIMUM_PROBES_FOR_ABSENCE:
            return (
                f"not seen in {self.events_probed} event(s) — below the "
                f"{MINIMUM_PROBES_FOR_ABSENCE} needed before absence means "
                "anything"
            )
        return (
            f"not seen in any of {self.events_probed} events — no historical "
            "price to test against"
        )


def rollup_by_project_market(result: "ProbeResult") -> list[MarketRollup]:
    """Retention per market this lab prices, not per provider key.

    This exists because the per-key table is misleading in exactly the way the
    EPL lab's `total_2_5` mistake was. In the first NFL probe, three featured
    keys returned nothing at all — `player_rush_tds`,
    `player_reception_tds`, `player_defensive_interceptions` — while their
    alternate ladders were retained on 2, 2 and 9 events respectively. Read
    per key, that says three markets cannot be measured. Read per market,
    which is the unit that gets modelled, measured and approved, it says all
    three can.

    The reverse case is in the same data: `player_pass_longest_completion`
    is retained on all 20 events and its ladder on none. A rollup that only
    looked at ladders would get that one backwards.

    So the featured key and its ladder are one market here, because that is
    what they are everywhere else in this repository.
    """
    keys_for: dict[str, list[str]] = defaultdict(list)
    for provider_key in result.markets_requested:
        market = market_for_provider_key(provider_key)
        keys_for[market.key if market else provider_key].append(provider_key)

    probed = len(result.successful)
    rollups: list[MarketRollup] = []
    for project_key, provider_keys in keys_for.items():
        seen = sum(
            1
            for probe in result.successful
            if any(key in probe.books_by_market for key in provider_keys)
        )
        books: set[str] = set()
        outcomes = 0
        for key in provider_keys:
            books |= set(result.books(key))
            outcomes += result.outcomes(key)
        rollups.append(
            MarketRollup(
                project_key=project_key,
                provider_keys=tuple(provider_keys),
                events_seen=seen,
                events_probed=probed,
                books=tuple(sorted(books)),
                outcomes=outcomes,
            )
        )
    return sorted(rollups, key=lambda r: (-r.events_seen, r.project_key))


# -- reporting --------------------------------------------------------------


def _project_label(provider_key: str) -> str:
    market = market_for_provider_key(provider_key)
    return market.key if market else "—"


def render(result: ProbeResult, league: League) -> str:
    """The report. Every number carries the count of events behind it."""
    lines: list[str] = []
    add = lines.append
    n = len(result.successful)
    add(f"# Historical retention probe — {league.title}")
    add("")
    add(
        f"**{n} of {len(result.probes)} probed events returned a snapshot**, "
        f"taken {result.snapshot_lead_minutes} minutes before kickoff, across "
        f"{len(result.markets_requested)} requested markets."
    )
    add("")
    add(result.spend.summary_line())
    if result.spend.credits_estimated and result.spend.credits_spent:
        ratio = result.spend.credits_spent / result.spend.credits_estimated
        add("")
        add(
            f"Actual spend was **{ratio:.0%} of the pessimistic bound**. The "
            "gap is not slack — it is the measurement: the endpoint bills per "
            "market *returned*, so the shortfall is exactly the markets no "
            "book retained."
        )
    if result.stopped_early:
        add("")
        add(f"> **Stopped early.** {result.stopped_early}")
    add("")

    windows = Counter(probe.target.window for probe in result.successful)
    add("## What was sampled")
    add("")
    add(
        "Stratified by kickoff window, because book coverage is not uniform "
        "across the schedule and a sample drawn from national night games "
        "would measure marquee retention and call it retention."
    )
    add("")
    add("| Kickoff window | Events probed |")
    add("|:---------------|--------------:|")
    for window in sorted(windows):
        add(f"| {window} | {windows[window]} |")
    seasons = Counter(probe.target.season for probe in result.successful)
    add("")
    add(
        "Seasons: "
        + ", ".join(f"{season} ({seasons[season]})" for season in sorted(seasons))
        + f". Probing never goes earlier than {PROPS_AVAILABLE_FROM}, before "
        "which the provider served featured markets only — absence there "
        "would be the data not existing, not the provider not retaining it."
    )
    add("")

    rollups = rollup_by_project_market(result)
    measurable = [item for item in rollups if item.retained]
    add("## Retention by market — the unit that actually gets approved")
    add("")
    add(
        "A market and its alternate ladder are one market everywhere else in "
        "this repository, so they are one row here. Reading the per-key table "
        "below on its own is how the EPL lab wrote off `total_2_5` for a "
        "season: the complete line was absent from the featured market and "
        "present in the ladder the whole time."
    )
    add("")
    add("| Market | Provider keys | Verdict | Books | Priced outcomes |")
    add("|:-------|:--------------|:--------|------:|----------------:|")
    for item in rollups:
        keys = ", ".join(f"`{key}`" for key in item.provider_keys)
        add(
            f"| `{item.project_key}` | {keys} | {item.verdict()} | "
            f"{len(item.books)} | {item.outcomes:,} |"
        )
    thin = [item for item in rollups if item.thin]
    solid = [item for item in measurable if not item.thin]
    add("")
    add(
        f"**{len(measurable)} of {len(rollups)} markets have historical "
        f"prices at all, and {len(solid)} have enough to measure against.**"
    )
    if thin:
        add("")
        add(
            f"{len(thin)} are retained but too thin to support a "
            "measurement — fewer than a quarter of the probed events, or a "
            "single book quoting them: "
            + ", ".join(
                f"`{item.project_key}` ({item.events_seen}/"
                f"{item.events_probed} events, {len(item.books)} book(s), "
                f"{item.outcomes:,} outcomes)"
                for item in thin
            )
            + ". A measurement against one book measures that book's pricing, "
            "not the market's. These are bought only if a purchase is buying "
            "their neighbours anyway, and their evidence accumulates forward."
        )
    unmeasurable = [item for item in rollups if not item.retained]
    if unmeasurable:
        add("")
        add(
            f"{len(unmeasurable)} have no historical price at all: "
            + ", ".join(f"`{item.project_key}`" for item in unmeasurable)
            + ". Those accumulate forward evidence and nothing else."
        )
    add("")

    add("## Retention, provider key by provider key")
    add("")
    add(
        "The same data before the rollup. Useful for deciding what to *ask* "
        "for — an unretained key is a key not worth buying — and misleading "
        "for deciding what can be *measured*, which the table above answers."
    )
    add("")
    add("| Provider market | This lab calls it | Verdict | Books | Priced outcomes |")
    add("|:----------------|:------------------|:--------|------:|----------------:|")
    retained: list[str] = []
    absent: list[str] = []
    refused = set(result.refused_everywhere())
    for market in result.markets_requested:
        books = result.books(market)
        verdict = result.verdict(market)
        add(
            f"| `{market}` | `{_project_label(market)}` | {verdict} | "
            f"{len(books)} | {result.outcomes(market):,} |"
        )
        if result.events_seen(market):
            retained.append(market)
        elif market not in refused:
            absent.append(market)
    add("")

    add("## What this supports")
    add("")
    add(
        f"**{len(retained)} of {len(result.markets_requested)} provider keys "
        f"returned prices**, covering "
        f"**{len(measurable)} of {len(rollups)} markets**. The second number "
        "is the one that matters: it is markets, not keys, that get modelled, "
        "measured and approved."
    )
    if refused:
        add("")
        add(
            f"**{len(refused)} were refused by name** — the provider does not "
            "serve these keys for this sport, which is a different fact from "
            "not retaining them, and is why the request list is bisected "
            "rather than reported as one failure: "
            + ", ".join(f"`{m}`" for m in sorted(refused))
            + "."
        )
    if absent:
        add("")
        if n < MINIMUM_PROBES_FOR_ABSENCE:
            add(
                f"**{len(absent)} were not seen in {n} event(s).** That is "
                f"below the {MINIMUM_PROBES_FOR_ABSENCE} events this lab "
                "requires before absence means anything, so it is recorded as "
                "*not seen*, not as *cannot be measured*. A single probe once "
                "called an NHL market unmeasurable that was priced on 54 of "
                "the next 58 events."
            )
        else:
            covered = {
                item.project_key for item in rollups if item.retained
            }
            rescued = sorted(
                m
                for m in absent
                if (market_for_provider_key(m) or None)
                and market_for_provider_key(m).key in covered
            )
            stranded = [m for m in absent if m not in rescued]
            add(
                f"**{len(absent)} provider keys were not seen in any of {n} "
                "events**: " + ", ".join(f"`{m}`" for m in sorted(absent)) + "."
            )
            if rescued:
                add("")
                add(
                    f"**{len(rescued)} of those are still measurable**, "
                    "because another key feeds the same market — "
                    + ", ".join(f"`{m}`" for m in rescued)
                    + ". This is the `total_2_5` lesson in a new costume, and "
                    "it is why the rollup above is the table to read."
                )
            if stranded:
                add("")
                add(
                    f"**{len(stranded)} leave their market with no historical "
                    "price at all**: "
                    + ", ".join(f"`{m}`" for m in sorted(stranded))
                    + "."
                )
    add("")
    add(
        "None of this is a statement about whether a market is worth betting. "
        "It is a statement about whether a priced test of it is possible. See "
        "`docs/what_we_can_and_cannot_claim.md`."
    )

    failures = [probe for probe in result.probes if not probe.ok]
    if failures:
        add("")
        add("## Events that produced nothing, and why")
        add("")
        add("| Event | Reason |")
        add("|:------|:-------|")
        for probe in failures:
            add(f"| {probe.target.label} | {probe.error or 'unknown'} |")
        add("")
        add(
            "A failed probe is counted and named. It is never treated as a "
            "market being absent, because those look identical in a total and "
            "mean opposite things."
        )

    return "\n".join(lines) + "\n"


def to_json(result: ProbeResult, league: League) -> dict[str, Any]:
    return {
        "league": league.key,
        "snapshot_lead_minutes": result.snapshot_lead_minutes,
        "events_probed": len(result.probes),
        "events_returned": len(result.successful),
        "credits_spent": result.spend.credits_spent,
        "credits_estimated": result.spend.credits_estimated,
        "quota_remaining": result.spend.quota_remaining,
        "quota_used": result.spend.quota_used,
        "requests_made": result.spend.requests_made,
        "stopped_early": result.stopped_early,
        "notes": list(result.spend.notes),
        "markets": {
            market: {
                "project_key": _project_label(market),
                "events_seen": result.events_seen(market),
                "books": list(result.books(market)),
                "outcomes": result.outcomes(market),
                "verdict": result.verdict(market),
            }
            for market in result.markets_requested
        },
        "rollup": {
            item.project_key: {
                "provider_keys": list(item.provider_keys),
                "events_seen": item.events_seen,
                "events_probed": item.events_probed,
                "books": list(item.books),
                "outcomes": item.outcomes,
                "verdict": item.verdict(),
                "thin": item.thin,
            }
            for item in rollup_by_project_market(result)
        },
        "events": [
            {
                "label": probe.target.label,
                "season": probe.target.season,
                "week": probe.target.week,
                "window": probe.target.window,
                "home": probe.target.home,
                "away": probe.target.away,
                "snapshot": probe.target.snapshot,
                "event_id": probe.event_id,
                "markets_returned": list(probe.markets_returned),
                "refused": list(probe.refused_markets),
                "credits_spent": probe.credits_spent,
                "error": probe.error,
            }
            for probe in result.probes
        ],
    }
