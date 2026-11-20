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

## FINDINGS.md text

For the lead to commit as `reviews/318-thaw-watchdog/FINDINGS.md` (see "Done", step 3), then delete this section.

<!-- FINDINGS START -->
# 318: findings

Brief: `briefs/318-thaw-watchdog.md`. Plan and verdict rules: `PLAN.md`, committed in `eb499fb3` before S0 and unchanged since. Steps 2 and 3 by a Claude Opus 5.5 builder on 2026-11-20. **Step 4, the research section (what the sleeping world could do about it), is left to the next agent** and goes at the end of this file.

## Verdict: WATCHDOG CONFIRMED (the `null` backend only)

Every condition of PLAN.md's WATCHDOG CONFIRMED holds, and all three trials are VALID:

| PLAN.md condition | Result |
|---|---|
| B1 dies by SIGKILL | Yes. Gradle's exit value 137, so signal 9. The zombie was already reaped when the watcher looked, so the signal comes from the fallback source the brief allows. |
| Between B1's thaw and its death, a recorded realtime thread runs at least 150 ms without a voluntary context switch | Yes: **189.6 ms**, with no switch of either kind. |
| A1 and A2 both survive (alive 60 s after the return request, with frames recorded after the wake) | Yes. Both alive at +60.0 s, with 1159 and 1163 frames in the 10 s wake. |
| In each A trial, the demoted thread runs at least 200 ms without a voluntary switch after the thaw | Yes: **347.4 ms** (A1) and **349.1 ms** (A2). |

In plain words: after a five-minute freeze, OpenAL Soft's mixer thread catches up on the audio it missed in one go, using the CPU without a break for about 350 ms. As a realtime thread it has a 200 ms budget for that (`RLIMIT_RTTIME`, soft = hard), and the kernel kills the whole game when it is used up. B1's mixer was killed after about 200 ms of its catch-up. Made an ordinary thread before the thaw, the same catch-up ran to its end in A1 and A2 (about 350 ms), and both games played on.

The sender is inferred from this evidence, not seen directly; PLAN.md's rules don't ask for more. If the lead wants to see the kernel name the signal, `kernel.print-fatal-signals=1` during one more B1-style run would show it. That needs root, so it is the lead's option; the builder changed no system setting.

**Scope:** this covers OpenAL Soft's `null` backend, which every rig forces with `ALSOFT_DRIVERS=null`. Whether the real session's backend catches up the same way is step 4's question.

## The runs

All four runs went through `schedule.py` on the first attempt: no exit 75, no busy lock, no other builder's game or Gradle build during any run (`attempt.json`: `overlapped_by_other_java` false), and at least 7.0 GiB available at each start. Records: `runs/<name>/`. `rig/read_run.py runs/<name>` prints the numbers below from them, with PLAN.md's measure.

| Run | Settings | Exit | Outcome | Valid |
|---|---|---|---|---|
| S0 | `setup-flat` creation (`MODE=create CREATE_FLOW=automatic QUIT=1 COVER=0 SHOTS=1`) | 0 | Base world made (`fixture-hashes.json`, `screenshots/`). Not a trial. | n/a |
| B1 | `RT=keep`, `COVER=300 RECLAIM=600M FREEZE=1` | 1 | Died by SIGKILL 197–207 ms after the thaw write | VALID |
| A1 | `RT=demote`, otherwise the same | 0 | Alive 60 s after the return request | VALID |
| A2 | `RT=demote`, otherwise the same | 0 | Alive 60 s after the return request | VALID |

B1's exit 1 is the expected shape of a death: the wake input breaks once the game is gone, and the health watch ends the run (`health-failure.json`: "VINPUT_PID exited"). Its cleanup started 629 ms after the death was seen, so the death counts.

### Validity, trial by trial

| PLAN.md gate | B1 | A1 | A2 |
|---|---|---|---|
| Card awake (D0) from the freeze to the end of sampling | `active` at every reading from before the freeze to the watcher's end; the journal's only `cardwired` line is the D0 at the run's start, no D3 | same | same |
| A realtime thread existed when the freeze was confirmed | 1 | 1 | 1 |
| For `demote`, no thread realtime at the thaw | n/a | `rt-prethaw.json`: none; no realtime thread in any scan after the thaw | same |
| If the game died, before any rig cleanup step | yes (`cleanup_started_before_exit` false; `cleanup_start` 629 ms after the exit was seen) | survived | survived |

### The realtime thread and the limits

Each game had exactly one realtime thread at the freeze (`rt-freeze.json`), and the same limits:

| Run | tid | `comm` | Policy, flags, priority | rtkit's grant | `Max realtime timeout` (soft / hard) |
|---|---|---|---|---|---|
| B1 | 3618139 | `Render thread` | `SCHED_RR`, `SCHED_RESET_ON_FORK`, 1 | "Successfully made thread 3618139 … RT at priority 1", the second OpenAL opened its device | 200000 / 200000 us |
| A1 | 3736529 | `Render thread` | `SCHED_RR`, `SCHED_RESET_ON_FORK`, 1 | same, for 3736529 | 200000 / 200000 us |
| A2 | 3765343 | `Render thread` | `SCHED_RR`, `SCHED_RESET_ON_FORK`, 1 | same, for 3765343 | 200000 / 200000 us |

**The thread is OpenAL Soft's mixer, though its name says `Render thread`.** The brief and step 1 expected the name `alsoft-mixer`. A new thread on Linux inherits the name of the thread that created it, and Minecraft opens its sound device from its render thread. Three facts say this is the mixer and not the game's own render thread:
- rtkit's grant came at the second the game logged "OpenAL initialized on device No Output", and priority 1 is OpenAL Soft's default.
- At the freeze it had used only 1.3–2.1 s of CPU in about 286 s, with about 198 voluntary switches a second. That is a thread that wakes every 5 ms to mix, not a render loop at 115 fps.
- After the thaw it ran without a single switch of either kind for as long as it lived (B1) or for about 350 ms (A1, A2), and then went back to about 0.5 ms of CPU per 100 ms.

Why the bundled OpenAL Soft doesn't rename its mixer thread is not known here (a guess: LWJGL's build leaves thread naming out). Step 4 can check the source. The thaw sampler also follows any thread named `alsoft-*`; there was none.

The same happens in S0: rtkit made two threads realtime there, because the creation run starts the sound engine twice.

### The sampler curves

PLAN.md's measure, from `thaw-samples.csv` (10 ms samples), counting only rows at or after the thaw write. "CPU per 100 ms" is the thread's CPU time gained by the last sample in each 100 ms after the thaw write.

| Run | Policy after the thaw | Longest no-switch stretch (PLAN.md measure) | Stretch, from–to after the thaw write | CPU per 100 ms after the thaw (first five) | Switches in the stretch (voluntary / nonvoluntary) |
|---|---|---|---|---|---|
| B1 | `SCHED_RR` | **189.6 ms** | +7.0 to +196.9 ms, then gone | 89.8, 99.8 (dead before the third) | 0 / 0 |
| A1 | `SCHED_OTHER` | **347.4 ms** | +0.5 to +350.5 ms | 88.2, 99.7, 99.7, 68.2, 0.5 | 0 / 2 |
| A2 | `SCHED_OTHER` | **349.1 ms** | +7.3 to +357.2 ms | 89.8, 99.7, 99.7, 60.8, 0.5 | 0 / 1 |

- **B1, the death.** The last sample, at +196.9 ms, shows the thread still running with 195.8 ms of CPU since its frozen value. The next sample, due about 10 ms later, found it gone. So the game died between +196.9 and about +207 ms, at about 200 ms of CPU, which is where the hard limit lies. The watcher's pidfd saw the whole process gone at +367 ms; tearing down a JVM with 600 MiB in swap takes time. The first sample after the thaw came 7.0 ms after the write, by when the thread had already used 6.15 ms; PLAN.md's measure doesn't count that part (see PLAN-GAP 1).
- **A1 and A2, the whole catch-up.** The demoted thread ran at almost a full core until about +350 ms, with only one or two nonvoluntary switches (as an ordinary thread it can be preempted). Then it went back to its normal rhythm: about 0.5 ms of CPU per 100 ms and about 197 voluntary switches a second, for the rest of the 10 s window.
- **No promotion again.** In A1 and A2 no thread of the game was realtime in any 100 ms scan after the thaw, and the journal holds no rtkit grant after the one at sound start. The demotion kept `SCHED_RESET_ON_FORK` set (`rt-demote.json`).

### Exit and signal

| Run | `exit.json` outcome | Signal | Source | Exit seen | Cleanup before the exit |
|---|---|---|---|---|---|
| B1 | exited | 9 (SIGKILL) | Gradle's exit value 137 (the zombie was "already reaped") | +367 ms after the thaw write, +532 ms after the return request | no |
| A1 | alive | none | | alive at +60 006 ms after the return request | n/a |
| A2 | alive | none | | alive at +60 050 ms after the return request | n/a |

The wake windows of the survivors (10 s, `summary.json`): A1 1159 frames at 115.8 fps, first frame 279 ms after the return request, slowest frame 71 ms; A2 1163 frames at 116.1 fps, first frame 275 ms after the return request, slowest 64 ms. These are single runs, recorded only to show that frames came after the wake.

The game logs end the same way in all three trials: "Can't keep up! … Running 267444–267607ms or 5348–5352 ticks behind" at the thaw. B1's log has nothing after it. The sound lines (`sound-lines.txt`) are only "OpenAL initialized on device No Output" and "Sound engine started" at game start.

## The catch-up of the demoted mixer

After 267.5 s frozen (the freeze starts 30 s into the 300 s cover), the demoted mixer used:
- **A1:** 347.4 ms of CPU without a voluntary switch, in 350 ms of wall time from the thaw write; at most about 356 ms counting the unsampled edges;
- **A2:** 349.1 ms by PLAN.md's measure, 354.5 ms counting the 5.4 ms before the first sample, ending by +357 ms.

So the catch-up after this freeze is **about 350–356 ms of CPU, run in one stretch at nearly a full core**, about 1.3 ms of CPU per frozen second. That is 1.75 times the 200 ms limit. Before the freeze the mixer used about 0.45–0.7% of a core while the game ran and paused. Step 4 works out the longest safe freeze from these numbers.

## How this differs from package 49's conditions

Package 49's two cover-freeze trials (`reviews/49-memory-cuts/failures/cover-freeze-1`, `-2`) and these trials ran the same workload and freeze on the same boot of the same kernel (the monotonic clock continues: 49 at about 260 000 s, these at about 469 000 s). Differences:

| | Package 49 | Package 318 |
|---|---|---|
| The card | Not held awake: it woke about once a minute during the freeze, and the rig's `nvidia-smi` snapshot woke it 380–517 ms before the thaws | Held awake for the whole run by 49b's holder; `active` at every reading |
| Input and failure handling | 49's blocking input pipe, no health watch | 49b's bounded input, health watch and cleanup; thaw on every exit path |
| Return request to thaw | 49.5 ms (cover-freeze-2) and 55.8 ms (cover-freeze-1), to the thaw action's start | 165.0 ms (B1), 177.7 ms (A1), 173.9 ms (A2) to the write: the policy check and the watcher's start come first |
| What was recorded at the thaw | `cgroup.events` and `memory.events` every 20 ms (`return-observer.jsonl`); the thread wasn't named | Each realtime thread's CPU time and switches every 10 ms, a realtime scan every 100 ms, a pidfd on the game, the limits and the policies |
| Mod source | `43c09273` (2026-11-17) | The branch head, from main `e3e9f4b8` (2026-11-20). `mod/` changed in 162 files since; the only sound-related lines are menu click sounds. The OpenAL setup is the same: one realtime thread at priority 1, the `null` device |
| Base world | 49's own `setup-flat` base | A new `setup-flat` base from S0 (49b's went with its worktree) |
| Freeze length | 267.5 s and 268.5 s | 267.5, 267.5 and 267.6 s |
| Frozen memory | RSS 510 and 494 MiB, scope swap 598 and 599 MiB | RSS 502 (B1), 474 (A1), 421 (A2) MiB; swap 598, 598, 682 MiB |
| Death after the thaw | 183–204 ms (cover-freeze-2, from its observer); cover-freeze-1 about the same | B1: 197–207 ms |
| Realtime threads | One per game, priority 1 (rtkit's journal) | One per game, priority 1, `SCHED_RR` with `SCHED_RESET_ON_FORK` |

None of the differences touches the mechanism. 49's deaths came at the same delay after the thaw as B1's, with the same single priority-1 thread and the same `null` backend, so the same watchdog very likely killed them too. The card, which brief review 1 had already cleared, stayed awake here and B1 died anyway. The longer delay before the thaw changes nothing for the mixer: it is frozen until the write.

## PLAN-GAP

1. **A third limit of the measure, not written in PLAN.md.** PLAN.md counts only samples at or after the thaw write, so the CPU time between the write and the first sample after it is left out: up to 10 ms. In B1 that was 6.15 ms (first sample at +7.0 ms), in A2 5.37 ms, in A1 none (first sample at +0.5 ms). It makes the measure read low, never high, so it can't have made a threshold pass. With it, B1's stretch would be 195.8 ms and A2's 354.5 ms. No verdict changes; the verdict uses the committed text.

Nothing else in PLAN.md needed a change.

## For the lead

- **No decision is needed for the verdict.** All three trials were valid on the first try, and the rules give WATCHDOG CONFIRMED.
- **Optional:** a direct sighting of the sender would take `kernel.print-fatal-signals=1` (root) during one more `RT=keep` run. The rules don't need it.

## Step 4: what the sleeping world could do about it

Left to the next agent (the brief's step 4: reading and research only, no product change, no extra runs). Inputs from these runs:
- the catch-up after 267.5 s frozen: about 350–356 ms of CPU in one stretch (above);
- the mixer, when running normally, wakes about 198 times a second;
- the realtime thread is named `Render thread`, not `alsoft-mixer`, so a supervisor that demotes "OpenAL's thread" by name would miss it: pick realtime threads by policy, as the rig does;
- after the demotion nothing promoted the thread again within 60 s, with the `null` backend.
<!-- FINDINGS END -->
