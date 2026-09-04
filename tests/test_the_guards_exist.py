"""The guard manifest: every hard-rule guard is tracked, defines tests, and
cannot be dropped from a session.

The defect this closes was measured, not imagined: `git rm` of the secrets
guard and the sibling-import guard left the suite green with fewer tests and
a faster wall clock. pytest cannot report a module it never saw, and a linter
that greps for a file's name proves only that a file by that name exists.

Three layers, each proved to fire here:

* this module asserts each required guard is tracked by git AND still
  defines at least five test functions, by `ast.parse` — a file emptied to a
  docstring is as gone as a file deleted;
* `conftest.py` refuses the whole session when a required module contributed
  zero collected items, which is what a rename, `-k`, `--deselect`,
  `--ignore`, a positional path and `PYTEST_ADDOPTS` all look like. That is
  OBSERVED below by running pytest in a subprocess under each of those and
  reading the exit code, not by inspecting the hook;
* `scripts/check_test_results.py` reads the junit file the CI run wrote and
  fails on a required module with no recorded testcase.

The three lists are held equal to each other, and this file is on all three,
so deleting it is a red build too.
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
