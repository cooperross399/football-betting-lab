"""Every hypothesis this lab has ever tested, and the correction that implies.

Cooper's instruction is to keep searching all season. That is the right
ambition and it has one failure mode, which this file exists to close.

**A search that runs every week is not twelve tests. It is twelve tests a week,
forever.** Correcting a Sunday's findings across "the twelve things I tested
today" is a lie if twelve more were tested last Sunday and twelve more the one
before. Over a season that is hundreds of looks, and at a nominal 5% threshold
roughly one in twenty of them clears by chance alone. An automated edge-hunter
without a cumulative tally does not find edges; it manufactures them on a
schedule, and it manufactures them with clean intervals and good prose.

So this is an **append-only** record of every hypothesis ever put to the data,
across every search, and the correction factor it hands back grows with the
count. The fiftieth test does not get the first test's benefit of the doubt.

## Why append-only, and what enforces it

The tempting edit is to drop the tests that failed, on the reasoning that they
were exploratory. That reasoning is exactly backwards: the failed tests are
what make the surviving one unlikely to be chance. A ledger that can shrink is
a ledger that will, one honest-seeming commit at a time, and the correction it
reports afterwards is smaller than the truth.

This heading used to read "enforced", and it was not. `save()` refused a
shrink by re-reading the file it was about to overwrite, and the only caller —
`scripts/record_experiments.py` — loads that same file first, so the guard
compared n against n and could never fire. Reproduced on this lab: hand-delete
eighteen entries from the tracked JSON, run the recorder, and it re-rendered
53 -> 35 without complaint and printed x1.69 -> x1.63 in the same prose.

Two things enforce it now, and each covers what the other cannot:

* `save()` takes the caller's pre-mutation entry count as an explicit `floor`,
  so an in-process shrink — a filter, a rebuild, a bug — is refused at the
  write. The recorder also reads the count committed at `HEAD` and passes the
  larger of the two, so a ledger edited by hand *before* the run is refused
  from inside a git checkout as well.
* `scripts/check_ledger_append_only.py`, run by `.github/workflows/ledger-guard.yml`
  on every pull request, diffs the ledger on the branch against the ledger at
  the PR base and refuses a removed key, a count drop, a rewritten outcome or
  date, and a same-key contradiction on either side. That is the half no
  runtime check reaches: a PR diff never calls `save()`.

What neither reaches: an appended hypothesis is taken on trust, and an edit
that survives both is one made in a checkout with no `HEAD` copy and merged
past a red required check — which branch protection on this repository does
not allow.

## What this is not

It is not a substitute for a held-out season. A correction widens an interval;
it cannot tell you whether a result reproduces. Replication remains the bar.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from statistics import NormalDist

#: The file, under `data/outputs/` like every other record the lab keeps.
LEDGER_FILENAME = "experiment_ledger.json"

#: The nominal two-sided level every interval in this lab is quoted at.
ALPHA = 0.05


@dataclass(frozen=True)
class Hypothesis:
    """One thing that was put to the data, once."""

    search: str
    name: str
    tested_on: str
    seasons: tuple[int, ...]
    outcome: str

    def key(self) -> tuple[str, str, tuple[int, ...]]:
        """What makes two entries the same test.

        The same hypothesis re-run on the same seasons is one degree of
        freedom, not two — re-running a script must not inflate the
        correction, or nobody will re-run anything.
        """
        return (self.search, self.name, self.seasons)


@dataclass
class ExperimentLedger:
    hypotheses: list[Hypothesis] = field(default_factory=list)

    @property
    def count(self) -> int:
        """Distinct hypotheses ever tested. The family size for any new claim."""
        return len({h.key() for h in self.hypotheses})

    def correction_factor(self, *, extra: int = 0) -> float:
        """How much wider a 95% interval has to be, given everything ever tested.

        Bonferroni on the cumulative count. Conservative on purpose: the
        alternatives (Holm, Benjamini-Hochberg) need the full set of p-values
        to be in hand at once, and this lab's tests arrive one week at a time
        over a season. A correction that can be computed incrementally and is
        slightly too wide beats one that is exactly right and cannot be
        computed until the season is over.
        """
        families = max(self.count + extra, 1)
        if families == 1:
            return 1.0
        return NormalDist().inv_cdf(1 - (ALPHA / families) / 2) / 1.96

    def record(self, *hypotheses: Hypothesis) -> int:
        """Add hypotheses. Returns how many were new."""
        seen = {h.key() for h in self.hypotheses}
        added = 0
        for entry in hypotheses:
            if entry.key() in seen:
                continue
            seen.add(entry.key())
            self.hypotheses.append(entry)
            added += 1
        return added

    def by_search(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for entry in self.hypotheses:
            counts[entry.search] = counts.get(entry.search, 0) + 1
        return counts


def load(path: Path) -> ExperimentLedger:
    """The ledger, or an empty one. An absent file is a lab that has tested
    nothing, which is a true statement about a fresh clone."""
    if not Path(path).is_file():
        return ExperimentLedger()
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return ExperimentLedger(
        hypotheses=[
            Hypothesis(
                search=str(e.get("search", "")),
                name=str(e.get("name", "")),
                tested_on=str(e.get("tested_on", "")),
                seasons=tuple(int(s) for s in e.get("seasons", [])),
                outcome=str(e.get("outcome", "")),
            )
            for e in payload.get("hypotheses", [])
        ]
    )


def save(ledger: ExperimentLedger, path: Path, *, floor: int) -> Path:
    """Write the ledger, refusing to shrink it below `floor` entries.

    The guard is the point. The tempting edit is to drop the tests that failed
    because they were "exploratory"; the failed tests are precisely what make a
    surviving one unlikely to be chance. This raises rather than warns, because
    a warning in a workflow log is not a guard.

    `floor` is required and it is the caller's pre-mutation count — how many
    entries the ledger held before this run touched it. It used to be measured
    here by re-reading `path`, and that was a guard that could not fire: the
    only caller loads `path`, mutates the object, and saves it back to `path`,
    so the file on disk always held exactly what was loaded and the comparison
    was n against n. `test_a_hand_edited_ledger_is_refused_by_the_floor` is
    the reproduction. The file is still read as a second floor, because it
    costs nothing and it is the one that stays correct if a caller passes a
    floor of zero; but it is the explicit floor that makes the guard real.
    """
    if not isinstance(floor, int) or isinstance(floor, bool) or floor < 0:
        raise TypeError(f"floor must be a non-negative int, got {floor!r}")
    target = Path(path)
    on_disk = len(load(target).hypotheses) if target.is_file() else 0
    lowest_permitted = max(floor, on_disk)
    if len(ledger.hypotheses) < lowest_permitted:
        raise ValueError(
            f"The experiment ledger would fall from {lowest_permitted} entries "
            f"to {len(ledger.hypotheses)}. "
            "It is append-only: the tests that failed are what make a "
            "surviving one unlikely to be chance, and a ledger that can "
            "shrink reports a correction smaller than the truth."
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            {
                "hypotheses": [
                    {
                        "search": h.search,
                        "name": h.name,
                        "tested_on": h.tested_on,
                        "seasons": list(h.seasons),
                        "outcome": h.outcome,
                    }
                    for h in ledger.hypotheses
                ]
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return target


def render(ledger: ExperimentLedger) -> str:
    lines: list[str] = []
    add = lines.append
    add("# Everything this lab has ever tested")
    add("")
    add(
        "**A search that runs every week is not twelve tests. It is twelve "
        "tests a week, forever.** Correcting today's findings across today's "
        "twelve is a lie if twelve more were tested last week. At a nominal 5% "
        "threshold roughly one look in twenty clears by chance, so an "
        "automated edge-hunter without a cumulative tally does not find edges "
        "— it manufactures them on a schedule, with clean intervals and good "
        "prose."
    )
    add("")
    if not ledger.hypotheses:
        add(
            "**Nothing has been recorded yet.** That is a true statement about "
            "a fresh clone and a false one about this lab; if you are seeing "
            "it here, the ledger did not load."
        )
        return "\n".join(lines) + "\n"

    factor = ledger.correction_factor()
    add(
        f"**{ledger.count} distinct hypotheses tested.** Any new 95% interval "
        f"must be widened by **x{factor:.2f}** before it means what it says."
    )
    add("")
    add("| Search | Hypotheses |")
    add("|:---|---:|")
    for search, n in sorted(ledger.by_search().items(), key=lambda kv: -kv[1]):
        add(f"| {search} | {n} |")
    add("")
    add("| # | Search | Hypothesis | Seasons | Tested | Outcome |")
    add("|---:|:---|:---|:---|:---|:---|")
    for i, h in enumerate(ledger.hypotheses, start=1):
        seasons = ", ".join(str(s) for s in h.seasons) or "—"
        add(
            f"| {i} | {h.search} | {h.name} | {seasons} | {h.tested_on} | "
            f"{h.outcome} |"
        )
    add("")
    add(
        "The correction is Bonferroni on the cumulative count — conservative on "
        "purpose. Holm and Benjamini-Hochberg need every p-value in hand at "
        "once, and this lab's tests arrive one week at a time over a season. A "
        "correction that can be computed incrementally and is slightly too wide "
        "beats one that is exactly right and cannot be computed until the "
        "season is over."
    )
    add("")
    add(
        "**This is not a substitute for a held-out season.** A correction "
        "widens an interval; it cannot tell you whether a result reproduces. "
        "Replication remains the bar."
    )
    return "\n".join(lines) + "\n"
