"""Reading the ledger back, with every instrument the historical work earned.

The ledger is the only evidence this lab can still gather — the bought
population is complete — so it is the one place a mistake in reading it
compounds for a whole season.
"""

from __future__ import annotations

import pandas as pd

from football_betting_lab.forward_evidence import render_ledger
from football_betting_lab.leagues import NFL


def _ledger(rows: list[dict]) -> pd.DataFrame:
    base = {
        "snapshot_date": "2026-09-13",
        "home_team": "Seattle Seahawks",
        "away_team": "New England Patriots",
        "market": "rush_yards",
        "outcome": "won",
        "profit_units": 1.0,
    }
    return pd.DataFrame([{**base, **row} for row in rows])


def _many(market: str, n: int, profit: float, outcome: str = "won") -> list[dict]:
    return [
        {
            "market": market,
            "outcome": outcome,
            "profit_units": profit,
            "snapshot_date": f"2026-09-{13 + i % 15:02d}",
            "home_team": f"H{i % 30}",
            "away_team": f"A{i % 30}",
        }
        for i in range(n)
    ]


def test_an_empty_ledger_offers_no_number() -> None:
    text = render_ledger(pd.DataFrame(), NFL)

    assert "ledger is empty" in text
    assert "absence, not a result" in text


def test_a_settlement_suspect_is_reported_as_not_evidence() -> None:
    """`tackles_assists` returned +16% across three bought seasons on a
    settlement offset alone. The ledger must not repeat that reading."""
    ledger = _ledger(_many("tackles_assists", 400, 1.0))

    text = render_ledger(
        ledger, NFL, settlement_suspects=frozenset({"tackles_assists"})
    )

    assert "not evidence" in text
    assert "settlement suspect" in text


def test_a_settlement_suspect_is_excluded_from_the_pooled_number() -> None:
    """Pooling it would import the artefact into the headline."""
    ledger = _ledger(_many("tackles_assists", 400, 1.0) + _many("rush_yards", 400, -1.0))

    text = render_ledger(
        ledger, NFL, settlement_suspects=frozenset({"tackles_assists"})
    )

    assert "Pooled, excluding settlement suspects: -100.0%" in text


def test_a_thin_market_is_not_enough_evidence_rather_than_a_number() -> None:
    ledger = _ledger(_many("rush_yards", 20, 1.0))

    text = render_ledger(ledger, NFL, minimum_bets=200)

    assert "not enough evidence" in text


def test_an_interval_including_zero_says_no_demonstrated_edge() -> None:
    """In those words, every time."""
    rows = _many("rush_yards", 300, 1.0) + _many("rush_yards", 300, -1.0)
    text = render_ledger(_ledger(rows), NFL, minimum_bets=100)

    assert "no demonstrated edge" in text


def test_voids_are_excluded_from_the_return_and_the_assumption_is_stated() -> None:
    """A void returns the stake. Counting it as a loss would be a different
    strategy, and the assumption is the largest one in the lab."""
    rows = _many("rush_yards", 100, 1.0) + _many("rush_yards", 100, 0.0, "void")
    text = render_ledger(_ledger(rows), NFL, minimum_bets=50)

    assert "100 settled" in text
    assert "100 voided" in text
    assert "largest assumption" in text


def test_the_report_names_that_the_ledger_is_the_only_growing_evidence() -> None:
    text = render_ledger(_ledger(_many("rush_yards", 10, 1.0)), NFL)

    assert "bought population is complete" in text


def test_an_interval_excluding_zero_says_which_direction() -> None:
    """"Interval excludes zero" reads to anyone as good news.

    The NHL lab shipped exactly this into its claims document, where a
    replicated LOSS produced a headline saying a market had survived and
    replicated. The direction is not decoration.
    """
    losing = render_ledger(_ledger(_many("rush_yards", 400, -1.0, "lost")), NFL)
    winning = render_ledger(_ledger(_many("rush_yards", 400, 1.0)), NFL)

    assert "interval excludes zero, **negative**" in losing
    assert "positive" not in losing.split("| `rush_yards` |")[1].split("|\n")[0]
    assert "interval excludes zero, **positive**" in winning


def test_the_family_correction_can_come_from_the_cumulative_tally() -> None:
    """Reading the ledger back every week IS another look at it.

    A report that corrects across its own twelve rows, every week, for a
    season, is correcting across twelve when the true family is hundreds. The
    caller passes the cumulative count from the experiment ledger; without it
    the report silently resets the correction every Tuesday.
    """
    ledger = _ledger(_many("rush_yards", 400, 1.0))

    narrow = render_ledger(ledger, NFL, families=1)
    wide = render_ledger(ledger, NFL, families=200)

    # The same data, corrected across two very different families, cannot
    # produce the same interval.
    assert narrow != wide


def test_the_default_family_is_the_markets_reported() -> None:
    """Backwards compatible: a caller that does not know about the tally still
    gets the old behaviour rather than no correction at all."""
    ledger = _ledger(_many("rush_yards", 400, 1.0))

    assert render_ledger(ledger, NFL) == render_ledger(ledger, NFL, families=1)


def test_the_pooled_line_gets_the_same_family_correction_as_every_row_above_it() -> None:
    """It was judged on its RAW interval while every market row was judged on a
    corrected one — and the paragraph below then told the reader the numbers
    were family-corrected. At the live factor that is an interval 1.69x too
    narrow on the single most quotable sentence in the file.
    """
    ledger = _ledger(_many("rush_yards", 600, 1.0))

    narrow = render_ledger(ledger, NFL, families=1)
    wide = render_ledger(ledger, NFL, families=200)

    assert "family-corrected interval" in wide
    # A correction across 200 families cannot leave the pooled interval where a
    # correction across one left it.
    assert narrow != wide


def test_a_pooled_result_stops_excluding_zero_as_the_family_grows() -> None:
    """The exact shape the audit described: a pooled line that reads
    "interval excludes zero" on its raw interval and "no demonstrated edge"
    once the family it was actually searched over is accounted for.

    Asserted as a property rather than at a hand-picked family size, so the
    test does not quietly depend on today's correction arithmetic.
    """
    # Games that win and lose whole, so between-game variance is real.
    rows = []
    for game in range(200):
        won = game < 117
        rows += [
            {
                "market": "rush_yards",
                "outcome": "won" if won else "lost",
                "profit_units": 1.0 if won else -1.0,
                "snapshot_date": "2026-09-13",
                "home_team": f"H{game}",
                "away_team": f"A{game}",
            }
            for _ in range(4)
        ]
    ledger = _ledger(rows)

    def pooled_line(families: int) -> str:
        text = render_ledger(ledger, NFL, families=families)
        return next(l for l in text.splitlines() if l.startswith("**Pooled"))

    assert "excludes zero" in pooled_line(1)
    # Somewhere between one family and a thousand, the claim has to give way.
    assert "no demonstrated edge" in pooled_line(1000)
