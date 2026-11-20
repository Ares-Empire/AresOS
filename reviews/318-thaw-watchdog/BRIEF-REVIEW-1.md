# 318: brief review 1

**Verdict: READY WITH CHANGES.** The hypothesis is well supported and the A/B design (keep against demote, card held awake) is the right one. One blocking fix: the demotion command as written fails on every rtkit thread, and nothing stops a failed demotion from being scored WATCHDOG REFUTED. Its fix is mechanical, and the step-1 stand-in test (finding 1) proves it, so a second brief review is only needed if the lead changes the design. The SHOULD-FIXes tighten the verdict rules so that each plausible outcome gets the right label.

Reviewer: Claude Opus 5.5, fresh context, 2026-11-20. Brief at `c6d7c175`.

## What I checked (read-only)

- `AGENTS.md`, the brief, package 49's report and both `failures/cover-freeze-*` records (including `partial/actions.jsonl`, `marks.txt`, `wake-input.jsonl`, `return-observer.jsonl`), the 49 and 49b rigs (`measure.sh`, `lifecycle.sh`, `run.sh`, `inner.sh`, `java-wrapper.sh`, `scope.py`, `snap.py`, `observe-return.py`, `helper41.py`), `mod/dev/env.sh` (supervisor and holder), the SIGKILL call sites in `os/config/usr/libexec/aresos-shell`, and 49b's `schedule.py`.
- The journal for 2026-11-17 23:26–23:53, in `short-precise` and `short-monotonic` (the monotonic form lines up with the rig's `monotonic_ns` marks), and cardwired's lines for 49b's runs on 2026-11-18.
- `busctl` on rtkit: `RTTimeUSecMax` 200000, `MaxRealtimePriority` 20. `kernel.print-fatal-signals` 0, `perf_event_paranoid` 2, `RLIMIT_RTPRIO` 0/0, `CONFIG_HZ=1000`, chrt from util-linux 2.41.6.
- `chrt -p` on the account's existing realtime threads (the session's PipeWire data loops), read only.
- One throwaway child process of my own, started as `SCHED_OTHER|SCHED_RESET_ON_FORK`, to test the kernel's permission rule (finding 1). It touched no other process.
- The OpenAL Soft that Minecraft 26.2 loads: Loom pins `lwjgl-openal:3.4.1`, and its Linux native is OpenAL Soft commit `c41d64c6`. I read its strings through a pipe, without extracting it. I also read OpenAL Soft's `alc/backends/null.cpp` and `core/helpers.cpp` at that commit on GitHub.

What agrees with the brief: one rtkit grant per game at priority 1, and nothing else from rtkit; no systemd-oomd, kernel OOM or NVRM line; no "Stopping" line for either game scope; the rig, helper41 and aresos-shell send the game no SIGKILL (aresos-shell's two `killpg(..., SIGKILL)` calls hit only its own icon converter's process group); and OpenAL Soft lowers `RLIMIT_RTTIME` before it asks rtkit. The rig's cleanup also came after the death: run 2's first wake input was at +452 ms and the broken pipe at +553 ms, after `inner.sh`'s cleanup had ended the input reader once Gradle reported exit 137. Gradle's line is its normal report of a child's abnormal exit, not a cancellation.

## Findings

### 1. BLOCKING: `chrt --other` cannot demote an rtkit thread, and a failed demotion would be scored WATCHDOG REFUTED

rtkit grants `SCHED_RR|SCHED_RESET_ON_FORK`. The account's own rtkit threads show it (`chrt -p` on a PipeWire data loop prints `SCHED_RR|SCHED_RESET_ON_FORK`). The kernel lets only a `CAP_SYS_NICE` caller clear that flag (chrt(1): "it can be reset only if the thread has the CAP_SYS_NICE capability"). On my throwaway child that carried the flag:

```
os.sched_setscheduler(0, SCHED_OTHER, ...)                      -> [Errno 1] Operation not permitted
chrt --other --pid 0 <pid>                                       -> failed to set pid's policy: Operation not permitted
os.sched_setscheduler(0, SCHED_OTHER | SCHED_RESET_ON_FORK, ...) -> allowed
chrt --reset-on-fork --other --pid 0 <pid>                       -> exit 0, policy SCHED_OTHER|SCHED_RESET_ON_FORK
```

So brief line 30's command fails with EPERM on exactly the thread it targets. Line 30's "an unprivileged thread may still switch to a normal policy" holds only when the flag is kept. Step 1's "plain-policy stand-ins" carry no flag, so the offline test passes with the wrong command. Line 30 then says only "Record the result". A1 and A2 would freeze with the mixer still realtime, die like B1, and the rules would print WATCHDOG REFUTED. That is a measurement that wrongly concludes.

Proposed wording:
- Line 30: "**`demote`:** set each recorded realtime thread to `SCHED_OTHER` and keep rtkit's reset-on-fork flag: `chrt --reset-on-fork --other --pid 0 <tid>`, or `os.sched_setscheduler(tid, os.SCHED_OTHER | os.SCHED_RESET_ON_FORK, os.sched_param(0))`. Without the flag the kernel refuses an unprivileged caller (EPERM). Record each thread's policy with its flags (`os.sched_getscheduler` or `chrt -p`), before and after."
- Add a gate: "If any thread of the game is still `SCHED_FIFO` or `SCHED_RR` after the demotion, thaw, end the run and mark it INVALID. It is not an A run. Fix the cause and repeat it once."
- Step 1 tests: "The demotion stand-in carries the reset-on-fork flag (start it with `chrt --other --reset-on-fork 0 <command>`; no rtkit is needed). The test shows that plain `chrt --other` gets EPERM on it, and that the rig's command succeeds and keeps the flag."

### 2. SHOULD-FIX: record and demote after the freeze is confirmed, not before

While the game is frozen its threads can't exit, start a new mixer thread or call rtkit. Recording and demoting there gives three things:
- **No tid reuse between the `Tgid` check and the policy change.** The only other realtime threads on this account are the session's PipeWire data loops, and they have the same owner. A reused tid would therefore be his audio. With `pid_max` 4194304 that is very unlikely, but this order rules it out at no cost.
- **No window between demotion and freeze** in which a new mixer thread could be promoted.
- **The recorded set is exactly the set that is thawed.** "Record the policy again just before the thaw" becomes a plain check.

Changing the policy of a frozen task works normally.

Proposed wording for lines 29–30: "**After the freeze is confirmed, in both modes:** record every thread ... In `demote`, demote them now, then read the policy of every thread of the game again."

### 3. SHOULD-FIX: the evidence summary misplaces the GPU wake and leaves out the mechanism the rig itself sets up

- **The card didn't wake at the thaw.** In the monotonic journal, run 1's `cardwired ... D0` is at 259868.341, and its thaw write (`actions.jsonl`) is at 259868.722, 380 ms later. Run 2: D0 at 260840.396, thaw at 260840.912, 517 ms later. The cause is the rig's `covered5m` snapshot, which runs `nvidia-smi -q -x` (49 `rig/snap.py:112`). The same per-minute snapshot woke the card from D3cold four more times in each freeze (run 2: 23:48:29, 23:49:29, 23:50:29, 23:51:29). The frozen game survived those wakes, and a fatal signal does reach a task in a frozen cgroup-v2 group. What remains of the GPU suspect is the game's first GPU use after D3cold cycles while its context was frozen. That is still worth B1's held card, but it is weaker than "woke at the thaw".
- **Both rigs force OpenAL Soft's null backend** (`ALSOFT_DRIVERS=null`: 49 `inner.sh:29`, 49b `inner.sh:41`). Its mixer (`NullBackend::mixerProc` in `alc/backends/null.cpp`, thread name `alsoft-mixer`) calls `SetRTPriority()`. It then counts the samples due from wall-clock time since `start` and renders all of them in an inner `while(avail-done >= mUpdateSize)` loop, which never sleeps. After five frozen minutes that is about five minutes of audio in one go. This is the hypothesis's catch-up loop, in the rig's own configuration, and the brief should say so.
- **Soft equals hard.** OpenAL Soft sets the hard limit to `RTTimeUSecMax` and the soft limit to `min(soft, hard)`, so both are 200 ms. The kernel checks the hard limit first, which is why the signal is SIGKILL and not SIGXCPU. Expect `Max realtime timeout 200000 200000 us`.
- **Timing.** In run 2 the thaw write was at +49.5 ms after the return request. The observer saw the game alive at +232.8 ms and a zombie at +253.1 ms. So death came 183–204 ms after the thaw: the 253 ms is the first observation, not the moment. Run 1 had no observer, but both game scopes ended about the same time after their thaw writes: 339 ms (run 1) and 344 ms (run 2), from the journal's "Consumed" line against `actions.jsonl`. So run 1 died at the same delay. Twice the same ~200 ms after the thaw fits a fixed timer.
- **memory.events at death** were recorded only in run 2. Run 1's last record is the frozen five-minute snapshot (all zero).

Proposed replacement for lines 16–17:

> - **The timing fits.** In cover-freeze-2 the thaw write came 49.5 ms after the return request; the game was alive at 233 ms and a zombie at 253 ms, so it died 183–204 ms after the thaw. Both games' scopes ended 339 and 344 ms after their thaws, so cover-freeze-1 died at the same delay.
> - **The rig sets up the catch-up.** Both rigs run the game with `ALSOFT_DRIVERS=null`. OpenAL Soft's null backend renders, without sleeping, every sample due since its clock started, so after five frozen minutes its realtime mixer has about five minutes of audio to render at once.
> - **The other suspect: the NVIDIA card.** It went D3cold during both freezes and was woken once a minute by the rig's own `nvidia-smi` snapshots, the last time 0.4–0.5 s before each thaw; the frozen game survived those wakes. Left untested is the game's first GPU use after those cycles. Package 49b's rig holds the card awake for the whole run, which removes the cycles.

### 4. SHOULD-FIX: the verdict rules need validity gates, a positive control in the A runs, and labels that don't overclaim

Outcomes the current rules would mislabel:
- **B1 survives by chance.** The catch-up's length is unknown and may be near 200 ms, since it depends on the active voices and on swap-ins after the 600M reclaim. Many things differ from 49: the held card, the 49b rig changes, the current mod source and the new sampler. "GPU SUSPECT" names one of them.
- **B1 gets no realtime thread.** rtkit refuses (its per-user limits are shared with his session), B1 survives, and the rules print GPU SUSPECT.
- **A survives because the catch-up never happened** (conditions changed, or the mixer was replaced), not because demotion removed the kill. Survival only means something if the same long run happened without the kill.
- **"No sample showing it asleep" can't see short sleeps.** A 10 ms state sample misses sub-millisecond sleeps, and any sleep resets the watchdog: `RLIMIT_RTTIME` counts CPU time "without making a blocking system call" (getrlimit(2)). The thread's `voluntary_ctxt_switches` (`/proc/<pid>/task/<tid>/status`) is exact: while it doesn't change, the thread never blocked.
- **A death in a cleanup path.** The 49b lifecycle the copy inherits can SIGKILL the game scope: `lifecycle.sh:36` after 15 s, the supervisor in `mod/dev/env.sh:190` after 20 s, and the supervisor aborts the whole run if the holder dies. A thaw inside cleanup can also trip the watchdog. Neither is a B1/A result.
- **One A death by SIGKILL** shows that another sender exists. It does not by itself clear the watchdog of B1's death, so "REFUTED" overclaims.

With the gates and the positive control, three runs are enough for the scoped claim "under the null backend, after a five-minute freeze with the 600M reclaim, the RT watchdog kills the thawed game". Each A run then shows the condition present and the kill absent, and B1 is the third death of three under the same conditions. They are not enough for any claim about his session (finding 6).

Proposed replacement for lines 39–45:

> - **A valid run:** the card stayed awake from the freeze to 60 s after the return request (no `cardwired` D3 line in that window; `power/runtime_status` reads `active` at the freeze, each minute and the thaw; package 47 found that reading it doesn't wake the card); at the freeze the game had at least one `SCHED_FIFO`/`SCHED_RR` thread, with `Max realtime timeout` 200000/200000; no other builder's game or Gradle overlapped; any death came before the rig's first cleanup mark. A1 and A2 also need: every recorded thread `SCHED_OTHER` with its flag after the demotion, no realtime thread of the game at any post-thaw scan, and no rtkit grant for the game PID in the journal after the demotion. An invalid run is reported, not judged, and repeated once.
> - **Survives:** alive 60 s after the return request, with frames recorded after the wake.
> - **NOT REPRODUCED:** B1 is valid and survives. Stop, run no A trial, and report the realtime thread's longest post-thaw stretch without a voluntary switch, and how B1 differs from 49 (the held card is one difference). The lead picks the next run.
> - **WATCHDOG CONFIRMED:** B1 is valid and dies by SIGKILL, and from the first sample after the thaw to the last before its death a recorded realtime thread's CPU time rose by at least 150 ms with its voluntary switch count unchanged; and A1 and A2 are valid and both survive, and in each the demoted thread's CPU time rose by at least 200 ms after the thaw with its voluntary switch count unchanged (the same long run, without the kill).
> - **ANOTHER SENDER:** a valid A run dies by SIGKILL. Something other than the RT watchdog killed that game; report its timing next to B1's.
> - **INCONCLUSIVE:** anything else. Report it, and run nothing more without the lead's OK.

Also add `mark cleanup_start` as the first line of the copied `finish()`, so the "before the first cleanup mark" test has something to compare against.

### 5. SHOULD-FIX: what the sampler and the run record need to support those rules

Proposed wording for line 31:

> Add a thaw sampler. From just before the thaw write, every 10 ms, record for each recorded thread its `schedstat` first field (CPU time, ns), `voluntary_ctxt_switches` and `nonvoluntary_ctxt_switches` from its `status`, its state and its policy; every 100 ms, the policy of every thread of the game. Stop at exit, or after 3 s in `keep` and 10 s in `demote` (so the demoted catch-up's full length is measured). A separate exit watcher (a pidfd) runs until 60 s after the return request and reads the zombie's wait status from `/proc/<pid>/stat` (field 52, as package 49's `observe-return.py` did; the zombie lasted about 140 ms there). If it misses the zombie, use Gradle's "exit value" line and say which source was used. After each run, copy the journal's rtkit and `cardwired` lines for the run's window (read-only, no hostname).

The game's parent is Gradle, so the rig can't `waitpid` it. That is why the zombie read is needed. All of this is unprivileged and cheap: one or two threads every 10 ms, plus a scan of about 100 small files every 100 ms.

### 6. SHOULD-FIX: the verdict is about the null backend, and step 4 has to say what his session would do

The bundled OpenAL Soft (`c41d64c6`, from LWJGL 3.4.1) also has PipeWire and PulseAudio backends, which it loads on demand (`libpipewire-0.3.so.0`, `libpulse.so.0`). In his real session the game would use one of those, not `null`. Their mixing is driven by the sound server's cycle rather than wall-clock catch-up. That last point is my guess from how those backends work, and it is what step 4 should check in the source. If it holds, the kill may be a property of the rig rather than of the sleeping world, and step 4's remedies would aim at the wrong thing.

Never test this with a real backend. The rig's game would connect to his session's sound server and play into it.

Proposed additions to step 4:
- "FINDINGS states that the verdict holds for the null backend. From OpenAL Soft's source, say whether the PipeWire and PulseAudio backends run a realtime thread (and who promotes it) and whether either can run 200 ms without blocking after a thaw. Mark guesses."
- **Bullet 1 is already answerable read-only.** The library carries `ALC_SOFT_pause_device`, and `lwjgl-openal-3.4.1.jar` has `org/lwjgl/openal/SOFTPauseDevice.class`. Add, to check in the source: resuming starts a new mixer thread, which calls `SetRTPriority()` again.
- **Bullet 2's answer includes that.** Any backend restart (resume, reset, reopen, a device change) brings a new mixer thread and a fresh rtkit grant.
- **Bullet 3:** also name the `rt-time-limit` option (present in the library). Any config must apply to the game alone, through `ALSOFT_CONF` in the game's environment, never `~/.config/alsoft.conf`: that file belongs to the same account as his session and would change his other OpenAL programs.
- "From the demote runs' measured catch-up CPU time, give the longest freeze whose catch-up stays under 200 ms. That is a freeze length the sleeping world could use without any audio change."

### 7. SHOULD-FIX: copying `rig/` alone doesn't run, and the needed setup run isn't in the plan

- **The base world is gone.** 49b's base worlds lived in its worktree's `.work/pkg49b/`, and that worktree no longer exists. 49b made its flat base with a `setup-flat` creation run (`schedule.py:61`: `MODE=create CREATE_FLOW=automatic QUIT=1`). PLAN.md is committed word for word, so list that run there as a setup run without a verdict, before B1.
- **The frames path breaks.** `measure.sh:88` calls `$here/../frames/build.sh`. Copy `frames/` as well, or point at 49b's (tracked and read-only).
- **Rename the prefix.** Change `pkg49b` to `pkg318` in the unit names, the `scope.py:7` pattern, the `measure.sh:83` guard and `.work/pkg49b`, so neither package's guards or records are confused with the other's.

### 8. NIT: the allowed writes don't cover the step-1 stand-ins, and rtkit stand-ins share his budget

Line 71 limits scheduling changes to the game's threads, while step 1 asks for a demotion test on a stand-in. Add "and on the offline tests' own stand-in processes".

Prefer the reset-on-fork stand-in from finding 1 to rtkit. rtkit counts requests and threads per user, and this account is also his session's. A burst of test requests could get his own audio programs refused realtime for a while. The harm is low and brief, hence a NIT.

### 9. NIT: record the whole `/proc/<pid>/limits`

Recording the whole file catches `Max cpu time` too (expected unlimited). FINDINGS should name the expected `Max realtime timeout 200000 200000`: a soft value under the hard one would mean SIGXCPU first, which is a different signature.

### 10. NIT: name the decisive root-only check for the INCONCLUSIVE case

With `kernel.print-fatal-signals=1` the kernel logs `RT Watchdog Timeout (hard): <comm>[<tid>]` at the kill. It needs root, so the builder only names it in FINDINGS as the lead's option and never changes it (the brief already forbids that).

### 11. NIT: record cardwired's state per run

`cardwired` is a root daemon on the GPU path: Cardwire 0.12.3, mode Hybrid, `ExperimentalNvidiaBlock` false, eBPF process blocking. It logged no block in 49's window, so suspicion is low. Recording `cardwire get` and its journal lines costs nothing, and they are part of what B1's held card changes.

### 12. NIT: the package review's fallback

The brief names a Codex `gpt-6.2-sol` package review, which exists today. The Codex allowance ends on 2026-11-21, and the package may finish later. Name the fallback, a fresh Claude Opus reviewer, as `CLAUDE.md` does.

## Answers to the five questions

1. **Evidence summary:** mostly accurate. Wrong: the GPU "woke at the thaw" (finding 3). Imprecise: "253 ms" is the first observation, and memory.events at death come from run 2 only. Missing: the null backend's catch-up loop, soft equals hard, and the matching timing in run 1.
2. **Discrimination:** keep against demote with a held card is the right design. As written, the rules mislabel a chance B1 survival, a B1 without a realtime thread, an A run whose catch-up didn't happen, a failed demotion and a cleanup-path death (findings 1, 4 and 5). With the gates and the positive control, three runs are enough for the scoped claim.
3. **Buildable:** yes, apart from the demotion command (finding 1) and the copy details (finding 7). Sampling 10 ms of `schedstat` and `status` is cheap and unprivileged. The exit signal comes from the zombie's `/proc/<pid>/stat`, with Gradle's exit value as the fallback.
4. **Safe:** yes. The cgroup writes are 49's, checked by `scope.py`, and the scheduling changes are limited to the game's threads. Demoting while frozen (finding 2) closes the only path to his session's realtime audio threads. The rtkit stand-ins are a low-harm NIT (finding 8). The B1 mixer spinning at RR priority 1 for 200 ms on one of 16 CPUs, below his PipeWire's priority 20, is what package 49 already did.
5. **Step 4:** sensible. It needs the backend question first (finding 6), and its first two bullets can be partly answered from what is already on disk.
