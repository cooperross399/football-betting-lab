"""The bundle allowlists nothing, and its default is "not supported".

Every bar exists because something failed it. The point of collecting them in
one artifact is that a human can check the reasoning rather than take it.
"""

from __future__ import annotations

import pytest

from football_betting_lab.reports.allowlist_evidence import (
    NOT_SUPPORTED,
    SUPPORTED,
    Bar,
    EvidenceBundle,
    MarketEvidence,
    render,
)


def _market(**bars: bool) -> MarketEvidence:
    entry = MarketEvidence(market="rush_yards", bets=16_829)
    entry.bars = [Bar(name, passed, "detail") for name, passed in bars.items()]
    return entry


def test_a_market_failing_any_bar_is_not_supported() -> None:
    """One failure is enough. The bars are not a score."""
    for failing in ("harness", "settlement", "consensus", "books", "replication"):
        bars = {b: True for b in ("harness", "settlement", "consensus", "books", "replication")}
        bars[failing] = False
        assert _market(**bars).verdict == NOT_SUPPORTED, failing


def test_a_market_clearing_every_bar_is_supported_for_review_not_approved() -> None:
    """The words matter. Clearing the bars means the measurements do not rule
    it out; it does not mean an edge is established."""
    entry = _market(harness=True, settlement=True, consensus=True, books=True,
                    replication=True)

    assert entry.verdict == SUPPORTED
    assert "not an approval" in entry.summary()


def test_a_market_with_no_bars_at_all_is_supported_only_vacuously() -> None:
    """Guarded because a bundle built with no measurements would otherwise
    pass everything silently."""
    empty = MarketEvidence(market="x", bets=0)

    assert empty.verdict == SUPPORTED
    assert not empty.bars  # ...which the render makes visible.


def test_the_rendered_bundle_says_it_allowlists_nothing() -> None:
    bundle = EvidenceBundle(league="nfl", markets=[_market(harness=True)])

    text = render(bundle)

    assert "allowlists nothing" in text
    assert "step six is Cooper" in text


def test_the_rendered_bundle_names_every_failed_bar() -> None:
    """A reader has to be able to see which bar failed and why, or the verdict
    is an assertion."""
    bundle = EvidenceBundle(
        league="nfl",
        markets=[_market(harness=True, settlement=False, consensus=True)],
    )

    text = render(bundle)

    assert "**FAIL**" in text
    assert "settlement" in text


def test_the_bundle_carries_what_would_change_the_numbers() -> None:
    bundle = EvidenceBundle(league="nfl", markets=[_market(harness=True)])
    bundle.caveats = ["**The did-not-play rule.** ..."]

    assert "What would change these numbers" in render(bundle)


def test_approval_is_stated_not_to_skip_the_gates() -> None:
    """Allowlisting says these prices may be used. It does not say skip the
    checks, and a reader signing it should see that."""
    text = render(EvidenceBundle(league="nfl", markets=[_market(harness=True)]))

    assert "does not say *skip the checks*" in text
