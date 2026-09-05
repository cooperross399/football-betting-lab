"""The workflows' invariants, parsed and executed rather than grepped.

The job branch protection gates on — the one named `Tests` — could be renamed,
emptied (`echo` in place of pytest), disabled (`if: false`,
`continue-on-error`), narrowed (`-x`, a positional path, `PYTEST_ADDOPTS`), or
have its failure swallowed (`if ! pytest; then echo; fi`), and the previous
version of this file stayed green through every one of those. Its rules were
substring searches over the YAML text, and a substring search proves only that
one spelling is absent. The `|| true` rule here was defeated four times in this
repository's own history by rewordings of the same swallow.

DO NOT MATCH TEXT. PARSE THE FILE AND EXECUTE THE THING.
--------------------------------------------------------
Every structural rule below reads `yaml.safe_load` and asserts on the tree.
Every behavioural rule writes the run block to a sandbox, replaces every
command word with a shell function of known exit status, runs it under
`bash -e` — the shell GitHub runs a `run:` block with — and reads what came
out: the exit code, which stubs were invoked with which arguments, what was
written to `$GITHUB_OUTPUT` and the step summary, what was printed. Nothing
real runs: PATH is an empty directory, and a command that reaches the shell
without a stub is reported as "this block was never modelled", which is a
failure of the check rather than a pass.

The required check is pinned three ways:

* STRUCTURE — exactly one job in the repository carries `name: Tests`; it
  takes no `if:`, no `needs:` and no `strategy:`, and NO OTHER JOB in
  `tests.yml` takes an `if:` either, because GitHub reports a
  conditionally-skipped required check as Success and `needs: a-skipped-job`
  is `if: false` with one more step of indirection. EVERY STEP of that job is
  held the same way and not only the two that run the chain, because a step
  GitHub skips does not fail its job either — graded at 5304f79, `if: false`
  on the compile step, on the checkout and on the upload was rejected by none
  of the twenty-nine rules that existed then. The clean-tree step and the
  append-only step must also be present, deleting either having passed every
  rule at 5304f79 as well. The pytest invocation is checked against a
  WHITELIST of the arguments it may carry rather than a blocklist of the ones
  it may not, because the flags nobody thought of were `--version`, `-h` and
  `--help`, each of which exits 0 having run nothing. The junit path written
  on the suite line must sit under `$RUNNER_TEMP` and match no tracked path,
  which stops a junit committed to the repository being gated out of the
  workspace; it does not stop a step that copies one onto the gated path
  through a shell variable, and that route is asserted open below rather than
  claimed shut. The gate line is pinned as a whole command and then EXECUTED
  under stubs, because a substring pin is satisfied by
  `: python scripts/check_test_results.py <path>`. `PYTEST_ADDOPTS` appears
  in no `env:` and no run block; nothing rebinds `PATH` or `PYTHONHOME`; the
  `pull_request` trigger carries no `paths:`, `paths-ignore:` or `branches:`;
  and the junit path pytest writes is the path the gate reads, with no step
  in between NAMING it.
* EXECUTION — every run block in `tests.yml` and `ledger-guard.yml` is run
  with every command failing, and then with each failing alone, and the block
  must exit non-zero every time a top-level command failed. That is what
  catches `set +e`, `trap 'exit 0' ERR`, `if cmd; then ok; else warn; fi`,
  and every future rewording.
* PROOF — each rule is a `check_*` function aimed at a synthetic workflow
  built to break it, and asserted to REJECT. A linter nobody has watched fail
  is a linter that might not work.

The operational workflows — the card, the purchase, the probe, the shadow, the
quota and the weekly check — are held to the rules the old file held them to,
by observation instead of by grep: the credential is planted as a canary in
the environment and asserted absent from every stdout, stderr, runner file
and stub argument; the "refuse to run without the secret" step is run with the
variable empty and must exit non-zero before invoking python; and a step may
not force its own exit status, observed by failing the last command that ran
at top level and demanding the step fail with it.

What still gets through is in `test_the_disclosed_holes_are_real`, asserted
open so it goes red the day it is closed.
"""

from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable, Iterator, NamedTuple

import pytest
import yaml

from football_betting_lab.config import PROJECT_ROOT


WORKFLOW_DIR = PROJECT_ROOT / ".github" / "workflows"

#: The status check branch protection requires on `main`, by the name GitHub
#: matches it under — the JOB's `name:`. Read back off the protection rule
#: with `gh api repos/<owner>/<repo>/branches/main/protection` on 2026-09-05:
#: required contexts `['Tests']`, `enforce_admins` true, force-pushes and
#: deletions refused, on a public repository. If that rule changes, this
#: changes with it — nothing in this file can see the change happen.
REQUIRED_CHECK_CONTEXT = "Tests"
REQUIRED_CHECK_WORKFLOW = "tests.yml"

#: The two workflows whose green tick is evidence that something ran, and
#: which are therefore held to the full swallow rule and the no-secret rule.
EVIDENCE_WORKFLOWS = frozenset({"tests.yml", "ledger-guard.yml"})

#: The junit gate's file name; the evidence chain runs pytest -> this.
GATE_SCRIPT = "check_test_results.py"

#: The provider credential's name. It may be bound into an `env:` by an
#: operational workflow, from the secrets context and nowhere else, and it
#: may never reach a log, a runner file, or a command-line argument.
CREDENTIAL_NAMES = frozenset({"FOOTBALL_ODDS_API_KEY"})

#: What the harness plants under the credential's name and under every
#: `${{ secrets.* }}` expression. Not 32 hex characters and not a placeholder
#: word, so the secrets guard neither flags it nor waves it through.
CANARY = "canary-planted-by-test-workflows-7k2q9"

#: Workflows that spend credits. Each needs a cap and manual control.
SPENDING = {
    "provider-retention-probe.yml",
    "provider-shadow.yml",
    "football-gameday-refresh.yml",
}

#: The only workflows that may comment on the operating-home issue.
MAY_COMMENT = {"football-gameday-refresh.yml", "weekly-ledger-check.yml"}

#: The only workflow that may write to the repository (the card feed).
MAY_WRITE_CONTENTS = {"football-gameday-refresh.yml"}


def workflow_files_in(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(
        path for path in directory.iterdir()
        if path.is_file() and path.suffix in {".yml", ".yaml"}
    )


WORKFLOWS = workflow_files_in(WORKFLOW_DIR)
every_workflow = pytest.mark.parametrize("path", WORKFLOWS, ids=[p.name for p in WORKFLOWS])
evidence_workflows = pytest.mark.parametrize(
    "path", [p for p in WORKFLOWS if p.name in EVIDENCE_WORKFLOWS],
    ids=[p.name for p in WORKFLOWS if p.name in EVIDENCE_WORKFLOWS],
)


def load(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def triggers(document: Any) -> Any:
    """The `on:` block. Bare `on` is a YAML 1.1 boolean, so `safe_load` files
    it under the key `True`; a quoted `"on"` lands under `"on"`."""
    if isinstance(document, dict):
        if "on" in document:
            return document["on"]
        if True in document:
            return document[True]
    return None


def mappings(node: Any) -> Iterator[dict]:
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from mappings(value)
    elif isinstance(node, list):
        for item in node:
            yield from mappings(item)


def jobs_of(document: Any) -> dict[str, dict]:
    jobs = document.get("jobs") if isinstance(document, dict) else None
    return {k: v for k, v in jobs.items() if isinstance(v, dict)} if isinstance(jobs, dict) else {}


def steps_of(job: dict) -> list[dict]:
    steps = job.get("steps")
    return [s for s in steps if isinstance(s, dict)] if isinstance(steps, list) else []


def steps_using(document: Any, action: str) -> Iterator[dict]:
    for mapping in mappings(document):
        uses = mapping.get("uses")
        if isinstance(uses, str) and uses.split("@", 1)[0] == action:
            yield mapping


def run_blocks(document: Any) -> Iterator[tuple[str, str]]:
    for mapping in mappings(document):
        command = mapping.get("run")
        if isinstance(command, str):
            yield str(mapping.get("name", "<unnamed step>")), command


# --------------------------------------------------------------------------
# Textual nets. Each is a second belt beside an executed rule, kept because
# execution has blind spots of its own (a failure inside `$(...)` or a
# pipeline element is invisible to errexit).
# --------------------------------------------------------------------------

SECRET_REFERENCE = re.compile(r"(?i)\bsecrets\s*[.\[)]")
GITHUB_EXPRESSION = re.compile(r"(?s)\$\{\{.*?\}\}")
SECRETS_WORD = re.compile(r"(?i)\bsecrets\b")
NONZERO_EXIT = re.compile(r"\bexit\s+[1-9]")
CONDITION = re.compile(r"^\s*(?:if|elif|while|until)\b")
DISABLES_ERREXIT = re.compile(
    r"\bset\b[^;&|]*\+(?:[a-z]*e[a-z]*\b|o\s+(?:errexit|pipefail)\b)"
)
ENABLES_PIPEFAIL = re.compile(r"^\s*set\b[^;&|]*-[a-zA-Z]*o\s+pipefail\b")
DISABLES_PIPEFAIL = re.compile(r"\bset\b[^;&|]*\+o?\s*pipefail\b")
PIPELINE = re.compile(r"(?<!\|)\|(?!\|)")
PROCESS_SUBSTITUTION = re.compile(r"[<>]\(")
BACKGROUND = re.compile(r"(?<![&>])&(?![&>])")
ASYNC_LAUNCHER = re.compile(r"\b(?:setsid|coproc|nohup)\b")
CONTINUATION = re.compile(r"(?:\\|\|\||&&|\|)$")

#: pytest flags that stop the run early, select a subset, reconfigure the run
#: (`-c`, `-o`, `--confcutdir` decide `testpaths`), disarm the gate
#: (`--runxfail`), or drop the conftest whose collection hook refuses a
#: narrowed session (`--noconftest`, `-p`).
NARROWING_PYTEST_LONG_FLAGS = frozenset({
    "--maxfail", "--ignore", "--ignore-glob", "--deselect", "--exitfirst",
    "--override-ini", "--config-file", "--confcutdir", "--runxfail",
    "--noconftest", "--collect-only", "--co", "--last-failed", "--lf",
    "--stepwise", "--sw", "--stepwise-skip", "--sw-skip", "--stepwise-reset",
    "--sw-reset", "--rootdir", "--keyword",
})
#: `-x`, `-k`, `-m`, `-o`, `-c`, `-p` matched as letters in a short cluster.
NARROWING_PYTEST_SHORT_FLAGS = frozenset("xkmocp")

#: THE WHITELIST. A blocklist of narrowing flags proves only that the flags
#: somebody thought of are absent, and the flags nobody thought of were
#: `--version`, `-h` and `--help`: each makes pytest print and EXIT 0 without
#: running a test or writing a junit file, which is a green suite step that
#: ran nothing. So the suite line may carry these arguments and no others.
#: `-q` for a readable log, `-rs` so the reason for each skip sits beside the
#: gate that fails on it, and the junit flag the gate reads.
PERMITTED_PYTEST_FLAGS = frozenset({"-q", "-rs"})
#: ...plus exactly one of these, written `--flag=<path>`.
PERMITTED_PYTEST_VALUE_FLAGS = frozenset({"--junit-xml", "--junitxml"})

#: The junit file must be written where the workspace is not: a path inside
#: the checkout can be TRACKED, and a tracked junit at the gated path is read
#: by the gate as this run's evidence and by the clean-tree check as an
#: unmodified file. Both spellings the runner accepts.
RUNNER_TEMP_PREFIXES = ("$RUNNER_TEMP/", "${{ runner.temp }}/", "${{runner.temp}}/")

#: The environment variable that keeps the working directory OFF `sys.path`.
#: Without it `python -m pytest` puts the checkout first, so a tracked
#: `pytest.py` at the root shadows the suite.
SAFE_PATH_VARIABLE = "PYTHONSAFEPATH"
PYTEST_ADDOPTS = "PYTEST_ADDOPTS"
PYTEST_ADDOPTS_TOKEN = re.compile(r"(?i)\bPYTEST_ADDOPTS\b")
JUNIT_FLAGS = frozenset({"--junit-xml", "--junitxml"})
BRACED_VARIABLE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}(?![A-Za-z0-9_])")
SHELL_OPERATOR_TOKENS = frozenset(
    {"|", "||", "&&", "&", ";", ";;", ">", ">>", "<", "<<", "2>", "&>", "(", ")"}
)
COMMAND_TERMINATORS = frozenset(";|&<>(){}\n")
SAFE_SHELLS = frozenset({"bash", "sh"})
PERMITTED_CHAIN_CONDITION = "always()"

#: The one NARROWING condition permitted anywhere in the required job, and it
#: is permitted on one step: the append-only comparison reads the pull
#: request's base commit, and a push has no base to read. Allowing the same
#: three words file-wide would let them switch the compile step or the
#: clean-tree step off for every push to main, so the rule below pins the
#: condition to the step that needs it.
PULL_REQUEST_ONLY_CONDITION = "github.event_name == 'pull_request'"

#: Two more steps of the required job that carry neither pytest nor the gate
#: script, so `_is_a_chain_step` does not see them and neither did any rule
#: here until the step-conditional and presence rules below.
LEDGER_SCRIPT = "check_ledger_append_only.py"
CLEAN_TREE_COMMAND = "git status --porcelain"


def commands(block: str) -> list[str]:
    """The LOGICAL lines of a run block that bash will actually execute:
    comment lines dropped, continuations joined."""
    joined: list[str] = []
    for raw in block.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if joined and CONTINUATION.search(joined[-1]):
            previous = joined[-1]
            if previous.endswith("\\"):
                previous = previous[:-1].rstrip()
            joined[-1] = f"{previous} {line}"
        else:
            joined.append(line)
    return [line[:-1].rstrip() if line.endswith("\\") else line for line in joined]


def without_quoted_spans(line: str) -> str:
    text: list[str] = []
    index, size = 0, len(line)
    while index < size:
        character = line[index]
        if character == "\\":
            text.append(" ")
            index += 2
            continue
        if character in "'\"":
            cursor = index + 1
            while cursor < size:
                if character == '"' and line[cursor] == "\\":
                    cursor += 2
                    continue
                if line[cursor] == character:
                    break
                cursor += 1
            text.append(" " * (min(cursor, size - 1) - index + 1))
            index = cursor + 1
            continue
        text.append(character)
        index += 1
    return "".join(text)


def _top_level_pieces(line: str) -> list[list[str]]:
    blanked = without_quoted_spans(line)
    segments: list[list[str]] = []
    chunks: list[str] = []
    current: list[str] = []
    depth = 0
    index, size = 0, len(blanked)
    while index < size:
        character = blanked[index]
        if character in "({":
            depth += 1
        elif character in ")}":
            depth = max(0, depth - 1)
        if depth == 0 and blanked.startswith("||", index):
            chunks.append("".join(current))
            current = []
            index += 2
            continue
        if depth == 0 and blanked.startswith("&&", index):
            chunks.append("".join(current))
            segments.append(chunks)
            chunks, current = [], []
            index += 2
            continue
        if depth == 0 and character == ";":
            chunks.append("".join(current))
            segments.append(chunks)
            chunks, current = [], []
            index += 1
            continue
        current.append(character)
        index += 1
    chunks.append("".join(current))
    segments.append(chunks)
    return segments


def unguarded_or_branches(line: str) -> list[str]:
    """The `||` branches on this line that do NOT end in a non-zero exit."""
    branches: list[str] = []
    for chunks in _top_level_pieces(line):
        if len(chunks) < 2:
            continue
        if CONDITION.search(chunks[0]):
            continue
        for position in range(1, len(chunks)):
            branch = "||".join(chunks[position:])
            if not NONZERO_EXIT.search(branch):
                branches.append(branch.strip())
    return branches


# --------------------------------------------------------------------------
# The stub harness.
# --------------------------------------------------------------------------

HARNESS_SHELL = shutil.which("bash")

SHELL_KEYWORDS = frozenset({
    "if", "then", "else", "elif", "fi", "for", "while", "until", "do", "done",
    "case", "esac", "in", "function", "select", "time", "coproc", "!", "{", "}",
    "[[", "]]",
})

#: Builtins left real: stubbing `true`, `:` or `test` would make `cmd || true`
#: look like a failure path.
SHELL_BUILTINS = frozenset({
    "set", "unset", "exit", "return", "echo", "printf", "test", "[", "]", ":",
    "true", "false", "cd", "pwd", "read", "eval", "exec", "export", "local",
    "shift", "trap", "source", ".", "wait", "break", "continue", "declare",
    "typeset", "let", "mapfile", "readarray", "alias", "unalias", "bind",
    "builtin", "caller", "command", "compgen", "complete", "dirs", "disown",
    "enable", "fc", "fg", "bg", "getopts", "hash", "help", "history", "jobs",
    "kill", "logout", "popd", "pushd", "readonly", "suspend", "times", "type",
    "ulimit", "umask", "shopt",
})
STUB_SAFE_NAME = re.compile(r"^[A-Za-z_./][A-Za-z0-9_./+-]*$")
PREFIX_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\+?=")
COMMAND_NOT_FOUND = re.compile(r"[:\s]([^:\s]+): command not found")
RUNNER_FILE_VARIABLES = ("GITHUB_STEP_SUMMARY", "GITHUB_OUTPUT", "GITHUB_ENV", "GITHUB_PATH")
VARIABLE_WITH_DEFAULT = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\s*:?[-=+?]")
VARIABLE_BRACED = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)")
VARIABLE_BARE = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)")
EXPRESSION = re.compile(r"\$\{\{(.*?)\}\}", re.S)

#: Directories the sandbox carries so a block's own `[ -d src ]` precheck
#: passes and the command behind it is what gets judged.
SANDBOX_DIRECTORIES = ("src", "scripts", "tests", "data/outputs", "data/processed")


def render_expressions(block: str, values: dict[str, str] | None = None) -> str:
    """`${{ expr }}` as the runner would substitute it, near enough to run.

    A `secrets` expression renders to the CANARY, so `echo "${{ secrets.X }}"`
    inside a run block is caught by the same observation as `echo $X`.
    Anything else renders to a stable placeholder, or to the value the caller
    chose for it — which is how a test drives `github.event_name` to
    `schedule` and watches which branch the block takes.
    """
    def substitute(match: re.Match) -> str:
        expression = match.group(1).strip()
        if values and expression in values:
            return values[expression]
        if SECRETS_WORD.search(expression):
            return CANARY
        slug = re.sub(r"[^A-Za-z0-9]+", "_", expression).strip("_")[:48]
        return f"__expr_{slug}__"

    return EXPRESSION.sub(substitute, block)


def _uncommented(block: str) -> str:
    return "\n".join(line for line in block.splitlines() if not line.strip().startswith("#"))


def _shell_regions(text: str) -> list[str]:
    outer: list[str] = []
    inner: list[str] = []
    index, size = 0, len(text)
    while index < size:
        character = text[index]
        if character == "'":
            close = text.find("'", index + 1)
            close = size if close < 0 else close
            outer.append(text[index: close + 1])
            index = close + 1
            continue
        if character == "\\":
            outer.append(text[index: index + 2])
            index += 2
            continue
        if text.startswith("$((", index):
            # Arithmetic: nothing inside is a command except a nested `$(...)`,
            # so only the nested substitutions become regions. Without this
            # `$(( $(wc -l < f) - 1 ))` handed `-` to the scanner as a command.
            depth, cursor = 2, index + 3
            while cursor < size and depth:
                if text[cursor] == "(":
                    depth += 1
                elif text[cursor] == ")":
                    depth -= 1
                cursor += 1
            arithmetic = text[index + 3: max(cursor - 2, index + 3)]
            inner.extend(_shell_regions(arithmetic)[1:])
            outer.append(" ")
            index = cursor
            continue
        if text.startswith("$(", index):
            depth, cursor = 1, index + 2
            while cursor < size and depth:
                if text[cursor] == "'":
                    close = text.find("'", cursor + 1)
                    cursor = (size if close < 0 else close) + 1
                    continue
                if text[cursor] == "\\":
                    cursor += 2
                    continue
                if text[cursor] == "(":
                    depth += 1
                elif text[cursor] == ")":
                    depth -= 1
                cursor += 1
            inner.append(text[index + 2: max(cursor - 1, index + 2)])
            outer.append(" ")
            index = cursor
            continue
        if character == "`":
            close = text.find("`", index + 1)
            close = size if close < 0 else close
            inner.append(text[index + 1: close])
            outer.append(" ")
            index = close + 1
            continue
        outer.append(character)
        index += 1
    regions = ["".join(outer)]
    for span in inner:
        regions.extend(_shell_regions(span) if "$((" not in span[:3] else [span])
    return regions


def _scan_command_words(region: str, found: list[str]) -> None:
    current: list[str] = []
    quote: str | None = None
    at_command, skip_next = True, False
    index, size = 0, len(region)

    def flush() -> None:
        nonlocal current, at_command, skip_next
        token = "".join(current)
        current = []
        if not token:
            return
        if skip_next:
            skip_next = False
            return
        if not at_command:
            return
        if token in SHELL_KEYWORDS or PREFIX_ASSIGNMENT.match(token):
            return
        at_command = False
        if token in SHELL_BUILTINS or re.fullmatch(r"[0-9]+", token):
            return
        if "$" in token or "*" in token or "?" in token:
            return
        if token not in found:
            found.append(token)

    while index < size:
        character = region[index]
        if quote is not None:
            if character == quote:
                quote = None
            elif quote == '"' and character == "\\":
                index += 1
            current.append(character)
            index += 1
            continue
        if character in "'\"":
            quote = character
            current.append(character)
            index += 1
            continue
        if character == "\\":
            index += 2
            continue
        if character in "<>":
            flush()
            skip_next = True
            index += 1
            continue
        if character == "\n" or character in ";|&(){}`":
            flush()
            at_command, skip_next = True, False
            index += 1
            continue
        if character.isspace():
            flush()
            index += 1
            continue
        current.append(character)
        index += 1
    flush()


def command_words(block: str) -> list[str]:
    """Every word this block would invoke as a command. Over-collection is
    safe (an unused stub) and under-collection is reported by the run."""
    found: list[str] = []
    for region in _shell_regions(_uncommented(block)):
        _scan_command_words(region, found)
    return found


def referenced_variables(block: str) -> list[str]:
    named = set(VARIABLE_BRACED.findall(block)) | set(VARIABLE_BARE.findall(block))
    return sorted(named - set(VARIABLE_WITH_DEFAULT.findall(block)))


def _quote(text: str) -> str:
    return "'" + text.replace("'", "'\\''") + "'"


def stub_preamble(
    words: list[str],
    failing: set[str] | None,
    logs: dict[str, Path],
    outputs: dict[str, str],
    failing_sites: set[tuple[str, int]] = frozenset(),
) -> str:
    """The shell that turns each command word into a function of known status.

    Each stub records itself in `invocations` with its arguments and whether
    it ran in the top-level shell (the pid test: `$$` is the script's pid
    everywhere, while a re-exec'd shell reports the shell that forked it, so a
    command inside `$(...)`, a pipeline element or a background job reads as
    not-top-level). A failing stub also records itself in `failures` (top
    level only) and `any_failures` (wherever it ran). Every stub prints
    something, so `test -z "$(cmd)"` behaves as it does with a real command.

    Written flat rather than through a helper: bash does not inherit an ERR
    trap into a nested function frame without `set -E`, and `trap 'exit 0'
    ERR` was only caught in the flat form.
    """
    assert HARNESS_SHELL, "no bash on PATH: the executed rules cannot run"
    lines = [
        "command_not_found_handle() { printf '%s\\n' \"$1\" >> "
        + _quote(str(logs["unmodelled"])) + "; return 127; }",
        "readonly PATH",
    ]
    for word in words:
        status = 1 if (failing is None or word in failing) else 0
        sites = sorted(line for site_word, line in failing_sites if site_word == word)
        body = ["%s() {" % word]
        # Drain a piped stdin, with builtins only — `cat` is itself stubbed,
        # so calling it here would recurse. A real `tee` reads what is piped
        # to it; a stub that returns without reading closes the pipe under the
        # upstream command, which takes SIGPIPE and reports 141. With pipefail
        # that became the whole pipeline's status, so `python ... | tee log`
        # failed a rule about one run in eight — measured at 1 failure in 8
        # runs of `-k "degraded_path or refuses_to_run_without"`. A guard that
        # is red on a coin flip is a guard people re-run rather than read.
        body.append('  if [ -p /dev/stdin ]; then while IFS= read -r __LINE_IN; do :; done; fi')
        body.append('  __TOP="$( exec %s -c \'echo $PPID\' )"' % _quote(HARNESS_SHELL))
        body.append('  if [ "$__TOP" = "$$" ]; then __TOP=1; else __TOP=0; fi')
        # The script line this call came from. A failure can be injected at
        # one call site rather than at every call of the word, which is what
        # lets the final-statement rule fail exactly the command it means to.
        body.append('  __LINE="${BASH_LINENO[0]}"')
        body.append("  __STATUS=%d" % status)
        for line in sites:
            body.append('  if [ "$__LINE" = %d ]; then __STATUS=1; fi' % line)
        body.append(
            "  printf '%s\\t%s\\t%s\\t%s\\n' " + _quote(word) + ' "$__TOP" "$__LINE" "$*" >> '
            + _quote(str(logs["invocations"]))
        )
        body.append('  if [ "$__STATUS" = 1 ]; then')
        body.append("    printf '%s\\n' " + _quote(word) + " >> " + _quote(str(logs["any_failures"])))
        body.append(
            '    if [ "$__TOP" = 1 ]; then printf \'%s\\n\' ' + _quote(word)
            + " >> " + _quote(str(logs["failures"])) + "; fi"
        )
        body.append("  fi")
        body.append("  printf '%s\\n' " + _quote(outputs.get(word, f"stub:{word}")))
        body.append('  return "$__STATUS"')
        body.append("}")
        lines.append("\n".join(body))
    lines.append(": > %s" % _quote(str(logs["marker"])))
    return "\n".join(lines) + "\n"


class Invocation(NamedTuple):
    word: str
    top_level: bool
    #: The line of the run block (1-based, after expression rendering) the
    #: call came from.
    line: int
    arguments: str


class BlockRun(NamedTuple):
    exit_code: int
    top_level_failures: list[str]
    unmodelled: list[str]
    stderr: str
    any_failures: list[str]
    stdout: str
    invocations: list[Invocation]
    runner_files: dict[str, str]
    sandbox_files: dict[str, str]


def run_block_under_stubs(
    block: str,
    failing: set[str] | None,
    sandbox: Path,
    *,
    environment: dict[str, str] | None = None,
    outputs: dict[str, str] | None = None,
    expressions: dict[str, str] | None = None,
    directories: tuple[str, ...] = SANDBOX_DIRECTORIES,
    failing_sites: set[tuple[str, int]] = frozenset(),
    append_colon: bool = True,
) -> BlockRun:
    """Execute one run block with every command replaced by a stub.

    `failing` is the set of command words whose stub returns 1; `None` means
    all of them; an empty set means none. A `:` is appended so a block that
    ends in a failing command is judged on what it DID with the failure —
    the swallow rule's question. The final-statement rule passes
    `append_colon=False` and reads the block's real exit status, which is what
    GitHub reads: a trailing `A && B` with `A` failing fails the step, and so
    does `set +e` followed by a failing last command. The
    environment is built from scratch: runner variables bound to sandbox
    files, every referenced variable bound to a harmless value, and
    `environment` overriding both — which is how the credential is planted as
    a canary, or bound empty.
    """
    assert HARNESS_SHELL, "no bash on PATH: the executed rules cannot run"
    block = render_expressions(block, expressions)
    sandbox = Path(sandbox)
    for name in ("run_block.sh", "preamble_completed"):
        (sandbox / name).unlink(missing_ok=True)
    logs = {
        "failures": sandbox / "top_level_failures.txt",
        "any_failures": sandbox / "any_failures.txt",
        "unmodelled": sandbox / "unmodelled_commands.txt",
        "invocations": sandbox / "invocations.txt",
        "marker": sandbox / "preamble_completed",
    }
    for name, path in logs.items():
        if name != "marker":
            path.write_text("", encoding="utf-8")
    for directory in directories:
        (sandbox / directory).mkdir(parents=True, exist_ok=True)
    empty_path_dir = sandbox / "empty-path"
    empty_path_dir.mkdir(exist_ok=True)

    words = command_words(block)
    unstubbable = [word for word in words if not STUB_SAFE_NAME.match(word)]
    preamble = stub_preamble(
        [word for word in words if STUB_SAFE_NAME.match(word)],
        failing, logs, outputs or {},
    )
    preamble_lines = preamble.count("\n")
    if failing_sites:
        # Sites are block lines; the stub compares script lines, and every
        # site adds exactly one line to the preamble in front of the block.
        preamble_lines += len(failing_sites)
        preamble = stub_preamble(
            [word for word in words if STUB_SAFE_NAME.match(word)],
            failing, logs, outputs or {},
            {(word, line + preamble_lines) for word, line in failing_sites},
        )
        assert preamble.count("\n") == preamble_lines
    parsed = subprocess.run([HARNESS_SHELL, "-n"], input=preamble, capture_output=True, text=True)
    if parsed.returncode != 0:
        raise RuntimeError(f"the stub preamble does not parse: {parsed.stderr}")

    script = sandbox / "run_block.sh"
    script.write_text(preamble + block + ("\n:\n" if append_colon else "\n"), encoding="utf-8")
    env = {
        "PATH": str(empty_path_dir),
        "LC_ALL": "C",
        "HOME": str(sandbox),
        "GITHUB_WORKSPACE": str(sandbox),
        "RUNNER_TEMP": str(sandbox),
    }
    for name in RUNNER_FILE_VARIABLES:
        target = sandbox / name.lower()
        target.write_text("", encoding="utf-8")
        env[name] = str(target)
    for name in referenced_variables(block):
        env.setdefault(name, "__harness__")
    env.update(environment or {})

    before = {p.name for p in sandbox.iterdir()}
    completed = subprocess.run(
        [HARNESS_SHELL, "-e", str(script)],
        cwd=sandbox, env=env, capture_output=True, text=True, timeout=60,
        # Closed, so a stub outside a pipeline sees a stdin that is not a pipe
        # and does not wait on the parent's terminal for a drain it never needs.
        stdin=subprocess.DEVNULL,
    )
    if not logs["marker"].exists():
        raise RuntimeError(
            f"the stub preamble did not run to completion: {completed.stderr}"
        )
    invocations = []
    for entry in logs["invocations"].read_text(encoding="utf-8").splitlines():
        fields = entry.split("\t", 3)
        if len(fields) < 4:
            continue
        word, top, script_line, arguments = fields
        try:
            block_line = int(script_line) - preamble_lines
        except ValueError:
            block_line = 0
        invocations.append(Invocation(word, top == "1", block_line, arguments))
    unmodelled = sorted(
        set(unstubbable)
        | set(logs["unmodelled"].read_text(encoding="utf-8").split())
        | set(COMMAND_NOT_FOUND.findall(completed.stderr))
    )
    sandbox_files = {}
    for path in sandbox.iterdir():
        if path.name not in before and path.is_file():
            try:
                sandbox_files[path.name] = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
    return BlockRun(
        completed.returncode,
        logs["failures"].read_text(encoding="utf-8").split(),
        unmodelled,
        completed.stderr,
        logs["any_failures"].read_text(encoding="utf-8").split(),
        completed.stdout,
        invocations,
        {name: (sandbox / name.lower()).read_text(encoding="utf-8", errors="replace")
         for name in RUNNER_FILE_VARIABLES},
        sandbox_files,
    )


def swallow_findings(block: str) -> list[str]:
    """Run the block under every single-failure configuration; report swallows.

    Every command failing, then each alone — the second half reaches a
    swallow that sits behind an earlier gate. A finding is an exit of 0 with
    a top-level failure in the log; a block with a background operator is
    judged on the any-failure log too, because errexit ignores an
    asynchronous command.
    """
    findings: list[str] = []
    rendered = render_expressions(block)
    words = command_words(rendered)
    backgrounded = [
        line for line in commands(rendered)
        if BACKGROUND.search(without_quoted_spans(line))
        or ASYNC_LAUNCHER.search(without_quoted_spans(line))
    ]
    with tempfile.TemporaryDirectory() as directory:
        sandbox = Path(directory)
        for failing in [None] + [{word} for word in words]:
            result = run_block_under_stubs(block, failing, sandbox)
            label = "every command failing" if failing is None else (
                "only %s failing" % ", ".join(sorted(failing))
            )
            if result.unmodelled:
                findings.append(
                    f"with {label}, {result.unmodelled} reached the shell with "
                    "no stub behind it, so this block was never modelled."
                )
                continue
            if result.exit_code == 0 and result.top_level_failures:
                findings.append(
                    f"with {label}, {sorted(set(result.top_level_failures))} "
                    "failed and the block still exited 0."
                )
                continue
            if result.exit_code == 0 and backgrounded and result.any_failures:
                findings.append(
                    f"with {label}, {sorted(set(result.any_failures))} failed "
                    f"and the block still exited 0 while running {backgrounded} "
                    "in the background."
                )
    return findings


COMPOUND_OPENERS = frozenset({"if", "for", "while", "until", "case", "{", "(", "then", "else", "elif", "do"})
COMPOUND_CLOSERS = re.compile(r"^(?:fi|done|esac|\}|\))\b")


def final_statement_is_simple(block: str) -> bool:
    """Whether the block's last logical line is a simple statement.

    The operational rule is about the command that decides the step's exit
    status, and only a simple final statement has one. A block that ends in
    `fi`, `done`, `}` or an `if ...; fi` on one line is a step that HANDLES a
    failure, which this repository does deliberately — a missing card-feed
    branch on the first run of a season is not an error — and the evidence
    workflows are held to the fuller rule instead.
    """
    lines = commands(block)
    if not lines:
        return False
    last = without_quoted_spans(lines[-1]).strip()
    if COMPOUND_CLOSERS.match(last):
        return False
    first = last.split(None, 1)[0] if last else ""
    return first not in COMPOUND_OPENERS


def status_forcing_findings(block: str) -> list[str]:
    """The operational workflows' rule, observed: a step may not force its own
    exit status.

    Tolerating an expected non-zero INSIDE a step is legitimate here and this
    repository does it deliberately. What is forbidden is a step reporting
    success after its FINAL command failed, because that is the value
    `continue-on-error` exists to record and `steps.<id>.outcome` exists to
    read. So the block is run once with every stub succeeding to find the last
    command it invokes at top level, then run again with a failure injected at
    exactly that call site — and a finding is an exit of 0, read the way
    GitHub reads it, with no `:` appended. `|| true`, `|| :`, `|| echo`,
    a trap and a wrapper function all come out the same way, because the
    verdict is the exit code and not a spelling. Three shapes that LOOK like
    swallows are not, measured under `bash -e`: `cmd; true` (errexit fires at
    `cmd`), `cmd && true` (the and-list's status is `cmd`'s) and `set +e`
    before a failing final command (its status is the script's). `if ! cmd; then warn; fi` as a final statement is NOT a
    finding here, by the rule's own definition; the disclosed-holes test says
    so.
    """
    findings: list[str] = []
    if not final_statement_is_simple(block):
        return findings
    with tempfile.TemporaryDirectory() as directory:
        sandbox = Path(directory)
        clean = run_block_under_stubs(block, set(), sandbox)
        if clean.unmodelled:
            return [
                f"{clean.unmodelled} reached the shell with no stub behind it, "
                "so this block was never modelled."
            ]
        top_level = [call for call in clean.invocations if call.top_level]
        if not top_level:
            return findings
        final = top_level[-1]
        injected = run_block_under_stubs(
            block, set(), sandbox, failing_sites={(final.word, final.line)},
            append_colon=False,
        )
        if injected.exit_code == 0 and final.word in injected.top_level_failures:
            findings.append(
                f"the final command of the step, `{final.word}` on line "
                f"{final.line}, failed and the step exited 0. A step that "
                "cannot fail cannot be read; use `continue-on-error: true` so "
                "a later gate can read `steps.<id>.outcome`."
            )
    return findings


# --------------------------------------------------------------------------
# pytest and the evidence chain.
# --------------------------------------------------------------------------


def pytest_arguments(line: str) -> list[str]:
    found = re.search(r"\bpytest\b", line)
    if found is None:
        return []
    tail = line[found.end():]
    try:
        return shlex.split(tail)
    except ValueError:
        return tail.split()


def pytest_lines(document: Any) -> Iterator[tuple[str, str]]:
    for name, block in run_blocks(document):
        for line in commands(block):
            if re.search(r"\bpytest\b", line):
                yield name, line


def same_path(text: str) -> str:
    return BRACED_VARIABLE.sub(r"$\1", text.strip())


def arguments_after(line: str, marker: str) -> list[str]:
    position = line.find(marker)
    if position < 0:
        return []
    tail = line[position + len(marker):]
    cut: list[str] = []
    quote: str | None = None
    for character in tail:
        if quote is not None:
            if character == quote:
                quote = None
            cut.append(character)
            continue
        if character in "'\"":
            quote = character
            cut.append(character)
            continue
        if character in COMMAND_TERMINATORS:
            break
        cut.append(character)
    try:
        tokens = shlex.split("".join(cut))
    except ValueError:
        tokens = "".join(cut).split()
    arguments: list[str] = []
    for token in tokens:
        if token in SHELL_OPERATOR_TOKENS:
            break
        arguments.append(token)
    return arguments


def junit_paths_on(line: str) -> list[str]:
    arguments = pytest_arguments(line)
    found: list[str] = []
    index = 0
    while index < len(arguments):
        head, _, tail = arguments[index].partition("=")
        if head in JUNIT_FLAGS:
            if tail:
                found.append(same_path(tail))
            elif index + 1 < len(arguments) and not arguments[index + 1].startswith("-"):
                found.append(same_path(arguments[index + 1]))
                index += 1
            else:
                found.append("")
        index += 1
    return found


def gate_lines(document: Any) -> Iterator[tuple[str, str]]:
    for name, block in run_blocks(document):
        for line in commands(block):
            if GATE_SCRIPT in line:
                yield name, line


def gate_path_on(line: str) -> str:
    for argument in arguments_after(line, GATE_SCRIPT):
        if not argument.startswith("-"):
            return same_path(argument)
    return ""


def _condition(node: dict) -> str | None:
    if "if" not in node:
        return None
    raw = str(node["if"]).strip()
    if raw.startswith("${{") and raw.endswith("}}"):
        raw = raw[3:-2].strip()
    return raw


def _is_a_chain_step(step: object) -> bool:
    if not isinstance(step, dict):
        return False
    run = step.get("run")
    return isinstance(run, str) and ("pytest" in run or GATE_SCRIPT in run)


def required_check_jobs(path: Path) -> list[tuple[str, dict]]:
    return [
        (job_id, job) for job_id, job in jobs_of(load(path)).items()
        if job.get("name", job_id) == REQUIRED_CHECK_CONTEXT
    ]


def tracked_paths() -> frozenset[str]:
    """Every path git tracks in THIS repository, as `git ls-files` prints it.

    Read from the real checkout even when the rule is being run against a
    synthetic workflow in tmp_path, because the question a synthetic case asks
    is the real one: would this junit path collide with a file that is
    committed here.
    """
    completed = subprocess.run(
        ["git", "ls-files"], cwd=PROJECT_ROOT, capture_output=True, text=True,
    )
    assert completed.returncode == 0, (
        f"git ls-files failed in {PROJECT_ROOT}: {completed.stderr}. The "
        "tracked-path rule cannot be checked, and a rule that did not run is "
        "not a rule that passed."
    )
    return frozenset(line.strip() for line in completed.stdout.splitlines() if line.strip())


# --------------------------------------------------------------------------
# Rules for every workflow.
# --------------------------------------------------------------------------


def check_parses_and_declares_a_trigger(path: Path) -> None:
    document = load(path)
    assert isinstance(document, dict), f"{path.name} did not parse to a mapping"
    assert document.get("name"), f"{path.name} does not name itself"
    assert triggers(document), f"{path.name} declares no `on:` trigger"


def check_no_trigger_is_path_filtered(path: Path) -> None:
    trigger = triggers(load(path))
    if not isinstance(trigger, dict):
        return
    for event, config in trigger.items():
        if not isinstance(config, dict):
            continue
        for key in ("paths", "paths-ignore"):
            assert key not in config, (
                f"{path.name}: `{event}` carries a `{key}:` filter. A "
                "path-filtered required check stays pending instead of passing."
            )


def check_no_workflow_declares_a_secrets_key(path: Path) -> None:
    for mapping in mappings(load(path)):
        declared = [key for key in mapping if str(key).strip().lower() == "secrets"]
        assert not declared, f"{path.name}: a `secrets:` key on {mapping.get('name', 'a job')}"


def check_no_job_delegates_to_a_reusable_workflow(path: Path) -> None:
    for job_id, job in jobs_of(load(path)).items():
        assert "uses" not in job, (
            f"{path.name}: job {job_id!r} delegates to {job['uses']!r}; every "
            "rule here reads run blocks and a called workflow has none here."
        )


def check_no_workflow_overrides_the_shell(path: Path) -> None:
    for mapping in mappings(load(path)):
        if "defaults" in mapping:
            run_defaults = (mapping["defaults"] or {}).get("run") if isinstance(mapping["defaults"], dict) else None
            assert not (isinstance(run_defaults, dict) and "shell" in run_defaults), (
                f"{path.name}: `defaults.run.shell` on {mapping.get('name', 'a job or the workflow')}"
            )
        if "shell" not in mapping:
            continue
        declared = mapping["shell"]
        assert isinstance(declared, str) and declared in SAFE_SHELLS, (
            f"{path.name}: `shell: {declared!r}` on {mapping.get('name', 'a step')}. "
            "`bash {0}` drops the errexit GitHub's default supplies."
        )


def check_python_version_is_pinned_to_an_exact_minor(path: Path) -> None:
    for mapping in mappings(load(path)):
        version = mapping.get("python-version")
        if version is None:
            continue
        assert isinstance(version, str) and re.fullmatch(r"\d+\.\d+", version), (
            f"{path.name}: python-version {version!r} is not an exact X.Y pin."
        )


def check_no_run_block_interpolates_the_secrets_context(path: Path) -> None:
    """A secret may reach a step through `env:` and nowhere else: an
    expression inside a run block is the secret written into the script the
    runner logs, and it is what `echo "${{ secrets.X }}"` looks like."""
    for name, block in run_blocks(load(path)):
        assert not any(SECRETS_WORD.search(m.group(0)) for m in GITHUB_EXPRESSION.finditer(block)), (
            f"{path.name}: step {name!r} interpolates the secrets context into its run block."
        )


def check_no_workflow_stages_the_whole_working_tree(path: Path) -> None:
    """`git add -A` on a tree holding `data/staging/` and a `.env` is how a
    credential reaches a public ref. Read as tokens, not as a substring."""
    for name, block in run_blocks(load(path)):
        for line in commands(block):
            for piece in _top_level_pieces(line):
                for segment in piece:
                    try:
                        tokens = shlex.split(segment)
                    except ValueError:
                        tokens = segment.split()
                    if len(tokens) >= 2 and tokens[0] == "git" and tokens[1] == "add":
                        wide = {"-A", "--all", ".", "-a", "--no-ignore-removal", "*"}
                        assert not (wide & set(tokens[2:])), (
                            f"{path.name}: step {name!r} stages the whole tree: {line!r}"
                        )


def check_the_step_status_is_never_forced(path: Path) -> None:
    for name, block in run_blocks(load(path)):
        findings = status_forcing_findings(block)
        assert not findings, f"{path.name}: step {name!r}: " + "; ".join(findings)


ALL_WORKFLOW_CHECKS: dict[str, Callable[[Path], None]] = {
    "parses_and_declares_a_trigger": check_parses_and_declares_a_trigger,
    "no_trigger_is_path_filtered": check_no_trigger_is_path_filtered,
    "no_workflow_declares_a_secrets_key": check_no_workflow_declares_a_secrets_key,
    "no_job_delegates_to_a_reusable_workflow": check_no_job_delegates_to_a_reusable_workflow,
    "no_workflow_overrides_the_shell": check_no_workflow_overrides_the_shell,
    "python_version_is_pinned_to_an_exact_minor": check_python_version_is_pinned_to_an_exact_minor,
    "no_run_block_interpolates_the_secrets_context": check_no_run_block_interpolates_the_secrets_context,
    "no_workflow_stages_the_whole_working_tree": check_no_workflow_stages_the_whole_working_tree,
    "the_step_status_is_never_forced": check_the_step_status_is_never_forced,
}


# --------------------------------------------------------------------------
# Rules for the evidence workflows, and for the required check in particular.
# --------------------------------------------------------------------------


def check_permissions_are_declared_and_read_only(path: Path) -> None:
    document = load(path)
    assert isinstance(document, dict) and "permissions" in document, (
        f"{path.name} declares no top-level `permissions:`."
    )
    for mapping in mappings(document):
        granted = mapping.get("permissions")
        if granted is None:
            continue
        rendered = (
            " ".join(f"{k}:{v}" for k, v in granted.items()) if isinstance(granted, dict) else str(granted)
        )
        assert "write" not in rendered, f"{path.name} grants write permission ({rendered})."


def check_no_step_or_job_continues_on_error(path: Path) -> None:
    for mapping in mappings(load(path)):
        assert "continue-on-error" not in mapping, (
            f"{path.name}: `continue-on-error` on {mapping.get('name', 'a job')}."
        )


def check_no_workflow_references_a_secret(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    accesses = [text[m.start(): m.end() + 40] for m in SECRET_REFERENCE.finditer(text)]
    accesses += [m.group(0) for m in GITHUB_EXPRESSION.finditer(text) if SECRETS_WORD.search(m.group(0))]
    assert not accesses, f"{path.name} references a secret ({accesses!r})."


def check_no_env_mapping_binds_a_provider_credential(path: Path) -> None:
    for mapping in mappings(load(path)):
        environment = mapping.get("env")
        if not isinstance(environment, dict):
            continue
        bound = CREDENTIAL_NAMES.intersection(map(str, environment))
        assert not bound, f"{path.name}: `env:` binds {sorted(bound)} on {mapping.get('name', 'a job')}."


def check_checkout_never_persists_credentials(path: Path) -> None:
    for step in steps_using(load(path), "actions/checkout"):
        options = step.get("with") or {}
        assert options.get("persist-credentials") is False, (
            f"{path.name}: checkout does not set `persist-credentials: false`."
        )


def check_every_piped_run_block_sets_pipefail(path: Path) -> None:
    for name, block in run_blocks(load(path)):
        lines = [without_quoted_spans(line) for line in commands(block)]
        if not any(PIPELINE.search(line) for line in lines):
            continue
        assert ENABLES_PIPEFAIL.search(lines[0]), (
            f"{path.name}: step {name!r} pipes but does not open with `set -o pipefail`."
        )
        for line in lines:
            assert not DISABLES_PIPEFAIL.search(line), f"{path.name}: step {name!r} turns pipefail off: {line!r}"


def check_no_run_block_swallows_a_failure(path: Path) -> None:
    for name, block in run_blocks(load(path)):
        for line in commands(render_expressions(block)):
            blanked = without_quoted_spans(line)
            assert not DISABLES_ERREXIT.search(blanked), f"{path.name}: step {name!r} disables errexit: {line!r}"
            assert not PROCESS_SUBSTITUTION.search(blanked), f"{path.name}: step {name!r} uses process substitution: {line!r}"
            assert not BACKGROUND.search(blanked), f"{path.name}: step {name!r} backgrounds a command: {line!r}"
            assert not ASYNC_LAUNCHER.search(blanked), f"{path.name}: step {name!r} detaches a command: {line!r}"
            unguarded = unguarded_or_branches(line)
            assert not unguarded, f"{path.name}: step {name!r} swallows a failure: {line!r} -> {unguarded}"
        findings = swallow_findings(block)
        assert not findings, f"{path.name}: step {name!r} was executed under stubs and " + "; ".join(findings)


def check_every_upload_fails_when_there_is_nothing_to_upload(path: Path) -> None:
    for step in steps_using(load(path), "actions/upload-artifact"):
        options = step.get("with") or {}
        assert options.get("if-no-files-found") == "error", (
            f"{path.name}: upload {step.get('name')!r} does not set `if-no-files-found: error`."
        )


def check_the_suite_and_the_gate_are_both_present(path: Path) -> None:
    document = load(path)
    suite = [name for name, _ in pytest_lines(document)]
    gate = [name for name, _ in gate_lines(document)]
    assert bool(suite) == bool(gate), (
        f"{path.name}: the suite runs in {suite} and the gate runs in {gate}. "
        "One end of the evidence chain is missing."
    )


def check_the_gate_reads_the_evidence_this_run_wrote(path: Path) -> None:
    document = load(path)
    written = {p for _, line in pytest_lines(document) for p in junit_paths_on(line)}
    gated = {gate_path_on(line) for _, line in gate_lines(document)}
    if not written and not gated:
        return
    assert written, f"{path.name}: {GATE_SCRIPT} is invoked and no pytest invocation writes a junit file."
    assert gated, f"{path.name}: pytest writes {sorted(written)} and nothing invokes {GATE_SCRIPT}."
    assert written == gated, f"{path.name}: pytest writes {sorted(written)} and the gate reads {sorted(gated)}."
    for name, block in run_blocks(document):
        for line in commands(block):
            normalised = BRACED_VARIABLE.sub(r"$\1", line)
            for junit in sorted(written):
                if not junit or junit not in normalised:
                    continue
                produced = junit_paths_on(line).count(junit)
                gated_here = int(GATE_SCRIPT in line and gate_path_on(line) == junit)
                assert produced or gated_here, (
                    f"{path.name}: step {name!r} names the junit path without producing or gating it: {line!r}"
                )
                assert normalised.count(junit) <= produced + gated_here, (
                    f"{path.name}: step {name!r} names the junit path more often than it produces or gates it: {line!r}"
                )


def check_no_condition_disables_the_chain(path: Path) -> None:
    for job_name, job in jobs_of(load(path)).items():
        chain = [step for step in steps_of(job) if _is_a_chain_step(step)]
        if not chain:
            continue
        assert _condition(job) is None, f"{path.name}: job {job_name!r} carries `if:` and contains the suite or the gate."
        for step in chain:
            condition = _condition(step)
            if condition is None:
                continue
            assert condition == PERMITTED_CHAIN_CONDITION, (
                f"{path.name}: a step running the suite or the gate carries `if: {condition}`."
            )


def check_the_required_check_job_is_pinned(path: Path) -> None:
    """Exactly one job carries the required context, and nothing on it can
    switch it off, hand it elsewhere, or change the shell it is judged in."""
    found = required_check_jobs(path)
    assert len(found) == 1, (
        f"{path.name}: {len(found)} jobs carry `name: {REQUIRED_CHECK_CONTEXT}`; "
        "branch protection matches the check by that name and needs exactly one."
    )
    job_id, job = found[0]
    # `needs:` is `if: false` with one more step of indirection. A required
    # job whose dependency GitHub skipped is itself skipped, and GitHub's own
    # troubleshooting page says a conditionally-skipped required check is
    # reported to branch protection as SUCCESS — unlike a path-filtered one,
    # which stays pending. So `needs: prep` where `prep` carries `if: false`
    # turns the merge gate green over a job that never ran, in one line.
    # `strategy:` is here for the neighbouring reason: a matrix with an empty
    # `include` produces zero jobs, and zero jobs is zero failures.
    for forbidden in (
        "if", "needs", "continue-on-error", "uses", "defaults", "container",
        "strategy",
    ):
        assert forbidden not in job, f"{path.name}: job {job_id!r} carries `{forbidden}:`."
    assert isinstance(job.get("runs-on"), str), f"{path.name}: job {job_id!r} has no plain `runs-on`."
    assert steps_of(job), f"{path.name}: job {job_id!r} has no steps."


#: Bindings that decide WHICH interpreter and WHICH libraries a `python`
#: command reaches. A step that rebinds one of these runs a different program
#: under the same name, which every rule that reads the command line calls
#: `python`.
INTERPRETER_VARIABLES = frozenset({
    "PATH", "PYTHONHOME", "PYTHONSTARTUP", "PYTHONEXECUTABLE",
})


def check_no_env_rebinds_the_interpreter(path: Path) -> None:
    """`env: PATH: /tmp/fake` makes `python` a different program.

    Every pin in this file names commands by the word the shell sees. That is
    only worth anything while the word resolves to what it says: bind `PATH`
    on the gate step and `python scripts/check_test_results.py` runs whatever
    is first on the new path, with the line unchanged and every rule green.
    Adding to PATH through `$GITHUB_PATH` is caught by the same reading.
    """
    document = load(path)
    for mapping in mappings(document):
        environment = mapping.get("env")
        if not isinstance(environment, dict):
            continue
        rebound = [
            key for key in environment
            if str(key).strip().upper() in INTERPRETER_VARIABLES
        ]
        assert not rebound, (
            f"{path.name}: `env:` on {mapping.get('name', 'a job')} binds "
            f"{rebound}. Rebinding the interpreter's search path makes every "
            "command pin in this file a pin on a name rather than on a program."
        )
    for name, block in run_blocks(document):
        for line in commands(block):
            assert "GITHUB_PATH" not in line, (
                f"{path.name}: step {name!r} writes to $GITHUB_PATH: {line!r}. "
                "That prepends a directory to PATH for every later step."
            )


def check_the_required_check_job_checks_out_history(path: Path) -> None:
    """`fetch-depth: 0`, because three tests in this suite read git history.

    The secrets guard runs `git ls-files`, the append-only step reads a blob
    out of the pull request's base commit, and
    `tests/test_experiment_ledger.py` reads the pre-floor `save()` out of the
    commit it was replaced in. A shallow checkout turns the third into a red
    build rather than a silent pass — which is the right direction, and is
    also a red build for a reason nobody would guess. Pinning the depth here
    is cheaper than diagnosing that.
    """
    found = required_check_jobs(path)
    assert len(found) == 1
    _, job = found[0]
    checkouts = [
        step for step in steps_of(job)
        if isinstance(step.get("uses"), str)
        and step["uses"].split("@", 1)[0] == "actions/checkout"
    ]
    assert checkouts, f"{path.name}: the required job does not check out the repository."
    for step in checkouts:
        options = step.get("with") or {}
        assert str(options.get("fetch-depth", "")).strip() == "0", (
            f"{path.name}: the required job checks out with "
            f"fetch-depth={options.get('fetch-depth')!r}. Three tests read git "
            "history; a shallow checkout makes them fail for a reason that "
            "looks nothing like the edit that caused it."
        )


def check_no_job_in_the_required_workflow_is_conditional(path: Path) -> None:
    """The other half of the `needs:` route, and the reason it is a whole rule.

    Forbidding `needs:` on the required job stops it depending on a job that
    can be switched off. This stops the file containing such a job at all:
    every job here must run unconditionally, so there is nothing for a future
    `needs:` to point at and nothing whose skip could propagate. It is cheap —
    this workflow has one job — and it means the rule above cannot be defeated
    by adding the dependency in the other direction.
    """
    for job_id, job in jobs_of(load(path)).items():
        condition = _condition(job)
        assert condition is None, (
            f"{path.name}: job {job_id!r} carries `if: {condition}`. A skipped "
            "job in this file is a job the required check could be made to "
            "wait on, and GitHub reports a conditionally-skipped required "
            "check as Success."
        )


def check_the_suite_step_is_pinned(path: Path) -> None:
    """The one step that runs pytest, pinned by WHITELIST rather than blocklist.

    The previous version of this rule listed the flags that narrow a run and
    refused those. That is a spelling check with extra steps: it proved that
    `-x`, `-k` and `--deselect` were absent and said nothing about
    `--version`, which exits 0, runs no test and writes no junit — a green
    suite step over an empty run, which the gate then reads a stale or tracked
    junit to confirm. `-h` and `--help` do the same. So the arguments are
    enumerated instead: `-q`, `-rs`, and exactly one `--junit-xml=<path>`.
    Anything else is refused whether or not anybody has thought about what it
    does, which is the property a blocklist cannot have.
    """
    found = required_check_jobs(path)
    assert len(found) == 1
    _, job = found[0]
    suite_steps = [s for s in steps_of(job) if isinstance(s.get("run"), str)
                   and any(re.search(r"\bpytest\b", l) for l in commands(s["run"]))]
    assert len(suite_steps) == 1, (
        f"{path.name}: {len(suite_steps)} steps in the required job invoke pytest; "
        "there must be exactly one, and `echo` in place of it is zero."
    )
    step = suite_steps[0]
    for forbidden in ("if", "continue-on-error", "shell", "working-directory", "uses"):
        assert forbidden not in step, f"{path.name}: the suite step carries `{forbidden}:`."
    invocations = [l for l in commands(step["run"]) if re.search(r"\bpytest\b", l)]
    assert len(invocations) == 1, f"{path.name}: the suite step invokes pytest {len(invocations)} times."
    line = invocations[0]
    # No assignment prefix. `PYTHONPATH=/tmp/whatever python -m pytest` is an
    # environment edit this file's other rules cannot see: the PYTHONPATH rule
    # in tests/test_the_guards_exist.py reads `env:` out of the YAML, and a
    # directory named only on the command line is not there. It is also a
    # `sitecustomize.py` route, because the interpreter looks for one on every
    # PYTHONPATH entry before pytest exists. The environment belongs in `env:`,
    # where it can be read.
    assert re.match(r"^python(?:3)?\s+-m\s+pytest\b", line), (
        f"{path.name}: the suite line is {line!r}. It begins with `python -m "
        "pytest` and nothing before it — an inline `NAME=value` prefix puts a "
        "directory on the path that no rule here reads."
    )
    arguments = pytest_arguments(line)
    junit_flags_seen = 0
    for argument in arguments:
        head, separator, value = argument.partition("=")
        if head in PERMITTED_PYTEST_VALUE_FLAGS:
            assert separator and value, (
                f"{path.name}: {head} carries no path, so the junit file's "
                "destination is decided somewhere this rule cannot read."
            )
            junit_flags_seen += 1
            continue
        assert argument in PERMITTED_PYTEST_FLAGS, (
            f"{path.name}: the suite line carries {argument!r}, which is not on "
            f"the whitelist {sorted(PERMITTED_PYTEST_FLAGS)} + "
            f"{sorted(PERMITTED_PYTEST_VALUE_FLAGS)}=<path>. An argument nobody "
            "listed is an argument nobody reasoned about, and `--version`, `-h` "
            "and `--help` all exit 0 having run no test and written no junit."
        )
    assert junit_flags_seen == 1, (
        f"{path.name}: the suite line carries {junit_flags_seen} junit flags; "
        "there must be exactly one, or the gate reads a file this line did not "
        "write."
    )

    junit = junit_paths_on(line)[0]
    # `$RUNNER_TEMP/../junit.xml` starts with the right prefix and lands in
    # the workspace's parent. A prefix check without this is a prefix check.
    assert ".." not in junit.split("/"), (
        f"{path.name}: the junit path {junit!r} climbs out of the directory "
        "its prefix names, which is the prefix check defeated by two dots."
    )
    assert junit.startswith(RUNNER_TEMP_PREFIXES), (
        f"{path.name}: the junit path is {junit!r}. It must be written under "
        f"one of {list(RUNNER_TEMP_PREFIXES)}: a path inside the workspace can "
        "be committed, and a tracked junit at the gated path satisfies the "
        "gate AND the clean-tree check while the suite runs nothing."
    )
    tracked = tracked_paths()
    for candidate in {junit, junit.lstrip("$"), junit.split("/", 1)[-1]}:
        assert candidate not in tracked, (
            f"{path.name}: the junit path {junit!r} collides with the tracked "
            f"file {candidate!r}. Evidence that is committed is not evidence."
        )

    environment = step.get("env")
    assert isinstance(environment, dict), (
        f"{path.name}: the suite step declares no `env:`, so it cannot set "
        f"{SAFE_PATH_VARIABLE}."
    )
    safe_path = str(environment.get(SAFE_PATH_VARIABLE, "")).strip()
    assert safe_path and safe_path != "0", (
        f"{path.name}: the suite step does not set {SAFE_PATH_VARIABLE}. "
        "Without it `python -m pytest` puts the checkout ahead of "
        "site-packages, so a tracked `pytest.py` or `coverage.py` at the root "
        "shadows the suite: measured on this lab, a three-line tracked "
        "`pytest.py` made the whole suite line exit 0 and write no junit."
    )


def check_the_gate_step_is_pinned(path: Path) -> None:
    """The gate line pinned as a WHOLE COMMAND, and then executed.

    Every other rule about the gate matched the line by substring — it need
    only CONTAIN `check_test_results.py` and the junit path. So
    `: python scripts/check_test_results.py "$RUNNER_TEMP/junit.xml"` passed
    all of them, and `echo python scripts/...` and
    `cat scripts/... "$RUNNER_TEMP/junit.xml"` did too, while the gate never
    ran. The line is now enumerated the way the suite line is, and then the
    block is run under stubs so that `python` is OBSERVED receiving the script
    as its first argument at the top level of the shell.
    """
    found = required_check_jobs(path)
    assert len(found) == 1
    _, job = found[0]
    gate_steps = [
        s for s in steps_of(job) if isinstance(s.get("run"), str)
        and any(GATE_SCRIPT in line for line in commands(s["run"]))
    ]
    assert len(gate_steps) == 1, (
        f"{path.name}: {len(gate_steps)} steps in the required job name "
        f"{GATE_SCRIPT}; there must be exactly one."
    )
    step = gate_steps[0]
    for forbidden in ("continue-on-error", "shell", "working-directory", "uses"):
        assert forbidden not in step, f"{path.name}: the gate step carries `{forbidden}:`."
    condition = _condition(step)
    assert condition in (None, PERMITTED_CHAIN_CONDITION), (
        f"{path.name}: the gate step carries `if: {condition}`. The only "
        f"condition it may take is `{PERMITTED_CHAIN_CONDITION}`, because the "
        "run that most needs the gate is the one where something already went "
        "wrong."
    )

    lines = commands(step["run"])
    assert len(lines) == 1, (
        f"{path.name}: the gate step runs {len(lines)} commands. It runs one, "
        "so there is nowhere for a second command to change the first's status."
    )
    try:
        tokens = shlex.split(lines[0])
    except ValueError as exc:  # pragma: no cover - unbalanced quoting
        raise AssertionError(f"{path.name}: the gate line does not parse: {exc}")
    assert len(tokens) == 3, (
        f"{path.name}: the gate line is {tokens!r}. It is exactly "
        f"`python scripts/{GATE_SCRIPT} <junit>` — three words, no prefix, no "
        f"redirection. A leading `:` or `echo` leaves every substring rule "
        "satisfied and the gate unexecuted."
    )
    assert tokens[0] in {"python", "python3"}, (
        f"{path.name}: the gate line begins with {tokens[0]!r}, not python."
    )
    assert tokens[1] == f"scripts/{GATE_SCRIPT}", (
        f"{path.name}: the gate line runs {tokens[1]!r}, not scripts/{GATE_SCRIPT}."
    )

    written = {p for _, line in pytest_lines(load(path)) for p in junit_paths_on(line)}
    if written:
        assert same_path(tokens[2]) in written, (
            f"{path.name}: the gate reads {tokens[2]!r} and the suite writes "
            f"{sorted(written)}."
        )

    # ...and observed. The stub harness replaces every command word with a
    # function of known status, so this reads which command the shell actually
    # reached and what it was handed.
    with tempfile.TemporaryDirectory() as directory:
        result = run_block_under_stubs(step["run"], set(), Path(directory))
        assert not result.unmodelled, (path.name, result.unmodelled)
        invoked = [
            call for call in result.invocations
            if call.word in {"python", "python3"} and call.top_level
        ]
        assert invoked, (
            f"{path.name}: running the gate step under stubs invoked python at "
            f"the top level {len(invoked)} times. The gate did not execute."
        )
        first = invoked[0].arguments.split()
        assert first and first[0] == f"scripts/{GATE_SCRIPT}", (
            f"{path.name}: python was invoked with {invoked[0].arguments!r}; "
            f"scripts/{GATE_SCRIPT} is not its first argument."
        )


def check_pytest_addopts_is_set_nowhere(path: Path) -> None:
    document = load(path)
    for mapping in mappings(document):
        environment = mapping.get("env")
        if isinstance(environment, dict):
            bound = [k for k in environment if str(k).strip().upper() == PYTEST_ADDOPTS]
            assert not bound, f"{path.name}: `env:` binds {PYTEST_ADDOPTS} on {mapping.get('name', 'a job')}."
    for name, block in run_blocks(document):
        for line in commands(block):
            assert not PYTEST_ADDOPTS_TOKEN.search(line), f"{path.name}: step {name!r} sets {PYTEST_ADDOPTS}: {line!r}"


def check_the_pull_request_trigger_is_unfiltered(path: Path) -> None:
    trigger = triggers(load(path))
    if isinstance(trigger, list):
        assert "pull_request" in trigger, f"{path.name}: no pull_request trigger."
        return
    assert isinstance(trigger, dict) and "pull_request" in trigger, f"{path.name}: no pull_request trigger."
    config = trigger["pull_request"]
    if config is None:
        return
    assert isinstance(config, dict)
    for key in ("paths", "paths-ignore", "branches", "branches-ignore"):
        assert key not in config, (
            f"{path.name}: `pull_request` carries `{key}:`. A filtered required check "
            "either stays pending or never runs on the branch that matters."
        )


def check_the_compile_step_fails_on_a_missing_directory(path: Path) -> None:
    """`compileall` exits 0 on a path that names nothing. Observed: the block
    is run with every stub SUCCEEDING in a sandbox with no `src`, and must
    exit non-zero; and with the directories present it must exit 0."""
    document = load(path)
    compile_blocks = [
        (name, block) for name, block in run_blocks(document)
        if any("compileall" in line for line in commands(block))
    ]
    assert compile_blocks, f"{path.name}: no step byte-compiles the modules."
    for name, block in compile_blocks:
        for line in commands(block):
            if "compileall" in line:
                assert "-f" in shlex.split(line), (
                    f"{path.name}: step {name!r} compiles without -f, so a stale __pycache__ masks a broken file."
                )
        with tempfile.TemporaryDirectory() as directory:
            missing = run_block_under_stubs(block, set(), Path(directory), directories=())
            assert missing.exit_code != 0, (
                f"{path.name}: step {name!r} exited 0 with no source directory present; "
                "the byte-compile gate would pass on nothing."
            )
        with tempfile.TemporaryDirectory() as directory:
            present = run_block_under_stubs(block, set(), Path(directory))
            assert present.exit_code == 0 and not present.unmodelled, (
                f"{path.name}: step {name!r} does not run clean with the directories present: {present.stderr}"
            )


def check_no_step_of_the_required_job_is_conditional(path: Path) -> None:
    """EVERY step of the required job, not only the two that run the chain.

    `check_no_condition_disables_the_chain` reads the steps whose `run:`
    mentions pytest or the gate script, which left every OTHER step of the
    required job unconditioned by anything. That is not a smaller version of
    the same hole, it is the same hole: GitHub does not fail a job because a
    step was skipped, it reports the job as Success with the step marked
    skipped. So a one-line `if: false` on the compile step, on the clean-tree
    step, on the append-only step or on the evidence upload deletes that
    guarantee and leaves the merge button green.

    Observed on this file's own control workflow before this rule existed:
    at 5304f79, `if: false` on the Compile step, on the checkout and on the
    upload step was rejected by 0 of the 29 rules then in `ALL_RULES`, and so
    was `if: github.event_name == 'pull_request'` on the Compile step, which
    switches that step off for every push to main. The cases are in
    REJECTIONS under `compile_step_if_false`, `checkout_step_if_false`,
    `upload_step_if_false`, `clean_tree_step_if_false` and
    `ledger_step_if_false`.

    The whitelist, by condition and by step:

    * `always()` on any step. It adds the case where an earlier step already
      failed; it does not take away a run the default would have made.
    * `github.event_name == 'pull_request'` on the append-only step alone. It
      narrows, so it is pinned to the one step that has a reason: there is no
      base commit to compare against on a push. The same three words on the
      compile step are a rejection case.

    Anything else is refused whether or not anybody has thought about what it
    evaluates to, which is the property a blocklist of `false` cannot have.
    """
    found = required_check_jobs(path)
    assert len(found) == 1, (
        f"{path.name}: {len(found)} jobs carry `name: {REQUIRED_CHECK_CONTEXT}`."
    )
    _, job = found[0]
    for index, step in enumerate(steps_of(job)):
        condition = _condition(step)
        if condition is None or condition == PERMITTED_CHAIN_CONDITION:
            continue
        name = step.get("name", f"step {index}")
        run = step.get("run")
        is_the_ledger_step = isinstance(run, str) and LEDGER_SCRIPT in run
        assert condition == PULL_REQUEST_ONLY_CONDITION and is_the_ledger_step, (
            f"{path.name}: step {name!r} of the required job carries "
            f"`if: {condition}`. A skipped step does not fail its job — the "
            f"required check reports Success with the step switched off. The "
            f"only conditions permitted here are `{PERMITTED_CHAIN_CONDITION}` "
            f"on any step and `{PULL_REQUEST_ONLY_CONDITION}` on the "
            f"{LEDGER_SCRIPT} step."
        )


def check_the_clean_tree_step_is_present(path: Path) -> None:
    """Deleting this step passed every rule, so its presence is now a rule.

    A run that writes into `data/outputs/` is how a committed measurement
    gets regenerated by CI and reviewed by nobody. Nothing else here reads
    that step, so `git rm`-ing it out of the job — or leaving it in place with
    its verdict ignored — was invisible.

    Presence is the cheap half. The other half is executed: the block is run
    under stubs with `git status --porcelain` printing a modified path, and
    must exit non-zero; then with it printing nothing, and must exit 0. A step
    that reports a dirty tree and carries on fails the first; a step that
    fails on a clean tree fails the second.
    """
    found = required_check_jobs(path)
    assert len(found) == 1
    _, job = found[0]
    blocks = [
        (step.get("name", "a step"), step["run"]) for step in steps_of(job)
        if isinstance(step.get("run"), str)
        and any(CLEAN_TREE_COMMAND in line for line in commands(step["run"]))
    ]
    assert len(blocks) == 1, (
        f"{path.name}: {len(blocks)} steps of the required job run "
        f"`{CLEAN_TREE_COMMAND}`; exactly one must."
    )
    name, block = blocks[0]
    with tempfile.TemporaryDirectory() as directory:
        dirty = run_block_under_stubs(
            block, set(), Path(directory),
            outputs={"git": " M data/outputs/experiment_ledger.json"},
        )
        assert dirty.exit_code != 0, (
            f"{path.name}: step {name!r} exited 0 with `{CLEAN_TREE_COMMAND}` "
            f"reporting a modified file: {dirty.stdout!r}"
        )
    with tempfile.TemporaryDirectory() as directory:
        clean = run_block_under_stubs(block, set(), Path(directory), outputs={"git": ""})
        assert clean.exit_code == 0 and not clean.unmodelled, (
            f"{path.name}: step {name!r} does not pass on a clean tree: "
            f"{clean.exit_code} {clean.unmodelled} {clean.stderr}"
        )


def check_the_append_only_step_is_present(path: Path) -> None:
    """The same for the ledger comparison, and for the same reason.

    Branch protection requires `Tests` and nothing else, so the pull-request
    half of the append-only comparison runs inside this job. Deleting the step
    left the `Ledger Guard` workflow's own tick, which does not block a merge.

    Executed: the block is run under stubs and `python` must be OBSERVED
    receiving `scripts/check_ledger_append_only.py`, so `echo python ...` and
    a leading `:` do not satisfy it; then again with `python` failing, where
    the block must exit non-zero rather than carry on.
    """
    found = required_check_jobs(path)
    assert len(found) == 1
    _, job = found[0]
    blocks = [
        (step.get("name", "a step"), step["run"]) for step in steps_of(job)
        if isinstance(step.get("run"), str) and LEDGER_SCRIPT in step["run"]
    ]
    assert len(blocks) == 1, (
        f"{path.name}: {len(blocks)} steps of the required job invoke "
        f"{LEDGER_SCRIPT}; exactly one must. Only this job blocks a merge."
    )
    name, block = blocks[0]
    # `mktemp` prints a name the block then redirects into, so the
    # non-empty-base check ahead of the comparison is satisfied in the sandbox.
    outputs = {"mktemp": "base_ledger.json"}
    with tempfile.TemporaryDirectory() as directory:
        ran = run_block_under_stubs(block, set(), Path(directory), outputs=outputs)
    assert not ran.unmodelled, (path.name, ran.unmodelled)
    reached = [
        call for call in ran.invocations
        if call.word in {"python", "python3"}
        and call.arguments.split()[:1] == [f"scripts/{LEDGER_SCRIPT}"]
    ]
    assert reached, (
        f"{path.name}: step {name!r} names {LEDGER_SCRIPT} and never runs it. "
        f"Invoked: {[(c.word, c.arguments) for c in ran.invocations]}"
    )
    with tempfile.TemporaryDirectory() as directory:
        refused = run_block_under_stubs(
            block, {"python", "python3"}, Path(directory),
            outputs=outputs, append_colon=False,
        )
    assert refused.exit_code != 0, (
        f"{path.name}: step {name!r} exited 0 with {LEDGER_SCRIPT} failing."
    )


REQUIRED_CHECK_RULES: dict[str, Callable[[Path], None]] = {
    "the_required_check_job_is_pinned": check_the_required_check_job_is_pinned,
    "no_job_in_the_required_workflow_is_conditional": check_no_job_in_the_required_workflow_is_conditional,
    "the_required_check_job_checks_out_history": check_the_required_check_job_checks_out_history,
    "no_env_rebinds_the_interpreter": check_no_env_rebinds_the_interpreter,
    "the_suite_step_is_pinned": check_the_suite_step_is_pinned,
    "the_gate_step_is_pinned": check_the_gate_step_is_pinned,
    "pytest_addopts_is_set_nowhere": check_pytest_addopts_is_set_nowhere,
    "the_pull_request_trigger_is_unfiltered": check_the_pull_request_trigger_is_unfiltered,
    "the_compile_step_fails_on_a_missing_directory": check_the_compile_step_fails_on_a_missing_directory,
    "the_suite_and_the_gate_are_both_present": check_the_suite_and_the_gate_are_both_present,
    "the_gate_reads_the_evidence_this_run_wrote": check_the_gate_reads_the_evidence_this_run_wrote,
    "no_condition_disables_the_chain": check_no_condition_disables_the_chain,
    "no_step_of_the_required_job_is_conditional": check_no_step_of_the_required_job_is_conditional,
    "the_clean_tree_step_is_present": check_the_clean_tree_step_is_present,
    "the_append_only_step_is_present": check_the_append_only_step_is_present,
}

EVIDENCE_RULES: dict[str, Callable[[Path], None]] = {
    "permissions_are_declared_and_read_only": check_permissions_are_declared_and_read_only,
    "no_step_or_job_continues_on_error": check_no_step_or_job_continues_on_error,
    "no_workflow_references_a_secret": check_no_workflow_references_a_secret,
    "no_env_mapping_binds_a_provider_credential": check_no_env_mapping_binds_a_provider_credential,
    "checkout_never_persists_credentials": check_checkout_never_persists_credentials,
    "every_piped_run_block_sets_pipefail": check_every_piped_run_block_sets_pipefail,
    "no_run_block_swallows_a_failure": check_no_run_block_swallows_a_failure,
    "every_upload_fails_when_there_is_nothing_to_upload": check_every_upload_fails_when_there_is_nothing_to_upload,
    "no_workflow_overrides_the_shell": check_no_workflow_overrides_the_shell,
}


# --------------------------------------------------------------------------
# The rules, applied to the real workflows.
# --------------------------------------------------------------------------


def test_the_workflow_directory_is_not_empty() -> None:
    names = {path.name for path in WORKFLOWS}
    assert len(WORKFLOWS) >= 7, names
    assert EVIDENCE_WORKFLOWS <= names and SPENDING <= names and MAY_COMMENT <= names


def test_the_executed_rules_have_a_shell_to_run_in() -> None:
    assert HARNESS_SHELL, "no bash on PATH: absence is never a pass"


@pytest.mark.parametrize("rule", sorted(ALL_WORKFLOW_CHECKS), ids=sorted(ALL_WORKFLOW_CHECKS))
@every_workflow
def test_every_workflow_passes_the_rules_every_workflow_must(path: Path, rule: str) -> None:
    ALL_WORKFLOW_CHECKS[rule](path)


@pytest.mark.parametrize("rule", sorted(EVIDENCE_RULES), ids=sorted(EVIDENCE_RULES))
@evidence_workflows
def test_the_evidence_workflows_pass_the_evidence_rules(path: Path, rule: str) -> None:
    EVIDENCE_RULES[rule](path)


@pytest.mark.parametrize("rule", sorted(REQUIRED_CHECK_RULES), ids=sorted(REQUIRED_CHECK_RULES))
def test_the_required_check_workflow_passes_every_pin(rule: str) -> None:
    path = WORKFLOW_DIR / REQUIRED_CHECK_WORKFLOW
    assert path.is_file(), f"{REQUIRED_CHECK_WORKFLOW} is missing; the required check has no workflow."
    REQUIRED_CHECK_RULES[rule](path)


def test_exactly_one_job_in_the_repository_carries_the_required_context() -> None:
    """Across EVERY workflow, not just tests.yml: a second job named `Tests`
    in any file would be a second check run under the protected name."""
    found = [(path.name, job_id) for path in WORKFLOWS for job_id, _ in required_check_jobs(path)]
    assert found == [(REQUIRED_CHECK_WORKFLOW, "tests")], found


def test_the_required_check_context_is_the_one_branch_protection_names() -> None:
    """Pinned as a literal rather than fetched: the protection rule is
    Cooper's to change, and this file must go red when it drifts, not adapt."""
    assert REQUIRED_CHECK_CONTEXT == "Tests"
    assert load(WORKFLOW_DIR / REQUIRED_CHECK_WORKFLOW)["jobs"]["tests"]["name"] == REQUIRED_CHECK_CONTEXT


def test_every_real_run_block_is_modelled_by_the_harness() -> None:
    """The executed rules are vacuous over a block the harness could not run;
    every run block in every workflow must be fully stubbed."""
    with tempfile.TemporaryDirectory() as directory:
        for path in WORKFLOWS:
            for name, block in run_blocks(load(path)):
                for failing in (set(), None):
                    result = run_block_under_stubs(block, failing, Path(directory))
                    assert not result.unmodelled, (path.name, name, result.unmodelled)


# -- the operational workflows, held to the old rules by observation ---------


def _steps_with_env(path: Path, variable: str) -> list[dict]:
    return [
        step for job in jobs_of(load(path)).values() for step in steps_of(job)
        if isinstance(step.get("env"), dict) and variable in step["env"] and isinstance(step.get("run"), str)
    ]


@pytest.mark.parametrize("name", sorted(SPENDING))
def test_a_workflow_that_spends_credits_takes_a_cap(name: str) -> None:
    document = load(WORKFLOW_DIR / name)
    inputs = triggers(document)["workflow_dispatch"]["inputs"]
    assert "credit_cap" in inputs and inputs["credit_cap"]["required"] is True
    passed = [
        line for _, block in run_blocks(document) for line in commands(block)
        if "--credit-cap" in shlex.split(line.replace("\n", " ")) if "--credit-cap" in line
    ]
    assert passed, f"{name}: no run block passes --credit-cap"


@pytest.mark.parametrize("name", sorted(SPENDING))
def test_a_workflow_that_spends_credits_refuses_to_run_without_the_secret(name: str) -> None:
    """Observed: the live step is run with the credential bound EMPTY and
    every stub succeeding, and must exit non-zero before python runs; bound
    to the canary it must proceed. Running without a credential is not a
    cheaper run; it is a run that fails halfway with a staged file."""
    steps = _steps_with_env(WORKFLOW_DIR / name, "FOOTBALL_ODDS_API_KEY")
    live = [s for s in steps if "--live" in s["run"]]
    assert live, f"{name}: no step binds the credential and runs --live"
    credential = next(iter(CREDENTIAL_NAMES))
    with tempfile.TemporaryDirectory() as directory:
        for step in live:
            empty = run_block_under_stubs(step["run"], set(), Path(directory), environment={credential: ""})
            assert empty.exit_code != 0, (name, step.get("name"))
            assert not [c for c in empty.invocations if c.word == "python"], (name, step.get("name"))
            assert "Nothing was requested" in empty.stdout + empty.stderr, (name, step.get("name"))
            planted = run_block_under_stubs(step["run"], set(), Path(directory), environment={credential: CANARY})
            assert planted.exit_code == 0 and [c for c in planted.invocations if c.word == "python"]


@every_workflow
def test_no_run_block_lets_the_credential_out(path: Path) -> None:
    """Observed, not grepped: every run block is executed with the credential
    planted as a canary — in the environment and under every `secrets`
    expression — and the canary must appear in no stdout, no stderr, no
    runner file, no file the block wrote, and no argument any stub received.
    That is `echo $FOOTBALL_ODDS_API_KEY`, `printf`, `env`, `set`,
    `--api-key "$X"` under any flag name, and `>> $GITHUB_STEP_SUMMARY`, in
    one observation."""
    credential = next(iter(CREDENTIAL_NAMES))
    with tempfile.TemporaryDirectory() as directory:
        for name, block in run_blocks(load(path)):
            for failing in (set(), None):
                result = run_block_under_stubs(
                    block, failing, Path(directory), environment={credential: CANARY},
                )
                leaked = {
                    "stdout": result.stdout, "stderr": result.stderr,
                    **{f"runner:{k}": v for k, v in result.runner_files.items()},
                    **{f"file:{k}": v for k, v in result.sandbox_files.items()},
                    **{f"argument:{c.word}": c.arguments for c in result.invocations},
                }
                offenders = sorted(where for where, text in leaked.items() if CANARY in text)
                assert not offenders, (path.name, name, offenders)


def test_the_canary_observation_fires_on_each_way_out(tmp_path: Path) -> None:
    """The positive controls for the rule above, one per channel."""
    credential = next(iter(CREDENTIAL_NAMES))
    for block, channel in (
        ("echo \"$" + credential + "\"", "stdout"),
        ("printf '%s\\n' \"${" + credential + "}\" >&2", "stderr"),
        ("echo \"key=$" + credential + "\" >> \"$GITHUB_OUTPUT\"", "runner:GITHUB_OUTPUT"),
        ("python scripts/x.py --api-key \"$" + credential + "\"", "argument:python"),
        ("python scripts/x.py --token=\"$" + credential + "\"", "argument:python"),
        ("echo \"${{ secrets." + credential + " }}\"", "stdout"),
        ("env", "stdout"),
        ("echo \"$" + credential + "\" > note.txt", "file:note.txt"),
    ):
        result = run_block_under_stubs(block, set(), tmp_path, environment={credential: CANARY},
                                       outputs={"env": f"{credential}={CANARY}"})
        leaked = {
            "stdout": result.stdout, "stderr": result.stderr,
            **{f"runner:{k}": v for k, v in result.runner_files.items()},
            **{f"file:{k}": v for k, v in result.sandbox_files.items()},
            **{f"argument:{c.word}": c.arguments for c in result.invocations},
        }
        assert CANARY in leaked[channel], (block, channel)


def test_only_the_gameday_workflow_may_write_to_the_repository() -> None:
    for path in WORKFLOWS:
        permissions = load(path).get("permissions") or {}
        expected = "write" if path.name in MAY_WRITE_CONTENTS else "read"
        assert permissions.get("contents") == expected, path.name


def test_only_the_named_workflows_may_comment_on_the_operating_home() -> None:
    for path in WORKFLOWS:
        permissions = load(path).get("permissions") or {}
        expected = "write" if path.name in MAY_COMMENT else None
        assert permissions.get("issues") == expected, path.name


def test_the_probe_and_the_shadow_run_are_manual_only() -> None:
    for name in ("provider-retention-probe.yml", "provider-shadow.yml"):
        trigger = triggers(load(WORKFLOW_DIR / name))
        assert "schedule" not in trigger and "workflow_dispatch" in trigger, name


def test_the_gameday_workflow_keeps_its_contract_name_and_schedule() -> None:
    document = load(WORKFLOW_DIR / "football-gameday-refresh.yml")
    assert document["name"] == "Football Gameday Refresh"
    crons = [entry["cron"] for entry in triggers(document)["schedule"]]
    assert crons
    for cron in crons:
        months = cron.split()[3]
        assert "9" in months and "12" in months and "1" in months


def _gameday_step(name: str) -> dict:
    document = load(WORKFLOW_DIR / "football-gameday-refresh.yml")
    for job in jobs_of(document).values():
        for step in steps_of(job):
            if step.get("name") == name:
                return step
    raise AssertionError(f"no gameday step named {name!r}")


def test_the_degraded_path_reaches_a_human_even_when_the_card_step_failed(tmp_path: Path) -> None:
    """`if: always()` on the posting step is read from the parse; what it
    posts is observed by running the block with DECISION=degraded and reading
    the body file it handed to `gh issue comment`."""
    step = _gameday_step("Post to the operating home")
    assert _condition(step) == "always()"
    result = run_block_under_stubs(
        step["run"], set(), tmp_path, environment={"DECISION": "degraded", "GH_TOKEN": CANARY},
        outputs={"mktemp": "body.md", "head": "17"},
    )
    assert result.exit_code == 0 and not result.unmodelled, result.stderr
    comment = [c for c in result.invocations if c.word == "gh" and c.arguments.startswith("issue comment")]
    assert comment, result.invocations
    assert "--body-file body.md" in comment[0].arguments
    assert "Run did not complete" in result.sandbox_files["body.md"]
    assert CANARY not in result.sandbox_files["body.md"]


def test_a_rehearsal_never_publishes_to_the_card_feed() -> None:
    step = _gameday_step("Publish to the card-feed branch")
    assert _condition(step) == "always() && inputs.rehearsal_slate_date == ''"


def test_the_standdown_guard_honours_an_automated_dispatch(tmp_path: Path) -> None:
    """Parsed: the input exists and defaults to false. Observed: with a
    dispatch that asks for the standdown, the block reads the feed before
    deciding; with a plain dispatch it decides `run=yes` without touching git."""
    document = load(WORKFLOW_DIR / "football-gameday-refresh.yml")
    inputs = triggers(document)["workflow_dispatch"]["inputs"]
    assert str(inputs["respect_standdown"]["default"]).lower() == "false"
    step = next(s for s in steps_of(jobs_of(document)["already-published"]) if s.get("id") == "check")
    plain = run_block_under_stubs(
        step["run"], set(), tmp_path,
        expressions={"github.event_name": "workflow_dispatch", "inputs.respect_standdown || 'false'": "false"},
    )
    assert plain.exit_code == 0 and "run=yes" in plain.runner_files["GITHUB_OUTPUT"]
    assert not [c for c in plain.invocations if c.word == "git"]
    respectful = run_block_under_stubs(
        step["run"], set(), tmp_path,
        expressions={"github.event_name": "workflow_dispatch", "inputs.respect_standdown || 'false'": "true"},
    )
    assert [c for c in respectful.invocations if c.word == "git"], respectful.invocations


def test_the_purchase_reaches_back_through_previous_runs_for_its_cache(tmp_path: Path) -> None:
    """`actions/download-artifact` only sees the current run's artifacts.
    Parsed: it is not used. Observed: the restore block is run with `gh`
    failing and `wc` reporting zero files, and must say loudly that it
    restored nothing rather than silently re-buying."""
    path = WORKFLOW_DIR / "historical-purchase.yml"
    document = load(path)
    assert not list(steps_using(document, "actions/download-artifact"))
    restore = next(s for job in jobs_of(document).values() for s in steps_of(job)
                   if str(s.get("name", "")).startswith("Restore"))
    result = run_block_under_stubs(restore["run"], {"gh"}, tmp_path, outputs={"wc": "0"})
    assert any(c.word == "gh" and c.arguments.startswith("run download") for c in result.invocations) or any(
        c.word == "gh" and c.arguments.startswith("run list") for c in result.invocations
    )
    assert "::warning::" in result.stdout and "Nothing restored" in result.stdout


def test_the_weekly_check_can_tell_a_stale_calendar_from_a_lost_game_day() -> None:
    document = load(WORKFLOW_DIR / "weekly-ledger-check.yml")
    steps = [s for job in jobs_of(document).values() for s in steps_of(job)]
    schedule = [s for s in steps if s.get("id") == "schedule"]
    assert schedule and schedule[0].get("continue-on-error") is True
    readers = [s for s in steps if isinstance(s.get("env"), dict)
               and s["env"].get("SCHEDULE") == "${{ steps.schedule.outcome }}"]
    assert len(readers) >= 2, "both the report step and the failing gate must read the schedule outcome"


def test_every_only_feed_named_in_a_workflow_is_a_real_feed() -> None:
    from football_betting_lab.data import nflverse

    known = set(nflverse.FEEDS_BY_NAME)
    bad: list[str] = []
    for path in WORKFLOWS:
        for _, block in run_blocks(load(path)):
            for line in commands(render_expressions(block)):
                try:
                    tokens = shlex.split(line)
                except ValueError:
                    tokens = line.split()
                for index, token in enumerate(tokens):
                    if token != "--only":
                        continue
                    for feed in tokens[index + 1:]:
                        if feed.startswith("-") or feed.startswith("$") or feed in SHELL_OPERATOR_TOKENS:
                            break
                        if feed not in known:
                            bad.append(f"{path.name}: --only {feed}")
    assert bad == [], f"{bad}; known feeds: {sorted(known)}"


def test_the_operating_home_title_in_the_workflows_is_the_contract_string() -> None:
    from tests.test_contract_strings import OPERATING_HOME_ISSUE

    for name in sorted(MAY_COMMENT):
        blocks = [block for _, block in run_blocks(load(WORKFLOW_DIR / name))]
        assert any(OPERATING_HOME_ISSUE in block for block in blocks), name


# --------------------------------------------------------------------------
# The self-regression suite: proof that the rules above can actually FAIL.
# --------------------------------------------------------------------------

GOOD_WORKFLOW = """\
name: Tests
"on": [push, pull_request]

permissions:
  contents: read

jobs:
  tests:
    name: Tests
    runs-on: ubuntu-latest
    steps:
      - name: Check out repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
          persist-credentials: false
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Compile
        run: |
          set -euo pipefail
          for d in src scripts; do
            [ -d "$d" ] || { echo "::error::$d is missing"; exit 1; }
          done
          python -m compileall -q -f src scripts
      - name: Tests
        env:
          PYTHONSAFEPATH: '1'
        run: python -m pytest -q -rs --junit-xml="$RUNNER_TEMP/junit.xml"
      - name: Gate on the results
        if: always()
        run: python scripts/check_test_results.py "$RUNNER_TEMP/junit.xml"
      - name: Fail if the suite wrote into the working tree
        if: always()
        run: test -z "$(git status --porcelain)" || { git status --porcelain; echo '::error::dirty'; exit 1; }
      - name: Refuse a removed or rewritten hypothesis
        if: github.event_name == 'pull_request'
        env:
          BASE: ${{ github.event.pull_request.base.sha }}
        run: |
          set -euo pipefail
          git cat-file -e "${BASE}^{commit}" || { echo '::error::no base'; exit 1; }
          if git cat-file -e "${BASE}:data/outputs/experiment_ledger.json" 2>/dev/null; then
            TMP="$(mktemp)"
            git show "${BASE}:data/outputs/experiment_ledger.json" > "${TMP}"
            [ -s "${TMP}" ] || { echo '::error::empty base'; exit 1; }
            python scripts/check_ledger_append_only.py --base "${TMP}" --head data/outputs/experiment_ledger.json
          else
            python scripts/check_ledger_append_only.py --base-absent --head data/outputs/experiment_ledger.json
          fi
      - name: Upload the test evidence
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: test-results
          path: ${{ runner.temp }}/junit.xml
          if-no-files-found: error
"""

SUITE_LINE = 'python -m pytest -q -rs --junit-xml="$RUNNER_TEMP/junit.xml"'
SUITE_ENV = "        env:\n          PYTHONSAFEPATH: '1'\n"
SUITE_STEP = "      - name: Tests\n" + SUITE_ENV + "        run: " + SUITE_LINE + "\n"
GATE_STEP = (
    "      - name: Gate on the results\n        if: always()\n"
    '        run: python scripts/check_test_results.py "$RUNNER_TEMP/junit.xml"\n'
)
JOB_HEAD = "  tests:\n    name: Tests\n    runs-on: ubuntu-latest\n"
TRIGGER_LINE = '"on": [push, pull_request]'
COMPILE_LINE = "python -m compileall -q -f src scripts"
CLEAN_TREE_STEP = """\
      - name: Fail if the suite wrote into the working tree
        if: always()
        run: test -z "$(git status --porcelain)" || { git status --porcelain; echo '::error::dirty'; exit 1; }
"""
LEDGER_STEP = """\
      - name: Refuse a removed or rewritten hypothesis
        if: github.event_name == 'pull_request'
        env:
          BASE: ${{ github.event.pull_request.base.sha }}
        run: |
          set -euo pipefail
          git cat-file -e "${BASE}^{commit}" || { echo '::error::no base'; exit 1; }
          if git cat-file -e "${BASE}:data/outputs/experiment_ledger.json" 2>/dev/null; then
            TMP="$(mktemp)"
            git show "${BASE}:data/outputs/experiment_ledger.json" > "${TMP}"
            [ -s "${TMP}" ] || { echo '::error::empty base'; exit 1; }
            python scripts/check_ledger_append_only.py --base "${TMP}" --head data/outputs/experiment_ledger.json
          else
            python scripts/check_ledger_append_only.py --base-absent --head data/outputs/experiment_ledger.json
          fi
"""


def mutate(anchor: str, replacement: str, text: str = GOOD_WORKFLOW) -> str:
    assert anchor in text, f"anchor no longer in the control: {anchor!r}"
    return text.replace(anchor, replacement, 1)


def suite_block(*lines: str) -> str:
    body = "".join(f"          {line}\n" for line in lines)
    return mutate("        run: " + SUITE_LINE + "\n", "        run: |\n" + body)


def workflow(tmp_path: Path, text: str, name: str = "tests.yml") -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def assert_rejects(check: Callable[[Path], None], path: Path) -> None:
    with pytest.raises(AssertionError):
        check(path)


ALL_RULES = {**ALL_WORKFLOW_CHECKS, **EVIDENCE_RULES, **REQUIRED_CHECK_RULES}


@pytest.mark.parametrize("rule", sorted(ALL_RULES), ids=sorted(ALL_RULES))
def test_the_control_workflow_passes_every_rule(tmp_path: Path, rule: str) -> None:
    ALL_RULES[rule](workflow(tmp_path, GOOD_WORKFLOW))


#: One anchored substitution each. The rule that must reject it is named, so
#: a mutation caught by some OTHER rule does not count as proof of this one.
REJECTIONS: dict[str, tuple[str, str]] = {
    "job_renamed": ("the_required_check_job_is_pinned", mutate("    name: Tests\n", "    name: Suite\n")),
    "job_conditioned": ("the_required_check_job_is_pinned", mutate(JOB_HEAD, JOB_HEAD + "    if: github.event_name == 'schedule'\n")),
    "job_continue_on_error": ("the_required_check_job_is_pinned", mutate(JOB_HEAD, JOB_HEAD + "    continue-on-error: true\n")),
    "job_defaults_shell": ("the_required_check_job_is_pinned", mutate(JOB_HEAD, JOB_HEAD + "    defaults:\n      run:\n        shell: bash {0}\n")),
    "job_delegated": ("no_job_delegates_to_a_reusable_workflow", "name: Tests\n\"on\": [pull_request]\npermissions:\n  contents: read\njobs:\n  tests:\n    name: Tests\n    uses: someone/else/.github/workflows/x.yml@main\n"),
    "echo_in_place_of_pytest": ("the_suite_step_is_pinned", mutate(SUITE_LINE, "echo 'suite passed'")),
    "suite_step_if_false": ("the_suite_step_is_pinned", mutate(SUITE_STEP, "      - name: Tests\n        if: false\n" + SUITE_ENV + "        run: " + SUITE_LINE + "\n")),
    "suite_step_if_expression": ("the_suite_step_is_pinned", mutate(SUITE_STEP, "      - name: Tests\n        if: ${{ github.event_name == 'schedule' }}\n" + SUITE_ENV + "        run: " + SUITE_LINE + "\n")),
    "suite_step_continue_on_error": ("the_suite_step_is_pinned", mutate(SUITE_STEP, "      - name: Tests\n        continue-on-error: true\n" + SUITE_ENV + "        run: " + SUITE_LINE + "\n")),
    "suite_step_shell": ("the_suite_step_is_pinned", mutate(SUITE_STEP, "      - name: Tests\n        shell: bash {0}\n" + SUITE_ENV + "        run: " + SUITE_LINE + "\n")),
    "suite_step_working_directory": ("the_suite_step_is_pinned", mutate(SUITE_STEP, "      - name: Tests\n        working-directory: tests/fast\n" + SUITE_ENV + "        run: " + SUITE_LINE + "\n")),
    "narrowed_x": ("the_suite_step_is_pinned", mutate("pytest -q", "pytest -x -q")),
    "narrowed_cluster": ("the_suite_step_is_pinned", mutate("pytest -q", "pytest -qx")),
    "narrowed_exitfirst": ("the_suite_step_is_pinned", mutate("pytest -q", "pytest --exitfirst -q")),
    "narrowed_maxfail": ("the_suite_step_is_pinned", mutate("pytest -q", "pytest --maxfail=1 -q")),
    "narrowed_keyword": ("the_suite_step_is_pinned", mutate("pytest -q", "pytest -k 'not secrets' -q")),
    "narrowed_marker": ("the_suite_step_is_pinned", mutate("pytest -q", "pytest -m fast -q")),
    "narrowed_ignore": ("the_suite_step_is_pinned", mutate("pytest -q", "pytest --ignore=tests/test_no_secrets_committed.py -q")),
    "narrowed_deselect": ("the_suite_step_is_pinned", mutate("pytest -q", "pytest --deselect tests/test_workflows.py -q")),
    "narrowed_config": ("the_suite_step_is_pinned", mutate("pytest -q", "pytest -c ci.ini -q")),
    "narrowed_override_ini": ("the_suite_step_is_pinned", mutate("pytest -q", "pytest -o testpaths=tests/fast -q")),
    "narrowed_noconftest": ("the_suite_step_is_pinned", mutate("pytest -q", "pytest --noconftest -q")),
    "narrowed_plugin": ("the_suite_step_is_pinned", mutate("pytest -q", "pytest -p no:cacheprovider -q")),
    "narrowed_positional": ("the_suite_step_is_pinned", mutate("pytest -q", "pytest tests/test_gates.py -q")),
    "narrowed_runxfail": ("the_suite_step_is_pinned", mutate("pytest -q", "pytest --runxfail -q")),
    "narrowed_collect_only": ("the_suite_step_is_pinned", mutate("pytest -q", "pytest --co -q")),
    "no_junit": ("the_suite_step_is_pinned", mutate(SUITE_LINE, "python -m pytest -q -rs")),
    "addopts_step_env": ("pytest_addopts_is_set_nowhere", mutate(SUITE_STEP, "      - name: Tests\n        env:\n          PYTHONSAFEPATH: '1'\n          PYTEST_ADDOPTS: -x\n        run: " + SUITE_LINE + "\n")),
    "addopts_job_env": ("pytest_addopts_is_set_nowhere", mutate(JOB_HEAD, JOB_HEAD + "    env:\n      pytest_addopts: '-k fast'\n")),
    "addopts_workflow_env": ("pytest_addopts_is_set_nowhere", mutate("permissions:\n", "env:\n  PYTEST_ADDOPTS: --maxfail=1\npermissions:\n")),
    "addopts_exported": ("pytest_addopts_is_set_nowhere", suite_block("export PYTEST_ADDOPTS=-x", SUITE_LINE)),
    "addopts_github_env": ("pytest_addopts_is_set_nowhere", mutate(COMPILE_LINE, COMPILE_LINE + '\n          echo "PYTEST_ADDOPTS=-x" >> "$GITHUB_ENV"')),
    "pr_paths": ("the_pull_request_trigger_is_unfiltered", mutate(TRIGGER_LINE, '"on":\n  push:\n  pull_request:\n    paths: [src/**]')),
    "pr_paths_ignore": ("the_pull_request_trigger_is_unfiltered", mutate(TRIGGER_LINE, '"on":\n  push:\n  pull_request:\n    paths-ignore: [docs/**]')),
    "pr_branches": ("the_pull_request_trigger_is_unfiltered", mutate(TRIGGER_LINE, '"on":\n  push:\n  pull_request:\n    branches: [release]')),
    "no_pr_trigger": ("the_pull_request_trigger_is_unfiltered", mutate(TRIGGER_LINE, '"on": [push]')),
    "push_paths": ("no_trigger_is_path_filtered", mutate(TRIGGER_LINE, '"on":\n  push:\n    paths: [src/**]\n  pull_request:')),
    "swallow_if_not": ("no_run_block_swallows_a_failure", suite_block("if ! " + SUITE_LINE + "; then echo 'tests failed'; fi")),
    "swallow_or_true": ("no_run_block_swallows_a_failure", suite_block(SUITE_LINE + " || true")),
    "swallow_or_colon": ("no_run_block_swallows_a_failure", suite_block(SUITE_LINE + " || :")),
    "swallow_or_echo": ("no_run_block_swallows_a_failure", suite_block(SUITE_LINE + " || echo failed")),
    "swallow_set_plus_e": ("no_run_block_swallows_a_failure", suite_block("set +e", SUITE_LINE)),
    "swallow_set_plus_o": ("no_run_block_swallows_a_failure", suite_block("set +o errexit", SUITE_LINE)),
    "swallow_trap": ("no_run_block_swallows_a_failure", suite_block("trap 'exit 0' ERR", SUITE_LINE)),
    "swallow_if_else": ("no_run_block_swallows_a_failure", suite_block("if " + SUITE_LINE + "; then echo ok; else echo warn; fi")),
    "swallow_function": ("no_run_block_swallows_a_failure", suite_block("run() { \"$@\" || return 0; }", "run " + SUITE_LINE)),
    "swallow_background": ("no_run_block_swallows_a_failure", suite_block(SUITE_LINE + " &", "wait")),
    "swallow_pipeline": ("every_piped_run_block_sets_pipefail", suite_block(SUITE_LINE + " | tee log.txt")),
    "swallow_pipefail_off": ("every_piped_run_block_sets_pipefail", suite_block("set -euo pipefail", "set +o pipefail", SUITE_LINE + " | tee log.txt")),
    "swallow_process_substitution": ("no_run_block_swallows_a_failure", suite_block("tee log.txt < <(" + SUITE_LINE + ")")),
    "gate_deleted": ("the_suite_and_the_gate_are_both_present", mutate(GATE_STEP, "")),
    "gate_continue_on_error": ("no_step_or_job_continues_on_error", mutate("        if: always()\n        run: python scripts/check", "        if: always()\n        continue-on-error: true\n        run: python scripts/check")),
    "gate_if_false": ("no_condition_disables_the_chain", mutate("        if: always()\n        run: python scripts/check", "        if: false\n        run: python scripts/check")),
    "gate_elsewhere": ("the_gate_reads_the_evidence_this_run_wrote", mutate('check_test_results.py "$RUNNER_TEMP/junit.xml"', "check_test_results.py fixtures/green.xml")),
    "gate_planted": ("the_gate_reads_the_evidence_this_run_wrote", mutate(SUITE_STEP, SUITE_STEP + '      - name: Plant\n        run: cp fixtures/green.xml "$RUNNER_TEMP/junit.xml"\n')),
    "secret_referenced": ("no_workflow_references_a_secret", mutate(SUITE_STEP, "      - name: Tests\n        env:\n          PYTHONSAFEPATH: '1'\n          TOKEN: ${{ secrets.GITHUB_TOKEN }}\n        run: " + SUITE_LINE + "\n")),
    "secret_whole_context": ("no_workflow_references_a_secret", mutate(SUITE_STEP, "      - name: Tests\n        env:\n          PYTHONSAFEPATH: '1'\n          ALL: ${{ toJSON(secrets) }}\n        run: " + SUITE_LINE + "\n")),
    "credential_bound": ("no_env_mapping_binds_a_provider_credential", mutate(JOB_HEAD, JOB_HEAD + "    env:\n      FOOTBALL_ODDS_API_KEY: x\n")),
    "write_permission": ("permissions_are_declared_and_read_only", mutate("permissions:\n  contents: read\n", "permissions:\n  contents: write\n")),
    "no_permissions": ("permissions_are_declared_and_read_only", mutate("permissions:\n  contents: read\n\n", "")),
    "python_unpinned": ("python_version_is_pinned_to_an_exact_minor", mutate("python-version: '3.12'", "python-version: '3.x'")),
    "python_float": ("python_version_is_pinned_to_an_exact_minor", mutate("python-version: '3.12'", "python-version: 3.10")),
    "persist_credentials": ("checkout_never_persists_credentials", mutate("          persist-credentials: false\n", "")),
    "upload_warn": ("every_upload_fails_when_there_is_nothing_to_upload", mutate("if-no-files-found: error", "if-no-files-found: warn")),
    "shell_pwsh": ("no_workflow_overrides_the_shell", mutate(SUITE_STEP, "      - name: Tests\n        shell: pwsh\n" + SUITE_ENV + "        run: " + SUITE_LINE + "\n")),
    "workflow_defaults_shell": ("no_workflow_overrides_the_shell", mutate("permissions:\n", "defaults:\n  run:\n    shell: bash {0}\npermissions:\n")),
    "secrets_inherit": ("no_workflow_declares_a_secrets_key", "name: Tests\n\"on\": [pull_request]\npermissions:\n  contents: read\njobs:\n  tests:\n    name: Tests\n    uses: someone/x/.github/workflows/y.yml@main\n    secrets: inherit\n"),
    "compile_no_existence_check": ("the_compile_step_fails_on_a_missing_directory", mutate("          for d in src scripts; do\n            [ -d \"$d\" ] || { echo \"::error::$d is missing\"; exit 1; }\n          done\n", "")),
    "compile_no_force": ("the_compile_step_fails_on_a_missing_directory", mutate(COMPILE_LINE, "python -m compileall -q src scripts")),
    "compile_deleted": ("the_compile_step_fails_on_a_missing_directory", mutate(COMPILE_LINE, "python -c 'print(1)'")),
    "status_forced": ("the_step_status_is_never_forced", suite_block(SUITE_LINE + " || true")),
    "status_forced_reworded": ("the_step_status_is_never_forced", suite_block(SUITE_LINE + " || :")),
    "status_forced_wrapper": ("the_step_status_is_never_forced", suite_block("run() { \"$@\" || return 0; }", "run " + SUITE_LINE)),
    "secret_in_run": ("no_run_block_interpolates_the_secrets_context", suite_block('echo "${{ secrets.FOOTBALL_ODDS_API_KEY }}" > /dev/null', SUITE_LINE)),
    "git_add_all": ("no_workflow_stages_the_whole_working_tree", suite_block("git add -A", SUITE_LINE)),
    "git_add_dot": ("no_workflow_stages_the_whole_working_tree", suite_block("git add --all", SUITE_LINE)),
    "no_trigger": ("parses_and_declares_a_trigger", mutate(TRIGGER_LINE + "\n", "")),
    "no_name": ("parses_and_declares_a_trigger", mutate("name: Tests\n", "", )),

    # -- A. `needs:` is `if: false` reworded ------------------------------
    # GitHub reports a conditionally-skipped required check as Success. A
    # one-line `needs: prep` on the required job, where `prep` never runs,
    # skips the required job and turns the merge gate green over nothing.
    "job_needs_a_disabled_job": ("the_required_check_job_is_pinned", mutate(
        JOB_HEAD, "  prep:\n    name: Prep\n    if: false\n    runs-on: ubuntu-latest\n"
        "    steps:\n      - run: echo nothing\n" + JOB_HEAD + "    needs: prep\n")),
    "job_needs_anything_at_all": ("the_required_check_job_is_pinned", mutate(
        JOB_HEAD, "  prep:\n    name: Prep\n    runs-on: ubuntu-latest\n"
        "    steps:\n      - run: echo nothing\n" + JOB_HEAD + "    needs: [prep]\n")),
    "job_matrix": ("the_required_check_job_is_pinned", mutate(
        JOB_HEAD, JOB_HEAD + "    strategy:\n      matrix:\n        include: []\n")),
    "gate_step_rebinds_path": ("no_env_rebinds_the_interpreter", mutate(
        "      - name: Gate on the results\n        if: always()\n",
        "      - name: Gate on the results\n        if: always()\n        env:\n          PATH: /tmp/fake\n")),
    "suite_step_rebinds_pythonhome": ("no_env_rebinds_the_interpreter", mutate(
        "PYTHONSAFEPATH: '1'", "PYTHONSAFEPATH: '1'\n          PYTHONHOME: /tmp/fake")),
    "a_step_prepends_to_github_path": ("no_env_rebinds_the_interpreter", mutate(
        COMPILE_LINE, COMPILE_LINE + '\n          echo /tmp/fake >> "$GITHUB_PATH"')),
    "suite_line_carries_an_inline_assignment": ("the_suite_step_is_pinned", mutate(
        "run: python -m pytest", "run: PYTHONPATH=/tmp/fake python -m pytest")),
    "shallow_checkout": ("the_required_check_job_checks_out_history", mutate(
        "          fetch-depth: 0\n", "          fetch-depth: 1\n")),
    "no_checkout_at_all": ("the_required_check_job_checks_out_history", mutate(
        "      - name: Check out repository\n        uses: actions/checkout@v4\n        with:\n          fetch-depth: 0\n          persist-credentials: false\n", "")),
    "a_sibling_job_is_conditional": ("no_job_in_the_required_workflow_is_conditional", mutate(
        JOB_HEAD, "  prep:\n    name: Prep\n    if: false\n    runs-on: ubuntu-latest\n"
        "    steps:\n      - run: echo nothing\n" + JOB_HEAD)),

    # -- C. the suite line is a whitelist, and the junit is pinned ---------
    # Each of these exits 0 having run no test and written no junit file.
    "suite_version_short_circuit": ("the_suite_step_is_pinned", mutate("pytest -q", "pytest --version -q")),
    "suite_help_short_circuit": ("the_suite_step_is_pinned", mutate("pytest -q", "pytest --help -q")),
    "suite_h_short_circuit": ("the_suite_step_is_pinned", mutate("pytest -q", "pytest -h -q")),
    "suite_unlisted_flag": ("the_suite_step_is_pinned", mutate("pytest -q", "pytest --tb=no -q")),
    "junit_into_the_workspace": ("the_suite_step_is_pinned", mutate(
        '--junit-xml="$RUNNER_TEMP/junit.xml"', '--junit-xml="junit.xml"')),
    "junit_onto_a_tracked_path": ("the_suite_step_is_pinned", mutate(
        '--junit-xml="$RUNNER_TEMP/junit.xml"', '--junit-xml="conftest.py"')),
    "junit_flag_without_a_path": ("the_suite_step_is_pinned", mutate(
        '--junit-xml="$RUNNER_TEMP/junit.xml"', "--junit-xml")),
    "junit_climbs_out_of_runner_temp": ("the_suite_step_is_pinned", mutate(
        '--junit-xml="$RUNNER_TEMP/junit.xml"', '--junit-xml="$RUNNER_TEMP/../junit.xml"')),
    "two_junit_flags": ("the_suite_step_is_pinned", mutate(
        '--junit-xml="$RUNNER_TEMP/junit.xml"',
        '--junit-xml="$RUNNER_TEMP/junit.xml" --junitxml="$RUNNER_TEMP/junit.xml"')),

    # -- D. the gate step pinned as a whole command -----------------------
    "gate_no_opped_with_a_colon": ("the_gate_step_is_pinned", mutate(
        'run: python scripts/check_test_results.py "$RUNNER_TEMP/junit.xml"',
        'run: \': python scripts/check_test_results.py "$RUNNER_TEMP/junit.xml"\'')),
    "gate_echoed": ("the_gate_step_is_pinned", mutate(
        "run: python scripts/check_test_results.py",
        "run: echo python scripts/check_test_results.py")),
    "gate_replaced_by_cat": ("the_gate_step_is_pinned", mutate(
        "run: python scripts/check_test_results.py",
        "run: cat scripts/check_test_results.py")),
    "gate_given_a_second_command": ("the_gate_step_is_pinned", mutate(
        'run: python scripts/check_test_results.py "$RUNNER_TEMP/junit.xml"',
        'run: |\n          python scripts/check_test_results.py "$RUNNER_TEMP/junit.xml"\n'
        "          echo done")),

    # -- G. a step of the required job that GitHub skips -------------------
    # GitHub reports a job whose step was skipped as Success. Before
    # `no_step_of_the_required_job_is_conditional` existed, each of these
    # passed all twenty-nine rules — the conditional rule only read the steps
    # whose `run:` mentions pytest or the gate script.
    "compile_step_if_false": ("no_step_of_the_required_job_is_conditional", mutate(
        "      - name: Compile\n", "      - name: Compile\n        if: false\n")),
    "checkout_step_if_false": ("no_step_of_the_required_job_is_conditional", mutate(
        "      - name: Check out repository\n",
        "      - name: Check out repository\n        if: false\n")),
    "upload_step_if_false": ("no_step_of_the_required_job_is_conditional", mutate(
        "      - name: Upload the test evidence\n        if: always()\n",
        "      - name: Upload the test evidence\n        if: false\n")),
    "clean_tree_step_if_false": ("no_step_of_the_required_job_is_conditional", mutate(
        "      - name: Fail if the suite wrote into the working tree\n        if: always()\n",
        "      - name: Fail if the suite wrote into the working tree\n        if: false\n")),
    "ledger_step_if_false": ("no_step_of_the_required_job_is_conditional", mutate(
        "        if: github.event_name == 'pull_request'\n", "        if: false\n")),
    # The pull-request condition is legitimate on the append-only step and on
    # nothing else: on the compile step it switches that step off for every
    # push to main.
    "compile_step_narrowed_to_pull_requests": ("no_step_of_the_required_job_is_conditional", mutate(
        "      - name: Compile\n",
        "      - name: Compile\n        if: github.event_name == 'pull_request'\n")),

    # -- H. the two steps whose deletion nothing read ---------------------
    "clean_tree_step_deleted": ("the_clean_tree_step_is_present", mutate(CLEAN_TREE_STEP, "")),
    "clean_tree_verdict_ignored": ("the_clean_tree_step_is_present", mutate(
        CLEAN_TREE_STEP,
        "      - name: Fail if the suite wrote into the working tree\n        if: always()\n"
        "        run: git status --porcelain\n")),
    "ledger_step_deleted": ("the_append_only_step_is_present", mutate(LEDGER_STEP, "")),
    "ledger_step_echoed": ("the_append_only_step_is_present", mutate(
        "            python scripts/check_ledger_append_only.py --base",
        "            echo python scripts/check_ledger_append_only.py --base")),

    # -- F. the shadow-module belt ----------------------------------------
    "suite_without_safe_path": ("the_suite_step_is_pinned", mutate(SUITE_ENV, "")),
    "safe_path_switched_off": ("the_suite_step_is_pinned", mutate("PYTHONSAFEPATH: '1'", "PYTHONSAFEPATH: '0'")),
}


@pytest.mark.parametrize("case", sorted(REJECTIONS), ids=sorted(REJECTIONS))
def test_every_defeat_of_the_required_check_is_rejected(tmp_path: Path, case: str) -> None:
    rule, text = REJECTIONS[case]
    assert_rejects(ALL_RULES[rule], workflow(tmp_path, text))


def test_every_rule_has_a_case_that_proves_it_fires() -> None:
    proven = {rule for rule, _ in REJECTIONS.values()}
    unproven = sorted(set(ALL_RULES) - proven)
    assert not unproven, f"rules with no synthetic case proving they fire: {unproven}"


def test_a_second_job_named_tests_anywhere_is_rejected(tmp_path: Path) -> None:
    """The cross-file half: a job named `Tests` in another workflow is a second
    check run under the protected name."""
    workflow(tmp_path, GOOD_WORKFLOW)
    other = workflow(tmp_path, GOOD_WORKFLOW.replace("name: Tests\n", "name: Other\n", 1), "other.yml")
    found = [(p.name, j) for p in workflow_files_in(tmp_path) for j, _ in required_check_jobs(p)]
    assert found == [("other.yml", "tests"), ("tests.yml", "tests")]
    assert required_check_jobs(other)


def test_the_stub_harness_runs_nothing_real(tmp_path: Path) -> None:
    result = run_block_under_stubs("python -c 'import os; os.remove(\"/\")'\nrm -rf /\n", set(), tmp_path)
    assert result.exit_code == 0
    assert [c.word for c in result.invocations] == ["python", "rm"]
    assert "-rf /" in result.invocations[1].arguments
    assert not result.unmodelled


def test_the_stub_harness_does_not_sigpipe_its_own_pipelines(tmp_path: Path) -> None:
    """A guard that is red once in eight runs is a guard people re-run.

    A stub downstream of a pipe used to return without reading it, so the
    upstream stub took SIGPIPE and the block exited 141 — with `pipefail` on,
    that became the step's status and two rules about `... | tee` failed at
    random. Measured on this repository before the fix: 6 failures in 40 runs
    of `-k "degraded_path or refuses_to_run_without"`; after it, 0 in 40. The
    stubs now drain a piped stdin with shell builtins, which is what a real
    `tee` does.
    """
    block = 'set -euo pipefail\npython scripts/x.py | tee "$RUNNER_TEMP/log.txt"\n'
    for _ in range(30):
        result = run_block_under_stubs(block, set(), tmp_path)
        assert result.exit_code == 0, result
        assert [call.word for call in result.invocations] == ["python", "tee"]
    # ...and the pipeline still FAILS when the upstream really fails, so the
    # drain did not buy determinism by swallowing the thing being measured.
    # A pipeline element runs in a subshell, so the failure is recorded in
    # `any_failures` rather than `top_level_failures`; `pipefail` is what
    # carries it out to the block's status.
    failed = run_block_under_stubs(block, {"python"}, tmp_path)
    assert failed.exit_code != 0 and failed.any_failures == ["python"]


def test_the_stub_harness_reports_a_command_it_could_not_model(tmp_path: Path) -> None:
    result = run_block_under_stubs("eval 'mystery_cmd --flag'\n", set(), tmp_path)
    assert "mystery_cmd" in result.unmodelled
    assert swallow_findings("eval 'mystery_cmd'\n")


def test_the_stub_harness_distinguishes_top_level_from_substitution(tmp_path: Path) -> None:
    result = run_block_under_stubs('echo "$(git status)"\ngit fetch\n', None, tmp_path)
    assert [(c.top_level, c.line) for c in result.invocations] == [(False, 1), (True, 2)]
    assert result.top_level_failures == ["git"] and result.any_failures == ["git", "git"]


def test_a_failure_can_be_injected_at_one_call_site(tmp_path: Path) -> None:
    block = "git fetch || true\ngit status\n"
    result = run_block_under_stubs(block, set(), tmp_path, failing_sites={("git", 2)})
    assert result.exit_code == 1
    assert [c.line for c in result.invocations] == [1, 2]
    assert result.top_level_failures == ["git"]
    result = run_block_under_stubs(block, set(), tmp_path, failing_sites={("git", 1)})
    assert result.exit_code == 0 and result.top_level_failures == ["git"]


def test_the_status_forcing_rule_keeps_the_repositorys_legitimate_shapes() -> None:
    """The lab's own idiom, tolerated on purpose: an expected non-zero inside
    a substitution, and a failure handled by the lines that follow."""
    assert status_forcing_findings(
        "for f in $(git ls-tree -r --name-only tip | grep '^snapshots/' || true); do\n  echo \"$f\"\ndone\n"
    ) == []
    assert status_forcing_findings(
        'git fetch --depth=1 "$REMOTE" tip 2>/dev/null || true\n'
        'if git cat-file -e tip:ledger.csv 2>/dev/null; then echo yes; fi\n'
    ) == []
    # ...and the exact line that was in weekly-ledger-check.yml, plus its
    # rewordings, are findings.
    for swallow in (
        "PYTHONPATH=src python scripts/fetch_football_data.py --only schedules || true",
        'cat data/outputs/card.md >> "$GITHUB_STEP_SUMMARY" || true',
        "python scripts/x.py || :",
        "python scripts/x.py || echo failed",
        "trap 'exit 0' ERR\npython scripts/x.py",
        "set +e\npython scripts/x.py\necho done",
        "run() { \"$@\" || return 0; }\nrun python scripts/x.py",
        "git fetch || true\ngit status || true",
    ):
        assert status_forcing_findings(swallow + "\n"), swallow
    # ...and two shapes that look like swallows and are not, measured: under
    # `bash -e` the step fails on both.
    for honest in ("python scripts/x.py; true", "set +e\npython scripts/x.py",
                   "python scripts/x.py && true",
                   "python -m pip install -r requirements.txt && python -m pip install -e ."):
        assert status_forcing_findings(honest + "\n") == [], honest


# --------------------------------------------------------------------------
# The Ledger Guard's base resolution, driven with the input that made it red.
# --------------------------------------------------------------------------

ALL_ZEROS = "0" * 40


def _resolve_step() -> dict:
    document = load(WORKFLOW_DIR / "ledger-guard.yml")
    steps = [s for job in jobs_of(document).values() for s in steps_of(job)
             if s.get("id") == "base"]
    assert len(steps) == 1, "ledger-guard.yml has no single `id: base` step to drive"
    return steps[0]


def _git(directory: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments], cwd=directory, capture_output=True, text=True,
        env=dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
                 GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid"),
    )
    assert completed.returncode == 0, (arguments, completed.stderr)
    return completed.stdout.strip()


def test_a_branchs_first_push_resolves_a_base_instead_of_going_red(tmp_path: Path) -> None:
    """The false red, driven against REAL git rather than against stubs.

    On a branch's first push `github.event.before` is forty zeros, because the
    ref did not exist. The resolve step treated that as an unresolvable base
    and stopped — so every new branch's first push was red, and a check that
    is red on every first push is one people learn to scroll past.

    Here the step's own script is run, with real git, in a repository with a
    real `origin/main` and a real branch off it. It must exit 0 and write the
    merge base — the commit the push actually built on — to `$GITHUB_OUTPUT`.
    """
    upstream = tmp_path / "upstream"
    upstream.mkdir()
    _git(upstream, "init", "-q", "-b", "main")
    (upstream / "ledger.json").write_text("{}\n", encoding="utf-8")
    _git(upstream, "add", "ledger.json")
    _git(upstream, "commit", "-q", "-m", "base")
    base_sha = _git(upstream, "rev-parse", "HEAD")

    clone = tmp_path / "clone"
    _git(tmp_path, "clone", "-q", str(upstream), str(clone))
    _git(clone, "checkout", "-q", "-b", "a-new-branch")
    (clone / "ledger.json").write_text('{"hypotheses": []}\n', encoding="utf-8")
    _git(clone, "commit", "-q", "-am", "a first commit on a new branch")

    # The base commit is real and reachable; the all-zeros sha is not, which
    # is exactly why `git cat-file -e` on it used to end the run.
    assert _git(clone, "merge-base", "HEAD", "origin/main") == base_sha
    unreachable = subprocess.run(
        ["git", "cat-file", "-e", f"{ALL_ZEROS}^{{commit}}"],
        cwd=clone, capture_output=True,
    )
    assert unreachable.returncode != 0

    script = tmp_path / "resolve.sh"
    script.write_text(render_expressions(_resolve_step()["run"]), encoding="utf-8")
    output = tmp_path / "github_output"
    output.write_text("", encoding="utf-8")
    completed = subprocess.run(
        [HARNESS_SHELL, "-e", str(script)], cwd=clone, capture_output=True, text=True,
        env=dict(os.environ, EVENT_NAME="push", PUSH_BEFORE_SHA=ALL_ZEROS,
                 PR_BASE_SHA="", GITHUB_OUTPUT=str(output)),
        timeout=60,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert f"sha={base_sha}" in output.read_text(encoding="utf-8"), output.read_text()
    assert "First push of this ref" in completed.stdout


def test_every_other_unresolvable_base_is_still_a_hard_stop(tmp_path: Path) -> None:
    """Fail-closed was the right instinct in the wrong place, and it stays.

    A sha that is not all zeros and that git cannot resolve — a force-pushed
    range, a shallow clone, a typo — must still stop the run. So must an empty
    base and an event this step does not handle. Absence is never a pass.
    """
    upstream = tmp_path / "upstream"
    upstream.mkdir()
    _git(upstream, "init", "-q", "-b", "main")
    (upstream / "ledger.json").write_text("{}\n", encoding="utf-8")
    _git(upstream, "add", "ledger.json")
    _git(upstream, "commit", "-q", "-m", "base")
    clone = tmp_path / "clone"
    _git(tmp_path, "clone", "-q", str(upstream), str(clone))

    script = tmp_path / "resolve.sh"
    script.write_text(render_expressions(_resolve_step()["run"]), encoding="utf-8")
    output = tmp_path / "github_output"

    cases = {
        "a sha git does not have": {"EVENT_NAME": "push", "PUSH_BEFORE_SHA": "d" * 40},
        "an empty base": {"EVENT_NAME": "push", "PUSH_BEFORE_SHA": ""},
        "an unhandled event": {"EVENT_NAME": "issue_comment", "PUSH_BEFORE_SHA": "d" * 40},
        "a pull request with no base": {"EVENT_NAME": "pull_request", "PR_BASE_SHA": ""},
    }
    for label, environment in cases.items():
        output.write_text("", encoding="utf-8")
        env = dict(os.environ)
        env.update(EVENT_NAME="push", PUSH_BEFORE_SHA="", PR_BASE_SHA="",
                   GITHUB_OUTPUT=str(output))
        env.update(environment)
        completed = subprocess.run(
            [HARNESS_SHELL, "-e", str(script)], cwd=clone, capture_output=True, text=True,
            env=env, timeout=60,
        )
        assert completed.returncode != 0, (label, completed.stdout, completed.stderr)
        assert "NOT evidence that the ledger is intact" in completed.stdout, (label, completed.stdout)
        assert "sha=" not in output.read_text(encoding="utf-8"), label


def test_the_first_push_branch_still_stops_when_origin_main_cannot_be_reached(tmp_path: Path) -> None:
    """The new branch is not a new way to pass without comparing anything.

    All-zeros with no reachable `origin/main` is still unresolvable, and still
    a hard stop — the fix widened what CAN be resolved, not what counts as a
    pass.
    """
    lonely = tmp_path / "lonely"
    lonely.mkdir()
    _git(lonely, "init", "-q", "-b", "main")
    (lonely / "ledger.json").write_text("{}\n", encoding="utf-8")
    _git(lonely, "add", "ledger.json")
    _git(lonely, "commit", "-q", "-m", "only commit, no remote")

    script = tmp_path / "resolve.sh"
    script.write_text(render_expressions(_resolve_step()["run"]), encoding="utf-8")
    output = tmp_path / "github_output"
    output.write_text("", encoding="utf-8")
    completed = subprocess.run(
        [HARNESS_SHELL, "-e", str(script)], cwd=lonely, capture_output=True, text=True,
        env=dict(os.environ, EVENT_NAME="push", PUSH_BEFORE_SHA=ALL_ZEROS,
                 PR_BASE_SHA="", GITHUB_OUTPUT=str(output)),
        timeout=60,
    )
    assert completed.returncode != 0, completed.stdout + completed.stderr
    assert "NOT evidence that the ledger is intact" in completed.stdout
    assert "sha=" not in output.read_text(encoding="utf-8")


def test_the_disclosed_holes_are_real(tmp_path: Path) -> None:
    """What still gets through, asserted open so it goes red when closed.

    * In an OPERATIONAL workflow, a swallow that is not the final simple
      statement of the block. `if ! git fetch; then warn; exit 0; fi` — mid
      block or as the last statement — is permitted by the lab's own rule
      (a handled failure), and the executed version of that rule fails only
      the final simple statement's command. The evidence workflows get the
      full rule, under which the same line IS a finding.
    * A leak the canary cannot see: the credential read by a Python script
      and printed by it. The stubs do not run python; that is the secrets
      guard's and the provider code's territory, not this file's.
    * A failure inside `$(...)`, a pipeline element, or a `( )` subshell is
      invisible to errexit and therefore to the executed rule; the textual
      or-list net covers the `( cmd ) || true` shape for the evidence
      workflows only.
    * In an OPERATIONAL workflow, `set +e` before an earlier command, or any
      swallow of a command that is not the final one. Same rule, same reason.
    * A launcher the harness does not name (`systemd-run`, `at`, a wrapper
      script that forks) detaches a command the same way `setsid` does.
    * A shell that is not bash. `shell:` is refused unless it is bare
      `bash`/`sh`, but `sh` on the runner is dash, and the harness grades
      every block under bash.

    Added 2026-09-04, after attacking this round's own fixes:

    * BRANCH PROTECTION ITSELF is not in this repository. Every rule here
      pins the workflow that PRODUCES the `Tests` context; whether that
      context is still required on `main`, and whether administrators are
      still included, lives in the repository settings and is Cooper's to
      change. `REQUIRED_CHECK_CONTEXT` is held as a literal so a rename in
      the workflow goes red rather than adapting, which is the most this file
      can do about it.
    * THE EVIDENCE WINDOW IS SIX HOURS, not "this job". A junit written into
      `$RUNNER_TEMP` by an earlier step of the same job, under a spelling
      `check_the_gate_reads_the_evidence_this_run_wrote` does not recognise
      as the same path, is inside the window and would be read as this run's.
      The path pin and the tracked-path pin are what stand between that and a
      committed junit; the timestamp only rules out the stale one.
    * A PLANT THROUGH A SHELL VARIABLE. The rules above read the junit path as
      it is WRITTEN on the line. A step that puts the path in a variable first
      —  `D="$RUNNER_TEMP"; cp fixtures/green.xml "$D/junit.xml"` — names no
      literal the rule can match, and is refused by none of them. The literal
      form (`gate_planted` in REJECTIONS) is caught. tests.yml's header used
      to say a committed junit could not stand in as this run's evidence; it
      now says what is actually pinned. The report's timestamp is the thing
      that would still have to be got past, and it is a six-hour window rather
      than a proof of origin.
    * A GUARD THAT RUNS AND ASSERTS NOTHING. Every floor in the repository is
      a count, and `assert True` satisfies a count. See
      `tests/test_the_guards_exist.py::test_known_gaps_in_the_guard_floors`.
    * `concurrency: cancel-in-progress` is permitted, deliberately: a
      cancelled required check is not a Success, so a superseded run being
      cancelled blocks a merge rather than clearing one. So is
      `timeout-minutes`, for the same reason — a timed-out job is red.
    * A TRACKED PACKAGE ON A DECLARED PYTHONPATH ENTRY still shadows the real
      one, because `PYTHONSAFEPATH` removes the working directory from
      `sys.path` and not the PYTHONPATH entries. Measured: a tracked
      `src/pytest/__init__.py` makes `python -m pytest` fail with `No module
      named pytest.__main__` and a non-zero exit. That is fail-CLOSED — the
      step is red — and `tests/test_the_guards_exist.py` names the directory
      as well, so this is a loud gap rather than a silent one.
    * THE LEDGER GUARD'S BASE-ABSENT BRANCH. On a first push whose merge base
      with `origin/main` holds no ledger, the guard takes the `--base-absent`
      path, which validates the head and compares nothing. Measured against a
      real repository built for it: the resolve step exits 0 and reports the
      merge base. On this repository main always carries the ledger, so the
      branch is reachable only from a history that never had one.
    """
    assert status_forcing_findings(
        "if ! git fetch origin card-feed; then echo '::warning::no branch'; exit 0; fi\npython scripts/x.py\n"
    ) == []
    assert status_forcing_findings("if ! python scripts/x.py; then echo failed; fi\n") == []
    assert swallow_findings("if ! python scripts/x.py; then echo failed; fi\n")
    # `set +e` before an EARLIER command, followed by a later command that
    # succeeds, is a swallow the operational rule does not see and the
    # evidence rule does.
    assert status_forcing_findings("set +e\npython scripts/a.py\npython scripts/b.py\n") == []
    assert swallow_findings("set +e\npython scripts/a.py\npython scripts/b.py\n")
    assert swallow_findings("X=\"$(python scripts/x.py)\"\necho \"$X\"\n") == []
    assert swallow_findings("( python scripts/x.py ) || true\n") == []
    assert not [c for c in run_block_under_stubs(
        'python -c "import os; print(os.environ[\'FOOTBALL_ODDS_API_KEY\'])"\n', set(), tmp_path,
        environment={"FOOTBALL_ODDS_API_KEY": CANARY},
    ).invocations if CANARY in c.arguments]

    # The plant through a shell variable, run rather than described: the
    # literal form is refused and the variable form is not.
    literal = workflow(tmp_path, mutate(
        SUITE_STEP,
        SUITE_STEP + '      - name: Plant\n        run: cp green.xml "$RUNNER_TEMP/junit.xml"\n',
    ), "literal_plant.yml")
    assert_rejects(check_the_gate_reads_the_evidence_this_run_wrote, literal)
    through_a_variable = workflow(tmp_path, mutate(
        SUITE_STEP,
        SUITE_STEP + "      - name: Plant\n        run: |\n"
        '          D="$RUNNER_TEMP"\n          cp green.xml "$D/junit.xml"\n',
    ), "variable_plant.yml")
    for rule in ALL_RULES.values():
        rule(through_a_variable)  # asserted OPEN: no rule here refuses it

    # Branch protection is outside this repository: the most these rules can
    # do is pin the name and refuse to adapt when it drifts.
    assert REQUIRED_CHECK_CONTEXT == "Tests"
    assert not any(
        "branch" in name and "protection" in name for name in ALL_RULES
    ), "a rule claiming to check branch protection would be checking nothing"

    # `concurrency` and `timeout-minutes` are permitted on the required job:
    # neither produces a Success, so neither clears a merge.
    for permitted in ("concurrency", "timeout-minutes"):
        good = workflow(tmp_path, mutate(JOB_HEAD, JOB_HEAD + f"    {permitted}: 1\n"
                                         if permitted == "timeout-minutes"
                                         else JOB_HEAD + "    concurrency:\n      group: t\n"),
                        "permitted.yml")
        check_the_required_check_job_is_pinned(good)

    # The evidence window is six hours, not "this job" — read off the gate
    # script rather than restated here, so the two cannot drift.
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "check_test_results", PROJECT_ROOT / "scripts" / "check_test_results.py")
    assert spec is not None and spec.loader is not None
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    assert gate.MAXIMUM_EVIDENCE_AGE.total_seconds() > 60 * 60
