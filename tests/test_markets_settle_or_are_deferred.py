"""Every wired market names what settles it; everything else says why not.

The rule this protects: **if nothing here can settle it, it is not wired.**
Fetching prices nothing can consume spends credits on rows no join will ever
find, and pricing without honest settlement manufactures evidence.

The second rule: a market the provider serves and this lab does not wire is
**recorded with its reason**, never silently dropped. "The provider does not
offer this" and "we never asked" have looked identical before, and the second
cost the NHL lab a market for a season.
"""

from __future__ import annotations

import pytest

from football_betting_lab import markets as registry


def test_every_wired_market_names_the_quantity_that_settles_it() -> None:
    missing = [m.key for m in registry.ALL_MARKETS if not m.settles_on.strip()]

    assert missing == [], (
        f"these markets are wired with nothing to settle them: {missing}. "
        "Either name the nflverse quantity, or move them to DEFERRED_MARKETS "
        "with the reason."
    )


def test_every_market_key_is_unique_on_both_sides_of_the_vocabulary() -> None:
    project = [m.key for m in registry.ALL_MARKETS]
    provider = [m.provider_key for m in registry.ALL_MARKETS]

    assert len(set(project)) == len(project), "duplicate project market key"
    assert len(set(provider)) == len(provider), "duplicate provider market key"


def test_an_alternate_ladder_maps_onto_a_market_that_exists() -> None:
    """A ladder pointing at nothing is a fetch whose rows never join."""
    orphans = {
        ladder: target
        for ladder, target in registry.ALTERNATE_PROVIDER_KEYS.items()
        if target not in registry.MARKETS_BY_KEY
    }

    assert orphans == {}, f"alternate ladders with no market: {orphans}"


def test_the_three_featured_markets_are_the_only_bulk_ones() -> None:
    """Everything else is per event. Asking the bulk endpoint for an
    alternate ladder made the provider refuse the whole request in the NHL
    lab, and it looked like an off-season for two rounds of debugging."""
    bulk = registry.bulk_provider_keys(tier=2)

    assert set(bulk) == {"h2h", "spreads", "totals"}


def test_tier_one_is_a_strict_subset_of_tier_two() -> None:
    """Tiers are a credit decision, so they must nest. A tier-1 market absent
    from tier 2 would be fetched by the cheap plan and not the full one."""
    tier1 = set(registry.per_event_provider_keys(1))
    tier2 = set(registry.per_event_provider_keys(2))

    assert tier1 <= tier2


def test_deferred_markets_each_carry_a_reason() -> None:
    empty = [key for key, why in registry.DEFERRED_MARKETS.items() if not why.strip()]

    assert empty == [], f"deferred without a reason: {empty}"


def test_a_deferred_market_is_never_also_wired() -> None:
    """Otherwise the reason and the wiring disagree and one of them is a lie."""
    wired = {m.provider_key for m in registry.ALL_MARKETS}
    both = wired & set(registry.DEFERRED_MARKETS)

    assert both == set(), f"markets both wired and deferred: {sorted(both)}"


def test_market_lookup_reports_what_it_knows_rather_than_raising_blindly() -> None:
    with pytest.raises(KeyError) as excinfo:
        registry.market_for("player_wickets")

    assert "Known markets" in str(excinfo.value)


def test_an_unknown_provider_key_is_ignored_not_fatal() -> None:
    """A provider response carries markets this lab does not price. Every one
    of them being an error would make an ordinary response unparseable."""
    assert registry.market_for_provider_key("player_disposals") is None
    assert registry.market_for_provider_key("player_pass_yds") is not None


def test_yardage_markets_say_they_are_compound_rather_than_counts() -> None:
    """Yards are opportunities x yards per opportunity: right-skewed and
    zero-inflated. A count distribution is the wrong shape, and the place that
    has to remember it is the table the models read."""
    for key in ("pass_yards", "rush_yards", "reception_yards"):
        assert "compound" in registry.market_for(key).settles_on

    for key in ("pass_longest_completion", "rush_longest", "reception_longest"):
        assert "extreme-value" in registry.market_for(key).settles_on

    # ...and receptions is the one that genuinely is a count.
    assert "count" in registry.market_for("receptions").settles_on
