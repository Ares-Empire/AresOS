# 318: the plan

Committed before the first game run (brief `briefs/318-thaw-watchdog.md`, step 2). From this commit on this file doesn't change. A change found to be needed is a PLAN-GAP in `FINDINGS.md`, and the verdict uses the text committed here.

## The runs and the verdict rules (the brief's step 2, word for word)

- **Runs, in this order:**
  - **S0:** `setup-flat` creation of the base world. Not a trial.
  - **B1:** `RT=keep`, freeze as 49 (card held awake by the rig).
  - **A1 and A2:** `RT=demote`, otherwise the same.
- **A trial is VALID only if all of these hold:**
  - the card stayed awake (D0) from the freeze to the end of sampling;
  - a realtime thread existed when the freeze was confirmed;
  - for `demote`, no thread of the game was realtime at the thaw;
  - if the game died, it died before any rig cleanup step started.

  An invalid trial is kept, marked and repeated once. A second invalid one ends the runs as INCONCLUSIVE.
- **NOT REPRODUCED:** B1 survives the thaw. Stop after B1, run no A trial, and report.
- **WATCHDOG CONFIRMED:** all of these hold:
  - B1 dies by SIGKILL;
  - between B1's thaw and its death, a recorded realtime thread runs at least 150 ms without a voluntary context switch;
  - A1 and A2 both survive (alive 60 s after the return request, with frames recorded after the wake);
  - in each A trial, the demoted thread runs at least 200 ms without a voluntary switch after the thaw. The catch-up happened and nothing killed it.
- **ANOTHER SENDER:** A1 or A2 dies by SIGKILL.
- **INCONCLUSIVE:** anything else. Report it, and run nothing more without the lead's OK. If only the sender is unclear, name `kernel.print-fatal-signals=1` as the decisive check. It needs root, so it is the lead's option, and the builder never changes it.
- **Scope of any verdict:** it covers the `null` backend only.

## The run measure (the lead's definition, 2026-11-20)

"Runs N ms without a voluntary context switch", as used by the 150 ms (B1) and 200 ms (A trials) thresholds above:

For a recorded thread, the longest stretch after the thaw write of consecutive 10 ms samples in which its `voluntary_ctxt_switches` stays the same, measured as the sum of its schedstat CPU-time increases across that stretch.

In the rig's records:
- the thaw write is the `write_monotonic_ns` of the `thaw` record in `actions.jsonl`;
- the samples are `thaw-samples.csv` (`monotonic_ns,tid,cpu_ns,voluntary,nonvoluntary,state,policy`, one row per thread per 10 ms); a stretch is a run of consecutive rows of one tid, at or after the thaw write, with the same `voluntary`, and its length is the sum of the `cpu_ns` increases between those rows;
- "a recorded thread" is a thread in `rt-freeze.json` (the realtime threads at the confirmed freeze). In `demote` runs that is the demoted thread.

**Known limits of the measure:**
- up to 10 ms before a death goes unsampled, so a measured stretch that ends in a death can be up to 10 ms short;
- a running thread's schedstat CPU time updates in about 1 ms steps (`CONFIG_HZ=1000`).

## How the runs are made

From the worktree root, one at a time, each in the background:

```
python3 reviews/318-thaw-watchdog/rig/schedule.py setup              # S0 (name s0)
python3 reviews/318-thaw-watchdog/rig/schedule.py trial b1 keep      # B1
python3 reviews/318-thaw-watchdog/rig/schedule.py trial a1 demote    # A1
python3 reviews/318-thaw-watchdog/rig/schedule.py trial a2 demote    # A2
```

- A trial runs `COVER=300 SHOTS=0 RECLAIM=600M FREEZE=1 RT=<mode>` on a fresh copy of S0's base world; the other settings are the rig's defaults (`rig/README.md`), with `ALSOFT_DRIVERS=null`, headless.
- A repeat takes a new name (`b1-repeat-2`, `a1-repeat-2`, ...); earlier records stay.
- Before each run: at least 6 GiB free and nobody else holding the client-test lock (the rig enforces both). On exit 75, wait about five minutes and retry, at most six times (`retry.sh`). Other lock holders go through between runs.
- A run that another builder's game or Gradle build overlapped (`runs/<name>/attempt.json`, `overlapped_by_other_java`) is kept, marked and repeated.
- A failed demotion is not stopped early: the freeze runs its full time and the pre-thaw check (`rt-prethaw.json`) marks the trial INVALID (the lead's decision, 2026-11-20).
