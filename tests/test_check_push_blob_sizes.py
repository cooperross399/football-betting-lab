"""Fail loudly before `git push`, not at the remote.

`forward_evidence.csv` reached 136.75 MB on 2026-10-05 and GitHub rejected
the push with a bare "pre-receive hook declined", on a Monday with a
game day's opinions already frozen locally and nowhere to land. This is the
regression guard: `scripts/check_push_blob_sizes.py` must catch an oversized
file before the publish step ever calls `git hash-object` or `git push`.

Loaded by file path, not imported as a package, matching how the workflow
calls it and how `check_ledger_append_only.py`'s own tests load that script.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    name = "check_push_blob_sizes"
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


check = _load()


def test_a_file_at_github_s_real_failure_size_is_flagged(tmp_path: Path) -> None:
    """136.75 MB — the exact size that triggered the real rejection — must
    never again pass silently."""
    big = tmp_path / "forward_evidence.csv"
    big.write_bytes(b"0" * int(136.75 * 1_000_000))

    problems = check.oversized([big])

    assert problems == [(big, big.stat().st_size)]


def test_a_file_comfortably_under_the_margin_is_not_flagged(tmp_path: Path) -> None:
    small = tmp_path / "2026-09-13.csv"
    small.write_bytes(b"0" * 1_000)

    assert check.oversized([small]) == []


def test_a_file_exactly_at_the_margin_is_not_flagged(tmp_path: Path) -> None:
    """The boundary is `>`, not `>=`: a file exactly at the configured limit
    is not the one that breaks anything."""
    path = tmp_path / "at_limit.csv"
    path.write_bytes(b"0" * check.MAX_BYTES)

    assert check.oversized([path]) == []


def test_one_byte_over_the_margin_is_flagged(tmp_path: Path) -> None:
    path = tmp_path / "over_by_one.csv"
    path.write_bytes(b"0" * (check.MAX_BYTES + 1))

    assert check.oversized([path]) == [(path, check.MAX_BYTES + 1)]


def test_a_path_that_does_not_exist_is_silently_skipped(tmp_path: Path) -> None:
    """A shell glob with no matches expands to its own literal pattern
    unless `nullglob` is set; the workflow relies on that not crashing the
    check or being reported as oversized."""
    missing = tmp_path / "no-such-shard-*.csv"

    assert check.oversized([missing]) == []


def test_the_configured_margin_is_below_github_s_hard_limit() -> None:
    """GitHub's limit is 100.00 MB = 104,857,600 bytes. The margin exists so
    this fails inside CI before a file is close enough that one more
    settled day would cross the real wall unannounced."""
    assert 0 < check.MAX_BYTES < 104_857_600


def test_main_exits_nonzero_and_names_the_oversized_file(tmp_path: Path, capsys) -> None:
    big = tmp_path / "forward_evidence.csv"
    big.write_bytes(b"0" * (check.MAX_BYTES + 1))
    small = tmp_path / "card.md"
    small.write_bytes(b"ok")

    code = check.main([str(big), str(small)])

    assert code == 1
    captured = capsys.readouterr()
    assert str(big) in captured.err
    assert "104,857,600" in captured.err


def test_main_exits_zero_when_every_file_fits(tmp_path: Path, capsys) -> None:
    small = tmp_path / "2026-09-13.csv"
    small.write_bytes(b"0" * 1_000)

    code = check.main([str(small)])

    assert code == 0
    assert "1 file(s) checked" in capsys.readouterr().out


def test_main_with_no_arguments_is_a_usage_error_not_a_silent_pass() -> None:
    assert check.main([]) == 2


def test_main_tolerates_a_missing_path_among_real_ones(tmp_path: Path) -> None:
    small = tmp_path / "card.md"
    small.write_bytes(b"ok")
    missing = tmp_path / "does-not-exist.csv"

    assert check.main([str(small), str(missing)]) == 0
