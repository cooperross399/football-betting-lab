"""What the card says when it has nothing to recommend — which is always, now.

The failure this file guards is a card that goes quiet. A slate with no
selections, a day with no games, and a run that broke are three different
things, and a card that renders them the same way is lying by omission.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from football_betting_lab.leagues import NFL
from football_betting_lab.reports.card_pricing import PricingDiagnostics
from football_betting_lab.reports.gameday_card import (
    ACCUMULATING_NOTE,
    build_card,
    render,
)
from football_betting_lab.staging_provider_policy import StagingProviderPolicy


NOW = datetime(2026, 9, 9, 15, 0, tzinfo=timezone.utc)


def _prices(commence: str = "2026-09-10T00:20:00Z") -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "market": market,
                "home_team": "Seattle Seahawks",
                "away_team": "New England Patriots",
                "commence_time": commence,
            }
            for market in ("moneyline", "spread", "pass_yards")
        ]
    )


def _card(prices=None, diagnostics=None, preseason=None, now=NOW):
    return build_card(
        _prices() if prices is None else prices,
        NFL,
        policy=StagingProviderPolicy.load(),
        diagnostics=diagnostics or PricingDiagnostics(),
        now=now,
        slate_date="2026-09-09",
        preseason_excluded=preseason or [],
    )


def test_the_card_says_it_is_accumulating_evidence_not_recommending() -> None:
    """Not modesty. The accurate description of a lab whose evidence base is
    empty, and it must never soften into something that reads like a tip."""
    text = render(_card())

    assert ACCUMULATING_NOTE in text
    assert "accumulating evidence, not making recommendations" in text


def test_no_market_is_allowlisted_so_there_are_no_selections() -> None:
    card = _card()

    assert card.selections == []
    text = render(card)
    assert "**None.**" in text
    assert "not a pass, not an avoid" in text.lower()


def test_an_excluded_market_is_never_called_a_pass_or_a_no_value_call() -> None:
    text = render(_card()).lower()

    assert "no-value call" in text  # ...only ever as the thing it is not.
    for phrase in ("no value found", "avoid this market", "we pass on"):
        assert phrase not in text


def test_every_priced_market_is_listed_with_a_reason() -> None:
    card = _card()

    assert set(card.market_states) == {"moneyline", "spread", "pass_yards"}
    for reason in card.market_states.values():
        assert reason and reason != "eligible"


def test_a_day_with_no_games_is_an_absence_and_says_so() -> None:
    """Different from a run that failed, and different from a slate with no
    qualifying bet."""
    card = _card(prices=pd.DataFrame(columns=["market", "home_team", "away_team"]))

    text = render(card)

    assert card.decision == "no-slate"
    assert "absence, not a fault" in text


def test_a_slate_with_games_and_no_selections_is_reported_as_that() -> None:
    card = _card()

    assert card.decision == "no-selections"
    assert card.games


def test_preseason_exclusions_are_counted_and_named() -> None:
    """Books post exhibition lines and the provider does not flag them. An
    opinion frozen on one rots in the ledger as unsettleable noise."""
    card = _card(
        prices=pd.DataFrame(columns=["market", "home_team", "away_team"]),
        preseason=["2026-08-22 KC @ SEA (not in the regular-season schedule)"],
    )

    text = render(card)

    assert "excluded as preseason" in text
    assert "2026-08-22 KC @ SEA" in text


def test_a_started_game_is_quarantined_with_its_reason() -> None:
    card = _card(prices=_prices(commence="2026-09-09T12:00:00Z"))

    text = render(card)

    assert card.quarantined
    assert "Already started — no longer plays" in text
    assert "no longer available at the price shown" in text


def test_the_accounting_identity_is_printed_every_run() -> None:
    diagnostics = PricingDiagnostics(priced=10, no_opinion=3, opinions=7)

    text = render(_card(diagnostics=diagnostics))

    assert "priced 10 = no_opinion 3" in text
    assert "reconciles" in text


def test_an_identity_that_does_not_reconcile_shouts() -> None:
    """A row fell out for a reason nobody counted. Silent attrition is how a
    card ends up recommending from a sixth of a slate."""
    diagnostics = PricingDiagnostics(priced=10, no_opinion=1, opinions=2)

    text = render(_card(diagnostics=diagnostics))

    assert "DOES NOT RECONCILE" in text
    assert "does not reconcile" in text.lower()


def test_the_card_tells_the_reader_why_props_cannot_be_selected() -> None:
    text = render(_card())

    assert "cannot produce a selection" in text
    assert "no available feed publishes them" in text


def test_the_card_states_the_forward_ledger_position() -> None:
    card = _card()
    card.frozen_rows = 1903
    card.ledger_rows = 0

    text = render(card)

    assert "1,903 opinion(s) frozen" in text
    assert "cannot be back-dated" in text


def test_a_live_run_pricing_another_date_must_declare_itself_a_rehearsal() -> None:
    """The sharp edge that makes rehearsing dangerous.

    Pricing Week 1 twelve days early would freeze a snapshot dated for the
    real slate. On the day itself `write_snapshot` finds one already standing
    and declines to overwrite it, so the first opinion of the day would be a
    rehearsal taken before the teams were known — and forward evidence cannot
    be re-made.
    """
    import subprocess
    import sys

    from football_betting_lab.config import PROJECT_ROOT

    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "run_gameday_card.py"),
            "--live",
            "--slate-date",
            "2026-09-09",
            "--credit-cap",
            "100",
        ],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(PROJECT_ROOT / "src"), "PATH": "/usr/bin:/bin"},
        cwd=PROJECT_ROOT,
    )

    assert result.returncode == 2
    assert "needs --rehearsal" in result.stderr


def test_an_empty_or_unreadable_table_is_treated_as_empty_not_fatal(
    tmp_path,
) -> None:
    """A zero-byte file is a real state, not a corruption.

    `git show refs/...:file > file` creates the file even when the show
    fails, and pandas raises on a zero-byte CSV. The first rehearsal died
    exactly there, on the branch state the first real run would have had — a
    card feed with a card on it and no ledger yet.
    """
    import sys

    sys.path.insert(0, str((tmp_path / "..").resolve()))
    from importlib import import_module, util

    from football_betting_lab.config import PROJECT_ROOT

    spec = util.spec_from_file_location(
        "run_gameday_card", PROJECT_ROOT / "scripts" / "run_gameday_card.py"
    )
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)

    empty = tmp_path / "empty.csv"
    empty.write_text("", encoding="utf-8")
    missing = tmp_path / "missing.csv"
    junk = tmp_path / "junk.csv"
    junk.write_bytes(b"\xff\xfe\x00not,a,csv\x00")

    for path in (empty, missing, junk):
        assert module._read(path).empty, path.name


# -- the gate the runner now calls -------------------------------------------
#
# `gates.assess_availability` and `gates.report_coverage` had NO caller in
# `src/` or `scripts/` — referenced only by their own tests. These exercise
# the runner's real functions, because a key or a lookup built where nothing
# can execute it is a key that drifts, and that is exactly what happened to
# the player-id map these tests also cover.


def _runner():
    """The runner module, loaded the way this file already loads it."""
    from importlib import util

    from football_betting_lab.config import PROJECT_ROOT

    spec = util.spec_from_file_location(
        "run_gameday_card_under_test",
        PROJECT_ROOT / "scripts" / "run_gameday_card.py",
    )
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _prop_prices(player: str) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "market": "rush_yards",
                "player": player,
                "home_team": "Seattle Seahawks",
                "away_team": "New England Patriots",
                "commence_time": "2026-09-10T00:20:00Z",
            }
        ]
    )


def _one_man_roster():
    from football_betting_lab.rosters import RosterEntry, Rosters

    return Rosters(
        [
            RosterEntry(
                player_id="00-0000001", name="A Back", team="SEA", position="RB"
            )
        ],
        NFL,
    )


def test_the_runner_keys_a_player_the_way_every_reader_reads_him_back() -> None:
    """Join-vocabulary member six, caught before it cost anything.

    The runner stored `str(row.player).casefold()`; `card_pricing.price_slate`
    and `selection_key` both read `clean_text(row.player).casefold()`. The two
    part company on a provider spelling carrying whitespace, so a player who
    resolved perfectly well was stored under a key nothing ever asked for and
    counted `no_opinion` — "player not on a current roster", about a man on
    the roster. The availability map is looked up on the same key and would
    have inherited the split.
    """
    from football_betting_lab.providers.team_names import name_to_abbreviation
    from football_betting_lab.selection import player_key

    module = _runner()
    prices = _prop_prices("  A Back  ")

    player_ids, slate_players = module.resolved_players(
        prices, _one_man_roster(), league=NFL, lookup=name_to_abbreviation(NFL)
    )

    # The exact expression every reader uses, on the exact value it uses.
    assert player_ids.get(player_key("A Back")) == "00-0000001"
    assert slate_players.get(player_key("A Back")) == ("00-0000001", "SEA")
    # And the spelling that used to be stored is gone.
    assert "  a back  " not in player_ids
    assert "  a back  " not in slate_players


def test_the_runner_carries_the_club_from_the_roster_not_the_fixture() -> None:
    """A price row says which two clubs are playing, never which one the
    player is on, and the availability gate needs the club to find his
    team's injury report."""
    from football_betting_lab.providers.team_names import name_to_abbreviation

    module = _runner()

    _ids, slate_players = module.resolved_players(
        _prop_prices("A Back"),
        _one_man_roster(),
        league=NFL,
        lookup=name_to_abbreviation(NFL),
    )

    assert [club for _id, club in slate_players.values()] == ["SEA"]


def _games() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"season": 2026, "week": 1, "game_date": "2026-09-09"},
            {"season": 2026, "week": 2, "game_date": "2026-09-17"},
            {"season": 2025, "week": 9, "game_date": "2026-09-09"},
        ]
    )


def test_the_slate_week_comes_off_the_schedule_and_not_a_calendar_rule() -> None:
    """Week 1 2026 opens on a Wednesday because Thursday's game is in
    Australia. Any weekday rule gets that wrong."""
    module = _runner()

    assert module.slate_week(_games(), season=2026, slate_date="2026-09-09") == 1
    assert module.slate_week(_games(), season=2026, slate_date="2026-09-17") == 2


def test_a_slate_date_the_schedule_does_not_hold_has_no_week() -> None:
    """None rather than a guess. `gates.assess_slate` turns it into `UNKNOWN`
    for every player, which refuses; a guessed week would look up the wrong
    report and answer confidently."""
    module = _runner()

    for games, date in (
        (_games(), "2026-12-25"),
        (pd.DataFrame(), "2026-09-09"),
        (_games().drop(columns=["week"]), "2026-09-09"),
        (_games(), ""),
    ):
        assert module.slate_week(games, season=2026, slate_date=date) is None


def test_the_slate_week_is_this_season_s_week() -> None:
    """The cross-season defect in miniature. The fixture holds a 2025 row on
    the same calendar date; reading it would ask the 2026 injury feed for
    week 9."""
    module = _runner()

    assert module.slate_week(_games(), season=2026, slate_date="2026-09-09") == 1


def _injury_file(tmp_path, rows: list[dict]) -> None:
    directory = tmp_path / NFL.data_dir_segment / "injuries"
    directory.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        rows,
        columns=["season", "week", "team", "gsis_id", "full_name", "report_status"],
    ).to_csv(directory / "injuries_2026.csv", index=False)


def test_the_runner_reads_the_injury_feed_and_grades_each_player(tmp_path) -> None:
    """The end of "a gate with no caller". Three players, three states, one
    of which the verdict opens and two of which it does not."""
    from football_betting_lab.gates import EXCLUDED, NO_REPORT, UNDESIGNATED

    module = _runner()
    _injury_file(
        tmp_path,
        [
            {
                "season": 2026, "week": 1, "team": "SEA",
                "gsis_id": "00-0000001", "full_name": "A Back",
                "report_status": "Out",
            },
            {
                "season": 2026, "week": 1, "team": "SEA",
                "gsis_id": "00-0000777", "full_name": "Someone Else",
                "report_status": "Questionable",
            },
        ],
    )

    verdicts = module.slate_availability(
        {
            "a back": ("00-0000001", "SEA"),
            "a receiver": ("00-0000002", "SEA"),
            "a kicker": ("00-0000003", "NE"),
        },
        league=NFL,
        season=2026,
        slate_date="2026-09-09",
        games=_games(),
        raw_dir=tmp_path,
        undesignated_allowed=True,
    )

    assert verdicts["a back"].state == EXCLUDED
    assert verdicts["a receiver"].state == UNDESIGNATED
    assert verdicts["a kicker"].state == NO_REPORT
    assert [key for key, v in verdicts.items() if v.may_select] == ["a receiver"]


def test_a_missing_injury_file_is_not_a_clean_bill_of_health(tmp_path) -> None:
    """`run_feed_freshness` names this consequence: without the feed the gate
    used to read every player as undesignated — the one state a verdict can
    open. An absent file now lands every player in `NO_REPORT`, which never
    selects."""
    from football_betting_lab.gates import NO_REPORT

    module = _runner()

    verdicts = module.slate_availability(
        {"a back": ("00-0000001", "SEA")},
        league=NFL,
        season=2026,
        slate_date="2026-09-09",
        games=_games(),
        raw_dir=tmp_path,
        undesignated_allowed=True,
    )

    assert verdicts["a back"].state == NO_REPORT
    assert not verdicts["a back"].may_select


def test_the_runner_hands_the_card_a_map_rather_than_only_a_flag() -> None:
    """A gate is wired when its caller passes its answer, not when the module
    imports it. `build_card` gained `availability=` for this; a runner that
    computed the map and dropped it would leave `select()` deciding six
    states on one boolean again."""
    from football_betting_lab.config import PROJECT_ROOT

    source = (PROJECT_ROOT / "scripts" / "run_gameday_card.py").read_text(
        encoding="utf-8"
    )

    assert "availability=slate_availability(" in source
    assert "gates.assess_slate(" in source


def test_the_pricer_reads_the_key_the_runner_stored(tmp_path) -> None:
    """The consumer half of the same pin, and it was the untested half.

    `card_pricing.price_slate` looked the map up with
    `clean_text(player).casefold()` while the runner stored
    `str(row.player).casefold()`. Pinning only the producer leaves the join
    open from the other side — a lookup respelled here misses a resolved
    player and counts him "player not on a current roster", which reads as a
    roster problem rather than a key problem.

    The two `no_opinion` reasons are the discriminator: a player the lookup
    FOUND gets "no fitted rate", because this book is fitted on nothing.
    """
    from football_betting_lab.reports.card_pricing import PlayerBook, price_slate
    from football_betting_lab.selection import player_key

    prices = _prop_prices("  A Back  ")
    prices["selection"] = "over"
    prices["line"] = 40.5
    player_ids = {player_key("A Back"): "00-0000001"}

    _probabilities, diagnostics = price_slate(
        prices,
        NFL,
        distributions={},
        book=PlayerBook(pd.DataFrame(), {}, before="202601", draws=1),
        player_ids=player_ids,
    )

    reasons = dict(diagnostics.reasons)
    assert "player not on a current roster" not in reasons, (
        "the pricer missed a player the runner resolved — the two sides of "
        "the player key have come apart again"
    )
    assert "no fitted rate for `rush_yards`" in reasons
