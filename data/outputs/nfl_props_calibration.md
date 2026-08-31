# Are the prop distributions the right shape?

Fitted on seasons before 2025, scored on 2025. Walk-forward: the fit never sees the season it is judged on.

**Calibration can rule a model out. It can never rule one in.** Everything below is a statement about the model's internal coherence. Whether the market disagrees with it profitably is a different question and no number here answers it.

Each row is a randomised probability integral transform, in deciles. A correct distribution puts **10% in every bucket**; the shape of any departure names the defect.

## Receiving

Scored on **1,248 player-games**.

| Quantity | d1 | d2 | d3 | d4 | d5 | d6 | d7 | d8 | d9 | d10 | mean | Verdict |
|:---------|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|:--------|
| `receptions` | 7.3 | 13.2 | 12.4 | 11.5 | 10.8 | 11.1 | 9.0 | 8.7 | 6.9 | 9.1 | 0.474 | no material departure from flat |
| `reception_yards` | 8.3 | 10.4 | 12.2 | 11.6 | 11.4 | 10.8 | 9.6 | 9.2 | 7.5 | 9.0 | 0.482 | no material departure from flat |
| `reception_longest` | 7.5 | 11.3 | 11.3 | 10.6 | 10.7 | 11.7 | 10.0 | 11.2 | 7.7 | 8.0 | 0.490 | no material departure from flat |

## Rushing

Scored on **1,193 player-games**.

| Quantity | d1 | d2 | d3 | d4 | d5 | d6 | d7 | d8 | d9 | d10 | mean | Verdict |
|:---------|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|:--------|
| `rush_attempts` | 11.6 | 9.0 | 10.6 | 11.8 | 10.1 | 8.5 | 10.9 | 7.5 | 9.6 | 10.4 | 0.486 | no material departure from flat |
| `rush_yards` | 15.2 | 9.8 | 8.9 | 8.0 | 8.5 | 9.8 | 10.8 | 9.8 | 8.1 | 11.1 | 0.484 | too narrow — the tails arrive more often than priced |
| `rush_longest` | 14.8 | 9.1 | 8.5 | 8.7 | 9.1 | 9.1 | 10.6 | 10.6 | 10.0 | 9.3 | 0.484 | no material departure from flat |

## Passing

Scored on **526 player-games**.

| Quantity | d1 | d2 | d3 | d4 | d5 | d6 | d7 | d8 | d9 | d10 | mean | Verdict |
|:---------|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|:--------|
| `pass_completions` | 15.8 | 7.0 | 9.5 | 7.6 | 9.1 | 12.4 | 10.8 | 9.3 | 8.9 | 9.5 | 0.479 | no material departure from flat |
| `pass_yards` | 14.8 | 8.6 | 8.9 | 8.2 | 8.7 | 9.1 | 10.8 | 11.2 | 11.4 | 8.2 | 0.487 | no material departure from flat |
| `pass_longest_completion` | 11.2 | 9.5 | 9.7 | 9.9 | 11.4 | 8.9 | 11.0 | 10.8 | 8.6 | 8.9 | 0.487 | no material departure from flat |

## What the three families say together

**All 9 of 9 quantities have a mean PIT below 0.5**, so the model is centred above the outcomes everywhere it was measured — it expects a little more than happens.

That is 9 numbers and **3 of 3 independent observations**. Within a family, opportunities, yards and longest are read off one simulation, so they lean together almost by construction; counting them as nine would be counting one thing nine times. Three families leaning the same way is what a coin does one time in eight. **Not enough to call it systematic**, and recorded so the next season's run can say whether it persisted.

**Excess mass in the lowest decile** on `rush_yards` (15.2%, Rushing), `rush_longest` (14.8%, Rushing), `pass_completions` (15.8%, Passing), `pass_yards` (14.8%, Passing) — very low outcomes happen more often than the model allows. That is the shape a missing mechanism makes, and this model is missing the obvious one: **nothing here knows a player's day can be cut short.** Blowouts empty benches, injuries end afternoons, and a benched starter's line looks like a player who was never going to get the ball. The model is unconditional on game state and says so; this is what that costs, measured.

A mean below 0.5 means the model is centred above the outcomes — it expects more than happens. Sample sizes are beside every figure, and a decile histogram from a thousand games is itself noisy at the one-point level.
