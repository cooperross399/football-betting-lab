"""The league registry. Every league-specific fact lives here and nowhere else.

The NFL ships first and NCAAF is added later. The only way that addition is a
new registry entry rather than a refactor is if no other module ever writes a
league literal: not a sport key, not a market list, not a timezone, not a
credit cap, not a verdict path. A discipline test
(`tests/test_league_registry_is_the_only_place.py`) fails the build when one
appears, because the alternative — noticing during the NCAAF build — is
noticing after the cost has been paid.

## What "per league" means, precisely

Models are **fitted** per league. Measurements are **reported** per league.
Verdicts are **recorded** per league. Receipts and allowlist entries are
**signed** per league. Nothing is pooled into a headline number: 134 FBS teams
with forty-point talent gaps and 32 near-parity NFL teams do not share a
distribution, and a figure computed across both describes neither.

A shared or hierarchical model is not forbidden — it is *unproven*. It may
ship only when it is measured to beat two separate models on the price
backtest, per league, and the verdict recording that says so is itself
per league.

Adding NCAAF must not move a single NFL number. The NFL measurements are
recorded before the addition and pinned by a regression test; if they shift,
the addition touched something it had no business touching.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class League:
    """One league: what it is called, where its data comes from, what it costs."""

    #: The key used everywhere inside this repository. Also the directory
    #: segment under `data/` and the prefix on every output file, so two
    #: leagues can never write over each other's evidence.
    key: str
    #: Human title for reports.
    title: str
    #: The Odds API sport key. The provider's vocabulary, not ours.
    provider_sport_key: str
    #: The data-source adapter module that supplies schedules, results,
    #: rosters and player logs. Named rather than imported so the registry
    #: stays importable without pulling every adapter into every process.
    data_adapter: str
    #: The registry of markets this league prices. Per league because the
    #: provider serves NFL and NCAAF from the same key list but the books
    #: quote wildly different subsets, and "unquoted" must never be
    #: confused with "not asked for".
    market_registry: str
    #: The league's own calendar timezone. A game belongs to the day it is
    #: played in this zone, not to its UTC date.
    timezone: ZoneInfo
    #: Hard per-day credit cap. Not advisory: the fetch spends front-to-back
    #: and stops. Set from the league's own worst slate, so it can never
    #: starve one.
    daily_credit_cap: int
    #: Provider name in the staging policy. Allowlisting a market for one
    #: league never allowlists it for another, so the policy is keyed by
    #: `{provider}:{league}` and this is the league half.
    policy_provider_name: str = "the_odds_api"

    @property
    def data_dir_segment(self) -> str:
        """Where this league's data lives under `data/raw`, `data/processed`."""
        return self.key

    def output_name(self, stem: str, suffix: str) -> str:
        """`nfl_forward_evidence.md` — never a bare `forward_evidence.md`.

        An unprefixed output is a file two leagues would both write, and the
        second one to run would silently become the record.
        """
        return f"{self.key}_{stem}{suffix}"

    def verdict_dir(self, outputs_dir: Path) -> Path:
        return Path(outputs_dir) / self.key

    def policy_key(self) -> str:
        """The allowlist entry this league's card consults.

        Keyed by league on purpose: approving `player_pass_yds` in the NFL
        says nothing about approving it in college football, where the
        distribution, the roster churn and the books' own coverage are all
        different. One receipt, one league.
        """
        return f"{self.policy_provider_name}:{self.key}"


#: The NFL. The only league built today.
NFL = League(
    key="nfl",
    title="NFL",
    provider_sport_key="americanfootball_nfl",
    data_adapter="football_betting_lab.data.nflverse",
    market_registry="football_betting_lab.markets",
    timezone=ZoneInfo("America/New_York"),
    # 16 games on the season's largest slate (2027-01-10, Week 18, every
    # game simultaneous) times the 111 per-event markets asked, plus the
    # bulk call. Derived by `scripts/estimate_credit_cost.py` from the real
    # schedule rather than guessed, and re-derived when the market list
    # changes. A cap below the worst slate is a cap that starves it, and a
    # starved fetch and an unquoted market look identical in the reports.
    daily_credit_cap=1_800,
)

#: NCAAF is deliberately absent. Adding it is a `League(...)` here, an
#: adapter module, a market registry, its own fitted models, its own
#: measurements, its own verdicts and its own receipt — and nothing else.
#: It is not added now because the credit arithmetic does not yet permit it
#: (`docs/credit_cost.md`) and because no NFL number may move when it lands.
LEAGUES: dict[str, League] = {NFL.key: NFL}

#: The league this repository ships today. Anything defaulting to a league
#: uses this rather than the string "nfl".
DEFAULT_LEAGUE_KEY = NFL.key


def league_for(key: str) -> League:
    """Look up a league, or say which ones exist."""
    text = str(key or "").strip().lower()
    try:
        return LEAGUES[text]
    except KeyError as exc:
        raise KeyError(
            f"Unknown league {key!r}. Known leagues: {sorted(LEAGUES)}"
        ) from exc


def league_keys() -> tuple[str, ...]:
    return tuple(sorted(LEAGUES))
