"""Freeze once, settle honestly, and never let an interval be narrower than
the truth.

Forward evidence cannot be back-dated. Everything here protects the one
property that makes it worth anything: that what settles is what the card
actually said, before the game, unrevised.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from football_betting_lab.forward_evidence import (
    LOST,
    PATIENCE_DAYS,
    PUSH,
    SNAPSHOT_COLUMNS,
    UNSETTLEABLE,
    VOID,
    WON,
    append_ledger,
    interval_by_game,
    settle_snapshot,
    write_snapshot,
)
from football_betting_lab.leagues import NFL


LOOKUP = {"Seattle Seahawks": "SEA", "New England Patriots": "NE"}


def _games(home_score=24, away_score=20) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "game_id": "2026_01_NE_SEA",
                "game_date": "2026-09-09",
                "home_team": "SEA",
                "away_team": "NE",
                "home_score": home_score,
                "away_score": away_score,
            }
        ]
    )


def _logs(**columns) -> pd.DataFrame:
    row = {
        "game_id": "2026_01_NE_SEA",
        "player_name": "A Player",
        "reception_yards": 60.0,
        "receptions": 5.0,
        "anytime_td": 1.0,
    }
    row.update(columns)
    return pd.DataFrame([row])


def _snapshot(rows: list[dict]) -> pd.DataFrame:
    base = {
        "snapshot_date": "2026-09-09",
        "commence_time": "2026-09-10T00:20:00Z",
        "home_team": "Seattle Seahawks",
        "away_team": "New England Patriots",
        "market": "moneyline",
        "player": "",
        "selection": "home",
        "line": None,
        "american_odds": -150,
        "book": "draftkings",
        "model_probability": 0.6,
        "edge": 0.0,
        "gates_in_force": "test",
    }
    return pd.DataFrame(
        [{**base, **row} for row in rows], columns=list(SNAPSHOT_COLUMNS)
    )


def _settle(snapshot, games=None, logs=None, as_of=date(2026, 9, 15)):
    return settle_snapshot(
        snapshot,
        games=games if games is not None else _games(),
        logs=logs if logs is not None else _logs(),
        league=NFL,
        team_lookup=LOOKUP,
        as_of=as_of,
        settled_at="t",
    )


# -- the snapshot is written once --------------------------------------------


def test_the_first_opinion_of_the_day_stands(tmp_path: Path) -> None:
    """A repriced snapshot is not the card's opinion any more, and two
    snapshots for one day would let the flattering one be the one that
    settles."""
    prices = pd.DataFrame(
        [
            {
                "market": "moneyline",
                "selection": "home",
                "line": None,
                "american_odds": -150,
                "home_team": "Seattle Seahawks",
                "away_team": "New England Patriots",
                "commence_time": "2026-09-10T00:20:00Z",
                "player": "",
                "book": "dk",
            }
        ]
    )
    key_for = lambda row, *, market, selection, line: (market, selection)  # noqa: E731

    first = write_snapshot(
        prices,
        {("moneyline", "home"): 0.6},
        key_for=key_for,
        gates_in_force="test",
        snapshot_date="2026-09-09",
        archive_dir=tmp_path,
    )
    second = write_snapshot(
        prices,
        {("moneyline", "home"): 0.9},
        key_for=key_for,
        gates_in_force="test",
        snapshot_date="2026-09-09",
        archive_dir=tmp_path,
    )

    assert first is not None
    assert second is None
    assert pd.read_csv(first)["model_probability"].iloc[0] == pytest.approx(0.6)


def test_a_row_the_model_had_no_opinion_on_is_not_frozen(tmp_path: Path) -> None:
    """An absent key means no opinion, which is not a probability of zero."""
    prices = pd.DataFrame(
        [
            {
                "market": "moneyline",
                "selection": "home",
                "line": None,
                "american_odds": -150,
                "home_team": "Seattle Seahawks",
                "away_team": "New England Patriots",
                "commence_time": "2026-09-10T00:20:00Z",
                "player": "",
                "book": "dk",
            }
        ]
    )

    path = write_snapshot(
        prices,
        {},
        key_for=lambda row, *, market, selection, line: (market, selection),
        gates_in_force="test",
        snapshot_date="2026-09-09",
        archive_dir=tmp_path,
    )

    assert path is not None
    assert pd.read_csv(path).empty


# -- settlement --------------------------------------------------------------


def test_a_winning_moneyline_pays_the_price_it_was_frozen_at() -> None:
    settled = _settle(_snapshot([{"selection": "home", "american_odds": 150}])).settled

    assert settled["outcome"].iloc[0] == WON
    assert settled["profit_units"].iloc[0] == pytest.approx(1.5)


def test_a_losing_bet_costs_exactly_one_unit() -> None:
    settled = _settle(_snapshot([{"selection": "away"}])).settled

    assert settled["outcome"].iloc[0] == LOST
    assert settled["profit_units"].iloc[0] == pytest.approx(-1.0)


def test_a_tied_game_pushes_the_moneyline_rather_than_losing_it() -> None:
    """NFL regular-season games do end level, and a two-way moneyline is a
    push when they do."""
    settled = _settle(_snapshot([{}]), games=_games(20, 20)).settled

    assert settled["outcome"].iloc[0] == PUSH
    assert settled["profit_units"].iloc[0] == 0.0


def test_a_spread_on_the_exact_margin_pushes() -> None:
    """Margin here is 4. A home line of -4 is exactly on it."""
    snapshot = _snapshot([{"market": "spread", "selection": "home", "line": -4.0}])

    assert _settle(snapshot).settled["outcome"].iloc[0] == PUSH


def test_a_half_point_the_other_side_of_the_margin_wins() -> None:
    snapshot = _snapshot([{"market": "spread", "selection": "home", "line": -3.5}])

    assert _settle(snapshot).settled["outcome"].iloc[0] == WON


def test_a_total_on_the_exact_sum_pushes() -> None:
    snapshot = _snapshot(
        [{"market": "total_points", "selection": "over", "line": 44.0}]
    )

    assert _settle(snapshot).settled["outcome"].iloc[0] == PUSH


def test_a_player_who_never_dressed_voids_and_returns_the_stake() -> None:
    """Void is not a loss. He was never in the game to bet on."""
    snapshot = _snapshot(
        [
            {
                "market": "reception_yards",
                "player": "Absent Player",
                "selection": "over",
                "line": 40.5,
            }
        ]
    )

    result = _settle(snapshot)

    assert result.settled["outcome"].iloc[0] == VOID
    assert result.settled["profit_units"].iloc[0] == 0.0
    assert result.voided == 1


def test_a_prop_settles_against_the_players_own_line() -> None:
    snapshot = _snapshot(
        [
            {
                "market": "reception_yards",
                "player": "A Player",
                "selection": "over",
                "line": 40.5,
            },
            {
                "market": "reception_yards",
                "player": "A Player",
                "selection": "under",
                "line": 40.5,
            },
        ]
    )

    outcomes = list(_settle(snapshot).settled["outcome"])

    assert outcomes == [WON, LOST]


def test_a_prop_on_the_exact_number_pushes() -> None:
    snapshot = _snapshot(
        [
            {
                "market": "receptions",
                "player": "A Player",
                "selection": "over",
                "line": 5.0,
            }
        ]
    )

    assert _settle(snapshot).settled["outcome"].iloc[0] == PUSH


# -- patience ----------------------------------------------------------------


def test_a_game_with_no_result_yet_is_left_alone_rather_than_guessed() -> None:
    """It will settle on a later run. Recording it now as anything would be
    inventing a result."""
    result = _settle(
        _snapshot([{}]), games=pd.DataFrame(columns=_games().columns),
        as_of=date(2026, 9, 10)
    )

    assert result.settled.empty
    assert result.unsettleable == 0


def test_a_game_with_no_result_after_the_window_is_recorded_unsettleable() -> None:
    """Counted, named, and never guessed. A fortnight without a box score
    means the row will never settle against the game it priced."""
    result = _settle(
        _snapshot([{}]),
        games=pd.DataFrame(columns=_games().columns),
        as_of=date(2026, 9, 9) + pd.Timedelta(days=PATIENCE_DAYS + 1).to_pytimedelta(),
    )

    assert result.unsettleable == 1
    assert result.settled["outcome"].iloc[0] == UNSETTLEABLE
    assert result.settled["profit_units"].iloc[0] == 0.0


# -- the ledger --------------------------------------------------------------


def test_a_day_already_in_the_ledger_is_never_appended_twice(tmp_path: Path) -> None:
    settled = _settle(_snapshot([{}])).settled
    path = tmp_path / "ledger.csv"

    assert append_ledger(settled, path) == 1
    assert append_ledger(settled, path) == 0
    assert len(pd.read_csv(path)) == 1


# -- intervals ---------------------------------------------------------------


def _ledger(rows: list[tuple[str, str, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "snapshot_date": day,
                "home_team": "SEA",
                "away_team": game,
                "outcome": WON if profit > 0 else LOST,
                "profit_units": profit,
            }
            for day, game, profit in rows
        ]
    )


def test_the_interval_is_clustered_by_game_not_by_bet() -> None:
    """Ten correlated bets in one game are close to one observation, not ten.

    A naive per-bet interval over correlated bets is narrower than the truth,
    and a narrow interval is exactly how "no demonstrated edge" quietly
    becomes a claim.
    """
    concentrated = _ledger([("2026-09-09", "NE", 1.0)] * 10 + [("2026-09-16", "KC", -1.0)] * 10)
    spread_out = _ledger(
        [(f"2026-09-{d:02d}", f"T{d}", 1.0 if d % 2 else -1.0) for d in range(1, 21)]
    )

    _, low_c, high_c, bets_c, games_c = interval_by_game(concentrated)
    _, low_s, high_s, bets_s, games_s = interval_by_game(spread_out)

    assert bets_c == bets_s == 20
    assert games_c == 2 and games_s == 20
    assert (high_c - low_c) > (high_s - low_s)


def test_an_empty_ledger_reports_nothing_rather_than_dividing_by_zero() -> None:
    roi, low, high, bets, games = interval_by_game(
        pd.DataFrame(columns=["snapshot_date", "home_team", "away_team", "outcome", "profit_units"])
    )

    assert (roi, bets, games) == (0.0, 0, 0)


def test_a_single_game_gives_an_unbounded_interval_rather_than_a_narrow_one() -> None:
    """One game cannot bound anything, and pretending otherwise is the whole
    failure this file exists to prevent."""
    _, low, high, _, games = interval_by_game(_ledger([("2026-09-09", "NE", 1.0)]))

    assert games == 1
    assert low == float("-inf") and high == float("inf")


def test_voids_and_unsettleables_are_excluded_from_the_return() -> None:
    """A void is not a zero-return bet; it is not a bet."""
    ledger = _ledger([("2026-09-09", "NE", 1.0)])
    with_void = pd.concat(
        [
            ledger,
            pd.DataFrame(
                [
                    {
                        "snapshot_date": "2026-09-09",
                        "home_team": "SEA",
                        "away_team": "NE",
                        "outcome": VOID,
                        "profit_units": 0.0,
                    }
                ]
            ),
        ],
        ignore_index=True,
    )

    assert interval_by_game(with_void)[3] == 1


def _write(tmp_path: Path, probabilities: dict) -> Path | None:
    prices = pd.DataFrame(
        [
            {
                "market": "moneyline",
                "selection": "home",
                "line": None,
                "american_odds": -150,
                "home_team": "Seattle Seahawks",
                "away_team": "New England Patriots",
                "commence_time": "2026-09-10T00:20:00Z",
                "player": "",
                "book": "dk",
            }
        ]
    )
    return write_snapshot(
        prices,
        probabilities,
        key_for=lambda row, *, market, selection, line: (market, selection),
        gates_in_force="test",
        snapshot_date="2026-09-09",
        archive_dir=tmp_path,
    )


def test_an_empty_snapshot_does_not_lock_the_day(tmp_path: Path) -> None:
    """The first *opinion* stands, not the first *file*.

    The first live workflow run wrote an empty snapshot on a day with no
    games. On a real game day the same thing happens whenever the early run
    fetched nothing — a failed provider call, a slate the books had not posted
    — and the day would be locked empty. Every real opinion for that week
    would then be silently unrecordable, and forward evidence cannot be
    created later.
    """
    first = _write(tmp_path, {})
    assert first is not None and pd.read_csv(first).empty

    second = _write(tmp_path, {("moneyline", "home"): 0.6})

    assert second is not None
    assert len(pd.read_csv(second)) == 1


def test_a_snapshot_with_opinions_still_stands(tmp_path: Path) -> None:
    """The rule that matters is unchanged: a repriced snapshot is not the
    card's opinion any more."""
    _write(tmp_path, {("moneyline", "home"): 0.6})

    assert _write(tmp_path, {("moneyline", "home"): 0.9}) is None


def test_an_unreadable_snapshot_does_not_lock_the_day(tmp_path: Path) -> None:
    """Refusing to overwrite a corrupt file locks the day on a corrupt file."""
    directory = tmp_path / "priced_snapshots"
    directory.mkdir(parents=True)
    (directory / "2026-09-09.csv").write_text("", encoding="utf-8")

    assert _write(tmp_path, {("moneyline", "home"): 0.6}) is not None


def test_settlement_joins_on_identity_not_spelling() -> None:
    """`A.J. Brown` priced and `AJ Brown` logged is one player.

    The raw-string join recorded the mismatch as "the player did not dress".
    A void returns the stake, so the error never showed up in the returns —
    it just deleted, silently, exactly the players whose names are written
    two ways.
    """
    from football_betting_lab.rosters import normalise_name

    assert normalise_name("A.J. Brown") == normalise_name("AJ Brown")
    assert normalise_name("Deebo Samuel Sr.") == normalise_name("Deebo Samuel")

    source = (
        Path(__file__).resolve().parents[1]
        / "src" / "football_betting_lab" / "forward_evidence.py"
    ).read_text(encoding="utf-8")
    assert "normalise_name(row.player_name)" in source
    assert "normalise_name(player)" in source
    assert "player.casefold()" not in source, (
        "a casefolded raw name is the defect this test exists to prevent"
    )


def test_a_snapshot_frozen_before_calibration_existed_still_settles(tmp_path):
    """The ledger on `card-feed` predates the calibrated columns.

    Every run restores that branch before it starts, so the first run after
    this change settles rows that have no `calibrated_probability` at all. They
    must settle to NaN rather than raise — an older opinion is still an
    opinion, and losing the ledger to a schema change is the one failure this
    organ cannot survive.
    """
    from football_betting_lab.forward_evidence import LEDGER_COLUMNS, append_ledger

    old = pd.DataFrame(
        [
            {
                "snapshot_date": "2026-09-09",
                "market": "rush_yards",
                "selection": "over",
                "outcome": "won",
                "profit_units": 0.91,
            }
        ]
    )
    ledger = tmp_path / "forward_evidence.csv"
    old.to_csv(ledger, index=False)

    new = pd.DataFrame(
        [{c: None for c in LEDGER_COLUMNS} | {
            "snapshot_date": "2026-09-14",
            "market": "rush_yards",
            "selection": "under",
            "outcome": "lost",
            "profit_units": -1.0,
            "calibrated_probability": 0.42,
            "calibrated_edge": 0.01,
        }]
    )

    assert append_ledger(new, ledger) == 1

    combined = pd.read_csv(ledger)
    assert len(combined) == 2
    assert "calibrated_probability" in combined.columns
    # The pre-calibration row is blank there, and blank is the honest value.
    first = combined[combined["snapshot_date"] == "2026-09-09"].iloc[0]
    assert pd.isna(first["calibrated_probability"])
