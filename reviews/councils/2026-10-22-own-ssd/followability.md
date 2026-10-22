Reviewed `46c68e4`. No files changed or hardware operations performed. The existing release gates remain necessary; the findings below concern the instructions themselves.

1. **Should-fix before physical release — SSD fitting lacks a clear seating and tightening checkpoint.**  
   Where: [INSTALL.md:62](/C:/Users/pab/AresOS-10-own-ssd-install/docs/INSTALL.md:62).

   **Scenario:** A first-time installer interprets “align/seat…lower…secure” as inserting the SSD flat, or uses the screw to pull a partly inserted SSD into position. “Check seating” does not explain what correct seating looks like.

   **Impact:** Damaged connector, bent SSD or stripped fixing. The later stop condition for bending comes after the instruction to secure it.

   **Fix:** Add a short insertion sequence and close-up: identify the connector and 2280 support; insert at the appropriate angle; check full engagement and fixing-notch alignment before lowering; tighten only until secure, never use the screw to force alignment. Crucial’s own instructions specify approximately 30° insertion and warn against forcing or overtightening. Have Lenovo/service support confirm the model-specific illustration. [Crucial installation guide, step 7](https://content.crucial.com/content/dam/crucial/ssd-products/ssd-family/documents/installation-guides/nvme-pcie-m-2-install/crucial-nvme-pcie-m2-ssd-install-guide.pdf).

   **Check:** On expendable hardware, a novice must distinguish correctly seated, partly inserted and incorrectly supported examples before touching the screw.

2. **Should-fix before owner release — The mandatory Linux check asks the reader to identify relationships that its output does not show clearly.**  
   Where: [INSTALL-RECORD.md:63](/C:/Users/pab/AresOS-10-own-ssd-install/docs/INSTALL-RECORD.md:63), [INSTALL.md:73](/C:/Users/pab/AresOS-10-own-ssd-install/docs/INSTALL.md:73).

   **Scenario:** The owner sees long `NAME="..." TYPE="..."` lines, then must establish “no partition children,” compare every Windows partition and translate the result into the installer’s destination. The command uses `--pairs`, which disables the normal tree, and includes no explicit parent-device column. The comparison sheet also lacks a current Linux device-path field. [util-linux source](https://github.com/util-linux/util-linux/blob/master/lsblk-cmd/lsblk.c).

   **Impact:** A careful novice stops; an impatient one falls back to the two almost-identical capacities. The final erase check then depends on an uncertain mapping.

   **Fix:** Keep complete machine-readable records, but add a compact human-readable disk tree and a same-session mapping: **model + serial → whole-disk path → installer destination**. Show an annotated example distinguishing a disk from its partitions. Automate the detailed GUID/boundary comparison instead of making the owner repeatedly transcribe and reconcile it.

   **Check:** With near-equal drives and reversed enumeration, an unaided novice must select Crucial, reject a Crucial containing an unexpected partition, and identify a proposed Micron EFI write.

3. **Should-fix — “Simplest” undo unnecessarily means opening the laptop again.**  
   Where: [INSTALL.md:106](/C:/Users/pab/AresOS-10-own-ssd-install/docs/INSTALL.md:106).

   **Scenario:** The trial disappoints and the owner just wants normal Windows startup. The guide offers physical removal or destructive erasure, so they reopen the case despite having no need to reclaim the SSD.

   **Impact:** Avoidable handling of clips, screws and the battery connector—or an unnecessary disk-erasure session.

   **Fix:** Put **“Stop using AresOS; leave Crucial installed”** first: verify direct Windows boot and its original boot target, restore Windows as default, verify an unattended restart, then stop. Clearly say this retains Linux and its data. Keep erasure and removal as optional procedures for reuse or physical removal.

   **Check:** A novice can return to Windows-only everyday use without opening the case, preparing GParted or changing either disk’s layout.

4. **Should-fix — German keyboard setup happens after the first Linux command session.**  
   Where: [INSTALL.md:73](/C:/Users/pab/AresOS-10-own-ssd-install/docs/INSTALL.md:73).

   **Scenario:** Following the guide on a phone, the owner types record C’s commands into a live session using an English layout. German keyboard selection and its test occur only in the next installer step.

   **Impact:** Mistyped punctuation, paths and quoted variables produce failures before the owner reaches the documented keyboard setup.

   **Fix:** Configure and test the **live desktop’s** German keyboard before opening Konsole; distinguish that setting from the installer’s target-system keyboard. Include punctuation needed by the commands, such as `/ - " $`, in the test.

   **Check:** Follow the guide from a second device with a German physical keyboard and an initially English live session. All commands must be enterable without undocumented layout changes.

5. **Should-fix — The repeated Windows comparison omits reopening an administrator terminal after reboot.**  
   Where: [INSTALL-RECORD.md:29](/C:/Users/pab/AresOS-10-own-ssd-install/docs/INSTALL-RECORD.md:29).

   **Scenario:** After fitting or installing, the owner follows the direct link to record B and opens ordinary PowerShell. Record A’s elevated terminal disappeared during reboot; B does not repeat that prerequisite.

   **Impact:** The firmware-reading helper can fail for insufficient privileges, making a healthy installation appear to have failed its safety check.

   **Fix:** Begin B with the complete German navigation: right-click **Start → Terminal (Administrator)**, approve the prompt, select **Windows PowerShell**. Include an elevation precheck with a specific corrective message.

   **Check:** Start the walkthrough after a fresh Windows boot, directly at section B, with no terminal already open.

The separate-drive route no longer needs C: shrink calculations, Windows free-space margins, donated-sector intervals, manual EFI/Btrfs/subvolume creation, selective deletion between Windows partitions, or C: extension during undo. The draft correctly removes those operations; the remaining manual bookkeeping should also be simplified.

The minimal safe version retains verified backups, two labelled and boot-tested USBs, encryption/power checks, model-specific fitting, a saved Windows baseline, positive Crucial identification, a qualified whole-drive installer with Crucial’s own EFI, the released AresOS handoff and Windows-return checks. Detailed comparisons should produce clear pass/fail results; returning to Windows should require no disk operation.