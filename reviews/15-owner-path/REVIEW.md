Reviewed `562e29c` using `git diff 5156f5f...HEAD`.

1. **Blocking — the battery action assumes power is already disconnected.** [EMERGENCY.md:43](C:/Users/pab/AresOS-15-owner-path/docs/EMERGENCY.md:43)  
   “Keep AC disconnected” covers disassembly, but not an owner noticing swelling, heat or smell while the laptop is running and charging. “Stop before touching connectors” also fails to distinguish external AC from internal battery work.  
   **Fix:** lead with stopping use and safely disconnecting external power, then distinguish the already-open/disconnected case. Preserve the prohibition on handling the battery and require service clearance. This follows [Lenovo’s immediate-action guidance](https://download.lenovo.com/pccbbs/pubs/t490/html_en/en/Conditions_that_require_immediate_action.html).

2. **Blocking — step 7 substitutes a real, unguarded command for the reviewed reboot.** [INSTALL.md:165](C:/Users/pab/AresOS-15-owner-path/docs/INSTALL.md:165)  
   “Guarded `reboot`” invites typing `reboot`, which bypasses the helper’s attached-stick, stale-title and unfinished-layout checks. Package 14 spelled out `sudo /var/lib/ares/at reboot` here. The equality test checks Bash fences, so this inline regression escapes it.  
   **Fix:** restore the complete canonical command and expected result. Extend command checks to actionable inline invocations.

3. **Should-fix — the everyday boot path loses explicit anomaly STOP conditions.** [INSTALL.md:179](C:/Users/pab/AresOS-15-owner-path/docs/INSTALL.md:179)  
   Old §8 explicitly stopped for changed Secure Boot, Windows recovery prompts, and missing internal boot entries while their SSD remained attached. The replacement supplies order-restoration instructions without retaining those owner-facing conditions. They should not require discovering the design specification.  
   **Fix:** restore these conditions beside the boot-order procedure, with STOP → Help and a named return destination.

4. **Should-fix — some returns discard the caller’s operating-system context.** [INSTALL-RECORD.md:68](C:/Users/pab/AresOS-15-owner-path/docs/INSTALL-RECORD.md:68), [EMERGENCY.md:27](C:/Users/pab/AresOS-15-owner-path/docs/EMERGENCY.md:27)  
   Keep-stock calls record B, but B offers no return to keep-stock or step 8; choosing `after-aresos` sends the owner to step 7, which expects AresOS despite stock being selected. Likewise, successful layout recovery on AresOS is followed by a card instruction to return to step 5, which expects corrected stock. These produce contradictory checks and another STOP after successful recovery.  
   **Fix:** preserve the calling procedure as well as the record stage. Return layout recovery through proof/finish/completion, then step 8. Add tests for these state-dependent returns; link reachability alone cannot catch them.

5. **Should-fix — the status table blurs historical release boundaries.** [INSTALL-STATUS.md:10](C:/Users/pab/AresOS-15-owner-path/docs/INSTALL-STATUS.md:10)  
   The row places the current `9b19b7…` release beside 06c/06e qualification claims, although those runs tested `362af9…b6c402`. The 11n recovery/promotion row also lacks an explicit historical-release limit. This can make earlier second-default-boot/menu evidence appear to qualify the current image.  
   **Fix:** label each historical result with its tested release, and distinguish the current release’s 13f evidence and limits. Preserve the existing drive-order and physical-test qualifications.

Static checks found all canonical commands present and no noncanonical Bash-fence lines; `git diff --check` passed. I could not rerun the Python tests: Python was unavailable on PATH and WSL returned access denied.

CHANGES-NEEDED