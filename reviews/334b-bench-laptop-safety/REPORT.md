# Package 334b — Laptop bench safety

## Done

- `os/ci/bench/laptop.py` uses the dev rig’s client-test lock and its Lunar Java check. Bench runs refuse a busy lock, inadequate memory, battery operation or missing VM-mode KVM with exit 75. The run checks the gates before phase setup and immediately before launch. The home-screen game is reported from its populated cgroup.
- One transient user scope runs under `aresos-bench.slice` with a 5 GiB cap, CPU weight 10, nice 10 and `oom_score_adj=1000`. The launcher leaves swap enabled. A separate guardian outside that slice retains the shared lock until the scope empties. It watches a PID handle for the bench caller and stops the scope if the caller dies. The memory watcher requests graceful shutdown through a callback and the guardian bounds the grace period. [systemd scope settings](https://www.freedesktop.org/software/systemd/man/259/systemd.scope.html)
- `os/ci/bench/store.py` admits the sum of coexisting writes across filesystems. It journals the phase before creating its output directories and recovers abandoned outputs at the next run or expiry check. Normal completion, failure and catchable signals delete the ephemeral files. One image generation and its base disk, one builder boot image, and five evidence runs are retained across worktrees. A build store expires at the next locked run or expiry check after seven idle days.
- `os/ci/bench/bench status` reads allocated bytes by filesystem, retention and gate results. `bench clean` takes the same lock and removes the store and bench evidence from registered worktrees. `AGENTS.md` records the shared store exception and one-copy rule.

### Disk writes and phase peaks

The global cap is **40 GB allocated** and the reserve is **20 GB free on each filesystem receiving writes**. Both use decimal bytes. The phase declares a peak for every applicable row. It may declare smaller peaks. Existing files count by `st_blocks × 512` and the check adds 1 MiB per affected filesystem for bookkeeping. The managed writer charges touched blocks and a 64 KiB per-file metadata allowance before creating a file. It also rechecks the free-space reserve before each write.

| Phase output | Write location | Maximum per declared output | Retention |
| --- | --- | ---: | --- |
| Build cache and layers | Store `build-store/` | 17 GB | Seven idle days |
| Podman temporary data | Store `podman-tmp/` | 17 GB | Phase end |
| New image payload | Store `image/image/` | 7 GB | Replaced with the base disk |
| New base disk | Store `image/base-disk/` | 10 GB | Replaced with the image |
| Image export | Store `export/` | 7 GB | Phase end |
| Builder boot image | Store `builder-boot/` | 1 GB | One copy |
| Builder scratch disk | Store `builder-scratch/` | 15 GB | Phase end |
| Test overlay | Store `test-disk/` | 10 GB | Test end, including failures and signals |
| Evidence | Worktree `.work/bench/<run>/` | 180 MB | Five runs across worktrees |
| Journal, worktree registrations and directory creation | Store and evidence trees | 1 MiB coordination allowance per affected filesystem | Journal removed at phase end. Registry retained until clean. |

The empty synchronization file uses the dev rig’s existing lock location outside the store. File staging uses same-directory renames. A phase declaring 17 GB of build store, 15 GB of builder scratch and 10 GB of base disk is refused before creating outputs, even on an empty store.

## Verified

- Ran `python3 -B -m unittest discover -s os/tests -p 'test_bench_laptop_gates.py' -v`, then the same command separately for `test_bench_laptop_store.py` and `test_bench_laptop_watch.py`. They printed `Ran 6 tests in 0.008s`, `Ran 10 tests in 0.487s` and `Ran 5 tests in 4.887s`, each with `OK`. A second run printed the same test counts and `OK` for all three modules. The tests used fake proc, sys, KVM, free-space, store and lock paths and only signalled processes they started.
- `git diff --check` passed. `os/ci/bench/bench --help` returned the two commands. `find .work -type f -size +500M -print` listed no files.
- Dispatched `gh workflow run 'OS image' --ref pkg/334b-bench-laptop-safety -f checks_only=true`. Run [45098910833](https://github.com/Ares-Empire/AresOS/actions/runs/45098910833) was superseded after adding the signal-during-stop regression. Watched [45099195144](https://github.com/Ares-Empire/AresOS/actions/runs/45099195144) on `eece3fac` with `gh run watch 45099195144 --exit-status --interval 60`. The regression job finished in 33m48s and printed `Ran 2610 tests in 1975.341s`, `OK (skipped=24)` and `Live hosted system manager passed: 437 unit files, 466 unit names`. All 21 package tests passed on the runner.

| Stand-in case | Detection after fixture change | Both scope members stopped |
| --- | ---: | ---: |
| Falling available memory | 0.971–0.973 s | 1.272–1.275 s |
| Rising memory pressure | 0.976–0.980 s | 1.278–1.282 s |
| Watcher SIGKILL | PID handle event | 0.002 s |

The separate stand-in game survived every case. Tests sampled every second and used a 0.3 s shutdown grace. SIGKILL of the watcher skipped that grace. The signal-during-stop test held disk cleanup until the guardian had stopped the remaining stand-in. On the hosted runner, memory and pressure each took 0.981 s to detect and 1.283 s to stop. Watcher loss took 0.002 s to stop. A separate test killed a file-writing phase midway and exercised recovery on both the next run and `clean`.

## Not verified

- Step 6 will verify enforcement by the laptop’s user manager, keep the full rootless tree inside the cap, and measure real pressure, swap growth, responsiveness, KVM access and termination delays.
- Step 7 will verify real workload write peaks, builder boot-image provenance and the storage bounds used by external programs.
- The package had no mod changes or visual acceptance. The local mod client tests require the real shared lock, and the hosted Mod job starts a builder container. Both are outside this brief’s test rules.

## JUDGMENT-CALL

- The watcher starts with a 2 GiB minimum, a 10% Linux PSI `some avg10` threshold, a one-second sample interval and two-second grace. The brief sets the 7 GiB and 6 GiB start gates. Reusing those numbers during a run would trigger when a 4 GiB guest consumes its expected memory. The watcher values are parameters for step 6. Local build mode also starts with a 5 GiB scope cap pending measurement.
- Disk placement keeps export, scratch and Podman temporary data under the shared store. Evidence may use a second filesystem. Admission requires the reserve without counting hypothetical free space from deleting a prior generation. Snapshots and shared extents can prevent those bytes from becoming available. Updating a ceiling or phase declaration is a code change without a store migration.

## PLAN-GAP

- `mod/dev/build.sh` and `mod/dev/run-hub.sh` still need the shared lock. The brief assigns those changes and the concurrent-build proof to step 6.
- The design gives estimates for overlapping disk outputs. Some combinations exceed 40 GB. Step 7 needs measured sub-phases and enforced bounds for the external writers before it can enable the laptop image path.

## Known limits

- System-wide PSI and available memory lag workload changes. A sudden allocation or scheduling stall can beat the watcher. The measurements above exercise fakes and the owned stand-in processes.
- The managed file writer enforces its own allocations. External tools will need independently bounded output locations before step 7 can use them. A simultaneous loss of the watcher and its guardian is outside the single-process loss test.
- Cleanup after a hard kill runs when the next locked command recovers the journal. Build cache expiry also runs under the shared lock when the bench next runs or explicitly checks expiry.

## Open questions

- Step 6 will set the final build cap and watcher thresholds from laptop measurements. Step 7 will set the release-to-laptop phase peaks.
