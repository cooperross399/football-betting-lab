"""The skip gate, exercised on XML instead of on a merged workflow.

The one place this gate runs for real is the `.github/workflows/tests.yml` step
whose command is `python scripts/check_test_results.py "$RUNNER_TEMP/junit.xml"`
— cited by its command and not by its position. A workflow can only be tested
by merging it, so the logic lives in a script and the script's cases live here.

The case that matters most is not the clean pass. It is the pair at the bottom:
a required module that vanished, and one that is still listed but ran nothing.
Both are what `git rm tests/test_no_secrets_committed.py` looks like from
inside the evidence file, and both used to make the build GREENER. No count is
quoted for the drop; the size of it is whatever `pytest --collect-only -q` on
the guard reports today.

Every fixture is built in tmp_path. This test reads no junit.xml from disk and
does not care whether the suite it is part of is passing.

What it does not do, said plainly: it does not prove the script consults no
ambient input. The NCAAF lab's copy of this file runs a differential sweep over
the environment, the hash seed and the working directory to observe that; this
lab's does not, and the honest residue is that a waiver keyed on something
outside the XML is caught here only by review of `check()`. What IS observed is
that the verdict follows the bytes and not the file's name, and that no
environment variable this file can think of moves it.
"""

from __future__ import annotations

import importlib.util
import os
import random
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_test_results.py"
_spec = importlib.util.spec_from_file_location("check_test_results", _SCRIPT)
assert _spec is not None and _spec.loader is not None
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)


def case(classname: str, name: str, body: str = "") -> str:
    inner = f">{body}</testcase>" if body else " />"
    return f'<testcase classname="{classname}" name="{name}" time="0.001"{inner}'


def now_stamp() -> str:
    """A timestamp the gate reads as "this run", in pytest's own spelling."""
    return datetime.now().astimezone().isoformat()


def suite(
    cases: list[str],
    *,
    skipped: int = 0,
    failures: int = 0,
    errors: int = 0,
    timestamp: str | None = None,
) -> str:
    """A junit document shaped as pytest writes one, with the counts passed
    separately so a fixture can make them disagree with the elements.

    The timestamp defaults to now because every fixture that is not about
    staleness must look like fresh evidence; the staleness cases pass their
    own.
    """
    stamped = now_stamp() if timestamp is None else timestamp
    attribute = f' timestamp="{stamped}"' if stamped else ""
    return (
        '<?xml version="1.0" encoding="utf-8"?><testsuites name="pytest tests">'
        f'<testsuite name="pytest" errors="{errors}" failures="{failures}" '
        f'skipped="{skipped}" tests="{len(cases)}" time="0.9"{attribute}>'
        + "".join(cases)
        + "</testsuite></testsuites>"
    )


def defined_in(module: str) -> int:
    """How many `test_*` functions the real guard module defines."""
    return gate.test_functions_in(gate.REPOSITORY_ROOT / module) or 0


def full_run(extra: list[str] | None = None, drop: str | None = None) -> list[str]:
    """Every required module, at or above the per-test floor it is held to.

    Two testcases used to be enough here. They no longer are: the gate floors
    each module's recorded testcases against the `test_*` functions its source
    defines, so a fixture that stands in for a clean run has to clear that
    floor the way a clean run does.
    """
    cases: list[str] = []
    for module in gate.REQUIRED_MODULES:
        if module == drop:
            continue
        key = gate.module_key(module)
        cases.append(case(key, "test_one"))
        # A test inside a class is recorded as `<module>.<Class>`; it must
        # still count toward its module.
        cases.append(case(f"{key}.TestGroup", "test_two"))
        for index in range(max(0, defined_in(module) - 2)):
            cases.append(case(key, f"test_filler_{index}"))
    return cases + (extra or [])


def write(tmp_path: Path, xml: str, name: str = "junit.xml") -> Path:
    path = tmp_path / name
    path.write_text(xml, encoding="utf-8")
    return path


def test_a_clean_run_passes(tmp_path: Path) -> None:
    problems, summary = gate.check(write(tmp_path, suite(full_run())))
    assert problems == []
    assert f"{len(full_run())} testcases recorded" in summary
    assert "0 skipped, 0 xfailed, 0 failed, 0 errored" in summary
    assert gate.main(["check_test_results.py", str(write(tmp_path, suite(full_run())))]) == 0


def test_one_skip_fails_the_run(tmp_path: Path) -> None:
    """The case the whole gate exists for: pytest exits 0 on this."""
    skip = case(
        "tests.test_build_datasets", "test_anytime_td_is_a_flag",
        '<skipped type="pytest.skip" message="processed tables not built in this checkout">'
        "tests/test_build_datasets.py:29: processed tables not built</skipped>",
    )
    problems, _ = gate.check(write(tmp_path, suite(full_run([skip]), skipped=1)))
    assert len(problems) == 1
    assert "1 skipped test(s)" in problems[0]
    assert "test_anytime_td_is_a_flag" in problems[0]
    assert "processed tables not built in this checkout" in problems[0]


def test_an_xfail_fails_the_run(tmp_path: Path) -> None:
    xfail = case(
        "tests.test_workflows", "test_paths_filter_absent",
        '<skipped type="pytest.xfail" message="known broken" />',
    )
    problems, _ = gate.check(write(tmp_path, suite(full_run([xfail]), skipped=1)))
    assert len(problems) == 1
    assert "1 xfail/xpass test(s)" in problems[0]


def test_a_skipped_element_with_no_type_still_fails(tmp_path: Path) -> None:
    """Bucketing by `type=` is for the report only; anything pytest wrote as
    <skipped> is a test that did not run."""
    odd = case("tests.test_gates", "test_x",
               '<skipped message="xfail-marked test passes unexpectedly" />')
    problems, _ = gate.check(write(tmp_path, suite(full_run([odd]), skipped=1)))
    assert any("skipped test(s)" in p for p in problems)


def _xml_escape(text: str) -> str:
    for raw, entity in (("&", "&amp;"), ("<", "&lt;"), (">", "&gt;"), ('"', "&quot;")):
        text = text.replace(raw, entity)
    return text


def test_nothing_written_inside_a_skipped_element_can_excuse_it(tmp_path: Path) -> None:
    """The verdict follows the count, never the wording.

    `skips = [s for s in skips if "WAIVED" not in s]` spliced into check()
    reads no environment and opens no second file. The only thing that
    catches it is refusing to let the element's own text change the answer,
    over a fixed table of plausible waiver words plus seeded random strings.
    """
    rng = random.Random(20260904)
    types = ["pytest.skip", "pytest.xfail", "", "custom.reason", "Skipped"]
    words = [
        "WAIVED", "waived by review", "approved", "allow", "ok", "expected",
        "TODO", "known issue", "temporary", "flaky", "", " ", "not yet",
        "& <tag> \"quoted\"", "x" * 500,
    ]
    pairs = [(kind, word) for kind in types for word in words]
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 _-.:/"
    for _ in range(40):
        pairs.append((rng.choice(types),
                      "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 40)))))
    for index, (kind, message) in enumerate(pairs):
        attribute = f' type="{_xml_escape(kind)}"' if kind else ""
        marker = f"test_flavour_{index}"
        odd = case("tests.test_gates", marker,
                   f'<skipped{attribute} message="{_xml_escape(message)}" />')
        evidence = write(tmp_path, suite(full_run([odd]), skipped=1), f"junit_{index}.xml")
        problems, summary = gate.check(evidence)
        assert problems, (kind, message)
        assert any(marker in problem for problem in problems), problems
        assert "0 skipped, 0 xfailed" not in summary


def test_the_verdict_follows_the_bytes_and_not_the_filename(tmp_path: Path) -> None:
    """Rename the evidence, get the same answer. The path is an input as surely
    as an environment variable is."""
    rng = random.Random(20260904)
    skip = case("tests.test_contract_strings", "test_x",
                '<skipped type="pytest.skip" message="not yet" />')
    document = suite(full_run([skip]), skipped=1)
    names = ["junit.xml", "results.xml", ".hidden.xml", "JUNIT.XML",
             "junit report.xml", "a" * 80 + ".xml", "junit", "junit.xml.bak"]
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
    for _ in range(24):
        drawn = "".join(rng.choice(alphabet) for _ in range(rng.randint(1, 30)))
        names.append(drawn if drawn.strip(".") else "x" + drawn)

    def verdict(directory: Path, name: str) -> list[str]:
        evidence = write(directory, document, name)
        problems, _ = gate.check(evidence)
        return [problem.replace(str(evidence), "<evidence>") for problem in problems]

    baseline_dir = tmp_path / "baseline"
    baseline_dir.mkdir()
    baseline = verdict(baseline_dir, "junit.xml")
    assert baseline
    for index, name in enumerate(names):
        directory = tmp_path / f"n{index}"
        directory.mkdir()
        assert verdict(directory, name) == baseline, name


def test_no_environment_variable_excuses_a_skip(tmp_path: Path) -> None:
    """Run as the workflow runs it — a subprocess with no package on the path —
    under every waiver-shaped variable this file can think of, and under an
    empty environment. Both answers must be red."""
    skip = case("tests.test_gates", "test_x",
                '<skipped type="pytest.skip" message="not yet" />')
    evidence = write(tmp_path, suite(full_run([skip]), skipped=1))
    hatches = {name: "1" for name in (
        "SKIP_OK", "ALLOW_SKIP", "SKIP_GATE", "IGNORE_SKIPS", "FORCE", "CI",
        "ALLOW_SKIPS", "PYTEST_ALLOW_SKIP", "GATE_WAIVE", "WAIVE",
    )}
    for environment in (dict(os.environ, **hatches), {"PATH": os.environ.get("PATH", "")}):
        completed = subprocess.run(
            [sys.executable, str(_SCRIPT), str(evidence)],
            capture_output=True, text=True, env=environment, cwd=tmp_path,
        )
        assert completed.returncode == 1, completed.stderr
        assert "1 skipped test(s)" in completed.stderr


def test_an_empty_run_fails(tmp_path: Path) -> None:
    """A run that recorded no testcases has verified nothing."""
    problems, _ = gate.check(write(tmp_path, suite([])))
    assert any("0 testcases recorded" in p for p in problems)
    assert gate.main(["check_test_results.py", str(write(tmp_path, suite([])))]) == 1


def test_a_report_that_contradicts_its_own_count_fails(tmp_path: Path) -> None:
    xml = suite(full_run()).replace(f'tests="{len(full_run())}"', 'tests="0"')
    problems, _ = gate.check(write(tmp_path, xml))
    assert any("totals tests=0" in p for p in problems)


def test_a_missing_file_fails(tmp_path: Path) -> None:
    problems, summary = gate.check(tmp_path / "never-written.xml")
    assert len(problems) == 1
    assert "does not exist" in problems[0]
    assert summary == ""


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ("<testsuites><testsuite tests=", "not parseable XML"),
        ("", "not parseable XML"),
        ("<html><body>ok</body></html>", "no <testsuite> element"),
    ],
)
def test_unreadable_evidence_fails(tmp_path: Path, payload: str, expected: str) -> None:
    problems, _ = gate.check(write(tmp_path, payload))
    assert any(expected in p for p in problems)


def test_a_deleted_required_module_fails(tmp_path: Path) -> None:
    """`git rm` of a hard-rule guard stays green under pytest. This is the
    assertion that turns it into a red build, and the reason the manifest is
    hard-coded rather than derived from what happens to be on disk."""
    dropped = "tests/test_no_secrets_committed.py"
    problems, _ = gate.check(write(tmp_path, suite(full_run(drop=dropped))))
    assert len(problems) == 1
    assert dropped in problems[0]
    assert "appears in no recorded classname" in problems[0]


def test_a_renamed_required_module_fails(tmp_path: Path) -> None:
    """Renaming is deleting with better manners, and a prefix match must not
    excuse it."""
    dropped = "tests/test_workflows.py"
    renamed = [case("tests.test_workflows_v2", "test_one"),
               case("tests.test_workflows_v2", "test_two")]
    problems, _ = gate.check(write(tmp_path, suite(full_run(renamed, drop=dropped))))
    assert len(problems) == 1
    assert dropped in problems[0]


def test_a_required_module_that_ran_nothing_fails(tmp_path: Path) -> None:
    """Present in the report with an empty classname — a collection error or a
    module-level skip — is still not a guard."""
    dropped = "tests/test_no_sibling_lab_import.py"
    stub = case("", gate.module_key(dropped),
                '<error message="collection failure">ImportError</error>')
    problems, _ = gate.check(write(tmp_path, suite(full_run([stub], drop=dropped), errors=1)))
    assert any(dropped in p and "contributed 0 tests" in p for p in problems)
    assert not any("appears in no recorded classname" in p for p in problems)
    assert any("errored test(s)" in p for p in problems)


def test_failures_and_errors_fail(tmp_path: Path) -> None:
    """A strict xpass arrives as <failure message="[XPASS(strict)] ...">."""
    bad = [
        case("tests.test_gates", "test_a", '<failure message="assert 1 == 2">x</failure>'),
        case("tests.test_gates", "test_b",
             '<failure message="[XPASS(strict)] fixed already">x</failure>'),
        case("tests.test_gates", "test_c", '<error message="teardown">x</error>'),
    ]
    problems, _ = gate.check(write(tmp_path, suite(full_run(bad), failures=2, errors=1)))
    assert any("2 failed test(s)" in p for p in problems)
    assert any("1 errored test(s)" in p for p in problems)
    assert any("XPASS(strict)" in p for p in problems)


def test_every_problem_is_reported_at_once(tmp_path: Path) -> None:
    mixed = [
        case("tests.test_gates", "test_s", '<skipped type="pytest.skip" message="m" />'),
        case("tests.test_gates", "test_x", '<skipped type="pytest.xfail" message="m" />'),
    ]
    problems, _ = gate.check(
        write(tmp_path, suite(full_run(mixed, drop="tests/test_contract_strings.py"), skipped=2))
    )
    assert len(problems) == 3


def test_module_key_maps_paths_to_the_dotted_form() -> None:
    assert gate.module_key("tests/test_contract_strings.py") == "tests.test_contract_strings"
    assert all(
        gate.module_key(m) != m and "/" not in gate.module_key(m)
        for m in gate.REQUIRED_MODULES
    )


def test_the_manifest_names_every_hard_rule_guard() -> None:
    """Shrinking REQUIRED_MODULES is the quiet way to make deleting a guard
    legal again, so the floor is asserted here rather than left to review."""
    for module in (
        "tests/test_no_secrets_committed.py",
        "tests/test_no_sibling_lab_import.py",
        "tests/test_contract_strings.py",
        "tests/test_league_registry_is_the_only_place.py",
        "tests/test_workflows.py",
        "tests/test_the_guards_exist.py",
        "tests/test_check_test_results.py",
        "tests/test_check_ledger_append_only.py",
    ):
        assert module in gate.REQUIRED_MODULES, module


def test_the_gate_against_a_real_junit_of_this_suite(tmp_path: Path) -> None:
    """Not a synthetic document: pytest's own junit writer, over a guard module
    of this suite, so the classname mapping is checked against what pytest
    actually writes and not against what this file believes it writes."""
    evidence = tmp_path / "real.xml"
    subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
         # --noconftest because the conftest hook refuses a narrowed session,
         # which is exactly what this subprocess is. That flag is banned from
         # CI by tests/test_workflows.py; here it is what lets one module run.
         "--noconftest", f"--junit-xml={evidence}",
         "tests/test_check_ledger_append_only.py"],
        cwd=_SCRIPT.parents[1], capture_output=True, text=True,
        env=dict(os.environ, PYTEST_ADDOPTS=""),
    )
    assert evidence.is_file()
    problems, _ = gate.check(evidence)
    absent = [m for m in gate.REQUIRED_MODULES if m != "tests/test_check_ledger_append_only.py"]
    # Every OTHER required module is missing from this narrowed run, and the
    # gate has to say so for each; the one that ran must NOT be reported.
    for module in absent:
        assert any(module in problem for problem in problems), module
    assert not any("tests/test_check_ledger_append_only.py" in problem for problem in problems)


def test_wrong_invocation_is_not_a_pass() -> None:
    assert gate.main(["check_test_results.py"]) == 2
    assert gate.main(["check_test_results.py", "a", "b"]) == 2


# --------------------------------------------------------------------------
# The evidence has to be THIS run's.
# --------------------------------------------------------------------------


def test_evidence_older_than_the_job_is_not_the_jobs_evidence(tmp_path: Path) -> None:
    """`pytest --version` exits 0 and writes no junit, so a junit left lying
    at the gated path is how a suite that never ran reports a pass. A report
    stamped hours ago did not come from the job reading it."""
    stale = (datetime.now().astimezone() - gate.MAXIMUM_EVIDENCE_AGE - timedelta(minutes=1)).isoformat()
    problems, _ = gate.check(write(tmp_path, suite(full_run(), timestamp=stale)))
    assert any("older than the" in p for p in problems), problems
    assert gate.main(["check_test_results.py", str(write(tmp_path, suite(full_run(), timestamp=stale)))]) == 1

    # ...and the same document one minute inside the window is a pass, so the
    # rule is a bound and not a blanket refusal.
    fresh = (datetime.now().astimezone() - gate.MAXIMUM_EVIDENCE_AGE + timedelta(minutes=1)).isoformat()
    assert gate.check(write(tmp_path, suite(full_run(), timestamp=fresh)))[0] == []


def test_evidence_that_cannot_be_dated_is_not_a_pass(tmp_path: Path) -> None:
    """Absence is never a pass, and neither is an unreadable stamp."""
    for timestamp, expected in (
        ("", "carries no `timestamp`"),
        ("not-a-date", "unreadable `timestamp`"),
        ("2026-13-45T99:99:99", "unreadable `timestamp`"),
    ):
        problems, _ = gate.check(write(tmp_path, suite(full_run(), timestamp=timestamp)))
        assert any(expected in p for p in problems), (timestamp, problems)


def test_evidence_stamped_in_the_future_is_refused(tmp_path: Path) -> None:
    """A forged timestamp is as easy to put ahead of the clock as behind it."""
    ahead = (datetime.now().astimezone() + gate.MAXIMUM_EVIDENCE_SKEW + timedelta(minutes=5)).isoformat()
    problems, _ = gate.check(write(tmp_path, suite(full_run(), timestamp=ahead)))
    assert any("in the future" in p for p in problems), problems
    # A clock a little fast is not a false red.
    near = (datetime.now().astimezone() + timedelta(minutes=5)).isoformat()
    assert gate.check(write(tmp_path, suite(full_run(), timestamp=near)))[0] == []


def test_a_naive_timestamp_is_read_as_local_time(tmp_path: Path) -> None:
    """Older pytest wrote no offset. That is a report to read, not to refuse."""
    naive = datetime.now().replace(microsecond=0).isoformat()
    assert gate.check(write(tmp_path, suite(full_run(), timestamp=naive)))[0] == []


# --------------------------------------------------------------------------
# The floor is per test, not per module.
# --------------------------------------------------------------------------


def test_one_deselected_guard_test_is_a_shortfall(tmp_path: Path) -> None:
    """The hole this closes, in the shape it was measured in.

    `--deselect tests/test_no_secrets_committed.py::test_env_file_is_never_tracked`
    — from pyproject addopts, from PYTEST_ADDOPTS, or from a -c config file —
    left the module contributing dozens of testcases, so every count that
    stopped at the module was satisfied. Only comparing against what the file
    DEFINES sees it.
    """
    module = "tests/test_no_secrets_committed.py"
    key = gate.module_key(module)
    cases = full_run()
    shortened = cases[:]
    for index, entry in enumerate(shortened):
        if f'classname="{key}"' in entry:
            del shortened[index]
            break
    else:  # pragma: no cover - the module is in the manifest by construction
        pytest.fail(f"no testcase for {module} in the fixture")

    assert gate.check(write(tmp_path, suite(cases)))[0] == []
    problems, _ = gate.check(write(tmp_path, suite(shortened)))
    assert any(module in p and "test function(s)" in p for p in problems), problems


def test_the_floor_is_a_floor_and_not_an_equality(tmp_path: Path) -> None:
    """Parametrisation multiplies one function into many testcases, so more
    than the count defined must stay a pass. `tests/test_workflows.py` has the
    widest margin of the eight required guards — it parametrises every rule
    over every workflow and every mutation over its rule — and the ratio moves
    with each rule and each mutation added, which is why it is not written
    down. `tests/test_contract_strings.py` parametrises nothing and so sits
    exactly ON its floor. The generous end is exercised below; the exact-on-floor
    end is exercised above, in test_one_deselected_guard_test_is_a_shortfall,
    whose control run builds exactly the defined count per module."""
    module = "tests/test_workflows.py"
    key = gate.module_key(module)
    generous = full_run([case(key, f"test_param_{i}") for i in range(200)])
    assert gate.check(write(tmp_path, suite(generous)))[0] == []


def test_an_unreadable_guard_source_is_not_a_pass(tmp_path: Path) -> None:
    """A floor that could not be measured has not been checked."""
    problems, _ = gate.check(write(tmp_path, suite(full_run())), source_root=tmp_path)
    assert len(problems) == len(gate.REQUIRED_MODULES)
    assert all("could not be read" in p for p in problems), problems


def test_the_gate_counts_test_functions_the_way_the_manifest_does() -> None:
    """Two counters, one rule. `tests/test_the_guards_exist.py` holds the same
    floor against the same files; if they ever disagreed, one of them would be
    flooring a module against a number the other does not recognise."""
    import test_the_guards_exist as manifest

    for module in gate.REQUIRED_MODULES:
        path = gate.REPOSITORY_ROOT / module
        assert gate.test_functions_in(path) == manifest.count_test_functions(path), module


def test_the_gates_counter_reads_a_tree_and_not_a_name(tmp_path: Path) -> None:
    hollow = tmp_path / "test_hollow.py"
    hollow.write_text('"""A guard in name only."""\n\ndef helper():\n    pass\n', encoding="utf-8")
    assert gate.test_functions_in(hollow) == 0
    real = tmp_path / "test_real.py"
    real.write_text(
        "def test_a(): pass\nclass TestB:\n    def test_b(self): pass\n"
        "async def test_c(): pass\n", encoding="utf-8",
    )
    assert gate.test_functions_in(real) == 3
    broken = tmp_path / "test_broken.py"
    broken.write_text("def test_a(:\n", encoding="utf-8")
    assert gate.test_functions_in(broken) is None
    assert gate.test_functions_in(tmp_path / "never_written.py") is None


# --------------------------------------------------------------------------
# Collection-phase skips: what pytest_runtest_logreport would never see.
# --------------------------------------------------------------------------


COLLECTION_SKIPS = {
    "module_level_skip": (
        "import pytest\n"
        'pytest.skip("the table lives outside the repo", allow_module_level=True)\n'
        "\n\ndef test_never_runs():\n    assert True\n"
    ),
    "module_level_importorskip": (
        "import pytest\n"
        'pytest.importorskip("a_module_this_lab_does_not_have")\n'
        "\n\ndef test_never_runs():\n    assert True\n"
    ),
}


@pytest.mark.parametrize("shape", sorted(COLLECTION_SKIPS), ids=sorted(COLLECTION_SKIPS))
def test_a_collection_phase_skip_reaches_the_gate(tmp_path: Path, shape: str) -> None:
    """Observed on a real tree, not asserted about the implementation.

    A module-level `pytest.skip(allow_module_level=True)` and a module-level
    `importorskip` never reach `pytest_runtest_logreport` — they arrive as
    CollectReports — so a skip gate written as a runtest hook cannot see
    either. This gate reads the junit file instead, and pytest's junit writer
    records a collection skip as a `<testcase>` carrying `<skipped>`. That is
    the reason this lab's gate survives the shape, and it is worth an
    observation rather than an argument: a real pytest writes a real report
    and the gate's exit code is read off it.

    Defect 7 was this exact shape — twenty permanent skips on a gitignored
    table, and the build green.
    """
    tree = tmp_path / "repo"
    (tree / "tests").mkdir(parents=True)
    (tree / "tests" / "test_fine.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    (tree / "tests" / "test_skipped.py").write_text(COLLECTION_SKIPS[shape], encoding="utf-8")
    evidence = tmp_path / "junit.xml"
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
         "--noconftest", f"--junit-xml={evidence}", "tests"],
        cwd=tree, capture_output=True, text=True,
        env=dict(os.environ, PYTEST_ADDOPTS=""),
    )
    # pytest itself is GREEN on this tree. That is the whole problem.
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert evidence.is_file()

    problems, _ = gate.check(evidence, source_root=tree)
    assert any("skipped test(s)" in p for p in problems), problems
    assert gate.main(["check_test_results.py", str(evidence)]) == 1
