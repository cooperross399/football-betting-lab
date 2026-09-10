"""A feature that cannot reproduce itself cannot predict anything.

The screen these tests guard exists because three matchup features were
measured against a closing price before anyone measured them against
themselves, and every one of those nulls was predictable in minutes from free
data. The load-bearing piece is the *ranked* carryover: pooling year pairs
across seasons whose league mean has moved destroys the raw correlation while
every team holds its place, and reading that as "the feature does not persist"
is the exact error this module exists to stop.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from football_betting_lab.reports import reliability as rel


def _frame(rows) -> pd.DataFrame:
    return pd.DataFrame(
        [{"entity": e, "season": s, "week": w, "value": v, "weight": g}
         for e, s, w, v, g in rows]
    )


def _stable(seasons, offsets, entities=32, weeks=16, noise=0.0, seed=0):
    """Entities with a fixed rank, plus a league-wide level shift per season."""
    rng = np.random.default_rng(seed)
    rows = []
    for season, offset in zip(seasons, offsets):
        for index in range(entities):
            base = index / entities + offset
            for week in range(1, weeks + 1):
                rows.append((f"e{index}", season, week,
                             base + rng.normal(0, noise), 1.0))
    return _frame(rows)


def test_a_league_wide_shift_destroys_the_raw_carryover_and_not_the_ranked() -> None:
    """The man-coverage case: league mean 0.286, 0.423, 0.492, 0.318 across four
    seasons. Raw carryover measured +0.017 and ranked +0.435, and only the
    second is about the teams."""
    frame = _stable([2022, 2023, 2024, 2025], [0.0, 3.0, 6.0, 0.5])
    out = rel.measure(frame, "drifting", minimum=8, half_minimum=4)
    assert out.year_over_year is not None and out.year_over_year_ranked is not None
    assert out.year_over_year_ranked > 0.9
    assert out.year_over_year < out.year_over_year_ranked
    assert out.drifts is True


def test_a_feed_with_a_steady_level_shows_no_drift_and_the_columns_agree() -> None:
    frame = _stable([2022, 2023, 2024, 2025], [0.0, 0.0, 0.0, 0.0])
    out = rel.measure(frame, "steady", minimum=8, half_minimum=4)
    assert out.drifts is False
    assert out.year_over_year == pytest.approx(out.year_over_year_ranked, abs=0.05)


def test_the_governing_number_is_the_ranked_one() -> None:
    """A live card holds the prior season and a model's intercept absorbs any
    league-wide level change, so what has to persist is relative position."""
    frame = _stable([2022, 2023, 2024, 2025], [0.0, 3.0, 6.0, 0.5])
    out = rel.measure(frame, "drifting", minimum=8, half_minimum=4)
    assert out.ceiling == out.year_over_year_ranked
    assert out.verdict == "usable"


def test_pure_noise_is_reported_as_too_noisy_to_carry_a_signal() -> None:
    rng = np.random.default_rng(3)
    rows = [
        (f"e{i}", s, w, float(rng.normal()), 1.0)
        for s in (2022, 2023, 2024) for i in range(40) for w in range(1, 17)
    ]
    out = rel.measure(_frame(rows), "noise", minimum=8, half_minimum=4)
    assert abs(out.ceiling) < 0.20
    assert out.verdict == "**too noisy to carry a signal**"


def test_a_season_value_is_weighted_by_its_denominator() -> None:
    """A two-target game must not count as much as a twelve-target one."""
    frame = _frame([("e0", 2024, 1, 10.0, 2.0), ("e0", 2024, 2, 0.0, 18.0)])
    out = rel._aggregate(frame, ["entity", "season"], 0.0)
    assert out["value"].iloc[0] == pytest.approx(1.0)   # not 5.0


def test_an_entity_below_the_minimum_never_reaches_the_correlation() -> None:
    frame = _frame([("e0", 2024, 1, 5.0, 3.0), ("e1", 2024, 1, 5.0, 40.0)])
    assert len(rel._aggregate(frame, ["entity", "season"], 40.0)) == 1


def test_spearman_brown_lifts_a_positive_half_and_is_withheld_from_a_negative() -> None:
    """A negative half-correlation does not become a positive whole one, and
    the formula would happily report that it does."""
    rng = np.random.default_rng(7)
    truth = {f"e{i}": rng.normal() for i in range(60)}
    rows = [
        (name, 2024, w, value + rng.normal(0, 1.0), 1.0)
        for name, value in truth.items() for w in range(1, 17)
    ]
    out = rel.measure(_frame(rows), "signal", minimum=8, half_minimum=4)
    assert out.split_half is not None and out.full_season is not None
    assert out.full_season > out.split_half

    flipped = rel.Reliability("x", 1, -0.4, None, 10, -0.4, 10, -0.4)
    assert flipped.full_season is None


def test_too_few_pairs_reports_nothing_rather_than_a_perfect_correlation() -> None:
    """Two points always correlate perfectly and say nothing at all."""
    value, pairs = rel._correlate(pd.Series([1.0, 2.0]), pd.Series([1.0, 2.0]))
    assert value is None and pairs == 2


def test_a_missing_column_is_refused_rather_than_silently_scored() -> None:
    with pytest.raises(ValueError, match="missing"):
        rel.measure(pd.DataFrame({"entity": ["a"], "season": [2024]}), "bad", minimum=1)


def test_the_table_ranks_by_the_governing_number_and_flags_every_drifter() -> None:
    rows = [
        rel.Reliability("weak one", 10, 0.1, 0.2, 10, 0.10, 10, 0.10),
        rel.Reliability("strong one", 10, 0.8, 0.9, 10, 0.80, 10, 0.80),
        rel.Reliability("drifter", 10, 0.9, 0.95, 10, 0.02, 10, 0.45),
    ]
    table = rel.render(rows)
    assert table.index("strong one") < table.index("drifter") < table.index("weak one")
    assert "⚠︎" in table and "*drifter*" in table


def test_the_pinned_weights_match_the_committed_report() -> None:
    """A board that quotes a reliability weight must quote the one the report
    actually produced. Hand-editing the dict to flatter a layer is exactly the
    move this pin exists to prevent, so the numbers are checked against the
    generated file rather than trusted."""
    import re
    from pathlib import Path

    outputs = Path(__file__).resolve().parents[1] / "data" / "outputs"
    reports = [outputs / "nfl_feature_reliability.md", outputs / "nfl_metric_reliability.md"]
    for report in reports:
        assert report.is_file(), f"{report.name} is committed and must exist"
    text = "\n".join(r.read_text(encoding="utf-8") for r in reports)
    found: dict[str, float] = {}
    for line in text.splitlines():
        if not line.startswith("| ") or "**" not in line:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        name = cells[0].replace(" ⚠︎", "")
        ranked = re.search(r"\*\*([+-][\d.]+)\*\*", line)
        if ranked and name in rel.MEASURED:
            found[name] = float(ranked.group(1))
    missing = set(rel.MEASURED) - set(found)
    assert not missing, f"pinned but absent from the report: {sorted(missing)}"
    for name, pinned in rel.MEASURED.items():
        assert abs(found[name] - pinned) < 5e-4, (
            f"{name}: pinned {pinned:+.3f}, report says {found[name]:+.3f}"
        )
