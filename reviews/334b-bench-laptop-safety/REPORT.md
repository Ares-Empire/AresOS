# Package 334b — Laptop bench safety

## Done

- `os/ci/bench/laptop.py` uses the dev rig’s client-test lock and its Lunar Java check. A busy lock, inadequate or invalid memory readings, unconfirmed external power, running Lunar Java or missing VM-mode KVM refuse the run with exit 75. After scope activation and ownership verification, the helper checks Lunar and power again and reads available memory last before exec. The home-screen game is reported from its cgroup events.
- One transient user scope runs under `aresos-bench.slice` with a 5 GiB cap, CPU weight 10, nice 10 and `oom_score_adj=1000`. The launcher leaves swap enabled and sets both core dump limits to zero. The watcher requests graceful shutdown and the guardian limits its duration. Each can stop the pinned cgroup if the other dies. The surviving process retains the shared lock until it confirms the cgroup is empty. [systemd scope settings](https://www.freedesktop.org/software/systemd/man/259/systemd.scope.html) [systemd core dump handling](https://www.freedesktop.org/software/systemd/man/latest/systemd-coredump.html)
- `os/ci/bench/store.py` admits coexisting declared writes against the cap and each affected storage pool’s reserve. It journals the phase before creating its output directories, then rechecks space before releasing the scoped workload. It deletes ephemeral output at phase end and recovers abandoned output at the next locked phase or expiry check. The store retains one image generation with its base disk and one builder boot image. The current worktree retains its five newest evidence runs. A build store expires at the next locked phase or expiry check after seven idle days.
- `bench status` reports measured allocation by storage pool, the fixed allowance against the cap, retention and gate results. The native store and lock both use the account’s canonical home, with the lock outside the store. `bench clean` takes that lock and removes the store and the current worktree’s bench evidence. `AGENTS.md` records the shared store exception and one-copy rule.

### Disk writes and phase peaks

Admission charges measured allocation in the store and current worktree, the new phase’s declared peaks, and a fixed 2 GB allowance for evidence in other worktrees against the **40 GB cap**. It requires **20 GB free on each storage pool receiving writes**. Btrfs subvolumes with the same filesystem UUID share one reserve. When any pool is unknown, admission combines the affected paths and uses the smallest free-space reading. Both limits use decimal bytes. Actual allocation counts by `st_blocks × 512`. Each affected pool gets a 1 MiB coordination allowance. The managed writer charges touched blocks and 64 KiB of metadata per file and rechecks the reserve before each write. Fixed disks are charged at the block-rounded virtual size plus metadata. On Btrfs, the size charge doubles unless the empty file has verified No_COW. A polled directory is charged at its peak plus its declared margin. [Btrfs subvolume storage](https://btrfs.readthedocs.io/en/latest/btrfs-subvolume.html)

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
| Evidence | Current worktree `.work/bench/<run>/` | 180 MB | Five runs in this worktree. Other worktrees are represented by the fixed 2 GB allowance. |
| Journal, ownership markers and directory creation | Store and current worktree evidence trees | 1 MiB coordination allowance per affected storage pool | The journal is removed at phase end. Ownership markers stay with their trees. |

The disk limits above are phase charges. A Btrfs disk without verified No_COW must fit twice its block-rounded virtual size plus metadata within its declared peak. The empty synchronization file uses the dev rig’s existing lock location outside the store. Evidence is staged in the same directory as its final name. Managed writes publish after the write completes. Command evidence publishes after a successful workload and confirmed shutdown. A phase declaring 17 GB of build store, 15 GB of builder scratch and 10 GB of base disk is refused before creating outputs, even on an empty store.

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

## Review fixes, round 1

1. **Start gates.** Validate all memory and PSI rows, including duplicate and contradictory readings. Lunar detection checks the process's recorded UIDs under a pinned proc directory before reading its executable. Unreadable owner executables and unknown power types cause a refusal. VM mode requires opening a character device and getting KVM API version 12. The scoped helper reads the memory floor again after activation and immediately before exec. Gate refusals return 75.
2. **Scope ownership.** The helper waits for permission to exec. The launcher checks its invocation ID, manager-reported cgroup and the membership of its own PID before granting permission. Shutdown signals the pinned cgroup through `cgroup.kill`. It confirms emptiness from pinned `cgroup.events` or kernel removal of that same cgroup. A failed kill is reported as a run failure once emptiness is confirmed. An unconfirmed tree keeps the lock and disk cleanup held. [systemd scope launcher](https://github.com/systemd/systemd/blob/main/src/run/run.c) [Linux cgroup v2](https://docs.kernel.org/admin-guide/cgroup-v2.html)
3. **Guardian loss.** The watcher has its own cgroup descriptors and stops the tree if the guardian exits early. The guardian holds its copy of the shared lock if the watcher dies. The guardian-only SIGKILL test confirms lock contention and disk retention while the fallback is waiting for shutdown.
4. **Bounded workloads.** A phase must create a bounded command before it can launch. Managed writes use `Phase.write`. Raw disks are charged at full virtual size plus metadata. A polled directory is charged at its peak plus its margin and supplies a precreated file. Landlock restricts writes to the declared regular files, and the kernel enforces a hard file-size ceiling. The helper also blocks operations that could bypass that ceiling or delegate host writes. At the directory peak the watcher requests an immediate kill. The fixtures exercised a growing writer, an unbounded command, a fixed disk and an undeclared destination. [Landlock kernel documentation](https://docs.kernel.org/userspace-api/landlock.html)
5. **Deletion.** Cache paths are validated before use. Store and evidence roots carry ownership markers. Cleanup uses directory descriptors and rejects symlink traversal and mount boundaries, including same-device bind mounts. Recovery accepts only store-relative output kinds. The worktree registry is gone. Each worktree counts, prunes and cleans only its own evidence. Existing unmarked directories are refused.
6. **Game state.** A missing or malformed events file for a game scope yields `unknown` unless another game scope is confirmed running.
7. **Evidence recovery.** Recovery sweeps unfinished staging files from this worktree and preserves files completed by `Phase.write`. Explicit clean removes this worktree's entire evidence directory.

### Verification

- Ran `python3 -B -m unittest discover -s os/tests -p 'test_bench_laptop_<name>.py'` separately for `gates`, `store` and `watch`. They printed `Ran 12 tests in 0.017s`, `Ran 14 tests in 0.719s` and `Ran 13 tests in 7.851s`, all with `OK`. Cleanup used fake mount IDs for same-device bind mounts. All tests used fixture paths, a temporary lock and only the processes they started.
- The local stand-in memory reading took 0.969 s to detect and 1.275 s to stop both scope members. The pressure reading took 0.972 s to detect and 1.276 s to stop them. Either guardian-only or watcher-only SIGKILL took 0.002 s to stop the owned stand-ins and left the stand-in game running.
- `git diff --check` passed. `find .work -type f -size +500M -print` listed no files.
- Dispatched `gh workflow run 'OS image' --ref pkg/334b-bench-laptop-safety -f checks_only=true` for `85addb36`. Watched run `45104958316` with `gh run watch 45104958316 --exit-status --interval 60`. The regression job passed in 31m11s and printed `Ran 2628 tests in 1803.956s`, `OK (skipped=24)` and `Live hosted system manager passed: 434 unit files, 421 unit names`. The model-selection job passed in 15s. [Hosted checks-only run](https://github.com/Ares-Empire/AresOS/actions/runs/45104958316)
- On the hosted runner, memory took 0.977 s to detect and 1.279 s to stop the stand-ins. Pressure took 0.976 s to detect and 1.278 s to stop them. Guardian-only SIGKILL took 0.001 s and watcher-only SIGKILL took 0.002 s to stop the stand-ins.

### Known limits from review 1

- Build-cache expiry runs during the next locked phase or explicit expiry check. This package adds no scheduled seven-day cleanup.
- Step 6 still owns real user-manager behavior, workload containment, laptop pressure and stop timing, KVM behavior and adoption of the shared lock by `mod/dev/build.sh` and `mod/dev/run-hub.sh`. Step 7 still owns verification of real write peaks and storage bounds for VM and Podman. The regular-file contract and synthetic polling case use Linux x86-64, Landlock ABI 3 or later and seccomp. Fixed disks in the same command must fit its common file-size ceiling.
- The watcher and guardian cover either process dying independently. Simultaneous loss of both remains outside this round's tests.

## Review fixes, round 2

1. **Gate readings.** Require all three memory counters in kB, with `MemFree` and `MemAvailable` between zero and the positive `MemTotal`. The power gate requires an online mains or USB supply and refuses when a system battery is discharging. An empty inventory, charging with offline external power and out-of-bounds memory each return 75 before scope launch.
2. **Shutdown.** Closed stderr cannot interrupt the retry loop. The guardian and watcher fallback keep ownership of shutdown until the pinned scope is confirmed empty. A test forces two failed kills with closed stderr and a populated scope before allowing shutdown to complete.
3. **Disk admission.** Recheck free space after scope activation and before granting permission to exec. Charge the fixed 2 GB allowance against the cap. Round 2 grouped equal `f_fsid` values. Round 3 adds filesystem UUIDs for Btrfs, where `f_fsid` varies across subvolumes. The reserve recheck and cap tests simulate a 35 GB store and a drop in available space after activation. [Linux Btrfs implementation](https://github.com/torvalds/linux/blob/v6.18/fs/btrfs/super.c)
4. **Core dumps.** Set the soft and hard `RLIMIT_CORE` to zero for every workload. The fixed-disk stand-in reads back both limits without crashing. [systemd core dump handling](https://www.freedesktop.org/software/systemd/man/latest/systemd-coredump.html)
5. **Evidence mounts.** Traverse from the opened worktree root through `.work` and `bench` with descriptor-relative mount checks. The same-device fake-mount test puts a mount boundary on `.work` and confirms the evidence survives `clean`.
6. **Evidence recovery.** Give commands writable `.partial` files and publish them after successful exit and confirmed scope shutdown. The hard-kill test removes the staged command file during recovery and keeps the completed `Phase.write` file.
7. **Canonical lock and store.** Use the password database home for both `.cache/aresos-bench` and `.cache/aresos-dev/client-test.lock`. Absent variables and explicit matching values resolve to the same lock. Conflicting `HOME` or `XDG_CACHE_HOME` values are refused. Two accepted setups contend for the same fixture lock.
8. **Test isolation.** The test launchers open pidfds for their owned children and pass the descriptors over fixture Unix sockets. The unsafe-cache cleanup tests use a fixture home and worktree.

### Verification

- Ran `python3 -B -m unittest discover -s os/tests -p 'test_bench_laptop_<name>.py'` one module at a time. The final runs reported `Ran 14 tests in 0.025s` for `gates`, `Ran 16 tests in 0.754s` for `store` and `Ran 16 tests in 8.855s` for `watch`, each with `OK`. The tests used only fixture locks, stores, proc and sys inputs and stand-ins they started.
- Locally, falling available memory took 0.975 s to detect and 1.278 s to stop the scope members. Rising pressure took 0.968 s to detect and 1.271 s to stop them. Guardian-only and watcher-only SIGKILL each took 0.002 s to stop the scope members. The stand-in game survived each case.
- `git diff --check` passed. `find .work -type f -size +500M -print` listed no files.
- Dispatched `gh workflow run 'OS image' --ref pkg/334b-bench-laptop-safety -f checks_only=true` for `6d2a1db1`. Watched `45109390834` with `gh run watch 45109390834 --exit-status --interval 60`. The regression job passed in 44m21s and printed `Ran 2635 tests in 2620.395s`, `OK (skipped=24)` and `Live hosted system manager passed: 437 unit files, 468 unit names`. All 46 bench tests passed. The model-selection job passed in 23s and selected the bounded slice. [Hosted checks-only run](https://github.com/Ares-Empire/AresOS/actions/runs/45109390834)
- On the hosted runner, the memory and pressure changes each took 0.970 s to detect. The scope members stopped after 1.271 s for memory and 1.272 s for pressure. Either single-process SIGKILL took 0.002 s to stop the scope members.

### Known limits from review 2

- The 2 GB allowance estimates retained evidence across other worktrees. Actual evidence across several worktrees can exceed that allowance. Cleanup and pruning are confined to the current worktree. Build-cache expiry runs on the next locked phase or explicit expiry check.
- Step 6 still owns the real user-manager, KVM, pressure and shared-lock adoption checks. Step 7 still owns real VM and Podman disk peaks. The loss tests cover the watcher and guardian dying independently.

## Review fixes, round 3

1. **Launch gates.** Recheck Lunar Java and external power after the scoped helper receives its release byte. Available memory remains the last safety reading before exec. Two regressions change only fixture proc or power data during scope activation and confirm exit 75 before the stand-in runs.
2. **Fixed disks.** Set `FS_NOCOW_FL` on the Btrfs output directory and read the attribute from the new empty file before sizing it. Charge one block-rounded virtual size when verified and two when absent or unreadable, plus 64 KiB of file overhead in either case. An unknown filesystem type also uses the doubled charge. The reserve tests cover refusal with space for only one copy, admission with space for two, and admission at the original boundary with verified No_COW or on ext4. The bounded writer also overwrites a previously filled disk at the same length.
3. **Storage pools.** Find the opened path’s filesystem type in mountinfo and read the filesystem UUID from that Btrfs mount with `BTRFS_IOC_FS_INFO`. The kernel returns the same UUID for its subvolumes without needing to open a block device. With an unknown pool, reserve admission combines the peaks and uses the lowest free-space reading. Tests exercise distinct subvolume IDs with a shared UUID and the unknown-pool fallback. [Linux Btrfs filesystem info](https://linux.googlesource.com/linux/kernel/git/torvalds/linux/+/94426e4201fbb1c5ea4a697eb62a8b7cd7dfccbf/fs/btrfs/ioctl.c)

### Verification

- Ran `python3 -B -m unittest discover -s os/tests -p 'test_bench_laptop_store.py'` and then the same command for `test_bench_laptop_watch.py`. They printed `Ran 18 tests in 0.798s` and `Ran 18 tests in 9.322s`, both `OK`. An initial verbose store run failed on the new test fixture’s free-space rounding. After fixing the fixture, both verbose runs also passed. Tests used fixture paths, a fixture lock and owned stand-ins.
- The last watcher run detected falling memory in 0.972 s and stopped the stand-ins after 1.275 s. Rising pressure took 0.971 s to detect and 1.274 s to stop them. Guardian-only SIGKILL took 0.001 s and watcher-only SIGKILL took 0.002 s to stop the stand-ins.
- In a temporary directory on the laptop home filesystem, `stat -f -c %T` printed `btrfs`. Unprivileged `chattr +C disks` succeeded. After creating an empty image, `lsattr -d disks` and `lsattr disks/empty.img` printed `---------------C------` for both entries. A second temporary fixture confirmed the bench code could read the Btrfs UUID, set the directory flag and verify inheritance on the empty file. Both fixtures were removed.
- `git diff --check` passed. `find .work -type f -size +500M -print` listed no files.
- Dispatched `gh workflow run 'OS image' --ref pkg/334b-bench-laptop-safety -f checks_only=true` for `172005e1` and watched run `45115132328` with `gh run watch 45115132328 --exit-status --interval 60`. The regression job passed in 31m03s and printed `Ran 2639 tests in 1805.268s`, `OK (skipped=24)` and `Live hosted system manager passed: 434 unit files, 421 unit names`. All 50 laptop bench tests passed. The model-selection job passed in 16s. [Hosted OS checks-only run](https://github.com/Ares-Empire/AresOS/actions/runs/45115132328)
- On the hosted runner, falling memory took 0.978 s to detect and rising pressure took 0.979 s. The stand-ins stopped after 1.280 s in both cases. Either single-process SIGKILL took 0.001 s to stop the stand-ins.
- The PR privacy check passed for `172005e1`. [Hosted Repo privacy run](https://github.com/Ares-Empire/AresOS/actions/runs/45115140443)

### Known limits from review 3

- The earlier subvolume gap required evidence and the store to reside on different subvolumes of the same Btrfs filesystem. Round 3 adds the shared reserve for that layout. The tests model distinct subvolumes with fixture mountinfo and a fake UUID reader.
- A hard kill during initial ownership-marker creation can leave a directory that cleanup refuses. Real user-manager containment and pressure timing remain step 6 checks. Real VM and Podman write peaks remain step 7 checks.
