# Does the team model beat the closing line?

Walk-forward over 2016-2025, 2,639 games scored, betting only where the model disagrees with the close by at least 3.5% and the price is no worse than -160.

**This is a conservative test in two directions at once.** It bets into the close, which is the sharpest price of the week; and it uses one consensus line rather than the best of the nine books the retention probe found quoting these games. A card does neither. So a positive result here is stronger than it looks, and a negative one is not proof a card would lose — it is proof the model does not beat the closing consensus.

**Closing-line value cannot be measured here at all**, because the bet is placed at the close. CLV needs the bought snapshots.

| Market | Bets | Games | Won | Push | ROI | 95% interval | Family-corrected | Verdict |
|:-------|-----:|------:|----:|-----:|----:|:-------------|:-----------------|:--------|
| `moneyline` | 1,923 | 1,923 | 622 | 5 | -6.2% | -12.9% to +0.4% | -14.4% to +1.9% | **no demonstrated edge** |
| `spread` | 1,886 | 1,886 | 932 | 46 | -1.9% | -6.3% to +2.4% | -7.2% to +3.3% | **no demonstrated edge** |
| `total_points` | 1,708 | 1,708 | 856 | 14 | -1.8% | -6.4% to +2.8% | -7.4% to +3.8% | **no demonstrated edge** |

Intervals are clustered by game — the three markets on one game are one afternoon seen three ways, and a naive per-bet interval over correlated bets is narrower than the truth. The family correction is Bonferroni across the 3 market(s) with enough bets to report, applied because with three markets something will look profitable by chance.

**200 bets** is the minimum declared in advance. Below it the verdict is *not enough evidence* and not a number, however good the number looks.
