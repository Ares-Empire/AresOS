# 334b: the bench's laptop safety pieces (test bench, step 2)

**Goal:** the safety layer every later laptop step of the test bench stands on (`docs/design/TEST-BENCH.md`, step 2).
It covers one heavy thing at a time, start gates, the capped process tree and its watcher, a disk budget enforced
before writes, and automatic cleanup. This step builds and tests these pieces with fakes and stand-in processes. It
starts no VM, container or image build. Those come in steps 6 to 8, which will use these pieces.

What the owner was promised (board T500 and his question on disk space): the 40 GB is a cap, not a reservation. Only
the newest bench image is kept, each test's disk is deleted when the test ends, `bench clean` removes everything, and
normal use stays well under the cap.

Model: Codex `gpt-6.2-sol`, effort `xhigh` (the repo's build default; this code guards the owner's game and SSD).

## Read first

- `AGENTS.md`.
- `docs/design/TEST-BENCH.md`:
  - section 3, "Memory (laptop)" and "Disk space (laptop)" with its table;
  - section 6, the `bench` interface and exit codes;
  - section 7, step 2's row and "Carried into the step briefs", Step 2 (part of this brief), and Step 6 for what
    comes later;
  - section 9, Known limits.
- `reviews/334-test-bench/REVIEW-2.md` (blocking 2) and `REVIEW-3.md` (blocking 2 and 3), for why the gates look the
  way they do.
- `mod/dev/env.sh` (`aresos_lunar_game_pids`, `aresos_available_kib`, `aresos_check_room`, `aresos_lock`,
  `aresos_scope_start`, `aresos_stop_scopes`, the client-test lock) and `mod/dev/client-test.sh`: the dev rig's
  existing lock, floors and scopes, which the bench reuses.
- `os/ci/bench/` (step 1, on `main`): where the bench code lives.
- `os/ci/overlay/checks.py` (`desktop_jvm`, `memory_protection`): the `aresos-game-*.scope` name and oomd's settings.

## Decided by the lead

- **The store's location.** The bench's store lives at `${XDG_CACHE_HOME:-$HOME/.cache}/aresos-bench/`, one store for
  the laptop, outside every worktree. Images and disks must outlive a worktree, and the disk cap is per laptop, not
  per worktree. Evidence stays in the worktree's `.work/bench/`, as section 6 says.
  - Amend `AGENTS.md` rule 1 with one narrow exception: the bench store, written only through the bench's own code.
    The shared lock is not in the store.
  - Rule 7's "one verified copy of each large download" holds inside the store too.
- **The shared lock.** The bench takes the existing client-test lock from `mod/dev/env.sh`, so the bench and the dev
  rig's client tests never run their heavy work at the same time. When the lock is busy, the bench exits 75 before
  any heavy work. Making `mod/dev/build.sh` and `mod/dev/run-hub.sh` take the same lock is **not** in this step. They
  belong to another lead and go into step 6's brief. Record it under PLAN-GAP in the report.

## In scope

All code under `os/ci/bench/` (the release build excludes `ci/`), plus the `AGENTS.md` amendment.

1. **Start gates.** Each gate returns exit 75 with a short reason, and there is no `--force`.
   - Memory floors: 7 GiB available for a 4 GiB guest, 6 GiB for a local build. Checked at start and again right
     before the heavy process.
   - Refuse while Lunar Client's Java runs (the same test as `aresos_lunar_game_pids`), on battery, and without
     `/dev/kvm` for VM mode.
   - Detect the home screen's game as an `aresos-game-*.scope` by reading the cgroup tree; it is not a refusal. Report
     it so later steps can give the guest two CPUs.
   - Every input path (`/proc/meminfo`, `/proc/pressure/memory`, `/sys/class/power_supply`, the cgroup root, `/dev/kvm`)
     is a parameter, so tests use fakes.
2. **The capped tree.** A launcher that starts a command in a transient user scope inside one bench slice, with
   `MemoryMax` (5 GiB in VM mode), low CPU weight and `nice`, and `oom_score_adj=1000` for the heavy process. Swap stays
   enabled. Test the exact `systemd-run` arguments. Running it for real under the user manager is step 6's check.
3. **The watcher.** It runs outside the bench slice. Every 1 to 2 seconds it reads `MemAvailable` and
   `/proc/pressure/memory`. Below the floor, or above the pressure threshold, it asks the tree to stop gracefully (a
   callback; QMP `system_powerdown` arrives in a later step), then kills the scope after a short grace. **If the watcher
   dies, the tree stops.** The thresholds are parameters with the section 3 starting values; step 6 measures and sets
   them. Prove with stand-in processes and fake proc files that:
   - a falling `MemAvailable` stops the stand-in tree;
   - rising pressure stops it;
   - killing the watcher stops it;
   - a stand-in "game" process outside the tree keeps running in every case.
   Report the measured detection and stop delays from these tests, with the caveat that real pressure is step 6's.
4. **The disk budget, enforced before writes.**
   - Count every bench write on each filesystem: store, export, builder scratch, Podman temporary storage, allocated
     growth of sparse disks (`st_blocks`, not apparent size) and evidence.
   - Each phase declares its peak. Refuse a phase before it writes if current use plus that peak would exceed 40 GB,
     or if the filesystem can't fit it and still keep 20 GB free.
   - List every write and each phase's enforced peak in the report (the step 2 carry-over).
5. **Automatic cleanup:**
   - keep only the newest bench image and its base disk; delete the older one before a replacement is written;
   - delete each test's disk when the test ends, also on failure and on a signal;
   - delete the export and the builder scratch in the step that made them;
   - delete the build store after seven idle days;
   - `bench clean` removes all bench data, retained evidence included.
   - Run, expiry cleanup and `clean` all take the shared lock, which lives outside the store. Cleanup refuses an
     active store.
   - **Interruption:** a phase records what it is writing before it writes. The next run or `clean` removes partial
     files left by a killed phase. Prove it by killing a stand-in phase midway.
6. **`bench status` and `bench clean`** (section 6), with exit codes 0 / 1 / 2 / 75. `status` prints the store's use
   against the cap, what is kept and why, and the gates' current answers. It only reads.
7. **Tests** in `os/tests/test_bench_laptop_*.py`, run by the hosted checks.

## Out of scope

- Starting QEMU, Podman, a VM, a container or an image build, on the laptop or anywhere. Steps 6 to 8 do that.
- Changing `mod/dev/build.sh`, `mod/dev/run-hub.sh` or anything else under `mod/` (another lead's area; step 6).
- The network levels, the desk and the recorder.

## Rules

- `AGENTS.md` holds, and its laptop rules matter here: no sudo, nothing installed system-wide, no window or input in
  the owner's session, never `test_owner_update`, and run only the test modules you touch, one at a time.
- **Tests never touch the real thing.** They use temporary directories for the store, the lock and every proc or sys
  path. They never take the real client-test lock, never write to the real `~/.cache/aresos-bench`, and only ever
  stop processes they started. A test that would need real memory pressure belongs to step 6.
- Hosted: `gh workflow run "OS image" --ref <branch> -f checks_only=true`, watched with
  `gh run watch <id> --exit-status --interval 60`. No bench dispatches are needed in this step.
- Write "the owner", never a person's name. Repo-relative paths in everything committed.
- Commit and push on `pkg/334b-bench-laptop-safety`, open a PR into `main`, never merge. Name the model in commit
  trailers. Keep `reviews/334b-bench-laptop-safety/PROGRESS.md` while you work. At the end, write `REPORT.md` there:
  what was built, the write and peak table, the watcher's measured delays, the run IDs, PLAN-GAP and Known limits.
  Then delete `PROGRESS.md`.
