"""Every NFL market this lab knows how to name, price, and settle.

One table, in one place, so a market cannot mean one thing in the fetch and
another in the report. The provider adapter, the eligibility gate, the models,
the card and the backtest all read from here.

## The rule that decides what is in this table

**If nothing here can settle it, it is not wired.** Fetching prices nothing
can consume spends credits on rows no join will ever find, and pricing
without honest settlement manufactures evidence. Every entry names the
nflverse quantity it settles against; a market the provider serves and
nflverse cannot settle is recorded in `DEFERRED_MARKETS` with its reason
rather than silently dropped.

## Tiers

`tier` is a *credit* decision, not a modelling one. The shared Odds API quota
is spent by two labs already, and the full documented catalogue is 111
per-event markets — 30,192 credits for one pass over the 2026 NFL season
(`docs/credit_cost.md`). Tier 1 is what a Week 1 fetch asks for. Tier 2 is
wired, settleable, and waiting on a quota decision that is Cooper's.

A tier is not an opinion about edge. Nothing in this table has been measured
against a price yet, and `docs/what_we_can_and_cannot_claim.md` is explicit
that nothing may be described as though it had.

## What the provider bills

The bulk `/odds` endpoint bills `markets x regions` for the whole slate and
serves `h2h`, `spreads`, `totals`. Everything else is per event, billed at
**unique markets returned x regions** — so an asked-for market nobody quotes
costs nothing, and the alternate ladders ride along free until a book hangs
one. The cap is still enforced against the pessimistic bound, because a cap
that trusts the optimistic one is not a cap.
"""

from __future__ import annotations

from dataclasses import dataclass


PLAYER = "player"
TEAM = "team"


@dataclass(frozen=True)
class Market:
    """One market: what it is called here, at the provider, and how it settles."""

    #: The name used everywhere inside this repository.
    key: str
    #: The Odds API market key that supplies it.
    provider_key: str
    #: Human label for reports.
    label: str
    #: `player` or `team`.
    kind: str
    #: The nflverse quantity a settled result is read from, in words. Prose
    #: rather than a bare column name because several of these are
    #: derivations over play-by-play, and a column name would imply a column
    #: that does not exist.
    settles_on: str
    #: The selections a complete market must quote. A player prop quotes one
    #: side at most books, which is why most list only `over`; a genuinely
    #: two-sided market lists both, and an incomplete one is excluded rather
    #: than half-used.
    selections: tuple[str, ...] = ("over",)
    #: Whether the provider serves it from the per-event endpoint.
    per_event: bool = True
    #: 1 = asked for on a Week 1 fetch. 2 = wired and waiting on quota.
    tier: int = 1
    #: The game segment it settles over: full game, half, or quarter.
    period: str = "game"


# --------------------------------------------------------------------------
# Team markets. The bulk three cost `markets x regions` for the whole slate.
# --------------------------------------------------------------------------

BULK_TEAM_MARKETS: tuple[Market, ...] = (
    Market(
        key="moneyline",
        provider_key="h2h",
        label="Moneyline",
        kind=TEAM,
        settles_on="final score, home vs away (ties are possible in the NFL "
        "and settle as a push on a two-way moneyline)",
        selections=("home", "away"),
        per_event=False,
    ),
    Market(
        key="spread",
        provider_key="spreads",
        label="Spread",
        kind=TEAM,
        settles_on="final margin against the line; a whole-number line "
        "pushes on an exact margin, which is where 3 and 7 live",
        selections=("home", "away"),
        per_event=False,
    ),
    Market(
        key="total_points",
        provider_key="totals",
        label="Total points",
        kind=TEAM,
        settles_on="home_score + away_score against the line; a whole-number "
        "total pushes on an exact sum",
        selections=("over", "under"),
        per_event=False,
    ),
)

PER_EVENT_TEAM_MARKETS: tuple[Market, ...] = (
    Market(
        key="alternate_spread",
        provider_key="alternate_spreads",
        label="Spread (alternate ladder)",
        kind=TEAM,
        settles_on="same as `spread`, every offered rung",
        selections=("home", "away"),
    ),
    Market(
        key="alternate_total_points",
        provider_key="alternate_totals",
        label="Total points (alternate ladder)",
        kind=TEAM,
        settles_on="same as `total_points`, every offered rung",
        selections=("over", "under"),
    ),
    Market(
        key="team_total",
        provider_key="team_totals",
        label="Team total points",
        kind=TEAM,
        settles_on="one side's final score against the line",
        selections=("home_over", "home_under", "away_over", "away_under"),
    ),
    Market(
        key="alternate_team_total",
        provider_key="alternate_team_totals",
        label="Team total points (alternate ladder)",
        kind=TEAM,
        settles_on="same as `team_total`, every offered rung",
        selections=("home_over", "home_under", "away_over", "away_under"),
    ),
    Market(
        key="moneyline_h1",
        provider_key="h2h_h1",
        label="Moneyline, first half",
        kind=TEAM,
        settles_on="score after two quarters, summed from play-by-play "
        "scoring plays",
        selections=("home", "away"),
        period="h1",
    ),
    Market(
        key="spread_h1",
        provider_key="spreads_h1",
        label="Spread, first half",
        kind=TEAM,
        settles_on="first-half margin from play-by-play scoring plays",
        selections=("home", "away"),
        period="h1",
    ),
    Market(
        key="total_points_h1",
        provider_key="totals_h1",
        label="Total points, first half",
        kind=TEAM,
        settles_on="first-half combined score from play-by-play scoring plays",
        selections=("over", "under"),
        period="h1",
    ),
    # ---- Tier 2: wired, settleable, waiting on the quota decision. ----
    Market(
        key="moneyline_3_way",
        provider_key="h2h_3_way",
        label="Result including the tie",
        kind=TEAM,
        settles_on="final score with the tie as a real outcome — the NFL "
        "plays a single overtime period in the regular season and games do "
        "end level",
        selections=("home", "draw", "away"),
        tier=2,
    ),
    Market(
        key="moneyline_h2",
        provider_key="h2h_h2",
        label="Moneyline, second half",
        kind=TEAM,
        settles_on="score in quarters 3-4 plus overtime, from play-by-play",
        selections=("home", "away"),
        tier=2,
        period="h2",
    ),
    Market(
        key="spread_h2",
        provider_key="spreads_h2",
        label="Spread, second half",
        kind=TEAM,
        settles_on="second-half margin from play-by-play",
        selections=("home", "away"),
        tier=2,
        period="h2",
    ),
    Market(
        key="total_points_h2",
        provider_key="totals_h2",
        label="Total points, second half",
        kind=TEAM,
        settles_on="second-half combined score from play-by-play",
        selections=("over", "under"),
        tier=2,
        period="h2",
    ),
) + tuple(
    # The quarter ladder. Four quarters x moneyline/spread/total, plus the
    # quarter team totals and the two alternate quarter ladders. All settle
    # from play-by-play scoring plays filtered by `qtr`, which is the same
    # derivation the halves use — so wiring them costs no new settlement
    # code, only credits. That is exactly why they are tier 2.
    Market(
        key=f"{stem}_q{quarter}",
        provider_key=f"{provider}_q{quarter}",
        label=f"{label}, Q{quarter}",
        kind=TEAM,
        settles_on=f"Q{quarter} scoring plays from play-by-play",
        selections=selections,
        tier=2,
        period=f"q{quarter}",
    )
    for stem, provider, label, selections in (
        ("moneyline", "h2h", "Moneyline", ("home", "away")),
        ("spread", "spreads", "Spread", ("home", "away")),
        ("total_points", "totals", "Total points", ("over", "under")),
        (
            "team_total",
            "team_totals",
            "Team total",
            ("home_over", "home_under", "away_over", "away_under"),
        ),
    )
    for quarter in (1, 2, 3, 4)
)


# --------------------------------------------------------------------------
# Player props.
#
# Yardage markets are flagged `compound` in their settlement prose because
# that is what the model must respect: yards are opportunities x yards per
# opportunity, right-skewed and zero-inflated, and a count distribution is
# the wrong shape for them. See `docs/what_we_can_and_cannot_claim.md`.
# --------------------------------------------------------------------------

_PROP_SPECS: tuple[tuple[str, str, str, str, int], ...] = (
    # (key, provider_key, label, settles_on, tier)
    ("pass_yards", "player_pass_yds", "Passing yards",
     "sum of `passing_yards` over the player's game (compound: attempts x "
     "yards per attempt, right-skewed, zero-inflated)", 1),
    ("pass_attempts", "player_pass_attempts", "Pass attempts",
     "count of pass attempts in play-by-play", 1),
    ("pass_completions", "player_pass_completions", "Pass completions",
     "count of completed passes in play-by-play", 1),
    ("pass_tds", "player_pass_tds", "Passing touchdowns",
     "count of touchdown passes thrown", 1),
    ("pass_interceptions", "player_pass_interceptions", "Interceptions thrown",
     "count of interceptions thrown", 1),
    ("pass_longest_completion", "player_pass_longest_completion",
     "Longest completion",
     "max `passing_yards` on a single completed play (a maximum, not a sum — "
     "its distribution is an extreme-value one and is modelled as such)", 1),
    ("rush_yards", "player_rush_yds", "Rushing yards",
     "sum of `rushing_yards` (compound; carries x yards per carry)", 1),
    ("rush_attempts", "player_rush_attempts", "Rush attempts",
     "count of carries in play-by-play", 1),
    ("rush_tds", "player_rush_tds", "Rushing touchdowns",
     "count of rushing touchdowns", 1),
    ("rush_longest", "player_rush_longest", "Longest rush",
     "max `rushing_yards` on a single carry (a maximum, not a sum: an "
     "extreme-value distribution)", 1),
    ("receptions", "player_receptions", "Receptions",
     "count of receptions — a genuine count, and the one prop family where a "
     "count distribution is the right shape", 1),
    ("reception_yards", "player_reception_yds", "Receiving yards",
     "sum of `receiving_yards` (compound; receptions x yards per reception)", 1),
    ("reception_tds", "player_reception_tds", "Receiving touchdowns",
     "count of receiving touchdowns", 1),
    ("reception_longest", "player_reception_longest", "Longest reception",
     "max `receiving_yards` on a single reception (a maximum, not a sum: "
     "an extreme-value distribution)", 1),
    ("anytime_td", "player_anytime_td", "Anytime touchdown scorer",
     "whether the player scored any touchdown (rush, reception or return) — "
     "priced as total TDs over 0.5, one name for one thing", 1),
    ("kicking_points", "player_kicking_points", "Kicking points",
     "3 x field goals made + 1 x extra points made, from play-by-play", 1),
    ("field_goals", "player_field_goals", "Field goals made",
     "count of made field goals", 1),
    ("tackles_assists", "player_tackles_assists", "Tackles + assists",
     "solo tackles + assisted tackles, from the defensive stats table", 1),
    ("sacks", "player_sacks", "Sacks",
     "sacks credited, half-sacks included, from the defensive stats table", 1),
    ("defensive_interceptions", "player_defensive_interceptions",
     "Defensive interceptions",
     "interceptions caught, from the defensive stats table", 1),
    # ---- Tier 2 ----
    ("first_td", "player_1st_td", "First touchdown scorer",
     "the scorer of the game's first touchdown, by play-by-play ordering", 2),
    ("last_td", "player_last_td", "Last touchdown scorer",
     "the scorer of the game's last touchdown, by play-by-play ordering", 2),
    ("solo_tackles", "player_solo_tackles", "Solo tackles",
     "solo tackles from the defensive stats table", 2),
    ("pats", "player_pats", "Points after touchdown",
     "count of made extra points", 2),
    ("pass_rush_yards", "player_pass_rush_yds", "Passing + rushing yards",
     "sum of the two, same player — a composite whose two parts this lab "
     "already models, and which must never be staked alongside either part "
     "as though independent", 2),
    ("pass_rush_reception_yards", "player_pass_rush_reception_yds",
     "Passing + rushing + receiving yards",
     "sum of all three for one player; same correlation warning", 2),
    ("pass_rush_reception_tds", "player_pass_rush_reception_tds",
     "Passing + rushing + receiving touchdowns",
     "sum of all three for one player; same correlation warning", 2),
    ("rush_reception_yards", "player_rush_reception_yds",
     "Rushing + receiving yards",
     "sum of the two, same player; the standard 'scrimmage yards' prop", 2),
    ("rush_reception_tds", "player_rush_reception_tds",
     "Rushing + receiving touchdowns", "sum of the two, same player", 2),
    ("pass_yards_q1", "player_pass_yds_q1", "Passing yards, Q1",
     "sum of `passing_yards` on plays with `qtr == 1`", 2),
)

PROP_MARKETS: tuple[Market, ...] = tuple(
    Market(
        key=key,
        provider_key=provider_key,
        label=label,
        kind=PLAYER,
        settles_on=settles_on,
        selections=("over",),
        tier=tier,
    )
    for key, provider_key, label, settles_on, tier in _PROP_SPECS
)


TEAM_MARKETS: tuple[Market, ...] = BULK_TEAM_MARKETS + PER_EVENT_TEAM_MARKETS
ALL_MARKETS: tuple[Market, ...] = TEAM_MARKETS + PROP_MARKETS
MARKETS_BY_KEY: dict[str, Market] = {m.key: m for m in ALL_MARKETS}

PROVIDER_KEY_TO_MARKET: dict[str, str] = {
    m.provider_key: m.key for m in ALL_MARKETS
}

#: Alternate ladders carry the same project market on a different line. They
#: are listed separately because the featured market and the ladder are
#: different provider keys with different coverage — the EPL lab wrote a
#: market off for a season after checking only the featured one.
ALTERNATE_PROVIDER_KEYS: dict[str, str] = {
    f"{m.provider_key}_alternate": m.key
    for m in PROP_MARKETS
    # The provider documents an `_alternate` ladder for 26 of the 32 NFL prop
    # keys. The touchdown-scorer markets and the Q1 passing market have none.
    if m.provider_key
    not in {
        "player_anytime_td",
        "player_1st_td",
        "player_last_td",
        "player_pass_yds_q1",
    }
}

#: Markets the provider serves for the NFL that this lab deliberately does not
#: wire, each with the reason. Recorded rather than dropped: "the provider
#: does not offer this" and "we never asked" have looked identical before,
#: and the second cost the NHL lab a market for a season.
DEFERRED_MARKETS: dict[str, str] = {
    "outrights": "A season-long future. This lab prices games, and a future "
    "cannot be settled by a boxscore or frozen into a day-as-unit ledger.",
    "h2h_lay": "Exchange-only. No exchange is in the `us` region set.",
    "outrights_lay": "Exchange-only, and a future besides.",
    "player_tds_over": "The provider documents it without an outcome shape "
    "this lab has parsed. Probe it in season before wiring; do not guess.",
    "alternate_spreads_h1": "Half and quarter alternate ladders settle from "
    "the same play-by-play derivation as their featured markets, so they are "
    "settleable — they are unwired purely on credits (tier 3), and this entry "
    "exists so that is never misread as 'not offered'.",
    "alternate_totals_h1": "As above.",
    "alternate_team_totals_h1": "As above.",
    "h2h_3_way_h1": "As above; plus no first-half tie model yet.",
}


def market_for(key: str) -> Market:
    """Look up a market by its project key, or say which keys exist."""
    text = str(key or "").strip().lower()
    try:
        return MARKETS_BY_KEY[text]
    except KeyError as exc:
        raise KeyError(
            f"Unknown market {key!r}. Known markets: {sorted(MARKETS_BY_KEY)}"
        ) from exc


def market_for_provider_key(provider_key: str) -> Market | None:
    """The project market a provider key supplies, or None if we ignore it.

    None rather than an error, deliberately: a provider response carries
    markets this lab does not price, and every one of them being an error
    would make an ordinary response unparseable.
    """
    text = str(provider_key or "").strip().lower()
    project = PROVIDER_KEY_TO_MARKET.get(text) or ALTERNATE_PROVIDER_KEYS.get(text)
    return MARKETS_BY_KEY.get(project) if project else None


def bulk_provider_keys(tier: int = 1) -> tuple[str, ...]:
    return tuple(
        m.provider_key for m in ALL_MARKETS if not m.per_event and m.tier <= tier
    )


def per_event_provider_keys(tier: int = 1, *, alternates: bool = True) -> tuple[str, ...]:
    """Provider keys billed at one credit per market returned per event."""
    keys = [m.provider_key for m in ALL_MARKETS if m.per_event and m.tier <= tier]
    if alternates:
        allowed = {m.key for m in ALL_MARKETS if m.tier <= tier}
        keys += [k for k, v in ALTERNATE_PROVIDER_KEYS.items() if v in allowed]
    return tuple(dict.fromkeys(keys))


def markets_in_tier(tier: int) -> tuple[Market, ...]:
    return tuple(m for m in ALL_MARKETS if m.tier <= tier)
