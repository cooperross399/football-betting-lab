"""No policy ships by assertion, and no recorded decision is trusted blindly.

A constant in code says what is in force. It cannot say why, when, or on what
evidence, and six months later nobody can tell whether a flag was set because
a measurement won or because it looked sensible on a Tuesday.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from football_betting_lab.leagues import NFL
from football_betting_lab.verdicts import (
    VERDICT_FILES,
    describe,
    read,
    record,
    ships,
    verdict_path,
)


POLICY = "props_recency_weighting"


def test_no_verdict_file_means_no_policy_in_force(tmp_path: Path) -> None:
    """The conservative reading of "no recorded decision"."""
    assert not ships(POLICY, NFL, output_dir=tmp_path)


def test_an_unreadable_verdict_file_ships_nothing(tmp_path: Path) -> None:
    verdict_path(POLICY, NFL, tmp_path).write_text("{not json", encoding="utf-8")

    verdict = read(POLICY, NFL, output_dir=tmp_path)

    assert not verdict.ships
    assert "could not be read" in verdict.summary


def test_a_verdict_that_did_not_ship_does_not_ship(tmp_path: Path) -> None:
    record(POLICY, NFL, ships_it=False, measured_on="2025", variants_tested=1,
           summary="It lost.", output_dir=tmp_path)

    assert not ships(POLICY, NFL, output_dir=tmp_path)


def test_a_verdict_that_shipped_ships(tmp_path: Path) -> None:
    record(POLICY, NFL, ships_it=True, measured_on="2025", variants_tested=1,
           summary="It won.", output_dir=tmp_path)

    assert ships(POLICY, NFL, output_dir=tmp_path)


def test_an_unknown_policy_raises_rather_than_silently_not_shipping() -> None:
    """A typo that silently disables a policy is worse than one that stops the
    run, because nothing anywhere reports it."""
    with pytest.raises(KeyError) as excinfo:
        ships("props_recncy_weighting", NFL)

    assert "Known:" in str(excinfo.value)


def test_a_verdict_is_recorded_per_league(tmp_path: Path) -> None:
    """Approving a policy in the NFL says nothing about college football."""
    assert verdict_path(POLICY, NFL, tmp_path).name.startswith(f"{NFL.key}_")


def test_the_citation_names_the_degrees_of_freedom_that_were_spent(
    tmp_path: Path,
) -> None:
    """Testing five variants against one bought season and shipping the best
    is how a lab talks itself into noise. The count travels with the verdict."""
    record(POLICY, NFL, ships_it=True, measured_on="2025", variants_tested=5,
           summary="", output_dir=tmp_path)

    citation = read(POLICY, NFL, output_dir=tmp_path).citation()

    assert "5 variants" in citation
    assert "candidate rather than a finding" in citation


def test_a_single_variant_does_not_claim_degrees_of_freedom_it_did_not_spend(
    tmp_path: Path,
) -> None:
    record(POLICY, NFL, ships_it=True, measured_on="2025", variants_tested=1,
           summary="", output_dir=tmp_path)

    assert "variants" not in read(POLICY, NFL, output_dir=tmp_path).citation()


def test_describe_lists_every_known_policy(tmp_path: Path) -> None:
    line = describe(NFL, output_dir=tmp_path)

    for policy in VERDICT_FILES:
        assert policy in line


def test_the_recorded_file_carries_the_evidence_not_just_the_flag(
    tmp_path: Path,
) -> None:
    """A flag with no measurement behind it is what this door exists to
    prevent."""
    path = record(POLICY, NFL, ships_it=True,
                  measured_on="2025 bought prices, 24,470 bets",
                  variants_tested=2, summary="Won the priced test.",
                  output_dir=tmp_path)

    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["measured_on"]
    assert payload["variants_tested"] == 2
    assert payload["summary"]
    assert payload["league"] == NFL.key


def test_no_policy_is_in_force_without_a_measurement_behind_it() -> None:
    """The durable invariant, replacing "nothing ships".

    "Nothing ships" was true until the first experiment ran and then it was
    just a stale assertion about a moment. What has to stay true is that a
    policy in force can always name the measurement that put it there and how
    many variants were tried against the same data to get it.
    """
    for policy in VERDICT_FILES:
        verdict = read(policy, NFL)
        if not verdict.ships:
            continue
        assert verdict.measured_on, policy
        assert verdict.summary, policy
        assert verdict.variants_tested >= 1, policy


# -- what a decision rule must actually test ---------------------------------


def test_a_verdict_that_ships_must_name_what_it_was_measured_on(
    tmp_path: Path,
) -> None:
    """A shipped policy with an empty `measured_on` is a flag with no
    measurement behind it, which is the thing this door exists to prevent."""
    record(POLICY, NFL, ships_it=True, measured_on="", variants_tested=1,
           summary="", output_dir=tmp_path)

    verdict = read(POLICY, NFL, output_dir=tmp_path)

    assert verdict.ships
    # The citation is what a report prints. If there is nothing to cite, the
    # reader can see that rather than being told a decision was justified.
    assert "decided on" not in verdict.citation()
