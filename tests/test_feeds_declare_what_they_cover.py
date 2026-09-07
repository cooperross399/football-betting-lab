"""A feed's range and its place on the card path are declared, not discovered.

Two feeds added here reach back less far than the rest: `participation` is
charted from 2016 and the four `pfr_*` splits from 2018. Asking nflverse for a
season it never published returns HTTP 404, which arrives at the fetch CLI as a
`FetchError` — the same object a renamed release or a dead host produces. Left
alone, "2015 was never charted" and "the release moved and nothing works any
more" become one number in one summary line, and the second one stops being
visible. So the floor is declared on the feed and consulted before the fetch.

The other half is size. `participation` is 47 MB a season and the gameday card
runs five seasons, so fetching it on a path with a kickoff deadline would cost
roughly a quarter of a gigabyte for data nothing on that path reads. The card
path names what it needs instead — and these tests pin that it keeps doing so,
because the failure mode is silent: a feed added later just joins the download.
"""

from __future__ import annotations

import importlib.util
import subprocess
from datetime import date as _DATE
from pathlib import Path

import pytest

from football_betting_lab.data import nflverse
from football_betting_lab.leagues import NFL

#: Week 1 of 2026: the 2025 season is complete, 2026 is not.
_MID_SEASON = _DATE(2026, 9, 9)

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "fetch_football_data.py"
_spec = importlib.util.spec_from_file_location("fetch_football_data", _SCRIPT)
assert _spec is not None and _spec.loader is not None
fetch_cli = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fetch_cli)

WORKFLOW_DIR = _ROOT / ".github" / "workflows"

#: Pinned so an edit to a filename template is a failing test rather than a
#: 404 discovered on a Sunday. Each was fetched once by hand and returned 200;
#: this test pins the string, and does not and cannot prove the asset exists.
EXPECTED_URLS = {
    "participation": (
        "https://github.com/nflverse/nflverse-data/releases/download/"
        "pbp_participation/pbp_participation_2025.csv"
    ),
    "pfr_pass": (
        "https://github.com/nflverse/nflverse-data/releases/download/"
        "pfr_advstats/advstats_week_pass_2025.csv"
    ),
    "pfr_rec": (
        "https://github.com/nflverse/nflverse-data/releases/download/"
        "pfr_advstats/advstats_week_rec_2025.csv"
    ),
    "pfr_rush": (
        "https://github.com/nflverse/nflverse-data/releases/download/"
        "pfr_advstats/advstats_week_rush_2025.csv"
    ),
    "pfr_def": (
        "https://github.com/nflverse/nflverse-data/releases/download/"
        "pfr_advstats/advstats_week_def_2025.csv"
    ),
}


# --- what a feed covers -----------------------------------------------------

def test_a_feed_charted_from_2016_does_not_claim_2015() -> None:
    assert nflverse.FEEDS_BY_NAME["participation"].covers(2015) is False


def test_the_first_charted_season_is_itself_covered() -> None:
    """The boundary is `>=`. Off by one here silently drops a whole season."""
    assert nflverse.FEEDS_BY_NAME["participation"].covers(2016) is True
    assert nflverse.FEEDS_BY_NAME["pfr_def"].covers(2018) is True
    assert nflverse.FEEDS_BY_NAME["pfr_def"].covers(2017) is False


def test_a_feed_with_no_declared_floor_covers_every_season() -> None:
    schedules = nflverse.FEEDS_BY_NAME["schedules"]
    assert schedules.first_season is None
    assert schedules.covers(1999) is True


def test_a_seasonless_request_is_covered_whatever_the_floor() -> None:
    """`per_season=False` feeds are fetched with `season=None`, not a year."""
    assert nflverse.FEEDS_BY_NAME["participation"].covers(None) is True


# --- shape of the registry --------------------------------------------------

def test_every_feed_name_is_unique() -> None:
    """`FEEDS_BY_NAME` is a dict comprehension: a repeated name loses a feed
    with no error at all. Four `pfr_*` entries share one release and were
    written by copying, which is exactly how that happens."""
    names = [feed.name for feed in nflverse.FEEDS]
    assert len(names) == len(set(names))
    assert len(nflverse.FEEDS_BY_NAME) == len(nflverse.FEEDS)


def test_no_two_feeds_resolve_to_the_same_url() -> None:
    urls = [feed.url(2025) for feed in nflverse.FEEDS]
    assert len(urls) == len(set(urls))


def test_a_per_season_feed_substitutes_its_season() -> None:
    for feed in nflverse.FEEDS:
        if not feed.per_season:
            continue
        assert "{season}" not in feed.resolve(2025), feed.name
        assert "2025" in feed.resolve(2025), feed.name


@pytest.mark.parametrize("name", sorted(EXPECTED_URLS), ids=sorted(EXPECTED_URLS))
def test_the_new_feeds_build_the_url_that_was_fetched_by_hand(name: str) -> None:
    assert nflverse.FEEDS_BY_NAME[name].url(2025) == EXPECTED_URLS[name]


def test_every_feed_is_fetched_from_the_one_allowed_host() -> None:
    for feed in nflverse.FEEDS:
        assert feed.url(2025).startswith(f"https://{nflverse.ALLOWED_HOST}/"), feed.name


# --- the card path ----------------------------------------------------------

def test_the_card_path_is_exactly_the_feeds_it_read_before_this_change() -> None:
    """Adding a research feed must not change what the gameday card fetches."""
    assert [f.name for f in nflverse.FEEDS if f.needed_for_the_card] == [
        "schedules", "player_stats", "pbp", "rosters",
        "weekly_rosters", "depth_charts", "injuries", "snap_counts",
    ]


def test_none_of_the_research_feeds_ride_the_card_path() -> None:
    for name in ("participation", "pfr_pass", "pfr_rec", "pfr_rush", "pfr_def"):
        assert nflverse.FEEDS_BY_NAME[name].needed_for_the_card is False


def test_a_feed_that_forgets_to_declare_defaults_onto_the_card_path() -> None:
    """The default points at the loud failure. A feed the card needs but
    nobody flagged is merely fetched; the opposite default would leave the
    card quietly short of data, which is the failure nobody notices."""
    assert nflverse.Feed(
        name="x", release="r", filename="f_{season}.csv", purpose="p"
    ).needed_for_the_card is True


def test_no_workflow_fetches_the_whole_feed_set_implicitly() -> None:
    """An unconstrained `fetch_football_data.py` grows every time a feed is
    added, on a path with a kickoff deadline, without anyone editing it."""
    offenders: list[str] = []
    for path in sorted(WORKFLOW_DIR.glob("*.yml")):
        text = path.read_text(encoding="utf-8")
        # Line continuations first, so a wrapped invocation reads as one line.
        for line in text.replace("\\\n", " ").splitlines():
            if "fetch_football_data.py" not in line:
                continue
            if "--only" not in line and "--card-only" not in line:
                offenders.append(f"{path.name}: {line.strip()}")
    assert offenders == [], offenders


# --- the CLI observes the floor ---------------------------------------------

def _run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, argv: list[str]):
    """Run the fetch CLI with the network replaced by a recorder."""
    asked: list[tuple[str, int | None]] = []

    def fake_fetch(feed, league, *, raw_dir, season=None, **kwargs):
        asked.append((feed.name, season))
        target = nflverse.feed_path(feed, league, raw_dir, season)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("stub\n", encoding="utf-8")
        return target, "fetched"

    monkeypatch.setattr(fetch_cli.nflverse, "fetch_feed", fake_fetch)
    code = fetch_cli.main([*argv, "--raw-dir", str(tmp_path)])
    return code, asked


def test_the_fetcher_is_never_asked_for_a_season_the_feed_never_published(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    code, asked = _run(
        tmp_path, monkeypatch,
        ["--seasons", "2015", "2016", "--only", "participation"],
    )
    assert code == 0
    assert asked == [("participation", 2016)], asked


def test_a_season_outside_the_charted_range_is_not_counted_as_a_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The distinction this change exists to make: an absence by construction
    is reported apart from a fetch that broke, so a real breakage stays loud."""
    _run(tmp_path, monkeypatch, ["--seasons", "2015", "--only", "participation"])
    out = capsys.readouterr().out
    assert "0 feed-season(s) cached, 0 unavailable, 1 not published" in out
    assert "not available" not in out
    assert "not published before 2016" in out


def test_a_feed_that_lands_after_the_post_season_is_not_asked_for_a_live_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """`participation` and the `pfr_*` splits are published once, after the
    post-season — `pbp_participation_2025.csv` was created 2026-02-10 and never
    updated. Asking for a season still being played is a guaranteed 404, and a
    guaranteed 404 in the failure list every week is how a real breakage stops
    being read."""
    monkeypatch.setattr(
        fetch_cli, "date", type("D", (), {"today": staticmethod(lambda: _MID_SEASON)})
    )
    code, asked = _run(
        tmp_path, monkeypatch, ["--seasons", "2025", "2026", "--only", "participation"]
    )
    assert code == 0
    assert asked == [("participation", 2025)], asked
    out = capsys.readouterr().out
    assert "participation 2026: published only after the post-season — skipped" in out
    assert "0 unavailable" in out


def test_the_completed_season_before_it_is_still_fetched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The skip must not swallow the season that does exist."""
    monkeypatch.setattr(
        fetch_cli, "date", type("D", (), {"today": staticmethod(lambda: _MID_SEASON)})
    )
    _, asked = _run(tmp_path, monkeypatch, ["--seasons", "2025", "--only", "pfr_def"])
    assert asked == [("pfr_def", 2025)]


def test_every_new_feed_is_marked_as_landing_after_the_season() -> None:
    for name in ("participation", "pfr_pass", "pfr_rec", "pfr_rush", "pfr_def"):
        assert nflverse.FEEDS_BY_NAME[name].published_after_the_season is True
    for name in ("schedules", "player_stats", "pbp", "injuries", "snap_counts"):
        assert nflverse.FEEDS_BY_NAME[name].published_after_the_season is False


def test_card_only_asks_for_the_card_feeds_and_nothing_else(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, asked = _run(tmp_path, monkeypatch, ["--seasons", "2025", "--card-only"])
    assert {name for name, _ in asked} == {
        f.name for f in nflverse.FEEDS if f.needed_for_the_card
    }


def test_without_card_only_the_research_feeds_are_fetched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The flag is the thing that narrows it; the default still fetches all."""
    _, asked = _run(tmp_path, monkeypatch, ["--seasons", "2025"])
    assert "participation" in {name for name, _ in asked}


# --- the cache must not be committable ---------------------------------------

#: The one feed whose cache is deliberately in the repository: the credit
#: arithmetic has to stay re-checkable from a fresh clone.
COMMITTED_FEED_CACHES = {"schedules"}


def test_every_feed_cache_is_ignored_unless_it_is_deliberately_committed() -> None:
    """`.gitignore` enumerated seven feed directories by hand until
    2026-09-07, so a feed added later was not ignored at all. Several sessions
    share this checkout and `git add -A` from any of them has swept another's
    files into a commit twice — and `participation` is 47 MB a season. The
    enumeration is now a rule, and this observes it for every feed there is,
    including ones added after this was written.
    """
    wrong: list[str] = []
    for feed in nflverse.FEEDS:
        path = nflverse.feed_path(feed, NFL, Path("data/raw"), 2025)
        ignored = subprocess.run(
            ["git", "check-ignore", "-q", str(path)],
            cwd=_ROOT, capture_output=True,
        ).returncode == 0
        if ignored is (feed.name in COMMITTED_FEED_CACHES):
            wrong.append(f"{feed.name}: ignored={ignored}")
    assert wrong == [], wrong
