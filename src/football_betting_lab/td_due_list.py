"""The NFL touchdown Due List: the NHL lab's Due List, ported to anytime scorers.

Cooper asked on 2026-10-11 for the logic of the NHL Due List applied to NFL
touchdown scorers, with the parameters left to Claude. This module is the port.
The machinery is the NHL lab's (`nhl_betting_lab.drought_rule`, read, not
imported: the labs never import each other); the parameters and every number
are this league's own.

## The rule

A player who scored **8 or more touchdowns last regular season** (scored, not
thrown: rushing, receiving, return and defensive, exactly what `anytime_td`
settles on) is listed for the anytime-scorer over 0.5 when his current drought
reaches the bar for his band:

    12+ touchdowns last season -> 3 straight games without one
    10-11                      -> 4
    8-9                        -> 5

The drought is the regular-season games he appeared in without scoring,
carried across the season boundary, entering tonight, which is how the NHL
lab counts it. "Appeared in" means he has a row in nflverse's weekly player
stats; a game he dressed for and recorded nothing in has no row and does not
extend the drought, so a drought here can only ever be understated.

## Why these numbers

The NHL tiers put each band's bar near the drought a typical player in it goes
on about one time in sixteen. The same rule is applied here, from the prior-
season hit rates measured over 2015-2025 (weekly player stats, regular season):

    band    players  typical share of games with a TD  bar  (1 - p)^bar
    12+       125              0.60-0.70                3      ~0.06
    10-11     100              ~0.51                    4      ~0.06
    8-9       218              ~0.46                    5      ~0.05

8 touchdowns is the floor because it leaves about forty qualifiers a season,
roughly the NHL list's 25-goal pool, and below it the bars stretch past six
games, a third of a season.

The bars were set from those hit rates before any listed row was compared
with an outcome or a price, so the backtest below is the one look, not the
best of several.

## What it is

A LIST beside the card, like the NHL one: no units, no edge, nothing in the
card's selections, the frozen snapshot, the forward ledger or the selection
fingerprint. Each row carries the best posted anytime price and its book, or
"not posted", never filled in. The backtest (`scripts/run_td_due_list_backtest.py`)
says what being due is worth, and the card prints that headline beside it.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from football_betting_lab.leagues import League
from football_betting_lab.rosters import normalise_name


#: Last regular season's scored touchdowns needed to be considered at all.
THRESHOLD = 8
#: (floor of last season's touchdowns, drought that lists him), best band first.
TIERS: tuple[tuple[int, int], ...] = ((12, 3), (10, 4), (8, 5))
MARKET = "anytime_td"
LINE = 0.5
SECTION_TITLE = "TD Due List"
BACKTEST_STEM = "td_due_list_backtest"

assert TIERS[-1][0] == THRESHOLD, "the lowest tier is the base qualifier"

_TOUCHDOWN_COLUMN = "anytime_td_count"


def tier_bar(prior_tds: Any) -> int | None:
    """The drought that lists a player on last season's touchdowns; None below the qualifier."""
    if prior_tds is None or pd.isna(prior_tds):
        return None
    for floor, bar in TIERS:
        if prior_tds >= floor:
            return bar
    return None


def band_label(prior_tds: Any) -> str | None:
    """The band last season's total falls in ("12+", "10-11", "8-9"); None below the qualifier."""
    if prior_tds is None or pd.isna(prior_tds):
        return None
    for i, (floor, _) in enumerate(TIERS):
        if prior_tds >= floor:
            return f"{floor}+" if i == 0 else f"{floor}-{TIERS[i - 1][0] - 1}"
    return None


def one_in(hit_rate: Any, drought: int) -> int | None:
    """N in "1 in N for him": round(1 / (1 - p)^drought); None when it cannot be said."""
    if hit_rate is None or pd.isna(hit_rate) or drought < 1:
        return None
    miss = 1.0 - float(hit_rate)
    if miss <= 0.0:
        return None
    rarity = miss**drought
    if rarity <= 0.0:
        return None
    return int(round(1.0 / rarity))


def prepare_logs(logs: pd.DataFrame) -> pd.DataFrame:
    """Every logged regular-season game with the drought entering it and last season's record.

    Columns added: `scored` (one or more touchdowns), `drought` (games without
    one entering this game, carried across seasons), `prior_tds`, `prior_gp`,
    `prior_rate` (last season's games with a touchdown over games logged),
    `bar` and `listed`. The card and the backtest both read this, so they
    cannot disagree about who was due.
    """
    needed = {"season", "week", "game_id", "player_id", _TOUCHDOWN_COLUMN}
    missing = needed - set(logs.columns)
    if missing:
        raise ValueError(f"player logs lack {sorted(missing)}")
    frame = logs.dropna(subset=["player_id"]).copy()
    frame["season"] = pd.to_numeric(frame["season"], errors="coerce")
    frame["week"] = pd.to_numeric(frame["week"], errors="coerce")
    frame = frame.dropna(subset=["season", "week"])
    frame["season"] = frame["season"].astype(int)
    frame["week"] = frame["week"].astype(int)
    tds = pd.to_numeric(frame[_TOUCHDOWN_COLUMN], errors="coerce")
    if tds.isna().any():
        # A missing count is not a game without a touchdown. Counting it as one
        # would extend a drought on a row that says nothing.
        frame = frame[tds.notna()].copy()
        tds = tds[tds.notna()]
    frame["tds"] = tds.astype(float)
    frame["scored"] = frame["tds"] > 0
    frame = frame.sort_values(["player_id", "season", "week"], kind="mergesort")
    frame = frame.drop_duplicates(subset=["player_id", "game_id"], keep="first")

    # Games without a touchdown entering each row: the running count of misses
    # since his last scoring game, shifted one so tonight is not counted.
    misses = (~frame["scored"]).astype(int)
    block = frame["scored"].astype(int).groupby(frame["player_id"]).cumsum()
    run = misses.groupby([frame["player_id"], block]).cumsum()
    frame["drought"] = (
        run.groupby(frame["player_id"]).shift(1).fillna(0).astype(int)
    )

    season_totals = (
        frame.groupby(["player_id", "season"])
        .agg(prior_tds=("tds", "sum"), prior_gp=("scored", "size"), prior_hits=("scored", "sum"))
        .reset_index()
    )
    season_totals["season"] = season_totals["season"] + 1
    frame = frame.merge(season_totals, on=["player_id", "season"], how="left")
    frame["prior_rate"] = frame["prior_hits"] / frame["prior_gp"]
    frame["bar"] = frame["prior_tds"].map(tier_bar)
    frame["listed"] = frame["bar"].notna() & (frame["drought"] >= frame["bar"].fillna(10**9))
    return frame.sort_values(["season", "week", "player_id"]).reset_index(drop=True)


def entering(logs: pd.DataFrame, *, season: int, week: int) -> pd.DataFrame:
    """Each qualifier's state entering `season` week `week`, before it is played.

    The same `prepare_logs`, asked about one more game: a sentinel row per
    qualifier at (season, week) with no touchdowns, so the drought it reports
    is the one entering that game and last season's record is read for
    `season`. Rows already logged at or after that week are dropped first, so
    a rebuilt table cannot leak the game into its own drought.
    """
    frame = logs.copy()
    frame["season"] = pd.to_numeric(frame["season"], errors="coerce")
    frame["week"] = pd.to_numeric(frame["week"], errors="coerce")
    before = frame[
        (frame["season"] < season) | ((frame["season"] == season) & (frame["week"] < week))
    ]
    last = before[before["season"] == season - 1]
    totals = pd.to_numeric(last[_TOUCHDOWN_COLUMN], errors="coerce").groupby(
        last["player_id"]
    ).sum()
    qualifiers = totals[totals >= THRESHOLD].index
    if not len(qualifiers):
        return pd.DataFrame()
    latest = (
        before.sort_values(["season", "week"]).groupby("player_id").tail(1).set_index("player_id")
    )
    sentinel = pd.DataFrame(
        {
            "season": season,
            "week": week,
            "game_id": [f"__tonight__{pid}" for pid in qualifiers],
            "player_id": list(qualifiers),
            "player_name": [latest.loc[pid].get("player_name", "") for pid in qualifiers],
            _TOUCHDOWN_COLUMN: 0,
        }
    )
    prepared = prepare_logs(pd.concat([before, sentinel], ignore_index=True))
    out = prepared[prepared["game_id"].astype(str).str.startswith("__tonight__")]
    return out.reset_index(drop=True)


@dataclass(frozen=True)
class DueRow:
    player: str
    player_id: str
    team: str
    opponent: str
    kickoff: str
    prior_tds: int
    prior_rate: float
    band: str
    bar: int
    drought: int
    one_in: int | None
    price: float | None
    book: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "player": self.player,
            "player_id": self.player_id,
            "team": self.team,
            "opponent": self.opponent,
            "kickoff": self.kickoff,
            "market": MARKET,
            "line": LINE,
            "prior_tds": self.prior_tds,
            "prior_rate": round(self.prior_rate, 4),
            "band": self.band,
            "bar": self.bar,
            "drought": self.drought,
            "one_in": self.one_in,
            "price": self.price,
            "book": self.book,
        }


def best_prices(prices: pd.DataFrame) -> dict[str, tuple[float, str]]:
    """normalised player name -> (best anytime over price, its book) from a staged price frame."""
    if prices is None or prices.empty or "market" not in prices.columns:
        return {}
    rows = prices[(prices["market"] == MARKET)]
    if "selection" in rows.columns:
        rows = rows[rows["selection"] == "over"]
    if rows.empty:
        return {}
    rows = rows.assign(
        american_odds=pd.to_numeric(rows["american_odds"], errors="coerce"),
        _name=rows["player"].map(normalise_name),
    ).dropna(subset=["american_odds"])
    out: dict[str, tuple[float, str]] = {}
    for name, group in rows.groupby("_name"):
        best = group.sort_values("american_odds", ascending=False).iloc[0]
        out[str(name)] = (float(best["american_odds"]), str(best.get("book", "") or ""))
    return out


def build_due_list(
    logs: pd.DataFrame,
    *,
    season: int,
    week: int,
    teams: dict[str, str],
    fixtures: list[tuple[str, str, str]],
    prices: pd.DataFrame | None = None,
) -> list[DueRow]:
    """Tonight's listed players.

    `teams` maps player id to his CURRENT club (from the roster, never from his
    last logged game: players move). `fixtures` is (home, away, kickoff) for
    the games being listed, in club abbreviations. A qualifier whose club is
    not playing, or whom the roster does not hold, is not listed.
    """
    state = entering(logs, season=season, week=week)
    if state.empty:
        return []
    opponents: dict[str, tuple[str, str]] = {}
    for home, away, kickoff in fixtures:
        opponents[str(home).upper()] = (str(away).upper(), kickoff)
        opponents[str(away).upper()] = (str(home).upper(), kickoff)
    priced = best_prices(prices) if prices is not None else {}
    rows: list[DueRow] = []
    for record in state[state["listed"]].itertuples():
        team = teams.get(str(record.player_id), "")
        if team not in opponents:
            continue
        opponent, kickoff = opponents[team]
        name = str(record.player_name or "")
        price, book = priced.get(normalise_name(name), (None, ""))
        rows.append(
            DueRow(
                player=name,
                player_id=str(record.player_id),
                team=team,
                opponent=opponent,
                kickoff=kickoff,
                prior_tds=int(record.prior_tds),
                prior_rate=float(record.prior_rate),
                band=band_label(record.prior_tds) or "",
                bar=int(record.bar),
                drought=int(record.drought),
                one_in=one_in(record.prior_rate, int(record.drought)),
                price=price,
                book=book,
            )
        )
    return sorted(rows, key=lambda r: (-(r.one_in or 0), -r.drought, r.player))


def backtest_json_name(league: League) -> str:
    """The backtest's JSON file name, league-prefixed like every output."""
    return league.output_name(BACKTEST_STEM, ".json")


def load_headline(outputs_dir: Path, league: League) -> dict[str, Any] | None:
    """The committed backtest's headline, or None when the file is absent or unreadable."""
    path = Path(outputs_dir) / backtest_json_name(league)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def _price_text(price: float | None, book: str) -> str:
    if price is None or (isinstance(price, float) and math.isnan(price)):
        return "not posted"
    sign = "+" if price > 0 else ""
    return f"{sign}{price:.0f}" + (f" ({book})" if book else "")


def headline_sentence(headline: dict[str, Any] | None) -> str:
    """One line on what being due has been worth, read from the backtest; never invented."""
    if not headline:
        return "No backtest is committed yet, so nothing is said here about what being due is worth."
    parts: list[str] = []
    hits = headline.get("hit_rate")
    if isinstance(hits, dict) and hits.get("listed_n"):
        parts.append(
            f"Since {hits.get('first_season')}, listed players scored in "
            f"{hits['listed_rate']:.1%} of {hits['listed_n']:,} games against "
            f"{hits['others_rate']:.1%} for the same qualifiers when not due "
            f"(n = {hits['others_n']:,})"
        )
    priced = headline.get("priced")
    if isinstance(priced, dict) and priced.get("bets"):
        verdict = (
            "no demonstrated edge"
            if priced["low"] <= 0.0 <= priced["high"]
            else ("a demonstrated loss" if priced["high"] < 0 else "an interval above zero")
        )
        parts.append(
            f"betting every listed over at the best price {priced['seasons']} returned "
            f"{priced['roi']:+.1%} over {priced['bets']:,} bets "
            f"({priced['low']:+.1%} to {priced['high']:+.1%}): {verdict}"
        )
    if not parts:
        return "The committed backtest has no headline, so nothing is said here."
    return "; ".join(parts) + "."


def render_section(rows: list[DueRow], *, headline: dict[str, Any] | None, note: str = "") -> str:
    """The card section. A list beside the card, never a selection."""
    out = [f"## {SECTION_TITLE}", ""]
    out.append(
        f"Anytime touchdown, over {LINE}. Listed: {THRESHOLD}+ touchdowns scored last "
        "regular season, on a drought of "
        + ", ".join(
            f"{bar}+ games ({band_label(floor)})" for floor, bar in TIERS
        )
        + ". Context only: no units, nothing here is a selection or is frozen."
    )
    out.append("")
    out.append(headline_sentence(headline))
    out.append("")
    if note:
        out += [note, ""]
    if not rows:
        out.append("Nobody playing on this slate is due.")
        return "\n".join(out) + "\n"
    out.append("| Player | Team | Opp | Kickoff | Last season | Drought (bar) | 1 in N for him | Best price |")
    out.append("|:--|:--|:--|:--|--:|:--|--:|:--|")
    for row in rows:
        rarity = f"1 in {row.one_in:,}" if row.one_in else "—"
        out.append(
            f"| {row.player} | {row.team} | {row.opponent} | {row.kickoff} | "
            f"{row.prior_tds} TD, {row.prior_rate:.0%} of games | {row.drought} ({row.bar}) | "
            f"{rarity} | {_price_text(row.price, row.book)} |"
        )
    return "\n".join(out) + "\n"


def slate_fixtures(games: pd.DataFrame, *, season: int, slate_date: str) -> tuple[int | None, list[tuple[str, str, str]]]:
    """(week, [(home, away, kickoff)]) for one league date, from the schedule table.

    On a Sunday slate the list is the weekly report Cooper asked for
    (2026-10-11, "every sunday just send a report of everyone who is on the
    list with our weekly NFL card"), so it also takes the rest of that week's
    games after Sunday — Monday night — with the day on the kickoff. The
    week's Thursday game has already been played by then, and its players'
    droughts have moved, so it is never included.
    """
    needed = {"season", "week", "game_date", "home_team", "away_team"}
    if games is None or games.empty or not needed <= set(games.columns):
        return None, []
    in_season = games[pd.to_numeric(games["season"], errors="coerce") == int(season)]
    dates = in_season["game_date"].astype(str).str[:10]
    rows = in_season[dates == slate_date]
    if rows.empty:
        return None, []
    week = int(pd.to_numeric(rows["week"], errors="coerce").max())
    if pd.Timestamp(slate_date).dayofweek == 6:
        rows = in_season[
            (pd.to_numeric(in_season["week"], errors="coerce") == week) & (dates >= slate_date)
        ]
        rows = rows.assign(_date=rows["game_date"].astype(str).str[:10]).sort_values("_date", kind="stable")

    def kickoff(row: Any) -> str:
        time = f"{row.gametime} ET" if isinstance(getattr(row, "gametime", None), str) else ""
        day = str(row.game_date)[:10]
        if day == slate_date:
            return time
        return f"{pd.Timestamp(day):%a} {time}".strip()

    fixtures = [(str(row.home_team), str(row.away_team), kickoff(row)) for row in rows.itertuples()]
    return week, fixtures


def card_section(
    logs: pd.DataFrame,
    games: pd.DataFrame,
    roster_teams: dict[str, str],
    prices: pd.DataFrame | None,
    *,
    season: int,
    slate_date: str,
    outputs_dir: Path,
    league: League,
) -> str:
    """The section the gameday card appends, or an empty string on a day with no NFL games."""
    if logs is None or logs.empty:
        return ""
    week, fixtures = slate_fixtures(games, season=season, slate_date=slate_date)
    if week is None or not fixtures:
        return ""
    rows = build_due_list(
        logs, season=season, week=week, teams=roster_teams, fixtures=fixtures, prices=prices
    )
    return render_section(rows, headline=load_headline(outputs_dir, league))
