# Market opportunity plan — where this lab looks next

Written 2026-08-31. Read after `docs/project_status.md` and
`docs/what_we_can_and_cannot_claim.md`; nothing here overrides either.

Cooper's instruction is "chase every market, find edges wherever possible, and
never stop improving." This document turns that into a costed sequence. It is
written against a lab whose honest position is **no demonstrated edge
anywhere**, on the complete bought population, so the sequence is ordered by
*what kind of thing could possibly be true* rather than by what would be
exciting.

---

## 1. The ranking principle, stated before anything is ranked

**Prefer edges that do not require out-forecasting the market.**

That is not a preference, it is what the evidence forces. Measured in this
repository:

| Instrument | Result | Sample |
|:---|:---|---:|
| Forecast skill (`nfl_forecast_skill.md`) | model Brier **0.26057** vs market **0.22703**; never better on any held-out season, even after walk-forward calibration, even with the vig handicapping the market | 74,345 bets, 768 games |
| Replication (`nfl_props_replication.md`) | **0 of 18 markets** clear on held-out seasons | 2023-25 |
| Price sensitivity (`nfl_price_sensitivity.md`) | no market profitable at the **consensus** price except the artefact | 83,947 bets |
| Null baseline (`nfl_null_baseline.md`) | betting everything returns **−9.47%** — the harness is sound | 366,725 bets |
| Closing line (`nfl_closing_line_backtest.md`) | team model vs the close: moneyline **−6.2%**, spread **−1.9%**, total **−1.8%**, every interval spanning zero | 1,923 / 1,886 / 1,708 bets |
| Settlement screen | `tackles_assists` **+11.7%** held-out is a settlement offset, not an edge | 3,109 held-out bets |

A model with a worse Brier score than the price is not unlucky, it is
uninformed, and no subgroup, threshold or new market rescues it. So the
ordering is:

* **Tier A — relations between prices.** Book-internal coherence (a book's own
  team totals against its own game total), cross-book two-sided arbitrage,
  ladder monotonicity. These ask whether a book's quotes contradict *each
  other*. Their failure mode is not "the model is bad", which is the only
  failure mode this lab has ever actually observed.
* **Tier B — information purchases.** Retention probes. They cannot find an
  edge. They buy the right to size a later question instead of guessing it,
  and they are the cheapest line items here by an order of magnitude.
* **Tier C — new populations where the price plausibly differs.** NCAAF team
  markets: 880 FBS games a season against 272, a price region the NFL data
  contains one game of, and a free open-and-close series four times deeper
  than nflverse's.
* **Tier D — anything that needs the model to forecast better than the
  market.** Bottom of the list, always, on this evidence. Items in this tier
  are listed for completeness and are not recommended.

### Corrections to the survey this plan was built from

The survey supplied to me cites artifacts that **do not exist in this
repository**. I checked each by path:

* `scripts/run_team_ladder_backtest.py` — **missing**. The quoted
  "−9.8% over 54,641 bets" team-ladder result has no file behind it.
* `data/outputs/nfl_team_ladder_backtest.md` — **missing**.
* `data/outputs/nfl_correlation_check.md` and
  `src/football_betting_lab/reports/correlation.py` — **missing**. The claim
  that "the model's joint is accurate to 0.014–0.043 on held-out data" has
  never been measured here. Two proposals rested on it; both are re-gated
  below on measuring it first, which is free.
* `scripts/check_parlay_pricing.py` — **missing**. The 15–30% SGP hold figure
  is not a measurement this lab holds.

Second: the survey treats `tackles_assists` as "the lab's only surviving
signal" and proposes `player_solo_tackles` as a replication of it. **It is a
settlement artefact.** nflverse records about half a tackle per player-game
fewer than the books settle on; the featured market is priced 50% over across
6,575 wagers and lands over 42% of the time; that gap is worth 15% to a model
that takes the under, which it does 86% of the time, and the measured return
is +11.7%. Solo tackles settle from **the same nflverse feed**, so buying them
would most likely reproduce the offset rather than test it. That item is
demoted from third to twelfth.

Third: `data/processed/half_scores.csv` holds **1,087 games (2022–2025)**, not
"3,167 team-games back to 2015" — the 3,167 is `team_games.csv`, which is
game-level and runs through the 2026 schedule. It covers all 816 bought
events, so the free half tests below are fine; the provenance sentence was
wrong.

**And one contradiction inside this repo, found while checking the above.**
`CLAUDE.md` records recency weighting as *"measured, does not ship"* — paired
+1.4%, interval −1.0% to +3.9% over 172 games — while
`data/outputs/nfl_props_recency_experiment.md` reports the paired difference as
+2.3%, interval +0.1% to +4.5% over 256 games, and says *"It ships."* Those
cannot both be current. `CLAUDE.md` wins by its own first paragraph, so the
operating state is *does not ship*, but the two files should be reconciled
before either number is cited again. Nothing in this plan depends on it; it is
counted as one spent degree of freedom either way.

### The window constraint, which applies to every item on this list

`CLAUDE.md` records the defect found on 2026-08-31: **every bought price is at
T−60, T−360 or T−5, and the card runs at 14:00 UTC — T−180 for a 13:00 ET
kickoff.** Measured directly from the file stamps: 2,445 snapshots, three per
event on 813 of 816 events, at leads of **~360, ~60 and ~5 minutes**. Nothing
was bought at the card's own window.

That constrains everything below, and it constrains Tier A hardest, because a
price relation is a fact about an instant. **Any residual, dispersion or
arbitrage figure must be reported per snapshot, and the only bought snapshot
outside the inactives window (T−90) is T−360 — which is three hours earlier
than the card.** A finding that exists only at T−5 is a finding about a window
this lab's card cannot reach. F1 below shows exactly that pattern and it is
the reason F1 reads negative.

### The degrees-of-freedom tally, and why the fifty-third test is not the first

Every hypothesis tested against the bought population spends a degree of
freedom, and the bought population **cannot grow** — 816 events is every NFL
game for which the provider serves historical props.

Committed hypotheses already spent on it: 18 markets in replication, 3 in the
closing-line backtest, 3 half markets, 12 pre-registered subgroups
(`docs/preregistered_subgroup_search.md`), 1 recency variant, 1 forecast-skill
comparison. Call it **38**. This plan proposes **15 new hypotheses** — three
free tests (F1, F2, F3) plus the twelve numbered items; F4, F5 and F6 are
preconditions, not tests, and spend nothing. That reaches **~53**.

| Test number in the family | Two-sided z | Bets to separate a true +5% edge from zero | +8% | +10% | +15% |
|---:|---:|---:|---:|---:|---:|
| 1st (uncorrected) | 1.960 | 1,540 | 600 | 385 | 171 |
| 15th | 2.935 | 3,454 | 1,346 | 863 | 383 |
| 53rd | 3.307 | 4,384 | 1,708 | 1,096 | 487 |

A full NFL season at three qualifying bets a game is roughly **800 bets**. So
the fifty-third hypothesis in this lab **cannot be settled by an NFL season**
for any true edge below about +12%. **The correction for the fifty-third test
is not the correction for the first: it demands 2.85× the sample.** That
arithmetic is the strongest argument in this document both *for* looking at an
880-game league and *against* running another dozen searches on 816 NFL
events.

**Every item below is numbered so the family is fixed in advance.** A search
whose width is decided afterwards has no honest correction at all.

---

## 2. The ranked plan

Costs are **pessimistic bounds** (every asked market quoted and billed). The
per-event endpoint bills only markets returned, so real spend lands lower —
the tier-1 probe came in at 79% of bound. Quota context: **100,000 per calendar
month**, shared with the NHL lab; **4,473,866 credits remaining** in the pool
(`CLAUDE.md`). Historical prices bill **10× live**.

| # | Item | What it tests | Credits | % of a 100k month | % of 4.47M | Confidence | Data we do not have |
|--:|:---|:---|---:|---:|---:|:---|:---|
| **F1** | Cross-book arbitrage census, bought team markets | Whether best-of-N over + best-of-N under ever sums under 1.00 | **0** | 0% | 0% | **measured — see §4, negative** | none |
| **F2** | Book-internal coherence census | Whether one book's team totals, game total, spread and H1 total contradict each other | **0** | 0% | 0% | plausible | none |
| **F3** | Subtraction-implied H2 line | Whether the book's H1/game-total split is a bettable rule | **0** | 0% | 0% | **measured — see §4, negative** | none |
| **F4** | Joint/copula accuracy on `player_game_logs.csv` | Precondition for #7; never measured here despite being cited | **0** | 0% | 0% | precondition | none |
| **F5** | Build `quarter_scores.csv` from PBP | Precondition for #8; settlement only, no prices owned | **0** | 0% | 0% | precondition | none |
| **F6** | P(first TD \| any TD) vs the bought anytime board | Precondition for #11 | **0** | 0% | 0% | precondition | none |
| **1** | NFL tier-2 retention probe, 20 events | Whether 37 never-requested provider keys are retained at all | 16,620 as the script stands; **7,420** with a `--only-new` flag | 16.6% / 7.4% | 0.37% / 0.17% | information, near-certain to return an answer | none |
| **2** | CFBD free open→close instrument, ~11,000 college games | CLV measurable at zero credits; kills or supports the whole college thesis | **0** | 0% | 0% | plausible | free CFBD key; **a new repo** (CLAUDE.md forbids NCAAF here) |
| **3** | NCAAF retention + book-count probe, 20 events × 27 team keys | Do books hang team ladders on non-marquee college games, and how many | 5,420 | 5.4% | 0.12% | information | new repo; CFBD game list |
| **4** | NCAAF bulk historical featured snapshots, 2020-25 | Cross-book dispersion as a measured covariate, not a story | 54,000–81,000 | 54–81% | 1.21–1.81% | plausible | `fetch_historical_bulk()` (~40 lines, does not exist); college name map keyed on CFBD ids |
| **5** | NCAAF forward team-market ledger | Forward evidence at 3.2× NFL games/season; cannot be back-dated | ~6,300/season (1 snap), ~12,600 (2) | 6.3% / 12.6% | 0.14% / 0.28% | plausible | new repo; third hand-port of the six NHL fixes |
| **6** | NCAAF book-internal consistency (`team_totals`) | Tier A, in a league with more games per trader | ~27,200 (1 snap) | 27% | 0.61% | speculative | gated on #3 |
| **7** | NFL composite yardage props off **book** marginals | A straight-bet-hold instrument for an accurate joint | 27,200 (2025) / 81,600 (3 seasons) | 27% / 82% | 0.61% / 1.82% | speculative | gated on **F4** and #1 |
| **8** | NFL quarter ladder (20 keys) | Do four quarter lines cohere with the game line already owned | 34,000–54,400 (2025) | 34–54% | 0.76–1.22% | speculative | gated on #1 and F5 |
| **9** | NFL directly-hung H2 markets | Whether a hung H2 differs from the subtraction | 8,160 (2025) | 8.2% | 0.18% | weak — F3 already returned no demonstrated edge | gated on #1 |
| **10** | NCAAF mismatch-tail ladders (spread ≥ 21, total ≥ 65) | A price region the NFL data holds **one game** of | 27,000–54,000 | 27–54% | 0.60–1.21% | speculative — **Tier D**, needs a forecast in a league with no fitted model | gated on #2, #3, #4 |
| **11** | NFL first/last TD scorer | Whether the board is a flat normalisation of anytime | 5,440 (2025) | 5.4% | 0.12% | long-shot — 20–30% overround swallows it | gated on F6 and #1 |
| **12** | NFL `solo_tackles` / `pats` | Reframed: an **artefact test**, not a replication | 10,880 (2025) | 10.9% | 0.24% | **do not buy as an edge test** | none, and that is the problem — same nflverse settlement source |
| — | NCAAF **player** props | — | — | — | — | **out of scope by Cooper's instruction.** Team markets only. |

**Forward evidence has a date on it.** NFL Week 1 is **2026-09-09** — nine
days — and nothing in the forward ledger can be back-dated: a Sunday not
captured is gone. The 2026 college season has been running since **2026-08-29**,
so item #5 is already losing ~60 games a Saturday to the absence of a repo to
put them in. Items #1–#4 and every free item are retrospective and have no
clock; #5 is the only one where waiting costs evidence rather than credits.

**Everything free runs before anything paid.** Total paid spend if items 1–5
all proceed: **73,140–115,640 credits — between three-quarters and one and a
sixth of a single month's quota, 1.6–2.6% of the pool.** Items 6–12 together
are another **~139,900**, and none of them should be bought before the gate
above it has returned.

---

## 3. The top three, in detail

### #F2 — Book-internal coherence census (free, NFL, largest unexplored surface)

**What it tests.** A book's spread S and total T determine its own team totals
exactly: home = (T+S)/2, away = (T−S)/2. Its H1 total and the game total are
bound by a share it chooses. Its alternate ladder, integrated, must reproduce
its own featured number. Where these are priced by separate feeds or separate
desks they disagree, and a disagreement is a two-sided position in the book's
own quotes with **no opinion about football in it**. This is the only Tier A
test with a population already paid for.

**Why it is first.** It needs no forecast, no purchase and no new data. It is
the one item on this list whose failure mode is not "the model is bad".

**The population exists — I checked.** Over the 12,225 bought price files
(2,446 event-snapshots; three per event at T−360, T−60 and T−5 on 813 of 816
events):

| Same book, same event, same snapshot | Triples |
|:---|---:|
| quotes all four of `team_totals`, `alternate_totals`, `alternate_spreads`, `totals_h1` | **7,521** |
| quotes `team_totals` **and** `alternate_totals` | 11,574 |
| quotes `alternate_totals` **and** `totals_h1` | 12,256 |
| touches any of the four | 22,444 |

**Exact first command** (runs today, spends nothing, ~2 minutes):

```
PYTHONPATH=src ./.venv/bin/python -c "
import json,glob,collections,os
need={'team_totals','alternate_totals','alternate_spreads','totals_h1'}
seen=collections.defaultdict(set)
for f in glob.glob('data/raw/nfl/historical_prices/*_*_*.json'):
    ev,ts,_=os.path.basename(f).split('_')
    for b in json.load(open(f)).get('bookmakers',[]):
        for m in b['markets']:
            if m['key'] in need: seen[(ev,ts,b['key'])].add(m['key'])
c=collections.Counter(frozenset(v) for v in seen.values())
print('triples quoting all four:',sum(n for k,n in c.items() if need<=k))
print('triples touching any:',len(seen))
"
```

**Then** commit it as `scripts/run_book_coherence.py` writing
`data/outputs/nfl_book_coherence.md`. Pre-register before looking at any
residual: the identity, the residual threshold in probability points, the
snapshot it is claimed at, and the stake rule. **Report every residual at all
three snapshots separately** — F1's negative-pair rate more than doubles from
T−360 to T−5, and a coherence result that exists only at T−5 is about a window
the card cannot reach. The bar it must clear is the **two-way overround at the
best of N** — measured below at 4.25–4.55% for these markets. A residual
smaller than that is a located rule, not a bet, and the report must say so in
those words.

---

### #1 — NFL tier-2 retention probe (7,420–16,620 credits; 7–17% of one month)

**What it tests.** The purchase manifest carries exactly one market fingerprint
— the 46 tier-1 per-event keys. Confirmed from the registry:
`per_event_provider_keys(2)` is 83 keys, so **37 keys have never once been
requested**, plus the 4 deferred H1-ladder keys and `player_tds_over`. Their
retention is **unknown**, which is not the same as absent. This is the
`total_2_5` error class the retention-probe module exists to prevent, and
every downstream NFL item (#7, #8, #9, #11) is unsizeable without it.

**Why it is second.** It cannot find an edge and does not pretend to. It buys,
for under a fifth of one month's quota, the distinction between "the provider
does not offer this" and "we never asked" for 42 keys at once — against
27,200–98,000 for any single blind purchase.

**Exact first command** (dry run — spends nothing, prints the bound and the
20 stratified events):

```
cd /Users/cooperross/Projects/football-betting-lab && PYTHONPATH=src ./.venv/bin/python scripts/run_retention_probe.py --tier 2 --events 20 --seasons 2024 2025
```

It prints `20 event(s) x 83 market(s): at most 16,620 credits`. **Note the
inefficiency before spending:** `--tier 2` re-asks the 46 tier-1 keys whose
retention is already known, which is about 9,200 wasted credits. Add a
`--only-new` flag (drop keys already in `per_event_provider_keys(1)`) and the
bound falls to **7,420**. Do that first; it is a dozen lines in
`scripts/run_retention_probe.py`.

Then, and only with Cooper's number agreed:

```
PYTHONPATH=src ./.venv/bin/python scripts/run_retention_probe.py --tier 2 --only-new --events 20 --seasons 2024 2025 --live --credit-cap 7500
```

Carry across the two defects the tier-1 probe found: the chunk-cache filename
collision and the 32-hex event-id secrets-guard false positive.

---

### #2 — The CFBD free open→close instrument (0 credits, ~11,000 games)

**What it tests.** CollegeFootballData `/lines` carries `spread_open` **and**
`spread`, `over_under_open` **and** `over_under`, per game back to 2013 — about
11,000 games. That makes **closing-line value measurable at zero credits**.
nflverse's schedule file carries one closing line and no opening line, which is
why this lab had to spend 587,732 credits to get a CLV instrument at all. CLV
is the leading indicator the whole apparatus (`reports/clv.py`, the verdicts
door) is built to consume.

**Why it is third and not first.** It is zero credits and a 4.1× larger
population than the free NFL instrument — but it is blocked on two things this
lab does not have: a free CFBD key, and **a new repository**. `CLAUDE.md` lines
9–13 are explicit: *"Do not add college football here — not a registry entry,
not an adapter, not a season calendar."* That is Cooper's call, and it carries
the stated price of a third hand-port of the six NHL fixes.

**Exact first command** (run in the **new** repo, after obtaining a free key at
collegefootballdata.com/key and putting it in a gitignored `.env` — never on a
command line, never in a URL):

```
curl -sS -H "Authorization: Bearer $CFBD_API_KEY" \
  "https://api.collegefootballdata.com/lines?year=2024&seasonType=regular" \
  -o cfbd_lines_2024.json && head -c 2000 cfbd_lines_2024.json
```

**The trap, which is exactly the `total_2_5` class.** The four `provider`
values are Caesars, consensus, numberfire and teamrankings. **numberfire and
teamrankings are model outputs, not prices.** Filter to `consensus` and
`Caesars` or the backtest grades a model against another model and calls it a
market. Verify the provider list from the returned payload before writing a
line of settlement code; I could not verify the endpoint or its fields from
here, having no key.

**The kill condition, declared now:** if nothing predicts open-to-close
movement across ~11,000 games, the college angle dies before a single credit is
spent, and items #3–#6 and #10 are cancelled.

---

## 4. What is free and testable today — against the 5.67M rows already bought

**This section matters most.** It costs nothing, needs no approval, and three
of its six items can start in the next command. Two of them I ran while
writing this plan; their results are below.

> **These two figures are ad-hoc and not yet regenerated by a committed
> script.** That is the exact condition under which this repository's false
> "roughly centred" claim survived — `CLAUDE.md` says so. Treat both as
> provisional until they are a script writing a file under `data/outputs/`.

### F1 — Cross-book two-sided arbitrage census — **run, and negative**

Over **all 12,225 bought price files**, 2,446 event-snapshots, pairing each
two-sided team wager at the best price across every quoting book:

| Market | Two-way wagers | Best-of-N overround (median) | Consensus overround | Negative-overround pairs | Median size | Median cross-book quote-age gap | Mean books/wager | Single-quoted |
|:---|---:|---:|---:|---:|---:|---:|---:|---:|
| `alternate_spreads` | 208,496 | 4.44% | 6.23% | 542 (0.26%) | 0.58% | 1.0 min | 3.44 | 30.8% |
| `alternate_totals` | 210,847 | 4.37% | 6.52% | 288 (0.14%) | 0.69% | 0.4 min | 3.53 | 29.3% |
| `alternate_team_totals` | 85,975 | 4.25% | 5.52% | 147 (0.17%) | 0.46% | 0.3 min | 1.95 | 46.9% |
| `team_totals` | 51,175 | 4.25% | 4.34% | 50 (0.10%) | 0.77% | 1.5 min | 1.55 | 71.1% |
| `totals_h1` | 7,569 | 4.55% | 4.76% | 8 (0.11%) | 0.50% | 1.4 min | 2.27 | 51.8% |
| `spreads_h1` | 6,737 | 4.13% | 4.73% | 7 (0.10%) | 0.72% | 0.4 min | 2.73 | 36.6% |
| `h2h_h1` | 2,445 | **1.95%** | 4.42% | 68 (**2.78%**) | 0.64% | 0.5 min | **8.00** | **0.0%** |
| **total** | **573,244** | — | — | **1,110 (0.194%)** | — | — | — | — |

This independently reproduces the survey's liquidity angle to within 0.1
percentage point on every market, which is the best evidence available that
both readings of the files are correct.

**Split by snapshot, which is what the window constraint demands:**

| Snapshot | Two-way wagers | Median best-of-N overround | Negative-overround pairs |
|:---|---:|---:|---:|
| T−360 min | 190,645 | 4.29% | 219 (**0.115%**) |
| T−60 min | 191,297 | 4.29% | 364 (0.190%) |
| T−5 min | 191,302 | 4.27% | 527 (**0.275%**) |

The rate **more than doubles from six hours out to five minutes out** while the
median overround does not move. That is the signature of stale quotes near
kickoff, not of a persistent mispricing — and the card runs at T−180, closest
to the T−360 row, where the rate is lowest. A route whose frequency is 0.115%
at 0.6% of stake in the window the card actually occupies is not a route.

**The honest reading is negative.** 0.194% of wagers show a riskless-looking
two-sided price, median size **0.6% of stake**, requiring simultaneous
execution at two books, at limits nobody has measured, on quotes whose median
age gap is 0.3–1.5 minutes. A 0.6% gross edge does not survive execution risk,
and this is the cross-book arbitrage route closed with a number rather than an
opinion. **`h2h_h1` is the one interesting cell** — 8.00 books on every wager,
0% single-quoted, a 1.95% best-of-N overround against 4.42% consensus, and
2.78% of its wagers negative. It is also 2,445 wagers, which is small.

**The structural finding worth carrying:** shoppability is not a function of
how many books quote a market, it is a function of whether books have a free
line parameter to disagree about. `team_totals` is quoted by 10 books and
**71.1% of its wagers are single-quoted**, because books hang different lines —
different propositions, not competing quotes. `h2h_h1` has no line to disagree
about and every wager carries 8 books. That is why best-of-N buys 2.5
percentage points on `h2h_h1` and 0.09 on `team_totals`.

### F3 — The subtraction-implied second-half line — **run, and negative**

Books hang the H1 total at a **mean 49.60% / median 49.47%** of the closing
game total (2,445 event-snapshots, H1 line median 21.5 against a 44.0 closing
total). The realised split over the same 816 games is **50.28% H1** — H1 22.691,
H2 22.438, game 45.129 — and the two halves are near-independent (r = 0.0436),
so the lines are not hedging each other. The subtraction-implied H2 line
therefore sits about **0.3 points too high**.

Betting that rule at the **latest bought snapshot (T−5)**, one bet per game,
flat, at −110 — and note that is the most favourable window available and
still not the card's:

| Side | Bets | Won | Push | ROI | 95% interval | Verdict |
|:---|---:|---:|---:|---:|:---|:---|
| under implied H2 | 798 | 425 | 18 | **+1.67%** | −4.94% to +8.29% | **no demonstrated edge** |
| over implied H2 | 798 | 373 | 18 | −10.77% | −17.38% to −4.15% | negative |

0.3 points on a 22-point half is worth well under the vig. **The rule is real
and the bet is not**, which is the same shape as every other located structure
in this lab. It also demotes item #9: the only remaining question there is
whether a *directly hung* H2 line inherits the same error, and that is a
5-figure purchase to answer a question whose free half already returned zero.

Caveat carried: this pairs a bought H1 line at ~T−5min against nflverse's
**closing consensus** game total — two sources, two timestamps. The clean
version uses the book's own game total recovered from its `alternate_totals`
ladder, which is item F2's machinery.

### F4 — Measure the joint, since nothing here ever has

The survey's composite-props proposal (#7) rests on "the model's joint is
accurate to 0.014–0.043 on held-out data". **No such measurement exists in this
repository.** It is free to produce: `data/processed/player_game_logs.csv` is
72,457 rows and holds `pass_yards`, `rush_yards`, `reception_yards` and the
three TD columns. Measure the empirical correlation matrix walk-forward,
compare to the compound simulation's implied correlations, and report the
error per pair with the player-game count beside it. If the joint is not
accurate, #7 is cancelled and 27,200 credits are not spent.

### F5 — Build `quarter_scores.csv`

`PBP_COLUMNS` at `src/football_betting_lab/data/build_datasets.py:106` already
reads `qtr`, `play_id`, `total_home_score`, `total_away_score`. Quarter scores
are the same derivation as `build_half_scores` (line ~410) with a different
grouping — roughly 25 lines. It settles nothing on its own, because this lab
owns **no quarter prices**; it is the precondition for #8 and it is free.

### F6 — First-TD against the anytime board already owned

`td_player_id` and `play_id` are in `PBP_COLUMNS`, so P(scored first | scored
at all) is directly measurable at zero credits, and `player_anytime_td` is
bought for 816 events across 8 books (3,734 priced outcomes in the probe
sample alone). What is free: computing what a **flat normalisation** of each
book's own anytime board would imply for first-TD, and how far that sits from
the empirical conditional. What is **not** free and not knowable until #11:
whether the book's actual first-TD board is that normalisation. Do the free
half; do not buy on the strength of it alone, because touchdown-scorer boards
commonly carry 20–30% overround against ~4.4% here.

---

## 5. What would make me stop

Blunt, because the alternative is a plan that can never be wrong.

**The single most likely outcome of everything above is "no demonstrated
edge".** That is what 0 of 18 markets, 0 of 3 closing-line markets, a Brier
gap of 0.034 over 74,345 bets, and three retracted findings predict. Nothing
in this document is a reason to expect otherwise; it is a sequence for finding
out cheaply and in the right order.

Specific stop conditions, declared now so they cannot be renegotiated later:

1. **If F2 finds book-internal residuals whose median is below the best-of-N
   overround at the T−360 snapshot** (4.29% median there, measured above —
   T−360 being the only bought window outside the inactives deadline and the
   nearest one to the card's T−180), there is no price-against-price trade in
   the NFL team board. Combined with F1's 0.194% at 0.6%, **the entire Tier A
   route in the NFL is closed**, and every
   remaining NFL item is Tier D — a forecast this model has been measured six
   ways as unable to make (forecast skill, replication, price sensitivity,
   null baseline, settlement screen, closing line). **Stop buying NFL history
   at that point.**
2. **If the CFBD open→close test finds nothing across ~11,000 games**, cancel
   items #3, #4, #5, #6 and #10. That is ~120,000 credits not spent on a
   thesis that failed its free gate.
3. **If the NCAAF probe returns fewer than four books on non-marquee games and
   no alternate or team-total ladders**, the dispersion thesis is unbuyable at
   size regardless of whether an edge exists. Learn it for 5,420 credits, not
   after the 81,000-credit purchase.
4. **If item #1 finds the 37 keys are thinly retained** — two books, a handful
   of events — items #7 through #11 are not "unknown", they are unmeasurable,
   and they come off the list permanently.
5. **If, after a full 2026 forward season, the ledger shows pooled CLV at or
   below zero and no market's family-corrected interval excludes zero**, this
   lab should not bet at all. Forward evidence is the only instrument immune
   to the multiple-comparisons problem that killed the retrospective searches;
   if it agrees with them, the answer is settled.
6. **The degrees-of-freedom stop.** If items 1–12 run and none clears its
   Bonferroni-corrected bar at k≈53, the honest conclusion is not "test
   sixteen". It is that these markets are efficient to the resolution this lab
   can measure. At k=53 a true +5% edge needs **4,384 bets** to separate from
   zero — five and a half NFL seasons at three bets a game. **A plan that
   proposes a fifty-fourth test is proposing something no available sample can
   settle**, and this document is bounded at fifteen for that reason.

**The thing that would most cheaply prove this lab should not bet at all** is
already half-run: F1 says cross-book arbitrage in NFL team markets is 0.194%
of wagers at 0.6% of stake — and **0.115% in the window nearest the card** —
and F3 says the one located pricing rule is worth less than its vig. If F2
returns the same shape — a real relation, smaller than the hold — then the NFL
board is internally consistent to within its own
margin, this lab's model cannot out-forecast it, and there is nothing left in
the NFL to bet on. The only honest moves then are the free forward ledger from
2026-09-09, and a decision about college that rests on its own free evidence
rather than on this lab's disappointment.