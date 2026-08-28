#!/usr/bin/env python3
"""Bet every priced selection with no model at all. Spends nothing.

    PYTHONPATH=src python scripts/run_null_baseline.py

**This is the test that says whether a backtest can be believed.** A sound
harness returns roughly the vig here — clearly negative. If betting
everything makes money, the fault is in the settlement, the prices or the
join, and no result computed on top of it means anything.

It also produces the number every market ROI has to be read against. The
baseline is not flat across seasons: 2023 returns -5.2%, 2024 -8.3%, 2025
-12.8%, because the price samples differ in how soft they are. A market whose
ROI falls by seven points between two seasons may simply be sitting on a
baseline that fell by seven points, and comparing raw ROIs across seasons
without this is comparing two different questions.
"""

import pandas as pd
from football_betting_lab.leagues import NFL
from football_betting_lab.providers.historical import CACHE_DIRNAME
from football_betting_lab.config import RAW_DIR, PROCESSED_DIR
from football_betting_lab.reports.props_backtest import (load_bought_prices, label_snapshots,
    best_price_per_selection, _game_weeks, _game_id)
from football_betting_lab.providers.team_names import name_to_abbreviation, resolve_team
from football_betting_lab.forward_evidence import profit_on_win
from football_betting_lab.markets import MARKETS_BY_KEY

logs=pd.read_csv(PROCESSED_DIR/'player_game_logs.csv', low_memory=False)
# index once; the per-row scan is what made this slow before
log_index={}
for r in logs.itertuples():
    log_index.setdefault((str(r.game_id), str(r.player_name).casefold()), r)

p=best_price_per_selection(label_snapshots(load_bought_prices(RAW_DIR / NFL.data_dir_segment / CACHE_DIRNAME, NFL)))
p=p[p.phase=='card'].copy()
props={k for k,v in MARKETS_BY_KEY.items() if v.kind=='player'}
p=p[p.market.isin(props)]
p['line']=pd.to_numeric(p.line, errors='coerce')
p=p.dropna(subset=['line'])
p=p[(p.american_odds>=-160)&(p.american_odds<=600)]
lk=name_to_abbreviation(NFL)
rows=[]
for season in (2023,2024,2025):
    sub=p[p.date.str[:4]==str(season)]
    weeks=_game_weeks(logs, sub, NFL, season)
    for ev, frame in sub.groupby('event_id'):
        wk=weeks.get(str(ev))
        if wk is None: continue
        f=frame.iloc[0]
        home=resolve_team(f['home_team'],NFL,lk) or ''; away=resolve_team(f['away_team'],NFL,lk) or ''
        gid=_game_id(logs, season, wk, home, away)
        for row in frame.itertuples():
            e=log_index.get((gid, str(row.player).casefold()))
            if e is None or not hasattr(e, row.market): continue
            actual=float(getattr(e, row.market)); line=float(row.line)
            if actual==line: profit=0.0
            else:
                over=actual>line
                won=(over and row.selection=='over') or ((not over) and row.selection=='under')
                profit=profit_on_win(row.american_odds) if won else -1.0
            rows.append({'season':season,'sel':row.selection,'market':row.market,'profit':profit})
n=pd.DataFrame(rows)
import sys
from football_betting_lab.config import OUTPUTS_DIR
n.to_csv(OUTPUTS_DIR / NFL.output_name("null_baseline_bets", ".csv"), index=False)
lines = ["# The null baseline: betting everything, with no model", ""]
lines.append(
    "A sound harness returns roughly the vig here. If betting everything makes "
    "money, the fault is in the settlement, the prices or the join, and no "
    "result computed on top of it means anything."
)
lines.append("")
lines.append("| Season | Bets | ROI |")
lines.append("|:-------|-----:|----:|")
for season, group in n.groupby("season"):
    lines.append(f"| {season} | {len(group):,} | {group['profit'].mean():+.2%} |")
lines.append(f"| **all** | {len(n):,} | {n['profit'].mean():+.2%} |")
lines.append("")
lines.append(
    "**The baseline is not flat across seasons**, and that matters more than "
    "it looks: a market whose ROI falls by seven points between two seasons "
    "may simply be sitting on a baseline that fell by seven points. Raw ROIs "
    "compared across seasons without this are comparing two different "
    "questions."
)
lines.append("")
lines.append("| Season | Market | Null bets | Null ROI |")
lines.append("|:-------|:-------|----------:|---------:|")
for (season, market), group in n.groupby(["season", "market"]):
    lines.append(
        f"| {season} | `{market}` | {len(group):,} | {group['profit'].mean():+.2%} |"
    )
(OUTPUTS_DIR / NFL.output_name("null_baseline", ".md")).write_text("\n".join(lines) + "\n", encoding="utf-8")

print("NULL MODEL — every priced selection in range, no model at all:\n")
print(n.groupby(['season','sel']).agg(bets=('profit','size'), roi=('profit','mean')).round(4).to_string())
print()
print(n.groupby('season').agg(bets=('profit','size'), roi=('profit','mean')).round(4).to_string())
print(f"\nALL: {len(n):,} bets, ROI {n.profit.mean():+.2%}")
print("^ a sound harness returns roughly the vig here, i.e. clearly negative.")
