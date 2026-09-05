"""No league literal may appear outside the league registry.

This is the test that makes "adding NCAAF is a registry entry, not a
refactor" true rather than aspirational. Without it the guarantee is a
promise in a docstring, and the moment to discover it was broken is during
the NCAAF build, after the cost has been paid.

What is banned, precisely:

* the provider's sport-key prefix (`americanfootball_`), anywhere outside
  `leagues.py`;
* a string constant that *is* a league key (`"nfl"`, `"ncaaf"`), or that uses
  one as a path or filename segment.

What is deliberately **not** banned: the letters NFL in prose. A docstring
explaining that NFL margins pile up on 3 and 7 is documentation, not a
dependency, and a test that forbade it would be gamed by rewording rather
than by fixing anything.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from football_betting_lab.leagues import LEAGUES, league_keys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REGISTRY = PROJECT_ROOT / "src" / "football_betting_lab" / "leagues.py"

#: Every league key the registry knows, plus the one not built yet. NCAAF is
#: listed on purpose: the test has to be able to fail *before* the league is
#: added, or it protects nothing at the moment it matters.
BANNED_LEAGUE_KEYS = frozenset(set(league_keys()) | {"ncaaf"})

#: The provider's own vocabulary for these leagues.
BANNED_SPORT_KEY_PREFIX = "americanfootball_"


def python_files() -> list[Path]:
    roots = (PROJECT_ROOT / "src", PROJECT_ROOT / "scripts")
    return sorted(
        path
        for root in roots
        if root.is_dir()
        for path in root.rglob("*.py")
        if "__pycache__" not in path.parts and path != REGISTRY
    )


def docstring_nodes(tree: ast.AST) -> set[int]:
    """Every string constant that is a docstring, by id.

    Docstrings are prose about the code and are exempt. Everything else is a
    value the code actually uses.
    """
    found: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            body = getattr(node, "body", [])
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                found.add(id(body[0].value))
    return found


def offending_strings(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    exempt = docstring_nodes(tree)
    problems: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        if id(node) in exempt:
            continue
        text = node.value
        lowered = text.lower()
        if BANNED_SPORT_KEY_PREFIX in lowered:
            problems.append((node.lineno, text))
            continue
        for key in BANNED_LEAGUE_KEYS:
            if lowered == key or f"/{key}/" in lowered or lowered.startswith(f"{key}_"):
                problems.append((node.lineno, text))
                break
    return problems


def test_the_corpus_is_not_empty() -> None:
    """An empty parametrisation collects nothing and reports green."""
    files = python_files()
    assert len(files) > 50, f"only {len(files)} Python files found; the roots are wrong"
    assert REGISTRY not in files and REGISTRY.is_file()


@pytest.mark.parametrize("path", python_files(), ids=lambda p: str(p.name))
def test_no_module_outside_the_registry_writes_a_league_literal(path: Path) -> None:
    problems = offending_strings(path)
    assert not problems, (
        f"{path.relative_to(PROJECT_ROOT)} writes a league literal that belongs "
        f"in leagues.py: {problems}. Take it from the League — "
        "`league.provider_sport_key`, `league.data_dir_segment`, "
        "`league.output_name(...)`, `league.policy_key()` — so that adding "
        "NCAAF is a registry entry and not a search-and-replace."
    )


def test_the_registry_holds_exactly_the_leagues_that_are_built() -> None:
    """The NFL ships; NCAAF does not exist yet. Both facts are asserted.

    The second half matters more than it looks. A registry that quietly
    gained an NCAAF entry would let college markets be fetched, priced and
    frozen into the ledger before a single NCAAF measurement existed.
    """
    assert league_keys() == ("nfl",)
    assert "ncaaf" not in LEAGUES


def test_every_league_names_an_adapter_and_a_market_registry() -> None:
    for key, league in LEAGUES.items():
        assert league.key == key
        assert league.provider_sport_key.startswith(BANNED_SPORT_KEY_PREFIX)
        assert league.data_adapter, f"{key} names no data adapter"
        assert league.market_registry, f"{key} names no market registry"
        assert league.daily_credit_cap > 0, f"{key} has no credit cap"


def test_outputs_are_league_prefixed_so_two_leagues_cannot_overwrite_each_other() -> None:
    """An unprefixed output is a file two leagues would both write.

    The second one to run would silently become the record, and the evidence
    for the first would be gone with no error anywhere.
    """
    for league in LEAGUES.values():
        name = league.output_name("forward_evidence", ".md")
        assert name.startswith(f"{league.key}_")
        assert name == f"{league.key}_forward_evidence.md"


def test_allowlisting_a_market_in_one_league_cannot_allowlist_it_in_another() -> None:
    """Policy keys carry the league, so a receipt covers one league only."""
    keys = {league.policy_key() for league in LEAGUES.values()}
    assert len(keys) == len(LEAGUES)
    for league in LEAGUES.values():
        assert league.policy_key().endswith(f":{league.key}")


def test_no_module_hardcodes_how_many_clubs_a_league_has() -> None:
    """A club count is a league fact and belongs in the registry.

    This test exists because two of them escaped. `EXPECTED_NFL_CLUBS = 32`
    sat in `season.py`, and `run_feed_freshness.py` read
    `len(league.club_abbreviations()) if hasattr(...) else 32` — where `League`
    has no such attribute, so the literal fired every single time and the check
    was a hardcoded 32 wearing a registry's clothes.

    Both were correct for the NFL by accident, which is why nothing caught
    them. Neither would have been correct for a league with a different number
    of clubs, and a schedule cache that had lost a hundred teams would have
    passed a 32-club completeness check trivially.

    The existing discipline test bans league keys and sport-key prefixes. It
    does not ban magic numbers, and a count is exactly as much a league literal
    as a name is.
    """
    from football_betting_lab.providers.team_names import abbreviations

    counts = {len(abbreviations(league)) for league in LEAGUES.values()}
    offenders: list[str] = []
    for path in python_files():
        if path.name in {"leagues.py", "team_names.py"}:
            continue
        for number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            code = line.split("#")[0]
            for count in counts:
                # A bare club count compared against something, which is the
                # shape both escapees had.
                if f"= {count}" in code or f">= {count}" in code or f"else {count}" in code:
                    offenders.append(f"{path.name}:{number}: {line.strip()}")
    assert not offenders, (
        "A league's club count is written here instead of read from the "
        "registry:\n  " + "\n  ".join(offenders)
    )


def test_the_club_count_actually_comes_from_the_registry() -> None:
    """The positive half: `expected_clubs` must move when the registry does,
    which a hardcoded literal cannot do."""
    from football_betting_lab.providers.team_names import abbreviations
    from football_betting_lab.season import expected_clubs

    for league in LEAGUES.values():
        assert expected_clubs(league) == len(abbreviations(league))
