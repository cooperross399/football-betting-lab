"""Any script that settles bought prices must ask which season each event is in.

This defect has now appeared twice, in two scripts, written by the same hand
weeks apart, and both times it produced a plausible number rather than an
error:

* `props_backtest._game_weeks` matched a priced event to a club pair *within
  the target season* and ignored the event's own kickoff. 406 of 794 events
  settled against more than one season. It looked like three seasons of
  replication.
* `run_half_scoring_experiment.py` keyed `games_by_key` on `args.season` for
  every event in a frame holding all three bought seasons, so a 2023
  Chiefs-at-Broncos event settled against the 2025 meeting of the same clubs.
  Its verdict moved from −16.5% over 619 bets to −4.6% over 2,866.

`events_in_season` is the one answer to that question. This test says every
script that loads bought prices and settles them has to use it — directly, or
by delegating to `props_backtest.run`, which applies the same rule from each
event's own kickoff. The alternative — each script writing the filter itself —
is what produced both defects, and a comment asking the next author to
remember is not a check.
"""

from __future__ import annotations

from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"

#: Scripts that load bought prices only to count, cost or describe them. They
#: never settle a price against an outcome, so there is no season to get wrong.
#: Each entry is a deliberate exemption, not a backlog.
DOES_NOT_SETTLE = {
    "buy_historical_prices.py",       # buys, never scores
    "check_provider_quota.py",        # reads a header
    "estimate_credit_cost.py",        # arithmetic on the schedule
    "rerender_retention_probe.py",    # re-renders a recorded run
    "run_retention_probe.py",         # asks which markets exist
    "run_provider_shadow.py",         # stages a live board
    "run_price_sensitivity.py",       # re-prices already-settled bets
    "run_clv.py",                     # compares two prices, settles neither
    "run_allowlist_evidence.py",      # reads settled bets from file
    "run_gameday_card.py",            # today's slate; one season by definition
    # Joins two price snapshots to ALREADY-SETTLED outcomes on the wager
    # key (event, market, player, selection, line). It never maps an event
    # to a season, so there is no season for it to get wrong.
    "run_inactives_value.py",
    # Same shape as run_inactives_value.py: joins a devigged price to
    # ALREADY-SETTLED bets on the wager key (event, market, identity, line) and
    # inherits each row's season from the settled bet rather than assigning one.
    # It does not argue this — it CHECKS it at runtime on the real frame, and
    # refuses to report if any event spans two seasons or the join duplicates a
    # wager. Measured on the full population: 762 events, 0 spanning, max 1 row
    # per wager key. CI cannot run that check because the price cache is not
    # committed, which is why the guard lives in the script.
    "run_encompassing.py",
}


def _settling_scripts() -> list[Path]:
    found = []
    for path in sorted(SCRIPTS.glob("*.py")):
        if path.name in DOES_NOT_SETTLE:
            continue
        text = path.read_text(encoding="utf-8")
        if "load_bought_prices" in text:
            found.append(path)
    return found


def test_there_is_at_least_one_script_to_check() -> None:
    """A glob that matches nothing passes every assertion below it."""
    assert _settling_scripts(), "no settling scripts found; the glob is wrong"


@pytest.mark.parametrize(
    "path", _settling_scripts(), ids=lambda p: p.name
)
def test_a_script_that_settles_bought_prices_asks_which_season_they_are_in(
    path: Path,
) -> None:
    text = path.read_text(encoding="utf-8")
    # Either ask directly, or delegate to the one function that asks. `run`
    # matches each event to the season it was played in through `_game_weeks`,
    # which is where the original defect was found and fixed.
    delegates = "props_backtest.run(" in text
    assert delegates or "events_in_season" in text, (
        f"{path.name} loads bought prices and settles them without calling "
        "events_in_season. Every bought season is in that frame. Matching an "
        "event to a season the caller chose, rather than to the one it was "
        "played in, is the defect that invalidated every prop result in this "
        "repository — twice, in two scripts. If this script genuinely never "
        "settles a price, add it to DOES_NOT_SETTLE with the reason."
    )
