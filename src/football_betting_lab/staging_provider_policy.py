"""The fail-closed provider policy.

`data/manual/staging_provider_policy.json` decides which provider and which
markets the card may use, **per league**. It ships allowlisting nothing, and
every failure mode here resolves to "not allowed":

* file missing -> not allowed
* file unreadable -> not allowed
* file malformed -> not allowed
* entry for a different league -> not allowed
* market absent from `required_markets` -> not allowed
* allowlist entry without a reviewer and a receipt id -> not allowed
* receipt file named but not present on disk -> not allowed
* receipt present but not readable back as a transcription -> not allowed
* receipt recording a reviewer off the allow-list -> not allowed
* receipt whose id is not the digest of the approval it carries -> not allowed
* market named by the entry but not by the receipt -> not allowed
* evidence that has moved since the approval -> not allowed

That is the whole design. A policy loader that returns a permissive default on
an unreadable file is a policy loader that stops existing the moment something
goes wrong, which is exactly when it matters.

## Why the receipt is read and not merely counted

This used to stop at `receipt_path(entry).is_file()`. The file was never
opened: not the reviewer, not the markets, not the checksums it prints. So a
forged receipt — any file at all, with the right name — plus a hand-edited
entry made `market_allowed()` return True, which is the read-time half of the
mechanism agreeing to something the merge-time half would have refused. The
merge gate re-fetches from GitHub and catches it, but only on a pull request:
the card runs on a schedule, and "it would have been caught at merge" is not a
check that runs when the card runs. So the receipt is parsed and verified
here, every time it is read.

**What this cannot do, stated rather than implied.** Nothing in a receipt file
is unforgeable offline. Every field checked here — the reviewer, the digest,
the checksums — is computable by anything that can run code in this checkout,
so a determined forgery that writes a *self-consistent* receipt still reads as
one at this layer. What these checks remove is the whole class of forgery that
needed no consistency at all: any file, with the right name. The layer that
cannot be forged is the merge-time gate, which asks GitHub. This one raises
the cost and closes the gap between "a file exists" and "a file says
something", and that is the honest description of it.

## Why the entries are keyed by league

Approving `player_pass_yds` in the NFL says nothing about approving it in
college football, where the distribution, the roster churn and the books' own
coverage are all different. One receipt, one league. The key is
`the_odds_api:nfl`, built by `League.policy_key()`, so a policy file cannot
express "allowed everywhere" even by accident.

## What Claude may never do

Claude may prepare a policy change and open a pull request for it. Claude may
never write a receipt, add a name to `allowed_provider_names`, or add a market
to `required_markets`. Those are Cooper's, and the PR gate re-verifies the
paperwork on every policy change.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from football_betting_lab.config import MANUAL_DIR
from football_betting_lab.leagues import League
from football_betting_lab.markets import MARKETS_BY_KEY


POLICY_FILENAME = "staging_provider_policy.json"
RECEIPTS_DIRNAME = "human_acceptance_receipts"

#: The evidence reports sit beside the manual directory, not inside it. Named
#: here so a policy loaded from a checkout under `tmp_path` re-checks that
#: checkout's evidence rather than the repository's.
OUTPUTS_DIRNAME = "outputs"

#: The one provider this lab is built around. Naming it here does not allow
#: it; the policy file does that, and it does not.
ODDS_API_PROVIDER_NAME = "the_odds_api"


@dataclass(frozen=True)
class AllowlistEntry:
    """One league's reviewed approval, and exactly what it covers."""

    policy_key: str
    status: str
    approved_at: str
    reviewer_name: str
    evidence_receipt_id: str
    required_markets: tuple[str, ...]
    known_limitations: tuple[str, ...] = ()

    @property
    def is_allowed(self) -> bool:
        """Every condition, not any of them.

        A status of "allowed" with no reviewer is what a half-finished edit
        looks like, and it must not read as an approval.
        """
        return (
            self.status == "allowed"
            and bool(self.reviewer_name.strip())
            and bool(self.evidence_receipt_id.strip())
            and bool(self.required_markets)
        )


class StagingProviderPolicy:
    """What the card is allowed to read, and the reason when it is not."""

    def __init__(
        self,
        entries: dict[str, AllowlistEntry] | None = None,
        *,
        load_error: str = "",
        manual_dir: Path | None = None,
        outputs_dir: Path | None = None,
    ) -> None:
        self.entries = dict(entries or {})
        self.load_error = load_error
        self.manual_dir = Path(manual_dir) if manual_dir else MANUAL_DIR
        # Beside the manual directory by default, which is the repository's
        # own layout and a test checkout's too. It names where the evidence
        # is, never who approved anything.
        self.outputs_dir = (
            Path(outputs_dir)
            if outputs_dir
            else self.manual_dir.parent / OUTPUTS_DIRNAME
        )
        #: One verification per receipt per load, because `allowed_markets`
        #: asks about every market in the registry and the answer does not
        #: depend on the market. Each value is (the problem or "", the markets
        #: the receipt names).
        self._receipt_verdicts: dict[tuple[str, str], tuple[str, tuple[str, ...]]] = {}

    # -- loading ----------------------------------------------------------

    @classmethod
    def load(
        cls,
        path: Path | None = None,
        *,
        manual_dir: Path | None = None,
        outputs_dir: Path | None = None,
    ) -> "StagingProviderPolicy":
        directory = Path(manual_dir) if manual_dir else MANUAL_DIR
        target = Path(path) if path else directory / POLICY_FILENAME
        if not target.is_file():
            return cls(
                load_error=f"No policy file at {target}.",
                manual_dir=directory,
                outputs_dir=outputs_dir,
            )
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            return cls(
                load_error=f"The policy file could not be read: {exc}.",
                manual_dir=directory,
                outputs_dir=outputs_dir,
            )
        if not isinstance(payload, dict):
            return cls(
                load_error="The policy file is not a JSON object.",
                manual_dir=directory,
                outputs_dir=outputs_dir,
            )
        raw = payload.get("provider_allowlist_entries")
        if not isinstance(raw, dict):
            return cls(manual_dir=directory, outputs_dir=outputs_dir)

        entries: dict[str, AllowlistEntry] = {}
        for key, value in raw.items():
            if not isinstance(value, dict):
                continue
            entries[str(key)] = AllowlistEntry(
                policy_key=str(key),
                status=str(value.get("allowlist_status", "")).strip().lower(),
                approved_at=str(value.get("approved_at", "")).strip(),
                reviewer_name=str(value.get("reviewer_name", "")).strip(),
                evidence_receipt_id=str(value.get("evidence_receipt_id", "")).strip(),
                required_markets=tuple(
                    str(item).strip()
                    for item in (value.get("required_markets") or [])
                    if str(item).strip()
                ),
                known_limitations=tuple(
                    str(item) for item in (value.get("known_limitations") or [])
                ),
            )
        return cls(entries, manual_dir=directory, outputs_dir=outputs_dir)

    # -- decisions --------------------------------------------------------

    def entry_for(self, league: League) -> AllowlistEntry | None:
        return self.entries.get(league.policy_key())

    def receipt_path(self, entry: AllowlistEntry) -> Path:
        return self.manual_dir / RECEIPTS_DIRNAME / f"{entry.evidence_receipt_id}.md"

    def receipt_problem(self, entry: AllowlistEntry, league: League) -> str:
        """Why this entry's receipt is not a transcription, or "" when it is.

        Everything here is read out of the receipt file and compared against
        something the file does not control: the allow-list in
        `github_approval`, the digest of the approval the receipt carries, its
        own filename, and the evidence on disk. None of it asks the policy
        entry what to think, because the policy entry is the thing being
        checked.

        Imported inside the function: `human_acceptance_receipt` imports this
        module for `RECEIPTS_DIRNAME`, so a module-level import here would be
        a cycle. The cost is one deferred import per load.
        """
        from football_betting_lab.github_approval import (
            ALLOWED_REVIEWERS,
            APPROVAL_DECISION,
            EVIDENCE_REPORTS,
            evidence_checksums,
        )
        from football_betting_lab.human_acceptance_receipt import (
            ReceiptError,
            read_receipt,
            receipt_id,
        )

        key = (league.policy_key(), entry.evidence_receipt_id)
        cached = self._receipt_verdicts.get(key)
        if cached is not None:
            return cached[0]

        def remember(problem: str, markets: tuple[str, ...] = ()) -> str:
            self._receipt_verdicts[key] = (problem, markets)
            return problem

        path = self.receipt_path(entry)
        try:
            binding = read_receipt(path)
        except ReceiptError as exc:
            return remember(
                f"the receipt at {path} is not readable as a transcription: {exc}"
            )

        if binding.get("decision") != APPROVAL_DECISION:
            return remember(
                f"the receipt records decision {binding.get('decision')!r}, not "
                f"{APPROVAL_DECISION!r}"
            )
        if str(binding.get("policy_key") or "") != entry.policy_key:
            return remember(
                f"the receipt covers `{binding.get('policy_key')}` and the "
                f"entry is `{entry.policy_key}`. One receipt, one league"
            )
        login = str(binding.get("reviewer_github_login") or "").strip()
        if login.lower() not in {name.lower() for name in ALLOWED_REVIEWERS}:
            return remember(
                f"the receipt's reviewer `{login or 'nobody'}` is not on the "
                "allow-list, so it transcribes nobody's approval"
            )
        if entry.reviewer_name.strip().lower() != login.lower():
            return remember(
                f"the entry credits `{entry.reviewer_name}` and the receipt "
                f"records `{login}`. The reviewer is whoever GitHub reported"
            )

        approval = binding.get("github_approval")
        if not isinstance(approval, dict):
            return remember(
                "the receipt records no GitHub approval, so nothing in it says "
                "a human signed anything"
            )
        expected = receipt_id(approval)
        if expected != str(binding.get("receipt_id") or ""):
            return remember(
                f"the receipt's id `{binding.get('receipt_id')}` is not the "
                f"digest of the approval it carries (`{expected}`). A receipt "
                "id is derived from the human act, not chosen"
            )
        if expected != entry.evidence_receipt_id:
            return remember(
                f"the entry names receipt `{entry.evidence_receipt_id}` and the "
                f"file records `{expected}`"
            )

        stored = dict(binding.get("evidence_checksums_sha256") or {})
        expected_names = {
            league.output_name(stem, suffix) for stem, suffix in EVIDENCE_REPORTS
        }
        absent = sorted(expected_names - set(stored))
        if absent:
            return remember(
                f"the receipt binds to no checksum for {absent}. An approval "
                "bound to some of the evidence is an approval nobody gave on "
                "the rest of it"
            )
        current = evidence_checksums(league, self.outputs_dir)
        moved = sorted(
            name
            for name in set(stored) | set(current) | expected_names
            if stored.get(name) != current.get(name)
        )
        if moved:
            return remember(
                f"the evidence has changed since the approval: {moved}. The "
                "reviewer signed a state, and the state moved"
            )
        return remember(
            "",
            tuple(
                str(item).strip()
                for item in (binding.get("approved_markets") or [])
                if str(item).strip()
            ),
        )

    def market_allowed(self, league: League, market: str) -> bool:
        """The one question the card asks. Every path out of it is explicit."""
        if self.load_error:
            return False
        entry = self.entry_for(league)
        if entry is None or not entry.is_allowed:
            return False
        key = str(market).strip()
        if key not in MARKETS_BY_KEY:
            # A market this lab cannot price or settle is never allowed, even
            # if a policy file names it. The policy grants permission; it does
            # not confer the ability to settle a bet.
            return False
        if key not in entry.required_markets:
            return False
        # The receipt must exist on disk, not merely be named. An id pointing
        # at nothing is the shape a fabricated approval takes.
        if not self.receipt_path(entry).is_file():
            return False
        # ...and it must read back as a transcription of a real approval. The
        # file used to be counted and never opened.
        if self.receipt_problem(entry, league):
            return False
        # The market has to be one the receipt actually names. The entry's own
        # `required_markets` is the list being checked, not the authority.
        return key in self.receipted_markets(entry, league)

    def receipted_markets(
        self, entry: AllowlistEntry, league: League
    ) -> tuple[str, ...]:
        """The markets a verified receipt names, or nothing when it is not one."""
        if self.receipt_problem(entry, league):
            return ()
        _, markets = self._receipt_verdicts[
            (league.policy_key(), entry.evidence_receipt_id)
        ]
        return markets

    def refusal_reason(self, league: League, market: str) -> str:
        """Why a market is not allowed, in words a card can print."""
        if self.load_error:
            return (
                f"{self.load_error} A policy that cannot be read allows "
                "nothing, so no market may reach the card."
            )
        entry = self.entry_for(league)
        if entry is None:
            if self.entries:
                # There are approvals, just not for this league. Say which,
                # because "no approval anywhere" and "approved next door"
                # are different situations and only one of them is a
                # question for Cooper.
                return (
                    f"No approval covers `{league.policy_key()}`. Other "
                    f"entries exist ({', '.join(sorted(self.entries))}) and "
                    "none carries across: the distributions, the roster churn "
                    "and the books' coverage differ by league."
                )
            return (
                "No market has a reviewed approval yet. Allowlisting takes "
                "measurement against real prices and a signed human "
                "acceptance receipt, and this is the correct state until "
                "both exist."
            )
        if not entry.is_allowed:
            missing = [
                name
                for name, present in (
                    ("a status of 'allowed'", entry.status == "allowed"),
                    ("a reviewer name", bool(entry.reviewer_name.strip())),
                    ("an evidence receipt id", bool(entry.evidence_receipt_id.strip())),
                    ("a non-empty market list", bool(entry.required_markets)),
                )
                if not present
            ]
            return (
                f"The allowlist entry for `{league.policy_key()}` is not a "
                f"complete approval: it lacks {', '.join(missing)}."
            )
        key = str(market).strip()
        if key not in MARKETS_BY_KEY:
            return (
                f"`{key}` is not a market this lab knows how to price or "
                "settle, so no approval can make it usable."
            )
        if key not in entry.required_markets:
            return (
                f"`{key}` is not named in the reviewed approval for "
                f"`{league.policy_key()}` (receipt "
                f"`{entry.evidence_receipt_id}`). Measurement and a signed "
                "human acceptance receipt are what add a market; nothing else."
            )
        path = self.receipt_path(entry)
        if not path.is_file():
            return (
                f"The approval names receipt `{entry.evidence_receipt_id}` but "
                f"no such file exists at {path}. An id pointing at nothing is "
                "not an approval."
            )
        problem = self.receipt_problem(entry, league)
        if problem:
            return (
                f"The receipt for `{league.policy_key()}` is not a "
                f"transcription of a real approval: {problem}. A file in the "
                "receipts directory is not a signature; what it reads back as "
                "is."
            )
        if key not in self.receipted_markets(entry, league):
            return (
                f"`{key}` is named by the policy entry and not by the receipt "
                f"`{entry.evidence_receipt_id}`, which approves "
                f"{sorted(self.receipted_markets(entry, league))}. The receipt "
                "is what was signed; the entry is what somebody typed."
            )
        return ""

    def allowed_markets(self, league: League) -> tuple[str, ...]:
        entry = self.entry_for(league)
        if entry is None:
            return ()
        return tuple(
            market
            for market in entry.required_markets
            if self.market_allowed(league, market)
        )

    def summary_line(self, league: League) -> str:
        allowed = self.allowed_markets(league)
        if not allowed:
            return (
                f"No market is allowlisted for {league.title}. That is the "
                "correct state until a market has been measured against real "
                "prices and Cooper has signed a receipt."
            )
        return (
            f"{len(allowed)} market(s) allowlisted for {league.title}: "
            f"{', '.join(allowed)}."
        )


def write_starter_policy(path: Path) -> None:
    """Write the shipping policy: allowlisting nothing.

    Exists so the file's default state is created by code with a comment
    explaining itself, rather than by hand where a future edit could quietly
    turn an empty list into a populated one with no reviewer.
    """
    payload: dict[str, Any] = {
        "_comment": [
            "This file decides which provider and which markets the card may",
            "use, per league. It ships allowlisting NOTHING, and that is the",
            "correct state until a market has been measured against real",
            "prices and Cooper has reviewed the evidence and signed a human",
            "acceptance receipt.",
            "",
            "Entries are keyed `{provider}:{league}`. Approving a market in",
            "the NFL never approves it in NCAAF.",
            "",
            "Claude may prepare a change to this file and open a pull request",
            "for it. Claude may never add a provider, add a market, or write a",
            "receipt. See docs/provider_allowlist_approval.md.",
        ],
        "allowed_provider_names": [],
        "provider_allowlist_entries": {},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
