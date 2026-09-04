"""This lab may not reach into a sibling lab, and nothing was checking.

There are five betting labs in this account — NFL, NCAAF, NHL, EPL and college
basketball — one per sport, and they deliberately share no code. Machinery moves
between them by being **ported**: copied into the repository that uses it, where
it is visible and free to diverge as the sport demands.

That was a promise in a docstring until it was broken. The NCAAF lab's venv was
copied from the NFL lab's to save a few minutes of setup, and that installed
`football_betting_lab` into it as an editable package pointing at the sibling
repository. No line of code had to be written for the two labs to be coupled:
any module could have imported it and it would simply have worked, with no
error and no warning, through a path nobody reads.

Two things are asserted, because either alone is insufficient:

* no module here imports a sibling lab — catches a line someone writes;
* no sibling lab is importable from this environment — catches the environment
  making it possible in the first place.

The second is the one that actually bit. A test that only read source would have
passed all day.
"""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]

#: The other four labs. Named individually rather than derived, so a copied
#: venv from ANY of them fails the same way rather than only the one that
#: happened to cause this.
SIBLING_PACKAGES = ("cbb_betting_lab", "epl_betting_lab", "ncaaf_betting_lab", "nhl_betting_lab",)


def _python_files() -> list[Path]:
    keep: list[Path] = []
    for root in (PROJECT_ROOT / "src", PROJECT_ROOT / "scripts", PROJECT_ROOT / "tests"):
        if root.is_dir():
            keep.extend(
                p for p in root.rglob("*.py")
                if ".venv" not in p.parts and p.name != Path(__file__).name
            )
    return keep


def test_the_corpus_is_not_empty() -> None:
    """A glob that matches nothing passes every assertion below it."""
    files = _python_files()
    assert len(files) > 50, f"only {len(files)} Python files found; the roots are wrong"
    assert any(p.parts[-2:] == ("football_betting_lab", "config.py") for p in files)


def sibling_imports(paths: list[Path]) -> list[str]:
    """Every import of a sibling lab in `paths`, by file and line.

    A `SyntaxError` propagates: an unparseable module is a failure naming
    the file, never a module quietly skipped by a guard. It used to be caught
    and `continue`d past, which made a broken file the one file this guard
    would never read.
    """
    offenders: list[str] = []
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                if name.split(".")[0] in SIBLING_PACKAGES:
                    offenders.append(f"{path.name}:{node.lineno}: imports {name}")
    return offenders


def test_the_scanner_catches_a_sibling_import(tmp_path: Path) -> None:
    """The positive control: a guard that only ever asserts absence has
    never been seen to fire. Every spelling of the import, and a broken file."""
    spellings = {
        "plain.py": "import ncaaf_betting_lab\n",
        "aliased.py": "import nhl_betting_lab.config as cfg\n",
        "from.py": "from epl_betting_lab.models import x\n",
        "nested.py": "def f():\n    from cbb_betting_lab import y\n",
        "clean.py": "import football_betting_lab\nfrom pathlib import Path\n",
    }
    for name, body in spellings.items():
        (tmp_path / name).write_text(body, encoding="utf-8")
    found = sibling_imports([tmp_path / name for name in sorted(spellings)])
    assert found == [
        "aliased.py:1: imports nhl_betting_lab.config",
        "from.py:1: imports epl_betting_lab.models",
        "nested.py:2: imports cbb_betting_lab",
        "plain.py:1: imports ncaaf_betting_lab",
    ]
    broken = tmp_path / "broken.py"
    broken.write_text("import (\n", encoding="utf-8")
    with pytest.raises(SyntaxError):
        sibling_imports([broken])


def test_no_module_imports_a_sibling_lab() -> None:
    files = _python_files()
    assert files, "no Python files to scan; absence is never a pass"
    offenders = sibling_imports(files)
    assert not offenders, (
        "This lab imports a sibling lab. Machinery is shared by PORTING it "
        "here, visibly, never by coupling two repositories:\n  "
        + "\n  ".join(offenders)
    )


@pytest.mark.parametrize("package", SIBLING_PACKAGES)
def test_no_sibling_lab_is_even_importable(package: str) -> None:
    """The environment half, and the one that actually bit."""
    assert importlib.util.find_spec(package) is None, (
        f"{package} is importable from this environment. A copied venv or a "
        "stray editable install couples two labs through a path nobody reads. "
        f"Uninstall it: `.venv/bin/python -m pip uninstall "
        f"{package.replace('_', '-')}`."
    )


def test_this_lab_s_own_package_is_importable() -> None:
    """The positive control. A guard that passes because nothing is installed
    is not a guard, it is a broken environment."""
    assert importlib.util.find_spec("football_betting_lab") is not None
