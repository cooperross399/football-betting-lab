# Does each feature correlate with itself?

Run before any feature is tested against a price. **Year over year is the column that governs**: a live card can only ever hold the prior season, so a feature that does not persist cannot help however precisely it is measured. Split-half says how noisy the measurement is; the two answer different questions and a high split-half beside a zero carryover means *we measure last year's team perfectly, and last year's team has left*.

| feature | entity-seasons | split-half | full season | carryover, raw | carryover, ranked | pairs | verdict |
|:--|--:|--:|--:|--:|--:|--:|:--|
| pressures per game (defender) | 3,746 | +0.846 | +0.916 | +0.882 | **+0.884** | 2,240 | usable |
| average depth of target faced (defender) | 1,531 | +0.735 | +0.847 | +0.783 | **+0.782** | 817 | usable |
| yards before contact per rush | 588 | +0.568 | +0.725 | +0.646 | **+0.674** | 340 | usable |
| broken tackles per game (rusher) | 983 | +0.598 | +0.748 | +0.643 | **+0.645** | 568 | usable |
| blitz rate, 5+ rushers (defence) | 128 | +0.745 | +0.854 | +0.542 | **+0.548** | 96 | usable |
| yards after contact per rush | 588 | +0.358 | +0.528 | +0.513 | **+0.500** | 340 | usable |
| completion % allowed (defender) | 1,531 | +0.377 | +0.548 | +0.450 | **+0.458** | 817 | usable |
| pressure rate generated (defence) ⚠︎ | 128 | +0.904 | +0.950 | +0.067 | **+0.439** | 96 | usable |
| man coverage rate (defence) ⚠︎ | 128 | +0.900 | +0.947 | +0.017 | **+0.435** | 96 | usable |
| bad throw % (quarterback) | 283 | +0.203 | +0.337 | +0.414 | **+0.435** | 177 | usable |
| broken tackles per game (receiver) | 2,168 | +0.326 | +0.492 | +0.411 | **+0.414** | 1,296 | usable |
| pressure rate faced (quarterback) | 283 | +0.403 | +0.574 | +0.397 | **+0.391** | 177 | weak |
| times blitzed per game (quarterback) | 283 | +0.458 | +0.628 | +0.392 | **+0.372** | 177 | weak |
| sacks taken per game (quarterback) | 283 | +0.416 | +0.588 | +0.382 | **+0.372** | 177 | weak |
| time to throw allowed (defence) ⚠︎ | 128 | +0.298 | +0.459 | +0.120 | **+0.327** | 96 | weak |
| passer rating when targeted (receiver) | 2,168 | +0.194 | +0.325 | +0.247 | **+0.251** | 1,296 | weak |
| missed tackle % (defender) | 3,539 | +0.125 | +0.222 | +0.215 | **+0.210** | 2,081 | weak |
| yards allowed per target (defender) | 1,531 | +0.147 | +0.256 | +0.173 | **+0.172** | 817 | **too noisy to carry a signal** |
| defenders in box (defence) ⚠︎ | 128 | +0.962 | +0.981 | +0.350 | **+0.152** | 96 | **too noisy to carry a signal** |
| passer rating allowed (defender) | 1,531 | +0.100 | +0.181 | +0.115 | **+0.125** | 817 | **too noisy to carry a signal** |
| drop % (receiver) | 2,168 | +0.022 | +0.044 | +0.075 | **+0.078** | 1,296 | **too noisy to carry a signal** |

⚠︎ **The two carryover columns disagree by 0.15 or more**, which means the league-wide level moved between seasons and the raw number is reading that shift rather than the teams: *pressure rate generated (defence)*, *man coverage rate (defence)*, *time to throw allowed (defence)*, *defenders in box (defence)*. Only the ranked column means anything for these.

Player features span 2018-2025 (7 year-over-year transitions); defence features span 2022-2025 (3), because participation charting is 47 MB a season and earlier ones are not cached.

Features weighted one-per-game rather than by a published denominator, because the feed does not publish one — this adds noise and so **understates** their reliability: *missed tackle % (defender)*, *pressures per game (defender)*, *broken tackles per game (rusher)*, *drop % (receiver)*, *passer rating when targeted (receiver)*, *broken tackles per game (receiver)*, *pressure rate faced (quarterback)*, *bad throw % (quarterback)*, *times blitzed per game (quarterback)*, *sacks taken per game (quarterback)*.

A correlation near zero is not proof the underlying thing is irrelevant to football. It is proof that this measurement of it, at this sample size, carries almost nothing — which is the only question worth answering before spending a season's credits on it.
