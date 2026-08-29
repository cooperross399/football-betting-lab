"""The card. Gating and presentation, and no pricing.

Pricing lives in `card_pricing`. Keeping them apart means a gate cannot be
bypassed by a pricing path, which is the shape of bug that lets an unapproved
market reach a selection.

## What this card says today, and why that is correct

**It makes no recommendations.** No market is allowlisted, because
allowlisting takes measurement against real prices and a signed human
acceptance receipt, and neither exists yet. So the card prices every market it
can, freezes those opinions into the forward ledger, and states in those words
that it is **accumulating evidence rather than making recommendations**.

That is not a degraded card. It is the product until the evidence exists.

## The order the gates run in, and why

1. **Preseason** — before anything is priced, because an exhibition opinion
   frozen into the ledger rots there as unsettleable noise.
2. **Market eligibility** — allowlisting, completeness, availability of prices.
3. **Kickoff** — a started game, or one whose start cannot be confirmed, is
   quarantined and its stake removed.
4. **Availability** — no feed publishes inactives, so no player prop can
   produce a selection at all.
5. **Quarterback change** — quarantines a team's passing and receiving tree.

Every exclusion is **counted and named**. An excluded market is never a pass,
an avoid, or a no-value call: those are genuine model judgements about markets
that were actually priced, and presenting one as the other misrepresents the
card.

## The accounting identity

Printed every run, and it is meant to fail loudly:

    priced = no_opinion + unparseable + ambiguous + opinions

Silent attrition is how a card ends up recommending from a sixth of a slate
and reporting it as the whole one.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

from football_betting_lab.config import (
    MAX_DEFAULT_JUICE,
    MAX_DEFAULT_PRICE,
    MIN_EDGE,
    MIN_PROP_EDGE,
)
from football_betting_lab.forward_evidence import american_to_implied
from football_betting_lab.gates import selection_blocked_note
from football_betting_lab.kickoff import QUARANTINE_HEADING, judge, partition
from football_betting_lab.leagues import League
from football_betting_lab.markets import MARKETS_BY_KEY, PLAYER
from football_betting_lab.reports.card_pricing import PricingDiagnostics
from football_betting_lab.season import clean_text
from football_betting_lab.selection import normalise_line, selection_key
from football_betting_lab.staging_provider_policy import StagingProviderPolicy


#: The sentence a card with nothing to recommend leads with. Contract-ish: the
#: tests match it, and it must never soften into something that reads like a
#: recommendation.
ACCUMULATING_NOTE = (
    "This card is **accumulating evidence, not making recommendations.**"
)


@dataclass
class CardResult:
    league: League
    generated_at: str
    slate_date: str
    games: list[str] = field(default_factory=list)
    preseason_excluded: list[str] = field(default_factory=list)
    quarantined: list[tuple[str, str]] = field(default_factory=list)
    market_states: dict[str, str] = field(default_factory=dict)
    diagnostics: PricingDiagnostics = field(default_factory=PricingDiagnostics)
    selections: list[dict] = field(default_factory=list)
    frozen_rows: int = 0
    ledger_rows: int = 0
    notes: list[str] = field(default_factory=list)

    @property
    def decision(self) -> str:
        """One word for the run summary and the card-feed status file."""
        if not self.games:
            return "no-slate"
        if self.selections:
            return "selections"
        return "no-selections"


def select(
    prices: pd.DataFrame,
    probabilities: Mapping[tuple, float],
    league: League,
    *,
    policy: StagingProviderPolicy,
    now: datetime,
    undesignated_allowed: bool = False,
) -> tuple[list[dict], list[tuple[str, str]]]:
    """Every bet that clears every bar, and everything the guard pulled.

    This path had never run. Nothing is allowlisted, so `build_card` recorded
    market states, ran the kickoff guard over the slate, and returned with an
    empty `selections` list that nothing ever filled — which looked identical
    to "no market qualified". **The first card after a signed receipt would
    have produced nothing and said so confidently.**

    The bars, in the order they are applied:

    1. the market has a reviewed approval;
    2. the model has an opinion at all — a missing key is *no opinion*, which
       is different from a probability of zero;
    3. the edge clears the market's threshold, higher for props than for team
       markets because a card is built before inactives are known;
    4. the price is not worse than the juice bar and not longer than the model
       is trusted to judge;
    5. for a player prop, the availability gate permits a selection — which it
       does not unless a recorded verdict says so;
    6. the kickoff guard confirms the game has not started.

    One wager can be quoted by many books. The best price is taken **after**
    every bar, so a bar is never cleared by a price the card would not have
    used.
    """
    if prices.empty:
        return [], []

    best: dict[tuple, dict] = {}
    quarantined: list[tuple[str, str]] = []
    for row in prices.itertuples():
        market_key = clean_text(getattr(row, "market", ""))
        market = MARKETS_BY_KEY.get(market_key)
        if market is None or not policy.market_allowed(league, market_key):
            continue
        selection = clean_text(getattr(row, "selection", ""))
        line = normalise_line(getattr(row, "line", None))
        probability = probabilities.get(
            selection_key(
                row, market=market_key, selection=selection, line=line, league=league
            )
        )
        if probability is None:
            continue
        try:
            odds = int(float(getattr(row, "american_odds")))
        except (TypeError, ValueError):
            continue
        if odds < MAX_DEFAULT_JUICE or odds > MAX_DEFAULT_PRICE:
            continue
        threshold = MIN_PROP_EDGE if market.kind == PLAYER else MIN_EDGE
        edge = probability - american_to_implied(odds)
        if edge < threshold:
            continue
        if market.kind == PLAYER and not undesignated_allowed:
            # No player prop may select until a recorded verdict says an
            # undesignated player can. Nothing reaches `confirmed` today.
            continue
        verdict = judge(getattr(row, "commence_time", ""), now=now)
        label = (
            f"{clean_text(getattr(row, 'away_team', ''))} @ "
            f"{clean_text(getattr(row, 'home_team', ''))}"
        )
        if not verdict.plays:
            quarantined.append((f"{label} — `{market_key}`", verdict.reason))
            continue
        key = (
            market_key,
            clean_text(getattr(row, "player", "")),
            selection,
            line,
            label,
        )
        candidate = {
            "game": label,
            "market": market_key,
            "player": clean_text(getattr(row, "player", "")),
            "selection": selection,
            "line": line,
            "odds": odds,
            "book": clean_text(getattr(row, "book", "")),
            "model_probability": probability,
            "edge": edge,
        }
        if key not in best or odds > best[key]["odds"]:
            best[key] = candidate

    selections = sorted(best.values(), key=lambda item: -item["edge"])
    return selections, quarantined


def build_card(
    prices: pd.DataFrame,
    league: League,
    *,
    policy: StagingProviderPolicy,
    diagnostics: PricingDiagnostics,
    now: datetime,
    slate_date: str,
    preseason_excluded: list[str],
    probabilities: Mapping[tuple, float] | None = None,
    undesignated_allowed: bool = False,
) -> CardResult:
    result = CardResult(
        league=league,
        generated_at=now.isoformat(),
        slate_date=slate_date,
        preseason_excluded=list(preseason_excluded),
        diagnostics=diagnostics,
    )
    if prices.empty:
        return result

    result.games = sorted(
        {
            f"{row.away_team} @ {row.home_team}"
            for row in prices[["home_team", "away_team"]].drop_duplicates().itertuples()
        }
    )

    # Every market's state, allowlisting included. Nothing is allowlisted, so
    # every market lands here with a stated reason rather than silently.
    for market in sorted(set(prices["market"].astype(str))):
        if policy.market_allowed(league, market):
            result.market_states[market] = "eligible"
        else:
            result.market_states[market] = policy.refusal_reason(league, market)

    # The kickoff guard runs over whatever would have been selected. With no
    # allowlisted market there is nothing to quarantine, and the guard still
    # runs so its absence is never the reason a started game got through.
    playable, quarantined = partition(
        [
            {
                "commence_time": row.commence_time,
                "label": f"{row.away_team} @ {row.home_team}",
            }
            for row in prices[
                ["home_team", "away_team", "commence_time"]
            ].drop_duplicates().itertuples()
        ],
        now=now,
    )
    result.quarantined = [
        (str(item["label"]), verdict.reason) for item, verdict in quarantined
    ]

    if probabilities:
        selections, pulled = select(
            prices,
            probabilities,
            league,
            policy=policy,
            now=now,
            undesignated_allowed=undesignated_allowed,
        )
        result.selections = selections
        result.quarantined.extend(pulled)
    return result


def render(result: CardResult) -> str:
    lines: list[str] = []
    add = lines.append
    league = result.league
    add(f"# {league.title} card — {result.slate_date}")
    add("")
    add(ACCUMULATING_NOTE)
    add("")
    allowlisted = sorted(
        market for market, state in result.market_states.items()
        if state == "eligible"
    )
    if allowlisted:
        add(
            f"**{len(allowlisted)} market(s) have a reviewed approval**: "
            + ", ".join(f"`{m}`" for m in allowlisted)
            + ". Every other market is priced, frozen into the forward ledger, "
            "and excluded from selection with a stated reason."
        )
    else:
        add(
            "No market is allowlisted. Allowlisting takes measurement against "
            "real prices and a signed human acceptance receipt, and neither "
            "exists yet. So every market that can be priced is priced, every "
            "opinion is frozen into the forward ledger, and none of it is a "
            "recommendation."
        )

    if not result.games:
        add("")
        add(
            f"**No {league.title} games are in scope for {result.slate_date}.** "
            "That is an absence, not a fault, and not a no-value call."
        )
        if result.preseason_excluded:
            add("")
            add(
                f"{len(result.preseason_excluded)} event(s) were excluded as "
                "preseason. Books post exhibition lines and the provider does "
                "not flag them; an opinion frozen on one would rot in the "
                "ledger as unsettleable noise."
            )
            for label in result.preseason_excluded:
                add(f"- {label}")
        return "\n".join(lines) + "\n"

    add("")
    add(f"## Slate ({len(result.games)} game(s))")
    add("")
    for game in result.games:
        add(f"- {game}")

    add("")
    add("## Selections")
    add("")
    if result.selections:
        add(
            "Every one of these cleared an approved market, a modelled "
            "opinion, its edge threshold, the juice and price bars, the "
            "availability gate and the kickoff guard. **A cleared bar is not "
            "a prediction.**"
        )
        add("")
        add("| Game | Market | Selection | Line | Price | Book | Edge |")
        add("|:-----|:-------|:----------|-----:|------:|:-----|-----:|")
        for pick in result.selections:
            player = f"{pick['player']} " if pick.get("player") else ""
            line = "—" if pick.get("line") is None else f"{pick['line']:g}"
            add(
                f"| {pick['game']} | `{pick['market']}` | "
                f"{player}{pick['selection']} | {line} | "
                f"{int(pick['odds']):+d} | {pick['book']} | "
                f"{pick['edge']:+.1%} |"
            )
    elif allowlisted:
        add(
            "**None.** Markets are approved, but nothing cleared every bar "
            "today. That is a genuine model judgement about markets that were "
            "priced and modelled — unlike an excluded market, which is a "
            "different thing entirely."
        )
    else:
        add(
            "**None.** Not a pass, not an avoid, and not a no-value call — no "
            "market has a reviewed approval, so the card is not permitted to "
            "select from any of them."
        )
    add("")
    add(selection_blocked_note())

    add("")
    add("## Markets, and why each is excluded")
    add("")
    add(
        "An excluded market is never a pass, an avoid, or a no-value call. "
        "Those are genuine model judgements about markets that were actually "
        "priced and modelled; this is a different thing entirely."
    )
    add("")
    # Grouped by reason rather than listed per market. Seventeen rows of one
    # identical sentence is noise, and noise on a card is how the line that
    # matters gets skipped.
    grouped: dict[str, list[str]] = {}
    for market, state in sorted(result.market_states.items()):
        grouped.setdefault(state, []).append(market)
    for state, markets in sorted(grouped.items(), key=lambda item: -len(item[1])):
        add(f"**{len(markets)} market(s)** — {state}")
        add("")
        add(", ".join(f"`{market}`" for market in markets))
        add("")

    if result.quarantined:
        add("")
        add(f"## {QUARANTINE_HEADING}")
        add("")
        add(
            "A game that has started, or whose start cannot be confirmed, is "
            "no longer available at the price shown. Ambiguity falls on the "
            "not-a-play side, always."
        )
        add("")
        for label, reason in result.quarantined:
            add(f"- **{label}** — {reason}")

    add("")
    add("## The accounting identity")
    add("")
    add(f"`{result.diagnostics.identity_line()}`")
    if result.diagnostics.reasons:
        add("")
        add("Where the opinions did not go:")
        add("")
        for reason, count in result.diagnostics.reasons.most_common(10):
            add(f"- {count} x {reason}")
    if not result.diagnostics.reconciles():
        add("")
        add(
            "> **The identity does not reconcile.** A row fell out for a "
            "reason nobody counted, and that is a bug rather than a slate."
        )

    add("")
    add("## Forward evidence")
    add("")
    add(
        f"{result.frozen_rows:,} opinion(s) frozen for {result.slate_date}; "
        f"{result.ledger_rows:,} row(s) in the settled ledger."
    )
    add("")
    add(
        "Frozen before kickoff, settled after, never repriced. Historical "
        "prices can be bought later; forward evidence cannot be back-dated."
    )
    for note in result.notes:
        add("")
        add(f"> {note}")
    return "\n".join(lines) + "\n"
