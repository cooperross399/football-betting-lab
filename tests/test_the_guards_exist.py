"""The guard manifest: every hard-rule guard is tracked, still defines the
tests it defined, and cannot be dropped from a session without a visible edit.

The defect this closes was measured, not imagined: `git rm` of the secrets
guard and the sibling-import guard left the suite green with fewer tests and
a faster wall clock. pytest cannot report a module it never saw, and a linter
that greps for a file's name proves only that a file by that name exists.

Four layers, each proved to fire here:

* this module asserts each required guard is tracked by git AND still defines
  at least the number of `test_*` functions recorded in `GUARD_TEST_FLOORS`,
  by `ast.parse` — a file emptied to a docstring is as gone as a file deleted,
  and so is one quietly relieved of twenty-four of its twenty-nine tests;
* `conftest.py` refuses the whole session when a required module contributed
  zero collected items, which is what a rename, `-k`, `--deselect`,
  `--ignore`, a positional path and `PYTEST_ADDOPTS` all look like. That is
  OBSERVED below by running pytest in a subprocess under each of those and
  reading the exit code, not by inspecting the hook;
* `conftest.py` ALSO refuses a session that was narrowed without emptying
  anything — one deselected test out of a full module — by reading what
  `config` actually received rather than what the command line spelled. Also
  observed below;
* `scripts/check_test_results.py` reads the junit file the CI run wrote and
  floors each required module's testcases against the `test_*` functions its
  source defines.

Two more layers live here because the suite line can be defeated without
touching the workflow at all: no tracked file may be named `pytest.py`,
`coverage.py`, `sitecustomize.py` or `usercustomize.py`, and no directory
named `pytest` or `coverage` may sit at the root or on a PYTHONPATH entry the
workflow declares. Both were measured, not supposed.

The three manifests are held equal to each other, and this file is on all
three, so deleting it is a red build too. What is still open is in
`test_known_gaps_in_the_guard_floors`, asserted so it goes red when closed.
"""

from __future__ import annotations

import ast
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

import conftest

PROJECT_ROOT = Path(__file__).resolve().parents[1]

#: Written out rather than imported from conftest, so that editing the list
#: in conftest to drop a guard is a disagreement this file reports.
REQUIRED_GUARDS: tuple[str, ...] = (
    "tests/test_no_secrets_committed.py",
    "tests/test_no_sibling_lab_import.py",
    "tests/test_contract_strings.py",
    "tests/test_league_registry_is_the_only_place.py",
    "tests/test_workflows.py",
    "tests/test_the_guards_exist.py",
    "tests/test_check_test_results.py",
    "tests/test_check_ledger_append_only.py",
)

#: A guard that has shrunk below this many test functions has been edited
#: down, whatever its name still says.
MINIMUM_TESTS_PER_GUARD = 5

#: ...and a floor per guard, because a global minimum of five lets a
#: twenty-nine-test guard lose twenty-four of them in silence. Measured
#: 2026-09-04 by `count_test_functions` on each file; the numbers are a FLOOR,
#: so adding tests needs no edit here and removing one does.
#:
#: This closes a hole the per-test junit floor does not: `check_test_results.py`
#: compares what RAN against what the file DEFINES, so deleting a guard test
#: outright lowers both sides together. Measured on this branch before this
#: list existed — delete `test_env_file_is_never_tracked` from the secrets
#: guard, run the suite: one test fewer than the control, pytest exit 0, gate
#: exit 0, a guard test gone and nothing red. The delta is the finding; the
#: two pass counts moved the next time anyone added a test, which is why they
#: are not written here. With this list in place the same edit is caught at
#: pytest=1 gate=1.
#:
#: It is an append-only list in the ledger's sense rather than a wall: someone
#: who means to remove a guard test edits a number here, and that edit is a
#: line in the diff that says so. The failure this prevents is the silent one.
GUARD_TEST_FLOORS: dict[str, int] = {
    "tests/test_no_secrets_committed.py": 29,
    "tests/test_no_sibling_lab_import.py": 5,
    "tests/test_contract_strings.py": 10,
    "tests/test_league_registry_is_the_only_place.py": 8,
    "tests/test_workflows.py": 37,
    "tests/test_the_guards_exist.py": 21,
    "tests/test_check_test_results.py": 30,
    "tests/test_check_ledger_append_only.py": 24,
}


def _gate_manifest() -> tuple[str, ...]:
    script = PROJECT_ROOT / "scripts" / "check_test_results.py"
    spec = importlib.util.spec_from_file_location("check_test_results", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return tuple(module.REQUIRED_MODULES)


def count_test_functions(path: Path) -> int:
    """`def test_*` at module level and inside classes, by AST.

    A `SyntaxError` propagates: an unparseable guard is a failure naming the
    file, never a module quietly counted as defining nothing.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("test_"):
                found += 1
    return found


def test_the_three_manifests_agree() -> None:
    assert REQUIRED_GUARDS == conftest.REQUIRED_GUARDS
    assert REQUIRED_GUARDS == _gate_manifest()


def test_this_file_is_in_the_manifest() -> None:
    assert "tests/test_the_guards_exist.py" in REQUIRED_GUARDS


@pytest.mark.parametrize("module", REQUIRED_GUARDS)
def test_every_required_guard_is_tracked_by_git(module: str) -> None:
    """On disk is not enough: a guard that is present but untracked never
    reaches CI, which runs against the checkout and not the working tree."""
    completed = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", module],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, f"{module} is not tracked by git: {completed.stderr}"
    assert (PROJECT_ROOT / module).is_file()


@pytest.mark.parametrize("module", REQUIRED_GUARDS)
def test_every_required_guard_still_defines_tests(module: str) -> None:
    count = count_test_functions(PROJECT_ROOT / module)
    assert count >= MINIMUM_TESTS_PER_GUARD, (
        f"{module} defines {count} test functions; a guard edited down below "
        f"{MINIMUM_TESTS_PER_GUARD} has been hollowed out, whatever its name says."
    )


def test_every_guard_covers_the_same_ground_it_did() -> None:
    """The floor list, applied. A guard may grow; shrinking takes an edit here."""
    for module, floor in GUARD_TEST_FLOORS.items():
        count = count_test_functions(PROJECT_ROOT / module)
        assert count >= floor, (
            f"{module} defines {count} test functions and its recorded floor "
            f"is {floor}. Deleting a guard test lowers what the junit gate "
            "floors against too, so nothing else in this repository sees it. "
            "If the removal is deliberate, lower the number in "
            "GUARD_TEST_FLOORS in the same commit, where a reviewer will see it."
        )


def test_the_floor_list_and_the_manifest_are_the_same_list() -> None:
    """A guard with no floor is a guard that can be emptied to five tests."""
    assert tuple(GUARD_TEST_FLOORS) == REQUIRED_GUARDS
    assert all(floor >= MINIMUM_TESTS_PER_GUARD for floor in GUARD_TEST_FLOORS.values())


def test_the_floor_list_would_notice_a_deletion(tmp_path: Path) -> None:
    """The rule's proof, on a file it can actually mutate.

    `GUARD_TEST_FLOORS` is checked against tracked files, so the mutation is
    made on a copy: take a real guard, delete one test function from it, and
    the count drops below the recorded floor.
    """
    module = "tests/test_no_secrets_committed.py"
    source = (PROJECT_ROOT / module).read_text(encoding="utf-8")
    tree = ast.parse(source)
    victims = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    ]
    assert victims, module
    lines = source.splitlines(True)
    del lines[victims[0].lineno - 1: victims[0].end_lineno]
    shrunk = tmp_path / "shrunk.py"
    shrunk.write_text("".join(lines), encoding="utf-8")

    assert count_test_functions(PROJECT_ROOT / module) >= GUARD_TEST_FLOORS[module]
    assert count_test_functions(shrunk) < GUARD_TEST_FLOORS[module]


def test_the_counter_fires_on_a_hollowed_module(tmp_path: Path) -> None:
    hollow = tmp_path / "test_hollow.py"
    hollow.write_text('"""A guard in name only."""\n\ndef helper():\n    pass\n', encoding="utf-8")
    assert count_test_functions(hollow) == 0
    real = tmp_path / "test_real.py"
    real.write_text(
        "def test_a(): pass\nclass TestB:\n    def test_b(self): pass\n"
        "async def test_c(): pass\n",
        encoding="utf-8",
    )
    assert count_test_functions(real) == 3
    broken = tmp_path / "test_broken.py"
    broken.write_text("def test_a(:\n", encoding="utf-8")
    with pytest.raises(SyntaxError):
        count_test_functions(broken)


def _collect(*arguments: str, environment: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    """Run this repository's own collection in a subprocess.

    `--collect-only` is enough: `pytest_collection_modifyitems` runs on a
    collect-only session too, so the hook's verdict is observed without
    executing the suite.
    """
    env = dict(os.environ)
    env.pop("PYTEST_ADDOPTS", None)
    env.update(environment or {})
    return subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q",
         "-p", "no:cacheprovider", *arguments],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        env=env,
    )


def test_a_full_collection_is_accepted_by_the_hook() -> None:
    """The positive control: the hook must not refuse the run it protects."""
    completed = _collect()
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "collected nothing from a hard-rule guard" not in completed.stdout


NARROWINGS = {
    "ignore": ["--ignore=tests/test_no_secrets_committed.py"],
    "deselect": ["--deselect", "tests/test_no_sibling_lab_import.py"],
    "keyword": ["-k", "not test_workflows"],
    "positional": ["tests/test_gates.py"],
    "addopts": [],
}


@pytest.mark.parametrize("narrowing", sorted(NARROWINGS))
def test_the_hook_refuses_a_session_that_omits_a_guard(narrowing: str) -> None:
    """Observed, not inspected: each narrowing is run and its exit code read."""
    environment = (
        {"PYTEST_ADDOPTS": "--ignore=tests/test_the_guards_exist.py"}
        if narrowing == "addopts"
        else None
    )
    completed = _collect(*NARROWINGS[narrowing], environment=environment)
    assert completed.returncode == 1, (narrowing, completed.stdout, completed.stderr)
    assert "collected nothing from a hard-rule guard" in completed.stdout


def test_the_hook_names_the_module_it_missed() -> None:
    completed = _collect("--ignore=tests/test_contract_strings.py")
    assert completed.returncode == 1
    assert "tests/test_contract_strings.py" in completed.stdout
    assert "tests/test_workflows.py" not in completed.stdout.split("hard-rule guard:")[1].split(".")[0]


def test_guard_counts_reads_item_paths(tmp_path: Path) -> None:
    class Item:
        def __init__(self, path: Path) -> None:
            self.path = path

    root = tmp_path
    items = [Item(root / "tests" / "test_workflows.py"), Item(root / "tests" / "test_other.py")]
    counts = conftest.guard_counts(items, root)
    assert counts["tests/test_workflows.py"] == 1
    assert counts["tests/test_no_secrets_committed.py"] == 0


# --------------------------------------------------------------------------
# The suite line can be defeated without touching the workflow at all.
# --------------------------------------------------------------------------

#: A tracked file with one of these basenames is imported INSTEAD of the
#: library it is named after, because `python -m` puts the working directory —
#: and every PYTHONPATH entry — ahead of site-packages. `sitecustomize` and
#: `usercustomize` are worse: the interpreter imports them at startup, before
#: pytest exists, so one of them can set `PYTEST_ADDOPTS` and narrow the run
#: from inside the checkout.
FORBIDDEN_TRACKED_BASENAMES = frozenset({
    "pytest.py", "_pytest.py", "coverage.py", "sitecustomize.py",
    "usercustomize.py",
})

#: A directory by these names shadows the installed package the same way a
#: module does, and a directory is easier to miss in review than a file.
FORBIDDEN_SHADOW_DIRECTORIES = frozenset({"pytest", "coverage", "_pytest"})

WORKFLOW_DIR = PROJECT_ROOT / ".github" / "workflows"
REQUIRED_CHECK_WORKFLOW = WORKFLOW_DIR / "tests.yml"


def tracked_files() -> list[str]:
    completed = subprocess.run(
        ["git", "ls-files"], cwd=PROJECT_ROOT, capture_output=True, text=True,
    )
    assert completed.returncode == 0, (
        f"git ls-files failed: {completed.stderr}. A rule that could not run "
        "has not passed."
    )
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def declared_python_paths() -> list[str]:
    """Every directory `tests.yml` puts on PYTHONPATH, read from the YAML.

    Parsed rather than grepped, and read from the workflow rather than
    hard-coded here, so adding a second entry to PYTHONPATH extends what this
    rule covers instead of quietly escaping it.
    """
    import yaml

    document = yaml.safe_load(REQUIRED_CHECK_WORKFLOW.read_text(encoding="utf-8"))
    found: list[str] = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            environment = node.get("env")
            if isinstance(environment, dict):
                for key, value in environment.items():
                    if str(key).strip().upper() == "PYTHONPATH" and isinstance(value, str):
                        found.extend(part for part in value.split(":") if part.strip())
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(document)
    return found


def test_the_workflow_declares_a_pythonpath_this_rule_can_read() -> None:
    """The rule below is vacuous if nothing is on PYTHONPATH, so the premise
    is asserted rather than assumed: this workflow puts `src` there today."""
    assert "src" in declared_python_paths(), declared_python_paths()


@pytest.mark.parametrize("basename", sorted(FORBIDDEN_TRACKED_BASENAMES))
def test_no_tracked_file_shadows_the_suite(basename: str) -> None:
    """Measured, not imagined: with `src` on PYTHONPATH and the checkout on
    `sys.path`, a three-line tracked `pytest.py` at the repository root made
    `python -m pytest -q -rs --junit-xml=...` print one line, exit 0, and
    write no junit file at all. `src/sitecustomize.py` setting PYTEST_ADDOPTS
    ran before pytest started and deselected a guard test.

    The workflow's `PYTHONSAFEPATH: '1'` is the other half — it keeps the
    working directory off `sys.path` — and `tests/test_workflows.py` requires
    it. This rule holds even if that flag is ever lost, and it covers the
    PYTHONPATH entries, which PYTHONSAFEPATH does not touch.
    """
    offenders = [
        tracked for tracked in tracked_files()
        if Path(tracked).name == basename
    ]
    assert not offenders, (
        f"{offenders} is tracked. `python -m pytest` imports it instead of the "
        f"real {basename[:-3]}, and the suite line then runs a file this "
        "repository controls."
    )


def test_no_tracked_directory_shadows_the_suite() -> None:
    """The same defeat with a package instead of a module."""
    roots = [""] + declared_python_paths()
    tracked = tracked_files()
    offenders: list[str] = []
    for entry in roots:
        prefix = "" if entry in ("", ".") else entry.rstrip("/") + "/"
        for name in sorted(FORBIDDEN_SHADOW_DIRECTORIES):
            candidate = f"{prefix}{name}/"
            if any(path.startswith(candidate) for path in tracked):
                offenders.append(candidate)
    assert not offenders, (
        f"{offenders} sits at the root or on a PYTHONPATH entry this "
        "workflow declares, and shadows the installed package of the same name."
    )


def test_the_shadow_rule_would_see_a_shadow(tmp_path: Path) -> None:
    """The rule's own proof: it fires on a tree that carries the shadow.

    A rule over `git ls-files` cannot be mutated in place without committing
    the very file it forbids, so the matching is exercised against a synthetic
    listing instead.
    """
    listing = ["conftest.py", "src/football_betting_lab/config.py", "tests/test_gates.py"]
    assert not [p for p in listing if Path(p).name in FORBIDDEN_TRACKED_BASENAMES]
    shadowed = listing + ["pytest.py", "src/sitecustomize.py", "src/coverage/__init__.py"]
    assert sorted(
        Path(p).name for p in shadowed if Path(p).name in FORBIDDEN_TRACKED_BASENAMES
    ) == ["pytest.py", "sitecustomize.py"]
    assert any(p.startswith("src/coverage/") for p in shadowed)


# --------------------------------------------------------------------------
# A module floor is not a test floor.
# --------------------------------------------------------------------------

#: Each of these removes exactly ONE test from a guard module and leaves every
#: other layer green: the module still collects dozens of items, the junit
#: still records the module, and the file on disk still defines every test it
#: ever did. Measured on this repository before the fix: one deselected, a pass
#: count one below the control, pytest exit 0 and
#: `scripts/check_test_results.py` exit 0.
_SINGLE_TEST = "tests/test_no_secrets_committed.py::test_env_file_is_never_tracked"

SINGLE_TEST_NARROWINGS = {
    "deselect_on_the_command_line": (["--deselect", _SINGLE_TEST], None, None),
    "deselect_through_addopts": ([], None, f"--deselect {_SINGLE_TEST}"),
    "deselect_through_the_environment": ([], {"PYTEST_ADDOPTS": f"--deselect {_SINGLE_TEST}"}, None),
    "keyword_that_empties_nothing": (["-k", "not test_env_file_is_never_tracked"], None, None),
}


@pytest.mark.parametrize("narrowing", sorted(SINGLE_TEST_NARROWINGS))
def test_the_hook_refuses_a_session_narrowed_below_a_whole_module(
    narrowing: str, tmp_path: Path,
) -> None:
    """Observed by running it and reading the exit code, not by inspection.

    The `addopts` case writes a real config file and points pytest at it with
    `-c`, because that is the route the workflow linter cannot see: `-c` is
    banned from the CI suite line, but nothing stops an addopts landing in
    `pyproject.toml` itself, and the conftest reads what pytest RECEIVED
    rather than what the command line spelled.

    The `-c` case is refused by the OTHER layer and that is recorded rather
    than smoothed over: `-c` moves pytest's rootdir to the config file's
    directory, so every required guard's repo-relative path stops matching and
    the module floor fires first. Both messages are a refusal; the assertion
    is that the session did not run, and which layer said so is reported.
    """
    arguments, environment, addopts = SINGLE_TEST_NARROWINGS[narrowing]
    if addopts is not None:
        config = tmp_path / "narrowed.ini"
        config.write_text(
            "[pytest]\ntestpaths = tests\npythonpath = src\n"
            f"xfail_strict = true\naddopts = {addopts}\n",
            encoding="utf-8",
        )
        arguments = ["-c", str(config), *arguments]
    completed = _collect(*arguments, environment=environment)
    assert completed.returncode == 1, (narrowing, completed.stdout, completed.stderr)
    refusals = ("narrowed before it ran", "collected nothing from a hard-rule guard")
    assert any(phrase in completed.stdout for phrase in refusals), (narrowing, completed.stdout)


@pytest.mark.parametrize(
    "narrowing",
    ["deselect_on_the_command_line", "deselect_through_the_environment",
     "keyword_that_empties_nothing"],
)
def test_the_narrowing_layer_is_the_one_that_refuses_a_full_collection(narrowing: str) -> None:
    """The layer matters here, because these three leave every guard FULL.

    `--deselect` of one test, and a `-k` that excludes one test by name, both
    collect something from all eight required modules — so the module floor is
    satisfied and says nothing. If these were caught by the older message, the
    new layer would be untested and the hole would still be open.
    """
    arguments, environment, _ = SINGLE_TEST_NARROWINGS[narrowing]
    completed = _collect(*arguments, environment=environment)
    assert completed.returncode == 1, (narrowing, completed.stdout, completed.stderr)
    assert "narrowed before it ran" in completed.stdout, (narrowing, completed.stdout)
    assert "collected nothing from a hard-rule guard" not in completed.stdout


def test_the_narrowing_observation_reads_what_pytest_received() -> None:
    """The unit half: a stub config carrying each shape is described, and a
    session that received nothing is silent."""
    class Config:
        def __init__(self, options: dict, ini: dict) -> None:
            self._options = options
            self.inicfg = ini
            self.inipath = "stub.ini"

        def getoption(self, name: str):
            if name not in self._options:
                raise ValueError(name)
            return self._options[name]

    clean = Config({name: None for name in conftest.NARROWING_OPTIONS}, {})
    assert conftest.narrowings_received(clean) == []

    for option in conftest.NARROWING_OPTIONS:
        values = {name: None for name in conftest.NARROWING_OPTIONS}
        values[option] = ["something"]
        found = conftest.narrowings_received(Config(values, {}))
        assert len(found) == 1 and option.replace("_", "-") in found[0], (option, found)

    ini = Config({name: None for name in conftest.NARROWING_OPTIONS}, {"addopts": "-k fast"})
    assert any("addopts" in entry for entry in conftest.narrowings_received(ini))


def test_the_narrowing_observation_reads_the_environment(monkeypatch) -> None:
    class Config:
        inicfg: dict = {}
        inipath = "stub.ini"

        def getoption(self, name: str):
            return None

    monkeypatch.delenv("PYTEST_ADDOPTS", raising=False)
    assert conftest.narrowings_received(Config()) == []
    monkeypatch.setenv("PYTEST_ADDOPTS", "--deselect tests/test_gates.py::test_x")
    found = conftest.narrowings_received(Config())
    assert found and "PYTEST_ADDOPTS" in found[0]
    # A variable set to whitespace is not a narrowing, and must not be a false red.
    monkeypatch.setenv("PYTEST_ADDOPTS", "   ")
    assert conftest.narrowings_received(Config()) == []


def test_known_gaps_in_the_guard_floors(tmp_path: Path) -> None:
    """What still gets through, asserted OPEN so it goes red when closed.

    Each of these was run against this branch with the fixes in place, and
    what is recorded is what the run did rather than what it counted — the
    counts move with every test anyone adds, and a stale count in a file whose
    whole job is to be trusted is worse than no count.

    1. A `collect_ignore` in the ROOT `conftest.py`, naming a module that is
       not on the required list. Run in a throwaway clone of this branch: every
       test in the named module was dropped, pytest exit 0,
       `check_test_results.py` exit 0 — a smaller green, nothing red. Every
       floor in this repository is aimed at the eight hard-rule guards; a
       non-required module has no floor at all, and giving one to every module
       would mean a recorded count for every test file in the suite that
       changes on every commit. The mitigation is that the edit is a line in
       `conftest.py`, which is a file reviewers read.

    2. A guard test deleted outright, WITH the matching floor lowered in the
       same commit. `GUARD_TEST_FLOORS` cannot stop that and is not meant to:
       it converts a silent deletion into a visible one. The measurement that
       motivated it is in the list's own comment.

    3. A guard whose tests all run and all assert nothing. Every count here —
       collected items, recorded testcases, `test_*` functions — is a count.
       `assert True` satisfies all three, and no static rule distinguishes it
       from a real assertion. This is what the mutation lists in
       `tests/test_workflows.py` and `tests/test_check_test_results.py` are
       for, and they cover those two files rather than the suite.

    4. `--noconftest`, which drops this hook entirely. It is explicit, visible
       in the command line, and refused on the CI suite line by the whitelist
       in `tests/test_workflows.py`. A local run can still use it.
    """
    # 1. A root-conftest collect_ignore is invisible to every layer, shown by
    #    the layers themselves rather than asserted from memory: the required
    #    manifest is the only thing any floor covers.
    assert "tests/test_gates.py" not in REQUIRED_GUARDS
    assert "tests/test_gates.py" not in GUARD_TEST_FLOORS
    assert set(GUARD_TEST_FLOORS) == set(REQUIRED_GUARDS)
    every_test_module = sorted(
        path.name for path in (PROJECT_ROOT / "tests").glob("test_*.py")
    )
    assert len(every_test_module) > len(REQUIRED_GUARDS), (
        len(every_test_module), len(REQUIRED_GUARDS)
    )

    # 2. The floor is a floor, so lowering it is permitted by construction.
    lowered = dict(GUARD_TEST_FLOORS)
    lowered["tests/test_no_secrets_committed.py"] = 1
    assert count_test_functions(
        PROJECT_ROOT / "tests/test_no_secrets_committed.py"
    ) >= lowered["tests/test_no_secrets_committed.py"]

    # 3. A vacuous test counts exactly as much as a real one.
    vacuous = tmp_path / "test_vacuous.py"
    vacuous.write_text(
        "\n".join(f"def test_{index}():\n    assert True\n" for index in range(29)),
        encoding="utf-8",
    )
    assert count_test_functions(vacuous) == 29
    assert count_test_functions(vacuous) >= GUARD_TEST_FLOORS[
        "tests/test_no_secrets_committed.py"
    ]
