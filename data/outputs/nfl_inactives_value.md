# What is knowing the inactives worth?

This lab refuses to let any player prop produce a selection, because **inactives are declared ninety minutes before kickoff and the card runs three hours out**. That premise has been argued about for weeks and never measured — and it turns out the evidence was bought and then never read.

Three snapshots exist per event: **T-360** (blind to inactives, and what every backtest used), **T-60** (inside the window, labelled `mid`, read by nothing), and T-6. The middle one is a third of the snapshot spend and the only direct evidence about the gate's own premise.

| Market | Wagers | Mean price move | Brier T-360 | Brier T-60 | Gain |
|:---|---:|---:|---:|---:|---:|
| `pass_yards` | 5,275 | 0.0099 | 0.22348 | 0.22263 | +0.00085 |
| `field_goals` | 383 | 0.0089 | 0.24097 | 0.24024 | +0.00073 |
| `rush_yards` | 9,541 | 0.0120 | 0.23559 | 0.23523 | +0.00036 |
| `pass_interceptions` | 612 | 0.0079 | 0.24282 | 0.24254 | +0.00029 |
| `pass_tds` | 851 | 0.0081 | 0.21515 | 0.21488 | +0.00028 |
| `rush_attempts` | 3,282 | 0.0145 | 0.22483 | 0.22460 | +0.00023 |
| `reception_yards` | 22,318 | 0.0104 | 0.22385 | 0.22366 | +0.00020 |
| `receptions` | 8,532 | 0.0123 | 0.21740 | 0.21727 | +0.00013 |
| `pass_longest_completion` | 598 | 0.0035 | 0.24854 | 0.24842 | +0.00012 |
| `pass_attempts` | 1,734 | 0.0102 | 0.23427 | 0.23415 | +0.00012 |
| `anytime_td` | 1,734 | 0.0104 | 0.17618 | 0.17607 | +0.00011 |
| `sacks` | 1,043 | 0.0072 | 0.22225 | 0.22217 | +0.00008 |
| `pass_completions` | 1,646 | 0.0110 | 0.22903 | 0.22900 | +0.00004 |
| `rush_longest` | 1,884 | 0.0055 | 0.24875 | 0.24885 | -0.00011 |
| `tackles_assists` | 3,716 | 0.0149 | 0.23944 | 0.23958 | -0.00013 |
| `kicking_points` | 698 | 0.0075 | 0.24124 | 0.24156 | -0.00032 |
| `reception_longest` | 5,133 | 0.0081 | 0.23885 | 0.23918 | -0.00033 |

**The later price is materially better in only 0 of 17 markets**, against a threshold of 0.002 declared in advance. Crossing the inactives deadline buys the market very little, so the gate costs very little — and the case for reorganising a card around it is weak.

**82,810 wager(s) present at T-360 had no price at T-60** and were dropped by the join. That is not noise: a player who is scratched loses his market, so the dropped rows are enriched in exactly the players this question is about. Every figure above is therefore conditioned on the wager still existing an hour out.

**This is an upper bound on what inactives are worth, not a measurement of them.** Five hours of steam, weather and late news move a line too, and nothing here separates them. A large gap could be any of those; a small gap is the more informative result, because nothing can be hiding inside it.
