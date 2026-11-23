# Review 4: 334b after review fixes round 3

**Verdict:** CHANGES-NEEDED

## Must fix

1. **Polled outputs can breach the 20 GB reserve on Btrfs.** `os/ci/bench/store.py:389–420` verifies No_COW or charges for a second copy only for `FixedDisk`. The same API accepts `PolledDirectory` for test disks and scratch files, where it charges `peak + margin` and enforces a file-length ceiling. An ordinary overwrite can allocate replacement blocks while Btrfs still holds the old blocks. The inode’s `st_blocks` poll at `os/ci/bench/store.py:446–451` cannot account for that transient space. An in-memory probe confirmed that a 4 GB polled output with an 8 MiB margin was admitted with about 1.1 MB above its file-length ceiling, including coordination space. Apply verified No_COW or a conservative physical allocation bound to polled outputs on Btrfs and unknown filesystems. Refuse the output before launch if that bound would cross the reserve. Add a reserve-boundary regression for a polled writer that overwrites existing blocks. [Btrfs copy-on-write design](https://btrfs.readthedocs.io/en/latest/dev/dev-btrfs-design.html#copy-on-write-logging)

## Should fix

- **Keep forced-stop evidence staged.** At `os/ci/bench/laptop.py:440–448` and `:504–512`, a launcher can exit 0 while a descendant is still writing. The guardian kills the remaining tree and reports success once it is empty. `os/ci/bench/laptop_cli.py:30–32` then publishes the staged file. Treat a clean foreground exit followed by forced descendant shutdown as a failed workload, and test that completed `Phase.write` evidence still survives.

## Known limits

- The watcher tests use pidfds for the targeted fault injections. The fixture’s teardown still calls `killpg` at `os/tests/test_bench_laptop_watch.py:81`. Recycling that group number would require the watcher and all group members to exit before the guardian signals it. Using the fixture’s owned pidfds for teardown would close that edge case.
- A hard kill during ownership-marker creation can leave a directory that cleanup refuses. Real user-manager containment and pressure timing remain step 6 checks. Real workload write peaks remain a step 7 check.

## Checked

- Reviewed `git diff origin/main...HEAD` at `6221b5f3` against the original brief, the named design sections, and all three reviews and fix briefs. `git diff --check origin/main...HEAD` passed.
- Confirmed fail-closed gate parsing, the KVM ioctl, post-activation Lunar and power checks, and memory as the final safety read before exec. Missing or malformed game events report `unknown`.
- Confirmed invocation and cgroup ownership checks, pinned shutdown, independent watcher and guardian stop paths, and lock retention until confirmed emptiness. The scoped worker sets both core dump limits to zero.
- Confirmed the canonical dev-rig lock, descriptor-relative cleanup and mount checks, allow-listed recovery records, and preservation of completed managed evidence. The fixed-disk No_COW handling, Btrfs pool grouping, pre-release reserve recheck, report corrections, and narrow `AGENTS.md` amendment match the fix briefs.
- Ran `python3 -B -m unittest discover -s os/tests -p 'test_bench_laptop_<name>.py'` one module at a time. `gates`, `store`, and `watch` reported 14, 18, and 18 setup errors respectively. The read-only worktree rejected temporary fixture creation with `Errno 30`, so no test body ran. The review used no live bench store, dev-rig lock, systemd scope, VM, or container.
