"""A partial fetch must not erase the manifest's memory of the rest of the cache.

`write_manifest` set `"feeds"` to the entries of the run that called it, and no
run is the whole cache. `--only schedules` fetches one feed and leaves thirty
other cached files exactly where they were; `--card-only` fetches eight and
leaves the five research feeds — 47 MB a season of `participation` among them —
untouched on disk. Writing that run's entries wholesale dropped every feed it
had not asked for, so the file whose stated job is to answer "how old is this?"
answered *nothing at all* for most of the cache. That is the same invisible
staleness the manifest exists to prevent, arriving through the manifest.

Measured on this checkout before the fix, with no network involved: a full run
of `player_stats` and `pbp` for 2022, then `--only player_stats`, left a
manifest listing `player_stats 2022` alone — `pbp 2022` erased with the cached
file still on disk and still readable.

It travels further than a local inconvenience because
`data/raw/nfl/nflverse_manifest.json` is TRACKED, several sessions share this
one checkout, and `git add -A` from any of them has swept another session's
files into a commit twice. The truncated manifest is therefore committable by a
session that never ran a fetch at all.

The rule these tests hold: the manifest may not forget a feed that is cached,
and it may not remember one that is not.
"""

from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from football_betting_lab.data import nflverse
from football_betting_lab.leagues import NFL

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "fetch_football_data.py"
_spec = importlib.util.spec_from_file_location("fetch_football_data", _SCRIPT)
assert _spec is not None and _spec.loader is not None
fetch_cli = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fetch_cli)

AUGUST = datetime(2026, 8, 28, 17, 10, tzinfo=timezone.utc)
SEPTEMBER = datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc)


def _feeds(raw_dir: Path) -> dict[str, dict]:
    path = raw_dir / NFL.data_dir_segment / nflverse.MANIFEST_FILENAME
    return json.loads(path.read_text(encoding="utf-8"))["feeds"]


def _manifest(raw_dir: Path) -> dict:
    path = raw_dir / NFL.data_dir_segment / nflverse.MANIFEST_FILENAME
    return json.loads(path.read_text(encoding="utf-8"))


def _run(
    raw_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
    argv: list[str],
    *,
    at: datetime = SEPTEMBER,
) -> int:
    """Run the fetch CLI at a fixed instant with the network replaced.

    The stub writes the file the real fetch would have written, so the cache
    on disk and the manifest describe the same world — which is the thing
    these tests are about.
    """

    def fake_fetch(feed, league, *, raw_dir, season=None, **kwargs):
        target = nflverse.feed_path(feed, league, raw_dir, season)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("stub\n", encoding="utf-8")
        return target, "fetched"

    monkeypatch.setattr(fetch_cli.nflverse, "fetch_feed", fake_fetch)
    monkeypatch.setattr(
        fetch_cli, "datetime", type("D", (), {"now": staticmethod(lambda tz: at)})
    )
    return fetch_cli.main([*argv, "--raw-dir", str(raw_dir)])


# --- the reproduction -------------------------------------------------------

def test_a_partial_run_keeps_the_feeds_it_did_not_ask_for(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The bug, exactly as it was measured. `pbp 2022` is cached, is not asked
    for, and must still be recorded as cached afterwards."""
    _run(tmp_path, monkeypatch, ["--seasons", "2022", "--only", "player_stats", "pbp"])
    assert set(_feeds(tmp_path)) == {"player_stats 2022", "pbp 2022"}

    _run(tmp_path, monkeypatch, ["--seasons", "2022", "--only", "player_stats"])

    assert set(_feeds(tmp_path)) == {"player_stats 2022", "pbp 2022"}


def test_the_schedules_only_run_ci_makes_weekly_keeps_the_rest_of_the_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`.github/workflows/weekly-ledger-check.yml` runs exactly this. On a
    fresh runner it costs nothing; run locally against a real cache it was the
    single command most likely to truncate the tracked file."""
    _run(tmp_path, monkeypatch, ["--seasons", "2025"])
    everything = set(_feeds(tmp_path))

    _run(tmp_path, monkeypatch, ["--seasons", "2025", "--only", "schedules"])

    assert set(_feeds(tmp_path)) == everything


def test_the_card_only_path_does_not_erase_the_research_feeds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The card path narrows deliberately — `participation` is 47 MB a season
    and nothing on that path reads it. Narrowing what is FETCHED must not
    narrow what is REMEMBERED, or every gameday run drops the research half of
    the cache out of the record."""
    _run(tmp_path, monkeypatch, ["--seasons", "2025"])
    assert "participation 2025" in _feeds(tmp_path)

    _run(tmp_path, monkeypatch, ["--seasons", "2025", "--card-only"])

    assert "participation 2025" in _feeds(tmp_path)
    assert "pfr_def 2025" in _feeds(tmp_path)


def test_a_run_for_a_new_season_does_not_erase_the_old_ones(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Seasons are the other axis a run narrows on, and the merge is per
    feed-season rather than per feed for exactly this reason."""
    _run(tmp_path, monkeypatch, ["--seasons", "2024", "--only", "pbp"])
    _run(tmp_path, monkeypatch, ["--seasons", "2025", "--only", "pbp"])

    assert set(_feeds(tmp_path)) == {"pbp 2024", "pbp 2025"}


# --- staleness stays per feed ----------------------------------------------

def test_a_carried_feed_keeps_its_own_fetched_at(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Carrying an entry forward with today's date would be worse than
    dropping it: a month-old file would read as fetched this morning, and
    nothing downstream could tell."""
    _run(tmp_path, monkeypatch, ["--seasons", "2022", "--only", "player_stats", "pbp"],
         at=AUGUST)

    _run(tmp_path, monkeypatch, ["--seasons", "2022", "--only", "player_stats"],
         at=SEPTEMBER)

    feeds = _feeds(tmp_path)
    assert feeds["pbp 2022"]["fetched_at"] == AUGUST.isoformat()
    assert feeds["player_stats 2022"]["fetched_at"] == SEPTEMBER.isoformat()


def test_the_cache_as_a_whole_is_still_dated_by_the_run_that_last_wrote_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The top-level stamp is what `staleness_hours` has always read and it
    still means what it meant: when a fetch last ran. The per-feed stamps are
    an addition, not a redefinition."""
    _run(tmp_path, monkeypatch, ["--seasons", "2022", "--only", "pbp"], at=AUGUST)
    _run(tmp_path, monkeypatch, ["--seasons", "2022", "--only", "player_stats"],
         at=SEPTEMBER)

    assert _manifest(tmp_path)["fetched_at"] == SEPTEMBER.isoformat()
    assert nflverse.staleness_hours(NFL, tmp_path, now=SEPTEMBER) == 0.0


def test_one_feed_can_be_asked_for_its_own_staleness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """After a partial run the cache and one of its feeds have different ages,
    and only the per-feed question can say so."""
    _run(tmp_path, monkeypatch, ["--seasons", "2022", "--only", "player_stats", "pbp"],
         at=AUGUST)
    _run(tmp_path, monkeypatch, ["--seasons", "2022", "--only", "player_stats"],
         at=SEPTEMBER)

    hours = nflverse.staleness_hours(NFL, tmp_path, now=SEPTEMBER, feed_season="pbp 2022")

    assert hours == pytest.approx((SEPTEMBER - AUGUST).total_seconds() / 3600.0)
    assert nflverse.staleness_hours(
        NFL, tmp_path, now=SEPTEMBER, feed_season="player_stats 2022"
    ) == 0.0


def test_a_feed_the_manifest_never_recorded_has_no_staleness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """None is not zero here either. "Never fetched" and "fetched a moment
    ago" are opposite conditions, and the per-feed answer must not blur them
    by falling back to the cache's own stamp."""
    _run(tmp_path, monkeypatch, ["--seasons", "2022", "--only", "player_stats"])

    assert nflverse.staleness_hours(
        NFL, tmp_path, now=SEPTEMBER, feed_season="pbp 2022"
    ) is None


def test_a_cache_that_was_never_fetched_has_no_staleness(tmp_path: Path) -> None:
    assert nflverse.staleness_hours(NFL, tmp_path, now=SEPTEMBER) is None
    assert nflverse.staleness_hours(
        NFL, tmp_path, now=SEPTEMBER, feed_season="pbp 2022"
    ) is None


# --- write_manifest on its own ----------------------------------------------

def _cache(raw_dir: Path, relative: str) -> str:
    path = raw_dir / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("stub\n", encoding="utf-8")
    return relative


def test_a_first_write_records_exactly_what_it_was_given(tmp_path: Path) -> None:
    entry = {"path": _cache(tmp_path, "nfl/pbp/play_by_play_2025.csv.gz"), "bytes": 5}

    nflverse.write_manifest(NFL, tmp_path, {"pbp 2025": entry}, fetched_at="A")

    assert set(_feeds(tmp_path)) == {"pbp 2025"}


def test_a_refetched_entry_replaces_its_predecessor_whole(tmp_path: Path) -> None:
    """Merging is per feed-season, not per field. An entry that no longer
    carries `bytes` must not keep the old run's `bytes` — a stale number
    presented as this run's measurement is the shape of every one of these."""
    relative = _cache(tmp_path, "nfl/pbp/play_by_play_2025.csv.gz")
    nflverse.write_manifest(
        NFL, tmp_path, {"pbp 2025": {"path": relative, "bytes": 5, "gone": True}},
        fetched_at="A",
    )

    nflverse.write_manifest(
        NFL, tmp_path, {"pbp 2025": {"path": relative, "bytes": 9}}, fetched_at="B"
    )

    assert _feeds(tmp_path)["pbp 2025"] == {
        "path": relative, "bytes": 9, "fetched_at": "B"
    }


def test_a_carried_entry_whose_file_is_gone_is_dropped(tmp_path: Path) -> None:
    """The other half of the rule. Merging forever would let the manifest
    assert a cached copy that somebody deleted, and "how old is this?" answered
    about a file that is not there is worse than no answer."""
    kept = _cache(tmp_path, "nfl/pbp/play_by_play_2025.csv.gz")
    deleted = _cache(tmp_path, "nfl/injuries/injuries_2025.csv")
    nflverse.write_manifest(
        NFL, tmp_path,
        {"pbp 2025": {"path": kept}, "injuries 2025": {"path": deleted}},
        fetched_at="A",
    )
    (tmp_path / deleted).unlink()

    nflverse.write_manifest(NFL, tmp_path, {"pbp 2025": {"path": kept}}, fetched_at="B")

    assert set(_feeds(tmp_path)) == {"pbp 2025"}


def test_an_entry_that_cannot_be_shown_absent_is_kept(tmp_path: Path) -> None:
    """Absence has to be shown. An entry with no usable path is not evidence
    that the file is missing — the same rule `is_provisional` applies to a date
    it cannot parse."""
    kept = _cache(tmp_path, "nfl/pbp/play_by_play_2025.csv.gz")
    nflverse.write_manifest(
        NFL, tmp_path,
        {"odd": {"bytes": 5}, "older": "a bare string", "pbp 2025": {"path": kept}},
        fetched_at="A",
    )

    nflverse.write_manifest(NFL, tmp_path, {"pbp 2025": {"path": kept}}, fetched_at="B")

    assert set(_feeds(tmp_path)) == {"odd", "older", "pbp 2025"}


def test_a_manifest_written_before_per_feed_stamps_inherits_the_run_that_wrote_it(
    tmp_path: Path,
) -> None:
    """The manifest committed to this repository has no per-feed stamps: every
    entry in it was written by the run whose top-level `fetched_at` it carries.
    Backfilling from that is the true answer, and leaving them bare would make
    the per-feed question unanswerable for the whole existing cache."""
    path = tmp_path / NFL.data_dir_segment / nflverse.MANIFEST_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    old = _cache(tmp_path, "nfl/injuries/injuries_2025.csv")
    path.write_text(
        json.dumps({
            "league": "nfl",
            "fetched_at": AUGUST.isoformat(),
            "feeds": {"injuries 2025": {"path": old, "bytes": 5}},
        }),
        encoding="utf-8",
    )
    new = _cache(tmp_path, "nfl/pbp/play_by_play_2025.csv.gz")

    nflverse.write_manifest(
        NFL, tmp_path, {"pbp 2025": {"path": new}}, fetched_at=SEPTEMBER.isoformat()
    )

    assert _feeds(tmp_path)["injuries 2025"]["fetched_at"] == AUGUST.isoformat()
    assert nflverse.staleness_hours(
        NFL, tmp_path, now=SEPTEMBER, feed_season="injuries 2025"
    ) == pytest.approx((SEPTEMBER - AUGUST).total_seconds() / 3600.0)


def test_an_unreadable_manifest_does_not_block_the_write(tmp_path: Path) -> None:
    """`read_manifest` answers `{}` for a corrupt file, so the merge has
    nothing to carry and the run still records what it fetched. A fetch that
    could not write its own record because the old one was damaged would turn
    a recoverable file into a stuck cache."""
    path = tmp_path / NFL.data_dir_segment / nflverse.MANIFEST_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not json", encoding="utf-8")
    relative = _cache(tmp_path, "nfl/pbp/play_by_play_2025.csv.gz")

    nflverse.write_manifest(NFL, tmp_path, {"pbp 2025": {"path": relative}},
                            fetched_at="B")

    assert set(_feeds(tmp_path)) == {"pbp 2025"}
