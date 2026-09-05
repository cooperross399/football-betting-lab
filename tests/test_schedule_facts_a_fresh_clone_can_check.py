"""Two facts about real NFL data, checked against the COMMITTED schedule.

Both were asserted by `tests/test_build_datasets.py` until #31, which rebuilt
that file to run against a synthetic nflverse feed in `tmp_path`. That was the
right call — those twenty tests needed gitignored processed tables, so they were
**skipped in every CI run, forever**, and a test that never runs guards nothing.
But two of the three facts deleted with them do not need the processed tables at
all. They are properties of the schedule cache, and the schedule cache is
committed precisely so this kind of arithmetic stays re-checkable.

So they are restored here, and they are now **stronger than they were**: they
run in a fresh clone with no venv data, which the originals never did.

The third deleted fact — that the weekly stats and play-by-play disagree on
about 0.21% of single-reception games — genuinely cannot be checked without the
gitignored play-by-play. It is not restored, and `CLAUDE.md` no longer claims a
test bounds it.
"""

from __future__ import annotations

import csv

import pytest

from football_betting_lab.config import RAW_DIR
from football_betting_lab.leagues import NFL
from football_betting_lab.season import schedule_path


#: Seasons whose results are final. 2026 is in progress and is deliberately not
#: asserted: a partially-published schedule is an absence, not a short season.
COMPLETED = (2023, 2024, 2025)

#: The one short season, and why. Buffalo-Cincinnati 2022 was abandoned after
#: Damar Hamlin's cardiac arrest and never replayed.
SHORT_SEASON, SHORT_SEASON_GAMES = 2022, 271


@pytest.fixture(scope="module")
def regular_season() -> dict[int, list[dict[str, str]]]:
    path = schedule_path(NFL, RAW_DIR)
    assert path.is_file(), (
        f"No committed schedule at {path}. It is committed on purpose — the "
        "credit arithmetic and these facts must stay re-checkable in a fresh "
        "clone."
    )
    seasons: dict[int, list[dict[str, str]]] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row.get("game_type") != "REG":
                continue
            try:
                season = int(row["season"])
            except (KeyError, TypeError, ValueError):
                continue
            seasons.setdefault(season, []).append(row)
    assert seasons, "the schedule parsed to nothing; the check is vacuous"
    return seasons


def test_2022_is_short_one_game_and_that_is_correct(regular_season) -> None:
    """A build that "corrected" this to 272 would be inventing a game."""
    played = len(regular_season.get(SHORT_SEASON, []))
    assert played == SHORT_SEASON_GAMES, (
        f"{SHORT_SEASON} has {played} regular-season games, not "
        f"{SHORT_SEASON_GAMES}. Buffalo-Cincinnati was abandoned and never "
        "replayed; if this now reads 272 the schedule has gained a game that "
        "was not played."
    )


def test_every_other_completed_season_is_the_full_272(regular_season) -> None:
    """The other half of the same fact: 271 is the exception, not the pattern."""
    for season in COMPLETED:
        played = len(regular_season.get(season, []))
        if not played:
            continue
        assert played == 272, f"{season} has {played} regular-season games, not 272."


def test_the_free_closing_line_series_is_complete_for_finished_seasons(
    regular_season,
) -> None:
    """One of this lab's three priced instruments, and it costs nothing.

    The schedule carries the closing spread, total and both moneylines back to
    1999. The closing-line backtest is built on it, so a season quietly losing
    its price columns would not fail — it would silently shrink the population
    the backtest ran on.
    """
    for season in (SHORT_SEASON,) + COMPLETED:
        rows = regular_season.get(season, [])
        if not rows:
            continue
        for column in ("spread_line", "total_line", "home_moneyline", "away_moneyline"):
            missing = sum(1 for row in rows if not str(row.get(column, "")).strip())
            assert missing == 0, (
                f"{season}: {missing} of {len(rows)} games have no {column}. "
                "The closing-line series is one of three priced instruments "
                "here; a hole in it shrinks a backtest without failing it."
            )


def test_the_fact_that_needs_play_by_play_is_not_pretended_to_be_checked() -> None:
    """The third deleted fact, recorded as unguarded rather than quietly lost.

    The 0.21% single-reception disagreement between the weekly stats and the
    play-by-play needs the gitignored play-by-play. No test bounds it, and
    CLAUDE.md must not say one does — that is the "document disagrees with the
    code" defect this repository has now paid for several times.
    """
    from football_betting_lab.config import PROJECT_ROOT

    text = (PROJECT_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    assert "Bounded by a test at 1%" not in text, (
        "CLAUDE.md still claims a test bounds the single-reception "
        "disagreement. That test was deleted with #31 and needs data no fresh "
        "clone has. Correct the prose or restore the guard."
    )
