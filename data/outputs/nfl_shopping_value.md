# What line shopping is worth, with no model at all

1,990,728 two-sided book quotes across 737,690 wagers, 13 books.

## The hold, as the number of books rises

Books are drawn at random from those quoting each wager, so this answers *what if I held accounts at N books* rather than *what if I held accounts at the N that turned out best* — a question nobody can act on, and one that would understate the hold at every N.

| books | median hold | mean hold | wagers | what betting blind returns |
|--:|--:|--:|--:|--:|
| 1 | 6.78% | 6.82% | 737,690 | -6.35% |
| 2 | 5.65% | 5.38% | 433,063 | -5.35% |
| 3 | 4.78% | 4.68% | 288,131 | -4.57% |
| 4 | 4.46% | 4.21% | 220,727 | -4.27% |
| 5 | 3.96% | 3.78% | 152,580 | -3.81% |
| 6 | 3.53% | 3.40% | 91,071 | -3.41% |
| 7 | 3.33% | 3.17% | 50,862 | -3.22% |
| 8 | 3.27% | 3.08% | 14,326 | -3.17% |
| 9 | 2.38% | 2.42% | 2,104 | -2.33% |
| 10 | 2.07% | 2.10% | 174 | -2.03% |

**Shopping every book cuts the median hold from 6.78% to 2.07%** — it recovers **4.70 points**. Betting blind goes from -6.35% to -2.03%.

## What that settles

**The hold is the model-free expected loss.** A book pricing both sides proportionally to the fair probability leaves `-h / (1 + h)` on either side, so a bettor with no opinion at all loses the hold and nothing else. Shopping does not add anything to a bet; it lowers the hold, and it can only lower a loss.

**The hold stays positive at every book count**, so shopping is a cost reduction and cannot make a losing strategy win. The 4.70 points it recovers is the whole of the best-of-N advantage seen in `nfl_price_sensitivity.md`; there is no residual edge underneath it to chase. To profit, a model still has to beat the price by more than 2.07% — and this lab's does not beat it at all.

## Wagers where the two best quotes cross

**4,717 of 737,690 wagers** (0.639%) have a best over and a best under that sum to no more than one — after **9 implausible quotes** were removed, every one of them FanDuel on `alternate_total_points` where three other books had the over at +366 to +400 and it had -295. Nine bad rows in 1.4 million is provider noise, but they land entirely here and would otherwise have been this section's headline at -48%.

A crossed pair is a claim about free money and every boring explanation has to be excluded before it is anything else: the two quotes are paired here on event, market, player, line **and** snapshot, so they are the same product at the same moment. What that pairing cannot establish is whether both were still on the screen when the second was taken, whether either book would have accepted a stake, or whether the price was an error the book would void. **Nothing here should be read as an executable strategy**, and this lab does not place bets.

| size of the crossing | wagers | share |
|:--|--:|--:|
| worse than -10% | 9 | 0.2% |
| -10% to -5% | 45 | 1.0% |
| -5% to -2% | 354 | 7.5% |
| -2% to -0.5% | 1,386 | 29.4% |
| -0.5% to 0 | 2,923 | 62.0% |

**The median crossing is -0.24%**, and most of them are within half a point of not crossing at all. An edge that size is inside the noise of actually placing the two bets: the lines move, the stakes are limited, and both quotes have to still be there when the second is struck. It is arbitrage-**shaped** and it is not a strategy.

Most common in `receptions` (1,653), `alternate_total_points` (554), `reception_yards` (433), `tackles_assists` (388).
