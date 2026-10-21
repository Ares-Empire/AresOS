Reviewed commit `4de9644`. Two safety gaps remain.

1. **Blocking — Undo does not prove Windows boots from the EFI partition that will survive deletion.**  
   **Where:** [INSTALL.md, §9 steps 1–5](C:/Users/pab/AresOS-05-dual-boot/docs/INSTALL.md:174), [OS-BASE.md, Appendix C.9](C:/Users/pab/AresOS-05-dual-boot/docs/design/OS-BASE.md:319).

   **Scenario:** A later Windows repair/reinstallation places Windows boot files on the AresOS ESP. F12 → “Windows Boot Manager” still starts Windows directly, and the AresOS partition GUIDs and boundaries still match the installation record. The guide’s checks therefore permit deleting that ESP. Bazzite explicitly warns that Windows installation can reuse its EFI partition; Microsoft documents boot-file placement and firmware-entry creation through BCDBoot. [Bazzite installation guide](https://docs.bazzite.gg/General/Installation_Guide/install-guide/#dual-booting-windows), [Microsoft BCDBoot](https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/bcdboot-command-line-options-techref-di).

   **Impact:** Undo deletes Windows’ active boot files and leaves Windows unbootable despite the successful preliminary boot.

   **Fix:** Before any deletion, verify the **current Windows Boot Manager device path identifies the original Windows ESP’s partition GUID**, with the expected Microsoft loader path. Require review if Windows now uses the AresOS ESP or the mapping cannot be established. A firmware entry’s displayed name is separate from its device/file target. [UEFI boot-manager specification](https://uefi.org/specs/UEFI/2.9_A/03_Boot_Manager.html#load-options).

   **Check:** In a file-backed VM, make Windows boot directly from Microsoft boot files on the Linux ESP while retaining the recorded partition boundaries. The revised undo procedure must refuse deletion; the ordinary original-ESP case must pass.

2. **Should-fix — The prescribed GParted identity check compares different kinds of identifiers.**  
   **Where:** [INSTALL.md, §9 steps 2–4](C:/Users/pab/AresOS-05-dual-boot/docs/INSTALL.md:175).

   **Scenario:** The owner records GPT partition GUIDs as instructed, then opens GParted’s **Information** dialog to check them. Its `UUID` field displays the **filesystem UUID**, not the GPT partition GUID. GParted’s implementation explicitly uses the filesystem identifier for this field. [GParted source](https://github.com/GNOME/gparted/blob/master/src/Dialog_Partition_Info.cc).

   **Impact:** Even a correct installation cannot satisfy the stated identity check through that dialog. Following the stop rule blocks undo; treating the different identifier as equivalent defeats a required deletion safeguard.

   **Fix:** Supply a read-only live-environment inventory showing device path, **PARTUUID** and filesystem **UUID** separately. Match PARTUUID to the saved Windows `Get-Partition.Guid`, then correlate that device path with GParted’s sector boundaries. State explicitly that its displayed UUID is a different field.

   **Check:** Rehearse identification on the chosen GParted Live release with two ESPs. Every deletion candidate must match its recorded PARTUUID and boundaries without relying on labels, partition numbers or filesystem UUID substitution.