# 334b review fixes, round 1

`reviews/334b-bench-laptop-safety/REVIEW-1.md` came back CHANGES-NEEDED with five must-fixes. This code guards the
owner's running game and his SSD, so each fix fails closed. Fix on `pkg/334b-bench-laptop-safety`. The original brief's
Rules all still hold, above all "tests never touch the real thing". Model: Codex `gpt-6.2-sol`, effort `xhigh`.

## Decided by the lead

- **No cross-worktree registry.** Drop the worktree registry entirely. `bench clean` removes the store and the
  **current** worktree's `.work/bench/` only. Evidence pruning ("five runs") works in the current worktree only.
  Nothing else in the store may name a path to delete.
- **Only bounded writes run.** A phase may launch a command only if every writable destination it gets has an
  enforced bound declared up front:
  - a disk image with a fixed virtual size, counted at that size;
  - a file written through `Phase.write`;
  - a directory the bench polls and kills at its peak, counted at its peak plus a declared margin.
  A command with any other writable destination is refused before launch. The concrete VM and Podman mechanisms come
  in steps 6 to 8. This step provides the contract and refuses everything else.

## Must fix

1. **Gates fail closed on bad input** (must fix 1).
   - An unreadable Lunar link, an unknown battery type, or a malformed or contradictory `/proc/meminfo` or PSI record
     refuses with exit 75 and a reason.
   - KVM means `/dev/kvm` opens and answers `KVM_GET_API_VERSION`, not that the path is accessible.
   - The final memory check runs last, right before the heavy process starts, after the other gates and after the
     scope is up.
   - Test each malformed case.
2. **Shutdown proves ownership** (must fix 2). Bind stop and kill to the scope the launcher actually created: its
   invocation ID and cgroup, checked after start. If the launcher didn't create it, never stop a unit with that name.
   A failed `systemctl stop`, or a cgroup that can't be confirmed empty, is a shutdown failure. Cleanup and the lock
   stay held until the owned tree is confirmed empty.
3. **Guardian loss stops the workload** (must fix 3). Add an independent stop path when the guardian dies. Keep the
   lock, and don't unlink a disk with a live writer, until shutdown is confirmed. Add a guardian-only SIGKILL test
   next to the watcher-only test.
4. **Disk peaks bind the workload** (must fix 4): the lead's "only bounded writes run" contract above, with a
   file-writing stand-in that is stopped at its peak and a test that an unbounded phase is refused.
5. **Deletion never leaves the bench's own directories** (must fix 5).
   - `XDG_CACHE_HOME` must be absolute, not `/`, and owned by the user. No component of the store path may be a
     symlink.
   - The store root carries a marker file the bench created. Without the marker the bench never deletes there.
   - Delete through directory file descriptors without following symlinks, and refuse mount points, including bind
     mounts on the same device and a mount at the deletion root.
   - Recovery records name paths relative to the store only.
   - Test with symlinks, `..`, a relative and an empty `XDG_CACHE_HOME`, `/`, a planted record pointing outside, and a
     bind-mount stand-in if possible without root (otherwise a fake mountinfo).

## Should fix

6. Report `unknown`, not `idle`, for missing or malformed game cgroup events.
7. Next-run recovery keeps the evidence files that `Phase.write` finished. `clean` still removes the whole run.

## Verify

The touched `test_bench_laptop_*` modules one at a time on the laptop; hosted `checks_only=true`. Add "Review fixes,
round 1" to the REPORT with each item and the run IDs, and REVIEW-1's Known limits. Push, leave the PR open, never
merge.
