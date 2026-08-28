"""Which club a player is on **now**, and who a provider name refers to.

A player's rate travels with him — shooting, target share, yards per carry are
his, not his club's — so the models learn rates from game logs and that is
right. But the logs also carry the club he last played for, which in September
is the club he left.

The NHL lab measured what that costs: **166 of 815 priced players (20.4%) had
changed clubs over one summer**, and each one matched neither side of the game
being priced, so each produced no opinion at all. A fifth of the pool missing
from opening night, looking exactly like books not posting props.

The first live NFL shadow run reproduced it immediately. On 2026-08-28 the
board for New England at Seattle priced **A.J. Brown** and **Romeo Doubs** —
a 2025 Eagle and a 2025 Packer, both on New England's 2026 roster. Taken from
their last logged game they belong to neither club in the fixture.

So `current_rosters` decides the side, and the logs are the fallback. A roster
naming a club that is not in the game fails the same safe way a stale log does:
**no opinion**, reported, never guessed at.

## Why matching is by identity rather than by string

The provider spells names its own way and the two sources disagree in ways a
string comparison cannot bridge: `A.J.` against `AJ`, `Deebo Samuel Sr.`
against `Deebo Samuel`, `Marvin Mims Jr.` against `Marvin Mims`, apostrophes
in `D'Onta Foreman`. Every alias of a name resolves to one identity.

**Disambiguation is by the clubs in the game, and a lone candidate on the
wrong team is a void, not a match.** That rule is the NHL lab's, earned on two
Sebastian Ahos and two Elias Petterssons: a fuzzy match produces a confident
price for a bet nobody placed, and the row looks exactly like a correct one.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from football_betting_lab.data import nflverse
from football_betting_lab.leagues import League
from football_betting_lab.providers.team_names import (
    abbreviations,
    name_to_abbreviation,
    resolve_team,
)
from football_betting_lab.season import clean_text


#: Generational suffixes carry no identity. Two people are never told apart by
#: one, and the provider drops them inconsistently.
SUFFIXES = frozenset({"jr", "sr", "ii", "iii", "iv", "v"})

_PUNCTUATION = re.compile(r"[.’'`\-]")
_WHITESPACE = re.compile(r"\s+")

#: What a resolution failed on, so a report can say which rather than "no".
NO_CANDIDATE = "no_candidate"
WRONG_TEAM = "wrong_team"
AMBIGUOUS = "ambiguous"
#: The fixture was described in the provider's vocabulary rather than this
#: lab's. A distinct reason on purpose — see `resolve`.
UNRESOLVED_CLUB = "unresolved_club"


def normalise_name(value: object) -> str:
    """One spelling for every way a name is written.

    Periods and apostrophes go, which collapses `A.J.` to `aj` and `D'Onta`
    to `donta`; generational suffixes go, which collapses `Deebo Samuel Sr.`
    to `deebo samuel`. Both directions matter — the provider adds suffixes the
    roster omits and omits ones the roster adds.
    """
    text = clean_text(value)
    if not text:
        return ""
    text = _PUNCTUATION.sub("", text).casefold()
    parts = [part for part in _WHITESPACE.split(text) if part]
    while len(parts) > 1 and parts[-1] in SUFFIXES:
        parts.pop()
    return " ".join(parts)


@dataclass(frozen=True)
class RosterEntry:
    player_id: str
    name: str
    team: str
    position: str


@dataclass(frozen=True)
class Resolution:
    """Who a provider name refers to in one fixture, or why it could not say."""

    entry: RosterEntry | None
    reason: str = ""
    candidates: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return self.entry is not None


class Rosters:
    """Every player on a current roster, indexed by normalised name."""

    def __init__(self, entries: list[RosterEntry], league: League) -> None:
        self.entries = entries
        self.league = league
        #: The league's own club list, from the registry. Validated against
        #: this rather than against the roster's contents: a club with nobody
        #: on it is a suspicious roster, which is a different fault from a
        #: caller describing the fixture in the wrong vocabulary.
        self._clubs = frozenset(abbreviations(league))
        self._by_name: dict[str, list[RosterEntry]] = defaultdict(list)
        for entry in entries:
            self._by_name[normalise_name(entry.name)].append(entry)

    def __len__(self) -> int:
        return len(self.entries)

    @classmethod
    def load(cls, league: League, raw_dir: Path, *, season: int) -> "Rosters":
        path = nflverse.feed_path(
            nflverse.FEEDS_BY_NAME["rosters"], league, raw_dir, season
        )
        if not path.is_file():
            return cls([], league)
        frame = pd.read_csv(path, low_memory=False)
        entries = [
            RosterEntry(
                player_id=clean_text(row.get("gsis_id")),
                name=clean_text(row.get("full_name")),
                team=clean_text(row.get("team")).upper(),
                position=clean_text(row.get("position")),
            )
            for _, row in frame.iterrows()
        ]
        return cls([entry for entry in entries if entry.name and entry.team], league)

    def resolve(self, provider_name: object, *, home: str, away: str) -> Resolution:
        """Who this name is, given the two clubs actually playing.

        The fixture is the disambiguator. Without it, two players sharing a
        name are a coin flip; with it, the answer is usually exact and the
        cases where it is not are reported rather than guessed.
        """
        key = normalise_name(provider_name)
        if not key:
            return Resolution(None, NO_CANDIDATE)
        candidates = self._by_name.get(key, [])
        if not candidates:
            return Resolution(None, NO_CANDIDATE)
        clubs = {str(home).upper(), str(away).upper()}
        # The fixture must be described in abbreviations, because that is what
        # a roster holds. Passing the provider's club names instead does not
        # fail loudly: every candidate is "on the wrong team" and every player
        # resolves to nothing, which reads as a board full of unknown players.
        #
        # That is exactly what happened the first time this was called, and it
        # is the same silent-miss shape as the club-name bug this module was
        # written to prevent — so the check is here rather than in a comment.
        stray = clubs - self._clubs
        if stray:
            return Resolution(None, UNRESOLVED_CLUB, tuple(sorted(stray)))
        in_game = [entry for entry in candidates if entry.team in clubs]
        if len(in_game) == 1:
            return Resolution(in_game[0])
        if not in_game:
            # A lone candidate on the wrong team is a void, not a match. He is
            # on a roster; he is not in this game.
            return Resolution(
                None,
                WRONG_TEAM,
                tuple(sorted({entry.team for entry in candidates})),
            )
        return Resolution(
            None, AMBIGUOUS, tuple(sorted(entry.player_id for entry in in_game))
        )


def last_logged_teams(logs: pd.DataFrame) -> dict[str, str]:
    """The club each player last appeared for. The fallback, never the source.

    Kept so the cost of using it can be measured rather than argued about.
    """
    if logs.empty:
        return {}
    frame = logs.sort_values(["season", "week"])
    return {
        normalise_name(row.player_name): str(row.team).upper()
        for row in frame.itertuples()
        if clean_text(row.player_name)
    }


@dataclass
class StalenessReport:
    """How much a stale club assignment would cost on one board."""

    priced_players: int = 0
    resolved_from_roster: int = 0
    changed_club: int = 0
    unknown_to_roster: int = 0
    wrong_team: int = 0
    ambiguous: int = 0
    unresolved_clubs: int = 0
    movers: list[str] = field(default_factory=list)

    @property
    def changed_share(self) -> float:
        if not self.priced_players:
            return 0.0
        return self.changed_club / self.priced_players

    def summary_line(self) -> str:
        extra = (
            f" {self.unresolved_clubs} row(s) named a club this lab could not "
            "resolve at all, which is a caller fault rather than a roster one."
            if self.unresolved_clubs
            else ""
        )
        return (
            f"{self.priced_players} priced player(s); "
            f"{self.resolved_from_roster} resolved from the current roster; "
            f"**{self.changed_club} ({self.changed_share:.1%}) are on a "
            "different club than their last logged game**, and each would "
            "have produced no opinion at all if the logs decided the side."
            + extra
        )


def measure_staleness(
    prices: pd.DataFrame, rosters: Rosters, logs: pd.DataFrame, league: League
) -> StalenessReport:
    """What taking the club from the logs would cost on this board.

    Measured rather than asserted, and re-measured every run, because the
    number is a property of one offseason and not a constant.
    """
    report = StalenessReport()
    if prices.empty or "player" not in prices.columns:
        return report
    last = last_logged_teams(logs)
    lookup = name_to_abbreviation(league)
    seen: set[tuple[str, str, str]] = set()
    for row in prices.itertuples():
        name = clean_text(getattr(row, "player", ""))
        if not name:
            continue
        # Staged rows carry the provider's club names, because the join key
        # is built from the provider's own strings. The conversion to this
        # lab's vocabulary happens exactly once, here.
        home = resolve_team(getattr(row, "home_team", ""), league, lookup) or ""
        away = resolve_team(getattr(row, "away_team", ""), league, lookup) or ""
        marker = (normalise_name(name), home, away)
        if marker in seen:
            continue
        seen.add(marker)
        report.priced_players += 1
        resolution = rosters.resolve(name, home=home, away=away)
        if not resolution.resolved:
            if resolution.reason == UNRESOLVED_CLUB:
                report.unresolved_clubs += 1
            elif resolution.reason == WRONG_TEAM:
                report.wrong_team += 1
            elif resolution.reason == AMBIGUOUS:
                report.ambiguous += 1
            else:
                report.unknown_to_roster += 1
            continue
        report.resolved_from_roster += 1
        previous = last.get(normalise_name(name))
        if previous and previous != resolution.entry.team:
            report.changed_club += 1
            report.movers.append(
                f"{name}: {previous} -> {resolution.entry.team}"
            )
    return report
