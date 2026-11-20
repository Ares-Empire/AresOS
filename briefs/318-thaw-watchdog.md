# 318: why frozen worlds die on thaw

Board T364 (the sleeping world), brief number from `board brief`. A follow-up of package 49 (`reviews/49-memory-cuts/REPORT.md`): its two cover-freeze trials held memory for five minutes, then both games died with SIGKILL (exit 137) on thaw. The report left the sender unknown. Patrik's sleeping-world idea (freeze or swap the world while it isn't needed, wake it early) can't go further until we know what kills a thawed game.

**Builder:** a Claude Opus agent per step (Claude has room this week; this is a careful measurement with a known rig).

**Reviews:**
- **This brief:** one Claude Opus review, and no Codex brief review: `mac-capacity` asked on 2026-11-20 to halve Codex use.
- **The package:** a fresh Codex `gpt-6.2-sol` `high` context. It is a measurement report with no product code.

## What the lead already found (read-only, 2026-11-20)

- **No OOM.** The scope's `memory.events` were all zero at death. The journal has no systemd-oomd line, no kernel OOM line and no `NVRM` line around either thaw. The rig, its helper (`helper41.py`) and `aresos-shell` send no SIGKILL to the game. The scopes have no "Stopping" line, so systemd didn't stop them.
- **Each game had one realtime thread.** rtkit's journal lines: "Successfully made thread 424679 of process 424422 (…/java) … RT at priority 1" (23:27:04), and the same for thread 428539 of process 428293 (23:43:16). Priority 1 is OpenAL Soft's default (`rt-prio`), so this is very likely the game's audio mixer thread.
- **rtkit's limit is 200 ms.** `RTTimeUSecMax` is 200000. rtkit only grants realtime to a process that has set `RLIMIT_RTTIME` at or under that. A realtime thread that runs past the hard limit without blocking gets SIGKILL from the kernel. `kernel.print-fatal-signals` is 0, so the kernel logs nothing.
- **The timing fits.** SIGKILL came 253 ms after the return request (cover-freeze-2's observer). That is about the thaw plus 200 ms of uninterrupted running.
- **The other suspect: the NVIDIA card.** At both thaws `cardwired` logged "NVIDIA GeForce RTX 4060 Laptop GPU: Power state changed: D0". 49's rig ran without package 47's holder, so the card slept while the game was frozen and woke at the thaw. Package 49b's rig (which this package copies) holds the card awake for the whole run, which takes the GPU wake out of the trial.

**Hypothesis:** after the thaw, OpenAL Soft's realtime mixer runs more than 200 ms without blocking (catching up five minutes of audio clock), and the kernel's `RLIMIT_RTTIME` watchdog kills the game.

## Steps

One fresh agent per step. Each step commits, pushes `pkg/318-thaw-watchdog`, and keeps `reviews/318-thaw-watchdog/PROGRESS.md` true: what is done, what is left in order, and what the code doesn't show. The last step deletes it.

1. **The rig.**
   - Copy `reviews/49b-arena-rerun/rig/` to `reviews/318-thaw-watchdog/rig/`. Packages 49's and 49b's records stay as they are.
   - Allow 49's cover-freeze path again (`RECLAIM=600M FREEZE=1`, as 49 ran it), keeping 49b's bounded input, health watch and cleanup. Thaw on every exit path stays.
   - Add `RT=keep|demote` (default `keep`):
     - **Record, in both modes, before the freeze:** every thread of the game PID whose policy is `SCHED_FIFO` or `SCHED_RR`, with its tid, `comm`, policy and priority, and the game's `RLIMIT_RTTIME` soft and hard values from `/proc/<pid>/limits`.
     - **`demote`:** set each recorded realtime thread to `SCHED_OTHER`, for example with `chrt --other --pid 0 <tid>`. First check that the tid's `Tgid` is the game PID. Record the result, and record the policy again just before the thaw, in case something promoted it back. The owner's `RLIMIT_RTPRIO` is 0: an unprivileged thread may still switch to a normal policy, but only rtkit can make it realtime again.
   - Add a thaw sampler. From just before the thaw write until the game exits or 3 s pass, every 10 ms, record for each recorded realtime thread its `/proc/<pid>/task/<tid>/schedstat` first field (time on CPU, ns) and its state. Record how and when the game exits, with the signal.
   - After a surviving wake, keep 49b's wake window. Also record that the game is still alive 60 s after the return request, and any OpenAL or sound lines in its log after the wake.
   - **Tests without a game:** cover the realtime-thread parsing, the `Tgid` check (a tid of another process is refused), demotion of a stand-in thread, the sampler's stop at exit, and thaw on every exit path. Use stand-ins only. If a stand-in needs real realtime, rtkit's D-Bus `MakeThreadRealtime` is the user-level way, but plain-policy stand-ins are fine where they prove the logic.
   - Commit before step 2.
2. **The plan, committed before the first run.** Write `reviews/318-thaw-watchdog/PLAN.md`: the runs below and these verdict rules, word for word. Any later change to it is a PLAN-GAP; the verdict uses the committed text.
   - **Runs, in this order:**
     - **B1:** `RT=keep`, freeze as 49 (card held awake by the rig).
     - **A1 and A2:** `RT=demote`, otherwise the same.
   - **GPU SUSPECT:** B1 survives the thaw. Stop after B1, run no A trial, and report.
   - **WATCHDOG CONFIRMED:** all three of these hold:
     - B1 dies by SIGKILL;
     - between the thaw and its death, a recorded realtime thread's CPU time rises by at least 150 ms with no sample showing it asleep;
     - A1 and A2 both survive: alive 60 s after the return request, with frames recorded after the wake.
   - **WATCHDOG REFUTED:** A1 or A2 dies by SIGKILL.
   - **INCONCLUSIVE:** anything else. Report it, and run nothing more without the lead's OK.
3. **The runs** (each about 10 minutes): B1, then A1 and A2 unless B1 says GPU SUSPECT. Write `reviews/318-thaw-watchdog/FINDINGS.md`:
   - the verdict against the committed rules;
   - every run's recorded realtime threads, limits and sampler curve;
   - how this differs from 49's conditions.
4. **What the sleeping world could do about it.** This step is research and reading only: no product change and no extra runs. In `FINDINGS.md`, give each user-level way to avoid the kill, with its cost:
   - the mod pauses the audio device before the freeze and resumes it after the thaw (OpenAL Soft's `ALC_SOFT_pause_device` through LWJGL). Say whether Minecraft 26.2's bundled OpenAL Soft has it, judging by its version or the LWJGL class, read-only;
   - the supervisor demotes the game's realtime threads before the freeze. Does anything promote them again?
   - OpenAL Soft's `rt-prio = 0` for the whole game through its config file;
   - anything else you find.

   If the game log or OpenAL Soft's source shows why the mixer runs so long after a thaw (which backend is in use, the catch-up loop), say so with the line. Mark guesses as guesses.

   Then delete `PROGRESS.md` and open the PR.

## Rules

- **Package 49's rules apply** (`briefs/49-memory-cuts.md`, "Rules"). Only `reviews/318-thaw-watchdog/` and this brief change, and nothing under `mod/src`, `mod/dev` or `os/`.
- **Game runs:**
  - only through the rig, under the client-test lock;
  - with 6 GiB free;
  - headless only, never `wayland-0`;
  - never `./gradlew` yourself, never `--force`.
- **On exit 75,** wait about five minutes and retry, at most six times per run. Let other lock holders through between runs. A run that another builder's game or Gradle build overlapped is kept, marked and repeated.
- **Allowed writes outside the repo:**
  - `memory.reclaim` and `cgroup.freeze` on the rig's own game scope only, as in 49;
  - scheduling-policy changes only on threads of the rig's own game PID, checked by `Tgid`.

  Nothing else under `/sys`, `/proc` or `/etc`, and no sudo. Don't change `kernel.print-fatal-signals` or any other system setting. If you think one is needed, write it in `FINDINGS.md` for the lead.
- **Off limits:** never touch `~/.minecraft`, `~/.lunarclient`, Lunar Client or `~/AresOS-try`. Stop only what you started, by PID or by the unit you created.
- **The repo is public:**
  - no personal data (no hostnames, serials or user names in logs: write `owner` for the user);
  - no Mojang assets;
  - no jars;
  - keep the committed data proportionate, with three runs.
- **The report's name:** Claude agents can't create a file named `REPORT.md`. Use `PLAN.md` and `FINDINGS.md` as above.
- **Commits:** end each commit with:

  ```
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_015ffFyQnMDXVxFaVyNCKSXH
  ```

- **The PR:** title it "Package 318: why frozen worlds die on thaw". End its body with:

  ```
  🤖 Generated with [Claude Code](https://claude.com/claude-code)

  https://claude.ai/code/session_015ffFyQnMDXVxFaVyNCKSXH
  ```

- **Never** merge, push to main or use `--no-verify`.
