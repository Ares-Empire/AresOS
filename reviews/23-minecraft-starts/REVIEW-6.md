Reviewed `bab298fc`, limited to round 5 and merge `3fd0bc1c`. **No blocking finding under the owner’s bar.** Two nonblocking limits need clearer reporting.

1. **Nit — an unconsumed SIGKILL record is also ignored after reboot.**  
   Where: [start()](/var/home/ares/AresOS-23-review/os/config/usr/libexec/aresos-desktop:1108), [restore_unresolved()](/var/home/ares/AresOS-23-review/os/config/usr/libexec/aresos-desktop:1189).

   Sequence: Java is SIGKILLed → wrapper durably records `-9` → reboot happens before the supervisor counts or latches the exit. Runtime state disappears; without a persisted unresolved launch, startup never reads that record and starts the hub. My in-memory reproduction returned `STARTING`, unlatched, with one launch.

   This is **below the blocking line**: one automatic attempt following reboot, not an unbounded restart loop, overlapping world access, or unreachable recovery. Known limit 2 currently mentions only an uncounted crash. **Fix:** explicitly include unconsumed kill records and the resulting boot attempt; add a regression documenting this accepted behavior.

2. **Nit — a delayed wrapper can consume the automatic retry, and the model deliberately permits this.**  
   Where: [begin()](/var/home/ares/AresOS-23-review/os/config/usr/libexec/aresos-desktop:1231), [check_settled()](/var/home/ares/AresOS-23-review/os/tests/test_aresos_desktop.py:2020).

   Sequence: supervisor consumes an ordinary-crash record → schedules its five-second backoff → wrapper remains delayed while holding the desktop lock → restart reaches `RECOVERY locked` → wrapper releases the lock. No restart remains scheduled. I reproduced that final state.

   This is **below the blocking line**: it costs an explicit `retry`; recovery remains available and no second JVM starts. The model’s crash expectation copies `outcome['restarts']`, so it cannot independently prove eventual restarting. **Fix:** list this limit explicitly and distinguish the model’s safety assertions from restart-liveness coverage.

The ten limits are **substantially honest, but incomplete** without those qualifications. `truth()` now derives quit/crash/kill classification independently of supervisor acceptance. `enabled()` still scripts wrapper progression, as limit 10 acknowledges; the order count is coverage of that model, not exhaustive execution coverage.

The principal fixes look sound: `conclude()` ignores signal ownership; old-session reconciliation clears the unresolved accounting once; `new_session()` handles both startup and later record discovery; the wrapper syncs the record and directory before reporting. Signal forwarding through `send()` also passed a focused check while `child.wait()` was active.

The merge’s four overlapping files retain this package’s changes. I found no additional package regression there.

Verification: scoped `git diff --check` passed; focused in-memory policy/reboot checks and the real-child signal check passed. I read both supplied run summaries; I did not rerun the filesystem-writing suites in this read-only workspace. No files changed.

SAFE