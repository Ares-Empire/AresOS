Reviewed `f13ac8e`. Five findings:

1. **Blocking — USB code executes before its integrity check.**  
   [INSTALL.md:146](C:/Users/pab/AresOS-14-owner-tools/docs/INSTALL.md:146), [at:10](C:/Users/pab/AresOS-14-owner-tools/os/owner-tools/at:10), [owner.py:1050](C:/Users/pab/AresOS-14-owner-tools/os/owner-tools/owner.py:1050).  
   The bootstrap runs the USB’s `at`, which executes the USB’s `owner.py`; only then does `checked_bundle()` run. A modified entry script can perform root writes—including to the Windows SSD—before reporting a hash mismatch. The tamper tests call an already-trusted validator directly, so they miss this.  
   **Fix:** use a trusted bootstrap to check the manifest against the documented fingerprint and validate every payload file **before executing or importing USB code**. Test the actual bootstrap with modified `at` and `owner.py`, requiring zero payload execution.

2. **Blocking — losing the original session makes a layout trial unrecoverable through the tools.**  
   [owner.py:939](C:/Users/pab/AresOS-14-owner-tools/os/owner-tools/owner.py:939), [owner.py:809](C:/Users/pab/AresOS-14-owner-tools/os/owner-tools/owner.py:809).  
   A crash, power loss, or closed original login leaves persistent `layout-pending.json`. Every completion/revert action requires the original boot, and revert additionally requires the original session. A fresh authenticated administrator therefore cannot recover it. Because `/var` is shared, booting retained stock does not clear the problem: `keep-stock` can succeed, but guarded reboot still refuses. With plain US selected, the umlaut password can also become inaccessible.  
   **Fix:** provide an identity-checked recovery path for abandoned trials, including recovery from retained stock without changing stock’s keyboard settings. Test session loss and an actual reboot during a pending trial.

3. **Should-fix — interrupted setup leaves states that its own commands cannot resume.**  
   [owner.py:687](C:/Users/pab/AresOS-14-owner-tools/os/owner-tools/owner.py:687), [owner.py:975](C:/Users/pab/AresOS-14-owner-tools/os/owner-tools/owner.py:975).  
   `prepare` pins stock before saving `prepared.json`. If a subsequent observation or record write fails, the next invocation has no saved record and rejects the now-pinned stock. Likewise, installation creates `/var/lib/ares` before copying and completing the installation; interruption leaves a partial directory that `install` unconditionally refuses.  
   **Fix:** stage installation privately and publish it atomically; journal preparation intent before mutations and resume only an exactly matching interrupted operation. Add failure injection after each mutation and record write.

4. **Should-fix — STOP diagnostics are omitted from the owner’s export path.**  
   [owner.py:1008](C:/Users/pab/AresOS-14-owner-tools/os/owner-tools/owner.py:1008), [media.py:83](C:/Users/pab/AresOS-14-owner-tools/os/owner-tools/media.py:83).  
   Every failure is recorded under `/run/ares-owner-diagnostics`, while `export` copies only `/var/lib/ares/records`. The owner can successfully export records and return to Windows without preserving the failure diagnostics; reboot then destroys them. CI conceals this discrepancy by reading both directories through its separate diagnostic reader.  
   **Fix:** persist STOP diagnostics privately and include them in the checked export route. Test failure → export → reboot, requiring the failure record to survive off-device.

5. **Should-fix — owner-facing qualification status contradicts the final report.**  
   [INSTALL.md:492](C:/Users/pab/AresOS-14-owner-tools/docs/INSTALL.md:492), [EMERGENCY.md:9](C:/Users/pab/AresOS-14-owner-tools/docs/EMERGENCY.md:9).  
   These still say the route stopped before its first tools command and remains unaccepted, with another dispatch awaiting approval. The newest report records successful qualification 20 and acceptance. Package 15 cannot reliably inherit both descriptions.  
   **Fix:** update these status passages to the completed VM scope while retaining **NOT RELEASED** and every outstanding physical gate.

All 12 payload hashes and source copies matched. I found no additional defect in the reviewed token-routing or minute-budget gates. No files changed; native/VM tests were not rerun.

CHANGES-NEEDED