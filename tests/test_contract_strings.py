"""The strings Cooper's automation hard-codes, pinned so they cannot drift.

Renaming any of these silently breaks his scheduled routines, and the
breakage does not look like a rename — it looks like the lab going quiet.
That failure mode is why these are tests and not a table in a document.

The NHL lab learned this the hard way with its workflow name and its
"Selections changed" marker. The same table is pinned here before anything
depends on it, which is the cheap moment to do it.
"""

from __future__ import annotations

import re
from pathlib import Path

from football_betting_lab.config import PROJECT_ROOT
from football_betting_lab.leagues import NFL


CLAUDE_MD = PROJECT_ROOT / "CLAUDE.md"

WORKFLOW_NAME = "Football Gameday Refresh"
WORKFLOW_FILE = ".github/workflows/football-gameday-refresh.yml"
CARD_FEED_BRANCH = "card-feed"
OPERATING_HOME_ISSUE = "Football Betting Lab — Claude Operating Home"
CHANGED_SELECTIONS_MARKER = "Selections changed"
ODDS_API_SECRET = "FOOTBALL_ODDS_API_KEY"

CONTRACT_STRINGS = (
    WORKFLOW_NAME,
    WORKFLOW_FILE,
    CARD_FEED_BRANCH,
    OPERATING_HOME_ISSUE,
    CHANGED_SELECTIONS_MARKER,
    ODDS_API_SECRET,
)


def test_claude_md_lists_every_contract_string_verbatim() -> None:
    text = CLAUDE_MD.read_text(encoding="utf-8")
    missing = [item for item in CONTRACT_STRINGS if item not in text]

    assert missing == [], (
        f"CLAUDE.md no longer names these contract strings: {missing}. "
        "If one was renamed, Cooper's scheduled routines still hold the old "
        "value and will simply stop finding anything."
    )


def test_the_operating_home_title_uses_an_em_dash_not_a_hyphen() -> None:
    """It is matched literally by an issue search. A hyphen finds nothing."""
    assert "—" in OPERATING_HOME_ISSUE
    assert " - " not in OPERATING_HOME_ISSUE


def test_the_output_contract_names_are_league_prefixed() -> None:
    """Every output names its league, so NCAAF cannot overwrite an NFL record."""
    text = CLAUDE_MD.read_text(encoding="utf-8")
    for stem in ("what_we_can_claim", "forward_evidence"):
        expected = f"data/outputs/{NFL.output_name(stem, '.md')}"
        assert expected in text, f"CLAUDE.md does not pin {expected}"


def test_the_secret_name_is_not_the_nhl_labs_secret_name() -> None:
    """One account, two repositories. Two secret names, so a rotation in one
    repository can never silently be assumed to have happened in the other."""
    assert ODDS_API_SECRET.startswith("FOOTBALL_")


def test_claude_md_states_the_week_one_date_that_was_verified() -> None:
    """The brief guessed the Thursday after Labor Day; the schedule says
    Wednesday 2026-09-09. The verified date is pinned so a later session
    cannot quietly revert to the guess."""
    text = CLAUDE_MD.read_text(encoding="utf-8")

    assert "2026-09-09" in text
    assert re.search(r"272 games", text), "the season's size must stay on record"
