"""Buying historical prices, resumably, under a hard cap.

Cooper approved this purchase on 2026-08-28: one season, two snapshots — the
price the card could have acted on, and the closing price — which gives a
priced backtest **and** closing-line value on every historical bet. At the
measured rate that is roughly 198,000 credits, which is two months of a
100,000-a-month quota. So it cannot be one run, and everything here is built
around that.

## Why the order matters more than the speed

A purchase that stops halfway leaves a sample, and **the order decides whether
that sample is representative or biased.** Buying weeks 1 to 10 and stopping
would measure early-season football and call it football: rosters are
healthier, weather is warmer, and books' props are looser before the market
learns the season.

So events are bought in a **van der Corput order** — first the middle of the
season, then the quarter points, then the eighths, and so on. Any prefix of
that order is spread evenly across the whole schedule, so a run that stops at
40% has bought a 40% sample of the season rather than the first 40% of it.

## Why a cached event costs nothing

Historical prices never change. Every response is cached under a key that
includes **which markets were asked for** — the fingerprint, because a later
run asking for one more market would otherwise be served the old file and
told, confidently, that the new market is not offered. So resuming is free and
re-running is free, and the cap only ever applies to genuinely new requests.

## The cap is checked before the request

Against the pessimistic bound, always. A cap enforced after the spend is not a
cap; it is a report of how far past it the run went. Real spend is read from
`x-requests-last`.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from football_betting_lab.leagues import League
from football_betting_lab.providers.odds_api import (
    CreditCapReached,
    OddsApiProvider,
    ProviderError,
    Spend,
)
from football_betting_lab.reports.retention_probe import (
    MARKETS_PER_REQUEST,
    ProbeTarget,
    _chunks,
    _fetch_chunk,
    _match_event,
    markets_fingerprint,
)


CACHE_DIRNAME = "historical_prices"
MANIFEST_FILENAME = "historical_manifest.json"

#: Minutes before kickoff for each snapshot this lab buys.
#:
#: The pair is the point. One snapshot gives a price and no closing-line
#: value; two give the model's price, the closing price, and therefore CLV on
#: every historical bet — which at 272 games a season is the fastest honest
#: signal available.
CARD_TIME_LEAD_MINUTES = 60
CLOSING_LEAD_MINUTES = 5


def van_der_corput_order(count: int) -> list[int]:
    """Indices ordered so that **every prefix is spread across the whole set**.

    The middle first, then the quarter points, then the eighths. This is what
    makes a half-finished purchase a half-sized sample of the season instead
    of the first half of the season, and the difference is the difference
    between a measurement and a seasonal artefact.
    """
    if count <= 0:
        return []
    scored = []
    for index in range(count):
        # Reverse the bits of (index + 1) to get its van der Corput value.
        value, n = 0.0, index + 1
        denominator = 2.0
        while n:
            value += (n & 1) / denominator
            n >>= 1
            denominator *= 2
        scored.append((value, index))
    scored.sort()
    return [index for _, index in scored]


@dataclass
class PurchaseProgress:
    """What has been bought, and what a run refused to buy."""

    season: int
    lead_minutes: int
    events_total: int = 0
    events_cached: int = 0
    events_bought: int = 0
    events_failed: int = 0
    rows_seen: int = 0
    spend: Spend = field(default_factory=Spend)
    stopped_early: str = ""
    failures: list[str] = field(default_factory=list)

    @property
    def events_done(self) -> int:
        return self.events_cached + self.events_bought

    @property
    def fraction_done(self) -> float:
        return self.events_done / self.events_total if self.events_total else 0.0

    def summary_line(self) -> str:
        return (
            f"{self.events_done} of {self.events_total} events at "
            f"T-{self.lead_minutes}min ({self.fraction_done:.0%}); "
            f"{self.events_bought} bought this run, {self.events_cached} "
            f"already cached, {self.events_failed} failed. "
            f"{self.spend.summary_line()}"
        )


def manifest_path(cache_dir: Path) -> Path:
    return Path(cache_dir) / MANIFEST_FILENAME


def read_manifest(cache_dir: Path) -> dict[str, Any]:
    path = manifest_path(cache_dir)
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def write_manifest(cache_dir: Path, manifest: dict[str, Any]) -> None:
    path = manifest_path(cache_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def snapshot_for(target: ProbeTarget, lead_minutes: int) -> str:
    moment = target.kickoff_utc - timedelta(minutes=lead_minutes)
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def cache_path(
    cache_dir: Path, event_id: str, snapshot: str, markets: Sequence[str]
) -> Path:
    stamp = str(snapshot).replace(":", "").replace("-", "")
    return Path(cache_dir) / f"{event_id}_{stamp}_{markets_fingerprint(markets)}.json"


def buy_season(
    provider: OddsApiProvider,
    league: League,
    targets: Sequence[ProbeTarget],
    markets: Sequence[str],
    *,
    lead_minutes: int,
    credit_cap: int,
    cache_dir: Path,
    season: int,
) -> PurchaseProgress:
    """Buy as much of a season as the cap allows, in a representative order."""
    asked = tuple(dict.fromkeys(str(m) for m in markets))
    progress = PurchaseProgress(
        season=season, lead_minutes=lead_minutes, events_total=len(targets)
    )
    Path(cache_dir).mkdir(parents=True, exist_ok=True)
    manifest = read_manifest(cache_dir)
    key = f"{season}:{lead_minutes}"
    done: dict[str, Any] = dict(manifest.get(key, {}))

    for index in van_der_corput_order(len(targets)):
        target = targets[index]
        snapshot = snapshot_for(target, lead_minutes)
        record = done.get(target.game_id)
        if record and record.get("markets") == markets_fingerprint(asked):
            progress.events_cached += 1
            progress.rows_seen += int(record.get("rows", 0))
            continue
        try:
            events = provider.list_historical_events(
                snapshot, spend=progress.spend, credit_cap=credit_cap
            )
            event_id, why = _match_event(events, target, league)
            if not event_id:
                progress.events_failed += 1
                progress.failures.append(f"{target.label}: {why}")
                continue
            rows = 0
            for chunk in _chunks(asked, MARKETS_PER_REQUEST):
                payload, _refused = _fetch_chunk(
                    provider,
                    event_id,
                    snapshot,
                    chunk,
                    spend=progress.spend,
                    credit_cap=credit_cap,
                )
                if payload:
                    cache_path(cache_dir, event_id, snapshot, chunk).write_text(
                        json.dumps(payload, indent=1, sort_keys=True) + "\n",
                        encoding="utf-8",
                    )
                    rows += sum(
                        len(market.get("outcomes", []) or [])
                        for bookmaker in payload.get("bookmakers", []) or []
                        for market in bookmaker.get("markets", []) or []
                    )
        except CreditCapReached as exc:
            progress.stopped_early = str(exc)
            break
        except ProviderError as exc:
            progress.events_failed += 1
            progress.failures.append(f"{target.label}: {exc}")
            continue

        done[target.game_id] = {
            "event_id": event_id,
            "snapshot": snapshot,
            "markets": markets_fingerprint(asked),
            "rows": rows,
        }
        progress.events_bought += 1
        progress.rows_seen += rows
        # Written after every event, not at the end. A run killed by a
        # timeout must not lose the record of what it already paid for.
        manifest[key] = done
        write_manifest(cache_dir, manifest)

    manifest[key] = done
    write_manifest(cache_dir, manifest)
    return progress
