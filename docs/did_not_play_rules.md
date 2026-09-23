# The did-not-play rule, read

`availability_cost.py` has said since it was written that the largest
assumption in this lab is **whether a book voids a player prop when the named
player takes no snap, or grades it** — and that it is "one a human can settle in
a minute by reading a book's prop rules".

This is that reading, done on **2026-09-23**.

## The answer

**Seven of the eight books whose rule text could be obtained void a
did-not-play prop, and void it symmetrically** — the stake is returned, on the
over and the under alike, with no over/under split for the zero-snap case at
any of them.

**The eighth is Bovada, which grades**, and Bovada is in this lab's feed. So
the short version — "books void" — is true of the industry and **false of the
book this lab is most likely to be acted on at**, which is the only reason this
document is longer than a sentence.

## Where the text came from

Six of these are **Massachusetts Gaming Commission house-rules filings** —
operators must file them, and the filed PDF is the authoritative published
version, which a marketing help page is not. Two are the operator's own rules
page, for books with no MA licence.

Every quote below is short and verbatim; the file and page are named so the
claim can be re-checked rather than believed.

| Book | Rule | Source |
|:--|:--|:--|
| **DraftKings** | must "participate in at least one (1) play (including special teams)"; otherwise "bets on that player/market will be void" | [MA filing, 8.1.24](https://massgaming.com/wp-content/uploads/DraftKings-House-Rules-8.1.24.pdf) p.56; restated generally in the [8.18.25 filing](https://massgaming.com/wp-content/uploads/DraftKings-House-Rules-8.18.25.pdf) |
| **FanDuel** | voided "only when a player does not play a snap in that game" | [MA filing, 3.27.25](https://massgaming.com/wp-content/uploads/FanDuel-House-Rules-3.27.25.pdf) |
| **BetMGM** | "the player(s) must play at least one snap for bets to have action" | [MA filing, 8.14.25](https://massgaming.com/wp-content/uploads/BetMGM-House-Rules-8.14.25.pdf) |
| **Caesars** | "players must play in the game or else wagers will be void" | [MA filing, 11.12.24](https://massgaming.com/wp-content/uploads/Caesars-House-Rules-11.12.24.pdf) |
| **Fanatics** | "must play at least one snap (including special teams snaps)" for action | [MA filing, 3.27.25](https://massgaming.com/wp-content/uploads/Fanatics-House-Rules-3.27.25.pdf) |
| **Pinnacle** | "the particular player must play for action" | [betting rules](https://www.pinnacle.com/en/future/betting-rules) |
| **ESPN Bet** | defines participation as "if they take to the field for at least one snap" — **but states no void consequence in its football section**; the void outcome is an inference from its general action clause, where its own baseball and basketball sections say it outright | [MA filing, 5.23.25](https://massgaming.com/wp-content/uploads/Penn-Sports-Interactive-House-Rules-5.23.25.pdf) FO.6.2 |
| **Bovada** | **"Players that are active and end up not playing still have action"** | [football betting rules](https://www.bovada.lv/help/common-faq/football-betting-rules) |

## Bovada is the exception, and it is the exception that matters

Bovada keys on the **game-day active roster**, not on snaps. A player who is
active and never takes a snap is **graded**, so the over loses and an under at
zero wins. It also says injuries after the opening kickoff do not affect
settlement.

That is the opposite rule from every other book here, and Bovada is in this
lab's price feed. It is also the weakest source in the table — an offshore book
with no regulator filing, so its rule rests on its own help page and cannot be
cross-checked against a filed document. **Worth a second read by a human before
it is relied on.**

## Three narrower carve-outs, each of which creates an over/under asymmetry

The blunt question — "does the asymmetry exist?" — is **no for the zero-snap
case at every book read**. It does exist in three narrower places, and each
would matter to a model that bets both sides:

1. **Fanatics, NFL only.** A player who is *active* and leaves injured in the
   first quarter without returning: "Wagers placed on the under option will be
   settled as winners", while the over is void. This is partial participation,
   not a did-not-play, and it is in the 9.3.24 filing too, so it is not new.
2. **FanDuel Kicking Points.** An active kicker who plays no snap: "all bets
   will stand" — graded, not voided.
3. **A literal reading of the Longest-X markets at DraftKings, FanDuel and
   Fanatics**, where a player who records no such statistic settles the under as
   won, with no participation condition attached. The general participation
   clause is written as an override and should control, but the two sentences
   point in opposite directions and only the book can say which wins.

Two stricter participation thresholds are also worth recording: **BetMGM**
requires a quarterback to *start*, not merely play, and **Pinnacle** voids a
quarterback market if he attempts no pass.

## What could not be read

Reported as unverified rather than guessed at.

- **bet365.** Every `help.bet365.com` path returns HTTP 403 from this
  environment and there is no Wayback capture. Search-index text attributed to
  those pages reads like the standard rule, but the page was not loaded, so it
  is not asserted here. Anyone on a normal browser can settle this in a minute.
- **BetRivers.** Rules pages are client-rendered and serve no rule text; Rush
  Street has no Massachusetts filing, so the regulator route that worked for the
  others is closed.

## The books in this lab's feed are not the books in that table

This is the gap that matters most for applying any of it. The quote store holds
eleven providers:

`barstool`, `betmgm`, `betonlineag`, `betrivers`, `bovada`, `draftkings`,
`fanatics`, `fanduel`, `pointsbetus`, `unibet_us`, `williamhill_us`.

- **Directly verified — five of eleven:** `betmgm`, `draftkings`, `fanatics`
  and `fanduel` **void**; `bovada` **grades**. Four to one, not five to zero,
  and the one is the exception.
- **Verified under a different name, assuming the operator mapping holds:**
  `williamhill_us` → Caesars, `barstool` → ESPN Bet (Penn), `pointsbetus` →
  Fanatics. These are legacy odds-api keys and the mapping is an **assumption**,
  not something checked against a filing.
- **Not researched at all:** `betrivers`, `unibet_us`, `betonlineag`.

The settled-bet ledger (`nfl_props_backtest_bets.csv`) carries **no book
column**, so the record cannot currently be split by settlement rule even now
that the rules are known. Adding one and re-running the backtest is what a
per-book sensitivity would need.

## What follows for this lab — and what does not

**This does not ship `props_selectable_when_undesignated`, and it should not.**

The verdict's own entry in `verdicts.py` says it waits on this question. That
was true when it was written and is no longer the whole picture:

- `availability_cost.py` retracts the +13.0%/−0.8% pair that motivated it — the
  numbers were computed on cross-season-settled bets.
- `CLAUDE.md` already states the conclusion: the clause "is still worth
  answering before anything is acted on, but **nothing waits on it**."
- The population the verdict would open measures **−3.7%**, and against a
  grade-as-loss rule **−5.8%**. The rules question is now answered; the *edge*
  question is answered the other way.

So the rules answer removes a stated blocker and leaves a real one. Shipping the
verdict would turn on live player-prop selection — `run_gameday_card.py` passes
`ships(...)` straight into `build_card` — for a population measured as losing,
in a repo whose allowlist evidence says 0 of 18 markets clear every bar.

**What the answer is actually worth** is narrower and real. Of the eleven
books in the feed, five were read directly: the void assumption under every
figure in `nfl_availability_cost.md` is *supported by rule text* at four of
them and *contradicted* at the fifth. The fifth is Bovada. A card that selects
player props there cannot use the void-based arithmetic, because Bovada does
not void.
