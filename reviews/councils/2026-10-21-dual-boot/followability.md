Reviewed commit `4de9644`. No files changed or installation trials performed. These gaps remain even after the planned image handoff exists.

1. **Blocking — The partition-identification checks cannot be completed from the screens and instructions provided.**  
   Where: [INSTALL.md:76](C:/Users/pab/AresOS-05-dual-boot/docs/INSTALL.md:76), steps 5.4 and 9.2–9.4.

   **Scenario:** The owner saves the requested Disk Management screenshot and skips the apparently optional PowerShell inventory. The screenshot cannot include the MSR partition: Microsoft says it is visible only through command-line tools. Later, undo requires matching partition GUIDs using GParted’s Information dialog, whose **UUID** is a filesystem identifier, not the GPT partition GUID. [Microsoft](https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/windows-and-gpt-faq?view=windows-11), [GParted source](https://raw.githubusercontent.com/GNOME/gparted/master/src/Dialog_Partition_Info.cc).

   **Impact:** A careful novice gets stuck; someone proceeding by size or position risks selecting the wrong partition, particularly the Windows EFI.

   **Fix:** Make the inventory mandatory and provide one compact comparison sheet: disk identity, Windows-to-Linux partition mapping, GPT `PARTUUID`, and matching boundaries. Supply a read-only way to obtain those fields in each environment. Calculate the permitted interval and inclusive sector endpoints for the owner instead of requiring manual conversion. Explain that the MSR’s absence from Disk Management is normal.

   **Check:** In a disposable VM containing two EFI partitions and another unused gap, a novice must identify the permitted gap and all three deletion targets using only the guide.

2. **Blocking — “Select the remaining free space for each creation” is wrong for the Btrfs subvolume steps.**  
   Where: [INSTALL.md:106](C:/Users/pab/AresOS-05-dual-boot/docs/INSTALL.md:106).

   **Scenario:** The owner creates EFI, boot and a Btrfs partition using the remaining space. The next instruction still tells them to select remaining free space, but none remains for creating `root`, `var` and `home`.

   **Impact:** They cannot finish the documented sequence without understanding Btrfs or improvising partition changes. The explanatory sentence about shared space does not identify the required selection.

   **Fix:** Split this into two explicit sequences: create the three partitions; then select the new Btrfs parent and create its three subvolumes. Show the expected resulting tree, mount points and pending-operation summary from the qualified ISO. Specify **English installer interface with German keyboard**, rather than making English optional while supplying only English installer labels. [Bazzite’s partitioning reference](https://docs.bazzite.gg/General/Installation_Guide/manual_partitioning/).

   **Check:** Have someone unfamiliar with Btrfs follow the sequence in a VM without verbal assistance. Confirm exactly three new partitions, the required subvolumes and untouched Windows partitions.

3. **Should-fix — Undo delegates USB preparation to a page containing materially different, potentially dangerous methods.**  
   Where: [INSTALL.md:176](C:/Users/pab/AresOS-05-dual-boot/docs/INSTALL.md:176).

   **Scenario:** To avoid installing another writer, the owner chooses the linked manual ZIP method, extracts it into Downloads and runs `makeboot.bat` there. The upstream instructions explicitly warn that running it from the local hard drive can leave Windows unbootable. [GParted USB instructions](https://gparted.org/liveusb.php).

   **Impact:** Preparing the undo tool introduces an avoidable Windows boot risk before any Linux partition is deleted.

   **Fix:** Prescribe one tested ISO-writing route, preferably reusing the already installed writer if qualified. Give the exact image selection, checksum check, USB selection and expected boot screen. Exclude the ZIP/manual batch-file route.

   **Check:** Rehearse that exact procedure with disposable media; confirm it reaches GParted in UEFI mode and requires no internal-drive operations.

4. **Should-fix — “Prepare Windows recovery media” lacks a usable procedure and a clear USB allocation plan.**  
   Where: [INSTALL.md:16](C:/Users/pab/AresOS-05-dual-boot/docs/INSTALL.md:16), section 3.

   **Scenario:** The owner has the advertised single 16 GB stick, prepares Windows recovery media on it, then overwrites it with Bazzite. They completed both instructions sequentially but no longer have Windows recovery media.

   **Impact:** If Windows subsequently cannot boot, the only laptop cannot recreate its own recovery USB.

   **Fix:** State which media must remain available and which may be overwritten. Link one concrete German Windows recovery procedure, distinguish recovery media from personal-file backup, and label the sticks by purpose. Microsoft provides a `recoverydrive.exe` route and explicitly notes that personal files are excluded. [Microsoft recovery-drive instructions](https://support.microsoft.com/de-de/windows/experience/backup-recovery/recovery-drive).

   **Check:** Before shrinking, verify the preserved Windows recovery USB boots to its initial recovery screen, then exit without restoring anything. Confirm the Bazzite writer targets a different expendable stick.

5. **Should-fix — Restoring Windows as the default is an instruction without the necessary firmware navigation.**  
   Where: [INSTALL.md:168](C:/Users/pab/AresOS-05-dual-boot/docs/INSTALL.md:168), step 9.1.

   **Scenario:** After installation changes startup order, the owner selects Windows through F12 and assumes that selection restores the default. The next unattended restart starts Linux again.

   **Impact:** The Windows-first requirement remains unmet, and the owner may enter unfamiliar firmware menus while trying to fix it.

   **Fix:** Clearly distinguish one-time F12 selection from persistent startup order. Add the LOQ setup-entry procedure and the **Boot → UEFI** navigation, with the expected Windows Boot Manager entry and save/exit action. Match the actual firmware language rather than guessing German translations. Lenovo documents these as separate operations. [Lenovo LOQ boot instructions](https://download.lenovo.com/pccbbs/pubs/loq_15_16/html_en/EN/select_boot_devices.html).

   **Check:** With USB removed and no keys pressed, a normal restart must enter Windows. Repeat after undo.

6. **Should-fix — The mandatory Fast Startup GUI walkthrough duplicates the command sequence and creates an unnecessary dead end.**  
   Where: [INSTALL.md:43](C:/Users/pab/AresOS-05-dual-boot/docs/INSTALL.md:43).

   **Scenario:** Hibernation is already disabled, so the owner cannot find the required Schnellstart checkbox. The explanation that it can disappear comes only after the command step.

   **Impact:** They waste time investigating an already-safe state or start skipping prerequisite checks because the guide does not match their screen.

   **Fix:** Use one minimal path: save work, run `powercfg /hibernate off`, verify with `powercfg /a`, then restart. Include representative German success output and explain that successful disabling may print nothing. Make the Control Panel route optional. This preserves the safety requirement: Fast Startup depends on hibernation. [Powercfg documentation](https://learn.microsoft.com/en-us/windows-hardware/design/device-experiences/powercfg-command-line-options), [Fast Startup documentation](https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/distinguishing-fast-startup-from-wake-from-hibernation).

   **Check:** Walk through both initial states—hibernation enabled and already disabled—on German Windows. Both should reach the same verified result without searching for a missing checkbox.