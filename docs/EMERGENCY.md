# If something goes wrong

The AresOS emergency card. **Keep it on your phone.** If AresOS is broken, you can't read it on the laptop.

This card applies once AresOS is installed. Physical installation is still **not released** (see [INSTALL.md](INSTALL.md)). The exact commands live in INSTALL.md. 11k passed automated Part A in both drive orders with the earlier Windows-first timing. [11n](../reviews/11-two-disk-rehearsal/REPORT.md#11n-safe-switch-test-prerequisites-and-continued-qualification-2026-10-24) passed the revised first-login → Windows-first sequence and GRUB stock recovery/promotion/second stock boot in a protected-second VM, with every reached protected-disk/NVRAM/BootNext audit passing and final zero writes. Physical media, laptop, loaded keyboard/actual typing, manual menu and followability gates remain open. Do not guess menu positions or bypass a STOP; prefer F12 → Windows and getting help.

## Stock preparation stops before the switch

An NVIDIA Flatpak runtime notification while offline is expected. Leave its
sync enabled; it retries after networking becomes available. That notification
alone is not an OS deployment STOP. Keep networking off until the checked OS
updater pause; do not disable the sync to hide it. Completion and unchanged
deployments still need the physical check in INSTALL's release gate.

Run INSTALL's [pause-and-retain block](INSTALL.md#pause-and-retain-stock-before-the-windows-comparison)
at the first stock login, before restarting into Windows, and repeat it before
switching to AresOS. It first stops the reviewed OS updaters, records their
states and deployment processes, and cancels at most one leftover transaction.
A five-minute idle refusal names the blocking unit, transaction or client; keep
those diagnostics privately and get help. It can discard one newer upstream update that is staged but
has not booted. If a newer stock version has already booted, another origin is
staged, or the block prints **STOP**, do not reboot, repin or roll back by guesswork:
keep the printed identities privately and get help. Leave stock updates paused
during the trial; re-enable them only after stock is your permanent choice and
its second default boot has passed.

Stock hardware setup can leave two stock entries of the same checksum before
the switch. The keyboard block repairs the booted serial only, then pin retains
that corrected serial. The older unpinned serial stays untouched temporarily;
do not boot it or remove it. Switch finalization on the first AresOS boot should
leave exactly AresOS plus the corrected pinned stock. Normal rollback reorders
that pair; it does not bring the old serial back. A surviving old stock serial,
an unexpected list, or failure before the final pair/menu title is confirmed
means F12 → Windows and get help. 13f proved the full switch/rollback lifecycle,
loaded layouts and physical tty3/foot text in a protected-second VM. The old
unpinned stock serial was still present while the switch was staged, then was
absent from the final pair. Both final entry labels say **Bazzite**:

| Observed state | AresOS | Corrected pinned stock |
| --- | --- | --- |
| AresOS booted after switch | `Bazzite (ostree:0)` | `Bazzite (ostree:1)` |
| Rollback queued, before reboot; also stock booted afterward | `Bazzite (ostree:1)` | `Bazzite (ostree:0)` |

**Any deployment reorder invalidates the previous stock title immediately.**
This includes a staged switch, **queuing rollback before reboot**, pending-update
cleanup and setting the Linux default. Familiar Bazzite labels do not make the
old title safe: after rollback is queued, the old stock `(ostree:1)` can name
AresOS instead. Before rebooting, use INSTALL's
[stock-title checkpoint](INSTALL.md#refresh-the-recorded-stock-title-before-reboot)
as `ares-recovery` with `sudo -i`; resolve the BLS target by the saved stock
**checksum, serial and stateroot**, then record the current exact title/state.
Mark the old title INVALID. A missing refresh means **F12 → Windows and help**,
even if the menu looks unchanged. Do not choose just by these example digits
or assume an entry says “AresOS.”

The first-switch staged title is provisional because finalization can change
it again. Before your own first successful AresOS boot confirms the final pair
and refreshes the title, **F12 → Windows and help is still required** if
switching fails: the staged list can contain both stock serials. Physical
installation, actual laptop keyboard/menu interaction and live KDE/KWrite
followability remain **NOT RELEASED**. See the [13f REPORT](../reviews/13-keyboard-layout/REPORT.md#13f--physical-typer-coverage-and-one-final-qualification).

## Which keyboard layout to use for recovery

**Owner decision, 2026-10-25:** backup Bazzite keeps the **layout chosen in the
installer — German in this guide**. Changing AresOS to US or another layout does
**not** change that frozen backup. On AresOS tty3, log in as `ares-recovery`
using AresOS's current layout; after booting backup Bazzite, type that same
account's password using the **installer layout**. No mechanism copies later
layout settings into stock. Do not treat different physical password keys as
proof the password changed, or alter the backup to make it follow AresOS.

The VM checked **de → us → de, then rollback to de**. **US in AresOS followed
directly by rollback was not run**; the backup-layout exception follows bootc's
per-deployment `/etc` and is source-verified, not runtime-verified. The approved
exception and later-layout steps are in
[INSTALL](INSTALL.md#change-the-aresos-layout-later-recovery-keeps-the-installer-layout).

## The three rules

1. **F12 → Windows Boot Manager is your way back.** AresOS lives on its own SSD and is built never to write to the Windows SSD, so Windows should keep starting on its own. That's the intended return route, checked with your install records. It isn't a guarantee: if Windows Boot Manager is missing or Windows doesn't start, stop and get help.
2. **When unsure, stop.** Take a photo of the screen and get help.
3. **Never "fix" with destructive tools:**
   - don't format or erase a drive
   - don't delete boot entries or AresOS versions
   - don't reset the firmware (BIOS) to defaults or clear the TPM
   - don't run Windows boot-repair commands

## Two different menus

- **F12 menu (the laptop's own menu):** tap F12 right after pressing the power button. It lists **Windows Boot Manager** and the Linux entry (possibly called Fedora or Bazzite). It picks which SSD starts, for this one start only. Automatic entries for unplugged devices, such as the installer stick, may disappear; that is normal. A missing Windows Boot Manager still means stop.
- **Boot menu (GRUB, on the AresOS SSD):** appears only after **F12 → the recorded Linux entry**. Both AresOS and stock can be labelled **Bazzite**. Use only the stock title resolved from the saved checksum **and serial** after the latest reorder and recorded before reboot. Do not count staged JSON rows or reuse the title saved after the original switch: queuing rollback already invalidates it. If the record is stale, missing or unclear, use F12 → Windows and get help, even when both menu labels look familiar.

Immediately after installation Linux is the default, including stock's one-time hardware-setup reboot and first-login pause/pin. **Windows becomes the default only after INSTALL §5's F2 → Windows first → Save and Exit and its successful unattended Windows check.** From then on, pressing nothing starts Windows; F12 selects one Linux start.

## Find your situation

| What's happening | What to do |
|---|---|
| **I want Windows.** | F12 → **Windows Boot Manager**. ([INSTALL §8](INSTALL.md#8-choose-the-os-at-startup)) |
| **AresOS runs, but the game or desktop is stuck.** | Press **Super+Ctrl+Esc** (Super is the Windows-logo key). It opens a terminal **without administrator rights**. Commands there can still change or delete your own files, so only type what a guide or Claude gives you. If no terminal opens, use the next row. |
| **AresOS is broken, and I need to fix it or undo it.** | Press **Ctrl+Alt+F3**, log in as **`ares-recovery` using the current AresOS layout**, and run **`sudo -i`**. Follow [INSTALL §6, "Roll back"](INSTALL.md#roll-back-to-the-retained-stock-deployment): run the checked rollback command, inspect identity, invalidate/refresh the stock title **before reboot**, then `systemctl reboot` → **F12 → the recorded Linux entry**. At stock's greeter sign in as **`ares-recovery` using the installer layout**. Windows stays the firmware default. If you stay in the current session instead, exit any root shell, run `sudo -k`, then `exit`; wait for the login prompt before Ctrl+Alt+F1. |
| **Nothing responds at all.** | First **press the power button briefly** (don't hold it) and wait about a minute: AresOS may still shut down cleanly. If it stays on, **hold the power button until the laptop turns off**. A forced power-off can lose unsaved work. **Never do this while a firmware/BIOS update screen is showing.** Then F12 → Windows Boot Manager. |
| **AresOS doesn't even reach the text screen.** | **F12 → the recorded Linux entry** opens GRUB (if hidden: **Esc** once, then **↓**). Use the stock title resolved by checksum/serial **after the latest reorder**, not a stale original-switch title. A failed first switch boot or missing refreshed record means **F12 → Windows and help**. With a valid matching record, select stock, sign in as **`ares-recovery` using the installer layout**, and run `sudo -i`. Follow ["Keep recovered stock as the default"](INSTALL.md#keep-recovered-stock-as-the-default): checked default command → inspect → refresh title before reboot → `systemctl reboot` → **F12 → the recorded Linux entry**, then no GRUB selection. Sign in as `ares-recovery` with the installer layout and verify stock again. Physical menu/followability is still an **open release gate**; stop at any difference. Windows remains the firmware default. |
| **Windows doesn't start, or F12 doesn't list Windows Boot Manager.** | Don't repair, reset or format anything. Stop and get help from another device. The **WINDOWS RECOVERY — KEEP** stick is the last resort; don't use its repair options without help. |
| **I'm done with AresOS.** | Just stop using it. Make Windows Boot Manager the default again and leave the SSD in. Nothing needs erasing. ([INSTALL §9](INSTALL.md#9-undo-return-to-everyday-windows)) |

## Getting help from Claude

If Windows works, start it (F12 → Windows Boot Manager), open a terminal, then run:

```powershell
cd C:\Users\pab\AresOS
claude
```

If Windows doesn't start, use Claude on your phone. Either way, describe what you saw and when, and share the screen photos. A help button inside AresOS that opens Claude directly is planned for later.

## Keep these safe (not only on the laptop)

- The **`ares-recovery` password**. Without it, the text-screen route above doesn't work.
- Your **install record** from INSTALL.md: drive identities, corrected stock checksum/serial/stateroot, installer keyboard layout, and the latest identity-resolved stock title with transaction state/time. Any deployment reorder invalidates an earlier title.
- The two USB sticks: **WINDOWS RECOVERY — KEEP** in a drawer, and the installer stick.

## Taking the AresOS SSD out

This is the last step, not the first, and it's rarely needed: [INSTALL §9](INSTALL.md#9-undo-return-to-everyday-windows) shows that the normal undo leaves the SSD in. Remove it only through §9's full procedure. That means backups verified first, Windows starting on its own with its checks passing, and every battery-safety step. **If those checks can't pass, leave the SSD in and get help.** Taking it out doesn't undo every change: firmware boot entries or settings may still need tidying.

The running deployment's system keyboard setting is `localectl`; see INSTALL's
initial repair and later-layout steps. The retained backup keeps the installer
layout. A keymap or identity STOP requires help before any reboot or switch.
