"""The provider says "New England Patriots"; every model here is keyed "NE".

Without this map the lookups miss silently and every game is priced
league-average versus league-average — plausible numbers, no error, nothing to
notice. That was the **first** member of the NHL lab's join-vocabulary bug
family, and it is the reason this module exists before any price is fetched
rather than after.

Unresolved names are **returned to the caller to report, never guessed at**. A
fuzzy match produces a confident price for a bet nobody placed, and the row
looks exactly like a correct one.

The map is keyed by `League.key` read from the registry, not by a literal, so
NCAAF's map drops in beside this one.
"""

from __future__ import annotations

from collections.abc import Mapping

from football_betting_lab.leagues import NFL, League


#: nflverse abbreviation -> the provider's full club name.
#:
#: Relocations matter here and are the trap: nflverse uses the *current*
#: abbreviation for a franchise across its whole history, so a 2015 Rams game
#: is `LA`, not `STL`. The historical aliases below exist because the odds
#: provider's own historical payloads use the name the club had at the time.
_NFL_ABBREV_TO_NAME: dict[str, str] = {
    "ARI": "Arizona Cardinals",
    "ATL": "Atlanta Falcons",
    "BAL": "Baltimore Ravens",
    "BUF": "Buffalo Bills",
    "CAR": "Carolina Panthers",
    "CHI": "Chicago Bears",
    "CIN": "Cincinnati Bengals",
    "CLE": "Cleveland Browns",
    "DAL": "Dallas Cowboys",
    "DEN": "Denver Broncos",
    "DET": "Detroit Lions",
    "GB": "Green Bay Packers",
    "HOU": "Houston Texans",
    "IND": "Indianapolis Colts",
    "JAX": "Jacksonville Jaguars",
    "KC": "Kansas City Chiefs",
    "LA": "Los Angeles Rams",
    "LAC": "Los Angeles Chargers",
    "LV": "Las Vegas Raiders",
    "MIA": "Miami Dolphins",
    "MIN": "Minnesota Vikings",
    "NE": "New England Patriots",
    "NO": "New Orleans Saints",
    "NYG": "New York Giants",
    "NYJ": "New York Jets",
    "PHI": "Philadelphia Eagles",
    "PIT": "Pittsburgh Steelers",
    "SEA": "Seattle Seahawks",
    "SF": "San Francisco 49ers",
    "TB": "Tampa Bay Buccaneers",
    "TEN": "Tennessee Titans",
    "WAS": "Washington Commanders",
}

#: Names the provider has used for a club that nflverse spells differently.
#: Kept separate from the canonical map so the canonical direction stays
#: one-to-one and a report can always print the club's current name.
_NFL_ALIASES: dict[str, str] = {
    "los angeles rams": "LA",
    "st. louis rams": "LA",
    "st louis rams": "LA",
    "san diego chargers": "LAC",
    "oakland raiders": "LV",
    "washington football team": "WAS",
    "washington redskins": "WAS",
    "las vegas raiders": "LV",
}

_BY_LEAGUE: dict[str, dict[str, str]] = {NFL.key: _NFL_ABBREV_TO_NAME}
_ALIASES_BY_LEAGUE: dict[str, dict[str, str]] = {NFL.key: _NFL_ALIASES}


def abbreviations(league: League) -> tuple[str, ...]:
    return tuple(sorted(_BY_LEAGUE.get(league.key, {})))


def name_to_abbreviation(league: League) -> dict[str, str]:
    """Every spelling the provider might use, lowercased, to an abbreviation."""
    lookup = {
        name.casefold(): abbrev
        for abbrev, name in _BY_LEAGUE.get(league.key, {}).items()
    }
    lookup.update(_ALIASES_BY_LEAGUE.get(league.key, {}))
    return lookup


def resolve_team(
    provider_name: object, league: League, lookup: Mapping[str, str] | None = None
) -> str | None:
    """The abbreviation for a provider club name, or None.

    None rather than a guess. The caller reports it; nothing downstream is
    allowed to invent a club.
    """
    text = str(provider_name or "").strip()
    if not text:
        return None
    table = dict(lookup) if lookup is not None else name_to_abbreviation(league)
    return table.get(text.casefold())
