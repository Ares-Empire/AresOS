# Package 47: client-test and NVIDIA power cycling

## Done

`mod/dev/client-test.sh` takes the shared client lock and checks room again before waking NVIDIA. Before its NVIDIA probe it starts an idle CUDA context on the same PCI device as the selected render node. Explicit Intel/software runs do not start a holder. NVIDIA is skipped if holding fails; `auto` retains the existing Intel/software fallback, and an explicit `--gpu nvidia` fails rather than probing without the holder.

`mod/dev/env.sh` calls the installed driver's `libcuda.so.1` through Python's standard-library `ctypes`; no CUDA toolkit or GPU work loop is needed. It requires the UVM module and accessible device to be present already. Initialization has a 30-second deadline, and the run-owned holder scope has a five-second stop timeout. After review fix 1, an independent supervisor watches the script through a pidfd, owns scope launchers, and keeps the shared lock through ordered cleanup: client scopes first, CUDA worker last. CUDA calls run only in that worker. The stand-in tests below cover parent death during hanging initialization/context creation, parent SIGKILL followed by a hanging release, persistent clients, and holder failure after readiness; they establish bounded cleanup in those tested conditions. They do not establish recovery from an unkillable kernel task or failure of the supervisor itself. Nothing is cached across runs or boots.

Only those two implementation files change; the review fix also adds a reproducible stand-in lifecycle harness under this review directory. The branch includes current main through the merges before hosted verification. PR: [#103](https://github.com/Ares-Empire/AresOS/pull/103).

## Verified

### Historical journal: what can actually be recovered

Read-only commands, using CET throughout:

```sh
journalctl --list-boots --no-pager
journalctl -k -b -1 --until '2026-11-14 05:50:00' --no-pager -o json --grep='NVRM|D3cold|D0|01:00'
journalctl -b -1 --until '2026-11-14 05:51:00' --no-pager -o json --grep='aresos-dev-.*client-test'
```

At investigation time, boot `-1` spans November 13–14 and boot `0` began November 15. The first `journalctl -k --since ...` query returned `-- No entries --` because `-k` defaults to the current boot; specifying `-b -1` retrieved the incident. JSON timestamps and messages were extracted locally; the public excerpts below omit hostnames, account paths and GPU identifiers.

**Historical D3cold/D0 cycle count: unavailable.** The retained kernel journal contains device capability messages mentioning D0/D3cold, but no normal suspend/resume transition records for the NVIDIA PCI device. Scope starts/stops show opportunities to wake or suspend, not actual power transitions. No contemporaneous runtime-status/counter trace is retained. The scripts keep one current probe log and compositor log, with no historical rotation; those files have been overwritten by subsequent runs. Therefore neither the brief's “dozens” count nor a causal link between cycling and the failure can be verified from these logs.

Before the failure, this boot has **78 NVIDIA client-run scope starts and 54 NVIDIA probe scope starts**. The difference includes older script versions whose probes were not separate scopes. From midnight November 14 to the failure there are **11 NVIDIA probe starts and 11 NVIDIA run starts**. These are counts of scopes, not GPU cycles. The last three pairs all belong to package 36:

| Probe started | Client scope started |
|---|---|
| 04:10:19.342 | 04:10:21.844 |
| 04:19:08.321 | 04:19:10.729 |
| 05:44:15.142 | 05:44:17.567 |

For the incident's pair, the probe stopped at **05:44:17.506**, the client scope started 61 ms later, and the client scope ended at **05:50:17.005**. The first incident error was therefore about **5 min 12 s into the client scope**, rather than at its probe/run boundary:

```text
05:49:29.565 NVRM: Xid (PCI:0000:01:00): 62, [diagnostic words omitted]
05:49:29.571 NVRM: GPU0 _kgspRpcGspEventPmuHalted: Received signal from GSP that PMU has halted.
05:49:29.571 NVRM: Xid (PCI:0000:01:00): 154, GPU recovery action changed from 0x0 (None) to 0x1 (PF FLR)
05:49:33.725 NVRM: GPU0 RmCheckForGcxSupportOnCurrentState: NVRM, Failed to get GCx pre-requisite, status=0x62
```

The GCx error then repeats about every five seconds. At 05:50:38, the next NVIDIA probe ended after roughly 254 ms, an Intel probe started, and the subsequent package 36 client scope used Intel. Earlier errors also exist: Xid 31 at 18:01 and 19:02 on November 13, and NVIDIA allocation failures at 04:08:49, 04:19:03 and 04:28:32 on November 14. Thus 05:49:29 is the first error of this persistent incident, not the boot's first NVIDIA error. The journal cannot establish HDMI detection, the exact triggering GPU operation or the underlying driver defect.

### Measurement on this laptop

Kernel `7.2.9-ogc3.1.fc44.x86_64`, NVIDIA open driver `615.78.08`, RTX 4060 Laptop GPU at `0000:01:00.0`. Read-only checks returned `power/control = auto`, `Runtime D3 status: Enabled (fine-grained)`, and an initially suspended card. `nvidia_uvm` and `/dev/nvidia-uvm` were already present before testing.

The local sampler (`.work/47/measure.py`) reads `power/runtime_status`, `runtime_active_time` and `runtime_suspended_time` every 20 ms. It starts sampling three seconds before the command and continues after the command exits: initially 15 seconds, extended to 30 seconds for the complete changed runs. It writes CSV timestamps and command output under `.work/47/`. Reading these files did not wake the initially suspended card. No `nvidia-smi` polling was used. All actual client runs used `mod/dev/client-test.sh`, its shared lock, room checks, private headless compositor and null audio; no `--force` or direct Gradle invocation was used.

The counters are device-wide. The lock serializes development clients, not every possible GPU user; scope timing correlates the observed baseline resumes with its running client without identifying each GPU caller.

| Measurement | Wake-ups / suspends | Active-time increase | Suspended-time increase | Result |
|---|---:|---:|---:|---|
| Unchanged script, 505.461 s observation | 8 / 8 | 476,573 ms | 28,888 ms | Existing client assertion failed after 8m 4s |
| Open `/dev/nvidia0` for 45 s, 63.164 s observation | 0 / 0 | 0 ms | 63,164 ms | Card stayed suspended; opening the fd did not request D0 |
| Idle CUDA context for 45 s, 65.499 s observation | 1 / 1 | 56,943 ms | 8,556 ms | Active throughout the hold, then suspended |
| Changed script interrupted to merge newer main, 58.480 s observation | 1 / 1 | 31,926 ms | 26,554 ms | Ctrl+C exit 130; returned to suspend |
| Complete changed run 1, 847.470 s observation | 1 / 1 | 821,958 ms | 25,512 ms | Exit 0, `BUILD SUCCESSFUL in 13m 30s` |
| Complete changed run 2, 840.275 s observation | 1 / 1 | 816,939 ms | 23,337 ms | Exit 0, `BUILD SUCCESSFUL in 13m 23s` |

The unchanged script's probe started at **15:23:21.320**, its client scope at **15:23:23.858**, and the card's first observed resume was **15:23:22.254**. Probe and run shared that initial wake. Seven further resumes occurred during the game: **15:25:26.908, 15:26:03.277, 15:26:16.562, 15:26:35.745, 15:27:07.519, 15:27:27.544 and 15:29:43.753**. The card returned to suspend at **15:31:34.857** after the failed run. This rules out probe-result caching alone as a way to bound a complete run to one cycle: it would not remove these seven in-game resumes. A cache implementation was not added or benchmarked.

The direct device-fd and CUDA experiments each took the shared client lock and repeated the room check. Both exited 0. The fd trial establishes that opening the device alone does not request D0; it did not separately test leaving the fd open after another process wakes the card. The CUDA experiment used `cuInit`, `cuDeviceGetByPCIBusId`, `cuDevicePrimaryCtxRetain`, a 45-second idle wait, and `cuDevicePrimaryCtxRelease_v2`. Its suspended counter did not increase during the hold; it resumed at **15:33:58.781**, became active at **15:34:00.016**, and suspended at **15:34:55.707** after release.

Experiment commands:

```sh
python3 .work/47/measure.py fd-holder bash .work/47/holder-trial.sh fd
python3 .work/47/measure.py cuda-holder bash .work/47/holder-trial.sh cuda
python3 .work/47/measure.py cancel-int python3 .work/47/cancel-run.py int
python3 .work/47/measure.py cancel-scope python3 .work/47/cancel-run.py scope-kill
```

This matches NVIDIA's documentation: fine-grained power management may suspend idle graphics clients, whereas CUDA applications keep the GPU active. The primary-context API retains a reference until release. Sources: [driver 615.78.08 RTD3 documentation](https://download.nvidia.com/XFree86/Linux-x86_64/615.78.08/README/dynamicpowermanagement.html), [CUDA primary-context API](https://docs.nvidia.com/cuda/cuda-driver-api/cuda_driver_api/group__CUDA__PRIMARY__CTX.html).

### Lifecycle and failure checks

`bash -n mod/dev/env.sh mod/dev/client-test.sh` and `git diff --check`: exit 0, no output. Syntax was also checked with `bash -n mod/dev/env.sh mod/dev/client-test.sh mod/dev/build.sh mod/dev/run-hub.sh`: exit 0. CLI checks returned the expected exit 2: `mod/dev/build.sh --daemon` printed that the daemon switch is refused; `mod/dev/client-test.sh --gpu invalid` printed the accepted GPU choices. Neither started a build or GPU probe.

The local lifecycle harness compiled a stand-in `libcuda.so.1` with `cc -shared -fPIC .work/47/fake-cuda.c -o .work/47/fake-lib/libcuda.so.1`. It ran the actual `aresos_hold_nvidia` helper with that library through `LD_LIBRARY_PATH`, recording init/retain/release calls. No stand-in game or owner tool was executed. `python3 .work/47/check-helper.py > .work/47/helper-checks-final.log 2>&1`: exit 0, all seven cases passed:

```text
normal      PASS exit 0   init/retain/release
fail        PASS exit 7   init
int         PASS exit 130 init/retain/release
term        PASS exit 143 init/retain/release
hup         PASS exit 129 init/retain/release
parent-kill PASS exit -9  init/retain/release
hang        PASS exit 7   init (29.6 seconds)
```

The harness deliberately prefilled the readiness log with stale `READY` text; a failed init still refused, confirming that startup truncates it. Each case also verified that its private lock could be reacquired. An initial harness run failed the immediate lock check after killing its parent because the harness itself had an unscoped 100 ms `sleep` child that inherited the lock. The harness wait was changed to a Bash builtin loop, removing that unrelated child; the unchanged assertions then passed. The production helper was subsequently tested again from the final implementation, including the initialization deadline.

Real headless interruption checks used `.work/47/cancel-run.py` to start the actual client script, wait for its own game scope, and signal only that script or that scope:

- Ctrl+C: client exit **130**, no scopes of that script remained. The journal has game scope stopped at **15:36:00.729**, then holder stopped at **15:36:01.357**.
- Game scope killed with KILL: client exit **137**, no scopes of that script remained, holder stopped at **15:36:31.618**, and the card was subsequently read as suspended.
- A preliminary full changed run was cancelled with Ctrl+C to merge newly arrived package 46. It exited **130** after 22 s; its measured trace contains one resume and one suspend, with the card suspended again at **15:37:53.296**. Its game scope stopped before its holder scope.

The first two short cancellation traces ended their original 15-second observation windows before the delayed runtime suspend; follow-up reads confirmed suspension. The preliminary full-run cancellation and complete runs use the longer observation window. The hard-parent-kill case was tested with the stand-in context, not by orphaning a real game.

A current-boot kernel audit (`journalctl -k -b 0 --since '2026-11-17 15:23:00' --no-pager -o json --grep='NVRM'`) returned one line at **15:32:50.508**, during the direct device-fd trial and before any CUDA experiment: `NVRM: invalid 42 structure size, expected 32, got 44!`. The kernel entry does not identify its caller, so that timing is a correlation. There were no Xid/GCx messages or additional NVRM lines during the CUDA trials and complete runs through this audit. The warning's cause was not established.

### Complete builds and hosted checks

Both complete changed commands use implementation commit `6296f07d`, after merging current main through `b5388476`. No implementation changed between them:

```sh
python3 .work/47/measure.py held-final-1 mod/dev/client-test.sh --keep-screenshots .work/47/held-final-1-screenshots build
python3 .work/47/measure.py held-final-2 mod/dev/client-test.sh --keep-screenshots .work/47/held-final-2-screenshots build --rerun-tasks
```

Run 1: exit **0**, `BUILD SUCCESSFUL in 13m 30s`, `19 actionable tasks: 16 executed, 3 up-to-date`. All client checks and all **104 required server game tests** passed. Unit XML reports **272 cases, zero failures/errors, six pre-existing Windows-only skips**. The script copied **92 PNGs** to its requested `.work/47/held-final-1-screenshots/` directory and reported NVIDIA GeForce RTX 4060 Laptop GPU. The card resumed once, then its suspended counter remained fixed until shutdown; it suspended again at **15:52:51.217**.

Run 2: exit **0**, `BUILD SUCCESSFUL in 13m 23s`, `19 actionable tasks: 19 executed`. All client checks and all **104 required server game tests** passed again. Unit XML again reports **272 cases, zero failures/errors, six pre-existing Windows-only skips**. Another **92 PNGs** were copied to `.work/47/held-final-2-screenshots/`; the script again reported NVIDIA GeForce RTX 4060 Laptop GPU. `--rerun-tasks` forced the complete build's tests to execute again rather than accepting up-to-date tasks. This trace also contains exactly one resume and one suspend; its suspended counter remained fixed until shutdown and the card suspended again at **16:07:48.528**.

The unchanged baseline command was `python3 .work/47/measure.py baseline mod/dev/client-test.sh --keep-screenshots .work/47/baseline-screenshots build`: exit **1**, `BUILD FAILED in 8m 4s`, `Apps picked up a copy while crafting was occupied`, in `MyAppsClientGameTest.commands`. The subsequently merged package 46 already fixes its cause with a serverbound close-packet barrier before filling the crafting grid; no assertion was changed by this package. The preliminary changed command (`held-run-1`, same arguments as run 1) was deliberately interrupted to merge that new main, not counted as a passing run.

Hosted checks, after fetching and merging `origin/main` before dispatch:

- [Mod 44105397900](https://github.com/Ares-Empire/AresOS/actions/runs/44105397900): **success**, watched with `gh run watch 44105397900 --exit-status --interval 60` (exit 0). Both builds passed all 104 required game tests, printing `BUILD SUCCESSFUL in 1m 18s` and `BUILD SUCCESSFUL in 1m 15s`; jar comparison passed.
- [Repo privacy 44105397859](https://github.com/Ares-Empire/AresOS/actions/runs/44105397859): **success**, `gh run watch 44105397859 --exit-status --interval 60` exit 0.
- [OS image 44105442692](https://github.com/Ares-Empire/AresOS/actions/runs/44105442692): **success**, dispatched with `gh workflow run "OS image" --ref pkg/47-gpu-awake -f checks_only=true`; `gh run watch 44105442692 --exit-status --interval 60` exited 0. The regression job completed in **30m 54s**, printing `Ran 1695 tests in 1807.266s`, `OK (skipped=4)`. Those four existing skips are `test_aresos_cover`: three headless labwc/grim/GTK checks unavailable on the hosted runner, and its GTK/gi no-display check. Syntax checks and the upstream-signature/input checks passed too. No local `os/tests` module was run; no skip condition was changed.

All hosted checks above target `b5388476`. Final report-only updates do not change the tested implementation. Screenshots generated by the existing client suite are preserved locally, then their tracked rewrites are restored; this package changes no game visuals and adds no visual test.

Cleanup checks found no remaining scopes for the baseline, interrupted build or either complete changed build. Both complete traces end suspended. No invocation returned exit 75, so no five-minute busy retries were needed. No lasting Gradle daemon was started; no shared-daemon stop command was used. Tracked review PNGs were restored and copied untracked PNGs removed. The closing `.work/` inventory contains **no file over 500 MiB**; no ISO/image-layer download or extracted disk image was created.

## Review fix 1

### Findings and cleanup behavior

1. **Parent death inside a CUDA call:** CUDA now runs in a worker scope under an independent Python supervisor. The supervisor watches a pidfd for the calling shell throughout startup, readiness, and execution. It owns each `systemd-run` launcher as a child, so parent death during scope creation can cancel that launcher too. No CUDA function executes in the supervisor. Initialization still has its existing 30-second deadline. Cleanup gives ordinary client/probe scopes 20 seconds and the CUDA worker five seconds, then sends KILL by the invocation-owned unit names and child PIDs. System-manager calls have a one-second timeout, and final removal checks have a three-second deadline per group. The normal case is much faster; combined cleanup has a 40-second bound under the tested, responsive Linux/systemd conditions.
2. **Parent SIGKILL with a running game:** the supervisor inherits the shared lock and stops the invocation's ordinary scopes before stopping its CUDA worker. This covers the headless compositor, its Xwayland, the game and Gradle processes in those scopes. Only names and launchers registered by this invocation are targeted. RPC helpers close their inherited lock descriptor; ordinary commands do not inherit it from the supervisor. Explicit Intel/software runs use the same cleanup supervisor without starting CUDA.
3. **Holder death after `READY`:** the supervisor watches the worker until its intentional release, including while cleaning up ordinary scopes. Unexpected exit prints `NVIDIA power holder exited unexpectedly; aborting client tests.`, signals the calling shell through its pidfd, stops the client scopes, and makes the run fail. The CUDA worker ignores terminal INT/HUP so those signals cannot release the context ahead of ordered cleanup; its supervisor sends TERM for intentional release and KILL if release hangs.
4. **Corrected claim:** the original unconditional statement that killing the script cannot orphan a context was too broad. The new tests establish cleanup for parent SIGKILL during hanging initialization or context creation, parent SIGKILL followed by a hanging release, and parent SIGKILL with persistent client descendants; they also establish failure and cleanup when the ready holder is killed. They do not prove recovery from an unkillable kernel task, a killed supervisor, or a broken system manager. No real wedged driver was induced.

The shared lock, two memory/owner-game checks before probing, final room check before Gradle, headless display isolation and NVIDIA → Intel → software order remain in place. CUDA still requires already available UVM and uses the installed driver library. No privileged operation, system configuration write, process-name kill or persistent GPU policy was added. The supervisor starts only after this run acquires the shared lock.

### Stand-in verification

```sh
python3 reviews/47-gpu-awake/lifecycle-test.py > .work/47/lifecycle-review-fix-1-final.log 2>&1
bash -n mod/dev/env.sh mod/dev/client-test.sh mod/dev/build.sh mod/dev/run-hub.sh
git diff --check
```

All exited **0**. The harness compiles its stand-in `libcuda.so.1` with `cc -shared -fPIC`, runs real invocation-owned systemd user scopes, and starts persistent Python clients with a descendant. It calls no real CUDA or game. All **14 cases passed**; exact output is in [lifecycle-review-fix-1.txt](lifecycle-review-fix-1.txt). Every case checks scope removal and immediate private-lock reacquisition after the shell and supervisor have exited; client cases also check their pidfds. Parent death during init/retain and hanging release took about five seconds; a TERM-ignoring client took about 20 seconds. Normal initialization timeout plus forced worker cleanup took 35.36 seconds. The descriptor case verifies separate compositor/game stderr, stdout, exported environment and exit-code forwarding.

Initial verification exposed an overlong Unix-socket path in the deep test directory; binding/connecting relative to the private directory fixed it. A later repeat failed the unchanged immediate lock assertion because an RPC helper still inherited the lock. Closing helper copies fixed that race; the final run retains the same assertion. Terminal-signal inspection also showed the CUDA worker shares the invocation's process group, leading to the INT/HUP guard and its added test. An exploratory real run was deliberately interrupted with INT to verify the final implementation afterward; it exited **130** after 3 min 6 s and its measured trace contains one wake-up and one suspend. It is not counted as a complete passing run.

CLI checks: `mod/dev/build.sh --daemon` exited **2** and printed that Gradle's daemon switch is refused; `mod/dev/client-test.sh --gpu invalid` exited **2** and printed the four accepted GPU choices. Neither command started a game or build.

### Real GPU verification after the fix

Implementation: `92f9fbd6`, including main through `774d7954` merged by `deac29bc`. No implementation changed between the complete runs. Sampling uses the same read-only 20 ms sampler and 30-second post-exit window described above. The first complete command was:

```sh
python3 .work/47/measure.py review-fix-1-final-1 mod/dev/client-test.sh --keep-screenshots .work/47/review-fix-1-final-1-screenshots build
```

Exit **0**: `BUILD SUCCESSFUL in 12m 50s`, `19 actionable tasks: 4 executed, 15 up-to-date`. The complete client suite and all **104 required server game tests passed**. The unit-test task was up-to-date in this run. The script copied **92 PNGs** to the requested worktree directory. NVIDIA resumed once, remained active with a fixed suspended-time counter, and suspended once after cleanup.

The second complete command forced all tasks to execute again:

```sh
python3 .work/47/measure.py review-fix-1-final-2 mod/dev/client-test.sh --keep-screenshots .work/47/review-fix-1-final-2-screenshots build --rerun-tasks
```

Exit **0**: `BUILD SUCCESSFUL in 13m 43s`, `19 actionable tasks: 19 executed`. The complete client suite and all **104 required server game tests passed again**. Unit XML reports **272 tests, zero failures/errors, six existing Windows-only skips**. Another **92 PNGs** were copied. Both commands reported NVIDIA GeForce RTX 4060 Laptop GPU.

| Complete run | Observation | Wake-ups / suspends | Active-time increase | Suspended-time increase |
|---|---:|---:|---:|---:|
| 1 | 807.3976 s | 1 / 1 | 781,963 ms | 25,434 ms |
| 2, forced tasks | 860.3227 s | 1 / 1 | 836,987 ms | 23,337 ms |

[power-review-fix-1.csv](power-review-fix-1.csv) preserves each status transition and each trace's final sample; the complete 20 ms traces and command output remain under `.work/47/`. In each trace the suspended-time counter stayed constant throughout the continuous active interval. Read-only checks after both runs found **zero remaining scopes** for their script PIDs. The interrupted exploratory run also left zero scopes. No command returned exit 75, so no busy retries were needed. The shared lock was released between runs, including the 30-second sampling window, for other builders.

Tracked PNG rewrites were restored after the screenshot copies; generated untracked review PNGs were removed. This change adds no game visuals. The closing `.work/` inventory contains **no file over 500 MiB**. No lasting Gradle daemon was started and no shared-daemon stop command was used.

### Hosted verification of review fixes

- [Mod 44242554714](https://github.com/Ares-Empire/AresOS/actions/runs/44242554714): **success**, watched with `gh run watch 44242554714 --exit-status --interval 60` (exit **0**). Both builds passed all 104 required server game tests; `BUILD SUCCESSFUL in 1m 19s` and `BUILD SUCCESSFUL in 1m 16s`; the jar comparison passed.
- [Repo privacy 44242554728](https://github.com/Ares-Empire/AresOS/actions/runs/44242554728): **success**, `gh run watch 44242554728 --exit-status --interval 60` exited **0**.

- [OS image 44242554926](https://github.com/Ares-Empire/AresOS/actions/runs/44242554926): **success**, dispatched with `gh workflow run "OS image" --ref pkg/47-gpu-awake -f checks_only=true`; `gh run watch 44242554926 --exit-status --interval 60` exited **0**. The regression job completed in **23m 42s**, printing `Ran 1772 tests in 1367.146s`, `OK (skipped=4)`. All four existing skips are the three headless labwc/grim/GTK cover checks and its GTK/gi no-display check. Syntax checks, the hosted system-manager query and upstream input/signature verification passed. The separate full-model job correctly selected the existing bounded slice because its sources did not change; no skip condition or test was changed here.

These runs target implementation `92f9fbd6`. Final report/evidence-only updates do not change that implementation. The preceding exploratory OS run and superseded Mod/privacy runs at `96eb4ee0` were cancelled before completion when the lock/signal fixes were pushed; they are not passing evidence. No local `os/tests` module was run.

## Review fix 2

### Findings and cleanup behavior

`mod/dev/env.sh` now calls `holder_lost()` on every iteration of ordinary-scope cleanup's final confirmation, and once more immediately before intentional holder release. The existing `holder_failed` latch retains failure through later successful scope removal; its diagnostic prints once. Intentional holder shutdown still follows ordinary-scope shutdown and does not count as an unexpected loss. No cleanup deadline or launch/fallback policy changed.

The timing claim in Done and Review fix 1 is corrected: `parent-kill-release-hang` proves **parent SIGKILL followed by a hanging release**. It does not kill the parent during a release that was already hanging. No new claim about a wedged real driver is made.

### Stand-in verification

```sh
python3 reviews/47-gpu-awake/lifecycle-test.py > .work/47/lifecycle-review-fix-2-final.log 2>&1
bash -n mod/dev/env.sh mod/dev/client-test.sh mod/dev/build.sh mod/dev/run-hub.sh
git diff --check
```

All exited **0**. The existing **14 cases** and the new deterministic `cleanup-final-holder-kill` case passed; exact output is in [lifecycle-review-fix-2.txt](lifecycle-review-fix-2.txt). The new case took **20.80 s**, returned **1**, printed the required diagnostic exactly once, and left its scopes gone, both client pidfds exited, and its private lock immediately available.

For that case only, a `systemctl` shim keeps the ordinary scope unconfirmed until the supervisor enters KILL escalation. Inside the first final-confirmation query it kills the recorded holder unit and waits for its recorded worker pidfd to exit. It keeps confirmation pending for another iteration, and asserts that the diagnostic has appeared before returning the real scope state. Every stop/kill reaches the real user manager and targets only this trial's recorded units. CUDA is a compiled stand-in; no real game or driver call is used in the harness.

A focused run of the new case passed in **20.77 s**. Running the same case against the pre-fix `env.sh`, with a separate worktree-local cache, reproduced cleanup returning **0** after the injected holder death. The local reproduction command `python3 .work/47/reproduce-review-fix-2.py` exited **0** and printed `Pre-fix regression reproduced: cleanup returned 0 after holder death during final confirmation; expected 1.`

The first full harness attempt passed the existing 14 cases but failed the new case because its injection looked for a separate `systemd-run` process after the scope launcher had already execed the worker. The shim now uses the worker PID recorded by the fake CUDA library; the failure-status assertion remains unchanged. Harness and embedded-supervisor Python parsing also passed. CLI checks `mod/dev/build.sh --daemon` and `mod/dev/client-test.sh --gpu invalid` each returned **2**, respectively printing the daemon-switch refusal and the accepted GPU choices, without launching a game or build.

### Real GPU verification

Implementation `93921c06`, with main through `87d86471` merged first by `25854164`. The same read-only 20 ms sampler starts three seconds before each command and samples for 30 seconds afterward. Both complete `build runClientGameTest` runs used the shared lock, normal memory/owner-game checks, private headless compositor, and NVIDIA holder. No `--force`, direct Gradle invocation, privileged operation, or system configuration change was used.

```sh
python3 .work/47/measure.py review-fix-2-final-1 mod/dev/client-test.sh --keep-screenshots .work/47/review-fix-2-final-1-screenshots build
python3 .work/47/measure.py review-fix-2-final-2 mod/dev/client-test.sh --keep-screenshots .work/47/review-fix-2-final-2-screenshots build --rerun-tasks
```

Both exited **0** and reported NVIDIA GeForce RTX 4060 Laptop GPU. Run 1 printed `BUILD SUCCESSFUL in 13m 1s`, `19 actionable tasks: 4 executed, 15 up-to-date`; its unit-test task was up-to-date. Run 2 printed `BUILD SUCCESSFUL in 13m 50s`, `19 actionable tasks: 19 executed`. Each passed the complete client suite and all **104 required server game tests**. The forced run's unit XML contains **272 tests, zero failures/errors, six existing Windows-only skips**. Each command copied **92 PNGs** to its requested worktree-local directory.

| Complete run | Observation | Wake-ups / suspends | Active-time increase | Suspended-time increase |
|---|---:|---:|---:|---:|
| 1 | 818.2045 s | 1 / 1 | 791,983 ms | 26,223 ms |
| 2, forced tasks | 867.0223 s | 1 / 1 | 841,949 ms | 25,074 ms |

[power-review-fix-2.csv](power-review-fix-2.csv) records all status transitions and final samples. Full traces and command logs remain under `.work/47/`. Both traces start and end suspended, with exactly one resume and one suspend; every active sample has the same suspended-time counter within its run. The card returned to suspend at **07:18:10.596** and **07:32:57.609 CET**, respectively. Checks by the recorded script PIDs found **zero remaining scopes** after each run. No invocation returned exit 75. The shared lock was released between runs, including the 30-second post-exit sampling interval, and after the second run.

Screenshot copies were retained locally, then the suite's 56 changed tracked PNGs were restored and its 25 generated untracked PNGs removed. There is no visual change in this fix. No lasting Gradle daemon was started, and no shared-daemon stop command was used. `find .work -type f -size +500M -printf '%P %s bytes\n'` returned no files: **nothing over 500 MiB remains in `.work/`**. No ISO, image layer, or extracted disk image was created.

### Hosted verification

- [Mod 44248844116](https://github.com/Ares-Empire/AresOS/actions/runs/44248844116): **success**, watched with `gh run watch 44248844116 --exit-status --interval 60` (exit **0**). Both builds passed all 104 required server game tests, printing `BUILD SUCCESSFUL in 1m 48s` and `BUILD SUCCESSFUL in 1m 44s`; jar hash comparison passed.
- [Repo privacy 44248844081](https://github.com/Ares-Empire/AresOS/actions/runs/44248844081): **success**, `gh run watch 44248844081 --exit-status --interval 60` exited **0**. The same privacy script also passed locally, printing `No file holds a home path with a real user name.`

- [OS image 44248863844](https://github.com/Ares-Empire/AresOS/actions/runs/44248863844): **success**, dispatched with `gh workflow run "OS image" --ref pkg/47-gpu-awake -f checks_only=true`; `gh run watch 44248863844 --exit-status --interval 60` exited **0**. The regression job took **22m 55s**, printing `Ran 1772 tests in 1268.565s`, `OK (skipped=4)`. The four existing skips are three headless labwc/grim/GTK cover tests and the GTK/gi no-display test. Syntax, the hosted system-manager query, release-input resolution and upstream-signature verification passed. The unchanged full-model selector chose the existing bounded slice because its sources did not change. The existing org package-visibility limitation was recorded; private metadata verification is not enabled on this branch. No skip condition or test was changed.

These hosted runs target implementation `93921c06`. This closing commit changes only the report and evidence. No local `os/tests` module was run. The final staged privacy check passed with `No file holds a home path with a real user name.`

## Not verified

The historical cause of the driver/HDMI failure, an actual recurrence of that failure, physical HDMI recovery, battery watts and long-term driver stability were not tested. No owner desktop, real game, boot settings, driver configuration or mounted disk was changed.

## JUDGMENT-CALL

Keep NVIDIA in D0 only for the lock-held test interval, including idle world loading and shutdown. This spends some battery during a test in exchange for avoiding repeated RTD3 transitions; it allows suspension afterward. An idle CUDA context avoids continuously rendering a dummy workload and supplied the measured D0 hold. Opening a graphics fd alone did not wake the card, and probe caching cannot prevent the measured in-game cycles. Removing this choice later means removing the helper call and its cleanup ordering; no persistent system setting needs undoing.

NVIDIA rendering now requires an already available UVM device, Python 3, and successful CUDA context initialization. If that is unavailable, `auto` falls back to Intel/software and explicit NVIDIA fails. Probing NVIDIA anyway would abandon the cycle bound. The prerequisite guard deliberately avoids asking the driver library to load a missing UVM module or create its device through a privileged helper.

If context creation succeeds but the NVIDIA OpenGL probe fails, the holder remains alive through the fallback run too. This keeps the entire attempted-NVIDIA interval covered, at the cost of idle NVIDIA power even while Intel/software renders. Its lifetime is still bounded by that invocation; explicit Intel/software selection never creates it.

Owner-only alternatives, **described, never applied**: disabling RTD3 with `NVreg_DynamicPowerManagement=0x00`, a kernel/module option, or `power/control=on` keeps the card powered outside tests too, costing idle battery and potentially heat. Coarse-grained `0x01` can keep it active for the lifetime of NVIDIA clients, whose lifetime may extend well beyond a test. NVIDIA documents that `nvidia-persistenced` with UVM persistence disables RTD3; that is a system service/policy with the same idle-power tradeoff, and plain persistence alone was not established here as a fine-grained RTD3 fix. These require the owner's separate decision, and none is needed by this patch. See the linked driver documentation.

## PLAN-GAP

The historical journal does not contain the cycle trace assumed by the brief. It supports the error sequence and scope timeline, not a numerical historical D3cold/D0 count or a proof of cause. The new runtime-status/counter observations establish the present behavior instead.

The present baseline cycles during the game itself, so preserving a probe result within a boot would not meet the one-cycle requirement. The context must cover the complete client interval.

## Open questions

Does this prevent recurrence of the November 14 driver fault during normal package work? That needs continued real use; reducing power transitions is not proof of a driver fix.
