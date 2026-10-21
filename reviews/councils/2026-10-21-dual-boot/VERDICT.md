**The guide is not ready for the owner to follow, even after the image handoff exists.** Eight member findings merge into seven distinct gaps: four BLOCKING and three NON-BLOCKING. Reviewed commit `4de9644`; no files changed and no installation trials performed.

1. **BLOCKING — Undo can delete Windows’ active boot files despite passing its preliminary checks.**  
   Where: [INSTALL §9](/C:/Users/pab/AresOS-05-dual-boot/docs/INSTALL.md:174), [OS-BASE Appendix C.9](/C:/Users/pab/AresOS-05-dual-boot/docs/design/OS-BASE.md:319).

   **Scenario and impact:** A later Windows reinstall uses the AresOS EFI system partition (ESP). F12 → Windows Boot Manager still starts Windows directly, and the Linux partition identifiers and boundaries remain unchanged. Undo therefore permits deleting the ESP containing Windows’ boot files. Bazzite documents Windows’ potential use of its ESP; UEFI distinguishes a boot entry’s displayed name from its device/file target. [Bazzite](https://docs.bazzite.gg/General/Installation_Guide/install-guide/#dual-booting-windows), [UEFI specification](https://uefi.org/specs/UEFI/2.9_A/03_Boot_Manager.html#load-options).

   **Fix:** Before deletion, map the Windows entry actually tested to the **original Windows ESP’s partition GUID and Microsoft loader path**. Stop if it targets AresOS storage or cannot be established.
   **Check:** In a file-backed VM, Windows booting directly from the Linux ESP must fail the deletion gate; Windows using its original ESP must pass.

2. **BLOCKING — The required partition-identification checks cannot be completed using the supplied instructions.**  
   Where: [INSTALL §4](/C:/Users/pab/AresOS-05-dual-boot/docs/INSTALL.md:76), §5.4 and §9.2–4.

   **Scenario and impact:** The owner skips the apparently optional PowerShell inventory and saves only Disk Management screenshots. Those cannot show the MSR. During undo, GParted’s displayed `UUID` is a filesystem identifier, not the requested GPT partition GUID. A careful reader must stop; guessing defeats the deletion safeguard. [Microsoft](https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/windows-and-gpt-faq?view=windows-11), [GParted source](https://raw.githubusercontent.com/GNOME/gparted/master/src/Dialog_Partition_Info.cc).

   **Fix:** Make the inventory mandatory. Supply read-only Windows/Linux instructions and one comparison sheet covering disk identity, `Guid` ↔ `PARTUUID`, device paths and boundaries. Calculate sector endpoints rather than requiring novice arithmetic; explain the missing MSR display.
   **Check:** With two ESPs and another unused gap in a disposable VM, a novice must identify the permitted interval and all deletion targets without assistance.

   This merges safety finding 2 with followability finding 1. **BLOCKING** is justified by the unusable safety check, even though obeying the stop rule prevents immediate damage.

3. **BLOCKING — Recovery media can be overwritten while the owner apparently completes every preparation step.**  
   Where: [INSTALL §1.2](/C:/Users/pab/AresOS-05-dual-boot/docs/INSTALL.md:16) and §3.

   **Scenario and impact:** The owner prepares Windows recovery media on their only USB stick, then writes Bazzite onto it. If Windows becomes unbootable, this sole laptop cannot recreate its recovery USB.

   **Fix:** Specify a preserved, labelled Windows recovery USB and a separate expendable installer USB. Provide a concrete German recovery-media procedure and distinguish it from personal-file backup, which recovery media excludes. [Microsoft recovery-drive instructions](https://support.microsoft.com/de-de/windows/experience/backup-recovery/recovery-drive).
   **Check:** Before shrinking, boot the preserved recovery USB to its initial screen and exit without restoring; confirm the Bazzite writer targets the other stick.

4. **BLOCKING — The partition-creation sequence gives the wrong selection for Btrfs subvolumes.**  
   Where: [INSTALL §5.5](/C:/Users/pab/AresOS-05-dual-boot/docs/INSTALL.md:106).

   **Scenario and impact:** After allocating the remaining gap to Btrfs, the instruction still says to select remaining free space for each creation. None remains for `root`, `var` and `home`; the novice must stop or improvise.

   **Fix:** Separate creation of the three partitions from creation of subvolumes inside the new Btrfs parent. Show the qualified installer’s resulting tree, mount points and pending operations. Specify English installer labels with a German keyboard, or provide complete German labels. Bazzite’s reference distinguishes the parent partition from its subvolumes. [Bazzite manual partitioning](https://docs.bazzite.gg/General/Installation_Guide/manual_partitioning/).
   **Check:** An unaided novice walkthrough must produce exactly three new partitions, the required subvolumes and unchanged Windows partitions.

5. **NON-BLOCKING — GParted USB preparation exposes an avoidable manual boot-code route.**  
   Where: [INSTALL §9.3](/C:/Users/pab/AresOS-05-dual-boot/docs/INSTALL.md:176).

   **Scenario and impact:** The owner selects the linked ZIP method, extracts it into Downloads and runs `makeboot.bat` there. Upstream explicitly warns that running it from the internal drive can prevent Windows booting. [GParted USB instructions](https://gparted.org/liveusb.php).

   **Fix:** Prescribe one rehearsed ISO-writing method, with checksum, USB identity and expected boot screen; exclude the manual batch-file route.
   **Check:** Rehearse that exact route on expendable media and confirm UEFI boot.
   
   This is a concrete operator-error risk, but **not a demonstrated failure when following upstream instructions**, which explicitly forbid the dangerous action.

6. **NON-BLOCKING — Restoring Windows as the default lacks actionable firmware navigation.**  
   Where: [INSTALL §8](/C:/Users/pab/AresOS-05-dual-boot/docs/INSTALL.md:168).

   **Scenario and impact:** The owner selects Windows through F12 and believes the default is restored; the next unattended restart enters Linux. Lenovo documents one-time selection and persistent boot order separately. [Lenovo instructions](https://download.lenovo.com/pccbbs/pubs/loq_15_16/html_en/EN/select_boot_devices.html).

   **Fix:** Add the model’s setup-entry procedure, Boot → UEFI navigation, Windows Boot Manager selection and save/exit action, matching the actual firmware.
   **Check:** With USB removed and no keys pressed, Windows must start normally after installation and after undo.

7. **NON-BLOCKING — The mandatory Fast Startup GUI step duplicates the command path and can dead-end.**  
   Where: [INSTALL §2](/C:/Users/pab/AresOS-05-dual-boot/docs/INSTALL.md:43).

   **Scenario and impact:** Hibernation is already disabled, so the owner cannot find the required checkbox and wastes time investigating a safe state.

   **Fix:** Use one primary path: save work, disable hibernation, verify available sleep states, then restart. Explain silent success and the absent checkbox; make the GUI route optional. Fast Startup uses hibernation. [Microsoft Fast Startup](https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/distinguishing-fast-startup-from-wake-from-hibernation), [Powercfg](https://learn.microsoft.com/en-us/windows-hardware/design/device-experiences/powercfg-command-line-options).
   **Check:** Walk through both initially enabled and already-disabled states on German Windows.

**Safety:** Undo is not yet safe: successful direct Windows boot does not prove its boot files will survive deletion. Existing stop conditions also need an executable identity check and confirmation that recovery media remains available.

**Followability:** The main failure points are partition identification and Btrfs creation. Risky steps contain useful acceptance conditions, but several lack the screens, fields or selection sequence needed to apply them.

**Proportionality and minimal safe version:** Keep the released-image gate, verified independent backup, preserved Windows recovery USB, encryption/hibernation checks, mandatory partition record, exact permitted interval, separate AresOS ESP and pending-operation review. Provide one qualified ISO and installer walkthrough, the tested rebase/rollback recipe, Windows-return checks, and undo that verifies both partition identity and Windows’ current boot target. Simplify the duplicate power-settings walkthrough, USB-method choices and manual arithmetic. Move maintainer research outside the owner’s action sequence. The already-explicit missing image handoff remains a prerequisite, not an additional council finding.

GAPS-FOUND (7)