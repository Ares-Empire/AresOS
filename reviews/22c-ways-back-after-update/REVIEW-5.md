Reviewed PR #46 at `2312fa99`, limited to `git diff 1b85d2f9..HEAD`. Two findings remain.

1. **Blocking — the forward-again gate can still admit staging.** [INSTALL.md:323](/var/home/ares/AresOS-22c-review/docs/INSTALL.md:323)

   **Case:** R28 tools are installed, but only R27, R13 and stock remain after an unsuccessful update. Return from default stock using `update`, restart and check: this confirms the return to installed R27. Later use `previous` to return to R13. The forward-again box now accepts the completed update-route confirmation, although R28 remains uninstalled. Its first `update` stages R28; shutdown would remove R27—the intended forward destination.

   **Why:** a confirmation also follows an installed-system reorder. It does not prove the current tools’ release was installed. The new test substitutes `state.bundle in releases` for the guide’s actual completion condition, so it misses this sequence.

   **Fix:** bind the gate to confirmation of the **current tools’ exact release**, with an equally explicit condition for tools-only updates. Alternatively, document a boot-menu route that guarantees selection without staging. Add the connected stock-return → previous → forward-again regression.

2. **Should-fix — entering the card after another check loses its routing evidence.** [EMERGENCY.md:20](/var/home/ares/AresOS-22c-review/docs/EMERGENCY.md:20), [INSTALL.md:308](/var/home/ares/AresOS-22c-review/docs/INSTALL.md:308)

   **Case:** R28 finalization fails, leaving `[R27,R13,stock]`; the predicted recovery row boots R13. Run the check instructed by the recovery-menu procedure or update check box, then follow its link to the card. That first check reports the unapplied update and archives its journal. The card requires another check, which no longer reports that outcome. None of its outcome branches now supplies the intended return to R27.

   **Why:** the unapplied-update message is emitted once by [owner.py:1270](/var/home/ares/AresOS-22c-review/os/owner-tools/owner.py:1270). The new trace starts directly at the card and misses this linked entry.

   **Fix:** explicitly reuse the check result just obtained when entering from those guides; require a fresh check only otherwise. Test this entry sequence and give unmatched results an explicit Help destination.

The requested isolated replays otherwise check out: the failed-update card avoids R13 when entered before the first check; returning from stock stops at the installed release; no-op returns and no-op rollback complete without requiring a confirmation; and direct rehearsal dispatches with changed model sources stop without same-head full-model qualification. The forward-again fix handles the immediate unfinished-update case, but not finding 1’s connected sequence.

**The judgment call is right.** When the attempted update is verified in place but has not started, `previous` safely selects its retained predecessor. Finalization leaves the new release, that predecessor and stock; the earlier predecessor is gone. Within that verified state, `previous` cannot go one release too far back, including when stock is running.

Verification: five selected tests passed; independent pure-ledger traces reproduced both findings and the recovery cases; four mocked direct-dispatch cases passed. One additional test was blocked during temporary-directory setup by the read-only filesystem, before owner dispatch. All 255 host-walk and 35 pending-rebind hashes matched. No files changed and no prohibited commands ran.

CHANGES-NEEDED