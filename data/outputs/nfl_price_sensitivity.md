# Does the edge survive at a price you could actually get?

The backtest takes the **best available** price across every book quoting a wager, which is what a card does. But a measured edge can be three different things: a real disagreement with the market, a line-shopping premium that exists only as the maximum of N quotes, or one soft book's mistake. Those decide whether a number is a strategy, an operational requirement, or a curiosity.

The **consensus** column is the median quote per wager — the closest thing to *the* price, and the one thing shopping cannot improve.

| Market | Bets | Best of N | Consensus | Books positive | Reading |
|:-------|-----:|----------:|----------:|:---------------|:--------|
| `tackles_assists` | 6,267 | +15.0% | +9.0% | 8/8 | **survives** — +9.0% at the consensus price and positive at 8 of 8 books |
| `rush_yards` | 16,829 | +13.0% | +8.3% | 10/11 | **survives** — +8.3% at the consensus price and positive at 10 of 11 books |
| `anytime_td` | 2,632 | +7.5% | +0.2% | 2/10 | mixed — +0.2% at the consensus, positive at 2 of 10 books |
| `receptions` | 12,918 | +6.8% | +1.5% | 7/10 | **survives** — +1.5% at the consensus price and positive at 7 of 10 books |
| `rush_attempts` | 5,153 | +6.6% | -0.5% | 8/9 | mixed — -0.5% at the consensus, positive at 8 of 9 books |
| `pass_attempts` | 2,762 | +5.9% | +2.9% | 7/8 | **survives** — +2.9% at the consensus price and positive at 7 of 8 books |
| `reception_yards` | 39,109 | +4.5% | +1.6% | 9/11 | **survives** — +1.6% at the consensus price and positive at 9 of 11 books |
| `rush_longest` | 3,050 | +3.8% | -0.6% | 6/6 | mixed — -0.6% at the consensus, positive at 6 of 6 books |
| `pass_yards` | 10,638 | +3.1% | +3.5% | 4/8 | mixed — +3.5% at the consensus, positive at 4 of 8 books |
| `reception_longest` | 8,917 | +2.5% | +0.1% | 7/8 | **survives** — +0.1% at the consensus price and positive at 7 of 8 books |
| `pass_completions` | 2,663 | +1.2% | -2.0% | 2/8 | **a shopping premium** — -2.0% at the consensus and positive at only 2 of 8 books. The edge is the maximum of N quotes, not a disagreement with the market |
| `pass_tds` | 2,354 | +0.2% | +3.1% | 0/9 | mixed — +3.1% at the consensus, positive at 0 of 9 books |
| `kicking_points` | 1,212 | -0.7% | -4.8% | 1/5 | **a shopping premium** — -4.8% at the consensus and positive at only 1 of 5 books. The edge is the maximum of N quotes, not a disagreement with the market |
| `pass_longest_completion` | 953 | -2.6% | -1.9% | 0/3 | **a shopping premium** — -1.9% at the consensus and positive at only 0 of 3 books. The edge is the maximum of N quotes, not a disagreement with the market |
| `field_goals` | 1,436 | -3.2% | -5.4% | 1/3 | **a shopping premium** — -5.4% at the consensus and positive at only 1 of 3 books. The edge is the maximum of N quotes, not a disagreement with the market |
| `pass_interceptions` | 2,750 | -10.2% | -6.6% | 0/8 | **a shopping premium** — -6.6% at the consensus and positive at only 0 of 8 books. The edge is the maximum of N quotes, not a disagreement with the market |
| `sacks` | 8,795 | -11.8% | -5.8% | 0/5 | **a shopping premium** — -5.8% at the consensus and positive at only 0 of 5 books. The edge is the maximum of N quotes, not a disagreement with the market |
| `defensive_interceptions` | 1,193 | -28.8% | -11.0% | 0/2 | **a shopping premium** — -11.0% at the consensus and positive at only 0 of 2 books. The edge is the maximum of N quotes, not a disagreement with the market |
| `reception_tds` | 61 | -31.2% | +23.4% | 0/0 | no book quoted enough of this market to say |
| `rush_tds` | 150 | -36.3% | -13.5% | 0/0 | no book quoted enough of this market to say |

### `tackles_assists` by book

| Book | Bets | ROI |
|:-----|-----:|----:|
| bovada | 1,988 | +16.0% |
| betmgm | 2,593 | +15.2% |
| draftkings | 5,360 | +14.5% |
| betonlineag | 1,261 | +13.1% |
| betrivers | 1,782 | +11.7% |
| unibet_us | 1,240 | +11.4% |
| williamhill_us | 2,246 | +9.0% |
| barstool | 751 | +6.0% |

### `rush_yards` by book

| Book | Bets | ROI |
|:-----|-----:|----:|
| draftkings | 6,498 | +15.1% |
| betrivers | 6,911 | +14.7% |
| unibet_us | 1,865 | +13.7% |
| fanduel | 5,336 | +8.7% |
| pointsbetus | 718 | +6.7% |
| williamhill_us | 4,818 | +4.9% |
| bovada | 3,861 | +3.6% |
| betonlineag | 4,152 | +3.6% |
| betmgm | 3,533 | +2.6% |
| fanatics | 766 | +2.1% |
| barstool | 480 | -6.3% |

### `anytime_td` by book

| Book | Bets | ROI |
|:-----|-----:|----:|
| fanduel | 2,486 | +1.1% |
| pointsbetus | 699 | +0.1% |
| fanatics | 776 | -0.5% |
| draftkings | 2,491 | -2.6% |
| betonlineag | 1,581 | -4.2% |
| williamhill_us | 2,402 | -5.3% |
| bovada | 2,181 | -5.4% |
| betmgm | 2,194 | -7.0% |
| betrivers | 2,469 | -9.6% |
| unibet_us | 894 | -14.2% |

### `receptions` by book

| Book | Bets | ROI |
|:-----|-----:|----:|
| unibet_us | 2,279 | +8.8% |
| barstool | 644 | +7.9% |
| betrivers | 9,685 | +4.7% |
| betmgm | 5,654 | +3.4% |
| draftkings | 9,547 | +2.6% |
| williamhill_us | 7,949 | +1.0% |
| bovada | 7,502 | +0.6% |
| fanduel | 11,682 | -1.1% |
| fanatics | 3,989 | -1.8% |
| betonlineag | 10,730 | -3.9% |

### `rush_attempts` by book

| Book | Bets | ROI |
|:-----|-----:|----:|
| unibet_us | 446 | +8.7% |
| fanduel | 1,939 | +7.7% |
| bovada | 1,109 | +7.7% |
| williamhill_us | 1,648 | +6.3% |
| draftkings | 2,666 | +6.2% |
| betrivers | 1,677 | +6.1% |
| betmgm | 2,261 | +4.3% |
| fanatics | 1,109 | +1.5% |
| betonlineag | 2,695 | -6.8% |

### `pass_attempts` by book

| Book | Bets | ROI |
|:-----|-----:|----:|
| betonlineag | 1,169 | +4.8% |
| draftkings | 1,900 | +3.9% |
| bovada | 739 | +3.6% |
| betmgm | 921 | +2.6% |
| fanduel | 1,144 | +2.6% |
| williamhill_us | 746 | +2.4% |
| betrivers | 1,103 | +2.2% |
| fanatics | 992 | -5.1% |

### `reception_yards` by book

| Book | Bets | ROI |
|:-----|-----:|----:|
| unibet_us | 3,800 | +11.8% |
| pointsbetus | 1,318 | +6.9% |
| fanatics | 1,790 | +4.8% |
| barstool | 880 | +4.7% |
| betrivers | 16,797 | +4.5% |
| fanduel | 15,508 | +3.9% |
| betmgm | 7,770 | +1.4% |
| draftkings | 14,534 | +1.4% |
| bovada | 9,187 | +1.0% |
| williamhill_us | 12,066 | -0.3% |
| betonlineag | 10,478 | -3.5% |

### `rush_longest` by book

| Book | Bets | ROI |
|:-----|-----:|----:|
| draftkings | 1,784 | +3.9% |
| betmgm | 1,473 | +3.5% |
| fanduel | 916 | +2.3% |
| betrivers | 1,618 | +1.9% |
| bovada | 1,363 | +1.5% |
| unibet_us | 401 | +1.0% |

### `pass_yards` by book

| Book | Bets | ROI |
|:-----|-----:|----:|
| draftkings | 3,696 | +7.5% |
| betrivers | 4,213 | +4.6% |
| fanduel | 2,524 | +3.2% |
| unibet_us | 1,037 | +1.8% |
| betmgm | 1,385 | -1.6% |
| williamhill_us | 2,625 | -3.9% |
| bovada | 1,404 | -5.3% |
| betonlineag | 2,337 | -9.3% |

### `reception_longest` by book

| Book | Bets | ROI |
|:-----|-----:|----:|
| unibet_us | 673 | +5.4% |
| barstool | 502 | +3.6% |
| bovada | 1,741 | +3.3% |
| draftkings | 3,741 | +1.5% |
| betrivers | 3,133 | +1.3% |
| betmgm | 4,090 | +0.7% |
| fanduel | 4,399 | +0.2% |
| williamhill_us | 2,812 | -0.0% |

### `pass_completions` by book

| Book | Bets | ROI |
|:-----|-----:|----:|
| unibet_us | 483 | +9.4% |
| betrivers | 1,336 | +1.5% |
| draftkings | 1,566 | -0.4% |
| betmgm | 817 | -0.5% |
| williamhill_us | 716 | -1.2% |
| fanduel | 1,106 | -1.7% |
| bovada | 712 | -2.5% |
| betonlineag | 1,745 | -4.2% |

### `pass_tds` by book

| Book | Bets | ROI |
|:-----|-----:|----:|
| fanduel | 3,272 | -2.0% |
| betrivers | 2,364 | -2.9% |
| betmgm | 1,021 | -3.3% |
| draftkings | 2,628 | -3.7% |
| bovada | 1,710 | -4.8% |
| unibet_us | 646 | -5.2% |
| williamhill_us | 2,330 | -7.0% |
| betonlineag | 2,285 | -8.5% |
| fanatics | 901 | -10.9% |

### `kicking_points` by book

| Book | Bets | ROI |
|:-----|-----:|----:|
| betrivers | 541 | +4.3% |
| williamhill_us | 779 | -0.3% |
| draftkings | 980 | -0.8% |
| bovada | 537 | -2.3% |
| betmgm | 621 | -6.7% |

### `pass_longest_completion` by book

| Book | Bets | ROI |
|:-----|-----:|----:|
| draftkings | 495 | -3.7% |
| fanduel | 449 | -4.2% |
| betrivers | 511 | -5.3% |

### `field_goals` by book

| Book | Bets | ROI |
|:-----|-----:|----:|
| betmgm | 644 | +0.2% |
| draftkings | 1,408 | -0.9% |
| williamhill_us | 1,182 | -1.7% |

### `pass_interceptions` by book

| Book | Bets | ROI |
|:-----|-----:|----:|
| barstool | 437 | -5.5% |
| betmgm | 1,466 | -7.1% |
| bovada | 1,112 | -8.2% |
| betonlineag | 1,854 | -9.2% |
| fanduel | 1,717 | -9.4% |
| betrivers | 2,285 | -9.8% |
| draftkings | 2,988 | -10.4% |
| williamhill_us | 1,564 | -10.9% |

### `sacks` by book

| Book | Bets | ROI |
|:-----|-----:|----:|
| draftkings | 5,657 | -10.0% |
| betonlineag | 7,159 | -12.0% |
| williamhill_us | 1,639 | -14.3% |
| betrivers | 2,078 | -17.5% |
| fanduel | 2,984 | -20.2% |

### `defensive_interceptions` by book

| Book | Bets | ROI |
|:-----|-----:|----:|
| betrivers | 1,426 | -25.3% |
| williamhill_us | 480 | -33.9% |

A book needs 400 bets in a market before its ROI is reported; below that the number is noise wearing a book's name.
