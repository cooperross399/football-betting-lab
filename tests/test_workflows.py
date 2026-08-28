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


def test_the_gameday_workflow_may_comment_but_the_others_may_not() -> None:
    """Commenting is a side effect on something a human watches. Only the run
    that produces the card needs it."""
    for path in WORKFLOWS:
        permissions = _load(path).get("permissions") or {}
        expected = "write" if path.name == "football-gameday-refresh.yml" else None
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
