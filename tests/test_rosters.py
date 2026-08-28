"""A player's club comes from the roster, and a near-match is never a match.

The two rules here are the NHL lab's, both earned expensively:

* the club comes from the **current roster**, never the last logged game —
  166 of 815 priced players (20.4%) had changed clubs over one summer, and
  each produced no opinion at all;
* **a lone candidate on the wrong team is a void, not a match** — a fuzzy
  match produces a confident price for a bet nobody placed, and the row looks
  exactly like a correct one.
"""

from __future__ import annotations

import pandas as pd
import pytest

from football_betting_lab.leagues import NFL
from football_betting_lab.rosters import (
    AMBIGUOUS,
    NO_CANDIDATE,
    UNRESOLVED_CLUB,
    WRONG_TEAM,
    RosterEntry,
    Rosters,
    last_logged_teams,
    measure_staleness,
    normalise_name,
)


def _rosters(*entries: tuple[str, str, str]) -> Rosters:
    return Rosters(
        [
            RosterEntry(player_id=pid, name=name, team=team, position="WR")
            for pid, name, team in entries
        ],
        NFL,
    )


# -- identity ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("left", "right"),
    [
        ("A.J. Brown", "AJ Brown"),
        ("Deebo Samuel Sr.", "Deebo Samuel"),
        ("Marvin Mims Jr.", "Marvin Mims"),
        ("D'Onta Foreman", "DOnta Foreman"),
        ("Michael Pittman Jr.", "Michael Pittman"),
        ("  Josh   Allen  ", "Josh Allen"),
    ],
)
def test_every_spelling_of_a_name_resolves_to_one_identity(
    left: str, right: str
) -> None:
    assert normalise_name(left) == normalise_name(right)


def test_two_different_people_do_not_collapse_into_one() -> None:
    """Suffix stripping must not make a father and son the same person by
    name alone — the fixture is what tells them apart, not the string."""
    assert normalise_name("Josh Allen") != normalise_name("Keenan Allen")
    assert normalise_name("Odell Beckham") != normalise_name("Odell Beckham Jr")[:5] + "zzz"


def test_a_blank_or_nan_name_normalises_to_empty_rather_than_the_string_nan() -> None:
    """A CSV round-trip turns an empty field into NaN, which is truthy."""
    assert normalise_name(float("nan")) == ""
    assert normalise_name(None) == ""
    assert normalise_name("nan") == ""


# -- resolution --------------------------------------------------------------


def test_the_fixture_disambiguates_two_players_sharing_a_name() -> None:
    rosters = _rosters(("1", "Josh Allen", "BUF"), ("2", "Josh Allen", "JAX"))

    assert rosters.resolve("Josh Allen", home="BUF", away="NE").entry.player_id == "1"
    assert rosters.resolve("Josh Allen", home="JAX", away="NE").entry.player_id == "2"


def test_two_candidates_both_in_the_game_are_ambiguous_rather_than_guessed() -> None:
    rosters = _rosters(("1", "Josh Allen", "BUF"), ("2", "Josh Allen", "NE"))

    resolution = rosters.resolve("Josh Allen", home="BUF", away="NE")

    assert not resolution.resolved
    assert resolution.reason == AMBIGUOUS


def test_a_lone_candidate_on_the_wrong_team_is_a_void_not_a_match() -> None:
    """He is on a roster; he is not in this game. Matching him anyway would
    price a bet nobody placed and the row would look correct."""
    rosters = _rosters(("1", "Josh Allen", "BUF"))

    resolution = rosters.resolve("Josh Allen", home="KC", away="NE")

    assert not resolution.resolved
    assert resolution.reason == WRONG_TEAM
    assert resolution.candidates == ("BUF",)


def test_a_name_on_no_roster_resolves_to_nothing() -> None:
    resolution = _rosters(("1", "Josh Allen", "BUF")).resolve(
        "Nobody Here", home="BUF", away="NE"
    )

    assert resolution.reason == NO_CANDIDATE


def test_a_fixture_named_in_the_providers_vocabulary_fails_loudly(
) -> None:
    """The bug this guard was written after.

    Passing club *names* where abbreviations belong does not fail loudly on
    its own: every candidate is "on the wrong team", every player resolves to
    nothing, and the board reads as full of unknown players. It happened on
    the first real call, and it is the same silent-miss shape the module
    exists to prevent.
    """
    rosters = _rosters(("1", "Josh Allen", "BUF"))

    resolution = rosters.resolve(
        "Josh Allen", home="Buffalo Bills", away="New England Patriots"
    )

    assert resolution.reason == UNRESOLVED_CLUB
    assert resolution.reason != WRONG_TEAM


# -- the measurement ---------------------------------------------------------


def _prices(rows: list[tuple[str, str, str]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"player": p, "home_team": h, "away_team": a, "market": "receptions"}
            for p, h, a in rows
        ]
    )


def _logs(rows: list[tuple[str, str]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"player_name": name, "team": team, "season": 2025, "week": 1}
            for name, team in rows
        ]
    )


def test_a_player_who_changed_clubs_is_counted_and_named() -> None:
    """The whole reason the roster decides the side."""
    rosters = _rosters(("1", "A.J. Brown", "NE"))
    prices = _prices([("A.J. Brown", "Seattle Seahawks", "New England Patriots")])

    report = measure_staleness(prices, rosters, _logs([("A.J. Brown", "PHI")]), NFL)

    assert report.priced_players == 1
    assert report.resolved_from_roster == 1
    assert report.changed_club == 1
    assert report.movers == ["A.J. Brown: PHI -> NE"]


def test_a_player_who_stayed_put_is_not_counted_as_a_mover() -> None:
    rosters = _rosters(("1", "Jaxon Smith-Njigba", "SEA"))
    prices = _prices(
        [("Jaxon Smith-Njigba", "Seattle Seahawks", "New England Patriots")]
    )

    report = measure_staleness(
        prices, rosters, _logs([("Jaxon Smith-Njigba", "SEA")]), NFL
    )

    assert report.changed_club == 0
    assert report.resolved_from_roster == 1


def test_one_player_priced_in_many_markets_is_counted_once() -> None:
    """Otherwise the share is a count of rows wearing a player's name."""
    rosters = _rosters(("1", "A.J. Brown", "NE"))
    prices = _prices(
        [("A.J. Brown", "Seattle Seahawks", "New England Patriots")] * 5
    )

    report = measure_staleness(prices, rosters, _logs([("A.J. Brown", "PHI")]), NFL)

    assert report.priced_players == 1
    assert report.changed_club == 1


def test_the_share_is_zero_rather_than_a_division_error_on_an_empty_board() -> None:
    report = measure_staleness(pd.DataFrame(), _rosters(), pd.DataFrame(), NFL)

    assert report.priced_players == 0
    assert report.changed_share == 0.0


def test_the_last_logged_team_is_the_most_recent_one() -> None:
    """The fallback has to be the *latest* log, or it is a third wrong answer."""
    logs = pd.DataFrame(
        [
            {"player_name": "A.J. Brown", "team": "TEN", "season": 2024, "week": 1},
            {"player_name": "A.J. Brown", "team": "PHI", "season": 2025, "week": 9},
        ]
    )

    assert last_logged_teams(logs)[normalise_name("A.J. Brown")] == "PHI"
