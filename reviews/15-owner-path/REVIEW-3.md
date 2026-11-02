Reviewed **e074f6e** against **79a67d2**. Two recovery-path defects remain.

1. **Should-fix — the interrupted-layout card leads to a second `layout abandon`.**  
   [EMERGENCY.md:31](C:/Users/pab/AresOS-15-owner-path/docs/EMERGENCY.md:31) runs abandon and requires PASS, then links “Finish abandoned-trial recovery” to [INSTALL-PROCEDURES.md:82](C:/Users/pab/AresOS-15-owner-path/docs/INSTALL-PROCEDURES.md:82), which instructs another fresh login and abandon invocation. The first success deletes `layout-pending.json`; following the linked procedure literally therefore STOPs with **`Missing private layout-pending record`**.

   **Fix:** add a completion anchor after the abandon command/results and link the card directly there, or let the card delegate execution entirely to the procedure. Test the complete card-to-procedure sequence, including the already-cleared pending state.

2. **Should-fix — restart recovery assumes the old layout even after an interrupted finish persisted the new one.**  
   [EMERGENCY.md:31](C:/Users/pab/AresOS-15-owner-path/docs/EMERGENCY.md:31) and [INSTALL-PROCEDURES.md:84](C:/Users/pab/AresOS-15-owner-path/docs/INSTALL-PROCEDURES.md:84) prescribe the last confirmed layout without distinguishing an interrupted `layout finish`. Finish persists the console map before the X11 setting and completion record. A crash in that interval can reboot into the new console map despite no `PASS layout finish`. The tool explicitly supports recovering this state; [test_owner_abandon.py:82](C:/Users/pab/AresOS-15-owner-path/os/tests/test_owner_abandon.py:82) covers both partial and completed persistence before failure.

   **Fix:** distinguish interrupted begin/revert from interrupted finish. Explain that after finish was invoked, the console may already use the proven new map; give a bounded login/recovery route using the recorded old/new profiles, with Help for uncertainty. Cover that branch in the owner-path tests instead of requiring the old-layout wording unconditionally.

The council delta RECHECK’s November conditions are **partly, but not completely, satisfied**:

- **Met:** native query compatibility, partition ancestry/EFI identity, unchanged protected fixture and cleanup. Retained qualification-21 acceptance records 20 loop checks, zero helper mutations and confirmed cleanup.
- **Met:** installed-VM trusted bootstrap/private-copy installation and subsequent helper use with the removable tools medium. Qualification 21 also establishes the reported preparation, layout/reset/abandon, rollback and protected-disk audit scope.
- **Still open:** the actual-runtime negative case with a **protected child mounted**, requiring refusal with zero mutations. The native loop fixture leaves the protected disk unmounted; the VM walk does not exercise that case. Its evidence remains synthetic in `test_owner_devices.py`. Keep this original RECHECK condition explicitly pending; package 14’s workflow acceptance can remain accurately described as met.

The current qualification and diagnostics status rows otherwise preserve the relevant limits: protected-second VM scope, no transferred manual-GRUB qualification, and no claim that qualification 21 tested the exact STOP → export → reboot diagnostic sequence. Physical installation remains **NOT RELEASED**.

Fresh read-only checks confirmed the literal 13-line bootstrap equals `commands.json`, all 12 payload hashes and source copies match, and all 48 quoted CLI PASS expectations match dispatcher formatting. Tools, harness, Windows helpers and mod match main. No Windows-SSD write path was introduced by this diff.

No files changed. Python tests could not run: `py -0p` found no installed Python, and WSL returned `E_ACCESSDENIED`.

CHANGES-NEEDED