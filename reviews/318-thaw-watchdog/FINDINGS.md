# 318: findings

Brief: `briefs/318-thaw-watchdog.md`. Plan and verdict rules: `PLAN.md`, committed in `eb499fb3` before S0 and unchanged since. Steps 2 and 3 by a Claude Opus 5.5 builder on 2026-11-20. Step 4, the research by reading only, is the last section, "What the sleeping world could do about it", by a second Claude Opus 5.5 builder the same day.

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
| B1 | `RT=keep`, `COVER=300 RECLAIM=600M FREEZE=1` | 1 | Died by SIGKILL, estimated 197–207 ms after the thaw write | VALID |
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

- **B1, the death.** The last sample, at +196.9 ms, shows the thread still running with 195.8 ms of CPU since its frozen value. The next sample, due about 10 ms later, found it gone. The watcher's pidfd saw the whole process gone at +367.3 ms. **Estimate, not measured directly:** the kill came between +196.9 and about +207 ms, at about 200 ms of CPU, where the hard limit lies, and the 160 ms after it were the JVM's teardown with 600 MiB in swap. The first sample after the thaw came 7.0 ms after the write, by when the thread had already used 6.15 ms; PLAN.md's measure doesn't count that part (see PLAN-GAP 1).
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

So the catch-up after this freeze is **about 350–356 ms of CPU, run in one stretch at nearly a full core**, about 1.3 ms of CPU per frozen second. That is 1.75 times the 200 ms limit. Before the freeze the mixer used about 0.45–0.7% of a core while the game ran and paused. Step 4 estimates from these numbers where a `null` thaw would cross the limit.

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
| Death after the thaw | 183–204 ms (cover-freeze-2, from its observer); cover-freeze-1 about the same | B1: estimated 197–207 ms |
| Realtime threads | One per game, priority 1 (rtkit's journal) | One per game, priority 1, `SCHED_RR` with `SCHED_RESET_ON_FORK` |

None of the differences touches the mechanism. 49's deaths came at the same delay after the thaw as B1's, with the same single priority-1 thread and the same `null` backend, so the same watchdog very likely killed them too. The card, which brief review 1 had already cleared, stayed awake here and B1 died anyway. The longer delay before the thaw changes nothing for the mixer: it is frozen until the write.

## PLAN-GAP

1. **A third limit of the measure, not written in PLAN.md.** PLAN.md counts only samples at or after the thaw write, so the CPU time between the write and the first sample after it is left out: up to 10 ms. In B1 that was 6.15 ms (first sample at +7.0 ms), in A2 5.37 ms, in A1 none (first sample at +0.5 ms). It makes the measure read low, never high, so it can't have made a threshold pass. With it, B1's stretch would be 195.8 ms and A2's 354.5 ms. No verdict changes; the verdict uses the committed text.

Nothing else in PLAN.md needed a change.

## For the lead

- **No decision is needed for the verdict.** All three trials were valid on the first try, and the rules give WATCHDOG CONFIRMED.
- **Optional:** a direct sighting of the sender would take `kernel.print-fatal-signals=1` (root) during one more `RT=keep` run. The rules don't need it.

## Inputs from the runs for step 4

What the next section builds on:
- the catch-up after 267.5 s frozen: about 350–356 ms of CPU in one stretch (above);
- the mixer, when running normally, wakes about 198 times a second;
- the realtime thread is named `Render thread`, not `alsoft-mixer`, so a supervisor that demotes "OpenAL's thread" by name would miss it: pick realtime threads by policy, as the rig does;
- after the demotion nothing promoted the thread again within 60 s, with the `null` backend.

## What the sleeping world could do about it

Step 4, by a Claude Opus 5.5 builder on 2026-11-20: reading only. No game or rig run, no real audio backend, nothing changed outside this file. Each claim cites a file and line or a tagged source. **Guess** marks what the sources don't settle.

### The sources

- **The bundled OpenAL Soft is release 1.25.1.** LWJGL 3.4.1's `lwjgl-openal-3.4.1-natives-linux.jar` (from the Gradle cache) holds a `libopenal.so` with the version string `1.1 ALSOFT 1.25.1`, and a `libopenal.so.git` file naming commit `c41d64c6`. That is `kcat/openal-soft`'s commit "Release 1.25.1", the one the tag `1.25.1` points to. The library's extension string lists `ALC_SOFT_pause_device`. OpenAL Soft paths below are at that tag: `https://github.com/kcat/openal-soft/blob/1.25.1/<path>`.
- **PipeWire 1.6.9**, this laptop's version (`pipewire --version`, rpm `pipewire-libs-1.6.9`): `https://gitlab.freedesktop.org/pipewire/pipewire/-/blob/1.6.9/<path>`.
- **rtkit 0.11** (rpm `rtkit-0.11`, started without options, so its built-in defaults hold): `https://github.com/heftig/rtkit/blob/v0.11/rtkit-daemon.c`.
- **LWJGL 3.4.1's `lwjgl-openal-3.4.1.jar`** (read with `javap`), and the mod's sound code under `mod/src`.

### 1. The product's backends have no catch-up loop

**Which backend the game picks.** OpenAL Soft tries `pipewire` first, then `pulse`, and `null` last (`alc/alc.cpp:221-271`). The PipeWire backend steps aside only if libpipewire is too old or PipeWire reports no audio nodes (`alc/backends/pipewire.cpp:2215-2237`). In the real session, with PipeWire as the sound server, the game very likely uses the PipeWire backend. **Guess:** nobody has seen it in a real session. The game log's "OpenAL initialized on device …" line is a hint, not proof: a device name alone doesn't establish the backend (`No Output` is the `null` backend).

| | `null` (the rigs) | PipeWire (most likely the product's) | PulseAudio (the fallback) |
|---|---|---|---|
| What sets the pace | the backend's own clock: `steady_clock` from the thread's start (`alc/backends/null.cpp:67-68`) | PipeWire's graph, one `process` call per cycle | the server's write requests |
| What one wake renders | everything due since the start. An inner loop renders update after update until it has caught up, with no sleep in between (`null.cpp:69-99`) | what the buffer asks for: `pw_buffer::requested` (`pipewire.cpp:1492-1534`), which PipeWire sets to one cycle (`src/pipewire/stream.c:461`) | the `nbytes` the server asks for (`alc/backends/pulseaudio.cpp:751-773`), OpenAL asks for a `tlength` of the device's buffer size (`pulseaudio.cpp:1008`, `1055`), a target for the server, not a cap the callback enforces |
| After a long stall | the whole backlog in one go: about 1.3 ms of CPU per frozen second here | no catch-up loop: each call renders what PipeWire requests | no catch-up loop: each call renders the `nbytes` the server requests |
| The thread that mixes | the backend's own thread, started with `std::thread` (`null.cpp:120-130`) | the PipeWire thread loop OpenAL creates per device, named `ALSoftP<n>` (`pipewire.cpp:1579-1590`). The stream connects without `PW_STREAM_FLAG_RT_PROCESS` unless `[pipewire] rt-mix = true` (`pipewire.cpp:1728-1730`; default false, `alsoftrc.sample:430-434`). PipeWire then gives the node the `main` loop class and `node.async` (`stream.c:2095-2099`), so `process` runs on that thread loop | libpulse's threaded mainloop thread (`pulseaudio.cpp:337`) |
| Realtime for that thread | yes. `SetRTPriority()` at the thread's start (`null.cpp:64`) asks the kernel, then rtkit, for `SCHED_RR` priority 1 (`core/helpers.cpp:373-396`, `398-480`, `484-491`) | not from OpenAL: `pipewire.cpp` has no `SetRTPriority` call | not from OpenAL: `pulseaudio.cpp` has no `SetRTPriority` call. **Guess:** libpulse doesn't make it realtime either |

Of OpenAL Soft's Linux backends only `null`, ALSA, OSS, JACK, sndio and Solaris ask for realtime (`null.cpp:64`, `alsa.cpp:460` and `538`, `oss.cpp:286`, `jack.cpp:405`, `sndio.cpp:89`, `solaris.cpp:94`). Whether ALSA catches up after a stall was not read.

**The game may still hold a realtime thread under PipeWire.** PipeWire's client config on this laptop loads `libpipewire-module-rt` into every client (`/usr/share/pipewire/client.conf:45-57`, `flags = [ ifexists nofail ]`). That module makes PipeWire's own data-loop threads realtime through rtkit, and when it uses rtkit it lowers the process's `RLIMIT_RTTIME` to rtkit's 200 ms (`src/modules/module-rt.c:1003-1019`). rtkit's journal on this laptop shows PipeWire clients (`pipewire`, `wireplumber`) at priority 20; the games' grants, all from rigs with `null`, are at priority 1. **Guess:** under PipeWire the game has one such data-loop thread at priority 20. It wakes once per graph cycle and blocks again, and OpenAL's stream doesn't run on it, so it has no backlog to catch up. Only a real session can show whether it exists and what it does after a thaw.

**In short:** by the source, neither real backend has the `null` backend's elapsed-time catch-up loop, and OpenAL asks for no realtime in either. So the kill seen in B1 is, by the source, a `null` behavior (and maybe ALSA's or OSS's, not read). Which backend the product actually selects, which of its threads run realtime, and how it behaves after a thaw stay open: nobody has watched a real-backend thaw.

### 2. Ways to avoid the kill, with their costs

#### a) Pause the device around the freeze (`ALC_SOFT_pause_device`)

- **What it does.** `alcDevicePauseSOFT` stops the backend and marks the device paused (`alc/alc.cpp:3468-3485`). `alcDeviceResumeSOFT` starts it again (`alc.cpp:3488-3532`). LWJGL 3.4.1 has both, `SOFTPauseDevice.alcDevicePauseSOFT(long)` and `alcDeviceResumeSOFT(long)`, and `ALCCapabilities.ALC_SOFT_pause_device` says whether the device offers them (`javap` on `lwjgl-openal-3.4.1.jar`).
- **With `null`:** the pause joins the mixer thread (`null.cpp:132-137`). The resume starts a new one (`null.cpp:120-130`) whose clock starts then (`null.cpp:67-68`), so there is no backlog. **The new thread asks for realtime again** (`null.cpp:64`): every resume means a new rtkit grant, with a new tid.
- **With PipeWire:** the pause sets the stream inactive (`pipewire.cpp:1843-1852`), and the resume sets it active again (`pipewire.cpp:1762-1767`). The thread loop is made once per opened device (`pipewire.cpp:1579-1590`), so a resume makes no new thread, and OpenAL asks for no realtime. **Guess:** Minecraft reloading its sound engine closes and reopens the device: a new backend and a new thread loop, still without a realtime request from OpenAL.
- **What the mod does today doesn't help.** The covered home screen pauses Minecraft's sounds (`mod/src/client/java/dev/aresos/client/HomeScreen.java:91-109`, `SoundManager.pauseAllExcept`). That pauses sources, not the device. The mixer keeps mixing silence, and B1 shows that silence builds a fatal backlog too.
- **Costs.**
  - A mod change: an accessor for Minecraft's device handle. **Guess:** the `currentDevice` field of `com.mojang.blaze3d.audio.Library`. The mod has no such accessor today, only a game-test one for `SoundEngine` (`mod/src/gametest/java/dev/aresos/test/mixin/SoundEngineTestAccess.java`).
  - A handshake before every freeze: the supervisor asks, the mod pauses the device and answers, and only then comes the freeze. A mod that doesn't answer must not block the freeze or the wake, and the mod must resume after every thaw, including a failed one.
  - With `null`, one rtkit request per wake. rtkit's limits are per user and shared with the owner's session: at most 25 actions in 20 s and 25 supervised threads (`rtkit-daemon.c:151-157`).
  - It covers only the device Minecraft opened. Any other realtime thread in the game (PipeWire's, for one) is untouched.
  - In return it is the only way that also stops the stream while frozen. **Guess:** PipeWire's graph doesn't schedule an inactive stream, so the server sees no missed cycles from a frozen game. The kill doesn't need this.

#### b) The supervisor demotes the game's realtime threads (measured in A1 and A2)

- **What it does.** `chrt --reset-on-fork --other --pid 0 <tid>` on each thread of the game whose policy is `SCHED_FIFO` or `SCHED_RR`, with the `Tgid` check, as the rig does. A1 and A2 show that it works with `null`.
- **Pick threads by policy, not by name.** In this build the mixer is named `Render thread` (point 4), and a realtime thread from PipeWire would carry PipeWire's name.
- **Demote after the freeze is confirmed, then check again just before the thaw** (the rig's order). A frozen game can't start a new thread between the demotion and the thaw. A thread that is realtime again at the check gets demoted again (the rig marks such a trial INVALID instead).
- **Does anything promote them again?**
  - OpenAL asks once, when the mixer thread starts (`null.cpp:64`). The running thread never asks again. A device restart (a resume after a pause, a reset, a reopen, a sound engine reload) makes a new thread that asks again (`null.cpp:120-130`), so the supervisor scans at every freeze instead of remembering tids.
  - rtkit changes a policy only when asked (`rtkit-daemon.c:765`, its `MakeThreadRealtime` path). On its own it only demotes, when its canary starves (`rtkit-daemon.c:903-1024`).
  - PipeWire's `module-rt` asks when one of its threads starts (`module-rt.c:845`). **Guess:** it doesn't ask again for a running thread.
  - Measured with `null`: in A1 and A2, no realtime thread and no new rtkit grant for 60 s after the thaw.
- **Costs.**
  - The demoted thread stays a normal thread until the next device restart. That is harmless for `null`, which plays nothing. **Guess:** for a real backend's realtime thread (the PipeWire data loop, if there is one), a little more risk of crackle under heavy load.
  - Supervisor code: the `Tgid` check, the pre-thaw check, and `--reset-on-fork`, without which an unprivileged `chrt --other` is refused (step 1's test).
  - No mod change. It works for any backend and any realtime thread.

#### c) `rt-prio = 0` or `rt-time-limit = false` for the game alone, through `ALSOFT_CONF`

- **Where it is read.** OpenAL Soft reads `/etc/openal/alsoft.conf`, the XDG system dirs, `~/.config/alsoft.conf`, an `alsoft.conf` next to the program, and last the file `ALSOFT_CONF` names (`alc/alconfig.cpp:427-530`). Later values win (`alsoftrc.sample:3-4`). So a file set through `ALSOFT_CONF` for the game alone overrides the keys it names and leaves the owner's own file in force for the rest. Both keys are read once, when the library starts (`alc.cpp:499-502`).
- **`rt-prio = 0`:** `SetRTPriority()` returns at once (`core/helpers.cpp:486-487`; `alsoftrc.sample:201-208`). The mixer stays a normal thread and its catch-up runs to the end, as in A1 and A2. No rtkit request at all.
- **`rt-time-limit = false`:** OpenAL no longer lowers `RLIMIT_RTTIME` (`helpers.cpp:436-444`; `alsoftrc.sample:210-213`). rtkit then refuses realtime, because it requires a hard limit of at most 200 ms in `/proc/<pid>/limits` (`rtkit-daemon.c:627-673`, checked at `795` and `812`). OpenAL falls back to a nice level of -15 (`helpers.cpp:463-472`), which rtkit grants without that check (`rtkit-daemon.c:835`). This is weaker than `rt-prio = 0`: if anything else in the process lowers the limit first (PipeWire's `module-rt` does, `module-rt.c:1014-1019`) or the game inherits a low one, rtkit grants realtime and the kill is back.
- **Costs.**
  - It changes only the backends that ask for realtime: `null` (the rigs) and the fallbacks ALSA and OSS. For PipeWire and PulseAudio it changes nothing.
  - On an ALSA fallback the mixer would no longer be realtime: more crackle risk under load.
  - One more file to ship, and an environment variable on the game's launch. **Guess:** anything the game starts directly inherits the variable, so an app using OpenAL Soft started from the game would read the same file.

#### d) Other things found

- **A laptop sleep is no risk.** libstdc++'s `steady_clock` is `CLOCK_MONOTONIC`, which doesn't advance while the system is suspended (`clock_gettime(2)`). So the `null` mixer sees no gap after a suspend. Only stopping the process while the system runs (a cgroup freeze, `SIGSTOP`) builds a backlog.
- **The limit can't be raised.** rtkit refuses any process whose hard `RLIMIT_RTTIME` is above 200 ms (`rtkit-daemon.c:142`, `665`), and raising a hard limit needs privilege.
- **Keep `[pipewire] rt-mix` off** (its default). With it OpenAL would mix on PipeWire's realtime thread (`pipewire.cpp:1728-1730`). Rendering one cycle per call keeps the risk small, but nothing is gained.
- **An upstream fix** would cap the `null` backend's backlog: drop what is more than a buffer behind instead of rendering it all. It would reach the game only through a new LWJGL, so it is nothing to wait for.

### 3. The estimated crossover for `null`

- The catch-up grows linearly with the frozen time: each frozen second adds a second of samples for the inner loop to render (`null.cpp:75-86`).
- Measured: 350–356 ms of CPU after 267.5 s frozen, so 1.31–1.33 ms per frozen second. B1 died at about 196–200 ms of it.
- **200 ms ÷ 1.33 ms per frozen second ≈ 150 s.** This is an extrapolation from one freeze length of one workload: near silence (the covered home screen pauses every sound) on this laptop's CPU. Music, many sources or HRTF cost more per second, and a slower or throttled CPU renders more slowly, so the crossing can come much earlier. No freeze length is shown to be safe; don't use a time limit in place of the demotion.
- **For the real backends: this number doesn't apply.** Their source has no elapsed-time catch-up loop, so it doesn't bound a real-session freeze; how a real backend behaves after a thaw stays open. Rig and CI runs of the sleeping world all use `null`: they need the demotion (or `rt-prio = 0`), not a time limit.

### 4. Why the thread is named `Render thread`

- The source does name it. `althrd_setname(GetMixerThreadName())` comes right after `SetRTPriority()` (`null.cpp:64-65`), with the name `alsoft-mixer` (`core/device.h:413`), and that string is in the binary.
- But in LWJGL's build `althrd_setname` does nothing. It calls `pthread_setname_np` only if `HAVE_PTHREAD_SETNAME_NP` was found at build time (`common/althrd_setname.cpp:67-74`), and the bundled `libopenal.so` imports no `pthread_setname_np` (`nm -D`: it imports `pthread_setschedparam`, `sched_get_priority_max`, `sched_get_priority_min` and `setrlimit`). So the thread keeps the name Linux gave it, its creator's, and Minecraft opens the device from its `Render thread`.
- **Guess, why the build lacks it:** the CMake check is `check_symbol_exists(pthread_setname_np pthread.h …)` (`CMakeLists.txt:711`), and the file defines no `_GNU_SOURCE`, which glibc needs before it declares `pthread_setname_np`.
- So in this build every OpenAL thread that would name itself (`alsoft-mixer`, `alsoft-record`) carries its creator's name, and a supervisor can't find it by name.

### Recommendation for the sleeping world

**Use b).** The supervisor demotes the game's realtime threads, picked by policy, after the freeze is confirmed, and checks again before the thaw. Why:
- It is the only way measured to work here (A1, A2), and the rig already has the code and its tests.
- It needs no mod change and no handshake, so a busy or stuck game can't hold up a freeze or a wake.
- It covers every backend and any realtime thread, whatever its name, including ones nobody knows about yet.
- Its cost is small: the demoted thread stays a normal thread until the next device restart, which `null` never notices.

By the source, the PipeWire backend has no catch-up loop and OpenAL doesn't make its mixer realtime; whether the kill can happen in the product stays open until a real session shows the backend and its threads. b) is the safety net for the fallbacks (ALSA, `null`) and for whatever realtime thread PipeWire adds to the game. Every rig and CI run of the sleeping world uses `null`, so those need b) (or `rt-prio = 0`) to survive a thaw.

Don't make c) the fix: by the source it does nothing for the PipeWire and PulseAudio backends, where OpenAL asks for no realtime, and PipeWire's own module can undo `rt-time-limit = false`. `rt-prio = 0` is a fine one-line choice for a rig that wants long freezes without the demotion code. Keep a) for later. It is the cleanest for the audio (no stream running while frozen), but it costs a mod change, a handshake on every freeze and, with `null`, an rtkit request on every wake. Take it up only if a real-session thaw shows audio trouble.

**Before relying on the source reading,** a real session should show, without freezing anything and read-only: the game log's "OpenAL initialized on device" line (a hint only), the audio libraries the game process has loaded (`/proc/<pid>/maps`), and the game's realtime threads (policy, priority, `comm`). Together these identify the backend and its realtime threads better than the device name alone. Once the release with the home screen runs on the laptop, the lead can read them from the running game. A real thaw test is a decision for a later package.

## Known limits (review 1)

Two latent paths in the rig, both inherited from packages 49 and 49b. They are filed here under decision 24's bar rather than fixed: the rig is finished evidence, not reused tooling, and neither path can lose data.

- **The recovery shortcut** (REVIEW-1 finding 2). `rig/start.sh` copies the product's labwc `rc.xml`, so its Super+Ctrl+Escape binding (`aresos-desktop hide-cover`) is live in the rig's compositor. Through the inherited `XDG_RUNTIME_DIR` it could reach an installed supervisor and hide its startup cover. The rig's virtual keyboard never sends that combination. A rig reused for the sleeping world should get its own compositor config without host-control bindings.
- **A controller killed while frozen** (REVIEW-1 finding 3). The thaw and stop run from the measurement shell's `EXIT` trap. If that shell is SIGKILLed while the game is frozen, the frozen game and its compositor scopes stay behind and hold their memory until stopped by hand (`systemctl --user stop 'pkg318-*'`). A reused rig should give an independent watcher both scopes.
