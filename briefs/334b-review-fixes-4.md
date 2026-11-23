# 334b review fixes, round 4

`reviews/334b-bench-laptop-safety/REVIEW-4.md` came back CHANGES-NEEDED with one must-fix: the same Btrfs copy-on-write
gap as round 3, in the other bounded write class. Fix it and the should-fix on `pkg/334b-bench-laptop-safety`. Earlier
decisions and Rules hold. Model: Codex `gpt-6.2-sol`, effort `xhigh`. Keep it small.

1. **One copy-on-write rule for every bounded write on Btrfs** (must fix 1). Apply round 3's rule to every write class
   the budget admits on Btrfs, not only `FixedDisk`: `PolledDirectory` (test disks, scratch, Podman temporary output)
   and anything else that charges by length or polled blocks.
   - A destination counts at its peak plus margin only if No_COW is set on it and verified before the first write. For
     a directory, set it on the directory so new files inherit it, and verify on a probe file.
   - Otherwise it counts at twice its peak plus margin.
   - Don't add another write class without this rule: put the rule in one place that every class goes through.
   - Add regressions for a polled output with and without verified No_COW.
2. **A forced stop is a failed workload** (should fix). When the foreground command exits 0 but descendants had to be
   killed to empty the scope, the phase fails, and its staged command output stays unpublished (recovery removes it).
   Finished `Phase.write` evidence survives. Add the test.
3. Known limit from REVIEW-4: use the fixture's owned pidfds for test teardown instead of `killpg`. It's cheap, so do
   it.

Add "Review fixes, round 4" to the REPORT with each item and the run IDs. Verify: the touched modules one at a time on
the laptop; hosted `checks_only=true`. Push, leave the PR open, never merge.
