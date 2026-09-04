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

* STRUCTURE — exactly one job in the repository carries `name: Tests`; it and
  its suite step carry no `if:` (bar `always()` on the gate), no
  `continue-on-error`, no `shell:` override and no `defaults.run.shell`; the
  pytest invocation has no narrowing flag and no positional; `PYTEST_ADDOPTS`
  appears in no `env:` and no run block; the `pull_request` trigger carries
  no `paths:`, `paths-ignore:` or `branches:`; and the junit path pytest
  writes is the path the gate reads, with nothing in between writing it.
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
#: matches it under — the JOB's `name:`. Verified against the repository's
#: protection rule on 2026-09-04; if that rule changes, this changes with it.
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
    for forbidden in ("if", "continue-on-error", "uses", "defaults", "container", "strategy"):
        assert forbidden not in job, f"{path.name}: job {job_id!r} carries `{forbidden}:`."
    assert isinstance(job.get("runs-on"), str), f"{path.name}: job {job_id!r} has no plain `runs-on`."
    assert steps_of(job), f"{path.name}: job {job_id!r} has no steps."


def check_the_suite_step_is_pinned(path: Path) -> None:
    """The one step that runs pytest: present, unconditional, unnarrowed."""
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
    assert re.match(r"^(?:PYTHONPATH=\S+\s+)?python(?:3)?\s+-m\s+pytest\b", line), (
        f"{path.name}: the suite is not invoked as `python -m pytest`: {line!r}"
    )
    arguments = pytest_arguments(line)
    for argument in arguments:
        assert argument.startswith("-"), (
            f"{path.name}: pytest is passed the positional {argument!r}, which selects a subset."
        )
        if argument.startswith("--"):
            assert argument.split("=", 1)[0] not in NARROWING_PYTEST_LONG_FLAGS, (
                f"{path.name}: pytest is narrowed with {argument}"
            )
        elif argument != "-":
            cluster = set(argument[1:].split("=", 1)[0])
            assert not (cluster & NARROWING_PYTEST_SHORT_FLAGS), f"{path.name}: pytest is narrowed with {argument}"
    assert any(a.split("=", 1)[0] in JUNIT_FLAGS for a in arguments), (
        f"{path.name}: the suite writes no junit file, so the gate has nothing to read."
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


REQUIRED_CHECK_RULES: dict[str, Callable[[Path], None]] = {
    "the_required_check_job_is_pinned": check_the_required_check_job_is_pinned,
    "the_suite_step_is_pinned": check_the_suite_step_is_pinned,
    "pytest_addopts_is_set_nowhere": check_pytest_addopts_is_set_nowhere,
    "the_pull_request_trigger_is_unfiltered": check_the_pull_request_trigger_is_unfiltered,
    "the_compile_step_fails_on_a_missing_directory": check_the_compile_step_fails_on_a_missing_directory,
    "the_suite_and_the_gate_are_both_present": check_the_suite_and_the_gate_are_both_present,
    "the_gate_reads_the_evidence_this_run_wrote": check_the_gate_reads_the_evidence_this_run_wrote,
    "no_condition_disables_the_chain": check_no_condition_disables_the_chain,
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
          fetch-depth: 1
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
        run: python -m pytest -q -rs --junit-xml="$RUNNER_TEMP/junit.xml"
      - name: Gate on the results
        if: always()
        run: python scripts/check_test_results.py "$RUNNER_TEMP/junit.xml"
      - name: Upload the test evidence
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: test-results
          path: ${{ runner.temp }}/junit.xml
          if-no-files-found: error
"""

SUITE_LINE = 'python -m pytest -q -rs --junit-xml="$RUNNER_TEMP/junit.xml"'
SUITE_STEP = "      - name: Tests\n        run: " + SUITE_LINE + "\n"
GATE_STEP = (
    "      - name: Gate on the results\n        if: always()\n"
    '        run: python scripts/check_test_results.py "$RUNNER_TEMP/junit.xml"\n'
)
JOB_HEAD = "  tests:\n    name: Tests\n    runs-on: ubuntu-latest\n"
TRIGGER_LINE = '"on": [push, pull_request]'
COMPILE_LINE = "python -m compileall -q -f src scripts"


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
    "suite_step_if_false": ("the_suite_step_is_pinned", mutate(SUITE_STEP, "      - name: Tests\n        if: false\n        run: " + SUITE_LINE + "\n")),
    "suite_step_if_expression": ("the_suite_step_is_pinned", mutate(SUITE_STEP, "      - name: Tests\n        if: ${{ github.event_name == 'schedule' }}\n        run: " + SUITE_LINE + "\n")),
    "suite_step_continue_on_error": ("the_suite_step_is_pinned", mutate(SUITE_STEP, "      - name: Tests\n        continue-on-error: true\n        run: " + SUITE_LINE + "\n")),
    "suite_step_shell": ("the_suite_step_is_pinned", mutate(SUITE_STEP, "      - name: Tests\n        shell: bash {0}\n        run: " + SUITE_LINE + "\n")),
    "suite_step_working_directory": ("the_suite_step_is_pinned", mutate(SUITE_STEP, "      - name: Tests\n        working-directory: tests/fast\n        run: " + SUITE_LINE + "\n")),
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
    "addopts_step_env": ("pytest_addopts_is_set_nowhere", mutate(SUITE_STEP, "      - name: Tests\n        env:\n          PYTEST_ADDOPTS: -x\n        run: " + SUITE_LINE + "\n")),
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
    "secret_referenced": ("no_workflow_references_a_secret", mutate(SUITE_STEP, "      - name: Tests\n        env:\n          TOKEN: ${{ secrets.GITHUB_TOKEN }}\n        run: " + SUITE_LINE + "\n")),
    "secret_whole_context": ("no_workflow_references_a_secret", mutate(SUITE_STEP, "      - name: Tests\n        env:\n          ALL: ${{ toJSON(secrets) }}\n        run: " + SUITE_LINE + "\n")),
    "credential_bound": ("no_env_mapping_binds_a_provider_credential", mutate(JOB_HEAD, JOB_HEAD + "    env:\n      FOOTBALL_ODDS_API_KEY: x\n")),
    "write_permission": ("permissions_are_declared_and_read_only", mutate("permissions:\n  contents: read\n", "permissions:\n  contents: write\n")),
    "no_permissions": ("permissions_are_declared_and_read_only", mutate("permissions:\n  contents: read\n\n", "")),
    "python_unpinned": ("python_version_is_pinned_to_an_exact_minor", mutate("python-version: '3.12'", "python-version: '3.x'")),
    "python_float": ("python_version_is_pinned_to_an_exact_minor", mutate("python-version: '3.12'", "python-version: 3.10")),
    "persist_credentials": ("checkout_never_persists_credentials", mutate("          persist-credentials: false\n", "")),
    "upload_warn": ("every_upload_fails_when_there_is_nothing_to_upload", mutate("if-no-files-found: error", "if-no-files-found: warn")),
    "shell_pwsh": ("no_workflow_overrides_the_shell", mutate(SUITE_STEP, "      - name: Tests\n        shell: pwsh\n        run: " + SUITE_LINE + "\n")),
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
