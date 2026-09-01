"""The workflows parse, name what they must, and cannot leak a credential.

A workflow is code that runs unattended with a secret in scope. These checks
are cheap and the failures they catch are not: a YAML typo means the lab goes
quiet on a Sunday, and a `git add -A` on a working tree holding a staged price
file and a `.env` is how a credential reaches a public ref.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from football_betting_lab.config import PROJECT_ROOT


WORKFLOW_DIR = PROJECT_ROOT / ".github" / "workflows"
WORKFLOWS = sorted(WORKFLOW_DIR.glob("*.yml"))

#: Workflows that spend credits. Each needs a cap and manual control.
SPENDING = {
    "provider-retention-probe.yml",
    "provider-shadow.yml",
    "football-gameday-refresh.yml",
}


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _without_comments(path: Path) -> str:
    """The workflow's executable text, with comment lines removed.

    A scanner that flags its own needles reports a false positive forever and
    teaches everyone to ignore it. The gameday workflow carries a comment
    explaining *why* it does not use `git add -A`, and that comment made this
    file fail on the very rule it documents.
    """
    return "\n".join(
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("#")
    )


def test_there_are_workflows_to_check() -> None:
    assert WORKFLOWS


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_every_workflow_parses(path: Path) -> None:
    assert isinstance(_load(path), dict)


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_every_workflow_names_itself(path: Path) -> None:
    assert _load(path).get("name")


def test_the_gameday_workflow_keeps_its_contract_name() -> None:
    """Cooper's scheduled routines hard-code this. A rename does not look like
    a rename; it looks like the lab going quiet."""
    path = WORKFLOW_DIR / "football-gameday-refresh.yml"

    assert path.is_file()
    assert _load(path)["name"] == "Football Gameday Refresh"


@pytest.mark.parametrize(
    "path", [p for p in WORKFLOWS if p.name in SPENDING], ids=lambda p: p.name
)
def test_a_workflow_that_spends_credits_takes_a_cap(path: Path) -> None:
    text = _without_comments(path)

    assert "credit-cap" in text or "credit_cap" in text


@pytest.mark.parametrize(
    "path", [p for p in WORKFLOWS if p.name in SPENDING], ids=lambda p: p.name
)
def test_a_workflow_that_spends_credits_refuses_to_run_without_the_secret(
    path: Path,
) -> None:
    """Running without a credential is not a cheaper run; it is a run that
    fails halfway with a staged file half written."""
    text = _without_comments(path)

    assert "FOOTBALL_ODDS_API_KEY" in text
    assert "Nothing was requested" in text


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_no_workflow_stages_the_whole_working_tree(path: Path) -> None:
    """`git add -A` on a tree holding `data/staging/` and a `.env` is how a
    credential reaches a public ref. The card feed is built with plumbing, so
    only files named one at a time can reach it."""
    text = _without_comments(path)

    assert "git add -A" not in text
    assert "git add ." not in text


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_no_workflow_echoes_the_credential(path: Path) -> None:
    text = _without_comments(path)

    for pattern in ("echo $FOOTBALL", "echo ${FOOTBALL", "apiKey="):
        assert pattern not in text


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_no_workflow_passes_the_credential_as_an_argument(path: Path) -> None:
    """A process list is world-readable and CI logs echo commands."""
    text = _without_comments(path)

    assert "--api-key" not in text
    assert "--apikey" not in text


def test_only_the_gameday_workflow_may_write_to_the_repository() -> None:
    """The probe and the shadow run produce evidence. A workflow that can push
    is a workflow whose failure modes include rewriting the evidence."""
    for path in WORKFLOWS:
        permissions = _load(path).get("permissions") or {}
        if path.name == "football-gameday-refresh.yml":
            assert permissions.get("contents") == "write"
        else:
            assert permissions.get("contents") == "read", path.name


def test_the_probe_and_the_shadow_run_are_manual_only() -> None:
    """Neither has a schedule, and neither should get one: they spend credits
    and nothing about them needs to happen unattended."""
    for name in ("provider-retention-probe.yml", "provider-shadow.yml"):
        triggers = _load(WORKFLOW_DIR / name)[True]  # PyYAML reads `on:` as True
        assert "schedule" not in triggers, name
        assert "workflow_dispatch" in triggers, name


def test_the_gameday_workflow_runs_on_a_schedule_covering_the_season() -> None:
    """September to January. A schedule that stops in December stops the
    ledger in December, and the ledger is the product."""
    triggers = _load(WORKFLOW_DIR / "football-gameday-refresh.yml")[True]
    crons = [entry["cron"] for entry in triggers["schedule"]]

    assert crons
    for cron in crons:
        months = cron.split()[3]
        assert "9" in months and "12" in months and "1" in months


def test_the_comment_stripper_does_not_hide_a_real_command(tmp_path: Path) -> None:
    """Stripping comments must not become a way to stop seeing things.

    Only whole comment lines go. A real command with a trailing comment is
    still a real command and is still checked.
    """
    path = tmp_path / "w.yml"
    path.write_text(
        "# git add -A would be wrong\n          git add -A  # and this is real\n",
        encoding="utf-8",
    )

    stripped = _without_comments(path)

    assert stripped.count("git add -A") == 1


# -- a broken run has to reach a human ---------------------------------------


def test_the_gameday_workflow_posts_to_the_operating_home() -> None:
    """A workflow that fails silently looks exactly like a day with no
    football. The card-feed branch records the fault; nothing reads a branch
    unprompted."""
    text = _without_comments(WORKFLOW_DIR / "football-gameday-refresh.yml")

    assert "gh issue comment" in text
    assert "Run did not complete" in text


def test_the_operating_home_title_in_the_workflow_is_the_contract_string() -> None:
    """Posted to by title rather than by a hardcoded number, so the issue can
    be recreated without editing a workflow — which means the title has to
    match exactly, em dash included."""
    from tests.test_contract_strings import OPERATING_HOME_ISSUE

    text = (WORKFLOW_DIR / "football-gameday-refresh.yml").read_text(encoding="utf-8")

    assert OPERATING_HOME_ISSUE in text


#: The only workflows that may comment on the operating-home issue. Commenting
#: is a side effect on something a human watches, so the set is named here and
#: a new workflow has to be added deliberately rather than by inheriting a
#: permission block from whatever was copied.
MAY_COMMENT = {
    # Produces the card, and must report a degraded run.
    "football-gameday-refresh.yml",
    # The second, independent watchdog. It exists precisely for the case where
    # the gameday run never started, so it cannot report through that run — a
    # check that can only speak through the thing it checks is not a check.
    "weekly-ledger-check.yml",
}


def test_only_the_named_workflows_may_comment_on_the_operating_home() -> None:
    """Commenting is a side effect on something a human watches.

    This was "only the gameday workflow", and the weekly ledger check was added
    to the set deliberately: it reports on game days the gameday run never
    froze, which is the one failure it cannot report on itself. The set is
    explicit so the next workflow cannot acquire the permission by copying a
    permissions block.
    """
    for path in WORKFLOWS:
        permissions = _load(path).get("permissions") or {}
        expected = "write" if path.name in MAY_COMMENT else None
        assert permissions.get("issues") == expected, path.name


def test_the_degraded_path_runs_even_when_the_card_step_failed() -> None:
    """`if: always()` on the posting step is the whole point: the case that
    most needs reporting is the one where an earlier step died."""
    text = _without_comments(WORKFLOW_DIR / "football-gameday-refresh.yml")
    posting = text[text.index("Post to the operating home") :]

    assert "if: always()" in posting[:200]


def test_a_rehearsal_never_publishes_to_the_card_feed() -> None:
    """Publishing a rehearsal would set the feed's slate_date to the rehearsed
    day, and the "already published?" guard would then stand the real run down
    on the day it matters."""
    text = _without_comments(WORKFLOW_DIR / "football-gameday-refresh.yml")
    publish = text[text.index("Publish to the card-feed branch") :]

    assert "rehearsal_slate_date == ''" in publish[:200]


def test_the_purchase_reaches_back_through_previous_runs_for_its_cache() -> None:
    """`actions/download-artifact` only sees the current run's artifacts, so
    the obvious spelling restored nothing — and the next run then uploaded
    only what it had just bought, dropping every earlier snapshot. Bought
    prices are paid-for evidence and cannot be re-derived."""
    text = _without_comments(WORKFLOW_DIR / "historical-purchase.yml")

    assert "gh run download" in text
    assert "actions/download-artifact" not in text


def test_the_purchase_says_so_loudly_when_it_restored_nothing() -> None:
    """Silently re-buying is spending credits that were already spent once."""
    text = _without_comments(WORKFLOW_DIR / "historical-purchase.yml")

    assert "Nothing restored" in text


# -- a step may not force its own exit status ---------------------------------
#
# `|| true` has caused the same class of defect four times in this repository,
# twice inside the fix for a previous instance. The failure is always the same
# shape: a step that cannot fail reports success, and the steps below it run on
# whatever it left behind. The last one sat on the step that fetches the
# schedule the weekly watchdog compares the ledger against — so a failed fetch
# left a STALE calendar and the check reported the week intact.
#
# The rule is not "never write `|| true`". Tolerating an expected non-zero
# INSIDE a command is legitimate and this repository does it correctly: `grep`
# finding no snapshots yet is not an error. What is forbidden is forcing the
# exit status of the STEP, because that is the value `continue-on-error` exists
# to record and `steps.<id>.outcome` exists to read.

def _run_blocks(path: Path) -> list[tuple[str, dict]]:
    """(step name, step) for every step with a `run:`, across every job."""
    loaded = _load(path)
    out: list[tuple[str, dict]] = []
    for job in (loaded.get("jobs") or {}).values():
        for step in job.get("steps") or []:
            if isinstance(step, dict) and "run" in step:
                out.append((step.get("name", "<unnamed>"), step))
    return out


def _forces_its_own_exit_status(script: str) -> bool:
    """Does the step's LAST executed command swallow its own failure?

    Only the final command decides the step's exit status, and only a `|| true`
    that is not nested inside a substitution or a loop body applies to it. A
    crude substring search would flag the legitimate `$(... | grep ... || true)`
    and teach everyone to ignore this test.
    """
    meaningful = [
        line.strip()
        for line in script.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    if not meaningful:
        return False
    last = meaningful[-1]
    if not last.endswith("|| true"):
        return False
    # Nested inside a command substitution, so it guards that command's status
    # rather than the step's. `$(... || true)` is how you tolerate grep finding
    # nothing, and flagging it would make this test noise.
    if "$(" in last:
        return False
    # Closing a compound statement rather than being the final simple command.
    return not last.startswith(("done", "fi", "esac"))


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_no_step_forces_its_own_exit_status(path: Path) -> None:
    offenders = [
        name
        for name, step in _run_blocks(path)
        if _forces_its_own_exit_status(str(step["run"]))
    ]
    assert offenders == [], (
        f"{path.name}: these steps end in `|| true`, which makes them incapable "
        f"of failing and therefore incapable of being read: {offenders}. Use "
        "`continue-on-error: true` instead — it records the outcome as "
        "`steps.<id>.outcome` so a later gate can tell a broken job from a real "
        "finding. This family has cost this repository four defects."
    )


def test_the_weekly_check_can_tell_a_stale_calendar_from_a_lost_game_day() -> None:
    """The failure that looks like good news.

    A silently failed schedule fetch leaves the committed calendar in place, the
    coverage check runs against it and succeeds, and the week is reported
    intact. So the gate has to read the fetch's outcome, and has to read it
    before it reports anything clean.
    """
    text = _without_comments(WORKFLOW_DIR / "weekly-ledger-check.yml")
    assert "id: schedule" in text, (
        "The schedule fetch has no id, so no gate can read whether it worked."
    )
    assert "steps.schedule.outcome" in text, (
        "Nothing reads the schedule fetch's outcome. A stale calendar would be "
        "reported as an intact week."
    )
    assert text.count("SCHEDULE: ${{ steps.schedule.outcome }}") >= 2, (
        "Both the report step and the failing gate must read the schedule "
        "outcome; a report that says 'intact' while the gate fails is two "
        "alarms wearing one label."
    )


def test_the_step_status_rule_catches_the_defect_it_was_written_for() -> None:
    """The exact line that was in `weekly-ledger-check.yml`, and the legitimate
    uses that must not be flagged."""
    assert _forces_its_own_exit_status(
        "PYTHONPATH=src python scripts/fetch_football_data.py --only schedule || true"
    )
    assert _forces_its_own_exit_status('cat data/outputs/card.md >> "$SUMMARY" || true')
    # Legitimate: an expected non-zero tolerated inside a command substitution.
    assert not _forces_its_own_exit_status(
        "for f in $(git ls-tree -r --name-only tip | grep '^snapshots/' || true); do\n"
        "  echo \"$f\"\n"
        "done"
    )
    # Legitimate: the failure is handled by the lines that follow it.
    assert not _forces_its_own_exit_status(
        'git fetch --depth=1 "$REMOTE" tip 2>/dev/null || true\n'
        'if git cat-file -e tip:ledger.csv 2>/dev/null; then echo yes; fi'
    )
