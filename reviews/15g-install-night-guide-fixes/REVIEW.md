I found three **should-fix** navigation/consistency issues and one **nit**. I found no new instruction authorizing writes to Micron or Windows boot files.

1. **Should-fix — the reinstall checkpoint sends the owner back through the live boot again.**  
   [INSTALL-RECORD.md:144](/C:/Users/pab/AresOS-15g-install-night-guide-fixes/docs/INSTALL-RECORD.md:144) says “Return to step 4, box 1” after validating the failed install’s partitions. But the owner reaches this checkpoint from box 2 **after** restarting the reinstall route. Following that return repeats Windows/USB boot and invalidates the same-session mapping just completed.  
   **Fix:** keep the initial return to box 1 in the failure route; after record C passes on the retry, return directly to the installer keyboard/destination boxes in the current live session.

2. **Should-fix — the new Windows serial detour lacks its own return.**  
   [INSTALL-RECORD.md:111](/C:/Users/pab/AresOS-15g-install-night-guide-fixes/docs/INSTALL-RECORD.md:111), reached from step 4 box 1, finishes the Windows reading and immediately continues into Linux identification and installer mapping. There is no return link at that boundary. A phone reader must remember the caller or use Back.  
   **Fix:** give the Windows reading a separate checkpoint and an explicit “PASS → Return to step 4, box 1; continue with the offline live boot” link before the Linux instructions.

3. **Should-fix — the emergency card and reference disagree about an idle live-session shutdown.**  
   [EMERGENCY.md:25](/C:/Users/pab/AresOS-15g-install-night-guide-fixes/docs/EMERGENCY.md:25) permits force-off **only after a successful install/tool command**. [INSTALL-REFERENCE.md:43](/C:/Users/pab/AresOS-15g-install-night-guide-fixes/docs/INSTALL-REFERENCE.md:43) explicitly also permits an idle live session after requesting desktop shutdown. Step 2’s test boot has no successful install/tool command.  
   **Fix:** state the idle-live-session exception identically on both pages, retaining the ten-minute wait, exclusions, Windows return and mandatory Help.

4. **Nit — later layout instructions still assume an umlaut password.**  
   [INSTALL-PROCEDURES.md:9](/C:/Users/pab/AresOS-15g-install-night-guide-fixes/docs/INSTALL-PROCEDURES.md:9) describes the “unchanged umlaut password”; line 41 explains the plain-US negative trial through password untypeability. The new every-install alphabet excludes umlauts.  
   **Fix:** explain that the password remains typeable and the public `yz-/!ü` proof exercises layout differences. Preserve the supervised negative test and recovery protections.

The **ten-minute JUDGMENT-CALL is reasonable on its merits**, with the existing narrow conditions. The pinned [OSTree service](https://raw.githubusercontent.com/ostreedev/ostree/v2026.4/src/boot/ostree-finalize-staged.service) allows five minutes for finalization alone. The retained finalizer supports the documented interrupted-deployment possibilities, and `owner.py` confirms that `PASS check` can describe stock. The guide correctly avoids treating elapsed time or PASS as proof of completed switching.

Other checks were sound:

- Micron reading uses read-only queries. The required unique match, `SerialNumber = A.Disk.Serial`, and matching disk GUID correctly tie the printed serial to A; those comparisons are manual.
- German key positions and allowed password characters match the retained maps. The MOK labels and continuation branch match [shim 16.1](https://raw.githubusercontent.com/rhboot/shim/16.1/MokManager.c).
- Reinstall restrictions retain Crucial-only writes and Micron protection. Status leaves later gates open. No added private serials/GUIDs were apparent.
- All **277 inline local links/anchors** resolved. The problems above concern return instructions.
- Pending rebind remains strict: **244 bound sources, 12 pending, no hash mismatches** in my independent committed-byte check using declared line endings. Historical tables and prohibited implementation paths are unchanged.

I could not run Python, `checkout_sources.records`, the required Python suites, or WSL verification. I did not run gitleaks, Gradle or hardware trials. GitHub PR/check retrieval was blocked by configuration access, so this review covers local `main...HEAD` at `c20510e6`.

CHANGES-NEEDED