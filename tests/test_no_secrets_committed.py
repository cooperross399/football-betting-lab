"""Repository hygiene: no credential may reach a tracked file.

These tests run against the files git actually tracks, so they fail the build
if a secret is ever committed — including by a future change that means well.
They deliberately do not read `.env`: the point is to prove nothing *else*
contains a credential, and reading the real key here would be the very leak
being guarded against.

Ported from the EPL lab, and then repaired, because the port carried five ways
past it that an audit reproduced on this lab with the suite green:

* any file whose name contained "checksum" or "receipt" was skipped from the
  hex scan outright, so identical bytes passed as `week3_receipt.md` and
  failed as `week3.md`;
* the key-shape matcher was `\\b[0-9a-f]{32}\\b`, so one underscore of
  adjacent context (`<key>_odds.json` in a string) hid a key, and so did
  uppercasing it;
* only bodies were scanned, and only the bodies of files whose suffix was not
  binary, so a key in a *filename* — any filename, `docs/<key>.png` included —
  was read by nothing, and a tracked symlink whose target was the key was
  dropped by `path.is_file()`;
* the event-id exemption harvested filename stems from EVERY tracked file
  before any directory restriction, so a decoy `<key>_x.md` at the repository
  root nominated the key into the exemption set and turned it green
  everywhere;
* the assignment scan knew `NAME=value` and nothing else: not
  `os.environ["NAME"] = "..."`, not YAML's `NAME: value`, not `:=`, not a
  Unicode blank after the operator — and it exempted every `.md`, `.rst` and
  `.txt` from the assignment scan unless the value happened to be 32 hex
  characters.

Every one of those is pinned below by a test that fails against the module as
it was. The rewordings that STILL get past this module are listed in
`test_the_gaps_this_guard_still_has_are_the_ones_written_down` rather than
left to be rediscovered — including the one this lab cannot close cheaply: the
bet tables under `data/outputs/` carry provider event ids from a purchase
cache that `.gitignore` keeps untracked, so their `event_id` column has to be
allowed to nominate an exemption, and a key written into that column is
indistinguishable from an event id. That is named, bounded to two files by
name and one column, and asserted. When you change a rule in here, attack the
new rule with three spellings of the same leak before believing it.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import unicodedata
from collections.abc import Iterable
from pathlib import Path

import pytest

from football_betting_lab.config import PROJECT_ROOT
from football_betting_lab.providers.env_file import ENV_FILENAME, PROVIDER_ENV_ALLOWLIST


#: Obvious placeholders that must never be mistaken for a real credential.
#:
#: This is the whole allowance documentation gets. There used to be a second,
#: much wider one — any `.md`, `.rst` or `.txt` value that was not 32 hex
#: characters was skipped outright — and that was a route by which a live key
#: could sit in a tracked Markdown file: it waved through every value shape
#: but one. Prose that wants to show the form of the command writes a
#: placeholder from this set or a reference (`$VAR`, `<your-key>`,
#: `${{ secrets.X }}`), both of which stay allowed everywhere.
PLACEHOLDERS = {
    "your-secret-key",
    "your-api-key",
    "test-secret-that-must-not-be-written",
    "env-file-secret-that-must-never-be-written",
    "shadow-test-secret-never-write",
    "discovery-secret-must-not-be-written",
    "props-secret-must-not-be-written",
    "already-exported-value",
    "${{",
}

#: A 32-hex-character run is the shape of an Odds API key.
#:
#: The fence is a pair of lookarounds and not `\b`. `\b` will not open beside
#: `_`, because `_` is a word character — and the provider cache names its
#: files `<event id>_<stamp>.json`, the convention an attacker would copy. The
#: lookarounds still refuse to fire inside a longer hex run, so a SHA-256 is
#: not a finding. `A-F` as well as `a-f` because an uppercased copy of a key
#: is the same key; while the class was lowercase only, `KEY = "<the key,
#: uppercased>"` was invisible.
HEX_KEY = re.compile(r"(?<![0-9a-fA-F])[0-9a-fA-F]{32}(?![0-9a-fA-F])")

#: ...and it is also the shape of an Odds API **event id**, which is a real
#: collision rather than a theoretical one: the retention probe's cache and
#: its record are full of them, and so are the bet tables.
#:
#: Exempting the directories they live in would be the easy fix and the wrong
#: one — it would carve a hole in the guard exactly where provider data lands.
#: So the exemption is by *value*: every event id this repository has actually
#: recorded is collected from the provider artifacts and those literals alone
#: are allowed. Any other 32-hex run is still a finding.
#:
#: Where the record may come FROM is the part that was wrong. `_collect_event_ids`
#: reads a body under `data/raw/` — the provider's own cache, tracked here
#: because the probe responses are bought evidence — and the `event_id` column
#: of the two `NOMINATING_TABLES`. It used to read stems off every tracked
#: filename in the repository, which let a decoy file CREATE the exemption a
#: hardcoded key then spent. A filename is a claim; only a body is a record.
_EVENT_ID_KEYS = ("id", "event_id")

#: Where a recorded event id may be *spent*: the provider cache and the
#: reports rendered from it. Nothing outside these has an innocent reason to
#: carry a provider event id, so nothing outside them gets to spend one — an
#: event id recorded in a report does not excuse the same hex run in
#: `scripts/`. This is a spend rule and only a spend rule; creating an
#: exemption is governed by `_collect_event_ids`.
EXEMPT_SCOPE = ("data/raw/", "data/outputs/")

#: The two tables this repository writes from the bought-price cache, which
#: `.gitignore` keeps untracked (`data/raw/nfl/historical_prices/`). Their
#: `event_id` column is the only place outside `data/raw/` that may nominate an
#: exemption, and it is named by file rather than by directory so that a
#: hand-committed `data/outputs/anything.json` cannot. `run_props_replication.py`
#: and `run_team_ladder_backtest.py` are the writers. The cost is stated in
#: the known-gaps ledger: a key written into this column, in one of these two
#: files, is indistinguishable from an event id.
NOMINATING_TABLES = (
    "data/outputs/nfl_props_backtest_bets.csv",
    "data/outputs/nfl_team_ladder_bets.csv",
)

#: Digests this repository has a recorded reason to allow, each with the file
#: it was read from. Empty because no tracked file needs one. This replaces
#: the by-name skip of any file called "checksum" or "receipt", which exempted
#: every 32-hex run in such a file — a real key included.
RECORDED_DIGESTS: frozenset[str] = frozenset()

#: The GitHub secret holding this lab's provider credential. The **name**
#: belongs in the repository — it is a contract string — and the **value**
#: never does. Here it is the same name the provider code reads.
GITHUB_SECRET_NAME = "FOOTBALL_ODDS_API_KEY"

#: The shape of a credential variable name, used to find names this guard has
#: not been taught. The suffix alternation is not decoration: `_API_KEY` alone
#: recognises one spelling, and a credential named `..._APIKEY` or
#: `..._API_TOKEN` would be invisible to both the drift guard and the
#: assignment scan.
CREDENTIAL_NAME_SHAPE = re.compile(
    r"\b[A-Z][A-Z0-9_]*_(?:API_KEY|APIKEY|API_TOKEN)\b"
)

#: Credential names the docs of this lab MENTION that belong to sibling labs
#: or upstream providers. Known here so an assignment of any of them is a
#: finding too; none may ever be valued in this repository.
FOREIGN_CREDENTIAL_NAMES: tuple[str, ...] = ("NHL_ODDS_API_KEY", "CFBD_API_KEY")

#: Every credential-ish variable name a tracked file may mention but never
#: assign. Only the credential-shaped members of `PROVIDER_ENV_ALLOWLIST` —
#: `FOOTBALL_ODDS_API_BASE_URL` is in the allowlist and is a URL, not a
#: credential, and a base URL written in prose is not a leak.
CREDENTIAL_NAMES: tuple[str, ...] = tuple(
    dict.fromkeys(
        (
            *(name for name in PROVIDER_ENV_ALLOWLIST if CREDENTIAL_NAME_SHAPE.fullmatch(name)),
            GITHUB_SECRET_NAME,
            *FOREIGN_CREDENTIAL_NAMES,
        )
    )
)


def _collect_event_ids(
    paths: Iterable[Path], root: Path
) -> tuple[set[str], set[str]]:
    """Split recorded event ids by how strong the evidence for them is.

    `content_ids` come out of a response body under `data/raw/` or the
    `event_id` column of a `NOMINATING_TABLES` file — the provider put them
    there, so they are a record. `name_ids` come off a filename under
    `data/raw/`, which anyone can choose, so they are a claim. Only
    `content_ids` is ever allowed to exempt a hex run; `name_ids` exists to be
    checked against it. A file anywhere else nominates nothing — that is the
    self-nomination hole, and it is closed here rather than in the spend rule.
    """
    content_ids: set[str] = set()
    name_ids: set[str] = set()

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in _EVENT_ID_KEYS and isinstance(value, str):
                    if HEX_KEY.fullmatch(value):
                        content_ids.add(value)
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    def csv_ids(path: Path, columns_wanted: tuple[str, ...]) -> None:
        try:
            header, *rows = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError, ValueError):
            return
        columns = [name.strip() for name in header.split(",")]
        wanted = [index for index, name in enumerate(columns) if name in columns_wanted]
        if not wanted:
            return
        for row in rows:
            cells = row.split(",")
            for index in wanted:
                if index < len(cells) and HEX_KEY.fullmatch(cells[index].strip()):
                    content_ids.add(cells[index].strip())

    for path in paths:
        relative = path.relative_to(root).as_posix()
        if relative in NOMINATING_TABLES:
            csv_ids(path, ("event_id",))
            continue
        if not relative.startswith("data/raw/"):
            # Creating an exemption is the provider cache's privilege alone.
            # `EXEMPT_SCOPE` says where one may be *spent*; using it here too
            # let a tracked report nominate the literal it wanted exempted,
            # and reading stems repo-wide let any file anywhere do the same.
            continue
        stem = path.name.split("_")[0]
        if HEX_KEY.fullmatch(stem):
            name_ids.add(stem)
        if path.suffix == ".json":
            try:
                walk(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, UnicodeError, json.JSONDecodeError):
                continue
        elif path.suffix == ".csv":
            csv_ids(path, _EVENT_ID_KEYS)
    return content_ids, name_ids


def _exempt_hex_values() -> set[str]:
    """Every 32-hex literal this repository has a recorded reason to allow.

    Which literals, not where they may appear: `_hex_key_offenders` decides
    that, and only lets them be spent under `EXEMPT_SCOPE`.
    """
    content_ids, _ = _collect_event_ids(_tracked_files(), PROJECT_ROOT)
    return content_ids | set(RECORDED_DIGESTS)


#: `apiKey=` FOLLOWED BY A VALUE is a leak. The bare token is not: it appears
#: legitimately in the redaction regex that strips credentials and in tests
#: asserting the token is absent. The spelling is a family — `apiKey`,
#: `apikey`, `api_key`, `api-key` — because a matcher that knows one casing
#: goes quiet on a rename. The value class admits `-` and `_` because the
#: example key this module uses everywhere (`sk-live-...`) carries them.
API_KEY_PARAM = re.compile(
    r"api[_-]?key=[A-Za-z0-9][A-Za-z0-9_-]{7,}", re.IGNORECASE
)

#: Punctuation that may sit between a credential name and the operator that
#: gives it a value: a closing quote, a subscript, a code span, an emphasis
#: marker, an HTML tag. `os.environ["NAME"] = "..."`, `**NAME**: ...`,
#: `<code>NAME</code>: ...`. A shape rather than an enumeration, because an
#: enumeration is a spelling; bounded at eight so it cannot run away across a
#: line, and newline excluded so `NAME` on one line and `=` on the next is not
#: an assignment — that is what keeps `.env.example` green.
_CLOSERS = r"(?:</?[A-Za-z][A-Za-z0-9]*[^<>\n]{0,64}>|[^0-9A-Za-z\n=:,|]){0,8}"

#: A horizontal blank, agreeing with `\S` about what a blank is.
#:
#: The spacing was `[ \t]*` — ASCII — and the value was captured with
#: `(?=(\S+))`, which is Unicode-aware. A U+00A0 after the operator fell in
#: the gap between the two: the spacing class would not consume it and `\S`
#: would not start on it, so `export NAME=<U+00A0>sk-live-…` opened no match.
#: `[^\S\r\n]*` is every character `\S` refuses, minus the line breaks.
_BLANK = r"[^\S\r\n]*"

#: How much of the line after the operator is handed to the value tests. A
#: zero-width lookahead so the match ends at the operator (a consumed value
#: would swallow a nested occurrence), and bounded so one line carrying the
#: name two thousand times cannot go quadratic.
_REST_OF_LINE = r"(?=(.{0,512}))"

_NAMES = "|".join(re.escape(name) for name in CREDENTIAL_NAMES)

#: `NAME=value` where NAME is a credential variable, in every spelling that
#: a machine reads back: the operator family `[:?+]?=` (Make's `:=`/`?=`/`+=`,
#: Go's short declaration, shell's `${NAME:=literal}`), closers between the
#: name and the operator, a Unicode-aware blank either side, and the whole
#: rest of the line rather than its first token — `NAME = "" "<key>"` and the
#: third cell of a table row were both dismissed on an empty first token.
#: `re.IGNORECASE` because a lowercased spelling of the name is the same name.
ASSIGNMENT = re.compile(
    r"(?<![A-Za-z0-9])("
    + _NAMES
    + r")"
    + _CLOSERS
    + _BLANK
    + r"[:?+]?="
    + _BLANK
    + _REST_OF_LINE,
    re.IGNORECASE,
)

#: The same idea for the separators `=` cannot cover: YAML's `NAME: value`,
#: the comma of `setdefault("NAME", value)` / `{"NAME": value}`, and the pipe
#: of a Markdown table row — CLAUDE.md documents its credential in a table.
#: Each of these also separates a name from ordinary prose, so the value must
#: independently look like a value (`_looks_like_a_credential_value`).
SEPARATED = re.compile(
    r"(?<![A-Za-z0-9])("
    + _NAMES
    + r")"
    + _CLOSERS
    + _BLANK
    + r"[:,|]"
    + _BLANK
    + _REST_OF_LINE,
    re.IGNORECASE,
)

#: Does this token look like a credential *value* rather than a word of prose?
#: One unbroken run of name-safe characters, long, containing a digit, and not
#: an identifier in shouting case. Two gaps this leaves are stated in
#: `test_the_value_test_gaps_are_the_ones_documented`.
CREDENTIAL_VALUE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{11,}")

#: An identifier in shouting case is a *name*, never a value.
SHOUTING_CASE = re.compile(r"[A-Z0-9_]+")

#: Unicode categories that occupy no space and belong to no credential:
#: U+200B, U+00AD, U+FEFF and the rest of the format and control marks.
#: Unicode does not call them whitespace, so `\S` starts on them and they
#: ride into the token; `_unwrap` deletes them by category, not by list.
INVISIBLE_CATEGORIES = frozenset({"Cf", "Cc"})


def _tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        check=True,
    )
    names = [item for item in result.stdout.decode("utf-8").split("\0") if item]
    return [PROJECT_ROOT / name for name in names]


#: This file necessarily contains every pattern it hunts for, so it must not
#: scan itself. Its NAME is still scanned like every other tracked path.
SELF = Path(__file__).resolve()


#: Suffixes whose *bodies* there is no point decoding. A statement about
#: bodies only: a file with one of these suffixes still has a name, and a name
#: needs no decoding — see `_hex_offenders_for_corpus`.
BINARY_SUFFIXES = frozenset(
    {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip"}
)


def _link_target(path: Path) -> str:
    """What a tracked symlink carries, which is neither name nor body.

    `git` stores a symlink as a blob whose contents are the target string, so
    `ln -s sk-live-… docs/provider_key` commits the credential in plaintext.
    Returns `""` for anything that is not a symlink, so callers can
    concatenate it unconditionally.
    """
    try:
        if not path.is_symlink():
            return ""
        return os.readlink(path)
    except OSError:
        return ""


def _is_this_file(path: Path) -> bool:
    """`path` is this module, resolving symlinks — and never raises.

    `Path.resolve()` raises `RuntimeError` on a symlink loop; a path that
    cannot be resolved is *not* this file, so it stays in the corpus.
    """
    try:
        return path.resolve() == SELF
    except (OSError, RuntimeError):
        return False


def _body_scannable(paths: Iterable[Path]) -> list[Path]:
    """The subset of `paths` whose contents are worth reading as text.

    A symlink is kept even when it dangles: its body reads as empty, but
    keeping it is what carries the path into `_assignment_offenders`, which
    scans the link target. Dropping it on `is_file()` hid
    `ln -s "NAME=<key>" note`.
    """
    keep: list[Path] = []
    for path in paths:
        if not path.is_file() and not path.is_symlink():
            continue
        if _is_this_file(path):
            continue
        if path.suffix in BINARY_SUFFIXES:
            continue
        keep.append(path)
    return keep


def _text_files() -> list[Path]:
    return _body_scannable(_tracked_files())


def _without_invisibles(text: str) -> str:
    """The text minus the format and control characters — line breaks and
    tabs kept, because newline is `Cc` too and a reading with the lines
    collapsed would join two innocent runs into one finding."""
    return "".join(
        character for character in text
        if character in "\n\r\t"
        or unicodedata.category(character) not in INVISIBLE_CATEGORIES
    )


def _read(path: Path) -> str:
    """The file as text, plus readings with the NULs and the invisible
    characters removed when there are any.

    A UTF-16 file decodes under `errors="ignore"` into `K\\x00E\\x00Y…`, and
    every matcher here wants an unbroken run. So does a key with a U+200B
    dropped into its middle — found by attacking this module's own hex scan
    after the assignment scan had learned to strip invisibles and the hex scan
    had not. Each extra reading is appended rather than substituted, so the
    ordinary reading is still scanned exactly as before.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
    readings = [text]
    if "\x00" in text:
        readings.append(text.replace("\x00", ""))
    stripped = _without_invisibles(readings[-1])
    if stripped != readings[-1]:
        readings.append(stripped)
    return "\n".join(readings)


def _hex_key_offenders(
    paths: Iterable[Path],
    allowed: set[str],
    root: Path,
    *,
    names: bool = True,
    bodies: bool = True,
) -> list[str]:
    """Every 32-hex run in `paths` — name, symlink target or body — that is
    not accounted for.

    Taking the corpus as an argument is what lets the regression tests run
    this exact code over a synthetic file. Only six characters of a finding
    are reported: enough to locate it, not enough to publish it. `allowed` is
    spendable only under `EXEMPT_SCOPE`, for a name exactly as for a body.
    """
    offenders: list[str] = []
    for path in paths:
        relative = path.relative_to(root).as_posix()
        permitted = allowed if relative.startswith(EXEMPT_SCOPE) else set()
        found: list[str] = []
        if names:
            found += [match.group(0) for match in HEX_KEY.finditer(relative)]
            found += [
                match.group(0)
                for match in HEX_KEY.finditer(_link_target(path))
            ]
        if bodies:
            found += [match.group(0) for match in HEX_KEY.finditer(_read(path))]
        for value in found:
            if value in permitted:
                continue
            finding = f"{relative}: {value[:6]}..."
            # Once per file and value: the extra readings `_read` appends
            # would otherwise report one key twice.
            if finding not in offenders:
                offenders.append(finding)
    return offenders


def _unwrap(raw: str) -> str:
    """Strip the punctuation that surrounds a value in source and prose.

    Invisible characters first (by category), then a string-literal prefix
    (`f"{SECRET}"` is quoting, not value), then quotes, closers and the
    leading `-` of a shell default so `${NAME:-<key>}` reads as what it is.
    """
    visible = "".join(
        character
        for character in raw
        if unicodedata.category(character) not in INVISIBLE_CATEGORIES
    )
    without_prefix = re.sub(r"^[fFrRbBuU]{1,2}(?=[\"'])", "", visible)
    return without_prefix.strip("'\"`").strip(",;)}]").strip("'\"`").lstrip("-")


def _is_a_reference(value: str) -> bool:
    """`$VAR`, `<placeholder>`, `${{ secrets.X }}`, an f-string `{SECRET}`.

    `$` is unconditional. The bracket forms are not: `NAME: <sk-live-…>` is
    the leak wearing the placeholder's clothes, so the brackets are stripped
    and what is inside has to fail the value test.
    """
    if value[0] == "$":
        return True
    if value[0] in "<{":
        return not _looks_like_a_credential_value(_unbracket(value))
    return False


def _unbracket(value: str) -> str:
    return value.strip("<>{} ")


def _looks_like_a_credential_value(value: str) -> bool:
    if not CREDENTIAL_VALUE.fullmatch(value):
        return False
    if SHOUTING_CASE.fullmatch(value):
        return False
    return any(character.isdigit() for character in value)


def _hex_offenders_for_corpus(
    tracked: Iterable[Path], allowed: set[str], root: Path
) -> list[str]:
    """The whole hex scan for a corpus: names (and link targets) over all of
    it, bodies over the part that has one worth reading.

    This split is the fix for a scan that a `.png` suffix could walk past
    entirely.
    """
    paths = list(tracked)
    offenders = _hex_key_offenders(paths, allowed, root, bodies=False)
    offenders += _hex_key_offenders(
        _body_scannable(paths), allowed, root, names=False
    )
    return offenders


def _assignment_offenders(paths: Iterable[Path], root: Path) -> list[str]:
    """Every `CREDENTIAL_NAME <given> <real value>` in `paths`, by file and name.

    Two families, because they need different evidence. `=` is an assignment
    wherever it appears, so its first token needs no value test. `:`, `,` and
    `|` also occur in prose, so a match there is a finding only if the value
    independently looks like a credential. Every token on the rest of the
    line is evaluated, and an empty token advances rather than ending the
    line. The symlink target is appended to the text.
    """
    offenders: list[str] = []
    for path in paths:
        relative = path.relative_to(root).as_posix()
        text = _read(path)
        target = _link_target(path)
        if target:
            text = f"{text}\n{target}"
        for pattern, value_must_look_real in ((ASSIGNMENT, False), (SEPARATED, True)):
            for match in pattern.finditer(text):
                tokens = [
                    unwrapped
                    for unwrapped in (
                        _unwrap(token) for token in match.group(2).split()
                    )
                    if unwrapped
                ]
                for index, value in enumerate(tokens):
                    must_look_real = value_must_look_real or index > 0
                    if value in PLACEHOLDERS:
                        continue
                    if _is_a_reference(value):
                        continue
                    if must_look_real and not _looks_like_a_credential_value(
                        _unbracket(value)
                    ):
                        continue
                    finding = f"{relative}: {match.group(1)}"
                    if finding not in offenders:
                        offenders.append(finding)
                    break
    return offenders


# --------------------------------------------------------------------------
# The gates over the real repository.
# --------------------------------------------------------------------------


def test_env_file_is_never_tracked() -> None:
    tracked = {path.name for path in _tracked_files()}

    assert ENV_FILENAME not in tracked


def test_env_file_is_gitignored() -> None:
    result = subprocess.run(
        ["git", "check-ignore", ENV_FILENAME],
        cwd=PROJECT_ROOT,
        capture_output=True,
    )

    assert result.returncode == 0, ".env must stay gitignored"


def test_no_tracked_file_assigns_a_real_credential() -> None:
    """Every tracked text file, every name in `CREDENTIAL_NAMES`, every
    suffix. Markdown is not a safer place to write a key than Python is."""
    files = _text_files()
    assert len(files) > 100, "the tracked-file corpus is implausibly small"
    offenders = _assignment_offenders(files, PROJECT_ROOT)

    assert offenders == [], f"credential assignment in tracked files: {offenders}"


def test_no_credential_name_in_the_repository_is_unknown_to_this_guard() -> None:
    """A credential name this module has not been taught is a name it cannot
    catch being assigned. Go and find every credential-shaped name in the
    tree and demand the list covers it."""
    found: set[str] = set()
    for path in _text_files():
        found.update(CREDENTIAL_NAME_SHAPE.findall(_read(path)))

    assert found, "no credential name found in any tracked file — scan is broken"
    assert found <= set(CREDENTIAL_NAMES), (
        "credential names this guard cannot recognise being assigned: "
        f"{sorted(found - set(CREDENTIAL_NAMES))}"
    )


def test_no_tracked_file_contains_an_odds_api_key_shape() -> None:
    """Every tracked file is scanned by **name** — binaries included — every
    tracked symlink by **target**, and every tracked text file by **body**.
    A file under `EXEMPT_SCOPE` may spend a recorded event id; a file
    anywhere else may not."""
    tracked = _tracked_files()
    assert len(tracked) > 100
    offenders = _hex_offenders_for_corpus(tracked, _exempt_hex_values(), PROJECT_ROOT)

    assert offenders == [], f"possible credential in tracked files: {offenders}"


def test_generated_reports_never_include_the_api_key_parameter() -> None:
    """`apiKey=<value>` is how the credential travels; never write it."""
    offenders: list[str] = []
    for path in _text_files():
        for match in API_KEY_PARAM.finditer(_read(path)):
            offenders.append(
                f"{path.relative_to(PROJECT_ROOT)}: {match.group(0)[:10]}..."
            )

    assert offenders == [], f"apiKey= with a value in tracked files: {offenders}"


def test_data_outputs_reports_are_not_tracked_with_secrets() -> None:
    """Report artifacts under data/outputs must be clean if tracked at all.

    Calls `_hex_key_offenders` so there is one matcher and one spend rule to
    keep correct rather than two, and scans names as well as bodies.
    """
    known = _exempt_hex_values()
    named = [
        path
        for path in _tracked_files()
        if path.relative_to(PROJECT_ROOT).as_posix().startswith("data/outputs/")
    ]
    assert named, "no tracked report under data/outputs/; the corpus is wrong"
    reports = _body_scannable(named)
    offenders = _hex_key_offenders(named, known, PROJECT_ROOT, bodies=False)
    offenders += _hex_key_offenders(reports, known, PROJECT_ROOT, names=False)
    offenders += [
        f"{path.relative_to(PROJECT_ROOT).as_posix()}: apiKey="
        for path in reports
        if API_KEY_PARAM.search(_read(path))
    ]

    assert offenders == [], f"tracked report contains a credential: {offenders}"


def test_the_guard_excludes_itself_from_its_own_scan() -> None:
    scanned = {path.resolve() for path in _text_files()}

    assert SELF not in scanned


def test_the_guard_still_scans_other_test_files() -> None:
    """Self-exclusion must be exactly one file, not all of tests/."""
    scanned = {path.name for path in _text_files()}

    assert "test_league_registry_is_the_only_place.py" in scanned
    assert "test_contract_strings.py" in scanned
    assert "test_workflows.py" in scanned


@pytest.mark.parametrize("name", CREDENTIAL_NAMES)
def test_credential_names_are_referenced_but_never_valued(name: str) -> None:
    assert isinstance(name, str) and name and CREDENTIAL_NAME_SHAPE.fullmatch(name)


def test_the_production_credential_name_is_the_one_the_workflow_uses() -> None:
    """The secret name is a contract with GitHub Actions; it must not drift."""
    assert "FOOTBALL_ODDS_API_KEY" in PROVIDER_ENV_ALLOWLIST
    assert GITHUB_SECRET_NAME in CREDENTIAL_NAMES
    # The base URL is in the allowlist and is not a credential.
    assert "FOOTBALL_ODDS_API_BASE_URL" in PROVIDER_ENV_ALLOWLIST
    assert "FOOTBALL_ODDS_API_BASE_URL" not in CREDENTIAL_NAMES


def test_every_cached_response_filename_is_corroborated() -> None:
    """A cached response is named after the event it holds, so its stem and
    its body must agree. This lab tracks the retention-probe cache under
    `data/raw/`, so — unlike the sibling labs — the repository half of this
    assertion is not vacuous, and that is asserted too."""
    content_ids, name_ids = _collect_event_ids(_tracked_files(), PROJECT_ROOT)

    assert name_ids, "no cached response is tracked; the corpus is wrong"
    assert content_ids >= name_ids, (
        "cached-response filenames no body records: "
        f"{sorted(stem[:6] + '...' for stem in name_ids - content_ids)}"
    )


def test_the_event_id_exemption_is_by_value_and_not_by_directory(
    tmp_path: Path,
) -> None:
    """A hex run that is not a recorded event id is still a finding, even in
    the directory where provider data lives — on the real repository AND on a
    corpus built here."""
    known = _exempt_hex_values()
    invented = "deadbeef" * 4
    assert known, "no provider event ids were found; the exemption is untested"
    assert HEX_KEY.fullmatch(invented)
    assert invented not in known

    raw = tmp_path / "data" / "raw"
    raw.mkdir(parents=True)
    recorded = "a1b2c3d4" * 4
    cached = raw / f"{recorded}_odds.json"
    cached.write_text(json.dumps({"id": recorded, "bookmakers": []}), encoding="utf-8")
    neighbour = raw / "settings.json"
    neighbour.write_text(json.dumps({"note": invented}), encoding="utf-8")

    content_ids, name_ids = _collect_event_ids([cached, neighbour], tmp_path)

    assert content_ids == {recorded}
    assert name_ids == {recorded}
    assert _hex_key_offenders([cached, neighbour], content_ids, tmp_path) == [
        f"data/raw/settings.json: {invented[:6]}..."
    ]


# --------------------------------------------------------------------------
# Reproductions: each of these failed against the module as it was.
# --------------------------------------------------------------------------


def test_a_file_is_never_exempt_from_the_hex_scan_for_what_it_is_called(
    tmp_path: Path,
) -> None:
    """(a) Receipts and checksum files are scanned like everything else.

    The guard used to `continue` past any file whose name contained "receipt"
    or "checksum". Identical bytes therefore passed as `week3_receipt.md` and
    failed as `week3.md`, and the blind spot sat on the files most likely to
    carry provenance.
    """
    key = "0123456789abcdef0123456789abcdef"
    receipts = tmp_path / "docs" / "receipts"
    receipts.mkdir(parents=True)
    for name in ("week3_acceptance_receipt.md", "manifest_checksum.txt", "receipt.json"):
        (receipts / name).write_text(
            f"human acceptance recorded against {key}\n", encoding="utf-8"
        )

    found = _hex_key_offenders(sorted(receipts.iterdir()), set(), tmp_path)

    assert found == [
        f"docs/receipts/manifest_checksum.txt: {key[:6]}...",
        f"docs/receipts/receipt.json: {key[:6]}...",
        f"docs/receipts/week3_acceptance_receipt.md: {key[:6]}...",
    ]
    # ...and a real digest never needed the skip: the lookarounds refuse to
    # fire inside a 64-character run.
    digest = tmp_path / "SHA256SUMS"
    digest.write_text("a" * 64 + "  data/outputs/report.md\n", encoding="utf-8")

    assert _hex_key_offenders([digest], set(), tmp_path) == []


def test_a_hex_key_beside_an_underscore_or_in_uppercase_is_a_finding(
    tmp_path: Path,
) -> None:
    """(b) `\\b[0-9a-f]{32}\\b` could not see either.

    `_` is a word character, so the boundary never opened beside it — and the
    cache-naming form `<key>_odds.json` is exactly that shape. An uppercased
    copy of a key is the same key and was invisible to a lowercase class.
    Several spellings on purpose: a fix that catches only the first is a
    narrower guard, not a repaired one.
    """
    key = "0123456789abcdef0123456789abcdef"
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    spellings = {
        "cache.py": f'CACHE = f"{key}_odds.json"\n',
        "named.py": f"KEY_{key} = 1\n",
        "fenced.py": f"_{key}_\n",
        "url.md": f"https://api.example/v4/{key}/odds\n",
        "ident.py": f"ODDS{key}ZONE = 2\n",
        "upper.py": f'KEY = "{key.upper()}"\n',
        "mixed.py": f'KEY = "{key[:16].upper()}{key[16:]}"\n',
    }
    for name, body in spellings.items():
        (scripts / name).write_text(body, encoding="utf-8")

    offenders = _hex_key_offenders(
        [scripts / name for name in sorted(spellings)], set(), tmp_path
    )

    assert offenders == [
        f"scripts/{name}: {key[:6]}..." for name in sorted(spellings)
    ]
    for fence in ("_", "-", ".", "/", "x", ""):
        assert HEX_KEY.search(f"{fence}{key}{fence}"), fence
    assert HEX_KEY.search(key.upper())
    # ...and a longer hex run is still not a 32-hex key.
    assert not HEX_KEY.search("sha256 = " + "a" * 64)
    assert not HEX_KEY.search("docs/" + "A" * 40 + ".txt")


def test_a_hex_run_in_a_filename_is_a_finding_wherever_the_name_sits(
    tmp_path: Path,
) -> None:
    """(c) A key in a filename was scanned by nothing, and a key in the name
    of a `.png` was scanned by nothing twice over."""
    key = "0123456789abcdef0123456789abcdef"
    docs = tmp_path / "docs"
    docs.mkdir()
    plain = docs / f"{key}.md"
    plain.write_text("Notes on the fetch. Nothing sensitive in here.\n", encoding="utf-8")
    cache_shaped = docs / f"{key}_odds.json"
    cache_shaped.write_text(json.dumps({"ok": True}), encoding="utf-8")
    binaries = [f"{key}.png", f"{key}.pdf", f"{key}_chart.zip", f"cover-{key.upper()}.jpg"]
    for name in binaries:
        (docs / name).write_bytes(b"\x89PNG\r\n\x1a\n\xff\xfe\x00\x01")
    # A text file wearing a binary suffix: its body is not decoded (and the
    # known-gaps ledger says so) but its NAME is.
    disguised = docs / f"{key}.pdf.txt"
    disguised.write_text("plain\n", encoding="utf-8")

    corpus = [plain, cache_shaped, disguised] + [docs / name for name in binaries]

    assert _body_scannable(corpus) == [plain, cache_shaped, disguised]
    assert sorted(_hex_offenders_for_corpus(corpus, set(), tmp_path)) == sorted(
        [
            f"docs/{key}.md: {key[:6]}...",
            f"docs/{key}_odds.json: {key[:6]}...",
            f"docs/{key}.pdf.txt: {key[:6]}...",
        ]
        + [f"docs/{name}: {key[:6]}..." for name in binaries]
    )

    # ...and the spend rule is the same for a name as for a body.
    recorded = "a1b2c3d4" * 4
    outputs = tmp_path / "data" / "outputs"
    outputs.mkdir(parents=True)
    chart = outputs / f"{recorded}.png"
    chart.write_bytes(b"\x89PNG\r\n\x1a\n")
    elsewhere = docs / f"{recorded}.pdf"
    elsewhere.write_bytes(b"%PDF-1.4\n")

    assert _hex_offenders_for_corpus([chart, elsewhere], {recorded}, tmp_path) == [
        f"docs/{recorded}.pdf: {recorded[:6]}..."
    ]


def test_a_tracked_symlink_carries_its_target_into_the_scans(
    tmp_path: Path,
) -> None:
    """(c) `path.is_file()` follows symlinks and drops a dangling one."""
    key = "0123456789abcdef0123456789abcdef"
    name = GITHUB_SECRET_NAME
    value = "sk-live-4f19c0d27ba6e83d"
    docs = tmp_path / "docs"
    docs.mkdir()
    hex_link = docs / "provider_key"
    hex_link.symlink_to(key)
    assignment_link = docs / "note"
    assignment_link.symlink_to(f"{name}={value}")

    assert not hex_link.is_file()
    assert _hex_offenders_for_corpus([hex_link], set(), tmp_path) == [
        f"docs/provider_key: {key[:6]}..."
    ]
    assert _body_scannable([assignment_link]) == [assignment_link]
    assert _read(assignment_link) == ""
    assert _assignment_offenders([assignment_link], tmp_path) == [f"docs/note: {name}"]

    # A symlink loop is a finding-free file, not a crash.
    loop = docs / "loop"
    loop.symlink_to("loop")

    assert _body_scannable([loop]) == [loop]
    assert _hex_offenders_for_corpus([loop], set(), tmp_path) == []
    assert _assignment_offenders([loop], tmp_path) == []


def test_a_decoy_filename_cannot_nominate_an_exemption(tmp_path: Path) -> None:
    """(d) The audit's reproduction: `<key>_x.md` at the repository root.

    The stem harvest ran over EVERY tracked file before any directory
    restriction, so the decoy nominated the key into the exemption set and a
    hardcoded key in `scripts/` went green. Measured on this corpus before the
    fix: zero offenders.
    """
    key = "0123456789abcdef0123456789abcdef"
    decoy = tmp_path / f"{key}_x.md"
    decoy.write_text("nothing here\n", encoding="utf-8")
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    hardcoded = scripts / "fetch.py"
    hardcoded.write_text(f'API_KEY = "{key}"\n', encoding="utf-8")

    content_ids, name_ids = _collect_event_ids([decoy, hardcoded], tmp_path)

    assert (content_ids, name_ids) == (set(), set())
    assert _hex_offenders_for_corpus([decoy, hardcoded], content_ids, tmp_path) == [
        f"{key}_x.md: {key[:6]}...",
        f"scripts/fetch.py: {key[:6]}...",
    ]


def test_a_report_this_repository_writes_cannot_nominate_an_exemption(
    tmp_path: Path,
) -> None:
    """(d) A hand-committed `data/outputs/x.json` whose body was `{"id": key}`
    created the very exemption it then spent, and turned the key green for its
    siblings under `data/outputs/` too. A report may **spend**; only the
    provider cache — and the `event_id` column of the two named bet tables —
    may **create**."""
    key = "0123456789abcdef0123456789abcdef"
    outputs = tmp_path / "data" / "outputs"
    outputs.mkdir(parents=True)
    self_nominating = outputs / "nfl_retention_probe.json"
    self_nominating.write_text(json.dumps({"id": key}), encoding="utf-8")
    sibling = outputs / "notes.md"
    sibling.write_text(f"the value is {key}\n", encoding="utf-8")
    # A CSV under data/outputs that is NOT one of the named tables.
    table = outputs / "bought_prices.csv"
    table.write_text(f"event_id,price\n{key},-110\n", encoding="utf-8")

    corpus = [self_nominating, sibling, table]
    content_ids, name_ids = _collect_event_ids(corpus, tmp_path)

    assert (content_ids, name_ids) == (set(), set())
    assert _hex_key_offenders(corpus, content_ids, tmp_path) == [
        f"data/outputs/nfl_retention_probe.json: {key[:6]}...",
        f"data/outputs/notes.md: {key[:6]}...",
        f"data/outputs/bought_prices.csv: {key[:6]}...",
    ]

    # ...and an exemption genuinely earned in `data/raw/` is spendable in a
    # report and NOT in `scripts/`.
    raw = tmp_path / "data" / "raw"
    raw.mkdir(parents=True)
    cached = raw / f"{key}_odds.json"
    cached.write_text(json.dumps({"events": [{"id": key}]}), encoding="utf-8")
    hardcoded = tmp_path / "scripts" / "fetch_odds.py"
    hardcoded.parent.mkdir()
    hardcoded.write_text(f'API_KEY = "{key}"\n', encoding="utf-8")

    content_ids, _ = _collect_event_ids([cached, sibling, hardcoded], tmp_path)

    assert content_ids == {key}
    assert _hex_key_offenders([cached, sibling, hardcoded], content_ids, tmp_path) == [
        f"scripts/fetch_odds.py: {key[:6]}..."
    ]


def test_the_canonical_python_assignment_and_yaml_are_findings(tmp_path: Path) -> None:
    """(e) `os.environ["NAME"] = "<key>"` and `NAME: <key>` were caught by
    nothing, and a `.md` was exempt from the assignment scan entirely."""
    name = GITHUB_SECRET_NAME
    value = "sk-live-4f19c0d27ba6e83d"
    leaks = {
        "src/fetch.py": f'import os\nos.environ["{name}"] = "{value}"\n',
        "docs/runbook.md": f'Then run `os.environ["{name}"] = "{value}"`.\n',
        "docs/setup.md": f"Export the credential:\n\n    export {name}={value}\n",
        "ci/gameday.yml": f"env:\n  {name}: {value}\n",
        "docs/notes.txt": f"{name}: {value}\n",
        "docs/table.md": f"| `{name}` | live | {value} |\n",
    }
    written: list[Path] = []
    for relative, body in leaks.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        written.append(path)

    assert _assignment_offenders(written, tmp_path) == [
        f"{relative}: {name}" for relative in leaks
    ]

    # ...and prose that shows the shape of the command still passes.
    fine = tmp_path / "docs" / "shape.md"
    fine.write_text(
        f"Run `export {name}=your-api-key`, or in CI set\n"
        f"`{name}=" + "${{ secrets." + name + " }}`, or locally\n"
        f"`{name}=$ODDS_KEY` / `{name}=<paste yours>`.\n"
        f"| `{name}` | The name of the GitHub secret holding the credential |\n",
        encoding="utf-8",
    )

    assert _assignment_offenders([fine], tmp_path) == []


def test_the_assignment_scan_survives_a_rewording(tmp_path: Path) -> None:
    """The attacks tried against the fix, and the prose it must not eat."""
    name = GITHUB_SECRET_NAME
    value = "sk-live-4f19c0d27ba6e83d"
    hexish = "aB3xQ9zLmN2pR7tV"
    rewordings = {
        "a.py": f'os.environ["{name}"] = "{value}"',
        "b.py": f"os.environ['{name}']='{value}'",
        "c.py": f'os.environ.setdefault("{name}", "{value}")',
        "d.py": f'CONFIG = {{"{name}": "{value}"}}',
        "e.py": f'settings["env"]["{name}"] = "{hexish}"',
        "f.yml": f"  {name}: {value}",
        "g.yml": f'  {name}: "{value}"',
        "h.md": f"- `{name}` = {value}",
        "i.sh": f': "${{{name}:-{value}}}"',
        "j.json": f'{{"{name}": "{hexish}"}}',
        "k.py": f'os.environ[ "{name}" ] = "{value}"',
        "l.toml": f'{name} = "{value}"',
        "m.md": f"**{name}**: {value}",
        "n.md": f"<code>{name}</code> = {value}",
        "o.mk": f"{name} := {value}",
        "p.mk": f"{name} ?= {value}",
        "q.mk": f"{name} += {value}",
        "r.py": f'os.environ["{name}"] = "" "{value}"',
        "s.py": f'os.environ["{name.lower()}"] = "{value}"',
        "t.yml": f"{name}: <{value}>",
    }
    for filename, body in rewordings.items():
        (tmp_path / filename).write_text(body + "\n", encoding="utf-8")

    caught = _assignment_offenders(
        [tmp_path / filename for filename in sorted(rewordings)], tmp_path
    )

    assert caught == [
        f"{filename}: {name.lower() if filename == 's.py' else name}"
        for filename in sorted(rewordings)
    ]

    prose = {
        "table.md": f"| `{name}` | The name of the GitHub secret |",
        "gloss.md": f"`{name}`: the name of the GitHub secret",
        "list.py": f'CREDENTIAL_NAMES = frozenset({{"{name}", "NHL_ODDS_API_KEY"}})',
        "guard.sh": f'if [ -z "${{{name}}}" ]; then echo missing; exit 1; fi',
        "ci.yml": f"  {name}: ${{{{ secrets.{name} }}}}",
        "empty.yml": f'  {name}: ""',
        "state.md": f"{name}: not-configured",
        "where.md": f"{name}: see docs/runbook-2024.md",
        "ref.md": f"{name}: $ODDS_KEY",
        "both.md": f"{name}, NHL_ODDS_API_KEY",
        "shape.md": f"Run `export {name}=your-api-key` first.",
        "example.env": f"{name}=",
        "sibling.yml": f"{name}_FILE: {value}",
        "fstring.py": f'os.environ["{name}"] = f"{{SECRET}}"',
        "next_line.env": f"{name}=\n{value}",
    }
    for filename, body in prose.items():
        (tmp_path / filename).write_text(body + "\n", encoding="utf-8")

    assert _assignment_offenders(
        [tmp_path / filename for filename in sorted(prose)], tmp_path
    ) == []


def test_a_unicode_blank_does_not_open_a_gap_between_the_classes(
    tmp_path: Path,
) -> None:
    """(e) `[ \\t]*` is ASCII and `\\S` is Unicode-aware; a U+00A0 fell between
    them and `export NAME=<U+00A0><key>` opened no match. U+200B is here for
    the opposite reason — it rides into the token and `_unwrap` deletes it."""
    name = GITHUB_SECRET_NAME
    value = "sk-live-4f19c0d27ba6e83d"
    blanks = {"nbsp": " ", "zero_width": "​", "ideographic": "　"}
    written: list[Path] = []
    for label, blank in blanks.items():
        for family, line in (
            ("after_equals", f"export {name}={blank}{value}"),
            ("around_equals", f"export {name}{blank}={blank}{value}"),
            ("after_colon", f"{name}:{blank}{value}"),
        ):
            path = tmp_path / f"{label}_{family}.md"
            path.write_text(line + "\n", encoding="utf-8")
            written.append(path)

    assert _assignment_offenders(written, tmp_path) == [
        f"{path.name}: {name}" for path in written
    ]
    assert re.fullmatch(_BLANK, " \t 　")


def test_the_value_test_gaps_are_the_ones_documented() -> None:
    """The `:`/`,`/`|` value test is not airtight; these are its exact edges,
    and the `=` family runs no value test on its FIRST token."""
    assert not _looks_like_a_credential_value("purelettersecret")
    assert not _looks_like_a_credential_value("ab12.cd34.ef56")
    assert not _looks_like_a_credential_value("sk/live/4f19c0d2")
    assert ASSIGNMENT.search(f"{GITHUB_SECRET_NAME}=purelettersecret")
    assert ASSIGNMENT.search(f"{GITHUB_SECRET_NAME}=ab12.cd34.ef56")
    assert not _looks_like_a_credential_value("the")
    assert not _looks_like_a_credential_value("FOOTBALL_ODDS_API_KEY")
    assert not _looks_like_a_credential_value("not-configured")
    assert _looks_like_a_credential_value("sk-live-4f19c0d27ba6e83d")
    assert _looks_like_a_credential_value("0123456789abcdef0123456789abcdef")
    assert _looks_like_a_credential_value("aB3xQ9zLmN2pR7tV")


def test_the_credential_name_shape_knows_more_than_one_spelling() -> None:
    for spelling in ("FOOTBALL_ODDS_APIKEY", "FOOTBALL_ODDS_API_TOKEN", "X_API_KEY"):
        assert CREDENTIAL_NAME_SHAPE.findall(f"export {spelling}=x") == [spelling]
    assert CREDENTIAL_NAME_SHAPE.findall("PROJECT_ROOT = Path(__file__)") == []
    assert CREDENTIAL_NAME_SHAPE.findall("API_KEY_PARAM = re.compile(...)") == []


def test_a_credential_in_a_utf16_body_is_a_finding(tmp_path: Path) -> None:
    key = "0123456789abcdef0123456789abcdef"
    name = GITHUB_SECRET_NAME
    little = tmp_path / "notes.txt"
    little.write_bytes(f'KEY = "{key}"\n'.encode("utf-16-le"))
    big = tmp_path / "config.txt"
    big.write_bytes(f'{name} = "sk-live-4f19c0d27ba6e83d"\n'.encode("utf-16-be"))

    assert "\x00" in little.read_text(encoding="utf-8", errors="ignore")
    assert _hex_key_offenders([little], set(), tmp_path) == [f"notes.txt: {key[:6]}..."]
    assert _assignment_offenders([big], tmp_path) == [f"config.txt: {name}"]


def test_a_key_broken_by_an_invisible_character_is_a_finding(tmp_path: Path) -> None:
    """Found by attacking the fix: `_unwrap` stripped U+200B from an
    assignment's value while the hex scan read the raw body, so a key with a
    zero-width space in its middle was thirty-two hex characters to a human
    and two runs of sixteen to `HEX_KEY`. Every invisible category, in the
    middle and at both ends, in a body and in a UTF-16 body."""
    key = "0123456789abcdef0123456789abcdef"
    for index, invisible in enumerate(("\u200b", "\u00ad", "\ufeff", "\u200d", "\x07")):
        broken = tmp_path / f"broken_{index}.py"
        broken.write_text(f'KEY = "{key[:16]}{invisible}{key[16:]}"\n', encoding="utf-8")
        assert not HEX_KEY.search(broken.read_text(encoding="utf-8"))
        assert _hex_key_offenders([broken], set(), tmp_path) == [f"broken_{index}.py: {key[:6]}..."]
    # ...and the same key in a filename is not hidden by one either.
    named = tmp_path / f"{key[:16]}\u200b{key[16:]}.md"
    named.write_text("notes\n", encoding="utf-8")
    assert _hex_offenders_for_corpus([named], set(), tmp_path) == []  # the disclosed edge, below


def test_the_api_key_parameter_matcher_knows_the_spelling_family() -> None:
    for spelling in ("apiKey=", "apikey=", "API_KEY=", "api-key=", "ApiKey="):
        for value in ("aZ90bYx8cW7v", "sk-live-4f19c0d27ba6e83d", "0123456789abcdef"):
            assert API_KEY_PARAM.search(f"https://x/v4/odds?{spelling}{value}&r=us"), (
                spelling, value,
            )
    assert API_KEY_PARAM.search("apiKey=abcdef0123456789abcdef0123456789")
    # ...and the defences that mention the token stay clean.
    assert not API_KEY_PARAM.search('re.compile(r"(apiKey=)[^&s]+")')
    assert not API_KEY_PARAM.search('assert "apiKey=" not in text')
    assert not API_KEY_PARAM.search("apiKey=[redacted]")


def test_the_key_shape_check_still_fires_on_something_that_is_not_an_event_id() -> None:
    known = _exempt_hex_values()
    leaked = "0123456789abcdef0123456789abcdef"

    assert leaked not in known
    assert HEX_KEY.search(f"{GITHUB_SECRET_NAME}={leaked}")


def test_the_gaps_this_guard_still_has_are_the_ones_written_down(
    tmp_path: Path,
) -> None:
    """The rewordings that still get past this module, asserted not remembered.

    **This asserts nothing is allowed.** Every gate above still demands an
    empty offender list. This is a ledger of coverage, and the correct
    response to any line is to close it and delete the line — a failure here
    means someone closed a gap.

    * Hex glued to another hex character (`<key>00`): a run longer than 32,
      and the matcher deliberately refuses to fire inside one.
    * A key split across a concatenation. Nothing here parses source.
    * A value on the line after its name. Newline is excluded on purpose.
    * A name assembled at runtime from pieces.
    * A separator this module does not know (a tab, a prose arrow).
    * A value under `:`/`,`/`|` shorter than twelve characters, all letters,
      or carrying `.` or `/`.
    * A literal nested inside a shell expansion: `${NAME:=${OTHER:-<key>}}`.
    * More than five hundred characters along the line from the name.
    * More than eight characters of markup between the name and the operator.
    * A Markdown link or an HTML entity between the name and the operator.
    * An invisible character Unicode files as a LETTER (U+3164 HANGUL FILLER)
      glued to a value under `:`/`,`/`|` — `Lo` is neither whitespace nor an
      invisible category. The `=` family catches it.
    * An invisible character inside a hex run in a FILENAME. Bodies are
      re-read with invisibles stripped; a path is scanned as written, and a
      U+200B in the middle of a 32-hex stem is two runs of sixteen. The same
      key in a UTF-16 body with a U+200B inside it decodes the invisible into
      a stray byte pair rather than into nothing. Both are one decoding short
      of closed; neither is closed by pretending.
    * A body that is not text — base64 or otherwise encoded. Nothing decodes.
    * A text body wearing a binary suffix (`notes.pdf` full of ASCII). Its
      name is still scanned.
    * A symlink wearing a binary suffix: name and target hex-scanned, but out
      of the assignment corpus.
    * This file's own body.
    * A file committed under `data/raw/` whose body carries `{"id": <key>}`.
      That is the rule working as designed — the provider cache is the one
      place a record may be created — and it is also a directory anyone can
      commit into. The key is then green under `EXEMPT_SCOPE` and nowhere
      else; a hardcoded copy in `scripts/` is still a finding, asserted
      below. Nothing short of verifying a cached response against the
      provider closes this, and the sibling labs carry it too.
    * THIS LAB'S OWN: a key written into the `event_id` column of one of the
      two `NOMINATING_TABLES`. The bought-price cache those tables come from
      is gitignored, so the column is the only record of its ids, and a key
      placed there is indistinguishable from one. It is bounded to two files
      by name and one column, it turns the key green only under
      `EXEMPT_SCOPE`, and the row it sits in is a bet nobody placed — a
      review of the diff is what catches it.
    """
    name = GITHUB_SECRET_NAME
    value = "sk-live-4f19c0d27ba6e83d"
    key = "0123456789abcdef0123456789abcdef"
    gaps = {
        "padded.py": f'KEY = "{key}00"',
        "glued.py": f"ODDS{key}CACHE = 2",
        "split.py": f'KEY = "{key[:16]}" "{key[16:]}"',
        "block.yml": f"{name}: >\n  {value}",
        "next_line.env": f"{name}=\n{value}",
        "built.py": f'os.environ["FOOTBALL_ODDS_" "API_KEY"] = "{value}"',
        "arrow.md": f"{name} -> {value}",
        "column.tsv": f"{name}\t{value}",
        "short.yml": f"{name}: abc123def45",
        "encoded.py": 'KEY = "MDEyMzQ1Njc4OWFiY2RlZg=="',
        "closers.md": f"{name}]]]]]]]]]]: {value}",
        "link.md": f"[{name}](#the-secret): {value}",
        "entity.md": f"{name}&nbsp;= {value}",
        "filler.md": f"{name}:ㅤ{value}",
        "past_colon.md": f"{name}: <your-key> sk.live.4f19c0d27ba6e83d",
        "far.md": f"{name}: " + "prose " * 120 + value,
        "nested.sh": ': "${' + name + ':=${OTHER:-' + value + '}}"',
    }
    for filename, body in gaps.items():
        (tmp_path / filename).write_text(body + "\n", encoding="utf-8")
    paths = [tmp_path / filename for filename in sorted(gaps)]

    assert _hex_key_offenders(paths, set(), tmp_path) == []
    assert _assignment_offenders(paths, tmp_path) == []

    disguised = tmp_path / "notes.pdf"
    disguised.write_text(f'KEY = "{key}"\n{name} = "{value}"\n', encoding="utf-8")
    assert _body_scannable([disguised]) == []
    assert _hex_offenders_for_corpus([disguised], set(), tmp_path) == []

    cover = tmp_path / "cover.png"
    cover.symlink_to(f"{name}={value}")
    assert _assignment_offenders(_body_scannable([cover]), tmp_path) == []
    hex_cover = tmp_path / "art.png"
    hex_cover.symlink_to(key)
    assert _hex_offenders_for_corpus([hex_cover], set(), tmp_path) == [f"art.png: {key[:6]}..."]

    # A body planted under data/raw/ nominates, by the rule's own design,
    # and the nomination is spendable under EXEMPT_SCOPE only.
    raw = tmp_path / "data" / "raw" / "nfl" / "historical_probe"
    raw.mkdir(parents=True)
    planted = raw / f"{key}_20240101T000000Z_6.json"
    planted.write_text(json.dumps({"id": key, "bookmakers": []}), encoding="utf-8")
    outputs = tmp_path / "data" / "outputs"
    outputs.mkdir(parents=True)
    report = outputs / "planted.md"
    report.write_text(f"see {key}\n", encoding="utf-8")
    elsewhere = tmp_path / "scripts" / "planted.py"
    elsewhere.parent.mkdir()
    elsewhere.write_text(f'KEY = "{key}"\n', encoding="utf-8")
    content_ids, _ = _collect_event_ids([planted, report, elsewhere], tmp_path)
    assert content_ids == {key}
    assert _hex_key_offenders([planted, report, elsewhere], content_ids, tmp_path) == [
        f"scripts/planted.py: {key[:6]}..."
    ]
    elsewhere.unlink()

    # This lab's own gap: the bet-table column nominates.
    table = outputs / "nfl_props_backtest_bets.csv"
    table.write_text(f"event_id,market,price\n{key},pass_yards,-110\n", encoding="utf-8")
    sibling = outputs / "notes.md"
    sibling.write_text(f"see {key}\n", encoding="utf-8")
    content_ids, _ = _collect_event_ids([table, sibling], tmp_path)
    assert content_ids == {key}
    assert _hex_key_offenders([table, sibling], content_ids, tmp_path) == []
    # ...bounded: the same key is still a finding outside EXEMPT_SCOPE, and a
    # column of any other name in the same file nominates nothing.
    leak = tmp_path / "scripts" / "leak.py"
    leak.write_text(f'API_KEY = "{key}"\n', encoding="utf-8")
    assert _hex_key_offenders([leak], content_ids, tmp_path) == [f"scripts/leak.py: {key[:6]}..."]
    table.write_text(f"id,market,price\n{key},pass_yards,-110\n", encoding="utf-8")
    assert _collect_event_ids([table], tmp_path) == (set(), set())

    # ...and the halves of those gaps that are NOT open, so narrowing one
    # back fails here rather than passing quietly.
    caught = {
        "filler_equals.md": f"{name}=ㅤ{value}",
        "past_equals_real.sh": f"{name}=$UNUSED {value}",
        "eight_closers.md": f"{name}]]]]]]]]: {value}",
    }
    for filename, body in caught.items():
        (tmp_path / filename).write_text(body + "\n", encoding="utf-8")

    assert _assignment_offenders(
        [tmp_path / filename for filename in sorted(caught)], tmp_path
    ) == [f"{filename}: {name}" for filename in sorted(caught)]
