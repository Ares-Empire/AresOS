# Review 2: 334b after review fixes round 1

**Verdict:** CHANGES-NEEDED

## Must fix

1. **The start gates still accept contradictory readings.** `os/ci/bench/laptop.py:59` accepts `MemFree` greater than `MemTotal` when `MemAvailable` looks valid. At `os/ci/bench/laptop.py:130`, an empty power inventory passes, and a battery reporting `Charging` passes even when every reported external supply is offline. These inputs can admit heavy work when the laptop’s state is uncertain. Validate the memory fields with known bounds, require affirmative external-power evidence on the laptop, and test that these cases return 75.

2. **A closed stderr can release the lock before the tree is empty.** `os/ci/bench/laptop.py:331` prints from inside the kill retry loop. If stderr has closed and the cgroup remains populated, that print can raise in both the guardian and the watcher’s fallback. The phase then unwinds into disk cleanup and lock release while a writer may still be alive. Make shutdown independent of logging and require confirmed emptiness before either process can hand off cleanup. Test a failed kill with closed stderr and a still-populated scope.

3. **The disk admission check can exceed both laptop limits.** `os/ci/bench/store.py:84` counts evidence from the current worktree only. A 35 GB store and a 4.9 GB phase can be admitted with another 0.9 GB retained in a different worktree. At `os/ci/bench/store.py:37`, grouping by `st_dev` can also give two Btrfs subvolumes separate 20 GB reserve checks against the same free-space pool. Account for retained evidence across the laptop without giving the store cross-worktree deletion paths. Group reservations by the underlying space pool and recheck the reserve before releasing the scoped worker. [Btrfs subvolume documentation](https://btrfs.readthedocs.io/en/latest/btrfs-subvolume.html)

4. **A workload crash can write outside the disk budget.** `os/ci/bench/write_bounds.py:82` sets `RLIMIT_FSIZE` but leaves the inherited core-dump limit in place. With a nonzero limit and a host coredump handler, an ordinary crash can send gigabytes to a service outside the scope and its declared destinations. Disable workload core dumps at launch and verify the limit in a stand-in without generating a dump. [systemd-coredump documentation](https://www.freedesktop.org/software/systemd/man/latest/systemd-coredump.html)

5. **Cleanup accepts a bind mount on an ancestor of the deletion root.** `os/ci/bench/store_paths.py:20` walks ancestors without checking mount transitions. At `os/ci/bench/store_paths.py:105`, the mount comparison starts at the immediate parent. If the current worktree’s `.work` is a bind mount of another worktree’s `.work`, its marked `bench` directory passes both checks and `clean` deletes the other worktree’s evidence. Anchor evidence traversal to the verified current worktree and check mount boundaries on the path to the deletion root. Add the mounted-parent case to the fake-mount tests.

6. **Interruption recovery keeps unfinished workload evidence.** `os/ci/bench/store.py:123` sweeps only `.partial` files, while `Phase.command` creates writable evidence at its final name at `os/ci/bench/store.py:333`. A killed writer can leave a truncated file that recovery treats as retained evidence. Stage command-produced evidence until it is complete, then publish it after the writer stops. Add a hard-kill case that preserves completed `Phase.write` evidence and removes the unfinished command output.

7. **One store can be reached under two different locks.** `os/ci/bench/laptop_cli.py:53` takes the store location from `XDG_CACHE_HOME` and the lock location from the caller’s `HOME`. Two invocations under the same account can point at one store and acquire different locks, allowing `clean` to remove a live test disk or two heavy phases to run together. Bind native invocations to the account’s canonical dev-rig lock and refuse a conflicting `HOME`. Test that two environment configurations cannot operate on one store under separate locks.

8. **The watcher tests can signal a recycled PID.** `os/tests/test_bench_laptop_watch.py:223`, `:233`, and `:291` open pidfds from numeric PID files. If a target exits and its number is reused before `pidfd_open`, a signal can hit an unrelated process. Obtain the handles while the launcher still owns the children and pass those handles to the test. Also inject a fixture worktree in the unsafe-cache `clean` tests at `os/tests/test_bench_laptop_gates.py:211` so a validation regression cannot reach real worktree evidence.

## Should fix

- Update `reviews/334b-bench-laptop-safety/REPORT.md` so its summary and write table match the round-one implementation. They still describe the removed worktree registry and cross-worktree evidence pruning.

## Known limits

- Build-cache expiry runs on the next locked phase or explicit expiry check. This package adds no scheduled expiry.
- Real user-manager containment, KVM behavior, and pressure response remain step 6 checks, alongside shared-lock adoption by `build.sh` and `run-hub.sh`. Real VM and Podman disk peaks remain step 7 checks. The loss tests cover the watcher and guardian dying independently.

## Checked

- Reviewed `git diff origin/main...HEAD` at `9b4db5c6` against both briefs, the named design sections, and Review 1. `git diff --check origin/main...HEAD` passed. The `AGENTS.md` amendment matches the lead’s narrow store exception and one-copy rule.
- Confirmed the scoped memory recheck, the KVM ioctl, invocation and cgroup identity checks, the independent guardian-loss path, and the unbounded-command refusal. Missing or malformed game cgroup events report `unknown`. Recovery preserves files completed by `Phase.write`, and journal records contain only allow-listed store-relative output kinds.
- Ran `python3 -B -m unittest discover -s os/tests -p 'test_bench_laptop_<name>.py'` separately for `gates`, `store`, and `watch`. They reported 12, 14, and 13 setup errors respectively. The read-only worktree rejected temporary fixture creation with `Errno 30`, so no test body ran.
- In-memory probes confirmed the gate, shutdown logging, disk admission, ancestor mount, and split-lock findings. The review used no live store, dev-rig lock, systemd scope, VM, or container.
