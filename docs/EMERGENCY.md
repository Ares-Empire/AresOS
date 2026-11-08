# AresOS emergency card

Keep this on your phone. Pick the symptom below. **Ctrl = Strg**; Super = Windows-logo key.

## Frozen laptop

**Action:** try **Super+Ctrl+Esc (Ctrl = Strg)** for a normal-user terminal.
For a black screen just after a console switch, wait **one minute**, do not reboot; [console fallback](INSTALL-REFERENCE.md#console). If otherwise frozen, request normal shutdown with a brief power press only when no command/write or layout trial is running. Wait **at least 10 minutes** without progress; force off only under the [hung-shutdown conditions](INSTALL-REFERENCE.md#hung-shutdown-or-restart), then **F12** (or **Fn+F12**) → **Windows Boot Manager** → Help. Never force off during a firmware/BIOS update; unknown command completion also needs Help.
**STOP → go to [Help](INSTALL-REFERENCE.md#help)** if Windows is missing or will not start. Return to [step 7](INSTALL.md#7-check-the-first-aresos-session) only after help clears the failure.

## Failed first switch boot

**Action:** use normal restart → **F12** (or **Fn+F12**) → **Windows Boot Manager** → get help. A hung restart uses the [10-minute wait and force-off conditions](INSTALL-REFERENCE.md#hung-shutdown-or-restart); never immediately hold power after switching.
The staged stock title is provisional. Do not try a GRUB row, repeat the switch or repair boot files.
Stock KDE returning instead of AresOS also fails: `PASS check` can describe valid stock and does not prove the switch finished.
**STOP → go to [Help](INSTALL-REFERENCE.md#help)**; return to [step 6](INSTALL.md#6-switch-to-aresos) only after help and the step 5 proof are complete.

## Blue MOK menu on first stock boot

**Action:** only on **Perform MOK management**, select **Continue boot**, Enter. Never enroll or change keys. [Expected screen](INSTALL-REFERENCE.md#mok-screen).
Normal stock boot continues → Return to [step 4](INSTALL.md#4-install-and-prepare-corrected-stock). Any other signature/enrollment/error screen, password request or repeated menu → **STOP → go to [Help](INSTALL-REFERENCE.md#help)**.

## Shutdown or restart hangs

**Action:** keep AC/lid open; wait **at least 10 minutes** with no progress, including after a switch. Keep waiting if progress changes. Force off only after a successful completed install/tool command and normal shutdown request. **Idle-live-session exception:** no successful install/tool command is required for an idle live session after requesting desktop shutdown. In either case, no firmware/BIOS update, media write/export or layout trial may be in progress. Unknown completion or an error → Help; do not force off. After a switch, require the recorded switch/title PASS and the checked reboot request first. [Full conditions and interrupted-switch outcome](INSTALL-REFERENCE.md#hung-shutdown-or-restart).
If those conditions permit a power hold, do it once until off → **F12 → Windows Boot Manager**. **STOP → go to [Help](INSTALL-REFERENCE.md#help)** before resuming; no switch retry or provisional GRUB title. Return to [step 4](INSTALL.md#4-install-and-prepare-corrected-stock) or the recorded calling step only after resolution; after a switch, Return to [step 6](INSTALL.md#6-switch-to-aresos) with step 5 proof rechecked.

## Stale or missing stock title

**Action:** do not choose a GRUB row. Use **F12** (or **Fn+F12**) → Windows → help.
Every deployment reorder invalidates old titles, even before reboot. Both entries can say Bazzite; position and checksum alone do not identify stock.
**STOP → go to [Help](INSTALL-REFERENCE.md#help)**. Return to [step 5](INSTALL.md#5-prove-windows-and-corrected-stock) before any authentication or switching.

## Password not accepted

**Action:** during a layout trial, return to the original open tty3 administrator session with **Ctrl+Alt+F3 (Ctrl = Strg)** or **Ctrl+Alt+Fn+F3 (Ctrl = Strg)** and [revert the trial](INSTALL-PROCEDURES.md#layout-revert).
For the **failed first install before tools installation**, resolve layout with the guiding session; if choosing reinstall, [Return to step 4, box 1](INSTALL.md#4-install-and-prepare-corrected-stock). Crucial must hold only that failed install's EFI, boot and system partitions, nothing else, with its saved plan/records; Micron must be unchanged/unmounted. Anything else or uncertain → **STOP → go to [Help](INSTALL-REFERENCE.md#help)**. Reinstall with **Use entire disk** on **Crucial only**, using the Create Account passphrase rule.
Otherwise use **F12** (or **Fn+F12**) → Windows → help. AresOS uses its current layout; backup stock always uses the installer’s German layout. Do not change the password to guess your way through.
**After `PASS layout revert` on AresOS:** [complete fresh-login proof and finish](INSTALL-PROCEDURES.md#layout-recovery-proof), then [layout completion](INSTALL-PROCEDURES.md#layout-completion) and Return to [step 8](INSTALL.md#8-everyday-boot-and-recovery). If the original session was lost, use [abandoned-trial recovery](INSTALL-PROCEDURES.md#abandoned-layout-trial). **STOP → go to [Help](INSTALL-REFERENCE.md#help)** if login/proof fails; no forced restart or password change. Do not resume the initial stock checks for this layout recovery.

## Crashed or restarted during a keyboard layout trial

**Action:** identify the interrupted action from your record. **Begin/revert:** after restart, try the **last confirmed layout once**; a failed login → Help. **Finish invoked, but no `PASS layout finish`:** the console may already use the proven new layout. Try the last confirmed layout **once**; only if login fails, try the recorded, proven new layout **once**. After two failed logins, **STOP → go to [Help](INSTALL-REFERENCE.md#help)**. Failed attempts before this route, unknown profiles/policy or any lockout warning → Help before starting. [Attempt-limit source and precautions](INSTALL-REFERENCE.md#layout-recovery-login-limit). Retained stock uses its own installer German.
Use a **fresh physical tty3 ares-recovery password login** for that bounded route ([TTY entry/exit](INSTALL-REFERENCE.md#console)); after that one successful login, run `sudo -i` in the same session using the successful map. If sudo rejects the password, stop at Help without a retry. Run `sudo /var/lib/ares/at layout abandon` once (require `PASS layout abandon`) and save the refreshed title.
**After `PASS layout abandon`:** [Finish abandoned-trial recovery](INSTALL-PROCEDURES.md#abandon-completion); do not run abandon again. If an accidental repeat says `Missing private layout-pending record` **and you already recorded that PASS**, use the same completion link. Every other refusal → **STOP → go to [Help](INSTALL-REFERENCE.md#help)**. On AresOS, check and Return to [step 8](INSTALL.md#8-everyday-boot-and-recovery); on retained stock, complete [keep-stock](INSTALL-PROCEDURES.md#keep-stock) before that return. Do not force a reset to test this route.

## A tools command stopped

**Action:** keep the entire screen and available administrator session open. If Linux is responsive, the installed tools are available and exporting is safe, insert ARESTOOLS after sign-in and run `sudo /var/lib/ares/at export`; require `PASS export` and **SAFE TO REMOVE ARESTOOLS**, then unplug.
Export includes private records and persistent STOP diagnostics from `/var/lib/ares/diagnostics`, copied as `diagnostic-` files with hash readback. Preserve them off-device; share no secrets. If the tools are unavailable (including bootstrap failure), export STOPs, or safe removal is absent, keep the error/photo privately and get help without pulling a mounted stick. **STOP → go to [Help](INSTALL-REFERENCE.md#help)**; Return to the failed recorded step only after resolution ([step 4](INSTALL.md#4-install-and-prepare-corrected-stock) for install/prepare, [step 8](INSTALL.md#8-everyday-boot-and-recovery) for later recovery). Never delete journals, retry another target or restart to clear a STOP.

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
