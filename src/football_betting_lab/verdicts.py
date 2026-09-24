"""Recorded experiment verdicts, read by the things that obey them.

Nothing in this repository ships a modelling policy by assertion. An
experiment measures the policy against real prices, records its verdict as a
`ships` list in a JSON file under `data/outputs/`, and the card and the model
read that list rather than hard-coding the decision — so the shipped
configuration is **auditable against the measurement that made it**, and
reverting a policy is re-running its experiment rather than editing code.

A missing or unreadable verdict file ships nothing. The conservative reading
of "no recorded decision" is "no policy in force".

## Why a file rather than a constant

A constant in code says *what* is in force. It cannot say *why*, *when*, or
*on what evidence*, and it cannot be checked against the experiment that
supposedly justified it. Six months later nobody can tell whether a flag was
set because a measurement won or because it looked sensible on a Tuesday.

The NHL lab's answer is this one, ported: the experiment writes its own
verdict, the code reads it, and the two cannot drift because there is only one
of them.

## The rule that matters most here

**Each variant tested against the same bought season burns a degree of
freedom.** The props backtest is one season, 67% sampled; testing five model
variants against it and shipping the best is how a lab talks itself into
noise. So a verdict file records `variants_tested`, every report that cites it
prints that count, and a verdict claiming an edge on a season the variant was
selected on is a **candidate**, not a finding.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from football_betting_lab.config import OUTPUTS_DIR
from football_betting_lab.leagues import League


#: Every verdict this repository can record, and the file that records it.
#: A policy absent from here has no door to come through, which is the point:
#: `ships()` raises on an unknown policy rather than returning False, because
#: a typo that silently disables a policy is worse than one that stops a run.
VERDICT_FILES: dict[str, str] = {
    # Exponential recency weighting on a player's opportunity rate. A role
    # from two seasons ago is not this season's role.
    "props_recency_weighting": "props_recency_experiment",
    # A within-game scoring model, which the half and quarter markets need.
    "half_scoring_model": "half_scoring_experiment",
    # Whether a player prop may produce a selection for a player who carries
    # no injury designation. Measured: 2.2% of such selections void and every
    # player listed Out or Doubtful voids 100% of the time.
    #
    # This entry used to say the result rested on one line in a book's rules,
    # "which turns +13.0% into -0.8%", and that the verdict waited for a human
    # who had read them. Both halves of that have moved:
    #
    # * The +13.0%/-0.8% pair is **retracted** — computed on
    #   cross-season-settled bets, see `reports/availability_cost.py`. The
    #   corrected pair is -3.7% against -5.8%.
    # * The rules **have been read**, on 2026-09-23, from state-regulator
    #   filings and operator rules pages: `docs/did_not_play_rules.md`. Books
    #   void, symmetrically — except Bovada, which keys on the game-day active
    #   roster and grades a player who is active and never plays.
    #
    # So the stated blocker is gone and the verdict still does not ship, for a
    # different and better reason: the population it would open measures -3.7%.
    # `CLAUDE.md` puts it plainly — the clause "is still worth answering before
    # anything is acted on, but nothing waits on it."
    "props_selectable_when_undesignated": "availability_policy",
}


@dataclass(frozen=True)
class Verdict:
    """One recorded decision, and the evidence that made it."""

    policy: str
    ships: bool
    measured_on: str = ""
    variants_tested: int = 0
    summary: str = ""

    def citation(self) -> str:
        """The sentence a report prints beside anything this verdict governs."""
        state = "in force" if self.ships else "not in force"
        line = f"`{self.policy}` is **{state}**"
        if self.measured_on:
            line += f", decided on {self.measured_on}"
        if self.variants_tested > 1:
            line += (
                f", one of **{self.variants_tested} variants** tested against "
                "the same data — a degree of freedom spent, and the reason "
                "this is a candidate rather than a finding"
            )
        return line + ("." if not self.summary else f". {self.summary}")


def verdict_path(policy: str, league: League, output_dir: Path | None = None) -> Path:
    stem = VERDICT_FILES.get(str(policy))
    if stem is None:
        raise KeyError(
            f"No experiment records a verdict for {policy!r}. Known: "
            f"{sorted(VERDICT_FILES)}"
        )
    directory = Path(output_dir) if output_dir else Path(OUTPUTS_DIR)
    return directory / league.output_name(stem, ".json")


def read(policy: str, league: League, *, output_dir: Path | None = None) -> Verdict:
    """The recorded verdict, or a not-in-force one when there is none."""
    path = verdict_path(policy, league, output_dir)
    absent = Verdict(policy=policy, ships=False, summary="No verdict is recorded.")
    if not path.is_file():
        return absent
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return Verdict(
            policy=policy,
            ships=False,
            summary=f"The verdict file at {path.name} could not be read.",
        )
    if not isinstance(payload, dict):
        return absent
    listed = payload.get("ships")
    shipped = isinstance(listed, list) and str(policy) in [str(x) for x in listed]
    return Verdict(
        policy=policy,
        ships=shipped,
        measured_on=str(payload.get("measured_on", "")),
        variants_tested=int(payload.get("variants_tested", 0) or 0),
        summary=str(payload.get("summary", "")),
    )


def ships(policy: str, league: League, *, output_dir: Path | None = None) -> bool:
    """Whether the recorded verdict for `policy` says it is in force."""
    return read(policy, league, output_dir=output_dir).ships


def record(
    policy: str,
    league: League,
    *,
    ships_it: bool,
    measured_on: str,
    variants_tested: int,
    summary: str,
    output_dir: Path | None = None,
) -> Path:
    """Write a verdict. Only an experiment calls this, never the card.

    The separation is the design: the thing that measures writes the verdict,
    the thing that prices reads it, and neither can quietly become the other.
    """
    path = verdict_path(policy, league, output_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "policy": policy,
                "league": league.key,
                "ships": [policy] if ships_it else [],
                "measured_on": measured_on,
                "variants_tested": variants_tested,
                "summary": summary,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def describe(league: League, *, output_dir: Path | None = None) -> str:
    """One line per policy, for run logs and the card."""
    return ", ".join(
        f"{policy}={'in force' if ships(policy, league, output_dir=output_dir) else 'off'}"
        for policy in sorted(VERDICT_FILES)
    )
