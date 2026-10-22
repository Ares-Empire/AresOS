# Same-drive fallback (archived, not authorised)

**Superseded 2026-10-22 by [the own-SSD guide](INSTALL.md).** Preserved from brief 05b, with its original 2026-10-21 source dates and unfinished qualification gates. Following it would resize the protected Windows disk: it requires a new explicit owner decision, a reviewed exception to CLAUDE.md hard rule 1, refreshed sources and its own release qualification. Do not switch to it when the new SSD is missing or an installation check fails.

The instructions below describe that historical proposal.

Checked **2026-10-21**. Owner-operated instructions for the Lenovo LOQ 15IRH8, German Windows 11 Home, one 512 GB SSD, UEFI and Secure Boot off. Exact disk layout and encryption status are still unknown. Agents never perform these actions.

**Do not shrink C: yet.** The hardware image/rebase handoff and installation/media rehearsals are not released. The [maintainer release gate](#maintainer-release-gate) must be completed first. Reading upstream documentation and passing synthetic tests do not qualify a physical installation.

Once released: back up → prepare two USBs → check Windows → record and shrink C: → install Bazzite in that gap → follow the supplied AresOS rebase → test the plain terminal session → check Windows. Read through undo first; keep this guide and the [private comparison sheet](INSTALL-RECORD-SAME-DRIVE.md#c-one-comparison-sheet) available on another device. A mismatch or failed check means **stop before the next write**.

## 1. Back up and preserve a Windows recovery USB

1. Connect AC, save work and finish pending Windows updates/restarts. Back up documents, photos, school files, browser recovery information and game saves **off this SSD**. Open several backed-up files from the independent destination. Recovery media does **not** contain personal-file backups.
2. Prepare **two physically separate sticks**, labelled on the outside:

   | Label | Capacity | Keep / overwrite |
   |---|---|---|
   | **WINDOWS RECOVERY — DO NOT ERASE** | Start with **32 GB**; use a larger stick if the Windows wizard requests it. Its displayed requirement is authoritative. | Preserve throughout install, testing and undo. Never put it in an ISO writer. |
   | **ARESOS INSTALLER — MAY ERASE** | **At least 16 GB**, and large enough for the released ISO. | Expendable; Bazzite now, GParted Live for undo later. |

   32 GB is our preparation allowance, not a promise that every Lenovo recovery image fits. Existing suitable sticks are fine; this guide does not assume the owner already owns both.
3. Disconnect backup disks and the installer stick. In Windows search **Wiederherstellungslaufwerk**, open it and approve its administrator prompt (`recoverydrive.exe` opens the same tool). Select **Systemdateien auf das Wiederherstellungslaufwerk sichern** → **Weiter**. Connect only the labelled recovery stick; check its drive/size → **Weiter → Erstellen → Fertig stellen**. This erases that stick. See [Microsoft's German walkthrough](https://support.microsoft.com/de-de/windows/experience/backup-recovery/recovery-drive).
4. Safely eject and preserve the recovery stick. Test its boot in §2 below, **after** confirming encryption/recovery status and **before** any shrinking.

## 2. Prepare Windows

1. Search `msinfo32`: require **BIOS-Modus: UEFI**, **Sicherer Startzustand: Aus**. Leave Secure Boot off. Do not change keys, TPM, storage-controller mode or boot mode.
2. Start button → right-click → **Terminal (Administrator)** → **Windows PowerShell**. Run:

   ```powershell
   manage-bde -status C:
   ```

   Require **Vollständig entschlüsselt**, **0,0%** encrypted and protection off. Protection off alone can mean suspended encryption; a missing Geräteverschlüsselung settings page proves nothing. If encrypted, suspended, decrypting or unclear: stop and save the matching recovery key independently for a separate owner-reviewed plan. Do not improvise decryption. [W1]
3. Save work, then use this **one primary path** for Fast Startup and hibernation:

   ```powershell
   powercfg /hibernate off
   powercfg /a
   ```

   The first command normally prints nothing on success. The second must list **Ruhezustand** and **Schnellstart** as unavailable because hibernation is disabled (wording varies; look for **Der Ruhezustand wurde nicht aktiviert** or the equivalent reason). An absent Schnellstart checkbox is expected, including when it was already disabled. Errors or an unclear result stop the guide. Restart Windows. Keep both off while dual booting; recheck after major updates. [W2]

   Optional GUI inspection only: **Systemsteuerung → Hardware und Sound → Energieoptionen → Auswählen, was beim Drücken von Netzschaltern geschehen soll → Einige Einstellungen sind momentan nicht verfügbar**. If shown, **Schnellstart aktivieren** must be unchecked. No checkbox hunt is required. Do not open Windows volumes from Linux.
4. **Test the preserved recovery USB now:** restart with that stick connected; repeatedly press **F12** when the power light comes on. Select its UEFI USB entry. Reach Windows Recovery's language/keyboard or **Option auswählen** screen; select the German keyboard if requested. **Do not select recovery/reset/reinstallation.** Choose **PC ausschalten**, unplug the stick, then boot Windows normally. Record the successful boot test and store the stick separately. If it will not boot, stop before shrinking.

## 3. Write and boot the installer USB

Use **Fedora Media Writer's ISO-file route** for both Bazzite and, later, GParted. No ZIP extraction, batch files, Ventoy or alternate writing methods in this guide. Bazzite recommends this writer; its Windows build writes and reads back the image. [B1], [F1]

1. Obtain the **exact official Bazzite legacy ISO and SHA-256 named in the released handoff**, for RTX 4060, KDE, no Steam Gaming Mode. The current hardware family is `bazzite-nvidia-open`; “legacy installer” does not mean the older-GPU `bazzite-nvidia` image. A missing or different ISO stops this route. [B4]
2. Compute its checksum in PowerShell, selecting the actual downloaded file at the prompt:

   ```powershell
   Get-FileHash -Algorithm SHA256 -LiteralPath (Read-Host 'Full path to the downloaded ISO')
   ```

   Compare **all** characters with the official release checksum; stop on a mismatch. Record filename, release and hash. [W6]
3. Keep the **Windows recovery stick and backup devices unplugged**. Connect only **ARESOS INSTALLER — MAY ERASE**. Use the handoff's rehearsed Fedora Media Writer version: **Select .iso file → Next → Select…**; choose the checked file. Under **USB Drive**, verify the stick's model/capacity against its physical label. Before **Write**, confirm the displayed file and USB, and that this entire USB may be erased. Never select the internal SSD. Let writing and verification finish; safely eject. Cancel any Windows prompt to format the written stick. [F1]
4. Test that stick through **F12 → its UEFI USB entry**. Expect the Bazzite installer boot menu, then the legacy language/installation screen. **Do not install yet**; shut down, remove it and return to Windows. Both media boot tests must pass before step 4 below.

## 4. Record the disk and shrink C: in Windows

The proposed donation is **96 GiB = 98304 MB** in Windows' shrink dialog. Leave at least **60 GiB and 15%** of the resulting C: capacity free. These are AresOS planning margins; the reported 168 GB free is not a measurement for this operation.

1. Complete [record A — before](INSTALL-RECORD-SAME-DRIVE.md#a-windows-before-and-after-shrinking), including the **mandatory command inventory**, original Windows ESP/boot target, independent copy and full Disk Management screenshot. Require a **basic GPT** disk. Disk Management hides the MSR; the command record includes it. Identify the SSD by model, serial and GPT disk GUID, not “Disk 0” or size alone.
2. In **Datenträgerverwaltung**, right-click **C: → Volume verkleinern**. Before **Verkleinern**, check C:, **98304 MB**, available shrink space and remaining free-space margins. If Windows offers less, cancel; do not move recovery partitions, disable the pagefile or use a Linux NTFS resizer. [W3]
3. After shrinking, run [record A — after](INSTALL-RECORD-SAME-DRIVE.md#a-windows-before-and-after-shrinking) in the same PowerShell window. It computes the allowed interval and proposed partition endpoints for you and refuses unexpected changes. Save its output off-device. Require a black **Nicht zugeordnet** block immediately to C:'s right; all original small partitions must remain unchanged. Do not create a Windows volume there. [W4]

   ```text
   Before: [Windows EFI] [MSR] [          C:          ] [Recovery]
   After:  [Windows EFI] [MSR] [smaller C:] [96 GiB gap] [Recovery]
   ```

   Illustration only: your original small partitions may differ. Another existing gap is **not** part of this donation.
4. Restart Windows normally, open files and confirm healthy startup. Shut down fully. Only the owner performs this shrink, and the later C: extension, using Windows tools.

## 5. Install Bazzite into that gap

1. Boot the installer USB through F12 in UEFI mode. Select **English (United States)** for the installer interface. In **Keyboard**, add **German**, move it first and test `y z ä ö ü` plus punctuation; choose **Europe/Berlin** for time. These settings make the English labels below usable with the German keyboard. [Legacy welcome/summary screenshots](https://docs.bazzite.gg/General/Installation_Guide/legacy-install/#3-inside-the-installation-medium).
2. Before configuring storage, run [record B's Linux commands](INSTALL-RECORD-SAME-DRIVE.md#b-linux-identify-the-ssd-its-partitions-and-the-free-interval). Match every original partition and the **calculated permitted gap**, including endpoints. If identifiers/console tools are unavailable, stop. Return to the installer.
3. **Installation Destination**: select only the recorded SSD, then **Advanced Custom (Blivet-GUI) → Done**. [Upstream selection screenshot](https://docs.bazzite.gg/img/select_manual_partitioning.png). Select the matching **free space** between the recorded neighbours. Do not use automatic partitioning, reclaim/delete options or a new partition table.

### Create three partitions first

For each row, select **only the remaining free space in the recorded gap**, then **+**. Use **Device type: Partition**, set the fields, then **OK**. The sizes below intentionally differ from upstream's small example.

| Order | Filesystem | Size | Mountpoint | Screen reference |
|---|---|---|---|---|
| 1. New AresOS EFI | EFI System Partition (FAT32) | **1 GiB** | `/boot/efi` | [EFI dialog](https://docs.bazzite.gg/img/efi_partition.png) |
| 2. New AresOS boot | ext4 | **2 GiB** | `/boot` | [boot dialog](https://docs.bazzite.gg/img/boot_partition.png) |
| 3. New system/data parent | btrfs | maximum **remaining donation**, about 93 GiB | **leave blank** | [Btrfs parent dialog](https://docs.bazzite.gg/img/btrfs_partition.png) |

Leave encryption off only for this disposable first trial; keep valuable Linux data off it. No disk swap. Never assign a mountpoint or format flag to any original Windows partition.

### Then create subvolumes inside the new Btrfs parent

Select the **new Btrfs volume**, shown under **Btrfs Volumes** (its generated name may resemble `btrfs.123`), then **+ → Device type: Btrfs Subvolume**. In **Available devices**, select only that new volume. Set **Name: root**, **Mountpoint: /**, then **OK**. Repeat from the **same parent volume** for **var → /var** and **home → /var/home**. Do not select disk free space: the subvolumes share the already-created Btrfs partition. [Root dialog](https://docs.bazzite.gg/img/root_subvolume.png), [var dialog](https://docs.bazzite.gg/img/var_subvolume.png), [home dialog](https://docs.bazzite.gg/img/var_home_subvolume.png).

Expected logical tree (device numbers are deliberately omitted):

```text
Recorded SSD
├─ all original Windows partitions — unchanged, no mountpoints/format flags
└─ exactly the recorded donation
   ├─ new EFI     1 GiB FAT32     /boot/efi
   ├─ new boot    2 GiB ext4      /boot
   └─ new Btrfs  ~93 GiB         no parent mountpoint
      ├─ root                    /
      ├─ var                     /var
      └─ home                    /var/home
```

4. Open **pending actions**, then review **Done → Summary of Changes** **before Accept Changes**. Expect creation of **three partitions**, their EFI/ext4/Btrfs formats, one Btrfs volume and **three subvolumes**, all within the computed interval. The number of action rows can exceed three because creation and formatting are separate. Only the new EFI may be `/boot/efi`; the original Windows ESP must remain unused. **Any original-partition edit, deletion, resize, format, shared EFI, whole-disk operation or unclear target means cancel.** Photograph the tree and full pending list privately. This is the [upstream manual sequence](https://docs.bazzite.gg/General/Installation_Guide/manual_partitioning/); the release must supply matching full-tree/summary screenshots from its exact ISO.
5. **User Creation**: follow the handoff's exact password-protected recovery-administrator username/UID recipe. Do not accept a default `bazzite` password or improvise an `ares` account. Before **Begin Installation**, recheck destination, accepted storage plan, backups and account recipe. Then install on AC. On an error, stop instead of retrying with wider erase options. Reboot, remove USB when prompted, use F12 to choose the new Linux entry (often **Fedora**).

**Secure Boot stays off; no MOK enrollment.** An unexpected enrollment/signature screen is a stop condition. The installer may add a Linux firmware entry/change order; its boot files must go exclusively to the **new** EFI partition. [B3]

## 6. First Bazzite boot and the AresOS rebase

Connect Wi-Fi, test the display and recovery login. Complete [record B/C](INSTALL-RECORD-SAME-DRIVE.md#b-linux-identify-the-ssd-its-partitions-and-the-free-interval): save all three new PARTUUIDs/boundaries, subvolume mounts, new EFI mount and Linux firmware entry. The Windows rows must still match the post-shrink record. Keep these records off-device for undo.

Use **F12 → Windows Boot Manager** and confirm normal Windows startup before continuing. Return to Bazzite and follow the released image verification, retained-deployment, rebase and rollback instructions on AC. A rebase must not repartition anything. Do not install games or optional Bazzite setup features first.

> **ARESOS IMAGE / IMMUTABLE DIGEST / TESTED REBASE + RECOVERY RECIPE: NOT RELEASED.**

If this placeholder remains, the pre-shrink gate is closed. Do not use package 03's raw VM disk or invent a `bootc switch` / `rpm-ostree rebase` command. Image transport/backend/account research belongs in [OS-BASE §8](design/OS-BASE.md#8-install-targets-image-delivery-and-choosing-an-os), not in the owner's installation decisions.

## 7. Early hardware first boot: no Minecraft yet

**Proposed P1a gate, immediately after the image package:** expect a plain **labwc session with a foot terminal**, not the Nether or a normal KDE desktop. Keep this first trial short, on AC, with the lid open; package 03 has no qualified critical-battery handler. Do not test suspend or hibernation.

Record pass/fail, the image digest and relevant output privately:

| Check | What success means |
|---|---|
| NVIDIA | Run `nvidia-smi`: it lists the **RTX 4060** and driver version without driver/communication errors. This checks the driver, not Minecraft rendering. [N1] |
| Screen | Correct native resolution; readable terminal; no flicker, corruption or black screen. Record the resolution and try brightness keys. |
| Wi-Fi | Connect using the handoff's network controls; reach a known website. `nmcli device status` can confirm the interface is connected. Test again after reboot. [N2] |
| Sound | Play a known local sound at low volume using the handoff's audio test, confirm the internal speakers and volume/mute keys. `wpctl status` alone is not an audible test. [N3] |
| Keyboard/touchpad | Type German letters, Y/Z and punctuation; test pointer movement, click, right-click and scrolling. |
| Recovery | Super+Ctrl+Escape opens a terminal. Ctrl+Alt+F3 reaches an authenticated recovery login; the supplied return-to-session steps work. A missing control or tool is a failed gate, not a pass. |
| Restart / Windows | Shut down through the supplied safe control, boot AresOS once more, then F12 → Windows Boot Manager. Test Windows with the installer USB absent and present (select Windows explicitly). Open files and verify its network/sound and disk layout. No unexpected repair or recovery prompt. |

If AresOS fails, use the documented previous-deployment entry or F12 → Windows. Record the failure and stop. Do not reinstall or edit boot files to make the checklist appear green. Only after P1a passes do we build/test the Minecraft milestone **P2**, then the full **P3** trial: Nether → app → save/shutdown → Windows, with restore checks.

## 8. Choosing Windows and handling changed boot order

**F12 is a one-time choice.** To make Windows the default again, first confirm the encryption/recovery checks in step 2 still hold. Remove USBs, restart and press **F2** repeatedly when the power light comes on. On Lenovo's welcome screen select **More Settings → Boot → UEFI**. Select the recorded **Windows Boot Manager**, move it to the top using the on-screen move controls/key legend, then choose **Save and Exit** and confirm saving. Do not guess a move hotkey or reset firmware defaults. [Lenovo setup entry](https://download.lenovo.com/pccbbs/pubs/loq_15_16/html_en/EN/task_start_bios_setup.html), [boot order](https://download.lenovo.com/pccbbs/pubs/loq_15_16/html_en/EN/select_boot_devices.html).

Restart **with no USB and no keys pressed**: Windows must start. Use F12 for AresOS; GRUB still selects Linux rollback deployments. If firmware labels differ, the Windows entry is ambiguous/missing, Windows asks for recovery or Secure Boot has changed, stop with the private record. Do not delete entries, edit BCD, clear TPM or run `bcdboot`/`bootrec` to guess a repair.

## 9. Undo: remove AresOS and return its space to C:

This erases **all Linux data**, including local backups. Export it and open the exported files first. Keep the Windows backup and **WINDOWS RECOVERY — DO NOT ERASE** stick intact. Undo is owner-operated, never an agent action.

1. Boot Windows directly through F12 with USBs removed. Verify normal startup/files and restore Windows as default using step 8. Then run [record D's actual Windows boot-target check](INSTALL-RECORD-SAME-DRIVE.md#d-undo-prove-the-windows-boot-you-just-tested-uses-the-original-esp). It must match the **original Windows ESP's GUID, boundaries and Microsoft loader path**. Windows booting successfully from AresOS storage **fails** this gate. Save the result off-device.
2. Prepare **ARESOS INSTALLER — MAY ERASE** with the handoff's official **GParted Live amd64 `.iso`** from [GParted Downloads](https://gparted.org/download.php). Check its SHA-256 against the official checksum, then repeat **exactly step 3's Fedora Media Writer ISO-file route**, targeting only the expendable stick. **No `.zip` or `makeboot.bat`.** Keep the recovery stick unplugged. The released media rehearsal must cover this ISO too.
3. F12 → UEFI USB. Expect **GParted Live (Default settings)**, then keyboard/language prompts and the GParted desktop. Select a **German** keymap, **US English** interface and the default graphical mode. [Upstream boot/keymap screenshots](https://gparted.org/display-doc.php?name=gparted-live-manual). Do not open/mount Windows volumes.
4. Repeat [record B and the final part of D](INSTALL-RECORD-SAME-DRIVE.md#d-undo-prove-the-windows-boot-you-just-tested-uses-the-original-esp). Recheck the **saved Windows Boot####** GUID/path in the current `efibootmgr -v` output. Its target must survive deletion. Match the SSD and **all three AresOS PARTUUIDs and exact sector bounds** to the post-install sheet, inside the original donation; check every original Windows partition too. Any moved/resized/reused partition, mounted SSD partition, missing record or ambiguity means **stop, delete nothing**.
5. In GParted's top-right device selector, choose that recorded SSD. Select each matched Linux device row → **Partition → Information** to cross-check **First sector / Last sector**. Its filesystem **UUID is not PARTUUID**; use the terminal inventory for the latter. Queue **Delete** for the new Btrfs, ext4 boot and **AresOS EFI** partitions only. [GParted manual](https://gparted.org/display-doc.php?name=help-manual).
6. **Before Apply All Operations**, require exactly those **three deletions**; no Windows edit, resize, move, format, new table or boot repair. Save the preview, then apply. Confirm the recovered unallocated interval matches the donation and is immediately after C:. If it coalesces with another old gap, the extend step must still be limited to the recorded donation. Shut down and remove USB.
7. Boot Windows. **Datenträgerverwaltung → right-click C: → Volume erweitern**. Before **Fertig stellen**, select only the original donated **98304 MB** on the same SSD, directly to C:'s right; verify it restores C:'s recorded original size. Do not accept a larger automatically selected amount. If disabled, separated by a recovery partition, or the recorded amount is unavailable: stop. Never move/delete that partition, convert to dynamic disk or resize NTFS in Linux. [W4]
8. Verify C:'s original size, all original small partitions and a normal Windows restart **with no USB/no keys**. A stale Linux firmware entry can stay unused; later reviewed cleanup may remove only its recorded entry. Never delete or modify `\EFI\Microsoft`, the original Windows ESP or unrecognised boot files.

## Maintainer release gate

**Outside the owner's action sequence.** Before replacing the NOT RELEASED marker and allowing any shrink, deliver:

- One qualified RTX image/base and **exact legacy ISO + SHA-256**, an accessible immutable AresOS image with trust verification, and the tested account/UID, Bazzite→AresOS migration and rollback instructions described in [OS-BASE §8](design/OS-BASE.md#8-install-targets-image-delivery-and-choosing-an-os). Image/rebase implementation remains the OS image package.
- Exact Fedora Media Writer and GParted ISO versions/checksums; an end-to-end rehearsal of **this one writing route** with expendable media, successful UEFI boot of both ISOs, and the required console commands. No physical media writing was performed in brief 05b. Do not describe source inspection as rehearsal evidence.
- A disposable file-backed VM walkthrough: two ESPs, a Windows-like MSR/C:/recovery layout and another unused gap; screenshots of the exact ISO's language/keyboard, Btrfs selection, resulting tree and pending actions. An unaided novice must identify the interval and three targets. Hash protected partition contents and compare GUIDs/boundaries through install and undo. Confirm bootloader writes stay off the Windows ESP, including fallback paths.
- Windows/UEFI trials of the read-only helper, including duplicate labels and Windows deliberately booting from the AresOS ESP (must refuse undo), plus normal original-ESP boot (must pass). Record unavailable-variable failure too. German Windows trials starting with hibernation both enabled and disabled; the owner later verifies the preserved recovery USB and actual Lenovo boot order. These are acceptance trials, not completed results in this documentation package.

The route comparison and reasons for keeping an independent ESP are in [OS-BASE §8](design/OS-BASE.md#8-install-targets-image-delivery-and-choosing-an-os). No shared-ESP fallback is authorised by this guide.

## Sources checked 2026-10-21

Upstream documentation supports the tools and UI references; the 96 GiB layout, margins and stop rules are AresOS proposals. Linked screenshots are **upstream examples**, not screenshots of an AresOS installation. Exact-ISO rehearsal evidence is still required. The [record page](INSTALL-RECORD-SAME-DRIVE.md#sources-and-limits--checked-2026-10-21) lists the inventory/firmware APIs separately.

[B1]: https://docs.bazzite.gg/General/Installation_Guide/install-guide/
[B3]: https://docs.bazzite.gg/General/Installation_Guide/legacy-install/
[B4]: https://docs.bazzite.gg/General/FAQ/
[F1]: https://github.com/FedoraQt/MediaWriter
[W1]: https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/manage-bde-status
[W2]: https://learn.microsoft.com/en-us/windows-hardware/design/device-experiences/powercfg-command-line-options
[W3]: https://learn.microsoft.com/en-us/windows-server/storage/disk-management/shrink-a-basic-volume
[W4]: https://learn.microsoft.com/en-us/windows-server/storage/disk-management/extend-a-basic-volume
[W6]: https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/get-filehash
[N1]: https://docs.nvidia.com/deploy/nvidia-smi/index.html
[N2]: https://networkmanager.dev/docs/api/latest/nmcli.html
[N3]: https://pipewire.pages.freedesktop.org/wireplumber/man/wpctl.html

Writer screen labels were checked against [MainPage](https://github.com/FedoraQt/MediaWriter/blob/main/src/app/qml/MainPage.qml) and [DrivePage](https://github.com/FedoraQt/MediaWriter/blob/main/src/app/qml/DrivePage.qml). Fast Startup's dependence on hibernation is documented by [Microsoft](https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/distinguishing-fast-startup-from-wake-from-hibernation). German output descriptions above are illustrative, not captured laptop output.
