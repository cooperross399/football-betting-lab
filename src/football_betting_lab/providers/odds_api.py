"""The Odds API adapter. Shadow-only by construction.

What this module does: fetch prices, normalise them into long-form rows, and
write them into `data/staging/`. What it does not do, ever: decide anything.
The card cannot read `data/staging/` — it reads only markets a reviewed policy
allowlists. So a fetch can be wrong, incomplete, or surprising without a single
pick changing.

## The credential

Read from `FOOTBALL_ODDS_API_KEY` in the environment (a GitHub secret in CI, a
gitignored `.env` locally). It is never written to a report, a provenance file,
a staged row, or a log line. Every string that reaches a report goes through
`redact`, and `tests/test_no_secrets_committed.py` fails the build if a key
shape ever reaches a tracked file.

**The key is never passed as a command-line argument.** A process list is
world-readable on a shared machine and a CI log echoes commands.

## What a fetch costs

From the provider's own documentation, verified 2026-08-28:

* `/v4/sports` and `/v4/sports/{sport}/events` — **free**.
* `/v4/sports/{sport}/odds` — `markets x regions`, whole slate.
* `/v4/sports/{sport}/events/{id}/odds` — `unique markets **returned** x
  regions`. An asked-for market nobody quotes costs nothing.
* `/v4/sports/{sport}/scores?daysFrom=N` — 2.
* every `/v4/historical/...` equivalent — **10x** the live rate.

Every entry point states its cost before spending it and takes a hard cap, so
a probe cannot become a bill by accident. The cap is checked **before** each
request, against the pessimistic bound, and the real spend is read afterwards
from `x-requests-last` rather than assumed.

## The sport key comes from the league registry

Never from a literal here. That is what makes NCAAF a registry entry rather
than a search-and-replace, and `tests/test_league_registry_is_the_only_place.py`
fails the build if this module ever writes one.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

import requests

from football_betting_lab.leagues import League
from football_betting_lab.providers.env_file import redact


API_KEY_ENV = "FOOTBALL_ODDS_API_KEY"
API_BASE_URL_ENV = "FOOTBALL_ODDS_API_BASE_URL"
DEFAULT_API_BASE_URL = "https://api.the-odds-api.com"

#: Only these hosts. A base-URL override is a convenience for testing against a
#: local mock, not a way to point the credential at an arbitrary server.
ALLOWED_API_HOSTS = frozenset({"api.the-odds-api.com", "ipv6-api.the-odds-api.com"})

PROVIDER_KEY = "odds_api"
PROVIDER_NAME = "the_odds_api"
PROVIDER_TYPE = "odds_api"

DEFAULT_REGIONS = "us"

#: The only response headers that may be recorded. Everything else in a
#: response's headers is either useless here or a place a credential could
#: hide; an allowlist is the safe shape.
SAFE_RESPONSE_HEADERS = (
    "x-requests-remaining",
    "x-requests-used",
    "x-requests-last",
)

#: Historical endpoints bill ten times the live rate. Used only as a
#: pre-flight upper bound, so the cap can be over-respected but never
#: breached. Real spend is read from `x-requests-last`.
HISTORICAL_MULTIPLIER = 10

#: The historical events listing. Documented flatly at 1, and free when it
#: finds nothing.
HISTORICAL_EVENTS_LIST_COST = 1


class ProviderError(RuntimeError):
    """The provider could not be used. Never carries a credential."""


class MissingCredentialError(ProviderError):
    """No key is available, so nothing live may be attempted."""


class CreditCapReached(ProviderError):
    """The next request could breach the cap, so it was not made."""


Requester = Callable[..., Any]


def _default_requester(url: str, *, params: Mapping[str, str], timeout: float) -> Any:
    return requests.get(url, params=dict(params), timeout=timeout)


@dataclass
class Spend:
    """What a run actually cost, measured rather than estimated."""

    credits_spent: int = 0
    requests_made: int = 0
    quota_remaining: str = ""
    quota_used: str = ""
    #: What the pessimistic pre-flight bound would have predicted, kept so the
    #: two can be compared in the report. A large gap is information: it means
    #: most asked markets are not quoted.
    credits_estimated: int = 0
    notes: list[str] = field(default_factory=list)

    def record(self, headers: Mapping[str, str], *, fallback: int) -> int:
        """Charge one response, preferring the measured cost over the guess.

        A missing `x-requests-last` charges the pessimistic fallback. Guessing
        low would let a run drift past its cap while reporting that it had not.
        """
        self.requests_made += 1
        try:
            actual = int(str(headers.get("x-requests-last", "")).strip())
        except (TypeError, ValueError):
            actual = 0
        if actual <= 0:
            actual = int(fallback)
            self.notes.append(
                "A response carried no `x-requests-last`; charged the "
                f"pessimistic estimate of {fallback} against the cap instead."
            )
        self.credits_spent += actual
        for header, attribute in (
            ("x-requests-remaining", "quota_remaining"),
            ("x-requests-used", "quota_used"),
        ):
            value = str(headers.get(header, "")).strip()
            if value:
                setattr(self, attribute, value)
        return actual

    def summary_line(self) -> str:
        line = (
            f"{self.credits_spent:,} credit(s) actually spent over "
            f"{self.requests_made} request(s)"
        )
        if self.credits_estimated:
            line += (
                f"; the pessimistic pre-flight bound was "
                f"{self.credits_estimated:,}"
            )
        if self.quota_remaining:
            line += f"; {self.quota_remaining} remaining"
        return line + "."


class OddsApiProvider:
    """One door to the provider. Every request in this repository goes through it.

    One door on purpose. Two callers building their own requests is how a
    credential reaches a log, how a cap gets bypassed, and how two copies of
    the billing rules drift apart.
    """

    def __init__(
        self,
        league: League,
        *,
        environment: Mapping[str, str] | None = None,
        requester: Requester | None = None,
        regions: str = DEFAULT_REGIONS,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.league = league
        self.environment = dict(os.environ if environment is None else environment)
        self.requester = requester or _default_requester
        self.regions = (regions or DEFAULT_REGIONS).strip()
        self.timeout_seconds = float(timeout_seconds)
        self._validate_base_url()

    # -- configuration ---------------------------------------------------

    @property
    def api_key(self) -> str:
        return str(self.environment.get(API_KEY_ENV, "")).strip()

    @property
    def base_url(self) -> str:
        return str(
            self.environment.get(API_BASE_URL_ENV) or DEFAULT_API_BASE_URL
        ).strip().rstrip("/")

    @property
    def sport_key(self) -> str:
        """From the registry. Never a literal in this module."""
        return self.league.provider_sport_key

    def _validate_base_url(self) -> None:
        host = (urlparse(self.base_url).hostname or "").lower()
        if host in ALLOWED_API_HOSTS:
            return
        if host in {"localhost", "127.0.0.1", "::1"}:
            # A local mock is the only other permitted target, and only
            # because a test that cannot run offline is a test nobody runs.
            return
        raise ProviderError(
            f"Refusing to send the credential to host {host!r}. Allowed: "
            f"{sorted(ALLOWED_API_HOSTS)} or a localhost mock."
        )

    def _require_credential(self) -> None:
        if not self.api_key:
            raise MissingCredentialError(
                f"A live fetch requires `{API_KEY_ENV}` from the environment, "
                "a gitignored local `.env`, or a GitHub Secret. Never pass the "
                "key as a command argument and never commit it."
            )

    # -- the one request path --------------------------------------------

    def _get(self, url: str, params: Mapping[str, str]) -> tuple[Any, dict[str, str]]:
        try:
            response = self.requester(
                url, params=dict(params), timeout=self.timeout_seconds
            )
        except (requests.RequestException, OSError, TimeoutError) as exc:
            raise ProviderError(
                redact(
                    f"The odds provider could not be reached "
                    f"({type(exc).__name__}). Nothing was written."
                )
            ) from exc
        status = int(getattr(response, "status_code", 0) or 0)
        if status != 200:
            # The status alone, never the URL: the URL carries the key.
            raise ProviderError(
                f"The odds provider returned HTTP {status or 'unknown'}. "
                "Nothing was written."
            )
        try:
            payload = response.json()
        except (AttributeError, TypeError, ValueError) as exc:
            raise ProviderError("The odds provider returned unreadable JSON.") from exc
        headers = getattr(response, "headers", {}) or {}
        safe = {
            name: str(headers.get(name, ""))
            for name in SAFE_RESPONSE_HEADERS
            if headers.get(name) is not None
        }
        return payload, safe

    # -- free endpoints ---------------------------------------------------

    def quota(self) -> dict[str, str]:
        """Remaining and used, from the free `/v4/sports` listing.

        Documented as costing nothing, so this is the cheapest possible answer
        to "how much is left" and to "when does the month reset" — the reset
        shows up as `x-requests-used` falling, which is worth watching for and
        costs nothing to watch.
        """
        self._require_credential()
        _, headers = self._get(
            f"{self.base_url}/v4/sports", {"apiKey": self.api_key}
        )
        return headers

    def list_events(self) -> list[dict[str, Any]]:
        """The upcoming slate. Free, and **upcoming only**.

        Pointing this at a past window returns nothing, which looks exactly
        like "the provider has no data" and is not. Past slates come from
        `list_historical_events`.
        """
        self._require_credential()
        payload, _ = self._get(
            f"{self.base_url}/v4/sports/{self.sport_key}/events",
            {"apiKey": self.api_key, "dateFormat": "iso"},
        )
        if not isinstance(payload, list):
            raise ProviderError("The events list is not a JSON list.")
        return [item for item in payload if isinstance(item, dict)]

    # -- historical -------------------------------------------------------

    def list_historical_events(
        self, snapshot: str, *, spend: Spend, credit_cap: int
    ) -> list[dict[str, Any]]:
        """Events on the slate at a past instant, plus what the lookup cost.

        Documented at one credit, and free when it finds nothing.
        """
        self._require_credential()
        _guard(spend, credit_cap, HISTORICAL_EVENTS_LIST_COST, "a historical slate")
        spend.credits_estimated += HISTORICAL_EVENTS_LIST_COST
        payload, headers = self._get(
            f"{self.base_url}/v4/historical/sports/{self.sport_key}/events",
            {"apiKey": self.api_key, "date": str(snapshot), "dateFormat": "iso"},
        )
        spend.record(headers, fallback=HISTORICAL_EVENTS_LIST_COST)
        data = payload.get("data") if isinstance(payload, Mapping) else payload
        return [item for item in (data or []) if isinstance(item, dict)]

    def historical_event_odds(
        self,
        event_id: str,
        snapshot: str,
        markets: tuple[str, ...],
        *,
        spend: Spend,
        credit_cap: int,
    ) -> dict[str, Any]:
        """One event's prices at a past instant.

        Billed at `10 x unique markets **returned** x regions`, so a market
        nobody retained costs nothing — but the cap is checked against every
        market being returned, which is the only direction it is safe to be
        wrong in.
        """
        self._require_credential()
        regions = len([r for r in self.regions.split(",") if r.strip()]) or 1
        bound = HISTORICAL_MULTIPLIER * len(markets) * regions
        _guard(spend, credit_cap, bound, f"event {event_id}")
        spend.credits_estimated += bound
        payload, headers = self._get(
            f"{self.base_url}/v4/historical/sports/{self.sport_key}/events/"
            f"{event_id}/odds",
            {
                "apiKey": self.api_key,
                "regions": self.regions,
                "markets": ",".join(markets),
                "oddsFormat": "american",
                "dateFormat": "iso",
                "date": str(snapshot),
            },
        )
        spend.record(headers, fallback=bound)
        data = payload.get("data") if isinstance(payload, Mapping) else payload
        return data if isinstance(data, Mapping) else {}


def _guard(spend: Spend, credit_cap: int, bound: int, what: str) -> None:
    """Refuse a request whose pessimistic cost could breach the cap.

    Checked **before** the request, not after. A cap enforced after the spend
    is not a cap; it is a report of how far past it the run went.
    """
    if credit_cap and spend.credits_spent + bound > credit_cap:
        raise CreditCapReached(
            f"Stopping before {what}: it could cost up to {bound} credits, "
            f"{spend.credits_spent} of the {credit_cap}-credit cap are already "
            "spent, and the cap is enforced against the pessimistic bound. "
            "Nothing further was requested."
        )
