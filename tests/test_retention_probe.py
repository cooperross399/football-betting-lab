"""What the probe may conclude, and what it may not.

Two of these are regression tests for defects this module actually shipped,
each written by reproducing the defect first:

* chunk responses cached under a filename tagged with the chunk's *length*,
  so four ten-market chunks collided and three were lost;
* retention rolled up by provider key alone, which reported three markets as
  unmeasurable when their alternate ladders had them all along.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from football_betting_lab.leagues import NFL
from football_betting_lab.providers.odds_api import CreditCapReached, Spend, _guard
from football_betting_lab.reports import retention_probe as rp


def _probe(markets: dict[str, tuple[int, int]], window: str = "sunday early"):
    """One event that returned `markets` as {key: (books, outcomes)}."""
    target = rp.ProbeTarget(
        season=2025,
        week=1,
        game_id="g",
        kickoff_utc=datetime(2025, 9, 7, 17, 0, tzinfo=timezone.utc),
        home="BUF",
        away="BAL",
        window=window,
    )
    probe = rp.EventProbe(target=target, event_id="e", markets_requested=tuple(markets))
    for key, (books, outcomes) in markets.items():
        probe.books_by_market[key] = {f"book{i}" for i in range(books)}
        probe.outcomes_by_market[key] = outcomes
    return probe


def _result(probes, requested):
    result = rp.ProbeResult(
        league_key=NFL.key,
        snapshot_lead_minutes=rp.SNAPSHOT_LEAD_MINUTES,
        markets_requested=tuple(requested),
    )
    for probe in probes:
        result.absorb_probe(probe)
        result.probes.append(probe)
    return result


# -- the cache-collision regression -----------------------------------------


def test_two_different_chunks_of_the_same_length_get_different_cache_files() -> None:
    """The defect, reproduced: tagging a chunk by its length collides.

    A forty-six-market request chunked by ten produces four chunks of ten. All
    four wrote to `{event}_{stamp}_10.json`, so three were silently lost and a
    report rebuilt from that cache called thirty-one retained markets absent.
    """
    first = ("player_pass_yds", "player_pass_tds")
    second = ("player_rush_yds", "player_rush_tds")

    assert len(first) == len(second)
    assert rp.markets_fingerprint(first) != rp.markets_fingerprint(second)
    assert rp._cache_path(Path("/c"), "e", "2025-09-07T17:00:00Z", first) != (
        rp._cache_path(Path("/c"), "e", "2025-09-07T17:00:00Z", second)
    )


def test_the_cache_key_does_not_depend_on_the_order_markets_were_asked_in() -> None:
    """Otherwise a re-run that reorders its market list re-buys everything."""
    assert rp.markets_fingerprint(("a", "b")) == rp.markets_fingerprint(("b", "a"))


# -- the roll-up regression --------------------------------------------------


def test_a_market_absent_from_its_featured_key_but_present_in_its_ladder_is_retained() -> None:
    """The `total_2_5` lesson, in the shape it actually took here.

    `player_rush_tds` returned nothing across twenty events; its ladder was
    priced on two of them. Read by key that says the market cannot be
    measured. Read by market — the unit that gets modelled, measured and
    approved — it says it can.
    """
    requested = ("player_rush_tds", "player_rush_tds_alternate")
    result = _result([_probe({"player_rush_tds_alternate": (1, 6)})], requested)

    rollup = {item.project_key: item for item in rp.rollup_by_project_market(result)}

    assert rollup["rush_tds"].retained
    assert rollup["rush_tds"].events_seen == 1
    assert result.events_seen("player_rush_tds") == 0


def test_a_market_present_in_its_featured_key_and_absent_from_its_ladder_is_retained() -> None:
    """The reverse case, from the same run: a roll-up that only trusted
    ladders would get `pass_longest_completion` backwards."""
    requested = (
        "player_pass_longest_completion",
        "player_pass_longest_completion_alternate",
    )
    result = _result([_probe({"player_pass_longest_completion": (6, 348)})], requested)

    rollup = {item.project_key: item for item in rp.rollup_by_project_market(result)}

    assert rollup["pass_longest_completion"].retained


def test_an_event_is_counted_once_even_when_both_keys_priced_it() -> None:
    """Otherwise a market with a ladder looks twice as covered as one without."""
    requested = ("player_pass_yds", "player_pass_yds_alternate")
    result = _result(
        [_probe({"player_pass_yds": (8, 100), "player_pass_yds_alternate": (7, 90)})],
        requested,
    )

    rollup = {item.project_key: item for item in rp.rollup_by_project_market(result)}

    assert rollup["pass_yards"].events_seen == 1
    assert rollup["pass_yards"].outcomes == 190


# -- retained is not the same claim as measurable ----------------------------


def test_a_market_quoted_by_one_book_is_reported_as_thin() -> None:
    """A measurement against one book measures that book, not the market."""
    result = _result(
        [_probe({"player_rush_tds_alternate": (1, 6)}) for _ in range(20)],
        ("player_rush_tds_alternate",),
    )

    item = rp.rollup_by_project_market(result)[0]

    assert item.retained and item.thin
    assert "thin" in item.verdict()


def test_a_market_on_a_handful_of_events_is_reported_as_thin() -> None:
    probes = [_probe({"player_rush_tds_alternate": (4, 6)}) for _ in range(2)]
    probes += [_probe({"player_pass_yds": (8, 100)}) for _ in range(18)]
    result = _result(probes, ("player_rush_tds_alternate", "player_pass_yds"))

    rollup = {item.project_key: item for item in rp.rollup_by_project_market(result)}

    assert rollup["rush_tds"].thin
    assert not rollup["pass_yards"].thin


def test_a_broadly_quoted_market_is_not_thin() -> None:
    result = _result(
        [_probe({"player_pass_yds": (8, 150)}) for _ in range(20)],
        ("player_pass_yds",),
    )

    assert not rp.rollup_by_project_market(result)[0].thin


# -- absence is a claim that needs a sample ----------------------------------


def test_below_the_minimum_absence_is_reported_as_not_seen_not_unmeasurable() -> None:
    """One NHL probe called a market unmeasurable that was priced on 54 of the
    next 58 events. Below the threshold the report may not make that claim."""
    probes = [_probe({"player_pass_yds": (8, 100)})]
    assert len(probes) < rp.MINIMUM_PROBES_FOR_ABSENCE
    result = _result(probes, ("player_pass_yds", "player_rush_tds"))

    verdict = result.verdict("player_rush_tds")

    assert "not seen" in verdict
    assert "no historical price" not in verdict


def test_above_the_minimum_absence_may_be_stated_plainly() -> None:
    probes = [_probe({"player_pass_yds": (8, 100)}) for _ in range(20)]
    result = _result(probes, ("player_pass_yds", "player_rush_tds"))

    assert "no historical price" in result.verdict("player_rush_tds")


def test_a_market_the_provider_refused_by_name_is_not_reported_as_unretained() -> None:
    """"The provider does not serve this key" and "no book retained it" are
    different facts, and only one of them is about retention."""
    probe = _probe({"player_pass_yds": (8, 100)})
    probe.markets_requested = ("player_pass_yds", "player_tds_over")
    probe.refused_markets = ("player_tds_over",)
    result = _result([probe], probe.markets_requested)

    assert result.refused_everywhere() == ("player_tds_over",)
    assert "refused by name" in result.verdict("player_tds_over")


# -- sampling ----------------------------------------------------------------


def _schedule_rows() -> list[dict[str, str]]:
    import csv

    from football_betting_lab.config import RAW_DIR
    from football_betting_lab.season import schedule_path

    with schedule_path(NFL, RAW_DIR).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_the_sample_spans_both_seasons_rather_than_front_loading_one() -> None:
    """A `[::step]` slice looks like an even spread and is not: it truncates
    to the first `take` picks, which drew 13 of 20 events from 2024."""
    targets = rp.select_targets(_schedule_rows(), NFL, seasons=(2024, 2025), count=20)

    by_season = {season: 0 for season in (2024, 2025)}
    for target in targets:
        by_season[target.season] += 1

    assert min(by_season.values()) >= 8, by_season


def test_the_sample_spans_kickoff_windows_rather_than_only_marquee_games() -> None:
    """Book coverage is not uniform across the schedule. A sample of night
    games would measure marquee retention and call it retention."""
    targets = rp.select_targets(_schedule_rows(), NFL, seasons=(2024, 2025), count=20)

    windows = {target.window for target in targets}

    assert {"sunday early", "sunday late"} <= windows
    assert len(windows) >= 4


def test_the_sample_never_predates_the_day_props_began_being_retained() -> None:
    """Absence before 2023-05-03 would be the data not existing, which is a
    different fact from the provider not retaining it."""
    targets = rp.select_targets(_schedule_rows(), NFL, seasons=(2023,), count=20)

    for target in targets:
        assert target.kickoff_utc.date().isoformat() >= rp.PROPS_AVAILABLE_FROM


def test_the_same_request_selects_the_same_events_every_time() -> None:
    """A probe that samples differently on each run cannot be re-run to check
    a number, and producing a number someone acts on is its whole job."""
    rows = _schedule_rows()
    first = rp.select_targets(rows, NFL, seasons=(2024, 2025), count=20)
    second = rp.select_targets(rows, NFL, seasons=(2024, 2025), count=20)

    assert [t.game_id for t in first] == [t.game_id for t in second]


def test_the_snapshot_is_taken_before_kickoff_not_after() -> None:
    target = rp.select_targets(_schedule_rows(), NFL, seasons=(2024,), count=1)[0]

    taken = datetime.strptime(target.snapshot, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=timezone.utc
    )

    assert taken < target.kickoff_utc


# -- the cap ------------------------------------------------------------------


def test_the_cap_is_checked_before_the_request_not_after() -> None:
    """A cap enforced after the spend is not a cap; it is a report of how far
    past it the run went."""
    spend = Spend(credits_spent=9_000)

    with pytest.raises(CreditCapReached):
        _guard(spend, 9_500, 600, "one more event")

    assert spend.credits_spent == 9_000


def test_a_response_with_no_cost_header_is_charged_the_pessimistic_estimate() -> None:
    """Guessing low would let a run drift past its cap while reporting that it
    had not."""
    spend = Spend()

    charged = spend.record({}, fallback=460)

    assert charged == 460
    assert spend.credits_spent == 460
    assert spend.notes


def test_the_measured_cost_is_preferred_over_the_estimate() -> None:
    spend = Spend()

    charged = spend.record({"x-requests-last": "120"}, fallback=460)

    assert charged == 120
    assert spend.credits_spent == 120
    assert not spend.notes


# -- the record round-trips ---------------------------------------------------


def test_the_report_rebuilds_from_the_record_without_spending_anything(
    tmp_path: Path,
) -> None:
    """The report is derived data. Improving its wording must never cost
    7,280 credits again."""
    result = _result(
        [_probe({"player_pass_yds": (8, 100)}) for _ in range(20)],
        ("player_pass_yds", "player_rush_tds"),
    )
    result.spend.credits_spent = 7_280
    payload = json.loads(json.dumps(rp.to_json(result, NFL)))

    rebuilt = rp.rebuild_from_record(payload, NFL, cache_dir=tmp_path)

    assert len(rebuilt.successful) == 20
    assert rebuilt.events_seen("player_pass_yds") == 20
    assert rebuilt.outcomes("player_pass_yds") == result.outcomes("player_pass_yds")
    assert rebuilt.books("player_pass_yds") == result.books("player_pass_yds")
    assert rebuilt.spend.credits_spent == 7_280


def test_a_cache_that_disagrees_with_the_record_is_reported_rather_than_hidden(
    tmp_path: Path,
) -> None:
    """The run whose chunks collided left a cache missing most of its markets.
    Preferring either side silently is how that stayed invisible."""
    result = _result(
        [_probe({"player_pass_yds": (8, 100)}) for _ in range(20)],
        ("player_pass_yds",),
    )
    payload = json.loads(json.dumps(rp.to_json(result, NFL)))

    rebuilt = rp.rebuild_from_record(payload, NFL, cache_dir=tmp_path)

    assert any("absent from the cached responses" in note for note in rebuilt.spend.notes)
