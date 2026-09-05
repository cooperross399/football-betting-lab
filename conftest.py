"""The session refuses to run when a hard-rule guard contributed nothing.

`git rm tests/test_no_secrets_committed.py` used to leave the suite green with
BETTER metrics — fewer tests, all passing — because pytest has no way to miss a
module it never saw. So did `-k "not secrets"`, `--deselect`, `--ignore`, a
positional path, and `PYTEST_ADDOPTS` carrying any of those: every one of them
runs a smaller suite and reports a smaller green.

This hook counts the collected items per required module AFTER every other
collection hook has deselected what it was going to (`trylast`, so `-k`, `-m`,
`--deselect` and `--lf` have already run), and exits the session with status 1
if any required module contributed zero. It is one of four layers and it is
the only one that sees the collection itself: `scripts/check_test_results.py`
reads the junit evidence after the run, and `tests/test_the_guards_exist.py`
asserts the modules are tracked and still define tests. Delete this file and
the other two still fire; edit the list here and
`test_the_guards_exist.py` fails on the disagreement.

A MODULE FLOOR IS NOT A TEST FLOOR, and that was the hole. Deselecting ONE
test out of a guard leaves the module contributing dozens of items, so the
count above never notices. Measured on this repository before the fix:
`addopts = "--deselect tests/test_no_secrets_committed.py::test_env_file_is_never_tracked"`
in `pyproject.toml` produced `987 passed, 1 deselected`, pytest exit 0, and
`scripts/check_test_results.py` exit 0 — a guard test removed with three
layers green. `PYTEST_ADDOPTS` carrying the same string, and `-c ci.ini`
carrying it in an alternate config, each did the same.

Two things close it, and neither is a spelling check. `check_test_results.py`
now floors each required module per TEST, against the count `ast` reads out of
the file. And the second hook below asks pytest what it ACTUALLY RECEIVED —
`config.getoption("deselect")`, `"keyword"`, `"markexpr"`, `"ignore"`,
`"ignore_glob"`, the `addopts` in the resolved ini, and `PYTEST_ADDOPTS` in
the environment — rather than searching the command line for a spelling. A
narrowing assembled from pieces, arriving through a file this hook never
reads, still lands in `config` before collection starts, and that is where it
is read.

The cost is deliberate and it is stated: a partial local run — `pytest
tests/test_gates.py` — is refused too, and so is `pytest -k something`, now
that a keyword expression is refused whether or not it happens to zero a
guard. Run the whole suite; it takes under two minutes (1061 tests in 76.97s
in a throwaway clone, `PYTHONPATH=src PYTHONSAFEPATH=1 python -m pytest -q
-rs`, 2026-09-04).

Two things narrow a run past this hook, and both are edits to tracked files
rather than flags. `--noconftest` drops the hook entirely: explicit, visible
in the command line, and refused on the CI suite line by the whitelist in
`tests/test_workflows.py`. A `collect_ignore` written INTO this file, or into
a `tests/conftest.py`, drops a module before any hook counts it — measured on
a throwaway clone of this branch, `collect_ignore = ["tests/test_gates.py"]`
here gave `1040 passed` against a control of `1061`, twenty-one tests gone,
with pytest and the junit gate both exit 0. (A `tests/conftest.py` carrying
the same line IS caught, at `pytest=1 gate=1`, because it shadows the root
conftest this repository's manifest test imports — which is luck, not a rule.)
That one is caught for the eight required guards, by the count below and by
the per-test floor in `scripts/check_test_results.py`, and is not caught for
any other module; it is asserted open in
`tests/test_the_guards_exist.py::test_known_gaps_in_the_guard_floors`.

There is no environment variable and no marker that relaxes any of this,
because an escape hatch the developer can reach is one the workflow can reach.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

#: The modules that enforce a hard rule, each of which must contribute at
#: least one collected item to every session. `tests/test_the_guards_exist.py`
#: holds this exact tuple against its own copy and against
#: `scripts/check_test_results.REQUIRED_MODULES`, so the three cannot drift.
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


def guard_counts(items: list, rootpath: Path) -> dict[str, int]:
    """Collected items per required guard, keyed by repo-relative path."""
    counts = {module: 0 for module in REQUIRED_GUARDS}
    root = Path(rootpath).resolve()
    for item in items:
        try:
            relative = Path(str(item.path)).resolve().relative_to(root).as_posix()
        except (ValueError, OSError):
            continue
        if relative in counts:
            counts[relative] += 1
    return counts


#: Options pytest exposes that SHRINK a collection. Read off `config` — what
#: pytest received, after `addopts` from any ini file and after
#: `PYTEST_ADDOPTS` — rather than searched for in the command line, because
#: the command line is one of several places a narrowing can arrive from.
NARROWING_OPTIONS: tuple[str, ...] = (
    "deselect", "keyword", "markexpr", "ignore", "ignore_glob",
)


def narrowings_received(config) -> list[str]:
    """Every narrowing this session ACTUALLY got, whatever route it came by.

    Returns a list of `name=value` descriptions, empty when the session is a
    whole-suite run. `config.getoption` is the value pytest parsed, so a
    `--deselect` assembled in `pyproject.toml`, in a `-c` config file, or in
    `PYTEST_ADDOPTS` is reported identically to one typed on the command line.
    The ini `addopts` and the environment variable are read on their own as
    well: they are refused even when what they carry is harmless, because the
    question this repository has to be able to answer is "did anything reshape
    this run", and "yes, but I checked and it was fine" is the answer that
    stops being checked.
    """
    found: list[str] = []
    for option in NARROWING_OPTIONS:
        try:
            value = config.getoption(option)
        except (ValueError, AttributeError):
            continue
        if value:
            found.append(f"--{option.replace('_', '-')}={value!r}")
    # `config.getini("addopts")` is the resolved ini value and is what pytest
    # itself prepended to the command line. `config.inicfg` is the same thing
    # a layer down and is deprecated from pytest 8, so it is only reached when
    # `getini` is not available — an old pytest must not make this check
    # silently pass.
    ini_addopts: object = ""
    try:
        ini_addopts = config.getini("addopts")
    except (ValueError, AttributeError):
        try:
            ini_addopts = config.inicfg.get("addopts") or ""
        except AttributeError:
            ini_addopts = ""
    if ini_addopts:
        found.append(f"addopts in {getattr(config, 'inipath', 'the ini file')}={ini_addopts!r}")
    environment_addopts = os.environ.get("PYTEST_ADDOPTS", "").strip()
    if environment_addopts:
        found.append(f"PYTEST_ADDOPTS={environment_addopts!r}")
    return found


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(session, config, items) -> None:
    # The module floor first, so a narrowing that empties a guard still gets
    # the message that names the guard it emptied.
    counts = guard_counts(items, config.rootpath)
    missing = [module for module, count in counts.items() if count == 0]
    if missing:
        pytest.exit(
            "This session collected nothing from a hard-rule guard: "
            + ", ".join(missing)
            + ". A run that omits a guard is a smaller green, not a pass — "
            "whether the module was deleted, renamed, deselected with -k or "
            "--deselect, ignored, narrowed by a positional path, or narrowed "
            "through PYTEST_ADDOPTS. Run the whole suite.",
            returncode=1,
        )

    # ...then the narrowing that left every guard non-empty. Deselecting ONE
    # test out of a guard is invisible to the count above and was measured to
    # leave pytest, this hook and the junit gate all green.
    received = narrowings_received(config)
    if received:
        pytest.exit(
            "This session was narrowed before it ran: "
            + "; ".join(received)
            + ". Every guard still collected something, which is exactly why "
            "the count above did not object — a single deselected test leaves "
            "a module full. A narrowed run reports a smaller green, not a "
            "pass, and it does so whether the narrowing was typed on the "
            "command line, written into addopts, carried by a -c config file, "
            "or assembled in PYTEST_ADDOPTS. Run the whole suite.",
            returncode=1,
        )
