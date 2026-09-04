"""The append-only gate, exercised without pushing a PR.

`.github/workflows/ledger-guard.yml` is the only place this script runs for
real, and a workflow can only be tested by merging it. So the comparison lives
in a script and the script's failures live here: every one of these cases is an
edit that reached `main` green before this round. The removal case is not
hypothetical — `scripts/record_experiments.py` loads and saves the same ledger
object to the same path, and `save()` used to measure its floor by re-reading
that path, so the runtime shrink guard compared n against n on every run and
could not fire. Eighteen hypotheses hand-deleted from the tracked ledger (53 ->
35) re-rendered clean and printed a smaller correction (x1.69 -> x1.63).

The tests that matter most are the equal-count ones. A gate that only counts
passes an edit that drops the failure and appends a replacement, and that edit
is the one someone would actually make.

`test_known_gaps_that_still_get_through` is the other half of that honesty. It
runs the script over the edits it still passes and asserts the exit code is 0,
so what this gate does not cover is a recorded fact that goes red when it
changes, rather than a sentence in a docstring that nobody re-checks.

This file is also the only thing holding the script's `ALPHA` and Bonferroni
factor against the package's. The workflow's re-render step runs
`scripts/record_experiments.py`, which imports the package and never reads the
script, so a value drifted in the script leaves that step green — see
`test_the_scripts_arithmetic_matches_the_package`.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

#: Loaded by path: `scripts/` is not a package and is not on `pythonpath`, and
#: the workflow invokes the file the same way — as a script, with no package
#: import available to it.
_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_ledger_append_only.py"
_spec = importlib.util.spec_from_file_location("check_ledger_append_only", _SCRIPT)
assert _spec is not None and _spec.loader is not None
check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check)

from football_betting_lab import experiment_ledger  # noqa: E402


def entry(
    name: str,
    *,
    search: str = "subgroup-search",
    seasons: tuple[int, ...] = (2023, 2024),
    tested_on: str = "2026-09-04",
    outcome: str = "no demonstrated edge",
) -> dict:
    return {
        "search": search,
        "name": name,
        "tested_on": tested_on,
        "seasons": list(seasons),
        "outcome": outcome,
    }


def write(path: Path, entries: list[dict]) -> Path:
    path.write_text(json.dumps({"hypotheses": entries}, indent=2) + "\n", encoding="utf-8")
    return path


def run(tmp_path: Path, base: list[dict] | None, head: list[dict]) -> int:
    head_path = write(tmp_path / "head.json", head)
    if base is None:
        return check.main(["--base-absent", "--head", str(head_path)])
    base_path = write(tmp_path / "base.json", base)
    return check.main(["--base", str(base_path), "--head", str(head_path)])


THREE = [entry("blowout risk"), entry("edge magnitude"), entry("odds range")]


def test_a_clean_append_passes(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    code = run(tmp_path, THREE, THREE + [entry("week of season")])

    assert code == 0
    out = capsys.readouterr().out
    assert "3 base hypotheses compared" in out


def test_the_first_line_carries_the_count_beside_the_factor(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """The workflow's Summarise step does `head -n 1` on this output, and the
    lab's rule is that no measured number travels without its sample size."""
    run(tmp_path, THREE, THREE)

    first = capsys.readouterr().out.splitlines()[0]
    assert "3 distinct hypotheses" in first
    # The literal, not `check.correction_factor(3)`: three distinct
    # hypotheses at ALPHA = 0.05 give 1.2214.
    assert "x1.22" in first


def test_the_scripts_arithmetic_matches_the_package() -> None:
    """The guard that makes the duplication safe.

    `check_ledger_append_only` restates `ALPHA` and the Bonferroni factor
    instead of importing them, because the workflow step runs the script
    without `PYTHONPATH=src`. Nothing else compares the two copies.
    """
    assert check.ALPHA == experiment_ledger.ALPHA

    empty = experiment_ledger.ExperimentLedger()
    assert empty.count == 0
    for count in range(0, 201):
        assert check.correction_factor(count) == empty.correction_factor(
            extra=count
        ), f"the two correction factors disagree at count={count}"


def test_the_audits_reproduction_is_now_caught(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """53 -> 35 by hand, re-rendered green. The exact shape the audit ran."""
    base = [entry(f"hypothesis {index}") for index in range(53)]
    head = base[:35]

    code = run(tmp_path, base, head)

    assert code == 1
    err = capsys.readouterr().err
    assert "falls from 53 entries to 35" in err
    assert err.count("removed from the ledger") == 18


def test_a_removal_fails_even_when_the_count_grew(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """Drop one, append two. `len(head) >= len(base)` holds and the ledger has
    still lost a degree of freedom it was corrected against."""
    head = THREE[:2] + [entry("week of season"), entry("position")]

    code = run(tmp_path, THREE, head)

    assert code == 1
    err = capsys.readouterr().err
    assert "removed from the ledger" in err
    assert "odds range" in err


def test_a_count_decrease_fails(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    code = run(tmp_path, THREE, THREE[:2])

    assert code == 1
    assert "falls from 3 entries to 2" in capsys.readouterr().err


def test_an_equal_count_outcome_swap_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """Same key, same count, a failure turned into a finding. A gate that only
    compares lengths reports green on this."""
    head = list(THREE)
    head[1] = entry("edge magnitude", outcome="+2.1% ROI, significant")

    code = run(tmp_path, THREE, head)

    assert code == 1
    err = capsys.readouterr().err
    assert "rewritten in the ledger" in err
    assert "'outcome'" in err


def test_an_equal_count_tested_on_swap_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """Re-dating a test is how an old look gets laundered into a fresh one."""
    head = list(THREE)
    head[0] = entry("blowout risk", tested_on="2026-10-01")

    code = run(tmp_path, THREE, head)

    assert code == 1
    err = capsys.readouterr().err
    assert "rewritten in the ledger" in err
    assert "'tested_on'" in err


@pytest.mark.parametrize("rewritten_at", [0, 1, 2])
def test_a_duplicate_key_rewrite_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture, rewritten_at: int
) -> None:
    """One base entry, three head copies, one of them rewritten.

    The count never falls and the key is still present, so both the shrink
    check and the removal check are satisfied. Only the loop over every match
    rejects this; where the rewrite sits is parametrised because a loop
    truncated to one end still catches the copy it happens to reach.
    """
    copies = [entry("blowout risk") for _ in range(3)]
    copies[rewritten_at] = entry("blowout risk", outcome="+2.1% ROI, significant")

    code = run(tmp_path, [entry("blowout risk")], copies)

    assert code == 1
    err = capsys.readouterr().err
    rewrites = [line for line in err.splitlines() if "rewritten in the ledger" in line]
    assert rewrites, err
    for line in rewrites:
        assert line.index("'no demonstrated edge'") < line.index(
            "'+2.1% ROI, significant'"
        )


def test_duplicating_an_entry_verbatim_is_not_itself_a_rewrite(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """The control: copies that agree are a redundant ledger, not a dishonest
    one, and they count as one degree of freedom."""
    code = run(tmp_path, [entry("blowout risk")], [entry("blowout risk") for _ in range(3)])

    assert code == 0
    out = capsys.readouterr().out
    assert "1 distinct hypotheses in the head ledger (3 entries)" in out
    assert "x1.00" in out


POISONED = [
    entry("edge magnitude"),
    entry("edge magnitude", outcome="+2.1% ROI, significant"),
]


@pytest.mark.parametrize("order", [(0, 1), (1, 0)])
def test_a_contradictory_pair_cannot_land(
    tmp_path: Path, capsys: pytest.CaptureFixture, order: tuple[int, int]
) -> None:
    """Two head records under one NEW key that disagree with each other.

    Nothing is removed, nothing is rewritten against the base, the count only
    grows — and a comparison that reduces the head to one record per key
    reports it as a clean append. Both orders, because the pass compares each
    later copy with the first.
    """
    head = [entry("blowout risk")] + [POISONED[i] for i in order]

    code = run(tmp_path, [entry("blowout risk")], head)

    assert code == 1
    err = capsys.readouterr().err
    assert "the head ledger contradicts itself" in err
    assert "subgroup-search / edge magnitude (2023, 2024)" in err
    assert "head entry 1" in err
    assert "head entry 2" in err


@pytest.mark.parametrize("survivor", [0, 1])
def test_an_inherited_contradiction_cannot_be_resolved_by_erasure(
    tmp_path: Path, capsys: pytest.CaptureFixture, survivor: int
) -> None:
    """Once a pair is in the base, deleting either copy is invisible to every
    other check, so the base is held to the same rule as the head."""
    base = [entry("blowout risk")] + POISONED
    head = [entry("blowout risk"), POISONED[survivor], dict(POISONED[survivor])]

    code = run(tmp_path, base, head)

    assert code == 1
    err = capsys.readouterr().err
    assert "the base ledger contradicts itself" in err


def test_a_contradiction_is_refused_on_the_first_commit_path(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """`--base-absent` is where a pair would be planted so it arrives as
    history. No base is not no check."""
    code = run(tmp_path, None, [entry("blowout risk")] + POISONED)

    assert code == 1
    captured = capsys.readouterr()
    assert "the head ledger contradicts itself" in captured.err
    assert "first-commit state" not in captured.out


def test_known_gaps_that_still_get_through(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """What this gate does NOT catch, asserted by running it rather than said.

    Every case below exits 0 today. None is a waiver — nothing here turns a
    red run green — they are the edges of the guarantee. If one starts
    failing, the gate got stronger: delete the case and move the sentence out
    of this list.
    """
    # 1. Contradictions are read on FROZEN_FIELDS only. Two records under one
    #    key that disagree about anything else are not seen.
    loud = entry("blowout risk")
    loud["games"] = "n = 3864"
    quiet = entry("blowout risk")
    quiet["games"] = "n = 12"
    assert run(tmp_path, [entry("blowout risk")], [loud, quiet]) == 0

    # 2. An appended hypothesis is taken on trust, whatever it claims to have
    #    found. Inventing a finding is not an edit to the base.
    assert run(
        tmp_path,
        THREE,
        THREE + [entry("week of season", outcome="+9.9% ROI, significant")],
    ) == 0

    # 3. `--base` is believed. Hand the same file to both flags and every
    #    comparison is satisfied by construction. Resolving the true base ref
    #    is the workflow's job, and its own hard stop when it cannot.
    invented = write(
        tmp_path / "head.json",
        [entry("blowout risk", outcome="+9.9% ROI, significant")],
    )
    assert check.main(["--base", str(invented), "--head", str(invented)]) == 0

    # 4. The merge key is literal, so the same test written two ways is two
    #    keys and the pair never meets. Not closed here on purpose: `key()`
    #    restates `Hypothesis.key()`, which is order-sensitive too.
    spans = entry("edge magnitude")
    reordered = entry(
        "edge magnitude", seasons=(2024, 2023), outcome="+2.1% ROI, significant"
    )
    assert run(tmp_path, [entry("blowout risk")],
               [entry("blowout risk"), spans, reordered]) == 0
    spaced = entry("edge magnitude ", outcome="+2.1% ROI, significant")
    assert run(tmp_path, [entry("blowout risk")],
               [entry("blowout risk"), spans, spaced]) == 0

    capsys.readouterr()


def test_a_missing_head_fails(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """An absent head is a broken check, not an empty ledger."""
    base_path = write(tmp_path / "base.json", THREE)

    code = check.main(["--base", str(base_path), "--head", str(tmp_path / "nowhere.json")])

    assert code == 1
    assert "does not exist" in capsys.readouterr().err


def test_a_blank_head_fails(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """A zero-byte file must not read as zero hypotheses."""
    head_path = tmp_path / "head.json"
    head_path.write_text("", encoding="utf-8")
    base_path = write(tmp_path / "base.json", THREE)

    code = check.main(["--base", str(base_path), "--head", str(head_path)])

    assert code == 1
    assert "not parseable JSON" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ("{not json", "not parseable JSON"),
        ('["a", "b"]', "not a JSON object"),
        ('{"hypotheses": {}}', "no 'hypotheses' list"),
        ('{"hypotheses": ["blowout risk"]}', "not an object"),
        ('{"entries": []}', "no 'hypotheses' list"),
        ('{"hypotheses": [{"search": "s"}]}', "missing 'name'"),
    ],
)
def test_a_malformed_head_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture, payload: str, expected: str
) -> None:
    head_path = tmp_path / "head.json"
    head_path.write_text(payload, encoding="utf-8")
    base_path = write(tmp_path / "base.json", THREE)

    code = check.main(["--base", str(base_path), "--head", str(head_path)])

    assert code == 1
    assert expected in capsys.readouterr().err


_ABSENT = object()


@pytest.mark.parametrize(
    ("seasons", "expected"),
    [
        pytest.param(_ABSENT, "is missing 'seasons'", id="absent"),
        pytest.param("2023", "has 'seasons' as a str, not a list", id="string"),
        pytest.param(None, "has 'seasons' as a NoneType, not a list", id="null"),
        pytest.param(["2023"], "has a season that is a str, not an int", id="str-season"),
        pytest.param([True], "has a season that is a bool, not an int", id="bool-season"),
    ],
)
def test_every_seasons_branch_refuses_its_own_bad_input(
    tmp_path: Path, capsys: pytest.CaptureFixture, seasons: object, expected: str
) -> None:
    """Seasons are half the merge key. A bool keys *identically* to 1, which is
    why `read_ledger` names bools instead of trusting `isinstance(x, int)`."""
    assert check.key({"search": "s", "name": "n", "seasons": [True]}) == check.key(
        {"search": "s", "name": "n", "seasons": [1]}
    )
    bad = entry("blowout risk")
    if seasons is _ABSENT:
        del bad["seasons"]
    else:
        bad["seasons"] = seasons
    head_path = write(tmp_path / "head.json", [bad])
    base_path = write(tmp_path / "base.json", THREE)

    code = check.main(["--base", str(base_path), "--head", str(head_path)])

    assert code == 1
    assert expected in capsys.readouterr().err


def test_base_absent_passes_on_a_valid_head(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    code = run(tmp_path, None, THREE)

    assert code == 0
    out = capsys.readouterr().out
    assert "3 distinct hypotheses" in out
    assert "first-commit state" in out


def test_a_base_that_compared_nothing_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """A base with no entries parses, keeps the count check happy, and lets the
    loop run zero times. Nothing was verified, so nothing may be reported."""
    code = run(tmp_path, [], THREE)

    assert code == 1
    assert "base was present but nothing was compared" in capsys.readouterr().err


def test_neither_origin_flag_is_refused(tmp_path: Path) -> None:
    """The base state must be stated, never defaulted."""
    head_path = write(tmp_path / "head.json", THREE)

    with pytest.raises(SystemExit) as excinfo:
        check.main(["--head", str(head_path)])

    assert excinfo.value.code == 2


@pytest.mark.parametrize("waiver", ["--force", "--allow", "--skip"])
def test_no_waiver_flag_exists(tmp_path: Path, waiver: str) -> None:
    head_path = write(tmp_path / "head.json", THREE[:2])
    base_path = write(tmp_path / "base.json", THREE)

    with pytest.raises(SystemExit) as excinfo:
        check.main(["--base", str(base_path), "--head", str(head_path), waiver])

    assert excinfo.value.code == 2


def test_no_environment_variable_turns_a_shrink_green(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in ("LEDGER_GUARD", "SKIP_LEDGER_CHECK", "FORCE", "CI", "ALLOW_SHRINK"):
        monkeypatch.setenv(name, "1")

    assert run(tmp_path, THREE, THREE[:2]) == 1


def test_the_real_ledger_passes_against_itself(capsys: pytest.CaptureFixture) -> None:
    """The tracked ledger has to be readable by its own guard; comparing it
    with itself is the append-of-nothing case a PR that does not touch it
    sees."""
    tracked = _SCRIPT.resolve().parents[1] / "data" / "outputs" / "experiment_ledger.json"

    code = check.main(["--base", str(tracked), "--head", str(tracked)])

    assert code == 0
    first = capsys.readouterr().out.splitlines()[0]
    assert "distinct hypotheses in the head ledger" in first
