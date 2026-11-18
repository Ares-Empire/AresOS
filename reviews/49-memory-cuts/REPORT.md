# Package 49: measuring the home screen's memory cuts

## Done

The builder changes only `reviews/49-memory-cuts/`. The branch also retains the supplied, unmodified `briefs/49-memory-cuts.md` from its initial brief commit (`fc1d31de`); upstream merge contents are not builder changes. No settings, supervisor action, image dependency or mod code ships here. `RESEARCH.md` and package 41's evidence remain unchanged.

**Recommendation: no new settings are fully qualified to ship under this brief's complete pass line.** The game-only arena cap is the most consistent isolated follow-up candidate, but its first flat trial added a 19.948 ms flight frame while all three current v1 controls stayed below 17 ms (flight maximum 15.1). The cause is unknown; one event does not prove a persistent allocator regression. It does prevent claiming the requested paired frame condition passed. All prescribed final workloads were completed; no cleaner repetition replaces the recorded discrepancy. The final three flat pairs average 167 MiB less RSS settled,295 after flight and 281 covered; workload details are below.

`rig/` and `frames/` copy package 41's workload and add game-only allocator environment variables, extra local mods, trim/GC probes, classified smaps, faults, scope swap, global zram statistics, covered reclaim/freezer experiments, an active ten-second return window, long idle runs, and a JVM-confirmed NMT-off mode. Cgroup writes validate this run's exact game scope, PID membership and systemd ControlGroup. Frozen snapshots never attach jcmd; cleanup thaws before stopping the run's scopes. The outer script acquires the shared client lock before changing the disposable world or compiling the recorder.

Every comparison uses a fresh copy of the forty-app flat base (seed 0); Nether controls/trials use the same seed 49 placeholder-hub base. [Fixture identities](fixture-hashes.json) record their manifests and saved-input hashes. Factor order is A/B in round 1 and B/A in round 2, with a new v1 control for each factor. Each run releases the shared lock and the batch waits another 30 seconds. All launches enforce the owner's-game and 6 GiB memory guards. Exit 75 waits five minutes and permits at most six retries; other failures stop that schedule.

Small snapshots, GC logs, sampling, marks, settings and frame summaries are public. Raw frame/game/launcher logs, helper credentials, worlds and jars remain in ignored `.work/`. `table.py` regenerates the comparison tables; `audit.py` records guards, provenance and source-matched frame comparisons. Runtime jars are identified by hashes, not committed. The FerriteCore jar remains a single verified local download; its SHA-512 and MIT metadata are in `ferritecore.json`.

The [results tables](TABLES.md) give every factor/control pair, observed saving/spread, approximate NMT residual, covered result and individual completed run. The [measurement audit](verification/measurement-audit.json) records completeness, source identity and guard/frame comparisons.

### Measurement limits

The hardware/runtime is the i5-13500H/16 GB laptop and its RTX 4060 through NVIDIA GLX/OpenGL, driver 615.78.08, Temurin 25.0.5+8, glibc 2.43 (observed during final qualification), a private headless labwc/Xwayland at 1920×1080@144, render 8 / simulation 5, game cap 120 fps, null audio, heap 1024/256 MiB, G1 free ratios 30/10, and MemoryHigh 2560M. No owner display or input is used. Host load, free memory and selected process counts accompany the snapshots; other builders and Chrome were running. Reported n=2/n=3 ranges describe observed spread, not confidence intervals.

RSS includes shared file/device mappings. Scope memory excludes pages charged elsewhere; neither equals the whole desktop session's incremental cost. zram `mm_stat` is global. Its first three fields are original bytes, compressed bytes and allocated physical memory including overhead ([kernel documentation](https://docs.kernel.org/admin-guide/blockdev/zram.html)); a change includes other processes, so it is not an exact attributed game cost.

Frames are gaps between recorder frame starts, not presentation timestamps. The return-request mark precedes thaw; the wake mark follows cover close. The first wake interval is clipped at that mark, avoiding a fabricated five-minute frozen stall. All comparative wakes use the same control-key transition and repeated camera movement. The initial probe's tiny movement left vanilla at 30 fps, so that diagnostic wake is retained but excluded from comparisons. A short activation transition at 30 fps also appears in active control wakes before 120 fps resumes.

The Nether glide is the existing rig's level teleport route through terrain, not normal player flight; terrain can occlude the rendered view while chunks still load. Its exact same fixture and tick counter make the paired comparison useful, but it does not establish worst-case visible Nether rendering.

Start time is scope-PID detection to joining (about one-second detection granularity), excluding Gradle startup and Prism. Creation additionally has observed plan-entry-to-join (automatic) or confirmation-to-join (menu), plus town-building windows. None is a measured cold product boot time.

The original matrix uses the mod tree at `80d3549a` (`4ec6bfe9…`). Main moved, so it was merged at `3be460c6`, incorporating main `58d2ae1b` and mod tree `b038c0dd…`. The helper and labwc configuration blobs are unchanged; the mod is not. `source-refresh.json` and the provenance audit record the exact identities. The current full build/client qualification passed twice more (13m 38 s and 13m 21 s builds), including the new menu/save/switch tests. Before hosted checks, main `918fba67` was merged at `2cf920a8`; its mod, helper and labwc blobs are identical to the measured current tree. A further pre-final-check merge incorporated main `774d7954` (handoff notes only), again leaving those measured blobs unchanged. Old and new frame ranges are not pooled.

Package 48's automatic first start also made the old title-screen automation obsolete. Current flat creation observes the real `HomePlan.create` entry; Nether setup uses the actual Esc/New home/Nether/Create/confirmation flow and verifies the observed plan's kind. GUI observation only supplies button bounds for private compositor input. It never invokes a product action or suppresses first start. Nether setup includes a warm flat home and a switch; the two Nether measurement JVMs then load identical fresh saved copies. Package 46's inherited lifecycle gate is removed so this rig never opens the real supervisor channel.

### Step 0 and isolated factors

Direct glibc trims returned 187 MiB settled, 46 MiB standing and 107 MiB after flight. The native gate passed, so every planned allocator factor was measured. All ten probe snapshots confirmed successful trim/GC commands. Its forced diagnostic GC reached 77.34 ms; that perturbed run is not a qualified product configuration.

Long idle windows receive no repeated input: vanilla may lower visible rendering from the active 120 fps workload to its inactivity caps. They are retention checks, not twenty minutes of 120 fps flight. The original twenty-minute visible idle run rose from 1245 MiB settled to 1364 MiB at idle minute 20, with a constant 341 MiB committed heap. A roughly 35 MiB RSS rise occurred near JVM minute 10; there was no 250 MiB step or multi-GiB allocation. The growth outside NMT is unattributed: these measurements do not identify the NVIDIA listener as its cause. Its maximum post-join GC pause was 12.84 ms, with no OOM/high events or lost frame records.

The native hypotheses were useful, but not all were confirmed. The default path mapped NVIDIA and LWJGL's jemalloc library, with no Mesa library identified on this GLX path. Anonymous VMAs cannot be reliably divided into glibc and jemalloc heaps. `[heap]` is only glibc's brk area; jemalloc library pages are not its allocations. The NMT residual table is approximate accounting, because NMT committed bytes are not resident bytes.

Against fresh controls, the arena cap saved 182–185 MiB settled, 248–295 after flight and 244–303 covered. Its committed Java heap was slightly larger than its controls, so the RSS reduction is not a smaller-heap artifact. Both trials had zero standing/flight frames over 17 ms and maximum GC below 16 ms. Native trimming every 60 seconds saved 170–206 settled and 184–283 after flight; one trial had an 18.5 ms flight frame. Switching LWJGL to system allocation removed the jemalloc library mapping but gave no consistent additional saving over trimming alone.

Compact headers lowered the standing post-G1 heap minimum by 17–23 MiB, below the estimated 30–60 MiB. Settled RSS savings ranged from −33 to +89 MiB; both flight/covered pairs improved. String dedup added only about 5.5 MiB of post-G1 heap saving beyond headers across the separate paired measurements and gave no consistent RSS improvement. Worker limits had mixed settled RSS and extra long frames; much of their post-flight RSS difference was committed heap rather than a lower native residual.

FerriteCore lowered that heap minimum by 9–12 MiB, below the estimated 15–45 MiB. Neither trial lowered post-flight or covered RSS. It passed the original client qualification twice, but the measured memory benefit does not justify adding it to the image in this package. On the merged product source it passed two further full client qualifications, including the actual automatic first start and home-menu scenarios.

### Covered actions

Both untreated controls completed at 1224 and 1294 MiB RSS after five minutes. GC/trim gave 1088–1091 MiB (paired saving 136–203), reclaim 300M gave 991–992 (233–302), and reclaim 600M gave 772–804 (420–522). The one-minute minima are not the reported sustained result: reclaimed anonymous pages were touched again while covered.

At five minutes the 300M trials held 98–99 MiB in scope swap and the 600M trials 251–341. Their covered major-fault counts were 52,478–52,800 and 59,757–84,289; ten-second wakes added 497–623 and 1258–1794. Global zram physical growth was 27–30 and 71–87 MiB, respectively, but cannot establish an exact per-game net saving. All four reclaim writes completed; 300M took about 1.5–1.6 seconds, 600M about 2.9–3.0. A return while that blocking write is in progress was not tested.

Every forced cover GC exceeded the unconditional 50 ms post-join limit: 73.28/74.66 ms for GC/trim, 69.84/72.83 for 300M, and 80.08/71.05 for 600M (frozen attempts 67.13/69.65). A hidden pause is still a failed guard. Untreated wakes had worst frames 33.5/33.8 ms; 300M gave 41.8/33.5 and 600M 53.1/62.9, with all counts shown in TABLES. Larger first-frame gaps also occur in untreated factor controls, so one worst wake frame does not isolate a swap-induced stall. Return-request to first recorded visible frame was 56–72 ms untreated, 74–81 with 300M and 95–111 with 600M. A completed reclaim request is not a promise that the same bytes stay swapped; the kernel also permits partial reclaim with EAGAIN ([kernel documentation](https://docs.kernel.org/admin-guide/cgroup-v2.html)). No request is silently retried as pressure.

Both freeze attempts held their memory stable for five minutes: 510 and 494 MiB RSS, with 598 and 599 MiB of scope swap. Global zram physical usage rose about 116–118 MiB. Both games exited 137 during thaw, after tick-backlog and repeated helper reconnect warnings; the input pipe then broke. The second attempt's read-only observer saw exit signal 9 at 253 ms after the return request, with scope OOM/high counters still zero. The sender of SIGKILL is unknown. Neither has a qualified wake window; abrupt death may also lose the recorder's buffered tail. Keep both failures visible, never average them as successful wakes. Freezing is not ready to recommend.

The prior FerriteCore input failure was different: a FIFO reader-reopening ENXIO race. Keeping one writer open and bounding startup retry fixed that cause; the delayed-reader regression and existing dead-reader bound passed. Its partial trial and retired control remain under `failures/`, and the complete fresh pair was rerun. No assertion or timeout was weakened.

### Final candidate and retained alternatives

The initial compact-header/native combination is retained under `candidates/compact-headers-native/`. Its creation pair saved 324 MiB settled, 385 after flight and 456 covered, but added a 21.9 ms standing frame and 26.3 ms flight frame versus control maxima 12.0/12.3. They align with 19.914 ms Mixed GC and 18.596 ms Remark pauses, away from nominal 60-second boundaries. It fails the requested frame comparison without identifying a sole cause or establishing that compact headers always regress.

The second set omitted headers, retaining the trim interval and arena cap. Its fresh creation pair had control/candidate RSS 1285/1003 MiB settled, 1395/1070 after flight and 1373/996 covered, with both active windows below 17 ms. The first flat pair saved 67/234/279 MiB; the second 222/303/361. All six measurements are retained under `candidates/native-interval-arena/`, outside final means. The second candidate's flight had one 34.916 ms frame (> 33 ms), versus control maximum 11.565 and no frames > 17. Its post-join GC maximum was 14.81 ms; nearby GCs were only 1.285 and 3.318 ms. The gap occurred at JVM uptime 246.208 s, about 6.2 s from a nominal 60-second boundary. The nearest two-second host sample had 7622 MiB available and load 2.21. Neither those samples nor nominal timer boundaries assign a cause ([observation](verification/native-flight-outlier.json)). Memory savings do not waive that failed frame comparison.

Only the owned Python scheduler was paused while its final control completed normally, then terminated before another game launched. No measured child was interrupted. The arena cap's isolated savings were already consistent; the timer's gains overlap them, so the final conservative candidate keeps only `MALLOC_ARENA_MAX=2` for the game JVM and retains the base JVM arguments. Omitting a timer after a failed combined comparison does not prove the timer caused that failure. The completed Nether utility fixture is reused byte-for-byte by both fresh Nether JVMs; its generation flags do not qualify any later set.

The final arena-only automatic creation pair saved 170 MiB settled,268 after flight and 274 covered. Control/candidate RSS was 1270/1100,1401/1133 and 1383/1109 MiB; settled PSS 1155/984. Candidate committed heap was larger (400 versus 361 MiB settled,426 versus 386 after flight), supporting a native reduction rather than a smaller-heap artifact. Join times were 9.69/9.57 seconds. Maximum post-join GC was 11.72/22.53 ms, with zero Full GC/OOM/high events, lost records, scope swap or added wake major faults. Standing maxima were 13.6/11.1 ms and flight 13.9/14.1, neither active window > 17 ms. Wake maxima were 36.9/33.6 ms, both 12 frames > 17 and 12 > 33; return-request to first frame 83.66/57.68 ms.

Startup is less uniform: first 30 s p99 was 9.38/8.62 ms and worst 105.6/102.0, with six frames > 17 in each, but 1/3 frames > 33. The town-build subwindow's worst was 32.2/102.0 ms; the control's 105.6 ms loading frame fell outside that shorter subwindow. The summary retains both the extra startup tail counts and the maxima; these metrics are not uniformly unchanged.

The first final flat pair saved 154/198/198 MiB settled/flight/covered. Standing had no frame > 17 ms, but flight added one 19.948 ms gap versus control 15.1 ms with none > 17. Nearby GC pauses were only 1.999/3.024 ms, and the nearest host sample had 7664 MiB available and load 1.62 ([observation](verification/arena-flight-outlier.json)). Its cause is unknown. This discrepancy stays in the final comparison; no further settings changes or selective reruns are planned. All three current flat controls have zero active frames > 17 ms; their flight maxima are 11.4–15.1 ms. The requested complete frame condition is not met.

The actual candidate JVM proves cap 2, ordinary CDS, no trim interval, baseline free-ratio/heap arguments, absent real lifecycle gate, and helper/compositor addresses matching this run's private record ([runtime proofs](runtime-proofs.json)). Earlier proofs refer to the retained alternatives.

Across the final three flat pairs, the arena-only candidate averaged 1017.0 MiB RSS settled (1011–1024),1064.3 after flight (1050–1078), and 1037.3 covered (1024–1051). These are measured values, not sums of isolated factor savings:

| Phase (n=3 each) | Fresh v1 RSS mean (range) | Arena-only RSS mean (range) | Paired RSS saving mean (range) | Arena-only PSS mean (range) |
|---|---:|---:|---:|---:|
| Settled |1184.3 (1165–1210)|1017.0 (1011–1024)|167.3 (154–194)|912.0 (907–918)|
| After flight |1359.3 (1263–1457)|1064.3 (1050–1078)|295.0 (198–379)|957.0 (944–971)|
| Covered five minutes |1318.3 (1235–1404)|1037.3 (1024–1051)|281.0 (198–353)|929.7 (918–943)|

Candidate settled committed heap averaged 7.7 MiB *more* than controls; the settled reduction is not a smaller-heap artifact. After flight, controls averaged 59 MiB more committed heap, so not all 295 MiB of that RSS difference can be attributed to native retention. Settled PSS saving averaged 166 MiB (153–192).

Scope-PID detection to join was 9.08–9.59 s for controls and 9.58–9.59 s for candidates; first creation was 9.69/9.57 s. Detection granularity is about a second, so these do not establish a start-time improvement. Flat candidate maximum post-join GC was 10.94–12.20 ms, without Full GC, OOM/high events, lost recorder entries, scope swap or added covered/wake major faults.

Standing p99 was 8.47–8.49 ms control and 8.46–8.48 candidate. Worst standing was 9.8–10.2 versus 11.5–14.4; neither group exceeded 17 ms. Flight p99 was 8.49–8.60 versus 8.52–8.54, but worst frames 11.4–15.1 versus 11.6–19.9, with zero control frames > 17 and one candidate frame > 17 (none > 33). The similar p99 does not erase the extra gap.

Wake maxima were 33.6–75.1 ms control versus 33.4–51.4 candidate. Counts > 17 were 11–12 versus 12; counts > 33 were 11 versus 11–12. Return-request to first visible frame was 59.53–126.58 ms versus 72.72–97.35. Both groups show the ordinary activation transition, and these few samples cannot assign its phase-dependent first gap to an allocator. The third paired wake is slower than its own control even though it lies inside the three-control worst-frame range.

The final Nether comparison (one complete control/trial, no repetition spread) saved 82 MiB settled,187 after glide and 218 covered. Control/candidate RSS was 1185/1103,1482/1295 and 1446/1228 MiB; PSS 1081/997,1377/1188 and 1341/1122. Candidate committed heap was larger settled and after glide (433 versus 385;589 versus 556), so this is not a smaller-heap saving. Both logged the complete 1200-tick route; repeated identical counter entries are log records, not independent runs or a direct TPS measurement.

Nether standing worst was 12.1/10.1 ms, with no frame > 17. Glide p99 was 10.15/9.76 ms, worst 29.1/21.8, and counts > 17 were 4/1, neither > 33. Wake worst was 33.7/48.2 ms, counts > 17 were 14/13 and > 33 were 12/12; return-request to first frame 66.04/86.68 ms. Join times were 9.58 s each. Post-join GC maximum was 13.63/20.01 ms, with no Full GC, OOM/high events, lost records, scope swap or added covered/wake major faults. The glide's better frames do not cancel the flat discrepancy, nor does this one pair establish unchanged wake latency.

The final `LONG=20` window lasted1207.4 seconds, including snapshot overhead. RSS was 1022 MiB settled and 1025at idle minute20; PSS was 918 MiB at both endpoints and committed heap 356 MiB throughout. Minute snapshots ranged1001–1029 MiB. A28 MiB drop at minute5 was followed by a 23 MiB rise at minute7; no 250 MiB resident step occurred. RSS peak remained1042 MiB. NMT committed total changed687→683 MiB. The small changes remain unattributed and are not a paired same-source comparison with the earlier long run. Maximum post-join GC was 13.59 ms, no Full GC/OOM/high/lost-frame events, no scope swap and no major faults added beyond the single startup fault. Mean idle rendering was 24.2fps as vanilla's inactivity caps took effect.

The final flat `NMT=0` run confirmed disabled tracking at **all ten live snapshots**, using the JVM's literal “Native memory tracking is not enabled” response. Its one absolute measurement was:

| NMT-off phase (n=1) | RSS MiB | PSS MiB | Committed Java heap MiB |
|---|---:|---:|---:|
| Settled visible |1056|949|395|
| After flight |1063|955|394|
| Covered five minutes |1038|929|397|
| After return |1038|930|397|

That is about 1.03 GiB RSS settled and 1.04 GiB after flight. This run had a larger committed heap than the tracked flat trials, so its difference from their means cannot estimate NMT overhead. Start-to-join was 9.08 s; maximum post-join GC13.15 ms, no Full GC/OOM/high/lost-frame events, scope swap or major faults. Standing p99/worst was 8.46/16.2 ms, flight 8.49/22.3 with one frame > 17 and none > 33, and wake worst 51.1 ms with12 frames > 17/12 > 33; return-to-first-frame 92.03 ms. There is no paired NMT-off control or repetition spread, and that extra active gap also remains in the record.

A single NMT-off number has no measured repetition spread and still includes the other rig instrumentation. No isolated gains are added together.

A later current-source Nether control was interrupted at return: the controller exited 143 after SIGTERM, its private compositor/X connection ended, and the launcher recorded game exit 1. The sender is unknown. Its glide had completed 1200 ticks and maximum post-join GC was 11.64 ms, but no complete wake window was recorded. That partial measurement remains under `failures/nether-control-interrupted/`; no OOM/allocator/owner cause is asserted. All its processes/scopes were gone before an unchanged full fresh control was started. It is excluded from final means, with no assertion or parameter changed. This interruption is distinct from the two frozen games' SIGKILLs. The unchanged repeat completed the entire protocol with runner exit 0 and a full ten-second wake; it had no added covered/wake faults or swap and maximum post-join GC 13.63 ms. Its success does not identify the earlier signal sender.

## Verified

[Hosted Mod run 44214086556](https://github.com/Ares-Empire/AresOS/actions/runs/44214086556) passed at commit `f2fdcd3d` after the second main merge. `gh workflow run "Mod" --ref pkg/49-memory-cuts` and `gh run watch 44214086556 --exit-status --interval 60` completed successfully. Both clean checkouts passed 104 required server game tests and printed `BUILD SUCCESSFUL in 1m 33s` / `1m 29s`; their jars had the identical SHA-256 `e88194c52e956e5c098477d02cc5debc7ce3b3d4c234c05ca676235152f45b48` ([extract](verification/hosted-mod.txt), [run identity](verification/hosted-mod.json)). It tests the same mod tree as final measurements, without the rig-only FerriteCore injection. Later report/data commits do not change that product tree.

Repo privacy: pending the PR's hosted check; the result will be recorded after that run.

`python3 reviews/49-memory-cuts/rig/table.py` regenerated [TABLES.md](TABLES.md); `python3 reviews/49-memory-cuts/rig/audit.py` regenerated the [audit](verification/measurement-audit.json). The audit records all 12required final protocol runs complete, all matching the current mod tree and selected settings,52 completed measurements and 65 total attempts. All final candidate memory/GC/recorder guards pass; the requested complete frame condition does **not**.

Python parsed960JSON/metadata files successfully, `bash -n` passed for all eight rig/frame shell scripts, and the full branch whitespace check passed after trimming five extracted-log line endings. [Local check record](verification/final-local-checks.json) gives the inputs and exit states. [Loader lists](verification/final-mods-check.json) confirm the frame recorder and absence of FerriteCore in all twelve final runs.

Both saved fixture hashes were unchanged after all measurements. The [closing storage inventory](verification/closing-storage.json) found **no regular file over 500,000,000 bytes** in `.work/`; its total was 502,129,417 bytes (about 479 MiB), largest file 14,108,102 bytes (the fourth raw client log). The single verified FerriteCore download is small; no ISO/image extraction was needed. [Closing process check](verification/closing-processes.json) found no package 49 scopes or exact rig-script processes, and the old read-only monitor had ended. The guarded scripts used no persistent Gradle daemon; no daemon-stop command was used.

Selected screenshots were inspected and saved here:

- [Current full client suite 3](screenshots/client-tests-3-0090-home-menu.png) and [suite 4](screenshots/client-tests-4-0090-home-menu.png); [original FerriteCore client 1](screenshots/ferrite-client-1-home.png) and [2](screenshots/ferrite-client-2-home.png).
- [Forty-app base](screenshots/setup-flat-forty.png), [final automatic creation](screenshots/arena-create-after-flight.png) and [final flat repetition 3](screenshots/arena-flat-3-after-flight.png).
- [Actual Nether choice](screenshots/setup-nether-choice.png), [Nether room](screenshots/setup-nether-room.png), [complete control glide](screenshots/nether-control-after-glide.png) and [arena-only glide](screenshots/arena-nether-after-glide.png). The [interrupted control image](screenshots/interrupted-nether-control-after-glide.png) is labelled separately; it does not prove a successful return.

The recorded invocation pattern for both full qualifications on each source was:

```bash
PKG49_TEST_MODS="$PWD/.work/pkg49/downloads/ferritecore-9.0.0-fabric.jar" \
reviews/49-memory-cuts/rig/retry.sh mod/dev/client-test.sh --gpu nvidia \
--keep-screenshots "$PWD/.work/pkg49/test-shots-N" \
-I "$PWD/reviews/49-memory-cuts/rig/client-mods.gradle" build
```

`N` was 1/2 on the original source and 3/4 on the refreshed source. The refreshed controller explicitly removed `ARESOS_DESKTOP_LIFECYCLE` from its child environment before invocation. [Qualification extracts](verification/client-tests-1.txt), [2](verification/client-tests-2.txt), [3](verification/client-tests-3.txt), [4](verification/client-tests-4.txt) retain the printed success lines and retry exits. [JUnit totals](verification/unit-results-4.json) retain the current suite counts.

The measurement schedules were `python3 reviews/49-memory-cuts/rig/batch.py step0`, `factors`, `covered`, and `winners reviews/49-memory-cuts/winners.json`. Failures stopped their schedules. The uncompleted covered variants were resumed explicitly after retaining each freeze failure; the revised winner schedule retained and excluded the rejected creation pair before restarting with fresh controls. [The command ledger](verification/run-commands.txt) gives every literal launch and recorded retry exit. These are not claimed as one uninterrupted successful batch.

Both setup and the second original client qualification each had two low-memory refusals (four exit-75 responses total); each waited 300 seconds before retry and then passed. No retry budget was exhausted, and no owner-game or memory guard was overridden.

The refreshed full qualifications printed `BUILD SUCCESSFUL in 13m 38s` / `13m 21s`, with client exit 0 after 13m 39 s / 13m 24 s. Each ran and passed 104 required separate server game tests. JUnit reports contain 272 cases, zero failures/errors and six Windows-only skips. Its 24 registered client entrypoints loaded FerriteCore, including menu/save/switch scenarios; the separate server game-test task did not inject it. Generated test artifacts outside this package were backed up, hash-checked and restored; [restoration record](verification/test-output-restoration.json) lists the 55 tracked and 25 untracked outputs.

Original qualification ran the guarded client script with the local FerriteCore init script and `build` twice: BUILD SUCCESSFUL in 12m 21 s and 11m 12 s; client exits 0 after 12m 22 s and 11m 15 s. Each ran and passed 104 required separate server game tests. JUnit reports contain 236 cases, zero failures/errors and six Windows-only skips. The 21 client entrypoints loaded FerriteCore, including their integrated-server scenarios; the separate server task did not inject it. The second qualification was refused twice with exit 75 (5.3 and 5.1 GB available), waited five minutes each time and then passed. No force override was used.

Gradle printed `:test` in passes 1/3 and `:test UP-TO-DATE` in 2/4. The second build on each unchanged product source reused the existing JUnit reports; it did not execute those unit cases again. `runClientGameTest` and `runGameTest` executed on both passes ([printed task outcomes](verification/task-outcomes.json)). The guarded client script adds `runClientGameTest`; `build` in the command above requests the full build as well.

Fourteen rig tests passed, including exact scope ownership/membership, unrelated scope refusal, smaps accounting, no jcmd while frozen, real FIFO reopening/dead-reader behavior, exact > 33 ms counting, frozen-gap clipping, acceptance/rejection of actual NMT-off responses, unique active GUI-button bounds and observed creation-kind/timing checks. The recorded run printed `Ran 14 tests in 2.273s` and `OK` ([output](verification/rig-unit-tests.txt)); later analysis/table changes were exercised directly against recorded data.

### Research claims checked

| Research claim | Measured outcome |
|---|---|
| Native memory return saves 50–200 MiB | Arena-cap pairs saved 182–185 settled and 248–295 after flight; interval pairs 170–206 and 184–283. The mechanism is useful; the factors overlap and their savings cannot be added. |
| Compact headers save 30–60 MiB | Standing post-G1 minimum fell 17–23 MiB. RSS was noisier; the first combined creation failed the frame comparison and was retained rather than selected. |
| String dedup adds 0–20 MiB | About 5.5 MiB extra post-G1 minimum across separate header/dedup pairs, with no consistent RSS gain. |
| FerriteCore saves 15–45 MiB on vanilla | Post-G1 minimum fell 9–12 MiB; post-flight/covered RSS improved in neither trial. Compatibility tests passed, but a memory case for adding it was not established. |
| Fewer workers save 10–40 MiB | Settled paired RSS saving −57 to +40 MiB; post-flight +47 to +84, with heap commitment confounding much of that difference and extra long frames. |
| Covered reclaim reaches 0.6–0.8 GiB resident | 600M trials reached 772–804 MiB at five minutes, but every forced GC failed the 50 ms guard. Global zram cannot prove the estimated net saving. |
| Frozen RSS reaches 0.2–0.4 GiB with acceptable return | 494–510 MiB resident, and both thaw attempts ended with SIGKILL. Retention worked; return did not qualify. |
| NVIDIA adds roughly 250 MiB near ten minutes | Not reproduced in the step-0 twenty-minute run. A roughly 35 MiB step and 119 MiB total growth remain unattributed. |
| A drawing floor near 0.85 GiB | An estimate, not a lower bound established here. The one NMT-off flat run measured1056RSS/949PSS MiB settled and 1063/955 after flight; these different metrics and workload phases are not a proof of a universal floor. |
| Fedora compact-header CDS, jemalloc configuration, Prism, real-session Mesa loading | Not verified here. The rejected Temurin candidate mapped its COH archive; the current arena-only set does not use it. |
| Other runtimes/backends and laptop-home/WebKit claims | Outside the measured game-memory scope; no result asserted. |

## Not verified

- An exhaustive combination search. For example, headers+arena cap without the trim timer was not tested; the failed combinations do not establish a sole cause or a global memory minimum.
- Human playing in the owner's real session: creation, walking/flight, opening and returning from real apps, and multi-display/audio continuity with the proposed game-only environment. The headless measurements do not count as that check.
- Product launch/boot time, Prism PSS, the supervisor/helper/laptop-home total in the owner's real session, native Wayland or multiple monitors, and real PipeWire audio. This rig uses null audio and a disposable compositor.
- Fedora's shipped COH CDS archive. Temurin actually mapped classes_coh.jsa in the rejected candidate. The final arena-only candidate does not request compact headers.
- `JE_MALLOC_CONF` behavior, an explicit jemalloc purge, or ownership of anonymous C allocations. Neither library mappings nor an NMT residual prove it.
- A successful frozen return, the sender of its SIGKILL, or the sender of the separate interrupted controller's SIGTERM. These are recorded failures, not human tests being counted as passes.
- The causes of the smaller ten-minute RSS step and long-run growth. Other runtime/backend experiments and laptop-home claims remain outside this brief.

## JUDGMENT-CALL

The unchanged pass line rules out an unconditional shipping recommendation from these measurements. Retain the current product settings. Arena cap 2 is the best measured candidate for an independent follow-up, not a fully qualified release set: its first flat trial adds one 19.948 ms gap against a 15.1 ms/zero > 17 ms control, and first-creation startup tail counts also differ. No later clean trial cancels those observations.

The following describes what linux-aresos would implement only after that qualification question is resolved; nothing ships here.

The final candidate retains heap 1024/256 MiB, G1 free ratios 30/10, MemoryHigh 2560M and distances 8/5. It adds only:

```text
MALLOC_ARENA_MAX=2   (game JVM environment only)
```

For that follow-up implementation, set the cap in `aresos-desktop-java`'s game environment. Keep the current JVM argument string: no compact headers, dedup, worker limits or native trim timer are proposed by this final set. The wrapper's supervisor-supplied allowlist currently excludes the cap; supplying it through the supervisor would require an explicit allowlist/validation change. A fixed game-wrapper default is another implementation choice. Do not set it across the desktop or Prism. Changing this choice later costs a wrapper/environment revision and a game restart, not a save migration. No extra mod or native purge hook is needed.

Recommend no forced GC/reclaim/freezer action on cover under the current pass line. The tested explicit actions started at 30 seconds covered, but every forced GC failed the limit and both frozen returns failed outright. A future revisit must keep one bounded request on the exact owned scope, observe partial EAGAIN, recheck cover state before acting, keep the control loop responsive during the 1.5–3 second write, and prioritize returning. It would also need heartbeat/timer behavior after thaw, the unknown SIGKILL cause, real compositor and audio checks; these are not implemented here.

FerriteCore's consistent 9–12 MiB post-G1 heap saving did not lower flight/covered RSS, so do not add it to the image for this result. System allocation, dedup and worker limits likewise do not earn a place. The retained combined sets failed frame comparisons; their larger memory reductions are not qualified alternatives. No product change is performed by this package.

`JVM_ARGS` currently seeds new Prism instances only. A future adoption of different JVM flags would need an existing-instance migration preserving owner edits. The final arena-only proposal changes no JVM arguments, so it does not require that migration.

## PLAN-GAP

- The rough 35-run estimate omits much of the fresh-control cost. The explicit requirements total 28 factor/control runs, two step-0 runs, ten covered trials, seven required winner runs and two setup runs. Main's mod changes required four additional current flat/creation controls, plus the planned current Nether control: 54 planned experiments. The retired FerriteCore pair adds two actual attempts, the rejected header creation pair adds two, and the rejected native-combination creation/two-flat pairs add six. The final count is 65 actual measurement attempts: 52 completed measurements (not all pass guards), 2 failed freezes, 8 rejected-candidate measurements, 2 retired/partial FerriteCore attempts and 1 interrupted Nether control. The four pre-launch low-memory refusals and four full build/client qualifications are separate.
- Smaps cannot assign all anonymous VMAs to glibc versus jemalloc. Preserve an unattributed class rather than pretend the requested split was measured.
- The research calls a covered full-GC pause invisible; the brief's ≤50 ms post-join guard has no covered exemption. This report applies it unchanged.
- For any future JVM-flag change, `JVM_ARGS` provisioning does not update an existing Prism instance. Such adoption needs more than changing the image's default constant; the final arena-only proposal avoids this migration.
- Five-minute freezer retention can work while return fails. The current 600M request did not reach the estimated 0.2–0.4 GiB absolute RSS, and stable frozen RSS is not evidence of acceptable heartbeat, compositor, audio or clock behavior after thaw.

## Open questions

- Can an independent larger repeat reproduce the arena cap's extra active gap, with the pass line fixed in advance? This study does not establish its cause or qualify the set by dropping that run.
- If JVM flags are revisited later, what migration should linux-aresos use for an existing managed Prism instance while preserving owner-edited arguments?
- What killed both thawing games despite zero scope OOM/high counters, and how should heartbeat, compositor and audio behavior be handled before any freezer revisit?
- How much do game, Prism, helper, supervisor and the laptop home cost together in the real session? That is the research's later product check, outside this rig.
