"""The tally that makes a season-long search honest.

Cooper's instruction is to keep searching all season. A search that runs every
week is not twelve tests — it is twelve tests a week, forever, and correcting
today's findings across today's twelve is a lie if twelve more were tested last
week. At a nominal 5% threshold roughly one look in twenty clears by chance, so
an automated edge-hunter without a cumulative tally manufactures findings on a
schedule, with clean intervals and good prose.
"""

from __future__ import annotations

import pytest

from football_betting_lab.experiment_ledger import (
    ExperimentLedger,
    Hypothesis,
    load,
    render,
    save,
)


def _h(name: str, search: str = "s", seasons=(2023, 2024)) -> Hypothesis:
    return Hypothesis(
        search=search, name=name, tested_on="2026-08-31",
        seasons=tuple(seasons), outcome="no demonstrated edge",
    )


def test_the_correction_grows_with_everything_ever_tested() -> None:
    """The fiftieth test does not get the first test's benefit of the doubt."""
    ledger = ExperimentLedger()
    ledger.record(_h("a"))
    one = ledger.correction_factor()
    ledger.record(*[_h(f"h{i}") for i in range(50)])

    assert ledger.correction_factor() > one
    assert one == 1.0


def test_re_running_the_same_test_does_not_inflate_the_correction() -> None:
    """The same hypothesis on the same seasons is one degree of freedom. If
    re-running a script widened every interval, nobody would re-run anything."""
    ledger = ExperimentLedger()
    ledger.record(_h("blowout risk"))
    added = ledger.record(_h("blowout risk"))

    assert added == 0
    assert ledger.count == 1


def test_the_same_hypothesis_on_a_new_season_is_a_new_test() -> None:
    """Because it is one: a fresh look at fresh data is a fresh chance for
    noise to clear."""
    ledger = ExperimentLedger()
    ledger.record(_h("blowout risk", seasons=(2023, 2024)))
    ledger.record(_h("blowout risk", seasons=(2025,)))

    assert ledger.count == 2


def test_the_ledger_refuses_to_shrink(tmp_path) -> None:
    """The tempting edit is to drop the tests that failed because they were
    "exploratory". Those are precisely what make a surviving one unlikely to be
    chance, and a ledger that can shrink reports a correction smaller than the
    truth."""
    path = tmp_path / "experiment_ledger.json"
    full = ExperimentLedger()
    full.record(*[_h(f"h{i}") for i in range(10)])
    save(full, path)

    trimmed = ExperimentLedger()
    trimmed.record(_h("h0"))

    with pytest.raises(ValueError, match="append-only"):
        save(trimmed, path)


def test_a_ledger_survives_the_round_trip(tmp_path) -> None:
    path = tmp_path / "experiment_ledger.json"
    original = ExperimentLedger()
    original.record(_h("a"), _h("b", search="other"))
    save(original, path)

    restored = load(path)

    assert restored.count == 2
    assert restored.by_search() == {"s": 1, "other": 1}
    assert restored.correction_factor() == pytest.approx(
        original.correction_factor()
    )


def test_an_absent_ledger_is_empty_rather_than_an_error(tmp_path) -> None:
    """A fresh clone has tested nothing, and that is a true statement."""
    assert load(tmp_path / "absent.json").count == 0


def test_the_report_states_the_factor_a_new_claim_must_clear() -> None:
    ledger = ExperimentLedger()
    ledger.record(*[_h(f"h{i}") for i in range(53)])

    text = render(ledger)

    assert "53 distinct hypotheses tested" in text
    assert "must be widened by" in text
    assert "not a substitute for a held-out season" in text


def test_an_empty_ledger_does_not_read_as_a_clean_bill_of_health() -> None:
    """The same failure the settlement screen once had: an absence rendering as
    a pass."""
    text = render(ExperimentLedger())

    assert "Nothing has been recorded yet" in text
    assert "must be widened by" not in text
