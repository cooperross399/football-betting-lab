# Does the edge survive at a price you could actually get?

Measured over **83,947 scored bets** on **768 games** across seasons 2023, 2024, 2025.

The backtest takes the **best available** price across every book quoting a wager, which is what a card does. But a measured edge can be three different things: a real disagreement with the market, a line-shopping premium that exists only as the maximum of N quotes, or one soft book's mistake. Those decide whether a number is a strategy, an operational requirement, or a curiosity.

The **consensus** column is the median quote per wager — the closest thing to *the* price, and the one thing shopping cannot improve.

| Market | Bets | Best of N | Consensus | Books positive | Reading |
|:-------|-----:|----------:|----------:|:---------------|:--------|
| `tackles_assists` | 4,428 | +12.0% | +10.6% | 8/8 | **survives** — +10.6% at the consensus price and positive at 8 of 8 books |
| `sacks` | 1,057 | +2.9% | +0.7% | 1/2 | mixed — +0.7% at the consensus, positive at 1 of 2 books |
| `rush_yards` | 11,565 | +0.9% | -1.0% | 2/10 | **a shopping premium** — -1.0% at the consensus, +0.9% at the best of 10 books, and positive at only 2 of them. The edge is the maximum of N quotes, not a disagreement with the market |
| `pass_longest_completion` | 644 | +0.5% | -0.5% | 0/0 | no book quoted enough of this market to say |
| `pass_attempts` | 1,863 | -0.4% | -2.6% | 2/8 | **loses at every price** — -2.6% at the consensus and -0.4% even at the best of 8 books. There is no price at which this market was profitable, so there is nothing to shop for |
| `anytime_td` | 1,750 | -2.7% | -14.1% | 0/10 | **loses at every price** — -14.1% at the consensus and -2.7% even at the best of 10 books. There is no price at which this market was profitable, so there is nothing to shop for |
| `rush_longest` | 2,004 | -3.3% | -4.4% | 0/5 | **loses at every price** — -4.4% at the consensus and -3.3% even at the best of 5 books. There is no price at which this market was profitable, so there is nothing to shop for |
| `reception_longest` | 5,854 | -3.3% | -4.1% | 0/7 | **loses at every price** — -4.1% at the consensus and -3.3% even at the best of 7 books. There is no price at which this market was profitable, so there is nothing to shop for |
| `field_goals` | 400 | -4.8% | -6.6% | 0/0 | no book quoted enough of this market to say |
| `receptions` | 8,659 | -5.0% | -8.9% | 0/10 | **loses at every price** — -8.9% at the consensus and -5.0% even at the best of 10 books. There is no price at which this market was profitable, so there is nothing to shop for |
| `pass_interceptions` | 610 | -5.1% | -8.3% | 0/5 | **loses at every price** — -8.3% at the consensus and -5.1% even at the best of 5 books. There is no price at which this market was profitable, so there is nothing to shop for |
| `pass_yards` | 6,987 | -5.5% | -7.1% | 0/8 | **loses at every price** — -7.1% at the consensus and -5.5% even at the best of 8 books. There is no price at which this market was profitable, so there is nothing to shop for |
| `reception_yards` | 26,022 | -5.7% | -7.6% | 1/11 | **loses at every price** — -7.6% at the consensus and -5.7% even at the best of 11 books. There is no price at which this market was profitable, so there is nothing to shop for |
| `kicking_points` | 739 | -6.5% | -8.0% | 0/3 | **loses at every price** — -8.0% at the consensus and -6.5% even at the best of 3 books. There is no price at which this market was profitable, so there is nothing to shop for |
| `pass_completions` | 1,738 | -6.8% | -9.2% | 0/7 | **loses at every price** — -9.2% at the consensus and -6.8% even at the best of 7 books. There is no price at which this market was profitable, so there is nothing to shop for |
| `rush_attempts` | 3,532 | -7.8% | -11.0% | 1/8 | **loses at every price** — -11.0% at the consensus and -7.8% even at the best of 8 books. There is no price at which this market was profitable, so there is nothing to shop for |
| `pass_tds` | 878 | -8.1% | -12.1% | 0/7 | **loses at every price** — -12.1% at the consensus and -8.1% even at the best of 7 books. There is no price at which this market was profitable, so there is nothing to shop for |
| `defensive_interceptions` | 43 | -34.7% | -34.7% | 0/0 | no book quoted enough of this market to say |

### `tackles_assists` by book

| Book | Bets | ROI |
|:-----|-----:|----:|
| betrivers | 1,318 | +11.5% |
| bovada | 1,441 | +11.4% |
| draftkings | 3,844 | +10.9% |
| unibet_us | 985 | +10.5% |
| betmgm | 1,817 | +10.4% |
| williamhill_us | 1,635 | +9.0% |
| betonlineag | 874 | +7.5% |
| barstool | 644 | +4.7% |

### `sacks` by book

| Book | Bets | ROI |
|:-----|-----:|----:|
| draftkings | 686 | +3.5% |
| betonlineag | 770 | -2.0% |

### `rush_yards` by book

| Book | Bets | ROI |
|:-----|-----:|----:|
| draftkings | 4,488 | +3.7% |
| betrivers | 4,789 | +2.7% |
| fanduel | 3,692 | -1.4% |
| unibet_us | 1,311 | -1.6% |
| pointsbetus | 512 | -3.8% |
| fanatics | 515 | -5.1% |
| betmgm | 2,401 | -6.2% |
| bovada | 2,629 | -6.3% |
| betonlineag | 2,835 | -7.0% |
| williamhill_us | 3,328 | -7.1% |

### `pass_attempts` by book

| Book | Bets | ROI |
|:-----|-----:|----:|
| betonlineag | 839 | +0.2% |
| bovada | 524 | +0.0% |
| betmgm | 662 | -0.8% |
| fanduel | 827 | -1.7% |
| betrivers | 790 | -2.1% |
| draftkings | 1,206 | -3.1% |
| williamhill_us | 543 | -3.3% |
| fanatics | 560 | -13.5% |

### `anytime_td` by book

| Book | Bets | ROI |
|:-----|-----:|----:|
| fanatics | 549 | -7.1% |
| betonlineag | 1,062 | -9.1% |
| fanduel | 1,659 | -9.2% |
| draftkings | 1,665 | -11.8% |
| pointsbetus | 460 | -12.3% |
| williamhill_us | 1,615 | -13.4% |
| bovada | 1,467 | -13.5% |
| betmgm | 1,450 | -15.3% |
| betrivers | 1,660 | -17.8% |
| unibet_us | 581 | -28.9% |

### `rush_longest` by book

| Book | Bets | ROI |
|:-----|-----:|----:|
| fanduel | 598 | -0.6% |
| betmgm | 995 | -2.8% |
| draftkings | 1,190 | -3.3% |
| betrivers | 1,077 | -4.0% |
| bovada | 911 | -5.6% |

### `reception_longest` by book

| Book | Bets | ROI |
|:-----|-----:|----:|
| bovada | 1,178 | -3.2% |
| unibet_us | 468 | -3.7% |
| draftkings | 2,433 | -4.4% |
| betrivers | 2,004 | -5.0% |
| fanduel | 2,895 | -5.1% |
| betmgm | 2,727 | -5.1% |
| williamhill_us | 1,865 | -5.7% |

### `receptions` by book

| Book | Bets | ROI |
|:-----|-----:|----:|
| barstool | 467 | -2.6% |
| unibet_us | 1,580 | -3.4% |
| betmgm | 3,807 | -4.7% |
| williamhill_us | 5,307 | -6.8% |
| betrivers | 6,541 | -7.0% |
| draftkings | 6,488 | -7.9% |
| bovada | 5,026 | -10.1% |
| fanduel | 7,864 | -10.9% |
| betonlineag | 7,204 | -13.6% |
| fanatics | 2,718 | -14.3% |

### `pass_interceptions` by book

| Book | Bets | ROI |
|:-----|-----:|----:|
| draftkings | 616 | -6.5% |
| fanduel | 518 | -7.3% |
| betrivers | 455 | -7.4% |
| betonlineag | 550 | -9.0% |
| betmgm | 442 | -11.6% |

### `pass_yards` by book

| Book | Bets | ROI |
|:-----|-----:|----:|
| draftkings | 2,348 | -1.7% |
| fanduel | 1,656 | -3.7% |
| betrivers | 2,876 | -3.7% |
| betmgm | 909 | -7.5% |
| unibet_us | 717 | -15.0% |
| williamhill_us | 1,620 | -15.7% |
| bovada | 897 | -15.8% |
| betonlineag | 1,351 | -23.5% |

### `reception_yards` by book

| Book | Bets | ROI |
|:-----|-----:|----:|
| pointsbetus | 917 | +0.0% |
| barstool | 622 | -0.5% |
| unibet_us | 2,541 | -2.0% |
| fanatics | 1,186 | -2.9% |
| fanduel | 10,482 | -5.9% |
| betrivers | 11,177 | -6.6% |
| betmgm | 5,211 | -7.6% |
| draftkings | 9,834 | -7.8% |
| williamhill_us | 8,182 | -9.2% |
| bovada | 6,222 | -9.6% |
| betonlineag | 6,931 | -13.6% |

### `kicking_points` by book

| Book | Bets | ROI |
|:-----|-----:|----:|
| williamhill_us | 446 | -6.6% |
| draftkings | 633 | -7.1% |
| betmgm | 402 | -8.9% |

### `pass_completions` by book

| Book | Bets | ROI |
|:-----|-----:|----:|
| betmgm | 569 | -2.7% |
| betrivers | 896 | -6.0% |
| bovada | 485 | -6.7% |
| fanduel | 777 | -7.3% |
| draftkings | 1,001 | -8.8% |
| williamhill_us | 505 | -9.4% |
| betonlineag | 1,112 | -11.8% |

### `rush_attempts` by book

| Book | Bets | ROI |
|:-----|-----:|----:|
| bovada | 734 | +0.0% |
| fanduel | 1,326 | -0.9% |
| betmgm | 1,569 | -3.5% |
| betrivers | 1,128 | -5.6% |
| williamhill_us | 1,155 | -6.1% |
| draftkings | 1,803 | -7.4% |
| fanatics | 746 | -12.3% |
| betonlineag | 1,761 | -25.6% |

### `pass_tds` by book

| Book | Bets | ROI |
|:-----|-----:|----:|
| fanduel | 866 | -8.6% |
| draftkings | 758 | -10.2% |
| betrivers | 810 | -11.8% |
| betonlineag | 689 | -12.1% |
| williamhill_us | 722 | -12.4% |
| betmgm | 486 | -13.3% |
| bovada | 504 | -15.8% |

A book needs 400 bets in a market before its ROI is reported; below that the number is noise wearing a book's name.
