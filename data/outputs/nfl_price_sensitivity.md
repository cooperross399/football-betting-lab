# Does the edge survive at a price you could actually get?

Measured over **83,405 scored bets** on **768 games** across seasons 2023, 2024, 2025.

The backtest takes the **best available** price across every book quoting a wager, which is what a card does. But a measured edge can be three different things: a real disagreement with the market, a line-shopping premium that exists only as the maximum of N quotes, or one soft book's mistake. Those decide whether a number is a strategy, an operational requirement, or a curiosity.

The **consensus** column is the median quote per wager — the closest thing to *the* price, and the one thing shopping cannot improve.

| Market | Bets | Best of N | Consensus | Books positive | Reading |
|:-------|-----:|----------:|----------:|:---------------|:--------|
| `sacks` | 1,079 | +2.3% | -0.0% | 1/2 | mixed — -0.0% at the consensus, positive at 1 of 2 books |
| `tackles_assists` | 3,987 | +2.1% | +0.9% | 3/8 | mixed — +0.9% at the consensus, positive at 3 of 8 books |
| `rush_yards` | 11,573 | +1.2% | -0.6% | 2/10 | **a shopping premium** — -0.6% at the consensus, +1.2% at the best of 10 books, and positive at only 2 of them. The edge is the maximum of N quotes, not a disagreement with the market |
| `pass_attempts` | 1,850 | +0.1% | -2.2% | 2/8 | **a shopping premium** — -2.2% at the consensus, +0.1% at the best of 8 books, and positive at only 2 of them. The edge is the maximum of N quotes, not a disagreement with the market |
| `anytime_td` | 1,740 | -0.5% | -12.2% | 0/10 | **loses at every price** — -12.2% at the consensus and -0.5% even at the best of 10 books. There is no price at which this market was profitable, so there is nothing to shop for |
| `pass_longest_completion` | 658 | -0.6% | -1.4% | 0/0 | no book quoted enough of this market to say |
| `rush_longest` | 2,014 | -3.4% | -4.5% | 0/5 | **loses at every price** — -4.5% at the consensus and -3.4% even at the best of 5 books. There is no price at which this market was profitable, so there is nothing to shop for |
| `field_goals` | 385 | -3.5% | -5.3% | 0/0 | no book quoted enough of this market to say |
| `reception_longest` | 5,800 | -3.5% | -4.3% | 0/7 | **loses at every price** — -4.3% at the consensus and -3.5% even at the best of 7 books. There is no price at which this market was profitable, so there is nothing to shop for |
| `receptions` | 8,666 | -4.7% | -8.6% | 0/10 | **loses at every price** — -8.6% at the consensus and -4.7% even at the best of 10 books. There is no price at which this market was profitable, so there is nothing to shop for |
| `pass_interceptions` | 613 | -5.2% | -8.4% | 0/5 | **loses at every price** — -8.4% at the consensus and -5.2% even at the best of 5 books. There is no price at which this market was profitable, so there is nothing to shop for |
| `pass_yards` | 6,937 | -5.2% | -6.9% | 0/8 | **loses at every price** — -6.9% at the consensus and -5.2% even at the best of 8 books. There is no price at which this market was profitable, so there is nothing to shop for |
| `reception_yards` | 26,028 | -5.9% | -7.7% | 0/11 | **loses at every price** — -7.7% at the consensus and -5.9% even at the best of 11 books. There is no price at which this market was profitable, so there is nothing to shop for |
| `kicking_points` | 742 | -6.3% | -7.8% | 0/3 | **loses at every price** — -7.8% at the consensus and -6.3% even at the best of 3 books. There is no price at which this market was profitable, so there is nothing to shop for |
| `pass_completions` | 1,753 | -7.4% | -9.7% | 0/7 | **loses at every price** — -9.7% at the consensus and -7.4% even at the best of 7 books. There is no price at which this market was profitable, so there is nothing to shop for |
| `rush_attempts` | 3,527 | -7.8% | -10.9% | 1/8 | **loses at every price** — -10.9% at the consensus and -7.8% even at the best of 8 books. There is no price at which this market was profitable, so there is nothing to shop for |
| `pass_tds` | 861 | -8.2% | -12.2% | 0/7 | **loses at every price** — -12.2% at the consensus and -8.2% even at the best of 7 books. There is no price at which this market was profitable, so there is nothing to shop for |
| `defensive_interceptions` | 40 | -42.8% | -42.7% | 0/0 | no book quoted enough of this market to say |

### `sacks` by book

| Book | Bets | ROI |
|:-----|-----:|----:|
| draftkings | 704 | +2.7% |
| betonlineag | 811 | -1.9% |

### `tackles_assists` by book

| Book | Bets | ROI |
|:-----|-----:|----:|
| betonlineag | 754 | +6.3% |
| bovada | 1,205 | +5.2% |
| draftkings | 3,369 | +0.3% |
| unibet_us | 762 | -0.7% |
| betrivers | 1,215 | -1.2% |
| betmgm | 1,450 | -2.5% |
| williamhill_us | 1,585 | -2.9% |
| barstool | 532 | -8.7% |

### `rush_yards` by book

| Book | Bets | ROI |
|:-----|-----:|----:|
| draftkings | 4,495 | +3.8% |
| betrivers | 4,797 | +2.8% |
| unibet_us | 1,315 | -1.0% |
| fanduel | 3,707 | -1.9% |
| pointsbetus | 523 | -2.6% |
| fanatics | 516 | -4.1% |
| betmgm | 2,394 | -6.0% |
| bovada | 2,635 | -6.1% |
| betonlineag | 2,853 | -6.3% |
| williamhill_us | 3,331 | -7.4% |

### `pass_attempts` by book

| Book | Bets | ROI |
|:-----|-----:|----:|
| bovada | 516 | +1.1% |
| betonlineag | 834 | +0.7% |
| betmgm | 658 | -0.6% |
| fanduel | 820 | -1.1% |
| betrivers | 784 | -1.5% |
| draftkings | 1,186 | -2.6% |
| williamhill_us | 539 | -3.0% |
| fanatics | 545 | -13.7% |

### `anytime_td` by book

| Book | Bets | ROI |
|:-----|-----:|----:|
| betonlineag | 1,070 | -6.4% |
| fanduel | 1,645 | -7.0% |
| fanatics | 558 | -9.2% |
| draftkings | 1,655 | -9.9% |
| williamhill_us | 1,604 | -11.4% |
| bovada | 1,459 | -11.5% |
| pointsbetus | 442 | -11.5% |
| betmgm | 1,441 | -13.2% |
| betrivers | 1,651 | -16.4% |
| unibet_us | 565 | -28.9% |

### `rush_longest` by book

| Book | Bets | ROI |
|:-----|-----:|----:|
| fanduel | 601 | -2.0% |
| betmgm | 992 | -2.9% |
| draftkings | 1,198 | -3.0% |
| betrivers | 1,086 | -4.3% |
| bovada | 910 | -5.7% |

### `reception_longest` by book

| Book | Bets | ROI |
|:-----|-----:|----:|
| bovada | 1,157 | -3.2% |
| betrivers | 1,984 | -3.9% |
| unibet_us | 460 | -4.1% |
| draftkings | 2,387 | -4.1% |
| fanduel | 2,850 | -4.6% |
| betmgm | 2,695 | -4.6% |
| williamhill_us | 1,818 | -6.5% |

### `receptions` by book

| Book | Bets | ROI |
|:-----|-----:|----:|
| barstool | 469 | -0.6% |
| unibet_us | 1,583 | -1.8% |
| betmgm | 3,818 | -4.5% |
| williamhill_us | 5,308 | -6.5% |
| betrivers | 6,557 | -6.7% |
| draftkings | 6,522 | -7.9% |
| bovada | 5,062 | -10.0% |
| fanduel | 7,883 | -10.7% |
| betonlineag | 7,231 | -13.6% |
| fanatics | 2,741 | -14.6% |

### `pass_interceptions` by book

| Book | Bets | ROI |
|:-----|-----:|----:|
| draftkings | 621 | -6.9% |
| fanduel | 521 | -7.4% |
| betrivers | 457 | -8.2% |
| betonlineag | 553 | -9.1% |
| betmgm | 443 | -11.9% |

### `pass_yards` by book

| Book | Bets | ROI |
|:-----|-----:|----:|
| draftkings | 2,324 | -0.3% |
| fanduel | 1,653 | -2.7% |
| betrivers | 2,848 | -3.5% |
| betmgm | 902 | -7.1% |
| bovada | 888 | -14.4% |
| williamhill_us | 1,593 | -15.3% |
| unibet_us | 712 | -15.6% |
| betonlineag | 1,336 | -22.9% |

### `reception_yards` by book

| Book | Bets | ROI |
|:-----|-----:|----:|
| barstool | 618 | -1.0% |
| pointsbetus | 920 | -1.3% |
| unibet_us | 2,536 | -3.1% |
| fanatics | 1,198 | -3.2% |
| fanduel | 10,439 | -5.6% |
| betrivers | 11,150 | -6.5% |
| betmgm | 5,227 | -7.1% |
| draftkings | 9,810 | -7.7% |
| williamhill_us | 8,171 | -9.1% |
| bovada | 6,239 | -9.3% |
| betonlineag | 6,968 | -14.0% |

### `kicking_points` by book

| Book | Bets | ROI |
|:-----|-----:|----:|
| williamhill_us | 446 | -6.5% |
| draftkings | 633 | -7.1% |
| betmgm | 403 | -8.5% |

### `pass_completions` by book

| Book | Bets | ROI |
|:-----|-----:|----:|
| betmgm | 577 | -2.1% |
| bovada | 489 | -5.9% |
| betrivers | 901 | -6.3% |
| fanduel | 790 | -7.0% |
| williamhill_us | 510 | -8.4% |
| draftkings | 1,016 | -9.2% |
| betonlineag | 1,133 | -11.8% |

### `rush_attempts` by book

| Book | Bets | ROI |
|:-----|-----:|----:|
| bovada | 732 | +0.3% |
| fanduel | 1,321 | -0.7% |
| betmgm | 1,562 | -3.0% |
| betrivers | 1,120 | -4.8% |
| williamhill_us | 1,152 | -6.4% |
| draftkings | 1,806 | -7.1% |
| fanatics | 751 | -12.4% |
| betonlineag | 1,762 | -25.5% |

### `pass_tds` by book

| Book | Bets | ROI |
|:-----|-----:|----:|
| fanduel | 847 | -8.9% |
| draftkings | 742 | -10.4% |
| betmgm | 475 | -12.1% |
| williamhill_us | 708 | -12.2% |
| betonlineag | 680 | -12.2% |
| betrivers | 794 | -12.4% |
| bovada | 498 | -16.4% |

A book needs 400 bets in a market before its ROI is reported; below that the number is noise wearing a book's name.
