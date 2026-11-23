# Review 3: 334b after review fixes round 2

**Verdict:** CHANGES-NEEDED

## Must fix

1. **The battery and Lunar gates can go stale before launch.** `os/ci/bench/laptop.py:511` checks both before starting the scope. Scope activation, ownership verification, and the disk recheck follow. At `os/ci/bench/laptop.py:422`, the helper checks only memory before `exec`. Unplugging the laptop or starting Lunar during that window can admit heavy work that should return 75. An in-memory check confirmed that switching to battery after the full gate still reached `exec`. Recheck the launch gates after scope activation, keep memory as the final read, and add regressions for power and Lunar changing during activation.
2. **The disk limit bounds file length but can breach the SSD reserve on Btrfs.** `os/ci/bench/store.py:321` budgets one file’s worth of blocks plus 64 KiB, and `os/ci/bench/write_bounds.py:82` enforces a file-length limit. The worktree is on Btrfs, where ordinary overwrites can allocate replacement blocks while the old blocks still occupy space. A fixed-size disk can therefore consume more than its admitted peak and cross the 20 GB reserve without growing in length. Require an enforceable physical allocation bound that covers rewrites, or refuse that write mode before launch. Add a regression for a fixed-size overwrite at the reserve boundary. [Btrfs copy-on-write design](https://btrfs.readthedocs.io/en/stable/dev/dev-btrfs-design.html#copy-on-write-logging)

## Should fix

- Correct the storage-pool claim in `reviews/334b-bench-laptop-safety/REPORT.md:12` and `:97`. Round 2 added the reserve recheck and the 2 GB evidence allowance, but its subvolume test supplies the same `f_fsid` to both paths. Linux includes the subvolume ID in Btrfs `f_fsid`. Use a filesystem-wide identifier or conservatively combine uncertain pools, and test with distinct subvolume IDs sharing one pool. [Linux Btrfs implementation](https://github.com/torvalds/linux/blob/v6.18/fs/btrfs/super.c)

## Known limits

- The subvolume accounting gap requires the store and evidence to land on different subvolumes of the same filesystem. It does not affect ordinary worktrees and a cache inside one home subvolume.
- A hard kill during initial ownership-marker creation can leave a directory that subsequent cleanup refuses. Real user-manager containment and pressure timing remain step 6 checks. Real VM and Podman write peaks remain step 7 checks.

## Checked

- Reviewed `git diff origin/main...HEAD` at `6e692949` against the original brief, both fix briefs, the named design sections, and both prior reviews. `git diff --check origin/main...HEAD` passed.
- Confirmed the earlier parser, KVM ioctl, and game-state fixes. Shutdown uses the pinned cgroup and independent watcher and guardian paths. The surviving supervisor holds the shared lock until the tree is confirmed empty, including when stderr is closed.
- Confirmed the canonical dev-rig lock, descriptor-relative cleanup, mount checks, restricted recovery records, and staging of unfinished command evidence. The report now describes current-worktree cleanup and the 2 GB allowance. The `AGENTS.md` amendment stays within the brief.
- Inspected test isolation and ran the requested modules one at a time. Gates, store, and watcher reported 14, 16, and 16 setup errors respectively. The read-only worktree rejected temporary fixture creation with `Errno 30`, so no test body ran. The in-memory probes used no real store, dev-rig lock, scope, VM, or container.
