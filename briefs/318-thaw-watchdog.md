# 318: why frozen worlds die on thaw

Board T364 (the sleeping world), brief number from `board brief`. A follow-up of package 49 (`reviews/49-memory-cuts/REPORT.md`): its two cover-freeze trials held memory for five minutes, then both games died with SIGKILL (exit 137) on thaw. The report left the sender unknown. Patrik's sleeping-world idea (freeze or swap the world while it isn't needed, wake it early) can't go further until we know what kills a thawed game, and whether the real session would hit it too.

**Builder:** a Claude Opus agent per step (Claude has room this week; this is a careful measurement with a known rig).

**Reviews:**
- **This brief:** one Claude Opus review, `reviews/318-thaw-watchdog/BRIEF-REVIEW-1.md` (READY WITH CHANGES, all findings taken into this version). No Codex brief review: `mac-capacity` asked on 2026-11-20 to halve Codex use.
- **The package:** a fresh Codex `gpt-6.2-sol` `high` context; a fresh Claude Opus reviewer if Codex is unavailable. It is a measurement report with no product code.

## What is known (read-only, 2026-11-20; corrected by brief review 1)

- **No OOM.** The scope's `memory.events` were all zero at death (recorded for cover-freeze-2 only). The journal has no systemd-oomd line, no kernel OOM line and no `NVRM` line around either thaw. The rig, its helper (`helper41.py`) and `aresos-shell` send no SIGKILL to the game in that phase. The scopes have no "Stopping" line, so systemd didn't stop them.
- **Each game had one realtime thread.** rtkit's journal lines: "Successfully made thread 424679 of process 424422 (…/java) … RT at priority 1" (23:27:04), and the same for thread 428539 of process 428293 (23:43:16). Priority 1 is OpenAL Soft's default (`rt-prio`), so this is very likely the game's audio mixer thread.
- **The limit is 200 ms, soft and hard.** rtkit's `RTTimeUSecMax` is 200000, and OpenAL Soft sets both `RLIMIT_RTTIME` values to it. A realtime thread that runs past the hard limit without blocking gets SIGKILL from the kernel, not SIGXCPU. `kernel.print-fatal-signals` is 0, so the kernel logs nothing.
- **The rigs use OpenAL Soft's `null` backend.** Package 49's and 49b's `inner.sh` and `mod/dev/client-test.sh` set `ALSOFT_DRIVERS=null`. That backend renders every sample due since its clock started, in one loop that doesn't sleep until it has caught up. After five frozen minutes that is a long catch-up.
- **The timing fits.** cover-freeze-2 died 183–204 ms after the thaw; its observer first saw the zombie at 253 ms. Both scopes ended 339 and 344 ms after their thaws, so cover-freeze-1 died at about the same delay.
- **The NVIDIA card is not the suspect it seemed.** Its D0 lines came 380 and 517 ms *before* the thaws, from the rig's own `nvidia-smi` snapshot (`snap.py:112`). The card also woke about once a minute during each freeze, and the frozen games survived those wakes. Package 49b's rig, which this package copies, holds the card awake for the whole run anyway.

**Hypothesis:** with the `null` backend, OpenAL Soft's realtime mixer runs more than 200 ms without blocking after a thaw, and the kernel's `RLIMIT_RTTIME` watchdog kills the game. Whether the real session's backend (PipeWire or PulseAudio) does the same is a separate question for step 4.

## Steps

One fresh agent per step. Each step commits, pushes `pkg/318-thaw-watchdog`, and keeps `reviews/318-thaw-watchdog/PROGRESS.md` true: what is done, what is left in order, and what the code doesn't show. The last step deletes it.

1. **The rig.**
   - Copy `reviews/49b-arena-rerun/rig/` to `reviews/318-thaw-watchdog/rig/`, and the `frames/` it needs (`measure.sh:88` reads `../frames/`). Rename the `pkg49b` prefixes (scopes, `/tmp` and `.work` names) to `pkg318`. Packages 49's and 49b's records stay as they are.
   - 49b's base world went with its worktree, so plan a `setup-flat` creation run to make one.
   - Allow 49's cover-freeze path again (`RECLAIM=600M FREEZE=1`, as 49 ran it), keeping 49b's bounded input, health watch, card holder and cleanup. Thaw on every exit path stays.
   - Add `RT=keep|demote` (default `keep`). After the freeze is confirmed (`cgroup.events` frozen 1), in both modes:
     - **Record** every thread of the game PID whose policy is `SCHED_FIFO` or `SCHED_RR`, with its tid, `comm`, policy, flags and priority, and the game's whole `/proc/<pid>/limits` (expected: "Max realtime timeout" 200000 / 200000).
     - **`demote`:** check that the tid's `Tgid` is the game PID, then set each recorded thread to the normal policy with `chrt --reset-on-fork --other --pid 0 <tid>`. rtkit's threads carry `SCHED_RESET_ON_FORK`, and an unprivileged process may not clear it, so a plain `chrt --other` fails with "Operation not permitted". Check the policy again just before the thaw. If any thread of the game is still realtime then, the run is **INVALID**: thaw, record and stop it; it doesn't count for any verdict.
   - **The thaw sampler,** from just before the thaw write:
     - every 10 ms, for each recorded thread: the first field of `/proc/<pid>/task/<tid>/schedstat` (time on CPU, ns), and `voluntary_ctxt_switches` and `nonvoluntary_ctxt_switches` from its `status`. Any sleep resets the watchdog, so a voluntary switch, not a sampled state, shows that the thread blocked;
     - every 100 ms, a scan of all the game's threads for any realtime policy;
     - for 3 s in `keep` runs and 10 s in `demote` runs, so the whole catch-up is measured.
   - **The exit watcher:** a pidfd on the game until 60 s after the return request. It records when the game exits and with which signal, read from the zombie where possible, otherwise Gradle's exit value. It also records whether any rig cleanup step had started before the exit.
   - **For each run, record:**
     - the rtkit and `cardwired` journal lines;
     - `cardwire get` if it answers without root;
     - the card's `power/runtime_status` around the freeze and the thaw;
     - any OpenAL or sound lines in the game log.
   - After a surviving wake, keep 49b's wake window, and record that the game is still alive 60 s after the return request.
   - **Tests without a game:**
     - the realtime-thread parsing;
     - the `Tgid` check (a tid of another process is refused);
     - the demote command on a stand-in thread with `SCHED_RESET_ON_FORK` set. Set it yourself with a normal policy; the test must show that the plain `chrt --other` is refused and the rig's command works;
     - the INVALID path when a thread stays realtime;
     - the sampler and the exit watcher stopping at exit;
     - thaw on every exit path.

     Use plain stand-ins you start yourself. Don't ask rtkit for realtime threads: this account shares rtkit's per-user limits with the owner's session.
   - Commit before step 2.
2. **The plan, committed before the first game run.** Write `reviews/318-thaw-watchdog/PLAN.md`: the runs below and these verdict rules, word for word. Any later change to it is a PLAN-GAP; the verdict uses the committed text.
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
3. **The runs** (each about 10 minutes): S0, B1, then A1 and A2 unless B1 says NOT REPRODUCED. Write `reviews/318-thaw-watchdog/FINDINGS.md`:
   - the verdict against the committed rules;
   - every run's recorded realtime threads, limits, sampler curves and exit;
   - the measured catch-up: how long the demoted mixer ran after five frozen minutes;
   - how this differs from 49's conditions.
4. **What the sleeping world could do about it.** This step is research and reading only: no product change and no extra runs. Never test a real audio backend live: the game would play into the owner's session.
   - **The product's backend:** in the real session the game uses OpenAL Soft's PipeWire or PulseAudio backend (bundled with LWJGL 3.4.1). From the source, does that backend catch up after a long stall the way `null` does, or does it drop the backlog? Mark guesses as guesses.
   - **Each user-level way to avoid the kill, with its cost:**
     - the mod pauses the audio device before the freeze and resumes it after the thaw (`ALC_SOFT_pause_device`, present in the bundled OpenAL Soft). Does a resume or a backend restart start a new mixer thread that rtkit makes realtime again?
     - the supervisor demotes the game's realtime threads before the freeze (with `--reset-on-fork`). Does anything promote them again?
     - OpenAL Soft's `rt-prio = 0` or `rt-time-limit`, for the game alone through `ALSOFT_CONF`, never `~/.config/alsoft.conf`;
     - anything else you find.
   - **The longest safe freeze:** from the measured catch-up rate, how long the `null` backend could stay frozen before a thaw would cross 200 ms. Say what that means for the real backend, if anything.

   Then delete `PROGRESS.md` and open the PR.

## Rules

- **Package 49's rules apply** (`briefs/49-memory-cuts.md`, "Rules"). Only `reviews/318-thaw-watchdog/` and this brief change, and nothing under `mod/src`, `mod/dev` or `os/`.
- **Game runs:**
  - only through the rig, under the client-test lock;
  - with 6 GiB free;
  - headless only, never `wayland-0`, and always with `ALSOFT_DRIVERS=null`;
  - never `./gradlew` yourself, never `--force`.
- **On exit 75,** wait about five minutes and retry, at most six times per run. Let other lock holders through between runs. A run that another builder's game or Gradle build overlapped is kept, marked and repeated.
- **Allowed writes outside the repo:**
  - `memory.reclaim` and `cgroup.freeze` on the rig's own game scope only, as in 49;
  - scheduling-policy changes only on threads of the rig's own game PID, checked by `Tgid`, and on stand-in processes you started yourself for the tests.

  Nothing else under `/sys`, `/proc` or `/etc`, and no sudo. Don't change `kernel.print-fatal-signals` or any other system setting. If you think one is needed, write it in `FINDINGS.md` for the lead.
- **Off limits:** never touch `~/.minecraft`, `~/.lunarclient`, Lunar Client, `~/AresOS-try`, `~/.config/alsoft.conf` or any process of the owner's session (PipeWire included). Stop only what you started, by PID or by the unit you created.
- **The repo is public:**
  - no personal data (no hostnames, serials or user names in logs: write `owner` for the user);
  - no Mojang assets;
  - no jars;
  - keep the committed data proportionate, with four runs.
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
