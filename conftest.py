"""The session refuses to run when a hard-rule guard contributed nothing.

`git rm tests/test_no_secrets_committed.py` used to leave the suite green with
BETTER metrics — fewer tests, all passing — because pytest has no way to miss a
module it never saw. So did `-k "not secrets"`, `--deselect`, `--ignore`, a
positional path, and `PYTEST_ADDOPTS` carrying any of those: every one of them
runs a smaller suite and reports a smaller green.

This hook counts the collected items per required module AFTER every other
collection hook has deselected what it was going to (`trylast`, so `-k`, `-m`,
`--deselect` and `--lf` have already run), and exits the session with status 1
if any required module contributed zero. It is one of three layers and it is
the only one that sees the collection itself: `scripts/check_test_results.py`
reads the junit evidence after the run, and `tests/test_the_guards_exist.py`
asserts the modules are tracked and still define tests. Delete this file and
the other two still fire; edit the list here and
`test_the_guards_exist.py` fails on the disagreement.

The cost is deliberate and it is stated: a partial local run — `pytest
tests/test_gates.py` — is refused too. Run the whole suite; it takes seconds.
The only way to narrow a run is `--noconftest`, which is explicit, visible in
the command line, and banned from CI by `tests/test_workflows.py`. There is no
environment variable and no marker that relaxes this, because an escape hatch
the developer can reach is one the workflow can reach.
"""

from __future__ import annotations

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


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(session, config, items) -> None:
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
