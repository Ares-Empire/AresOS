The four original reproductions are addressed, but `ce718024..68395f03` introduces two regressions.

1. **Blocking — RENAME can commit stale message identities and rename a replacement folder.**  
   **Where:** [filing.py:74](/Users/pab/AresOS-19b-state/control/aresos_control/mail/filing.py:74).

   Removing body reads also removed the UIDVALIDITY recheck. `safe_folder()` enumerates through an earlier IMAP session; the subsequent role check verifies folder roles, not UIDVALIDITY.

   **Reproduction run:** Called production `Mail._call('folder_rename', …)` with an in-memory store and IMAP fixture. After `safe_folder()` enumerated Source at UIDVALIDITY 2, the fixture recreated Source at UIDVALIDITY 3, preserving ordinary folder roles.

   ```text
   ce718024: SELECT(3), refused stale folder; no RENAME
   68395f03: RENAME(3), state=done; committed context says UIDVALIDITY 2
   ```

   Injecting ENOSPC into the result write still executed `RENAME(3)` and left the started record describing UIDVALIDITY 2. That violates R2: the retained context identifies different messages from those affected.

   **Fix:** Restore the metadata-only UIDVALIDITY check on the mutation connection before committing context. Keep body fetching and MIME parsing removed. Add the folder-recreation case with successful storage and failed result storage.

2. **Should-fix — the RENAME destination rule now rejects valid filing-check completion.**  
   **Where:** [model.py:605](/Users/pab/AresOS-19b-state/control/owner_state_oracle/model.py:605).

   `result_proof()` requires the destination to exist for both RENAME and message filing. For filing, a complete location scan can legitimately establish that the destination disappeared. Production commits that result with a warning; the destination-presence requirement applies specifically to RENAME recovery.

   **Reproduction run:** Seeded an interrupted MOVE, removed its destination, supplied healthy special roles, and ran production `resolve_checks()` with a complete scan of every remaining mailbox. It committed:

   ```text
   state=partial; check_open=False
   scan_complete=True; unacknowledged notice=True
   ```

   The oracle nevertheless reported `unjustified-check-close` and `unsupported-resolution`, retaining three recovery facts. Thus valid warning-bearing completion fails the required equality comparison.

   **Fix:** Make the destination-presence gate specific to RENAME. For filing, accept the correlated complete scan and committed warning even when the destination is absent. Add this positive case alongside the absent-destination RENAME negative case.

Verification: **60 selected plain-Python tests passed**—24 new fix tests and the prior review’s 36 selected tests. Both regressions above were reproduced in memory. The compact ledger is **928,878 bytes**, with all 2,024 groups assigned to stage 3; `local_flag` is included. No files were edited or containers run. The full filesystem fault sweep was not rerun.

CHANGES-NEEDED