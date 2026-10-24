# 11j: Fix the stock pause's idle check, keep its evidence, then finish A and B

Follow-up on branch `pkg/11-two-disk-rehearsal` (draft PR #11). Read the "11i" section of `reviews/11-two-disk-rehearsal/REPORT.md`. Briefs 11c–11g and 11i still apply, plus the changes below.

## What stopped 11i

The first real installation passed, and Windows-first restoration was exact. At the first installed stock login, 11g's updater pause masked the services and disabled `uupd.timer`, then stopped at its 300-second idle deadline. The final predicate values weren't exported, so the run didn't show which condition stayed false. Stopping was correct.

## Integrator finding (zero cost, from retained evidence)

The idle wait requires `pgrep -x bootc` and `pgrep -x rpm-ostree` to find nothing. But rpm-ostree's own system daemon is started as `rpm-ostree start-daemon`, so its process name is `rpm-ostree`. See `rpm-ostreed.service` with `ExecStart=+rpm-ostree start-daemon`, line 2501 of `os/manifest/ci/03e/vm-pass-1/runtime-updaters.json`. The same loop calls `rpm-ostree status --json` every ~2 seconds, which activates that daemon over D-Bus and keeps it from exiting when idle. On a real system, the "no client process" condition is very likely **never** true. That makes this a deterministic bug in our check, not a timing problem.

The stock-prepare tests mock `pgrep` to always return 1 (`os/tests/test_stock_prepare.py`), so they encoded the same wrong assumption. The check exists in three copies: `os/release/pause-stock-updates.sh`, `os/release/pin-stock.sh` and the owner block in `docs/INSTALL.md`.

This is the leading explanation, not a proven one. A unit still active, or a live rpm-ostree transaction left behind by the stopped updater, are still possible. The next run's recorded values must confirm or rule them out.

## Integrator decision

1. **Verify first**, offline or in the probe's existing cached-stock-image step (`--pull=never --network=none`):
   - the pinned **stock** image's `rpm-ostreed.service` `ExecStart`, and that the daemon's process name is `rpm-ostree`
   - which command the pinned `uupd` uses for the OS update: `bootc` running in its own process, or `rpm-ostree` going through the daemon (from the pinned binary or its tagged source)
   - the shape of `rpm-ostree status --json`'s `transaction` field, and what `rpm-ostree cancel` does in the pinned rpm-ostree version

   If any of this contradicts the finding above, stop and report a PLAN-GAP before any full dispatch.
2. **Fix the idle check.** Keep all three copies identical, as they are now.
   - A **client** is a process whose executable is `bootc` or `rpm-ostree` and which is **not** in `rpm-ostreed.service`'s cgroup. Identify it from `/proc` (exe, cmdline, cgroup), not by name alone.
   - The daemon itself is not a client. Its work shows up in `transaction`.
   - "Selected units inactive or failed" and "`transaction` is null" stay required.
   - Never kill or signal a process the script didn't start.
3. **A transaction still active after the updater units are stopped:**
   - Record the full field, then run `rpm-ostree cancel` **once**. Nothing else in the guide runs an OS transaction at that moment, and cancelling never touches the booted deployment.
   - Wait for idle under the same 300-second deadline.
   - A deployment staged before the cancel then goes through pin-stock's existing one-upstream-staged discard.
   - If the transaction is still active at the deadline, stop and name it.
4. **Always export the decision values.** Keep the last value of each predicate, and print it in both the success receipt and the stop message:
   - each selected unit's `ActiveState`/`SubState`
   - the raw `transaction` field
   - every bootc/rpm-ostree process (pid, exe, cmdline, cgroup), and whether it was excluded as the daemon
   - whether a cancel ran, and what it cancelled

   A stop must say which predicate stayed false. Put one plain line for the owner first, details after.
5. **Read the installed keyboard first.** In the first installed stock root shell, read the installed keyboard files (11i item 2) **before** the pause, so a pause stop no longer loses that result. Reading two files can't affect the updater. The check stays strict: a mismatch still stops. The guide's first owner command is still the pause.
6. **Regressions:**
   - A realistic process table with only the daemon running (`rpm-ostree start-daemon` in `/system.slice/rpm-ostreed.service`) must count as idle. This test must fail on the 11i code; show that it does.
   - A `bootc upgrade` process outside the daemon's cgroup must make the script wait, then stop at the deadline naming that process.
   - A transaction that stays active after the units stop must trigger exactly one cancel; then idle passes. If it's still active after the cancel, the script stops and names it.
   - A unit stuck active must stop the script and name the unit.
   - Running the script twice is still harmless, the three copies still match, and the 11g replays still pass.
7. **Budget unchanged:** 750 minutes and 5 full runs on the same ledger. 11i ended at 426/750 and 4/5. That fits one probe (42) and one complete full run (182), plus closing (14): 664. No sixth full run. If the guard can't fit the plan, stop and report; the integrator decides.

## Then

1. Update the stage walk-through before any dispatch. The pause step is now: read the installed keyboard → stop the units → cancel any leftover transaction → wait for idle by the new check.
2. Run a fresh probe on the new commit, including the item 1 checks that couldn't be done offline.
3. Run one complete full run: **Part A** in both orders (the installed keyboard check, pause/cleanup/pin, and every later stage), then **Part B**.

All stop rules hold.

## Acceptance

11c's acceptance, plus an "11j" REPORT section with:
- the item 1 verification results
- the exported decision values at every pause and pin: which predicates held, whether the daemon was seen and excluded, and whether a transaction was cancelled
- the installed keyboard result per order
- everything 11g's and 11i's acceptance lists

Push (fast-forward only). Mark PR #11 ready for review if acceptance is met. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the same Codex session).
