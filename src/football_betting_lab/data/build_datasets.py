"""Turn the cached nflverse feeds into the two tables everything else reads.

`team_games.csv` and `player_game_logs.csv` are **derived data**. Every raw
feed is cached, and these rebuild from the cache, so a defect found in this
module is fixed by re-running it rather than by re-fetching anything.

## The columns are settlement columns, and they are named for what they are

The NHL lab has a standing rule that came from a real bug: there is no
`power_play_points` column holding a count of goals, because naming a goals
count "points" is a lie the model inherits and every downstream report
repeats. The same rule applies here and bites in one specific place.

**`anytime_td` is not `passing_tds`.** A quarterback who throws four
touchdowns has scored none. Anytime-touchdown settles on touchdowns a player
**scored** — rushing, receiving, return and defensive — and reading the
passing column would credit every scoring drive to the quarterback and price
every quarterback as the most likely scorer on the field.

**`tackles_assists` is all three defensive columns summed**
(`def_tackles_solo + def_tackles_with_assist + def_tackle_assists`).

An earlier version summed only the first and third, reasoning that
`def_tackles_with_assist` "counts tackles *made with* an assister and would
double-count against the solo column". That reasoning was wrong, and it was
wrong in the direction that manufactured this lab's longest-running false
finding. `def_tackles_solo` counts tackles made **alone**;
`def_tackles_with_assist` counts tackles the player **made** while someone
else assisted. They are disjoint, and the official box score's *solo* figure
is their sum.

Verified against a published box score rather than argued:

    Zack Baun, 2024, 16 games
      def_tackles_solo                                    82
      def_tackles_with_assist                             11
      def_tackle_assists                                  58
      solo + with_assist            = 93   official solo      93
      solo + with_assist + assists  = 151  official combined  151
      solo + assists (the old sum)  = 140  -- 11 short

League-wide the old sum gave **123.6 combined tackles a game against the
correct 133.0**, a 7.1% undercount, and on the featured prop it put the mean
outcome **0.424 below the mean line**. The books were pricing the median of
the correct quantity to within **0.017 tackles** the whole time.

## Yardage can be negative, and the maximum can exceed the total

A reception behind the line of scrimmage loses yards. So a player's longest
catch can be **larger** than his total receiving yards — AJ Dillon caught
passes for 35 and -10 in 2023 week 14, giving a total of 25 and a longest of
35, and there are 262 such cases in four seasons.

This is written down because the obvious sanity check ("a maximum cannot
exceed its sum") is false here, looks like a join bug, and would be "fixed"
by clamping — which would invent data. The invariant that does hold is
asserted instead: with exactly one play there is nothing to cancel, so the
maximum must equal the total.

## The two sources disagree, rarely, and it is measured rather than assumed

Totals come from the weekly stats; maxima come from play-by-play. They are
independent settlement paths, and on a small number of games they disagree.

Measured over 2022-2025, on games with exactly one play of that kind — where
the maximum and the total must otherwise be identical:

| Market family | Single-play games | Disagreements |
|:--------------|------------------:|--------------:|
| receptions | 4,857 | 10 (0.21%) |
| rushes | 2,169 | 0 |
| completions | 140 | 0 |

The receiving cases are laterals and gamebook revisions — Christian Kirk's
one catch in 2022 week 5 is five yards in play-by-play and eleven in the
weekly stats. Both sources are internally consistent; they are describing the
same play with different conventions.

This matters because it is a real, if rare, way a card can be inconsistent
with itself: a one-catch game could settle "longest reception under 10" from
play-by-play while "receiving yards over 10.5" settles from the weekly stats.
It is recorded here, bounded by a test, and **not silently reconciled** —
picking a winner between two sources that both describe the game correctly
would be a fabrication dressed as a fix.

## Why play-by-play is read at all

Only for what a weekly aggregate cannot hold: the **maximum** of a per-play
quantity. Longest completion, longest rush and longest reception are maxima,
not sums, and their distribution is an extreme-value one. Everything else in
these tables comes from the weekly stats, which is smaller, faster, and
already carries the league's own corrections.

## The shrink guard

An accumulated table that suddenly loses half its rows is a bug, not a
season. `build` refuses to shrink either table by more than half unless told
to, each file guarded on its own and on rows rather than existence — because
a feed that fetched empty produces a file that exists and a table that is
quietly wrong.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from football_betting_lab.data import nflverse
from football_betting_lab.leagues import League
from football_betting_lab.season import game_date


TEAM_GAMES_FILENAME = "team_games.csv"
PLAYER_LOGS_FILENAME = "player_game_logs.csv"
PLAY_YARDAGE_FILENAME = "play_yardage.json"
HALF_SCORES_FILENAME = "half_scores.csv"

#: A rebuild that loses more than this fraction of an existing table is
#: refused. Rows, not existence: an empty fetch still produces a file.
MAX_SHRINK = 0.5

#: Play-by-play columns actually read. Named explicitly because the file is
#: 400 columns wide and reading all of them costs a hundred times the memory
#: for nothing.
PBP_COLUMNS = (
    "game_id",
    "play_id",
    "season_type",
    "qtr",
    "posteam",
    "home_team",
    "away_team",
    "total_home_score",
    "total_away_score",
    "complete_pass",
    "touchdown",
    "td_player_id",
    "passer_player_id",
    "passing_yards",
    "rusher_player_id",
    "rushing_yards",
    "receiver_player_id",
    "receiving_yards",
)


@dataclass
class BuildReport:
    """What a rebuild produced, and what it refused to do."""

    team_games: int = 0
    player_logs: int = 0
    seasons: tuple[int, ...] = ()
    refused: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.refused

    def summary_line(self) -> str:
        line = (
            f"{self.team_games:,} team-games and {self.player_logs:,} "
            f"player-games across {len(self.seasons)} season(s)"
        )
        if self.refused:
            line += f"; {len(self.refused)} table(s) REFUSED"
        return line + "."


def _guard_shrink(
    name: str, existing: Path, rows: int, report: BuildReport, *, allow_shrink: bool
) -> bool:
    """Refuse a rebuild that loses most of a table. Returns True to write."""
    if allow_shrink or not existing.is_file():
        return True
    try:
        before = sum(1 for _ in existing.open(encoding="utf-8")) - 1
    except OSError:
        return True
    if before > 0 and rows < before * MAX_SHRINK:
        report.refused.append(
            f"{name} would fall from {before:,} rows to {rows:,}. That is a "
            "bug, not a season. Nothing was written; pass --allow-shrink to "
            "override deliberately."
        )
        return False
    return True


def build_team_games(league: League, raw_dir: Path, seasons: tuple[int, ...]) -> pd.DataFrame:
    """One row per game: what it was, what happened, and what it closed at."""
    path = nflverse.feed_path(
        nflverse.FEEDS_BY_NAME["schedules"], league, raw_dir, None
    )
    frame = pd.read_csv(path, low_memory=False)
    frame = frame[frame["season"].isin(seasons) & (frame["game_type"] == "REG")].copy()

    frame["game_date"] = frame["gameday"].astype(str).str[:10]
    frame["neutral_site"] = frame["location"].astype(str).str.lower().eq("neutral")
    # `roof` is blank until a retractable venue's roof state is known, and it
    # is populated and WRONG for some international fixtures — three 2026
    # open-air games are labelled `dome`. So the gate never keys on it alone:
    # a neutral-site fixture is roof-unknown regardless of what it says.
    roof = frame["roof"].astype(str).str.strip().str.lower()
    frame["roof_stated"] = roof
    frame["roof_known"] = roof.isin({"dome", "outdoors", "closed", "open"}) & (
        ~frame["neutral_site"]
    )
    columns = [
        "game_id",
        "season",
        "week",
        "game_date",
        "weekday",
        "gametime",
        "home_team",
        "away_team",
        "home_score",
        "away_score",
        "result",
        "total",
        "overtime",
        "home_rest",
        "away_rest",
        "div_game",
        "neutral_site",
        "roof_stated",
        "roof_known",
        "surface",
        "temp",
        "wind",
        "stadium",
        "spread_line",
        "home_spread_odds",
        "away_spread_odds",
        "total_line",
        "over_odds",
        "under_odds",
        "home_moneyline",
        "away_moneyline",
    ]
    present = [column for column in columns if column in frame.columns]
    return frame[present].sort_values(["game_date", "game_id"]).reset_index(drop=True)


def _per_play_maxima(league: League, raw_dir: Path, season: int) -> pd.DataFrame:
    """Longest completion, rush and reception per player per game.

    These are the only quantities play-by-play is read for. A maximum cannot
    be recovered from a weekly total, and the three "longest" markets settle
    on nothing else.
    """
    path = nflverse.feed_path(nflverse.FEEDS_BY_NAME["pbp"], league, raw_dir, season)
    if not path.is_file():
        return pd.DataFrame(
            columns=[
                "game_id",
                "player_id",
                "longest_completion",
                "longest_rush",
                "longest_reception",
            ]
        )
    plays = pd.read_csv(
        path, compression="gzip", usecols=list(PBP_COLUMNS), low_memory=False
    )
    plays = plays[plays["season_type"] == "REG"]

    pieces: list[pd.DataFrame] = []
    for player_column, yards_column, output, mask in (
        ("passer_player_id", "passing_yards", "longest_completion", "complete_pass"),
        ("rusher_player_id", "rushing_yards", "longest_rush", None),
        ("receiver_player_id", "receiving_yards", "longest_reception", "complete_pass"),
    ):
        subset = plays
        if mask is not None:
            subset = subset[subset[mask] == 1]
        subset = subset[["game_id", player_column, yards_column]].dropna(
            subset=[player_column, yards_column]
        )
        if subset.empty:
            continue
        grouped = (
            subset.groupby(["game_id", player_column])[yards_column]
            .max()
            .reset_index()
            .rename(columns={player_column: "player_id", yards_column: output})
        )
        pieces.append(grouped)

    if not pieces:
        return pd.DataFrame(
            columns=[
                "game_id",
                "player_id",
                "longest_completion",
                "longest_rush",
                "longest_reception",
            ]
        )
    merged = pieces[0]
    for piece in pieces[1:]:
        merged = merged.merge(piece, on=["game_id", "player_id"], how="outer")
    return merged


def build_player_logs(
    league: League, raw_dir: Path, seasons: tuple[int, ...], report: BuildReport
) -> pd.DataFrame:
    """One row per player per game, carrying every tier-1 settlement column."""
    frames: list[pd.DataFrame] = []
    for season in seasons:
        path = nflverse.feed_path(
            nflverse.FEEDS_BY_NAME["player_stats"], league, raw_dir, season
        )
        if not path.is_file():
            # Say what is known, not what is guessed. "Not cached" and "not
            # published" are different facts, and the first draft of this
            # message asserted the second for 2020 and 2021 — seasons that
            # were played in full and simply had not been fetched. A report
            # that explains an absence it has not checked is worse than one
            # that says it does not know.
            report.notes.append(
                f"No weekly player stats cached for {season}. Fetch it with "
                f"`scripts/fetch_football_data.py --seasons {season}`, or, if "
                "the season has not been played yet, this is an absence "
                "rather than a fault."
            )
            continue
        stats = pd.read_csv(path, low_memory=False)
        stats = stats[stats["season_type"] == "REG"].copy()
        maxima = _per_play_maxima(league, raw_dir, season)
        merged = stats.merge(
            maxima, left_on=["game_id", "player_id"], right_on=["game_id", "player_id"],
            how="left",
        )
        frames.append(merged)

    if not frames:
        return pd.DataFrame()
    logs = pd.concat(frames, ignore_index=True)

    def column(name: str) -> pd.Series:
        if name in logs.columns:
            return pd.to_numeric(logs[name], errors="coerce").fillna(0)
        return pd.Series(0, index=logs.index, dtype="float64")

    out = pd.DataFrame(
        {
            "season": logs["season"],
            "week": logs["week"],
            "game_id": logs["game_id"],
            "player_id": logs["player_id"],
            "player_name": logs["player_display_name"],
            "position": logs.get("position", ""),
            "team": logs["team"],
            "opponent": logs["opponent_team"],
            # Passing.
            "pass_completions": column("completions"),
            "pass_attempts": column("attempts"),
            "pass_yards": column("passing_yards"),
            "pass_tds": column("passing_tds"),
            "pass_interceptions": column("passing_interceptions"),
            "pass_longest_completion": column("longest_completion"),
            # Rushing.
            "rush_attempts": column("carries"),
            "rush_yards": column("rushing_yards"),
            "rush_tds": column("rushing_tds"),
            "rush_longest": column("longest_rush"),
            # Receiving.
            "receptions": column("receptions"),
            "targets": column("targets"),
            "reception_yards": column("receiving_yards"),
            "reception_tds": column("receiving_tds"),
            "reception_longest": column("longest_reception"),
            "target_share": column("target_share"),
            # Kicking. A field goal is three points and an extra point is one;
            # there is no other arithmetic in this market.
            "field_goals": column("fg_made"),
            "pats": column("pat_made"),
            "kicking_points": 3 * column("fg_made") + column("pat_made"),
            # Defence. All three columns are disjoint and all three are part
            # of a combined tackle. `def_tackles_solo` is tackles made alone;
            # `def_tackles_with_assist` is tackles the player MADE while
            # someone else assisted; `def_tackle_assists` is assists he gave
            # on someone else's tackle. The official box score's *solo* figure
            # is the first two summed, and its *combined* figure is all three.
            # Dropping the middle one undercounted every defensive line in
            # this repository by about 7% and produced a +12% "edge" that was
            # the undercount and nothing else.
            "solo_tackles": (
                column("def_tackles_solo") + column("def_tackles_with_assist")
            ),
            "tackle_assists": column("def_tackle_assists"),
            "tackles_assists": (
                column("def_tackles_solo")
                + column("def_tackles_with_assist")
                + column("def_tackle_assists")
            ),
            "sacks": column("def_sacks"),
            "defensive_interceptions": column("def_interceptions"),
        }
    )
    # Touchdowns SCORED, never thrown. A quarterback with four passing
    # touchdowns has scored none, and settling anytime-scorer on the passing
    # column would make every quarterback the likeliest scorer on the field.
    out["anytime_td_count"] = (
        column("rushing_tds")
        + column("receiving_tds")
        + column("special_teams_tds")
        + column("def_tds")
    )
    out["anytime_td"] = (out["anytime_td_count"] > 0).astype(int)
    return out.sort_values(["season", "week", "game_id", "player_id"]).reset_index(
        drop=True
    )


def build_half_scores(
    league: League, raw_dir: Path, seasons: tuple[int, ...]
) -> pd.DataFrame:
    """Each game's score at half time, from play-by-play.

    The half and quarter markets are wired and settleable and have had no
    model, so every one of their rows lands in `no_opinion`. This is the table
    a within-game model needs, and it is the only thing play-by-play can
    supply that the weekly aggregates cannot.

    Taken from the running score on the **last play of the second quarter**
    rather than by summing scoring plays. The running totals are the league's
    own arithmetic; re-deriving them from play descriptions would be a second
    copy of a sum that already exists, and two copies of a sum is how they
    start disagreeing.
    """
    frames: list[pd.DataFrame] = []
    for season in seasons:
        path = nflverse.feed_path(nflverse.FEEDS_BY_NAME["pbp"], league, raw_dir, season)
        if not path.is_file():
            continue
        plays = pd.read_csv(
            path, compression="gzip", usecols=list(PBP_COLUMNS), low_memory=False
        )
        plays = plays[(plays["season_type"] == "REG") & (plays["qtr"] <= 2)]
        if plays.empty:
            continue
        last = plays.sort_values("play_id").groupby("game_id").tail(1)
        frames.append(
            pd.DataFrame(
                {
                    "game_id": last["game_id"],
                    "season": season,
                    "home_h1": pd.to_numeric(
                        last["total_home_score"], errors="coerce"
                    ),
                    "away_h1": pd.to_numeric(
                        last["total_away_score"], errors="coerce"
                    ),
                }
            )
        )
    if not frames:
        return pd.DataFrame(columns=["game_id", "season", "home_h1", "away_h1"])
    return pd.concat(frames, ignore_index=True).dropna()


def build_play_yardage(
    league: League, raw_dir: Path, seasons: tuple[int, ...]
) -> dict[str, dict[str, float]]:
    """The empirical distribution of yards on a single play, by kind.

    This is the shape a compound yardage model needs and a per-game total
    cannot supply. Yards are opportunities x yards-per-opportunity, so pricing
    a yardage market means drawing a count and then that many per-play
    outcomes — which also yields the **longest** play for free, and yields it
    consistently with the total rather than from a second model that could
    disagree with the first.

    Kept league-wide rather than per player. A single receiver has a few dozen
    catches a season, which is not enough to fit a tail; the league shape is,
    and a player's own yards-per-reception moves the mean by tilting it. That
    is the same device the team model uses on scores and for the same reason:
    the shape is what the data is good at, the mean is what a fit is good at.
    """
    # Counted PER SEASON, so a backtest can pool only the seasons before the
    # one it is pricing. Pooling every season into one distribution and
    # loading it outside the per-week loop was a walk-forward violation that
    # only the compound markets consumed — the count models fit walk-forward
    # through `before` — so it could only ever flatter the family that looked
    # good. It survived the cross-season settlement fix and had to be found
    # separately.
    by_season: dict[int, dict[str, Counter]] = {}
    for season in seasons:
        counts: dict[str, Counter] = {
            "completion": Counter(),
            "rush": Counter(),
            "reception": Counter(),
        }
        path = nflverse.feed_path(nflverse.FEEDS_BY_NAME["pbp"], league, raw_dir, season)
        if not path.is_file():
            continue
        plays = pd.read_csv(
            path, compression="gzip", usecols=list(PBP_COLUMNS), low_memory=False
        )
        plays = plays[plays["season_type"] == "REG"]
        completed = plays[plays["complete_pass"] == 1]
        for kind, frame, column in (
            ("completion", completed, "passing_yards"),
            ("rush", plays, "rushing_yards"),
            ("reception", completed, "receiving_yards"),
        ):
            values = pd.to_numeric(frame[column], errors="coerce").dropna()
            counts[kind].update(int(value) for value in values)
        by_season[int(season)] = counts

    distributions: dict[str, dict[str, dict[str, float]]] = {}
    for season, counts in by_season.items():
        per_season: dict[str, dict[str, float]] = {}
        for kind, counter in counts.items():
            total = sum(counter.values())
            if not total:
                continue
            per_season[kind] = {
                str(yards): count / total
                for yards, count in sorted(counter.items())
            }
        if per_season:
            distributions[str(season)] = per_season
    return distributions


def build(
    league: League,
    *,
    raw_dir: Path,
    processed_dir: Path,
    seasons: tuple[int, ...],
    allow_shrink: bool = False,
) -> BuildReport:
    report = BuildReport(seasons=tuple(sorted(seasons)))
    processed_dir = Path(processed_dir)
    processed_dir.mkdir(parents=True, exist_ok=True)

    games = build_team_games(league, raw_dir, report.seasons)
    report.team_games = len(games)
    games_path = processed_dir / TEAM_GAMES_FILENAME
    if _guard_shrink(
        TEAM_GAMES_FILENAME, games_path, len(games), report, allow_shrink=allow_shrink
    ):
        games.to_csv(games_path, index=False)

    yardage = build_play_yardage(league, raw_dir, report.seasons)
    if yardage:
        (processed_dir / PLAY_YARDAGE_FILENAME).write_text(
            json.dumps(yardage, indent=1) + "\n", encoding="utf-8"
        )
        report.notes.append(
            "Per-play yardage distributions: "
            + ", ".join(f"{kind} ({len(pmf)} values)" for kind, pmf in yardage.items())
        )

    halves = build_half_scores(league, raw_dir, report.seasons)
    if not halves.empty:
        halves.to_csv(processed_dir / HALF_SCORES_FILENAME, index=False)
        report.notes.append(
            f"Half-time scores for {len(halves):,} games, from play-by-play."
        )

    logs = build_player_logs(league, raw_dir, report.seasons, report)
    report.player_logs = len(logs)
    logs_path = processed_dir / PLAYER_LOGS_FILENAME
    if _guard_shrink(
        PLAYER_LOGS_FILENAME, logs_path, len(logs), report, allow_shrink=allow_shrink
    ):
        logs.to_csv(logs_path, index=False)

    return report
