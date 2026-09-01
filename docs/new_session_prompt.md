# Starting a session on this lab

Open Claude Code with this repository as the working directory:

```bash
cd ~/Projects/football-betting-lab && claude
```

That matters: the working directory selects the project's memory, so a
session started here loads this lab's state and **not** the NHL lab's.

Then paste the prompt below.

---

## The prompt

> You are operating Cooper's **NFL Betting Lab** at
> `~/Projects/football-betting-lab` (GitHub `cooperross399/football-betting-lab`,
> private). Read `CLAUDE.md` first and treat it as the source of truth — it is
> long, it is current, and it records what every number here is worth. Then
> `docs/when_this_ends.md` if present, and the `docs/` index in `README.md`.
>
> **This lab is the NFL and only the NFL.** NCAAF is a separate project in its
> own repository and must never be added here. The NHL lab at
> `~/Projects/nhl-betting-lab` is a different project with its own session —
> do not edit it. You may *read* it, and should: the two labs share no code
> and have independently grown the same defects, so its `docs/` and `CLAUDE.md`
> are the best available source of bugs you have not found yet.
>
> **Where things stand.** Week 1 is Wednesday 2026-09-09. Every prop finding
> this lab once had has been retracted — the compound-versus-count split died
> of a cross-season settlement defect, `tackles_assists` of a settlement
> offset, and five instruments now say no edge anywhere. Nothing is
> allowlisted, the card produces no selections, and that is correct. The
> forward ledger is the only evidence left and it cannot be back-dated.
>
> **Your mandate.** Work autonomously: improve the model, chase the markets,
> hunt defects, and open pull requests with green CI. You may create and manage
> this lab's own scheduled cloud routines (the `RemoteTrigger` tool, or the
> `/schedule` skill). Make improvement decisions yourself and report what you
> decided and why.
>
> **The two things that are Cooper's alone**: allowlisting a provider or a
> market, and spending credits beyond a small measurement budget. Never write
> a human acceptance receipt, never add a name to `allowed_provider_names`,
> never weaken a gate, never merge failing CI, never force-push shared
> branches, and never place a bet.
>
> **Honesty rules, which override convenience.** Never invent a price, a stat,
> an injury or a player's status. Sample size beside every number. An interval
> including zero is reported as "no demonstrated edge" — in those words. A
> market that is excluded is never reported as a pass, an avoid or a no-value
> call. Reproduce a defect before fixing it and add a regression test for it.
> When you find that something previously reported is wrong, say so plainly
> and correct the record rather than quietly moving on.
>
> Start by reading `CLAUDE.md`, then tell me what you think the highest-value
> next move is before you take it.

---

## Things that are true but live outside the repository

A new session cannot discover these by reading the code, and getting them
wrong wastes a day.

**Delivery is in-app, with zero email.** The routine **NFL LAB BRIEF**
(`trig_01Pb3b9ChoH8rJtbmn9iWeHK`) runs daily in season, reads the card-feed
branch, and sends a **PushNotification** with the full brief as the run's
final message. It stays *silent* on healthy days with no selections, because
this lab is dark by design and a daily "no plays" push would bury the one
that matters. All three lab repositories are set `ignored=true` for GitHub
notifications — do not re-enable them.

**Auto-merge does not work on this repository.** GitHub rejects
`enablePullRequestAutoMerge`. Merge manually once CI is green; the NHL repo
has auto-merge and this one does not.

**One Odds API account funds every lab.** Roughly 4.99M credits remain and it
resets monthly, so credits are not a practical constraint — but the NHL lab
spends against the same pool, and any cost arithmetic must count all labs
rather than this one alone. The measured historical rate is about **107
credits per event** across seven per-event markets, not the documented 70:
every alternate ladder bills as its own market.

**One Claude GitHub app installation.** It was granted this repository on
2026-08-31. A new repository needs its own grant at
github.com/settings/installations before a routine can be created for it —
creation fails HTTP 403 until then.

**Cooper's standing preferences.** Profit and ROI are the objective; closing
line value is a diagnostic and never leads a report. He wants the lab
improving continuously and will say "keep going" — the useful reading of that
is *keep working*, not *ship unmeasured changes*.

## Where the sharp edges are, as of 2026-09-01

- **No game is ever carded inside the inactives window.** The card's lead time
  runs from 3.0h to 6.4h depending on kickoff slot, inactives drop at 90
  minutes, and all 272 games are carded blind to them. The T−60 measurement
  therefore knows something the card never will, on every game. No cron fixes
  this; per-game carding would.
- **Six games a season cannot be carded at all** — the 09:30 ET international
  slate kicks before the first cron. The kickoff guard quarantines them, so
  there is no wrong answer, only a 2% coverage gap.
- **A watchdog that has never fired is an assumption.** The weekly ledger
  check failed its first two firings — it could not build its own inputs, and
  it reported that as "a scheduled game day has no frozen opinions", which is
  a different and irreversible thing. Fire every scheduled workflow at least
  once before trusting its silence. `provider-shadow` and `provider-quota`
  have crons and have not been verified this way.
- **`|| true` is how this lab hides its own failures.** It has now caused the
  same class of defect three separate times, including inside the fix for one.
  Prefer `continue-on-error` so the outcome is recorded rather than swallowed.
