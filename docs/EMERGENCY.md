# AresOS emergency card

Keep this on your phone. Pick the symptom below. **Ctrl = Strg**; Super = Windows-logo key.

## Frozen laptop

**Action:** try **Super+Ctrl+Esc (Ctrl = Strg)** for a normal-user terminal.
If nothing responds, briefly press power and wait one minute. Still on? Hold power until off (unsaved work can be lost), then repeatedly tap **F12** (or **Fn+F12**) → **Windows Boot Manager**. Never force off during a firmware/BIOS update; get help instead.
**STOP → go to [Help](INSTALL-REFERENCE.md#help)** if Windows is missing or will not start. Return to [step 7](INSTALL.md#7-check-the-first-aresos-session) only after help clears the failure.

## Failed first switch boot

**Action:** restart → **F12** (or **Fn+F12**) → **Windows Boot Manager** → get help.
The staged stock title is provisional. Do not try a GRUB row, repeat the switch or repair boot files.
**STOP → go to [Help](INSTALL-REFERENCE.md#help)**; return to [step 6](INSTALL.md#6-switch-to-aresos) only after help and the step 5 proof are complete.

## Stale or missing stock title

**Action:** do not choose a GRUB row. Use **F12** (or **Fn+F12**) → Windows → help.
Every deployment reorder invalidates old titles, even before reboot. Both entries can say Bazzite; position and checksum alone do not identify stock.
**STOP → go to [Help](INSTALL-REFERENCE.md#help)**. Return to [step 5](INSTALL.md#5-prove-windows-and-corrected-stock) before any authentication or switching.

## Password not accepted

**Action:** during a layout trial, return to the original open tty3 administrator session with **Ctrl+Alt+F3 (Ctrl = Strg)** or **Ctrl+Alt+Fn+F3 (Ctrl = Strg)** and [revert the trial](INSTALL-PROCEDURES.md#layout-revert).
Otherwise use **F12** (or **Fn+F12**) → Windows → help. AresOS uses its current layout; backup stock always uses the installer’s German layout. Do not change the password to guess your way through.
**After `PASS layout revert` on AresOS:** [complete fresh-login proof and finish](INSTALL-PROCEDURES.md#layout-recovery-proof), then [layout completion](INSTALL-PROCEDURES.md#layout-completion) and Return to [step 8](INSTALL.md#8-everyday-boot-and-recovery). **STOP → go to [Help](INSTALL-REFERENCE.md#help)** if the original session is unavailable or proof fails; keep the layout trial pending until help restores that recovery route. Do not resume the initial stock checks for this layout recovery.

## Text covers the prompt after stick hotplug or removal

**Action:** press **Enter** once to get the prompt back. Do not retype a running command.
If no prompt returns or a command prints STOP, preserve the screen and keep the session open.
**STOP → go to [Help](INSTALL-REFERENCE.md#help)**. Return to [step 4](INSTALL.md#4-install-and-prepare-corrected-stock), or your recorded later step, only after the command’s result is known.

## Forgotten tools stick at power-on

**Action:** do not select the stick in F12. Unplug it and continue to the recorded internal boot entry.
Plug ARESTOOLS in again only after Linux is up and you are signed in. Export/unmount and unplug before every restart.
**STOP → go to [Help](INSTALL-REFERENCE.md#help)** on an unfamiliar boot screen. Return to [step 5](INSTALL.md#5-prove-windows-and-corrected-stock) to verify the Windows proof before continuing.

## Battery warning sign

**Action:** stop using the laptop. If running or charging, disconnect the **external charger only if safe without touching a hot or swollen case**. Move it away from anything flammable only if safe; otherwise keep clear and move nearby flammable items away if safe.
**Already open, battery disconnected:** leave battery and internal connectors untouched; keep charger/battery disconnected. Do not press, handle, remove, reconnect or charge a damaged battery, or power on. Bulging, swelling, cracks, dents, leakage, unusual heat/smell or doubt requires Lenovo or a qualified repairer; no further use or fitting until service clearance. [Lenovo safety source used](INSTALL-REFERENCE.md#battery-safety-sources).
**STOP → go to Lenovo/qualified repairer, then [Help](INSTALL-REFERENCE.md#help)**. Return to [step 3](INSTALL.md#3-fit-and-identify-both-drives) only after repair clearance.

## Windows missing or not starting

**Action:** stop; get help on your phone. Do not reset firmware/TPM, delete entries, format or run boot repair.
Keep WINDOWS RECOVERY preserved; use its repair options only with help.
**STOP → go to [Help](INSTALL-REFERENCE.md#help)**. Return to [step 1](INSTALL.md#1-backups-recovery-and-windows-preparation) after resolution.

## Leaving AresOS permanently

**Action:** revoke the private-pull token from Windows or your phone, even if Linux cannot boot.
Use [step 9](INSTALL.md#9-retire-access-and-return-to-windows), whether leaving Crucial installed, removing it or erasing it. Deleting local files or partitions does not revoke access.
**STOP → go to [Help](INSTALL-REFERENCE.md#help)** if the token cannot be identified/deleted. Return to [step 9](INSTALL.md#9-retire-access-and-return-to-windows).

## References and preparation

The sole [current gate/status table](INSTALL-STATUS.md#current-gates) governs release. [Console entry/exit and FnLock](INSTALL-REFERENCE.md#console), [checked recovery menu and rollback](INSTALL-PROCEDURES.md#recovery-menu), [stock preparation](INSTALL.md#4-install-and-prepare-corrected-stock), and [private records](INSTALL-RECORD.md) contain the longer procedures. Preparation and evidence are outside this card’s symptom actions. Return to [step 1](INSTALL.md#1-backups-recovery-and-windows-preparation) for a new trial.
