# 334b review fixes, round 2

`reviews/334b-bench-laptop-safety/REVIEW-2.md` came back CHANGES-NEEDED with eight must-fixes, each a level deeper than
round 1. All eight are cheap and fail closed, so fix them all on `pkg/334b-bench-laptop-safety`. The original brief's
Rules hold. Model: Codex `gpt-6.2-sol`, effort `xhigh`. Keep each fix small and local; don't restructure.

1. **Contradictory readings refuse.** Check the memory fields against their known bounds (`MemFree` and
   `MemAvailable` within `MemTotal`, all present and non-negative). On the laptop, require affirmative evidence of
   external power: an AC or USB supply reporting `online=1`. An empty power inventory, or a battery saying `Charging`
   with every supply offline, refuses with 75. Test each case.
2. **Shutdown never depends on logging.** Logging failures (closed stderr) are swallowed. Neither the guardian nor the
   watcher hands off cleanup or the lock until the cgroup is confirmed empty. Test a failed kill with closed stderr
   and a still-populated scope.
3. **Disk admission stays inside both limits.**
   - Group the reserve check by the underlying space pool (`statvfs` `f_fsid`, not `st_dev`), so Btrfs subvolumes
     sharing one pool share one 20 GB reserve.
   - Recheck the reserve before releasing the scoped worker.
   - Evidence in other worktrees is not scanned (no cross-worktree paths, the lead's round-1 decision). Count a fixed
     allowance of 2 GB for it against the 40 GB cap instead, and say so in the report.
4. **No core dumps.** Set `RLIMIT_CORE` to 0 for every workload at launch. Verify the limit in a stand-in without
   producing a dump.
5. **Mount boundaries on the whole path.** Anchor evidence deletion to the verified current worktree. Check for mount
   transitions on every component from the worktree root down to the deletion root, not just from the immediate
   parent. Add the mounted-parent case to the fake-mount tests.
6. **Unfinished command evidence is not kept.** Stage command-produced evidence under a `.partial` name and publish it
   only after the writer has stopped. Add a hard-kill case that keeps finished `Phase.write` evidence and removes the
   unfinished command output.
7. **One store, one lock.** Derive both the store and the lock from the account's home directory as given by the
   password database (`pwd.getpwuid(os.getuid())`), not from `$HOME`. Refuse an `XDG_CACHE_HOME` or `HOME` that
   would place the store somewhere the canonical lock doesn't cover. Test that two environment setups can't reach one
   store under separate locks.
8. **Tests never signal a recycled PID.** Get pidfds while the launcher still owns the children and pass those handles
   to the tests, never numeric PIDs read back from files. Inject a fixture worktree into the unsafe-cache `clean`
   tests, so a validation regression can't reach real worktree evidence.

Should fix: bring REPORT.md's summary and write table in line with the round 1 and round 2 code (no worktree registry,
no cross-worktree pruning, the 2 GB allowance).

Verify: the touched `test_bench_laptop_*` modules one at a time on the laptop; hosted `checks_only=true`. Add
"Review fixes, round 2" to the REPORT, with each item and the run IDs. Push, leave the PR open, never merge.
