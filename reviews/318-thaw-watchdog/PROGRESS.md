# 318: progress

Brief: `briefs/318-thaw-watchdog.md` (the authority). Branch `pkg/318-thaw-watchdog`. The last step deletes this file.

## Done

**Step 1, the rig** (2026-11-20, Claude Opus 5.5 builder; no game was run):
- `rig/` and `frames/` copied from package 49b in their own commit, with the `pkg49b` names changed to `pkg318` and nothing else. The next commit holds every 318 change, so `git show` on it is the full diff against 49b.
- What changed and why: `rig/README.md`, "What changed from 49b".
- Offline tests, all passing, with outputs in `verification/`:
  - `bash -n` on the 8 rig scripts and `frames/build.sh`;
  - `test_rig.py` 14/14, `test_input.py` 2/2, `test_thaw.py` 16/16;
  - `test_lifecycle.py` 8/8 scenarios: 49b's 3, plus 5 new ones (thaw after a health failure, SIGTERM or a failing command while frozen; the INVALID return; the normal return).
- `frames/build.sh` compiles the renamed recorder (javac only, no Gradle).

**Step 2, the plan** (2026-11-20, Claude Opus 5.5 builder): `PLAN.md`, committed and pushed in `eb499fb3` before S0. Its rules section is the brief's step 2 word for word (checked with `diff`), plus the lead's run measure and its two known limits, and the commands. It hasn't changed since.

**Step 3, the runs** (2026-11-20, same builder): S0, B1, A1, A2, each on the first attempt, no exit 75, no overlap, all trials VALID. **Verdict: WATCHDOG CONFIRMED** (the `null` backend only). Records in `runs/s0`, `runs/b1`, `runs/a1`, `runs/a2`; `rig/read_run.py runs/<name>` prints each run's numbers with PLAN.md's measure.
- **`FINDINGS.md` is not in the repo yet.** The builder's file tool refuses to create a findings file (as with `REPORT.md`, see `CLAUDE.md`). Its full text is the last section of this file, "FINDINGS.md text". The lead commits it as `reviews/318-thaw-watchdog/FINDINGS.md`, for example, in `reviews/318-thaw-watchdog/`: `sed -n '/^<!-- FINDINGS START -->$/,/^<!-- FINDINGS END -->$/p' PROGRESS.md | sed '1d;$d' > FINDINGS.md`, and then deletes that section from here.

## Left, in order

1. **Step 4:** the reading-only research (the brief's step 4), as a section at the end of `FINDINGS.md`, "What the sleeping world could do about it". FINDINGS.md's own last section lists the inputs from the runs. Then delete this file and open the PR (title and body ending as in the brief's Rules).

## What step 4 must know

- **The realtime thread is named `Render thread`, not `alsoft-mixer`.** It is still OpenAL Soft's mixer (rtkit's grant at the "OpenAL initialized" second, priority 1, 1.3–2.1 s of CPU in 286 s, about 198 voluntary switches a second). The bundled OpenAL Soft seems not to rename its mixer thread; check the source (`althrd_setname`) and say whether that is a guess. Any product demotion must pick threads by policy, not by name.
- **The measured catch-up:** after 267.5 s frozen, about 350–356 ms of CPU in one stretch at nearly a full core (A1 347.4 ms, A2 349.1 ms by PLAN.md's measure; 354.5 ms for A2 counting the 5.4 ms before its first sample). B1 died at about 200 ms of it. Use these for "the longest safe freeze".
- **No promotion again** within 60 s after the demotion (the `null` backend): no realtime thread in any scan after the thaw, no new rtkit grant in the journal.
- **Nothing more may be run** for this package: step 4 is reading only.

## What the code doesn't show

### Commands
Run everything from the worktree root, one run at a time, each in the background (they take minutes):

```
python3 reviews/318-thaw-watchdog/rig/schedule.py setup              # S0 (name s0)
python3 reviews/318-thaw-watchdog/rig/schedule.py trial b1 keep      # B1
python3 reviews/318-thaw-watchdog/rig/schedule.py trial a1 demote    # A1
python3 reviews/318-thaw-watchdog/rig/schedule.py trial a2 demote    # A2
```

- **Fixed settings.** A trial always runs `COVER=300 SHOTS=0 RECLAIM=600M FREEZE=1 RT=<mode>` on a fresh copy of `.work/pkg318/AresHub-base`. The rest are the v1 defaults: RD 8/SD 5, heap 1024/256, MemoryHigh 2560M, roads flight, headless 1920×1080@144, `ALSOFT_DRIVERS=null`.
- **S0.** `MODE=create CREATE_FLOW=automatic QUIT=1 COVER=0 SHOTS=1`. It copies the save to the base, writes `fixture-hashes.json`, and copies two pictures of the rig's test town to `screenshots/`.
- **Repeats.** Names are never reused: a repeat is `b1-repeat-2`, and so on.
- **Waits.** Each call waits 30 s afterwards for other lock holders.
- **The lock.** `run.sh` waits for the client-test lock as long as it takes; a busy lock is not exit 75. Exit 75 comes from the memory or owner-game guards, and `retry.sh` retries it every 5 minutes, at most 6 times.

### Timing
From 49b's records, a measured run is about 10 minutes from `run.sh` to cleanup:
- about 1 minute of Gradle and game start;
- settle 120 s, standing 60 s and flight 60 s;
- cover 300 s, wake 10 s.

A 318 trial also holds a surviving game until 60 s after the return request, about 50 s more, so about 11 minutes. S0 has no cover, about 6–8 minutes. A B1 that dies ends about 10 s after the thaw.

### Exit codes
- **0:** survived, and `analyze.py` wrote `summary.json`.
- **1:** a death or rig failure. A B1 death normally shows as 1: wake input breaks after the game dies. That is the expected B1 result, not a rig bug. Read `exit.json`.
- **2:** bad settings.
- **3:** INVALID.
- **75:** busy after all retries.

### Where things land
- **Public:** `runs/<name>/`, written on every exit path, with paths redacted.
- **Raw:** `.work/pkg318/rigs/<name>/`, with the unredacted `game.txt` and `gradle.txt`. Never commit these.
- **Log:** `.work/pkg318/<name>.txt` holds `retry.sh`'s log.
- **Overlap:** `schedule.py` writes `runs/<name>/attempt.json`, whose `overlapped_by_other_java` comes from `host-watch.jsonl`.

### Reading a run (for PLAN.md and FINDINGS.md)
- **`rt-freeze.json`:** the realtime threads at the confirmed freeze (expect one `alsoft-mixer`, `SCHED_RR`, priority 1, flag `SCHED_RESET_ON_FORK`). Its `limits` should read `Max realtime timeout 200000 200000 us`.
- **`rt-demote.json` (demote runs):** per thread, the `chrt` exit, the policy before and after, and `realtime_after`.
- **`rt-prethaw.json`:** the last scan before the thaw. `invalid: true` means INVALID.
- **Thaw time:** the `thaw` record in `actions.jsonl` has `write_monotonic_ns`, just before the write. All timestamps are `CLOCK_MONOTONIC` ns, the same clock as `marks.txt`. The journal's `short-monotonic` seconds use the same clock.
- **`thaw-samples.csv`:** one row per thread per 10 ms (`monotonic_ns,tid,cpu_ns,voluntary,nonvoluntary,state,policy`), from about 0–30 ms before the thaw write. The "runs N ms without a voluntary switch" measure:
  - sum `cpu_ns` deltas between consecutive rows of one tid while `voluntary` stays unchanged;
  - take the longest such stretch after the thaw write.

  `test_thaw.py`'s survivor test computes it that way. Limits: up to 10 ms before a death goes unsampled, and a running thread's `schedstat` is updated at the 1 ms tick (`CONFIG_HZ=1000`). Say so in PLAN.md so B1's 150 ms threshold is applied as committed.
- **`thaw-scan.jsonl`:** each 100 ms scan with any realtime thread. An empty list after the thaw means none.
- **`exit.json`:**
  - `outcome`: `exited`, `alive` (at `hold_until_ns`), `stopped` (the watcher was ended: a rig failure, not a result) or `gone at start`;
  - `signal` with `source` `zombie`; if the zombie was already reaped, `signal_source: gradle exit value`, from `gradle_exit_value - 128`;
  - `after_return_ms` and `exit_detected_ns`;
  - `cleanup_started_before_exit`: if true, the death doesn't count.
- **Card awake:** `card-status.jsonl` should read `active` at before-freeze, frozen, each covered minute, pre-thaw and thaw-watch start/sample end/end. `journal.txt` should hold no `cardwired` D3 line in that window. `cardwire.txt` holds `cardwire get` (it may need root; that is recorded too).
- **Later rtkit grants:** `journal.txt` keeps rtkit's lines that name the game's PID or no process. A new grant for the game PID after the demotion means it was promoted again.
- **Sound lines:** `sound-lines.txt`.

### Known limits of the rig
- **A health failure ends the watcher.** It sends SIGTERM to the controller's direct children, the watcher included, which then records `stopped`. That is a rig failure, kept and repeated, not a trial result.
- **A failed demotion isn't stopped early.** If `chrt` fails, the run goes on with the 5-minute freeze and becomes INVALID at the pre-thaw check. That follows the brief literally.
- **A survivor stays up longer than in 49.** It is held to +60 s before cleanup, after 49b's 10 s wake window. Nothing before the thaw changed.
- **The thaw starts a little later than in 49.** The return-to-thaw delay is about 100 ms longer, for the policy check and the watcher's start. It is measurable from `return_start` and `write_monotonic_ns`.

### Never
- Change `kernel.print-fatal-signals` or anything else under `/sys`, `/proc` or `/etc`, except what the rig does.
- Use sudo or rtkit.
- Touch the owner's session, PipeWire or `~/.config/alsoft.conf`.
- Run a real audio backend: `ALSOFT_DRIVERS=null` stays.
