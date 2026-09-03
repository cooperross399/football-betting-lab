# Can the card hold an opinion today?

A stale feed does not fail — it answers, with last week's truth. The card prices that, freezes it into the forward ledger, and **the ledger is never revised**. A stale feed does not cost a run; it writes a wrong opinion into the one record this lab cannot correct.

Graded on **content, not file age**. A file rewritten this morning with last week's rows is stale and its timestamp says fresh, which is the ordinary failure when a fetch succeeds against an upstream that has not published yet.

**Ready.** All 6 feed(s) are current.

| Feed | State | Reaches | Expected | Clubs | What a stale copy costs |
|:---|:---|---:|---:|---:|:---|
| `rosters` | current | 22 | 18 | 32/32 | a player priced against the club he left; every one of his rows voids |
| `weekly_rosters` | current | 22 | 18 | 32/32 | inactives unseen, so a player who did not dress is priced as playing |
| `depth_charts` | current | — | 18 | 32/32 | QB1 unknown, so the passing and receiving tree cannot be quarantined |
| `injuries` | current | 22 | 18 | 32/0 | the availability gate reads every player as undesignated |
| `snap_counts` | current | 22 | 18 | 32/0 | role is fitted from volume alone, with no check on who was on the field |
| `player_stats` | current | 22 | 18 | 32/0 | nothing settles: yesterday's frozen opinions stay unsettleable |

A feed marked *not due yet* is one whose season has not started. **An absence before kickoff and an absence after it are different facts**, and reading the first as the second would block every run in the preseason.
