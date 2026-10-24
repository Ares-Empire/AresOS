# If something goes wrong

The AresOS emergency card. **Keep it on your phone.** If AresOS is broken, you can't read it on the laptop.

This card applies once AresOS is installed. Physical installation is still **not released** (see [INSTALL.md](INSTALL.md)). The exact commands live in INSTALL.md, and this card tells you which section to open. The 2026-10-24 [11j rehearsal](../reviews/11-two-disk-rehearsal/REPORT.md#11j-stock-pause-process-identity-and-decision-evidence-2026-10-24) passed its pinned-stock checks and review-only probe in both orders. The pause now records which unit, transaction or client prevents idle and permits one recorded transaction cancellation after updaters stop. A fresh budget guard repeatedly received HTTP 502; no fifth full was dispatched. Actual installed German files/options, installed stock preparation and the complete install/recovery/undo and GRUB promotion paths remain unqualified. Do not bypass any STOP. All reached probe protected-disk checks passed with final zero-write records; the UNTESTED recovery gate below stays open.

## Stock preparation stops before the switch

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
- **Boot menu (GRUB, on the AresOS SSD):** appears only after you pick the Linux entry. It lists the AresOS version and the backup Bazzite copy.

During the first trial Windows is the default: if you press nothing, Windows starts.

## Find your situation

| What's happening | What to do |
|---|---|
| **I want Windows.** | F12 → **Windows Boot Manager**. ([INSTALL §8](INSTALL.md#8-choose-the-os-at-startup)) |
| **AresOS runs, but the game or desktop is stuck.** | Press **Super+Ctrl+Esc** (Super is the Windows-logo key). It opens a terminal **without administrator rights**. Commands there can still change or delete your own files, so only type what a guide or Claude gives you. If no terminal opens, use the next row. |
| **AresOS is broken, and I need to fix it or undo it.** | Press **Ctrl+Alt+F3** to get a black text screen. Log in as **`ares-recovery`** with its password. From there you can undo the switch back to plain Bazzite. ([INSTALL §6, "Roll back"](INSTALL.md#roll-back-to-the-retained-stock-deployment)) When you're done, log out first: `exit` any root shell, then `sudo -k`, then `exit`. Wait for the login prompt, then press **Ctrl+Alt+F1**. |
| **Nothing responds at all.** | First **press the power button briefly** (don't hold it) and wait about a minute: AresOS may still shut down cleanly. If it stays on, **hold the power button until the laptop turns off**. A forced power-off can lose unsaved work. **Never do this while a firmware/BIOS update screen is showing.** Then F12 → Windows Boot Manager. |
| **AresOS doesn't even reach the text screen.** | F12 → pick the **Linux entry** to open the boot menu (if it's hidden: **Esc** once, then **↓**). Pick the **backup Bazzite entry that matches your install record**. Don't choose by position; if you can't tell which one it is, stop and use F12 → Windows instead. Picking it only counts for that one start, so then follow [INSTALL §6, "Keep recovered stock as the default"](INSTALL.md#keep-recovered-stock-as-the-default). That step is an **UNTESTED, open release gate**: even if every screen matches the guide, it hasn't been proven. Prefer F12 → Windows and getting help first. If you do run it, stop at the first difference. It only changes which Linux version starts; Windows stays the laptop's default. |
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
- Your **install record** from INSTALL.md (drive identities, the stock Bazzite checksum). Recovery steps compare against it.
- The two USB sticks: **WINDOWS RECOVERY — KEEP** in a drawer, and the installer stick.

## Taking the AresOS SSD out

This is the last step, not the first, and it's rarely needed: [INSTALL §9](INSTALL.md#9-undo-return-to-everyday-windows) shows that the normal undo leaves the SSD in. Remove it only through §9's full procedure. That means backups verified first, Windows starting on its own with its checks passing, and every battery-safety step. **If those checks can't pass, leave the SSD in and get help.** Taking it out doesn't undo every change: firmware boot entries or settings may still need tidying.
