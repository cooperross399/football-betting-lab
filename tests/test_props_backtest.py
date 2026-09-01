"""One wager is one bet, and a result that excludes zero is still a candidate.

The two mistakes this file guards are the ones that would make a losing model
look like a winning one: counting the same wager once per book, and calling a
single season's non-zero interval a finding.
"""

from __future__ import annotations

import pandas as pd

from football_betting_lab.leagues import NFL
import pytest

from football_betting_lab.reports import props_backtest
from football_betting_lab.reports.props_backtest import (
    MINIMUM_BETS,
    MarketResult,
    best_price_per_selection,
    fragility,
)


def _prices(rows: list[dict]) -> pd.DataFrame:
    base = {
        "event_id": "e1",
        "market": "receptions",
        "player": "A Player",
        "selection": "over",
        "line": 4.5,
        "american_odds": -110,
        "book": "dk",
        "home_team": "Seattle Seahawks",
        "away_team": "New England Patriots",
    }
    return pd.DataFrame([{**base, **row} for row in rows])


# -- one wager, not nine -----------------------------------------------------


def test_nine_books_quoting_one_wager_collapse_to_one_bet() -> None:
    """Counting each book separately multiplies one wager by nine, inflates
    every sample size by nearly an order of magnitude, and narrows every
    interval by a factor of three while measuring nothing new."""
    prices = _prices(
        [{"book": f"book{i}", "american_odds": -120 + i} for i in range(9)]
    )

    collapsed = best_price_per_selection(prices)

    assert len(collapsed) == 1


def test_the_price_kept_is_the_best_one_a_card_could_reach() -> None:
    """+150 beats +120 beats -110 beats -200. If the model cannot beat the
    best of nine books it certainly cannot beat the one a card reaches."""
    prices = _prices(
        [
            {"book": "a", "american_odds": -200},
            {"book": "b", "american_odds": 150},
            {"book": "c", "american_odds": -110},
        ]
    )

    collapsed = best_price_per_selection(prices)

    assert collapsed["american_odds"].iloc[0] == 150


def test_different_lines_are_different_bets() -> None:
    """The ladder is not one wager. Over 4.5 and over 8.5 are different bets
    and collapsing them would throw away most of the board."""
    prices = _prices([{"line": 4.5}, {"line": 8.5}])

    assert len(best_price_per_selection(prices)) == 2


def test_the_two_sides_are_different_bets() -> None:
    prices = _prices([{"selection": "over"}, {"selection": "under"}])

    assert len(best_price_per_selection(prices)) == 2


def test_the_same_player_in_two_games_is_two_bets() -> None:
    prices = _prices([{"event_id": "e1"}, {"event_id": "e2"}])

    assert len(best_price_per_selection(prices)) == 2


def test_a_row_with_no_usable_price_is_dropped_rather_than_staked() -> None:
    prices = _prices([{"american_odds": None, "book": "a"}])

    assert best_price_per_selection(prices).empty


# -- a candidate is not a finding --------------------------------------------


def _bets(rows: list[dict]) -> pd.DataFrame:
    base = {
        "event_id": "e1",
        "week": 5,
        "market": "tackles_assists",
        "player": "A Player",
        "outcome": "won",
        "profit": 1.0,
    }
    return pd.DataFrame([{**base, **row} for row in rows])


def test_a_result_carried_by_one_afternoon_shows_up_as_a_top_game_share() -> None:
    bets = _bets(
        [{"event_id": "big", "profit": 50.0}]
        + [{"event_id": f"g{i}", "profit": -1.0} for i in range(20)]
    )

    check = fragility(bets, "tackles_assists")

    assert check.top_game_share > 1.0  # the rest are negative, so it carries it all
    assert check.without_best_game < 0


def test_a_result_that_is_really_one_player_shows_up_in_the_player_count() -> None:
    bets = _bets([{"player": "One Man", "event_id": f"g{i}"} for i in range(30)])

    assert fragility(bets, "tackles_assists").players == 1


def test_halves_that_disagree_are_reported_as_disagreeing() -> None:
    """A hot fortnight looks like an edge until the season is split."""
    bets = _bets(
        [{"week": 2, "event_id": f"a{i}", "profit": 2.0} for i in range(20)]
        + [{"week": 15, "event_id": f"b{i}", "profit": -1.0} for i in range(20)]
    )

    check = fragility(bets, "tackles_assists")

    assert check.first_half > 0 > check.second_half
    assert not check.halves_agree


def test_halves_that_agree_are_reported_as_agreeing() -> None:
    bets = _bets(
        [{"week": 2, "event_id": f"a{i}", "profit": 0.2} for i in range(20)]
        + [{"week": 15, "event_id": f"b{i}", "profit": 0.15} for i in range(20)]
    )

    assert fragility(bets, "tackles_assists").halves_agree


def test_voids_are_excluded_from_the_fragility_arithmetic() -> None:
    """A void is not a zero-return bet; it is not a bet."""
    bets = _bets(
        [{"event_id": f"g{i}", "profit": 1.0} for i in range(10)]
        + [{"event_id": "v", "outcome": "void", "profit": 0.0}]
    )

    assert fragility(bets, "tackles_assists").games == 10


def test_below_the_declared_minimum_the_verdict_is_not_a_number() -> None:
    """However good the number looks."""
    entry = MarketResult(market="x", bets=MINIMUM_BETS - 1, roi=0.40)

    verdict = entry.verdict(corrected_low=0.30, corrected_high=0.50)

    assert "not enough evidence" in verdict
    assert "0.40" not in verdict


def test_an_interval_including_zero_is_no_demonstrated_edge_in_those_words() -> None:
    entry = MarketResult(market="x", bets=1000, roi=0.05)

    assert entry.verdict(corrected_low=-0.02, corrected_high=0.12) == (
        "**no demonstrated edge**"
    )


# -- two snapshots of one event are not one wager ----------------------------


def _two_snapshots() -> pd.DataFrame:
    """The same wager at card time and at the close, with a better close."""
    return _prices(
        [
            {"snapshot": "20250907T170000Z", "american_odds": -110, "book": "dk"},
            {"snapshot": "20250907T175500Z", "american_odds": 150, "book": "dk"},
        ]
    )


def test_the_two_snapshots_of_one_event_are_labelled_card_and_close() -> None:
    from football_betting_lab.reports.props_backtest import (
        CARD_TIME,
        CLOSING,
        label_snapshots,
    )

    labelled = label_snapshots(_two_snapshots())

    assert list(labelled["phase"]) == [CARD_TIME, CLOSING]


def test_an_event_with_one_snapshot_is_all_card_time() -> None:
    """A single purchase was a card-time purchase, and calling half of it the
    close would invent a closing price."""
    from football_betting_lab.reports.props_backtest import CARD_TIME, label_snapshots

    one = _prices([{"snapshot": "20250907T170000Z"}])

    assert list(label_snapshots(one)["phase"]) == [CARD_TIME]


def test_the_best_price_is_never_taken_across_two_snapshots() -> None:
    """The better of a card-time price and a closing price is not a price
    anyone could have taken. It is the best of two moments, and collapsing
    them would quietly inflate every measured edge."""
    from football_betting_lab.reports.props_backtest import label_snapshots

    collapsed = best_price_per_selection(label_snapshots(_two_snapshots()))

    assert len(collapsed) == 2
    assert set(collapsed["american_odds"]) == {-110, 150}


def test_nine_books_still_collapse_within_one_snapshot() -> None:
    """The snapshot joins the key; it does not replace it."""
    from football_betting_lab.reports.props_backtest import label_snapshots

    prices = _prices(
        [
            {"snapshot": "20250907T170000Z", "book": f"b{i}", "american_odds": -120 + i}
            for i in range(9)
        ]
    )

    assert len(best_price_per_selection(label_snapshots(prices))) == 1


def test_three_snapshots_label_earliest_card_latest_close_and_the_rest_mid() -> None:
    """The first version labelled every non-earliest snapshot `close`, which
    was right for two snapshots and silently wrong for three: a T-60 and a T-5
    price would have landed in the same bucket and the best-price collapse
    would have chosen between two different moments."""
    from football_betting_lab.reports.props_backtest import (
        CARD_TIME,
        CLOSING,
        MID,
        label_snapshots,
    )

    prices = _prices(
        [
            {"snapshot": "20250907T120000Z"},
            {"snapshot": "20250907T170000Z"},
            {"snapshot": "20250907T175500Z"},
        ]
    )

    assert list(label_snapshots(prices)["phase"]) == [CARD_TIME, MID, CLOSING]


def test_a_single_snapshot_is_card_not_close() -> None:
    """Earliest and latest are the same row, and one purchase was a card-time
    purchase — calling it the close would invent a closing price."""
    from football_betting_lab.reports.props_backtest import CARD_TIME, label_snapshots

    one = _prices([{"snapshot": "20250907T170000Z"}])

    assert list(label_snapshots(one)["phase"]) == [CARD_TIME]


# -- the cross-season settlement defect --------------------------------------


def test_an_event_is_never_settled_against_another_seasons_game() -> None:
    """The defect that invalidated every prop result in this repository.

    `_game_weeks` looked a club pair up in the target season's logs and
    ignored the event's own kickoff, while `run` was handed the whole
    three-season price frame for every season. So a 2023 Detroit-at-Chicago
    event settled against the 2024 and 2025 meetings too: **406 of 794 events
    settled against more than one season, and 100,466 of 148,587 bets were on
    such events.**

    It did not look like a bug. It looked like three seasons of replication.
    """
    from football_betting_lab.reports.props_backtest import _game_weeks

    logs = pd.DataFrame(
        [
            {"season": 2024, "week": 16, "game_id": "2024_16_DET_CHI",
             "player_name": "x", "team": "CHI"},
        ]
    )
    prices = pd.DataFrame(
        [
            {
                "event_id": "e2023",
                "home_team": "Chicago Bears",
                "away_team": "Detroit Lions",
                # Played in 2023. It must not settle against the 2024 meeting.
                "commence_time": "2023-12-10T18:03:00Z",
            }
        ]
    )

    assert _game_weeks(logs, prices, NFL, 2024) == {}


def test_an_event_played_in_the_target_season_still_maps() -> None:
    """The fix must not throw away the rows that were always correct."""
    from football_betting_lab.reports.props_backtest import _game_weeks

    logs = pd.DataFrame(
        [{"season": 2024, "week": 16, "game_id": "2024_16_DET_CHI",
          "player_name": "x", "team": "CHI"}]
    )
    prices = pd.DataFrame(
        [{"event_id": "e2024", "home_team": "Chicago Bears",
          "away_team": "Detroit Lions",
          "commence_time": "2024-12-22T18:00:00Z"}]
    )

    assert _game_weeks(logs, prices, NFL, 2024) == {"e2024": 16}


@pytest.mark.parametrize(
    ("commence_time", "expected"),
    [
        ("2023-12-10T18:03:00Z", 2023),
        # Week 18 is played in January and belongs to the previous season.
        ("2024-01-07T18:00:00Z", 2023),
        ("2025-09-05T00:20:00Z", 2025),
        ("2026-01-04T18:00:00Z", 2025),
    ],
)
def test_the_season_of_an_event_comes_from_its_own_kickoff(
    commence_time: str, expected: int
) -> None:
    from football_betting_lab.reports.props_backtest import _event_season

    assert _event_season(commence_time, NFL) == expected


def test_an_unparseable_kickoff_maps_to_no_season_rather_than_a_guess() -> None:
    from football_betting_lab.reports.props_backtest import _event_season

    for value in ("", "not a time", None):
        assert _event_season(value, NFL) is None


def test_a_calendar_year_filter_would_lose_week_eighteen() -> None:
    """The same bug family, in the three places that wrote the filter by hand.

    Week 18 is played in January, so `date[:4] == season` drops the target
    season's last week and imports the previous season's.
    """
    from football_betting_lab.reports.props_backtest import events_in_season

    prices = pd.DataFrame(
        [
            {"event_id": "sept", "commence_time": "2025-09-07T17:00:00Z"},
            {"event_id": "jan-same-season", "commence_time": "2026-01-04T18:00:00Z"},
            {"event_id": "jan-previous-season", "commence_time": "2025-01-05T18:00:00Z"},
        ]
    )

    kept = set(events_in_season(prices, NFL, 2025)["event_id"])

    assert kept == {"sept", "jan-same-season"}
    # ...and a naive year filter would have got both of those wrong.
    naive = {
        row["event_id"]
        for _, row in prices.iterrows()
        if str(row["commence_time"])[:4] == "2025"
    }
    assert naive == {"sept", "jan-previous-season"}


def test_events_in_season_refuses_a_frame_without_a_kickoff():
    """A reshaped price frame cannot be silently assumed to be in season.

    It used to return the frame unchanged, so a caller that had pivoted the
    kickoff column away asked "which of these were played in 2023?" and was
    handed all three seasons with nothing to indicate the question had gone
    unanswered.
    """
    frame = pd.DataFrame({"event_id": ["a"], "home_team": ["DET"]})
    with pytest.raises(ValueError, match="commence_time"):
        props_backtest.events_in_season(frame, NFL, 2023)


def test_game_weeks_refuses_a_frame_without_a_kickoff():
    """The mirror failure, which was just as quiet.

    With no kickoff to read, every event failed its season check and the
    function returned an empty mapping — indistinguishable downstream from
    "no priced event was played that season".
    """
    frame = pd.DataFrame({"event_id": ["a"], "home_team": ["DET"], "away_team": ["CHI"]})
    logs = pd.DataFrame({"season": [2023], "week": [1], "game_id": ["2023_01_CHI_DET"]})
    with pytest.raises(ValueError, match="commence_time"):
        props_backtest._game_weeks(logs, frame, NFL, 2023)


def test_load_scored_bets_refuses_a_file_that_cannot_say_what_it_covers(tmp_path):
    """Four reports read this file and all four phrase findings as if it were
    the whole bought population. A file with no season column cannot support
    that sentence, so it is refused rather than assumed."""
    path = tmp_path / "bets.csv"
    pd.DataFrame({"market": ["rush_yards"], "profit": [1.0]}).to_csv(path, index=False)
    with pytest.raises(ValueError, match="season"):
        props_backtest.load_scored_bets(path)


def test_coverage_line_names_every_season_behind_the_numbers():
    bets = pd.DataFrame(
        {
            "season": [2023, 2024, 2024],
            "event_id": ["a", "b", "b"],
            "profit": [1.0, -1.0, 0.5],
        }
    )
    line = props_backtest.coverage_line(bets)
    assert "2023, 2024" in line
    assert "3 scored bets" in line
    assert "2 games" in line


def test_settlement_matches_the_identity_the_model_priced_with():
    """The provider writes a generational suffix the roster omits.

    Matching on the name string voided 3,281 bets across 61 players who played
    every week — Travis Etienne Jr. 436 of 436, Brian Robinson Jr. 415 of 415,
    AJ Brown 200 of 200. A void returns the stake, so the error never showed in
    the returns; it silently deleted exactly the players whose names are
    written two ways, and inflated the void rate from 2.6% to 6.2%.

    The pricing side already resolved identity. Only settlement did not.
    """
    logs = pd.DataFrame([{
        "game_id": "2024_01_JAX_HOU", "player_id": "00-0036389",
        "player_name": "Travis Etienne", "rush_yards": 88.0,
    }])

    class _Row:
        market, player, selection, line = "rush_yards", "Travis Etienne Jr.", "over", 60.5

    assert props_backtest._settle(
        logs, "2024_01_JAX_HOU", _Row(), "00-0036389"
    ) == ("won", 88.0)


def test_settlement_falls_back_to_a_normalised_name_never_a_raw_one():
    """Without an id it must still collapse the suffix, exactly as
    `forward_evidence` does. A raw casefold is what caused the defect."""
    logs = pd.DataFrame([{
        "game_id": "2024_01_JAX_HOU", "player_id": "",
        "player_name": "Deebo Samuel", "reception_yards": 70.0,
    }])

    class _Row:
        market, player, selection, line = "reception_yards", "Deebo Samuel Sr.", "over", 49.5

    assert props_backtest._settle(logs, "2024_01_JAX_HOU", _Row())[0] == "won"


def test_two_spellings_of_one_player_collapse_to_one_wager():
    """Fixing settlement alone would convert 625 silent voids into 625
    duplicate stakes — one afternoon's opinion staked twice, each keeping its
    own best price, inflating the bet count and narrowing every interval."""
    frame = pd.DataFrame([
        {"event_id": "e1", "market": "rush_yards", "player": "Travis Etienne Jr.",
         "selection": "over", "line": 60.5, "american_odds": -110},
        {"event_id": "e1", "market": "rush_yards", "player": "Travis Etienne",
         "selection": "over", "line": 60.5, "american_odds": -105},
    ])

    assert len(props_backtest.best_price_per_selection(frame)) == 1
