"""The weekly watchdog reads the ledger where the card writes it.

From Week 1 of 2026 the Weekly Ledger Check failed every Tuesday with "A
scheduled game day has no frozen opinions. That evidence cannot be recovered."
Nothing had been lost. Four defects stacked:

* It restored the snapshots into `data/outputs/nfl_forward/snapshots/`, while
  the coverage check counts `priced_snapshots/` — so every played day had zero
  frozen rows beside thousands of settled ones, and read LOST.
* It restored the ledger into `data/outputs/nfl_forward/`, a folder only it
  ever wrote. The coverage check and the calibration refit read there; the
  evidence report reads `data/processed/`, where the card writes, and so in the
  same run it called a 132,856-row ledger empty while the refit folded in
  130,418 of its rows.
* It fetched only the schedule, so the freshness check graded six feeds that
  were never downloaded and read MISSING every week of the season.
* It chose its message by grepping the coverage report for "never frozen",
  which the report's own opening sentence contains. Any failure at all was
  announced as an unrecoverable loss.

These tests execute the restore blocks against a real git remote and hold the
destinations to the same functions the card and the checks call, so the next
disagreement fails here rather than on a Tuesday in October.
"""

from __future__ import annotations

import gzip
import importlib.util
import os
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest
import yaml

from football_betting_lab import config
from football_betting_lab import forward_evidence
from football_betting_lab.forward_evidence import ledger_path, snapshots_dir
from football_betting_lab.reports import slate_coverage

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
BASH = shutil.which("bash")
GIT = shutil.which("git")


def _load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    # A dataclass resolves its annotations through sys.modules.
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _steps(workflow: str) -> list[dict]:
    document = yaml.safe_load((WORKFLOWS / workflow).read_text(encoding="utf-8"))
    return [step for job in document["jobs"].values() for step in job["steps"]]


def _step(workflow: str, *, name_prefix: str = "", step_id: str = "") -> dict:
    for step in _steps(workflow):
        if step_id and step.get("id") == step_id:
            return step
        if name_prefix and str(step.get("name", "")).startswith(name_prefix):
            return step
    raise AssertionError(f"{workflow}: no step {name_prefix or step_id!r}")


def _render(block: str, values: dict[str, str]) -> str:
    for expression, value in values.items():
        block = block.replace("${{ " + expression + " }}", value)
    assert "${{" not in block, f"an expression was left unrendered:\n{block}"
    return block


# --------------------------------------------------------------------------
# One ledger path, one snapshot folder, for writer and every reader.
# --------------------------------------------------------------------------

def test_the_ledger_lives_where_the_card_has_always_written_it() -> None:
    """The helper did not move the file; it named where it already was."""
    assert ledger_path() == config.PROCESSED_DIR / forward_evidence.LEDGER_FILENAME
    assert snapshots_dir(config.ARCHIVE_DIR) == config.ARCHIVE_DIR / "priced_snapshots"


def test_the_coverage_check_reads_the_card_s_own_ledger_and_snapshots() -> None:
    coverage = _load_script("run_slate_coverage")
    assert coverage.default_inputs() == (snapshots_dir(config.ARCHIVE_DIR), ledger_path())


def test_the_calibration_refit_reads_the_card_s_ledger(tmp_path, monkeypatch) -> None:
    """Executed, not read: move where `ledger_path()` points and the refit follows.

    If the refit went back to building its own path, the redirected ledger
    would be invisible to it and this would fold in nothing.
    """
    monkeypatch.setattr(forward_evidence, "PROCESSED_DIR", tmp_path)
    pd.DataFrame({
        "snapshot_date": ["2026-09-13", "2026-09-14"],
        "market": ["spread", "spread"],
        "model_probability": [0.55, 0.45],
        "outcome": ["won", "lost"],
    }).to_csv(tmp_path / forward_evidence.LEDGER_FILENAME, index=False)
    refit = _load_script("fit_calibration")
    rows = refit._settled_forward_rows(None, before="2026-10-01")
    assert len(rows) == 2


def test_no_reader_builds_the_phantom_forward_folder() -> None:
    """`data/outputs/nfl_forward/` was written by the watchdog alone and read by
    two scripts that therefore saw nothing anywhere else. It must not return."""
    offenders = []
    for folder in ("scripts", "src"):
        for path in (ROOT / folder).rglob("*.py"):
            if 'output_name("forward", "")' in path.read_text(encoding="utf-8"):
                offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []


# --------------------------------------------------------------------------
# The restore blocks, executed against a real remote.
# --------------------------------------------------------------------------

LEDGER_CSV = (
    "snapshot_date,market,model_probability,outcome\n"
    "2026-09-13,spread,0.55,won\n"
    "2026-09-13,total_points,0.52,lost\n"
    "2026-09-14,spread,0.61,won\n"
)


SNAPSHOT_CSVS = {
    "2026-09-13.csv": "market,model_probability\nspread,0.55\ntotal_points,0.52\n",
    "2026-09-14.csv": "market,model_probability\nspread,0.61\n",
}


def _packed(text: str, parts: int) -> list[bytes]:
    """What the publish step writes: gzip without a timestamp, then split."""
    data = gzip.compress(text.encode("utf-8"), mtime=0)
    size = -(-len(data) // parts)
    return [data[i:i + size] for i in range(0, len(data), size)]


def _card_feed_remote(tmp_path: Path, layout: str = "plain") -> Path:
    """A bare repository whose card-feed branch looks like the live one.

    `plain` is every tip written before 2026-10-05; `packed` is the layout the
    publish step writes since GitHub refused a 136.75 MB plain ledger, with
    the ledger and one snapshot in more than one part so the reassembly is
    exercised rather than assumed."""
    work = tmp_path / "card-feed-work"
    (work / "snapshots").mkdir(parents=True)
    if layout == "plain":
        (work / "forward_evidence.csv").write_text(LEDGER_CSV, encoding="utf-8")
        for name, text in SNAPSHOT_CSVS.items():
            (work / "snapshots" / name).write_text(text, encoding="utf-8")
    else:
        (work / "ledger").mkdir()
        for i, part in enumerate(_packed(LEDGER_CSV, 3)):
            (work / "ledger" / f"forward_evidence.csv.gz.{i:03d}").write_bytes(part)
        for (name, text), parts in zip(SNAPSHOT_CSVS.items(), (2, 1)):
            for i, part in enumerate(_packed(text, parts)):
                (work / "snapshots" / f"{name}.gz.{i:03d}").write_bytes(part)
    env = _git_env(tmp_path)
    for args in (
        ["init", "-q", "-b", "card-feed"],
        ["add", "-A"],
        ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "card"],
    ):
        subprocess.run([GIT, *args], cwd=work, check=True, env=env)
    bare = tmp_path / "remote.git"
    subprocess.run([GIT, "clone", "-q", "--bare", str(work), str(bare)], check=True, env=env)
    return bare


def _git_env(tmp_path: Path, redirects: dict[str, str] | None = None) -> dict[str, str]:
    """Isolated git config; `redirects` rewrites a GitHub URL to a local path."""
    gitconfig = tmp_path / "gitconfig"
    if redirects:
        lines = []
        for url, target in redirects.items():
            lines += [f'[url "{target}"]', f"\tinsteadOf = {url}"]
        gitconfig.write_text("\n".join(lines) + "\n", encoding="utf-8")
    elif not gitconfig.exists():
        gitconfig.write_text("", encoding="utf-8")
    return {
        "PATH": os.environ["PATH"],
        "HOME": str(tmp_path),
        "GIT_CONFIG_GLOBAL": str(gitconfig),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0",
    }


def _restore(
    tmp_path: Path, workflow: str, remote_url: str, values: dict[str, str],
    layout: str = "plain", bare: Path | None = None,
) -> Path:
    bare = bare or _card_feed_remote(tmp_path, layout)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    env = _git_env(tmp_path, {remote_url: f"file://{bare}"})
    # The gameday restore runs inside the checkout; the weekly one makes its own.
    subprocess.run([GIT, "init", "-q"], cwd=workspace, check=True, env=env)
    step = _step(workflow, name_prefix="Restore the ledger")
    block = _render(step["run"], values)
    for key, value in (step.get("env") or {}).items():
        env[key] = _render(str(value), values)
    result = subprocess.run(
        [BASH, "-e", "-c", block], cwd=workspace, env=env,
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return workspace


def _where(workspace: Path, path: Path) -> Path:
    return workspace / path.relative_to(config.PROJECT_ROOT)


@pytest.mark.skipif(BASH is None or GIT is None, reason="needs bash and git")
@pytest.mark.parametrize("layout", ["plain", "packed"])
@pytest.mark.parametrize("workflow", ["weekly-ledger-check.yml", "football-gameday-refresh.yml"])
def test_every_restore_lands_where_the_code_reads(tmp_path, workflow, layout) -> None:
    token = "not-a-real-token"
    values = {
        "github.repository": "owner/repo",
        "secrets.GITHUB_TOKEN": token,
    }
    url = (
        f"https://x-access-token:{token}@github.com/owner/repo"
        if workflow == "weekly-ledger-check.yml"
        else "https://github.com/owner/repo"
    )
    workspace = _restore(tmp_path, workflow, url, values, layout)

    ledger = _where(workspace, ledger_path())
    assert ledger.is_file(), f"{workflow} did not put the ledger at {ledger_path()}"
    assert ledger.read_text(encoding="utf-8") == LEDGER_CSV
    folder = _where(workspace, snapshots_dir(config.ARCHIVE_DIR))
    assert sorted(p.name for p in folder.glob("*.csv")) == ["2026-09-13.csv", "2026-09-14.csv"]
    for name, text in SNAPSHOT_CSVS.items():
        assert (folder / name).read_text(encoding="utf-8") == text

    # And the check, reading what was restored, sees two frozen, settled days.
    result = slate_coverage.measure(
        scheduled={"2026-09-13": 13, "2026-09-14": 1},
        snapshot_rows=slate_coverage.snapshot_row_counts(folder),
        settled_rows=slate_coverage.settled_row_counts(pd.read_csv(ledger)),
        as_of=date(2026, 9, 22),
    )
    assert [d.state for d in result.days] == ["thin", "thin"]
    assert result.lost == [] and result.snapshot_missing == []


@pytest.mark.skipif(BASH is None or GIT is None, reason="needs bash and git")
@pytest.mark.parametrize("workflow", ["weekly-ledger-check.yml", "football-gameday-refresh.yml"])
def test_a_ledger_that_is_there_and_will_not_read_stops_the_run(tmp_path, workflow) -> None:
    """Falling through to "no ledger yet" would let the card publish a ledger
    of today's rows over the season's. A corrupt part must be a stop."""
    bare = _card_feed_remote(tmp_path, "packed")
    env = _git_env(tmp_path)
    clone = tmp_path / "corrupt"
    subprocess.run([GIT, "clone", "-q", "-b", "card-feed", str(bare), str(clone)], check=True, env=env)
    (clone / "ledger" / "forward_evidence.csv.gz.001").write_bytes(b"not gzip")
    for args in (
        ["add", "-A"],
        ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "corrupt"],
        ["push", "-q", "origin", "card-feed"],
    ):
        subprocess.run([GIT, *args], cwd=clone, check=True, env=env)
    token = "not-a-real-token"
    url = (
        f"https://x-access-token:{token}@github.com/owner/repo"
        if workflow == "weekly-ledger-check.yml"
        else "https://github.com/owner/repo"
    )
    with pytest.raises(AssertionError, match="could not be read"):
        _restore(
            tmp_path, workflow, url,
            {"github.repository": "owner/repo", "secrets.GITHUB_TOKEN": token},
            bare=bare,
        )


# --------------------------------------------------------------------------
# The publish step writes what GitHub accepts, and the restore reads it back.
# --------------------------------------------------------------------------

def _publish(
    tmp_path: Path, bare: Path, workspace: Path, part_bytes: int, ceiling: int | None = None,
) -> subprocess.CompletedProcess:
    step = _step("football-gameday-refresh.yml", name_prefix="Publish to the card-feed")
    token = "not-a-real-token"
    block = _render(step["run"], {
        "steps.card.outputs.decision || 'degraded'": "no-slate",
        "github.run_id": "1",
    })
    # The real part size is 45 MB; a test ledger that large would be slow, so
    # the size is shrunk to force several parts and prove they reassemble.
    assert "PART_BYTES=45000000" in block
    block = block.replace("PART_BYTES=45000000", f"PART_BYTES={part_bytes}")
    if ceiling is not None:
        assert block.count("$4 > 90000000") == 1
        block = block.replace("$4 > 90000000", f"$4 > {ceiling}")
    env = _git_env(tmp_path, {f"https://x-access-token:{token}@github.com/owner/repo": f"file://{bare}"})
    env["REMOTE"] = _render(str(step["env"]["REMOTE"]), {
        "secrets.GITHUB_TOKEN": token, "github.repository": "owner/repo",
    })
    return subprocess.run(
        [BASH, "-e", "-c", block], cwd=workspace, env=env,
        capture_output=True, text=True, timeout=60,
    )


@pytest.mark.skipif(BASH is None or GIT is None, reason="needs bash and git")
def test_the_published_ledger_is_split_and_reads_back_byte_for_byte(tmp_path) -> None:
    """On 2026-10-05 GitHub declined three pushes because the plain ledger was
    136.75 MB. The publish step now writes no plain ledger at all, writes
    parts no larger than its part size, and the restore step reads them back
    to exactly the bytes the card wrote."""
    bare = _card_feed_remote(tmp_path, "plain")
    workspace = tmp_path / "publisher"
    workspace.mkdir()
    subprocess.run([GIT, "init", "-q"], cwd=workspace, check=True, env=_git_env(tmp_path))
    ledger = _where(workspace, ledger_path())
    ledger.parent.mkdir(parents=True)
    # Varied rows, so gzip cannot shrink it below a few parts.
    rows = "".join(f"2026-10-0{1 + i % 5},spread,{(i * 7919) % 10007 / 10007:.6f},won\n" for i in range(20_000))
    text = LEDGER_CSV + rows
    ledger.write_text(text, encoding="utf-8")
    folder = _where(workspace, snapshots_dir(config.ARCHIVE_DIR))
    folder.mkdir(parents=True)
    (folder / "2026-10-04.csv").write_text(text, encoding="utf-8")

    result = _publish(tmp_path, bare, workspace, part_bytes=20_000)
    assert result.returncode == 0, result.stdout + result.stderr

    listing = subprocess.run(
        [GIT, "--git-dir", str(bare), "ls-tree", "-r", "-l", "card-feed"],
        check=True, capture_output=True, text=True, env=_git_env(tmp_path),
    ).stdout.splitlines()
    names = {line.split("\t")[1]: int(line.split()[3]) for line in listing}
    assert "forward_evidence.csv" not in names, "the plain ledger is what GitHub refused"
    ledger_parts = sorted(n for n in names if n.startswith("ledger/"))
    snapshot_parts = sorted(n for n in names if n.startswith("snapshots/2026-10-04"))
    assert len(ledger_parts) >= 3 and len(snapshot_parts) >= 3
    assert ledger_parts[0] == "ledger/forward_evidence.csv.gz.000"
    assert max(names.values()) <= 20_000

    reader = tmp_path / "reader"
    reader.mkdir()
    restored = _restore(
        reader, "football-gameday-refresh.yml", "https://github.com/owner/repo",
        {"github.repository": "owner/repo", "secrets.GITHUB_TOKEN": "x"}, bare=bare,
    )
    assert _where(restored, ledger_path()).read_text(encoding="utf-8") == text
    back = _where(restored, snapshots_dir(config.ARCHIVE_DIR))
    assert (back / "2026-10-04.csv").read_text(encoding="utf-8") == text


@pytest.mark.skipif(BASH is None or GIT is None, reason="needs bash and git")
def test_the_publish_step_refuses_a_file_github_would_refuse(tmp_path) -> None:
    """Checked before the push, so a failure names the file and the limit
    instead of arriving as a declined pre-receive hook. Observed with the
    ceiling lowered under a part, since a 90 MB fixture is not a unit test."""
    bare = _card_feed_remote(tmp_path, "plain")
    before = subprocess.run(
        [GIT, "--git-dir", str(bare), "rev-parse", "card-feed"],
        check=True, capture_output=True, text=True, env=_git_env(tmp_path),
    ).stdout
    workspace = tmp_path / "publisher"
    workspace.mkdir()
    subprocess.run([GIT, "init", "-q"], cwd=workspace, check=True, env=_git_env(tmp_path))
    ledger = _where(workspace, ledger_path())
    ledger.parent.mkdir(parents=True)
    ledger.write_text(LEDGER_CSV * 50, encoding="utf-8")

    result = _publish(tmp_path, bare, workspace, part_bytes=45_000_000, ceiling=10)
    assert result.returncode != 0
    assert "would be refused by GitHub's 100 MB limit" in result.stdout
    assert "ledger/forward_evidence.csv.gz.000" in result.stdout
    after = subprocess.run(
        [GIT, "--git-dir", str(bare), "rev-parse", "card-feed"],
        check=True, capture_output=True, text=True, env=_git_env(tmp_path),
    ).stdout
    assert after == before, "nothing may be pushed once the guard fires"


# --------------------------------------------------------------------------
# A settled day is never LOST.
# --------------------------------------------------------------------------

def test_a_day_with_settled_rows_and_no_snapshot_is_not_lost() -> None:
    result = slate_coverage.measure(
        scheduled={"2026-09-13": 13},
        snapshot_rows={},
        settled_rows={"2026-09-13": 54_625},
        as_of=date(2026, 9, 22),
    )
    (day,) = result.days
    assert day.state == "snapshot missing"
    assert result.lost == []
    assert result.snapshot_missing == [day]
    assert not result.is_intact
    text = slate_coverage.render(result, season=2026)
    assert "settled without a snapshot" in text
    assert "LOST" not in text.replace("not LOST", "")


def test_a_day_with_neither_snapshot_nor_settled_rows_is_still_lost() -> None:
    """The alarm this fix must not weaken."""
    result = slate_coverage.measure(
        scheduled={"2026-09-13": 13}, snapshot_rows={}, settled_rows={},
        as_of=date(2026, 9, 22),
    )
    assert [d.state for d in result.lost] == ["LOST"]


def test_the_coverage_script_exits_with_a_distinct_status_for_each_finding(tmp_path, monkeypatch) -> None:
    coverage = _load_script("run_slate_coverage")
    processed = tmp_path / "processed"
    processed.mkdir()
    pd.DataFrame({
        "season": [2026], "game_date": ["2026-09-13"], "week": [1],
    }).to_csv(processed / "team_games.csv", index=False)
    monkeypatch.setattr(coverage, "PROCESSED_DIR", processed)
    monkeypatch.setattr(coverage, "OUTPUTS_DIR", tmp_path / "outputs")
    archive = tmp_path / "archive"
    (archive / "priced_snapshots").mkdir(parents=True)
    argv = ["--season", "2026", "--as-of", "2026-09-22", "--archive-dir", str(archive)]

    assert coverage.main(argv) == 1, "no snapshot and no ledger: LOST"
    pd.DataFrame({"snapshot_date": ["2026-09-13"] * 30}).to_csv(
        archive / forward_evidence.LEDGER_FILENAME, index=False
    )
    assert coverage.main(argv) == 3, "settled without a snapshot is its own status"
    pd.DataFrame({"market": ["spread"] * 30}).to_csv(
        archive / "priced_snapshots" / "2026-09-13.csv", index=False
    )
    assert coverage.main(argv) == 0


# --------------------------------------------------------------------------
# The verdict comes from exit statuses, never from a phrase in a report.
# --------------------------------------------------------------------------

classifier = _load_script("classify_weekly_check")


@pytest.mark.parametrize(
    ("schedule", "feeds", "coverage_code", "freshness_code", "kinds"),
    [
        ("success", "success", "0", "0", []),
        ("success", "success", "1", "0", ["lost"]),
        ("success", "success", "3", "0", ["watchdog"]),
        ("success", "success", "2", "0", ["watchdog"]),
        ("success", "success", "", "0", ["watchdog"]),
        ("success", "success", "0", "1", ["stale"]),
        ("success", "failure", "0", "1", ["watchdog"]),
        ("success", "success", "0", "2", ["watchdog"]),
        ("success", "success", "1", "1", ["lost", "stale"]),
        ("failure", "success", "1", "1", ["watchdog"]),
        ("", "", "", "", ["watchdog"]),
    ],
)
def test_each_failure_is_named_for_what_it_is(schedule, feeds, coverage_code, freshness_code, kinds) -> None:
    findings = classifier.classify(
        schedule=schedule, feeds=feeds,
        coverage_code=coverage_code, freshness_code=freshness_code,
    )
    assert [f.kind for f in findings] == kinds


def test_only_a_lost_day_is_called_unrecoverable() -> None:
    """The 2026-09-15 and 09-22 message, on a week where only feeds were stale."""
    for coverage_code in ("0", "2", "3", ""):
        for freshness_code in ("0", "1", "2"):
            findings = classifier.classify(
                schedule="success", feeds="success",
                coverage_code=coverage_code, freshness_code=freshness_code,
            )
            assert not any("cannot be recovered" in f.message for f in findings)


def test_the_classifier_records_failed_and_lost_for_the_steps_that_read_it(tmp_path, monkeypatch, capsys) -> None:
    output = tmp_path / "github_output"
    output.write_text("", encoding="utf-8")
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    for key, value in {"SCHEDULE": "success", "FEEDS": "success",
                       "COVERAGE_CODE": "0", "FRESHNESS_CODE": "1"}.items():
        monkeypatch.setenv(key, value)
    assert classifier.main() == 0
    assert output.read_text(encoding="utf-8").splitlines() == ["failed=true", "lost=false"]
    assert "**stale**" in capsys.readouterr().out


# --------------------------------------------------------------------------
# The workflow wires those statuses through, and its last step is the gate.
# --------------------------------------------------------------------------

WORKFLOW = "weekly-ledger-check.yml"


def test_the_classifier_reads_every_status_it_names() -> None:
    verdict = _step(WORKFLOW, step_id="verdict")
    assert verdict.get("if") == "always()"
    assert verdict["env"] == {
        "SCHEDULE": "${{ steps.schedule.outcome }}",
        "FEEDS": "${{ steps.feeds.outcome }}",
        "COVERAGE_CODE": "${{ steps.coverage.outputs.code }}",
        "FRESHNESS_CODE": "${{ steps.freshness.outputs.code }}",
    }
    assert "classify_weekly_check.py" in verdict["run"]


def test_nothing_greps_a_report_for_its_verdict() -> None:
    for step in _steps(WORKFLOW):
        run = str(step.get("run", ""))
        assert "grep -qiE" not in run and "never frozen" not in run, step.get("name")


def test_the_report_and_the_gate_read_the_same_verdict() -> None:
    for prefix in ("Report to the operating home", "Fail the run"):
        step = _step(WORKFLOW, name_prefix=prefix)
        assert step["env"]["FAILED"] == "${{ steps.verdict.outputs.failed }}", prefix
        assert step.get("if") == "always()", prefix


def test_the_freshness_check_grades_feeds_this_job_fetched() -> None:
    feeds = _step(WORKFLOW, step_id="feeds")
    assert "--card-only" in feeds["run"]
    assert feeds.get("continue-on-error") is True
    names = [s.get("id") for s in _steps(WORKFLOW)]
    assert names.index("feeds") < names.index("freshness")


def _run_step(block: str, tmp_path: Path, env: dict[str, str]) -> subprocess.CompletedProcess:
    block = block.replace("/tmp/", f"{tmp_path}/")
    return subprocess.run(
        [BASH, "-e", "-c", block], cwd=tmp_path,
        env={"PATH": os.environ["PATH"], **env}, capture_output=True, text=True, timeout=60,
    )


@pytest.mark.skipif(BASH is None, reason="needs bash")
@pytest.mark.parametrize("step_id", ["coverage", "freshness"])
@pytest.mark.parametrize("code", [0, 1, 2, 3])
def test_each_check_records_its_own_exit_status(tmp_path, step_id, code) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake = fake_bin / "python"
    fake.write_text(f"#!/bin/sh\necho report\nexit {code}\n", encoding="utf-8")
    fake.chmod(0o755)
    output = tmp_path / "github_output"
    output.write_text("", encoding="utf-8")
    block = _render(_step(WORKFLOW, step_id=step_id)["run"], {"inputs.season || '2026'": "2026"})
    result = subprocess.run(
        [BASH, "-e", "-c", block.replace("/tmp/", f"{tmp_path}/")], cwd=tmp_path,
        env={"PATH": f"{fake_bin}:{os.environ['PATH']}", "GITHUB_OUTPUT": str(output)},
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == code
    assert output.read_text(encoding="utf-8") == f"code={code}\n"
    assert "report" in result.stdout


@pytest.mark.skipif(BASH is None, reason="needs bash")
def test_the_gate_fails_on_anything_but_an_explicit_clean_verdict(tmp_path) -> None:
    block = _step(WORKFLOW, name_prefix="Fail the run")["run"]
    verdict = tmp_path / "verdict.md"

    assert _run_step(block, tmp_path, {"FAILED": "false"}).returncode == 0

    for failed in ("", "maybe"):
        result = _run_step(block, tmp_path, {"FAILED": failed})
        assert result.returncode == 1
        assert "could not classify" in result.stdout

    verdict.write_text("- **stale**: At least one feed the card reads is stale.\n", encoding="utf-8")
    result = _run_step(block, tmp_path, {"FAILED": "true"})
    assert result.returncode == 1
    assert "::error::- **stale**" in result.stdout
    assert "cannot be recovered" not in result.stdout
