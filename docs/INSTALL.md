# Install AresOS on its own SSD

Read on your phone; save the [emergency card](EMERGENCY.md) there. **Start at step 1 and follow the numbered steps in order.** The [current gate/status table](INSTALL-STATUS.md#current-gates) is the only release authority. Until it permits physical installation, read only: do not open the laptop, write media or install. Agents do none of those actions.

This route is for Lenovo LOQ 15IRH8 (82XV), German Windows 11 Home and Crucial P310 500 GB (`CT500P310SSD801`). Crucial is the target; Micron `MTFDKCD512TFK…` 512 GB is **Windows — KEEP**. Expected sizes 465/477 GiB are estimates, never identification. Use model + serial + GUIDs. No C: resizing, shared Windows EFI or Linux mounts/writes on Micron. Ordinary Windows records still write ordinary files. The same-drive route is archived, not a fallback.

Keep a private checklist and [record](INSTALL-RECORD.md) off-device. At each step write its number, time and PASS/FAIL. Every blank or unclear check means **STOP → go to [Help](INSTALL-REFERENCE.md#help)** with that number; resume only at the named return step after resolution. Never photograph passwords, tokens or recovery keys. **Ctrl = Strg**. F12/F2 at power-on have **Fn+F12/Fn+F2** alternatives; [console entry/exit](INSTALL-REFERENCE.md#console) supplies both FnLock cases.

## 1. Backups, recovery and Windows preparation

- [ ] Finish Windows updates/restarts. Back up files, photos, schoolwork and game saves independently of both SSDs; open several copies. Disconnect the backup device.
- [ ] Label two distinct sticks **WINDOWS RECOVERY — KEEP** and **ARESOS INSTALLER — ERASE OK** (ordered 2 × 64 GB). Recovery excludes personal-file backups; its wizard's capacity requirement wins. Search **Wiederherstellungslaufwerk** (`recoverydrive.exe`) → approve → **Systemdateien auf das Wiederherstellungslaufwerk sichern → Weiter**. Connect only the recovery stick; recheck identity → **Weiter → Erstellen**. Finish, safely eject.
- [ ] In `msinfo32`, require **BIOS-Modus: UEFI**, **Sicherer Startzustand: Aus**. Right-click Start → **Terminal (Administrator) → Windows PowerShell**:

```powershell
manage-bde -status C:
```

Require **Vollständig entschlüsselt**, **0,0%**, protection off. Suspended/unknown encryption stops for an owner-reviewed plan and independently saved matching recovery key; do not improvise decryption.

- [ ] Save work, then:

```powershell
powercfg /hibernate off
powercfg /a
```

First command normally prints nothing; second must show **Ruhezustand / Schnellstart** unavailable because hibernation is disabled. Restart Windows; leave both disabled throughout dual boot.
- [ ] Power on → repeatedly **F12** (or **Fn+F12**) → recovery stick's UEFI entry. Expect language/keyboard or **Option auswählen**; choose **PC ausschalten**, never repair/reset/reinstall. Unplug and preserve it.
- [ ] **F12** (or **Fn+F12**) → **Windows Boot Manager**, both sticks absent. Complete [record A](INSTALL-RECORD.md#a-save-the-windows-baseline); copy off-device. Require the original Micron EFI/Microsoft loader target, disk GUID and every partition GUID/type/boundary. Never replace this baseline.

**Record:** backup-open test, recovery boot/date/label, UEFI/encryption/power outputs, record A location. **STOP → go to [Help](INSTALL-REFERENCE.md#help)** on any difference. After that detour, **Return to step 1** here; all boxes PASS → [step 2](#2-prepare-and-test-the-installer-stick).

## 2. Prepare and test the installer stick

- [ ] Use the pinned **Bazzite nvidia-open live KDE ISO, no Steam Gaming Mode**, and **Fedora Media Writer Windows x64 5.3.2**. [Download and full-hash checkpoint](INSTALL-REFERENCE.md#media-checksums): compare the complete ISO and writer against both repository pins and fresh publisher checksums. A changed/missing stable file requires maintainer requalification, never a new owner pin. **Return to step 2** here after that checkpoint.
- [ ] Disconnect recovery/backup devices. Connect only **ARESOS INSTALLER — ERASE OK**. Media Writer: **.iso-Datei auswählen → Weiter → Auswählen...** → checked ISO. Under **Ausgewählte Datei**, check the filename; under **USB-Laufwerk**, match the labelled stick's name/capacity.
- [ ] **Schreiben** opens **Löschbestätigung**: the entire device will be erased. Recheck the target before its second **Schreiben**. Wrong/unclear target → **Abbrechen**, no write. Expect **<ISO name> erfolgreich geschrieben** after writing/verification → **Fertig**. [Exact warning and cancellation reference](INSTALL-REFERENCE.md#writer-labels); **Return to step 2** here. Safely eject; cancel Windows format prompts.
- [ ] **F12** (or **Fn+F12**) → UEFI installer USB. Expect Bazzite boot menu then live desktop; do not install. Shut down through the desktop; unplug and return to Windows. Both sticks must boot successfully before fitting.

**Record:** filenames/versions/full hashes, exact stick identity, erase-dialog cancellation trial and successful boot. **STOP → go to [Help](INSTALL-REFERENCE.md#help)** on any mismatch/error. Return to step 2 after resolution; PASS → [step 3](#3-fit-and-identify-both-drives).

## 3. Fit and identify both drives

- [ ] Open the [model-specific fitting and battery checkpoint](INSTALL-REFERENCE.md#fitting). **Return to step 3** here only after its entire sequence passes. Battery warning signs require Lenovo/qualified repairer, with no connector work or reconnection. Occupied slot, missing parts, poor seating, resistance, damaged clips or unclear thermal pieces mean stop without powering on. Never use the screw to pull the SSD into place; leave Micron alone.
- [ ] After closing, reconnect AC. Power on → **F2** (or **Fn+F2**) → **More Settings** → storage/device information. Require **both Micron and Crucial**, model/serial where available; the boot list alone cannot identify an empty SSD. Exit without other changes.
- [ ] Windows: cancel Crucial initialise/format prompts. Direct **F12** (or **Fn+F12**) → Windows with both USBs absent; run [record B](INSTALL-RECORD.md#b-compare-windows-after-each-stage), stage **after-fit**. Require its full Windows-unchanged PASS line. **Return to step 3** here.

**Record:** private Crucial-label photo, fitting/seating result, firmware both-drive screen, timestamped after-fit comparison. **STOP → go to [Help](INSTALL-REFERENCE.md#help)**; battery warnings → qualified repairer first. Return to step 3 after resolution; PASS → [step 4](#4-install-and-prepare-corrected-stock).

## 4. Install and prepare corrected stock

- [ ] AC connected, lid open. **Offline from this live boot until `prepare` passes:** no Wi-Fi profile or Ethernet. The installer copies network profiles. Disconnect backup/recovery devices. **F12** (or **Fn+F12**) → UEFI installer USB.
- [ ] Before Konsole: **System Settings → Keyboard → Layouts → Enable** (accessible name **Configure Layouts**) → **Add → German → OK**, German first/active, Global switching if offered → **Apply**. In a text editor physically type `y z / - " $ ä ö ü`; correct every character. Repeat after every live boot. Then open Konsole → [record C](INSTALL-RECORD.md#c-identify-both-drives-in-live-linux). Match Micron to A and Crucial to its label by full identity, never disk number/size alone. Require Micron unchanged/unmounted and Crucial empty (no partitions, signatures, mounts or prior data). **Return to step 4** here with a same-session mapping.
- [ ] Installer **English (United States) → Welcome → Change system keyboard layout**: add German, remove US, **Save**; summary contains only **de**. **Date and time**: automatic timezone off → **Europe → Berlin**.
- [ ] **Installation method → Change destination**: match current whole-disk path in record C, only Crucial selected → **Use entire disk**. Do not use alongside/reclaim/manual. **Storage configuration**: **Encrypt my data** unchecked for this disposable trial. Personal use/encryption is a later decision.
- [ ] **Create Account**: **Use local account** checked, administrator access stated. Enter **ares-recovery** as User name first, full name, strong unique passphrase twice. Do not create daily `ares` or enable root. Keep the passphrase securely off-device.
- [ ] **Review and install**: record C installer-plan PASS requires every storage row on Crucial, its own **new EFI at /boot/efi**, boot/system/data, no Micron mount/write/EFI reuse. Join every path to this session's identity map. Save the entire summary privately. Any unclear/shared Windows EFI → **Quit**. Only all PASS permits **Erase data and install**.
- [ ] On success, reboot/remove installer; press nothing. **Linux is initially default**, including stock's one-time local hardware setup/possible automatic reboot. Stay offline through sign-in as **ares-recovery**, German layout. Unexpected signature/enrollment/error screens → stop.
- [ ] Shut down normally offline, installer absent. **F2** (or **Fn+F2**) → **More Settings → Boot → UEFI**: recorded **Windows Boot Manager first → Save and Exit**. Press nothing; require unattended Windows. Windows remains first thereafter. In Windows plug in only the former installer stick.
- [ ] Media Writer 5.3.2: **<stick name> wiederherstellen → Weiter** → **Laufwerk <stick name> wiederherstellen**. Recheck identity and the warning that live system/all saved data will be deleted → **Wiederherstellen**. Require **Das Laufwerk wurde erfolgreich wiederhergestellt! → Fertig**. This makes exFAT. [Restore details](INSTALL-REFERENCE.md#writer-labels), then **Return to step 4** here. On error stop; no diskpart/Format/third-stick fallback.
- [ ] PowerShell 7 in the reviewed repository used for record A; replace `T` with the restored stick's actual D–Z letter checked in Explorer, never C:

```powershell
Import-Module ./docs/install-tools/OwnerTools.psm1 -Force
Copy-AresOwnerTools -Source ./os/owner-tools/payload -DriveLetter T
```

Require `PASS tools manifest SHA256 118212ec60844043856b5531be95cf2319f9943319679fa6149f999db89bf6ba` and `PASS ARESTOOLS ready; safely eject and unplug before shutdown/restart or record B.` Safely eject/unplug. Do not use WINDOWS RECOVERY. Run record B **after-bazzite**, both sticks absent; **Return to step 4** here with PASS.
- [ ] **F12** (or **Fn+F12**) → recorded Linux entry → **ares-recovery** sign-in. [Enter tty3 and become administrator](INSTALL-REFERENCE.md#console); **Return to step 4** here, keeping that session open. Only now insert ARESTOOLS. If text covers the prompt, press Enter. Type exactly:

```bash
sudo bash -c 'set -e; mount -o ro LABEL=ARESTOOLS /mnt; trap "umount /mnt" EXIT; bash /mnt/ares-tools/at install'
```

At prompts enter photographed Crucial serial and record A's Micron serial. Require `PASS install` and the same manifest fingerprint. It installs root-only shared tools; it unmounts even on STOP. Do not try another mount path.

```bash
sudo /var/lib/ares/at prepare
```

Require `PASS prepare`, exact corrected stock checksum/serial/stateroot and `pin yes; pending none; updaters paused`. This pauses reviewed OS updaters, establishes idle, handles only permitted leftover work, repairs only booted stock and pins it. One/two stock serials are permitted; leave the old unpinned serial alone. A five-minute wait STOP names the blocker; keep session open and get help, without reboot/network/guessed repair. Run the **same prepare command again**; require `Already prepared; no OS mutations` and `PASS prepare`.
- [ ] Now enable networking using stock's controls. Leave NVIDIA Flatpak sync enabled: offline notifications/unfinished app-runtime retry are expected, distinct from OS deployment work. Then:

```bash
sudo /var/lib/ares/at title
sudo /var/lib/ares/at records
sudo /var/lib/ares/at export
```

Require `PASS title`, `PASS records`, `PASS export` and **SAFE TO REMOVE ARESTOOLS**; unplug. Title verifies entire prepared list/pins/pending/BLS unchanged after network. Compare installed disk/EFI identities with record C/A. Save corrected stock identity, resolved title, state/time; mark older titles INVALID. Full diagnostics remain in `/var/lib/ares/records`; export copies JSON with hash readback and unmounts. Never pull a busy/mounted stick.

**Record:** live mapping, installer plan/account/layout, firmware order, Windows comparison, both prepare results, title/records/export. **STOP → go to [Help](INSTALL-REFERENCE.md#help)**, preserving this session and screen. Return to step 4 after resolution. With all boxes PASS → [step 5](#5-prove-windows-and-corrected-stock). No authentication yet.

## 5. Prove Windows and corrected stock

- [ ] All sticks absent, latest title saved:

```bash
sudo /var/lib/ares/at reboot
```

Require `PASS reboot` / `Reboot requested; Windows stays default; F12 then Linux for one Linux start` (screen may disappear on restart). **Press nothing:** Windows must start unattended, without USB. Then direct **F12** (or **Fn+F12**) → Windows and [record B](INSTALL-RECORD.md#b-compare-windows-after-each-stage), stage **after-bazzite**. Require `PASS: Administrator terminal.` and `PASS: Windows disk identity, all partition GUIDs/types/boundaries and original Windows boot target match.` Copy records off-device. ARESTOOLS may be inserted in running Windows just to copy exports; eject/unplug before comparisons/restart. **Return to step 5** here.
- [ ] **F12** (or **Fn+F12**) → recorded Linux → stock greeter → **ares-recovery**, German password. [Fresh tty3 login → sudo -i](INSTALL-REFERENCE.md#console), then **Return to step 5** here:

```bash
sudo /var/lib/ares/at check
sudo /var/lib/ares/at title
sudo /var/lib/ares/at records
```

Require `PASS check`, `PASS title`, `PASS records`, loaded **de**/override-free corrected stock and exact saved pin/identity. Physically type `yz-/!ü` as public text (do not execute it); clear the line with **Ctrl+U (Ctrl = Strg)**. Type `exit` once to leave root for the recovery-user prompt; run `sudo -k`, then `sudo -v`, and enter the unchanged password to prove fresh password sudo. Return with `sudo -i`. Check rendered stock greeter/network/hardware. Linux mounts/EFI GUID must map only to Crucial; Micron must match original A. No stale-title or missing record exception.

**Record:** unattended no-key/no-USB Windows time, successful B filename, installed C/EFI comparison, physical password/text and exact stock title/state/time. **STOP → go to [Help](INSTALL-REFERENCE.md#help)** on any missing proof; **Return to step 5** after resolution. All checks PASS: write **STEP 5 COMPLETE** with those evidence locations in your private checklist. This marker is invalid if any check failed or its evidence is missing. Continue to [step 6](#6-switch-to-aresos).

## 6. Switch to AresOS

**Entry gate: require STEP 5 COMPLETE and its evidence before authentication or switching. If absent, STOP → [Return to step 5](#5-prove-windows-and-corrected-stock).** Recheck the marker immediately before each login or switch invocation, including a return from any detour. Tools do not enforce this physical Windows proof.

- [ ] Stock **ares-recovery UID1000 in wheel** is administrator; daily **ares UID1001 without wheel** must not yet exist. The following commands recheck accounts, saved stock state, idle/paused updaters and disk identities. Never repair accounts to bypass STOP. Keep German for this initial path.
- [ ] In the open tty3 administrator session, with step 5 evidence present:

```bash
sudo /var/lib/ares/at login
sudo /var/lib/ares/at verify
```

At prompts enter GitHub username and the approved unexpired **read:packages-only** token, **only at the hidden token prompt**. Record its identifying note/expiry privately for retirement, never the secret. Require `PASS login` and `PASS verify` for the exact release/signature:
`ghcr.io/ares-empire/aresos@sha256:9b19b7942bc131934eac3733a7f8a1c1de488659075897f60c006bc88c77f3eb`.
Credentials are root-owned mode0600 in `/etc/ostree/auth.json`; no token in commands/photos/chat/records. Failed checks → help, never public-image/signature bypass.
- [ ] Step 5 marker still valid, verify PASS:

```bash
sudo /var/lib/ares/at switch
```

Then refresh the title:

```bash
sudo /var/lib/ares/at title
```

Require `PASS switch`, `PASS title`, exact signed staged release and saved corrected pin. **Every reorder invalidates every old title**, including this staged switch. Save the new identity-resolved title as **provisional**, with checksum/serial/stateroot, pin, pending/transaction state and time. No recovery by provisional row.
- [ ] All sticks absent, title saved:

```bash
sudo /var/lib/ares/at reboot
```

**F12** (or **Fn+F12**) → recorded Linux. A failed first boot means **F12 → Windows → help**, never a guessed GRUB title. Successful boot → [step 7](#7-check-the-first-aresos-session).

**Record:** token note/expiry only, signature/digest PASS, staged identity/title/time. **STOP → go to [Help](INSTALL-REFERENCE.md#help)**. Return to step 6 only with step 5 proof rechecked; permanently abandoning → [step 9](#9-retire-access-and-return-to-windows).

## 7. Check the first AresOS session

- [ ] Expect **labwc and foot**, no Minecraft yet. Enter [tty3 as ares-recovery → sudo -i](INSTALL-REFERENCE.md#console) using German; **Return to step 7** here:

```bash
sudo /var/lib/ares/at check
sudo /var/lib/ares/at title
sudo /var/lib/ares/at records
```

Require all PASS: exact AresOS + corrected pinned stock final pair, no surviving old serial or retained keymap overrides, daily `ares` UID1001/no wheel and running labwc/foot. Save refreshed stock title before trusting recovery; staged title is now INVALID. Prove console `yz-/!ü` and fresh password sudo as step 5; return to desktop using the console-exit instructions. Test the same public text in foot without executing it.
- [ ] Stay on AC, lid open. Check RTX4060 with `nvidia-smi`, display/brightness, audible sound, network after reboot and touchpad. Test **Super+Ctrl+Escape (Ctrl = Strg)**, fresh recovery login/logout/desktop return. For restarts: recovery account → guarded `reboot`, all sticks absent → **F12** (or **Fn+F12**) → Linux. Require a second Linux boot.
- [ ] Log out the recovery console to its login prompt. From the desktop briefly press physical power; require clean shutdown. Boot Linux again, recovery tty3 → `sudo -i`:

```bash
sudo /var/lib/ares/at logs
```

Require `PASS logs` (collection only); inspect saved previous logind/full journal for the actual button event and orderly shutdown. Missing evidence leaves the physical gate unmet. Export diagnostics only after sign-in, require SAFE TO REMOVE, unplug before reboot.
- [ ] Direct Windows, first with USB absent. The separately supervised USB-present hardware trial uses **WINDOWS RECOVERY**, never ARESTOOLS; select Windows explicitly, then remove recovery without using its repair options. Check files/sound/network and [record B](INSTALL-RECORD.md#b-compare-windows-after-each-stage), **after-aresos**, USBs absent for B; require full PASS. **Return to step 7** here.

**Record:** final pair/title, console/foot/password results, hardware/button/journal/second-boot and Windows comparisons. **STOP → go to [Help](INSTALL-REFERENCE.md#help)**, return to step 7 after resolution. Minecraft/app/save/restore, battery use and suspend are later milestones. PASS → [step 8](#8-everyday-boot-and-recovery).

## 8. Everyday boot and recovery

Windows stays default after step 5 (first set during step 4's round trip). **F12** (or **Fn+F12**) picks the recorded Linux entry for one start; its label may remain Fedora/Bazzite. Never make Linux first to avoid this. If order changes: repeat step 1's encryption check, **F2** (or **Fn+F2**) → **More Settings → Boot → UEFI → Windows Boot Manager first → Save and Exit**; require unattended no-USB Windows and record B.

Tools stick: insert only after Linux is up and you are signed in; export → SAFE TO REMOVE → unplug before every shutdown/restart. If forgotten at power-on, do not select it; unplug and continue. Text over prompt → Enter. Backup stock keeps **German**, even after a later AresOS layout change.

Later work is outside this installation path: [layout trial](INSTALL-PROCEDURES.md#later-layout), [rollback/keep-stock and recovery menu](INSTALL-PROCEDURES.md#recovery-menu), [optional removal/erasure](INSTALL-PROCEDURES.md#optional-removal-or-erasure). Each has its own checks and return destination; **Return to step 8** after a completed later procedure. No guessed GRUB positions, firmware resets, TPM clear, entry deletion or boot repair.

**Record:** current boot order, latest stock title, future procedure result. **STOP → go to the [symptom card](EMERGENCY.md)**, then [Help](INSTALL-REFERENCE.md#help) if unresolved; return to step 8 after resolution. When permanently leaving AresOS, continue to [step 9](#9-retire-access-and-return-to-windows).

## 9. Retire access and return to Windows

**Required on permanent abandonment**, whether Crucial stays installed, is removed or erased, including when Linux cannot boot:

- [ ] In Windows or on your phone, sign in to GitHub → profile picture → **Settings → Developer settings → Personal access tokens → Tokens (classic)** → **Delete** to the right of the dedicated installation token (identify by the private note/expiry). Complete GitHub's confirmation if shown. Require that token to disappear from the list. Labels checked **2026-10-26** in [GitHub's current documentation](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#deleting-a-personal-access-token). Revoke the installation token even if the SSD is inaccessible. If no token was ever issued/used, record that instead; uncertainty → help.
- [ ] Record **revoked**, date/time and token note, never the secret. Local deletion is optional; this route uses no deletion command. Partition clearing/removal does not retire credentials.
- [ ] **Owner revocation check:** the [physical retirement gate](INSTALL-STATUS.md#current-gates) requires fresh authentication/private pull with the retired disposable token to fail, while retained deployments still boot offline. Existing `login` requires prepared stock; it cannot cover broken Linux or an already-switched machine. Have the maintainer supervise that gate on disposable credentials; do not return to authentication/switching here or claim list disappearance proves the negative test.
- [ ] Default undo leaves Crucial installed. Direct **F12** (or **Fn+F12**) → Windows, both USBs absent → [record B](INSTALL-RECORD.md#b-compare-windows-after-each-stage) **before-undo**. Require original Micron EFI/Microsoft target. **Return to step 9** here. Windows first via step 8's setup path, restart without keys/USB → require Windows → repeat B **after-undo**. Copy records off-device; leave Linux updaters paused. No case opening/erase needed.

**Record:** revocation/no-token result, outstanding supervised test if not performed, before/after-undo PASS and unattended boot. **STOP → go to [Help](INSTALL-REFERENCE.md#help)** if GitHub retirement or Windows proof fails; return to step 9 after resolution, remove/erase nothing. If explicitly choosing physical removal/reuse later, complete the [separate procedure](INSTALL-PROCEDURES.md#optional-removal-or-erasure), then **Return to step 9** to confirm Windows again. New installation trial: [Return to step 1](#1-backups-recovery-and-windows-preparation).
