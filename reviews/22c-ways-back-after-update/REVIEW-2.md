At `e44a797c`, I found **two should-fix issues, no blocking findings** within the requested fix diff.

1. **Should-fix — snapshot refusal leaves the journal blocking recovery.**  
   Location: [owner.py:1560](/var/home/ares/AresOS-22c-review/os/owner-tools/owner.py:1560).

   Concrete sequence:
   - `rollback` journals `[R27*, R13, S] → [S, R27*, R13]`.
   - An outside writer changes the list to `[R13, R27*, S]` before the script reads it.
   - The new snapshot assertion correctly refuses without executing any mutation.
   - The caller leaves `outcome-pending` at `intent`.

   I reproduced `title`, `previous`, `rollback` and `reboot` refusing on **all three boot choices**, because the list matches neither the journal’s original nor intended order. The new [regression test](/var/home/ares/AresOS-22c-review/os/tests/test_ways_back.py:347) explicitly expects that open intent instead of checking subsequent recovery.

   **Why it matters:** the unwanted reorder is fixed, but the recovery dead end remains. This is the observable pre-call drift case, not the accepted final-read/call race.

   **Fix:** durably distinguish a definite pre-mutation refusal and close/archive its intent so subsequent commands can survey the actual list. Do not discard journals on arbitrary script failures, which may follow a mutation. Extend the regression through recovery and restart.

2. **Should-fix — retrying `finish` can invalidate the saved restoration intent.**  
   Locations: [restoration acceptance](/var/home/ares/AresOS-22c-review/os/owner-tools/owner.py:2015), [finish persistence](/var/home/ares/AresOS-22c-review/os/owner-tools/owner.py:2128).

   I reproduced this sequence, keeping the original administrator login open:
   - Begin and prove German → US.
   - Interrupt `finish` after its console write: **US console / German X11**.
   - From a fresh second login, run `abandon`. It records that pair as `restoring`.
   - Interrupt abandon after its console write: both settings are now German, but the trial remains.
   - Return to the original login. `finish` accepts the old settings and existing proof. Interrupt it after both persistent writes: both settings are now US.
   - Restart and run `abandon`.

   Abandon refuses with `Finished system layout changed during the abandoned trial`: its saved restoration intent authorizes the earlier forward partial pair and German settings, **not the US pair that the subsequent finish actually wrote**. Transferring the trial to a repair note on stock preserves the same refusal.

   **Why it matters:** interrupted commands can strand restoration using only tool-generated settings. Stock remains available, but the affected deployment cannot complete its repair and stage an update.

   **Fix:** make restoration an exclusive phase: once `restoring` exists, refuse renewed finish and direct the owner to complete abandon. Add this regression, including returning to the still-open original session. The model currently makes “fresh session” prevent finish; it does not model returning to that original session.

The remaining checks were favorable:

- The first review’s exact restoration sequence now succeeds. The model really cuts abandon before persistence, between console/X11 writes, and after both writes.
- Restoration validates the recorded starting pair and accepts only that pair, its console-first restoration intermediate, and the old settings. I found no arbitrary mixed-layout acceptance.
- Transfer saves the repair note before clearing the trial and replaces it by deployment identity while preserving restoration authority. The interrupted-transfer regression passes; I found no additional loss or duplication issue.
- `start-next.sh` receives and compares the complete caller snapshot before `set-default`, retains target validation, and preserves both `sync` and the postcondition.
- Login, verify, switch and prepare now survey installed state before their operational checks. The survey bypasses prepared stock and the first staged switch, preserving their existing behavior. I found no additional healthy-state refusal.
- Other tool changes are limited to these fixes, their payload copies and checksums. Source/payload equality and manifest hashes pass.

Verification used an **in-memory filesystem adapter**, with no repository writes: **44 focused tests plus 18 model tests passed** (`62 tests in 11.658s; OK`). This executed the snapshot, installed-survey and restoration revert proofs. An additional **48 before/after restoration cut cases passed**, covering saves, both persistent writes, runtime restoration, record removal and directory-sync boundaries.

I did not rerun exhaustive model exploration or test real power-loss durability. No `test_owner_update` tests, owner commands or real deployment binaries ran. The pre-existing untracked review file was untouched.

CHANGES-NEEDED