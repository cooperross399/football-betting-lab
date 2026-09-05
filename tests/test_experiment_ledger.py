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


def _hand_edit(path, *, keep: int) -> None:
    """Truncate the ledger file in place, as an editor would: no guard runs."""
    import json

    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["hypotheses"] = payload["hypotheses"][:keep]
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


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
    save(full, path, floor=0)

    trimmed = ExperimentLedger()
    trimmed.record(_h("h0"))

    with pytest.raises(ValueError, match="append-only"):
        save(trimmed, path, floor=10)
    # ...and the file on disk is still a floor of its own, so a caller that
    # passes zero does not get past it either.
    with pytest.raises(ValueError, match="append-only"):
        save(trimmed, path, floor=0)


def test_a_hand_edited_ledger_is_refused_by_the_floor(tmp_path) -> None:
    """Reproduction: the shrink guard compared the ledger with itself.

    `scripts/record_experiments.py` loads the file, mutates the object, and
    saves it back to the same path. The floor used to be measured by
    re-reading that path inside `save()`, so a ledger already shrunk on disk —
    by hand, in an editor — was its own floor and the write went through. This
    is the load/mutate/save shape exactly, with the count the caller held
    before the edit passed as the floor; that count is what refuses it.
    """
    path = tmp_path / "experiment_ledger.json"
    full = ExperimentLedger()
    full.record(*[_h(f"h{i}") for i in range(53)])
    save(full, path, floor=0)
    committed = len(load(path).hypotheses)

    # The hand edit: eighteen entries gone from the file itself, written the
    # way an editor writes it — straight to disk, through no guard at all.
    _hand_edit(path, keep=35)
    assert len(load(path).hypotheses) == 35

    # The recorder's run: load the file, record nothing new, save it back.
    ledger = load(path)
    with pytest.raises(ValueError, match="from 53 entries to 35"):
        save(ledger, path, floor=committed)


def test_the_floor_must_be_stated(tmp_path) -> None:
    """A floor that defaults is a floor nobody measured."""
    path = tmp_path / "experiment_ledger.json"
    ledger = ExperimentLedger()
    ledger.record(_h("a"))
    with pytest.raises(TypeError):
        save(ledger, path)  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        save(ledger, path, floor=True)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        save(ledger, path, floor=-1)


def test_the_recorder_reads_the_committed_count_as_a_second_floor(
    tmp_path, monkeypatch
) -> None:
    """The audit's reproduction, run end to end through the script.

    A ledger committed with 53 entries, hand-edited to 35, then the recorder
    is run with no arguments. Before this round it re-rendered the shrunken
    ledger and printed the smaller correction. Now the count committed at
    `HEAD` is a floor and the write is refused.
    """
    import subprocess
    from importlib import util

    script = util.spec_from_file_location(
        "record_experiments",
        __file__.rsplit("/tests/", 1)[0] + "/scripts/record_experiments.py",
    )
    assert script is not None and script.loader is not None
    recorder = util.module_from_spec(script)
    script.loader.exec_module(recorder)

    repository = tmp_path / "repo"
    outputs = repository / "data" / "outputs"
    outputs.mkdir(parents=True)
    path = outputs / "experiment_ledger.json"
    full = ExperimentLedger()
    full.record(*[_h(f"h{i}") for i in range(53)])
    save(full, path, floor=0)
    for command in (
        ["git", "init", "-q"],
        ["git", "add", "-A"],
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com",
         "commit", "-q", "-m", "ledger"],
    ):
        subprocess.run(command, cwd=repository, check=True, capture_output=True)

    assert recorder.committed_entry_count(path, repository=repository) == 53

    _hand_edit(path, keep=35)

    monkeypatch.setattr(recorder, "OUTPUTS_DIR", outputs)
    monkeypatch.setattr(recorder, "PROJECT_ROOT", repository)
    with pytest.raises(ValueError, match="from 53 entries to 35"):
        recorder.main([])

    # ...and outside any repository the committed floor is honestly zero, so
    # the in-memory floor is the only one — which is the first-run state the
    # diff-level workflow guard exists for.
    assert recorder.committed_entry_count(tmp_path / "elsewhere.json", repository=tmp_path) == 0


def test_a_ledger_survives_the_round_trip(tmp_path) -> None:
    path = tmp_path / "experiment_ledger.json"
    original = ExperimentLedger()
    original.record(_h("a"), _h("b", search="other"))
    save(original, path, floor=0)

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


# --------------------------------------------------------------------------
# The old shape, run rather than described.
# --------------------------------------------------------------------------
#
# Four files in this repository used to say the pre-floor `save()` "could
# never fire" and "compared the ledger with itself". Half of that was false,
# and nothing checked it because the old code was described rather than
# executed. So the old body is reconstructed here — verbatim from the commit
# it was replaced in, `ac6d9b2` — and both halves are measured.


def _old_save(ledger: ExperimentLedger, path) -> None:
    """`save()` exactly as it stood before the explicit floor (`ac6d9b2`).

    Reconstructed rather than imported, because the point is to exercise
    behaviour that no longer exists in the package. The write itself is
    reduced to what the assertions need; the guard is copied unchanged, and
    `test_the_reconstruction_matches_the_commit_it_claims_to` holds it against
    the real blob.
    """
    import json
    from pathlib import Path

    target = Path(path)
    if target.is_file():
        existing = load(target)
        if len(ledger.hypotheses) < len(existing.hypotheses):
            raise ValueError(
                f"The experiment ledger would fall from "
                f"{len(existing.hypotheses)} entries to {len(ledger.hypotheses)}. "
                "It is append-only: the tests that failed are what make a "
                "surviving one unlikely to be chance, and a ledger that can "
                "shrink reports a correction smaller than the truth."
            )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps({"hypotheses": [
            {"search": h.search, "name": h.name, "tested_on": h.tested_on,
             "seasons": list(h.seasons), "outcome": h.outcome}
            for h in ledger.hypotheses
        ]}, indent=2) + "\n",
        encoding="utf-8",
    )


#: The commit whose `save()` the reconstruction below copies. Written in full
#: rather than abbreviated: an abbreviation is a prefix that can stop being
#: unique, and a test that fails because two objects now share seven
#: characters is a test nobody trusts.
PRE_FLOOR_COMMIT = "ac6d9b2c3841d3fd97652ef6753a3fd5785b86c9"


def test_the_reconstruction_matches_the_commit_it_claims_to() -> None:
    """A reconstruction nobody checked is a claim, not a measurement.

    The guard's own lines are compared against the blob at `PRE_FLOOR_COMMIT`,
    so the two tests below exercise the code that shipped rather than a
    plausible retelling of it. If git cannot produce the blob this FAILS: an
    unverifiable reconstruction proves nothing about the old behaviour, and
    "I could not check" must not read the same as "I checked".

    It therefore needs the repository's history, which is why
    `.github/workflows/tests.yml` checks out with `fetch-depth: 0` —
    `tests/test_workflows.py::check_the_required_check_job_checks_out_history`
    pins that, so this test's premise cannot be removed by a workflow edit.
    """
    import inspect
    import subprocess
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        ["git", "show", f"{PRE_FLOOR_COMMIT}:src/football_betting_lab/experiment_ledger.py"],
        cwd=root, capture_output=True, text=True,
    )
    assert completed.returncode == 0, (
        f"cannot read the pre-floor save() out of {PRE_FLOOR_COMMIT}: "
        f"{completed.stderr}. The reconstruction below cannot be checked, and "
        "an unchecked reconstruction is not evidence about the old code. A "
        "shallow clone is the usual cause; CI checks out with fetch-depth: 0."
    )
    original = completed.stdout
    for line in (
        "    target = Path(path)",
        "    if target.is_file():",
        "        existing = load(target)",
        "        if len(ledger.hypotheses) < len(existing.hypotheses):",
    ):
        assert line in original, line
        assert line in inspect.getsource(_old_save), line


def test_the_old_shape_fires_on_an_in_process_shrink(tmp_path) -> None:
    """The false claim, corrected by running the code.

    Four files said the pre-floor guard "could never fire" and "compared the
    ledger with itself". It compared the in-memory object against the FILE, so
    a run that shrinks the ledger while holding it is refused — which is a
    filter, a rebuild, or a bug, and is the case the guard was written for.
    """
    path = tmp_path / "experiment_ledger.json"
    full = ExperimentLedger()
    full.record(*[_h(f"h{index}") for index in range(53)])
    _old_save(full, path)

    shrunk = ExperimentLedger(hypotheses=load(path).hypotheses[:35])
    with pytest.raises(ValueError, match="from 53 entries to 35"):
        _old_save(shrunk, path)


def test_the_old_shape_cannot_see_a_ledger_edited_on_disk(tmp_path) -> None:
    """And the half that WAS open, which is the edit somebody would make.

    Shrink the file itself and commit it, and the recorder's load/mutate/save
    round trip re-reads the shrunken file as its own floor. 53 -> 35 goes
    through, silently, and the correction it renders afterwards is smaller
    than the truth. The explicit floor is what closes this, and the
    diff-level guard is what closes it for a PR that never runs the recorder.
    """
    path = tmp_path / "experiment_ledger.json"
    full = ExperimentLedger()
    full.record(*[_h(f"h{index}") for index in range(53)])
    _old_save(full, path)

    _hand_edit(path, keep=35)
    reloaded = load(path)
    assert len(reloaded.hypotheses) == 35

    _old_save(reloaded, path)  # no exception: this is the hole
    assert len(load(path).hypotheses) == 35

    # ...and the same round trip against today's save() is refused, given the
    # floor the recorder measures before the edit.
    with pytest.raises(ValueError, match="from 53 entries to 35"):
        save(reloaded, path, floor=53)


def test_the_correction_the_shrink_would_have_reported(tmp_path) -> None:
    """The arithmetic in the prose, recomputed rather than quoted.

    Every file that tells this story quotes 53 -> 35 and x1.69 -> x1.63. Those
    are the package's own factors at those counts and 53 - 18 = 35; asserted
    here so a future edit to the constants makes the prose go red instead of
    going stale.
    """
    fifty_three = ExperimentLedger()
    fifty_three.record(*[_h(f"h{index}") for index in range(53)])
    thirty_five = ExperimentLedger(hypotheses=fifty_three.hypotheses[:35])

    assert len(fifty_three.hypotheses) - 18 == len(thirty_five.hypotheses)
    assert f"{fifty_three.correction_factor():.2f}" == "1.69"
    assert f"{thirty_five.correction_factor():.2f}" == "1.63"
