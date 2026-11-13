Reviewed `8420eba2` against `180b598c`. Three findings remain.

1. **Blocking — a kill can still be mislabeled as wrapper-stopped and restart.**  
   Where: [aresos-desktop-java:246](/C:/Users/pab/AresOS-23-minecraft-starts/os/config/usr/libexec/aresos-desktop-java:246), [aresos-desktop:1386](/C:/Users/pab/AresOS-23-minecraft-starts/os/config/usr/libexec/aresos-desktop:1386).

   After the lost answer, the wrapper checks `child.poll()`, calls `stop(child)`, then unconditionally reports `stopped=True`. If Java receives SIGKILL between that first check and `stop()`’s own check, `stop()` finds Java dead and sends nothing. Nevertheless, both the record and socket report say the wrapper stopped it. The supervisor prefers `stopped_reason` over `status=-9`, counts a failure and automatically restarts. An exit with status zero in the same gap is also misclassified.

   **Fix:** derive `stopped` from the actual stop outcome, preserving Java’s status when it ended before the wrapper intervened. Add a deterministic regression that kills/reaps Java between those checks; require `RECOVERY/killed`, zero failures and no restart.

2. **Should-fix — late-report reconciliation disappears after a supervisor restart.**  
   Where: [aresos-desktop:1393](/C:/Users/pab/AresOS-23-minecraft-starts/os/config/usr/libexec/aresos-desktop:1393), [aresos-desktop:1454](/C:/Users/pab/AresOS-23-minecraft-starts/os/config/usr/libexec/aresos-desktop:1454).

   `launch.unexplained` exists only in memory. The unexplained-end path persists `accounted=launch.id`, the kill latch and `failed=True`. If the supervisor restarts before the wrapper’s explanation arrives, `account_for()` skips that already-accounted launch, leaving `self.launch=None`. The matching late report is then discarded, and its exit record is never reconciled. An explained failed start remains persistently latched, including across reboot, until the owner intervenes.

   **Fix:** persist the unresolved classification and restore enough launch identity to reconcile a matching report or exit record exactly once. Test supervisor restart between the unexplained latch and the explanation; retain the latch for a real kill.

3. **Should-fix — the 30-second deadline can truncate the new 20-second wait.**  
   Where: [aresos-desktop:1568](/C:/Users/pab/AresOS-23-minecraft-starts/os/config/usr/libexec/aresos-desktop:1568).

   `pending()` schedules both `authorized + 30` and `wrapper_gone + 20`; the earlier wins. Thus a connection lost 25 seconds after authorization gets only five seconds for stopping and reporting. Delayed authorization delivery, scope creation and handoff response can consume that time without exceeding each individual timeout. The supervisor can latch while Java is still within its permitted stop window. Late reconciliation may repair this in the same process, but finding 2 makes the false latch persistent across a supervisor restart.

   **Fix:** coordinate the deadlines so an observed lost handoff receives its full bounded stop/report window. Test connection loss late in the authorization window, rather than only immediately after startup.

The pressure-gap reset is correct. The new wire fields agree, and the ordinary late-report path prevents duplicate accounting. The supplied revert log records the expected failures for all three original findings; it does not include revert results for the added wrapper tests. Finding 1’s exit-record subcase still passes under reversion, as the report acknowledges.

`git diff --check` passed; no files were modified. Independent Python execution was unavailable: WSL returned `E_ACCESSDENIED`, and Windows reported no installed Python runtime.

CHANGES-NEEDED