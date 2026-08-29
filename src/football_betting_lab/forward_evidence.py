"""Freeze what the model said before kickoff, settle it after, accumulate.

The historical backtest re-prices past games with walk-forward fits, which is
honest but reconstructed. This is the stronger thing: **the opinion the live
card actually held, written down before kickoff, settled against the box score
after, and never revised.**

It is also the only priced evidence this lab will have for a while. One NFL
season is 272 games. Historical prices can be bought later — the retention
probe says they exist for every tier-1 market — but **forward evidence cannot
be back-dated.** Every week the pipeline is not freezing opinions is a week of
clean out-of-sample data that is gone permanently, which is why this organ is
built before the models are good.

## Three stages, each idempotent

**Snapshot.** After the card prices a slate, every priced row is written to
`data/archive/priced_snapshots/{league date}.csv` with the model's
probability, the edge against the price as sold, and the gates in force. A
snapshot is evidence and is **never overwritten**: the first opinion of the
day stands, because the card's opinion repriced at a better moment is not the
card's opinion any more.

**Settle.** Once a snapshot day's games are final, each row is settled from
the same tables the historical measurement uses — a second copy of either
would be how the next join bug starts. Settled rows append to the ledger; a
player who never dressed **voids** and returns the stake; a row whose game
never produced a result inside the patience window is recorded
**unsettleable**, counted, never guessed.

**Report.** Per-market accumulating intervals in the house vocabulary, sample
sizes beside every number, and "no demonstrated edge" in those words while it
is true — which it will be for a long time, because the detection arithmetic
says roughly six hundred bets separate a real +8% from zero.

## Intervals are clustered by game, not by bet

A quarterback's passing yards, his receiver's receiving yards, that team's
total and the game total are the same afternoon seen four ways. A naive
binomial interval over correlated bets is **narrower than the truth**, and a
narrow interval is exactly how "no demonstrated edge" turns into a claim. So
the interval is computed on **per-game** returns, which is the unit that is
close to independent.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

from football_betting_lab.leagues import League
from football_betting_lab.markets import MARKETS_BY_KEY
from football_betting_lab.season import clean_text


SNAPSHOT_DIRNAME = "priced_snapshots"
LEDGER_FILENAME = "forward_evidence.csv"

#: Days to keep waiting for a result before recording a row unsettleable. An
#: NFL game postponed by weather is replayed within days; a fortnight without
#: a final box score means the row will never settle against the game it
#: priced.
PATIENCE_DAYS = 14

WON, LOST, PUSH, VOID, UNSETTLEABLE = "won", "lost", "push", "void", "unsettleable"

SNAPSHOT_COLUMNS = (
    "snapshot_date",
    "commence_time",
    "home_team",
    "away_team",
    "market",
    "player",
    "selection",
    "line",
    "american_odds",
    "book",
    "model_probability",
    "edge",
    "gates_in_force",
)

LEDGER_COLUMNS = SNAPSHOT_COLUMNS + ("settled_at", "outcome", "actual", "profit_units")

#: How a market's settled value is found. Team markets read the game row;
#: player markets read the player's log column of the same name.
TEAM_SETTLEMENT = frozenset(
    {
        "moneyline",
        "spread",
        "alternate_spread",
        "total_points",
        "alternate_total_points",
        "team_total",
        "alternate_team_total",
    }
)


def _is_empty(path: Path) -> bool:
    """Whether a snapshot holds no frozen opinions.

    Rows, not existence. A header-only CSV exists and is worth nothing.
    """
    try:
        return len(pd.read_csv(path)) == 0
    except (OSError, UnicodeError, pd.errors.EmptyDataError, pd.errors.ParserError):
        # An unreadable snapshot is not evidence either, and refusing to
        # overwrite it would lock the day on a corrupt file.
        return True


def snapshots_dir(archive_dir: Path) -> Path:
    return Path(archive_dir) / SNAPSHOT_DIRNAME


def american_to_implied(odds: float) -> float:
    odds = float(odds)
    if odds > 0:
        return 100.0 / (odds + 100.0)
    return -odds / (-odds + 100.0)


def profit_on_win(odds: float, stake: float = 1.0) -> float:
    odds = float(odds)
    return stake * (odds / 100.0 if odds > 0 else 100.0 / -odds)


def write_snapshot(
    prices: pd.DataFrame,
    probabilities: Mapping[tuple, float],
    *,
    key_for,
    gates_in_force: str,
    snapshot_date: str,
    archive_dir: Path,
) -> Path | None:
    """Freeze today's priced opinions. Returns None when one already stands.

    `key_for(row, market, selection, line)` is the card's own key function,
    passed in rather than imported by both sides — the probability map and the
    snapshot must agree on the key **by construction**, not by both happening
    to import the same helper.
    """
    directory = snapshots_dir(archive_dir)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{snapshot_date}.csv"
    if target.exists() and not _is_empty(target):
        # The first opinion of the day stands. Two snapshots for one day would
        # let the flattering one be the one that settles.
        return None
    # ...but the first *opinion*, not the first *file*. An empty snapshot is
    # not an opinion. The first live workflow run wrote one on a day with no
    # games, and on a real game day the same thing would happen whenever the
    # early run fetched nothing — a failed provider call, a slate the books
    # had not posted yet — and the day would be locked empty. Every real
    # opinion for that week would then be silently unrecordable, which is the
    # one failure this organ cannot survive, because the evidence cannot be
    # created later.

    rows: list[dict[str, object]] = []
    for row in prices.itertuples():
        market = clean_text(getattr(row, "market", ""))
        selection = clean_text(getattr(row, "selection", "")).lower()
        line_value = getattr(row, "line", None)
        try:
            line = (
                None
                if line_value is None or pd.isna(line_value)
                else float(line_value)
            )
        except (TypeError, ValueError):
            line = None
        probability = probabilities.get(
            key_for(row, market=market, selection=selection, line=line)
        )
        if probability is None:
            continue
        odds = getattr(row, "american_odds", None)
        try:
            implied = american_to_implied(float(odds))
        except (TypeError, ValueError):
            continue
        rows.append(
            {
                "snapshot_date": snapshot_date,
                "commence_time": clean_text(getattr(row, "commence_time", "")),
                "home_team": clean_text(getattr(row, "home_team", "")),
                "away_team": clean_text(getattr(row, "away_team", "")),
                "market": market,
                "player": clean_text(getattr(row, "player", "")),
                "selection": selection,
                "line": line,
                "american_odds": odds,
                "book": clean_text(getattr(row, "book", "")),
                "model_probability": probability,
                "edge": probability - implied,
                "gates_in_force": gates_in_force,
            }
        )
    frame = pd.DataFrame(rows, columns=list(SNAPSHOT_COLUMNS))
    frame.to_csv(target, index=False)
    return target


@dataclass
class SettlementResult:
    settled: pd.DataFrame
    unsettleable: int = 0
    voided: int = 0
    notes: list[str] = field(default_factory=list)


def settle_snapshot(
    snapshot: pd.DataFrame,
    *,
    games: pd.DataFrame,
    logs: pd.DataFrame,
    league: League,
    team_lookup: Mapping[str, str],
    as_of: date,
    settled_at: str | None = None,
) -> SettlementResult:
    """Settle one day's frozen opinions against the results.

    A day is settled **as a unit**: a partially settled day would let the
    early games into the ledger and leave the late ones out, and the late
    window is a systematically different set of fixtures.
    """
    stamp = settled_at or datetime.now(timezone.utc).isoformat()
    rows: list[dict[str, object]] = []
    result = SettlementResult(settled=pd.DataFrame(columns=list(LEDGER_COLUMNS)))
    if snapshot.empty:
        return result

    # Index once rather than filtering per row. Settling a day is a few
    # thousand rows against a hundred thousand player-games, and a scan per
    # row turns a second into an hour — which in production means a settle
    # step that times out and a ledger that silently stops accumulating.
    game_index = {
        (
            str(row.game_date),
            str(row.home_team),
            str(row.away_team),
        ): row
        for row in games.itertuples()
    }
    log_index: dict[tuple[str, str], object] = {}
    for row in logs.itertuples():
        log_index.setdefault(
            (str(row.game_id), str(row.player_name).casefold()), row
        )

    for row in snapshot.itertuples():
        home = team_lookup.get(clean_text(getattr(row, "home_team", "")), "")
        away = team_lookup.get(clean_text(getattr(row, "away_team", "")), "")
        day = clean_text(getattr(row, "snapshot_date", ""))
        game = game_index.get((day, home, away))
        record = dict(row._asdict())
        record.pop("Index", None)
        record["settled_at"] = stamp
        if game is None or pd.isna(getattr(game, "home_score", None)):
            elapsed = _days_since(day, as_of)
            if elapsed is not None and elapsed < PATIENCE_DAYS:
                # Still inside the window. Not settled, and not recorded as
                # anything else either — it will settle on a later run.
                continue
            record.update(
                {"outcome": UNSETTLEABLE, "actual": None, "profit_units": 0.0}
            )
            result.unsettleable += 1
            rows.append(record)
            continue

        outcome, actual = _settle_row(record, game, log_index)
        record["actual"] = actual
        record["outcome"] = outcome
        if outcome == WON:
            record["profit_units"] = profit_on_win(record["american_odds"])
        elif outcome == LOST:
            record["profit_units"] = -1.0
        else:
            # A push and a void both return the stake. They are recorded
            # separately because they mean different things: a push is a
            # result, a void is a bet that never existed.
            record["profit_units"] = 0.0
            if outcome == VOID:
                result.voided += 1
        rows.append(record)

    result.settled = pd.DataFrame(rows, columns=list(LEDGER_COLUMNS))
    return result


def _days_since(day: str, as_of: date) -> int | None:
    try:
        return (as_of - date.fromisoformat(str(day)[:10])).days
    except ValueError:
        return None


def _settle_row(
    record: dict, game: object, log_index: dict[tuple[str, str], object]
) -> tuple[str, float | None]:
    market = str(record.get("market", ""))
    selection = str(record.get("selection", ""))
    line = record.get("line")
    home_score = float(getattr(game, "home_score"))
    away_score = float(getattr(game, "away_score"))

    if market in TEAM_SETTLEMENT:
        return _settle_team(market, selection, line, home_score, away_score)

    definition = MARKETS_BY_KEY.get(market)
    if definition is None or definition.kind != "player":
        return UNSETTLEABLE, None
    player = str(record.get("player", ""))
    entry = log_index.get(
        (str(getattr(game, "game_id", "")), player.casefold())
    )
    if entry is None:
        # He did not dress, or did not appear in the box score. The bet is
        # void and the stake comes back; it is not a loss.
        return VOID, None
    if not hasattr(entry, market):
        return UNSETTLEABLE, None
    actual = float(getattr(entry, market))
    if line is None or (isinstance(line, float) and math.isnan(line)):
        return UNSETTLEABLE, actual
    if actual == float(line):
        return PUSH, actual
    over = actual > float(line)
    if selection == "over":
        return (WON if over else LOST), actual
    if selection == "under":
        return (LOST if over else WON), actual
    return UNSETTLEABLE, actual


def _settle_team(
    market: str, selection: str, line, home_score: float, away_score: float
) -> tuple[str, float | None]:
    if market == "moneyline":
        if home_score == away_score:
            # NFL games do end level, and a two-way moneyline pushes.
            return PUSH, home_score - away_score
        winner = "home" if home_score > away_score else "away"
        return (WON if selection == winner else LOST), home_score - away_score
    if line is None:
        return UNSETTLEABLE, None
    line = float(line)
    if market in {"spread", "alternate_spread"}:
        margin = (home_score - away_score) if selection == "home" else (
            away_score - home_score
        )
        adjusted = margin + line
        if adjusted == 0:
            return PUSH, margin
        return (WON if adjusted > 0 else LOST), margin
    if market in {"total_points", "alternate_total_points"}:
        combined = home_score + away_score
        if combined == line:
            return PUSH, combined
        over = combined > line
        return (WON if (over == (selection == "over")) else LOST), combined
    if market in {"team_total", "alternate_team_total"}:
        which, direction = selection.rsplit("_", 1)
        score = home_score if which == "home" else away_score
        if score == line:
            return PUSH, score
        over = score > line
        return (WON if (over == (direction == "over")) else LOST), score
    return UNSETTLEABLE, None


def append_ledger(settled: pd.DataFrame, ledger_path: Path) -> int:
    """Append settled rows, never duplicating a day already recorded."""
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    if settled.empty:
        return 0
    if ledger_path.is_file():
        existing = pd.read_csv(ledger_path)
        already = set(existing["snapshot_date"].astype(str))
        settled = settled[~settled["snapshot_date"].astype(str).isin(already)]
        if settled.empty:
            return 0
        combined = pd.concat([existing, settled], ignore_index=True)
    else:
        combined = settled
    combined.to_csv(ledger_path, index=False)
    return len(settled)


def interval_by_game(ledger: pd.DataFrame) -> tuple[float, float, float, int, int]:
    """`(roi, low, high, bets, games)` with the interval clustered by game.

    Clustered because the selections inside one game are not independent. A
    naive per-bet interval is narrower than the truth, and a narrow interval
    is how "no demonstrated edge" quietly becomes a claim.
    """
    staked = ledger[ledger["outcome"].isin({WON, LOST, PUSH})]
    if staked.empty:
        return 0.0, 0.0, 0.0, 0, 0
    staked = staked.assign(
        _game=staked["snapshot_date"].astype(str)
        + " "
        + staked["away_team"].astype(str)
        + "@"
        + staked["home_team"].astype(str)
    )
    per_game = staked.groupby("_game").agg(
        profit=("profit_units", "sum"), bets=("profit_units", "size")
    )
    total_bets = int(per_game["bets"].sum())
    games = len(per_game)
    if not total_bets:
        return 0.0, 0.0, 0.0, 0, games
    roi = float(per_game["profit"].sum() / total_bets)
    if games < 2:
        return roi, float("-inf"), float("inf"), total_bets, games
    # Standard error of the mean per-bet return, from between-game variation.
    ratios = per_game["profit"] / per_game["bets"]
    weights = per_game["bets"] / total_bets
    variance = float((weights**2 * ratios.var(ddof=1) / games).sum() * games)
    standard_error = math.sqrt(max(variance, 0.0) / games)
    return roi, roi - 1.96 * standard_error, roi + 1.96 * standard_error, total_bets, games


# -- reading the ledger back ------------------------------------------------


def render_ledger(
    ledger: pd.DataFrame,
    league: League,
    *,
    settlement_suspects: frozenset[str] = frozenset(),
    minimum_bets: int = 200,
) -> str:
    """What the accumulated ledger supports, in the house vocabulary.

    Everything the historical work learned applies here and has to be applied
    *here*, not remembered: a settlement suspect's number is not evidence, an
    interval including zero is "no demonstrated edge" in those words, and a
    family correction across the markets reported is not optional because
    something always looks profitable by chance.

    The ledger is the only evidence that can still grow — the bought
    population is complete — so it is also the only place a mistake in reading
    it compounds for a season.
    """
    from statistics import NormalDist

    lines: list[str] = []
    add = lines.append
    add(f"# Forward evidence — {league.title}")
    add("")
    if ledger.empty:
        add(
            "**The ledger is empty.** No opinion has settled yet. That is an "
            "absence, not a result, and no number is offered in its place."
        )
        return "\n".join(lines) + "\n"

    settled = ledger[ledger["outcome"].isin({WON, LOST, PUSH})]
    voided = ledger[ledger["outcome"] == VOID]
    unsettleable = ledger[ledger["outcome"] == UNSETTLEABLE]
    days = sorted(set(ledger["snapshot_date"].astype(str)))

    add(
        f"**{len(ledger):,} frozen opinion(s) across {len(days)} day(s)**, "
        f"{days[0]} to {days[-1]}. {len(settled):,} settled, "
        f"{len(voided):,} voided (stake returned), "
        f"{len(unsettleable):,} unsettleable."
    )
    add("")
    add(
        "Every opinion here was frozen **before kickoff and never repriced**. "
        "It is the only evidence this lab can still gather: the bought "
        "population is complete, so nothing else grows."
    )
    add("")

    markets = sorted(set(settled["market"].astype(str)))
    families = max(len(markets), 1)
    factor = NormalDist().inv_cdf(1 - (0.05 / families) / 2) / 1.96

    add("| Market | Bets | Games | ROI | 95% interval | Family-corrected | Reading |")
    add("|:-------|-----:|------:|----:|:-------------|:-----------------|:--------|")
    for market in markets:
        rows = settled[settled["market"].astype(str) == market]
        roi, low, high, bets, games = interval_by_game(rows)
        half = (high - low) / 2 if math.isfinite(high - low) else float("inf")
        clow, chigh = roi - half * factor, roi + half * factor
        if market in settlement_suspects:
            reading = (
                "**not evidence** — this market is a settlement suspect; its "
                "return measures a disagreement between sources, not an edge"
            )
        elif bets < minimum_bets:
            reading = f"**not enough evidence** — {bets} bets, below {minimum_bets}"
        elif clow <= 0.0 <= chigh:
            reading = "**no demonstrated edge**"
        else:
            reading = "interval excludes zero"
        add(
            f"| `{market}` | {bets:,} | {games:,} | {roi:+.1%} | "
            f"{low:+.1%} to {high:+.1%} | {clow:+.1%} to {chigh:+.1%} | "
            f"{reading} |"
        )

    pooled_roi, pooled_low, pooled_high, pooled_bets, pooled_games = interval_by_game(
        settled[~settled["market"].astype(str).isin(settlement_suspects)]
    )
    add("")
    add(
        f"**Pooled, excluding settlement suspects: {pooled_roi:+.1%} over "
        f"{pooled_bets:,} bets across {pooled_games:,} games**, interval "
        f"{pooled_low:+.1%} to {pooled_high:+.1%}."
    )
    if settlement_suspects:
        add("")
        add(
            "Excluded as settlement suspects: "
            + ", ".join(f"`{m}`" for m in sorted(settlement_suspects))
            + ". A market settled on a different quantity from the one priced "
            "produces a constant offset, which replicates perfectly and looks "
            "exactly like an edge — `tackles_assists` returned +16% across "
            "three bought seasons on that basis alone."
        )
    add("")
    add(
        "Intervals are clustered by game because selections inside one game "
        f"are not independent, and family-corrected across the {families} "
        "market(s) reported. Voids are excluded from the return rather than "
        "counted as losses; that assumes a book returns the stake on a "
        "did-not-play, which is the single largest assumption in this lab."
    )
    return "\n".join(lines) + "\n"
