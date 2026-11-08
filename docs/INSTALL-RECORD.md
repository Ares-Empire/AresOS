# Own-SSD installation record

Mandatory companion to [INSTALL](INSTALL.md), checked **2026-10-22**. Keep all output and serial numbers **private, outside Git**, with a copy independent of both internal SSDs. The [archived same-drive record](INSTALL-RECORD-SAME-DRIVE.md) is not used here.

These commands query layout/firmware; they do not partition, mount, repair, format or change boot entries. Saving JSON writes ordinary files; Windows PowerShell's native-code compilation may create temporary files. The helper temporarily enables a process privilege to read firmware and restores it. **The maintainer (Claude) runs the Windows-side commands itself**, explaining impactful actions and obtaining the owner's OK first. The owner handles firmware screens and secrets, and types offline Linux commands with a guiding session. Codex does not run disk or boot tools on the real laptop. Errors mean stop.

**Before B/C/D, write the calling procedure and checklist step beside the record stage.** A stage such as after-aresos does not identify which Linux deployment is now default. The [return-by-calling-context table](#return-by-calling-context) takes precedence over a stage-only return.

## A. Save the Windows baseline

During INSTALL step 1, boot **F12 → Windows Boot Manager**, USBs absent. Open **Terminal (Administrator) → Windows PowerShell**. Use only the reviewed repository copy; if importing is blocked, stop rather than change execution policy.

```powershell
$ErrorActionPreference = 'Stop'
$aresRepo = Read-Host 'AresOS folder containing README.md'
Import-Module (Join-Path $aresRepo 'docs\install-tools\InstallRecord.psm1') -Force
$aresRecord = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'AresOS-own-ssd-record'
New-Item -ItemType Directory -Path $aresRecord -Force | Out-Null
$aresBaseline = Join-Path $aresRecord 'windows-before.json'
if (Test-Path $aresBaseline) { throw 'STOP: preserve the original baseline; do not overwrite it.' }
$before = Get-AresInstallRecord
$before | ConvertTo-Json -Depth 6 | Tee-Object -FilePath $aresBaseline
```

Require the Micron model/serial, a GPT disk GUID, and every Windows partition with GUID/type/start/end. The helper follows C: to its disk and checks this Windows boot targets an EFI partition **on that disk** using `\EFI\Microsoft\Boot\bootmgfw.efi`. Mark that row **original Windows EFI — KEEP**. Blank IDs or a different disk means stop.

Copy the folder off-device before fitting/installing. Disconnect that copy device before any writer/installer. Never regenerate the baseline after a change. A full **Datenträgerverwaltung** screenshot is useful, but its hidden MSR partition is included only in the command inventory. [W1]

**Return to step 1:** [backups/baseline](INSTALL.md#1-backups-recovery-and-windows-preparation). Any error → **STOP → [Help](INSTALL-REFERENCE.md#help)**.

## B. Compare Windows after each stage

Run after SSD fitting, after Bazzite, after AresOS, immediately before undo and after undo. Always start by **direct F12 → Windows Boot Manager**, USBs absent; do not chainload Windows through Linux.

After each reboot, **right-click Start → Terminal (Administrator)**, approve the prompt, then select **Windows PowerShell**. The previous elevated terminal did not survive the reboot. The pre-check below must print `PASS: Administrator terminal.` before any collection; otherwise reopen as instructed and rerun B. [W2]

```powershell
$ErrorActionPreference = 'Stop'
$aresIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
$aresPrincipal = [Security.Principal.WindowsPrincipal]::new($aresIdentity)
if (-not $aresPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'STOP: right-click Start -> Terminal (Administrator), approve the prompt, select Windows PowerShell, then rerun record B.'
}
'PASS: Administrator terminal.'
$aresRepo = Read-Host 'AresOS folder containing README.md'
Import-Module (Join-Path $aresRepo 'docs\install-tools\InstallRecord.psm1') -Force
$aresRecord = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'AresOS-own-ssd-record'
$before = Get-Content -Raw (Join-Path $aresRecord 'windows-before.json') | ConvertFrom-Json
$aresStage = Read-Host 'Stage: after-fit, after-bazzite, after-aresos, before-undo, after-undo'
if ($aresStage -notin 'after-fit','after-bazzite','after-aresos','before-undo','after-undo') {
    throw 'STOP: use one of the listed stage names.'
}
$current = Get-AresInstallRecord
$aresOutput = Join-Path $aresRecord ($aresStage + '-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '.json')
if (Test-Path $aresOutput) { throw 'STOP: preserve the existing stage record.' }
$current | ConvertTo-Json -Depth 6 | Tee-Object -FilePath $aresOutput
Confirm-AresWindowsDiskUnchanged -Before $before -After $current
```

Success prints:

```text
PASS: Windows disk identity, all partition GUIDs/types/boundaries and original Windows boot target match.
```

A comparison failure stops installation/undo: keep the output for review, never replace the baseline to obtain a pass. If collection itself fails, there may be no stage file; preserve the error privately. Copy successful records off-device.

The comparison allows disk/partition numbers, labels, firmware entry number and C: free space to change. It rejects any disk identity/size/sector-size change, partition addition/deletion/type/GUID/boundary change, C: identity change or different Windows boot target. **It does not hash filesystem contents or prove no files changed.** The offline two-disk write audit remains a release requirement.

**Return by caller:** [choose your recorded calling procedure](#return-by-calling-context), including keep-stock; any error → **STOP → [Help](INSTALL-REFERENCE.md#help)**. Never replace the original baseline.

## C. Identify both drives in live Linux

**Before disk commands in Konsole**, fix the live KDE layout: open **Konsole** → type `sudo localectl set-x11-keymap de`. With US still active, each `-` is the key labelled **ß** (right of **0**), `y` is **Z** (between **T** and **U**), and space is the spacebar; no Shift/AltGr. Check the displayed command before Enter. Then physically type `y z / - " $ ä ö ü` in a text editor. **PASS** only if every character matches; otherwise **STOP → [Help](INSTALL-REFERENCE.md#help)**. Repeat after every live boot. System Settings alone did not fix live Wayland typing. This is separate from the installer's target German setting. [Key/source check](INSTALL-REFERENCE.md#live-keyboard-source); after PASS, **Return to this record C**. In installed KDE test typing too; do not improvise layout changes there. In GParted Live choose German at startup and test before **Terminal**. Never click/mount a Windows volume to find commands.

Keep the complete output below. The first command shows relationships; the second retains exact IDs with **PKNAME = parent device**. A narrow window may clip the tree; maximise it and use the complete pairs record for full model/serial/IDs. [L1]

```bash
sudo lsblk --tree --paths --output NAME,TYPE,SIZE,MODEL,SERIAL,MOUNTPOINTS
sudo lsblk --bytes --paths --pairs --output NAME,PKNAME,TYPE,SIZE,MODEL,SERIAL,LOG-SEC,PTUUID,PARTUUID,PARTTYPE,FSTYPE,UUID,MOUNTPOINTS
sudo efibootmgr -v
```

**Example only — invented serials, not this laptop's output.** A line marked `disk` is a whole drive; indented `part` lines belong to the disk above. `p1` means partition 1, not a different SSD. USB/loop devices also appear in real output.

```text
NAME                   TYPE  SIZE  MODEL              SERIAL
/dev/nvme0n1           disk  465G  CT500P310SSD8       EXAMPLE-CRUCIAL  <- new drive
                                  (no child rows: empty layout)
/dev/nvme1n1           disk  477G  MTFDKCD512TFK...    EXAMPLE-MICRON   <- KEEP
├─/dev/nvme1n1p1        part  ...                                    <- Windows EFI: KEEP
├─/dev/nvme1n1p2        part  ...                                    <- MSR: KEEP
├─/dev/nvme1n1p3        part  ...                                    <- Windows: KEEP
└─/dev/nvme1n1p4        part  ...                                    <- recovery: KEEP
```

Partition order/types above are illustrative: use the baseline's GUIDs/types to identify the **actual** EFI/MSR/Windows/recovery rows. For the first install, no child rows alone does not prove a drive contains no data; stop for any filesystem/signature or known prior use as well. Only the bounded failed-install checkpoint below replaces this empty-drive rule.

### Same-session mapping — fill again after every boot

**Micron has two serial forms.** Record A's `Disk.Serial` is Windows' **EUI-64 drive ID**, in the form `xxxx_xxxx_xxxx_xxxx.` (format placeholder, not a real ID). Linux `lsblk` SERIAL is the **printed serial**, so it will not equal that EUI-64. Before the live boot, the maintainer reads it in Windows, read-only:

```powershell
$aresMicron = @(Get-PhysicalDisk | Where-Object FriendlyName -like 'Micron*')
if ($aresMicron.Count -ne 1) { throw 'STOP: Micron identity is ambiguous.' }
$aresMicron | Format-List FriendlyName,SerialNumber,AdapterSerialNumber
Get-Disk | Where-Object { $_.SerialNumber.Trim() -eq $aresMicron[0].SerialNumber.Trim() } | Format-List FriendlyName,SerialNumber,Guid
($aresMicron[0].AdapterSerialNumber -split '_')[0].Trim()
```

Require **exactly one** matching Get-Disk row. **PASS** only when the physical disk's **SerialNumber = record A's Disk.Serial** (trim whitespace), and that matching disk's **Guid = record A's Disk.Guid** (case/braces can differ). This ties `AdapterSerialNumber` to record A. Its part **before `_`, trimmed**, is the printed Micron serial; save it privately beside A without replacing A. Blank/different/ambiguous output → **FAIL — STOP → [Help](INSTALL-REFERENCE.md#help)**. Never open Micron to read its label or mount Windows from Linux.

Identify **Micron by model + printed serial + size + GPT disk GUID (`PTUUID`)**: the printed serial must match the Windows reading above; model, size and GUID must match `windows-before.json`. At the tools' **Windows baseline Micron serial** prompt, use this printed serial, not the EUI-64. Identify Crucial by the model and **printed label serial** in its private **physical-label photograph**, then match both to its live `disk` row and check size. Missing, truncated, different or ambiguous identity means **FAIL — STOP**; neither capacity nor a disk number substitutes for the serial.

Fill this table from the **current** complete output, then the installer opened in **this same session**. Keep a full destination screenshot. Record a new table after reboot or any device change; never carry a device path over from Windows or a previous live boot.

| Physical drive / trusted identity | Live model + serial (exact) | Whole-disk `NAME` where `TYPE="disk"` | Exact **Change destination** entry and device name shown | Result |
|---|---|---|---|---|
| Crucial: photographed model + serial | | | | PASS / FAIL |
| Micron — KEEP: baseline model + printed serial linked to A above | | | Must remain deselected | PASS / FAIL |

The installer may omit the serial and `/dev/`: join its device name to the **same-session** `NAME` (e.g. `nvme0n1` → `/dev/nvme0n1`), then verify its model/size too. Copy the **actual full entry**, not this example. Require a unique match; if the UI hides the device name or disagrees, **Quit**. A partition path such as `/dev/nvme1n1p1` is never a whole-disk destination. [B1]

If Crucial becomes `nvme1n1` next boot, its matching label/model/serial makes **that** the new target; all Micron children remain protected whichever number they get. In GParted, fill the entry column from its device selector instead; in installed KDE without a selector, mark that column **not applicable**, never reuse an old destination check.

Read each whole-disk `NAME` from this output; paths and numbering can change on every boot. To display exact partition sector bounds, run this block once for Micron, and again for Crucial after installation:

```bash
read -r -p 'Identified whole-disk path (from lsblk): ' aresDisk
sudo sfdisk --list "$aresDisk"
```

Only `sfdisk --list` is used; never bare `sfdisk`. Match Windows disk `Guid` to `PTUUID`, partition `Guid` to `PARTUUID`, and `GptType` to `PARTTYPE` (case/braces can differ). Match the helper's **StartSector / EndSector**, inclusive, against `sfdisk` **Start / End**, with the same sector size. The filesystem `UUID` is a different identifier. Use the private sheet below, including one row per Micron partition, and record each result. [L1]

### PASS/FAIL checkpoints

These are **manual results** from the saved output and visible plan; the automatic Windows comparison is in B. Mark PASS only after completing the check, otherwise **FAIL — STOP / Quit**, including unreadable or uncertain output. Preserve the detailed evidence. No PASS here proves the installer cannot write elsewhere; the two-disk release audit is still required.

| When / check | PASS only when | FAIL examples — do not continue |
|---|---|---|
| Every Linux session: **identity** | Both mapping rows match their trusted identity; current whole-disk paths are recorded, even after renumbering. | Crucial chosen by 465 GiB alone; copied old path; serial mismatch. |
| Every Linux session: **Micron unchanged** | Printed serial matches the Windows reading tied to A above; disk model/byte-size/PTUUID/sector-size and **every** partition's GUID/type/start/end match the original baseline, with no extra/missing rows. All Micron `MOUNTPOINTS` are empty (including no `[SWAP]`). | Changed/missing MSR or recovery; a Micron partition mounted; any unreadable field. |
| **Before first installation only: Crucial empty** | Matched Crucial has **zero partition children**, empty FSTYPE/UUID and no mounts, unknown data or prior use. A factory-empty drive may lack PTUUID. | Even one child partition, including a small EFI partition, or any filesystem signature: stop; do not erase to make this pass. |
| **Failed first install, before tools installation only: Crucial reinstall** | Same label-identified Crucial holds **only the failed install's EFI, boot and system partitions, nothing else**, matched to its saved plan/records; no mounts. Micron unchanged/unmounted still passes. [Return to step 4, box 1](INSTALL.md#4-install-and-prepare-corrected-stock), then **Use entire disk** on **Crucial only**. | Anything else on Crucial, missing records, uncertainty or tools already installed → **STOP**, no erasure under this exception. |
| **Before Erase data and install: installer plan** | Exact destination entry maps only to current Crucial; **every** proposed storage action is on Crucial, with its **own new EFI** at `/boot/efi`, boot and system. | Any proposed write, format, delete, resize, mount or EFI reuse on **Micron or any of its children**, even if Crucial is also selected; missing EFI or unclear path. |
| After installation: **Linux on Crucial** | The mount sources and Linux EFI GUID checked below all resolve to the recorded Crucial partitions. | `/boot/efi` or any Linux storage resolves to Micron, or a mount/EFI identity is unclear. |

In the example tree, a plan to use `nvme1n1p1` for `/boot/efi` is **FAIL — Micron EFI**, even if its label says Fedora. A plan using `nvme0n1` is only eligible for PASS after all other pre-install checks pass. After installation, expected Crucial partitions are checked against their saved record; the first-install **empty** test no longer applies.

After installing, save Crucial's new PTUUID and **every** partition's PARTUUID/type/bounds in the sheet below. In installed Bazzite also run:

```bash
findmnt --mountpoint /boot/efi --output SOURCE,TARGET,FSTYPE
findmnt --mountpoint /boot --output SOURCE,TARGET,FSTYPE
findmnt --mountpoint / --output SOURCE,TARGET,FSTYPE,OPTIONS
```

Match sources back to `lsblk`: EFI, boot and system must all be on Crucial. In `efibootmgr -v`, require the Linux entry's `HD(...,GPT,<GUID>,...)` to name Crucial's new EFI PARTUUID. Save its Boot####, loader path and the Windows entry; do not alter them. Save complete output privately (photographs/full copied lines, not truncated tables). The live USB's **BootCurrent identifies the USB**, not the earlier Windows boot. [L1], [U1]

### Private comparison sheet

Write **PASS** or **FAIL** beside each required comparison; any blank/FAIL blocks that stage. For newly created Crucial IDs, write **recorded after install** when first saved, then compare them at later checks. Keep the complete command output alongside this summary.

| Record | Original / first saved | After / current | Result |
|---|---|---|---|
| Micron model, EUI-64 from A, linked printed serial, size bytes, GPT GUID, logical sector bytes | | Compare each serial only to its own form; other fields must match A | |
| Each Micron partition: GUID, type, start/end sectors (**one row per partition**) | | Must match | |
| Windows EFI GUID/bounds and Microsoft loader path | | Must match | |
| Crucial label/model, serial, size bytes | | Must match | |
| Crucial GPT GUID (blank permitted only before first install) | | | |
| Every Crucial partition: PARTUUID, type, start/end sectors | | | |
| Linux entry Boot####, EFI PARTUUID, loader path | — | | |
| Corrected pinned stock: full checksum, serial, stateroot (`osname`), image reference/digest | After initial repair/pin | Same saved identity at recovery checkpoints | |
| Installer keyboard layout (backup keeps this even after an AresOS layout change) | | Backup password uses this layout | |
| Stock BLS resolved deployment path and exact title; transaction state/time; valid or provisional | | Refresh after each reorder, before reboot | |
| Direct Windows boot entry from latest before-undo JSON | — | | |
| Recovery USB model/label/boot-test date | | | |
| Installer USB model/label; writer/ISO versions and SHA-256 | | | |

### Recovery-title history — refresh before every affected reboot

Keep the complete output from INSTALL's
[stock-title checkpoint](INSTALL.md#5-prove-windows-and-corrected-stock).
Resolve the BLS target by the saved corrected stock **checksum, serial and
stateroot**, then copy that file's exact title. A checksum alone cannot separate
the two pre-finalization stock serials. Never infer a title from JSON row count
or a BLS filename.

**Any deployment reorder immediately invalidates the previous title**, including
pending-update cleanup, switch staging, queued rollback and set-default. Mark
each superseded row INVALID and fill a new row **before rebooting**. If no fresh
record is available, use F12 → Windows and get help, even if the old title still
appears in GRUB. A first-switch staged title is provisional and cannot be used
for recovery; confirm the final pair after the first successful AresOS boot.

| Checkpoint / time | Saved stock checksum + serial + stateroot | Resolved BLS target and exact title | Validity / previous title invalidated |
| --- | --- | --- | --- |
| Initial repair/pin; repeat after any pending cleanup | | | Pre-switch only |
| Switch staged, before reboot | | | Provisional; not first-switch recovery |
| First successful AresOS boot, final pair confirmed | | | |
| Rollback queued, **before** reboot | | | |
| Set-default completed, **before** reboot | | | |
| After each recovery/default boot, confirm again | | | |
| Any later reorder (new row per event) | | | |

Record the **installer layout separately from the current AresOS layout**.
Backup Bazzite keeps the former; type its recovery password with that layout.
The VM restored German before rollback; US-then-rollback was not performed.

**Return by caller:** [choose your recorded calling procedure](#return-by-calling-context), including keep-stock. Any blank/FAIL → **STOP → [Help](INSTALL-REFERENCE.md#help)**.

## D. Before erasing Crucial from live media

First complete INSTALL step 9's token retirement and successful direct Windows boot and record B (**before-undo**); keep that exact timestamped JSON independently. In live GParted repeat C, requiring **both internal disks unmounted** and every recorded Crucial partition/boundary still accounted for. Unknown additional partitions/data mean stop.

Find the **Boot.Entry saved by that Windows session** in current `efibootmgr -v`. Its GPT partition GUID and `File(...)` must still identify the original Micron EFI and `\EFI\Microsoft\Boot\bootmgfw.efi`. Locate that GUID's device with `lsblk`, then compare its `sfdisk` Start/End with the saved Boot.StartSector/EndSector. Do not mistake `HD(...)`'s hexadecimal start/size for decimal start/end; no conversion is required using the partition listing. The live USB's BootCurrent is not evidence about Windows. A missing/changed target, ambiguous path, Windows booting from Crucial, missing baseline or changed layout means **erase nothing**. Only a separately authorized erasure caller performs D; after PASS, use the calling-context return below.

**Return by caller:** [choose your recorded calling procedure](#return-by-calling-context), including keep-stock if that caller was retained. **STOP → [Help](INSTALL-REFERENCE.md#help)** on any failure.

## Return by calling context

Use your **calling procedure first**, then its stage. Do not use an installation-stage return while completing keep-stock. Unknown/missing caller → **STOP → [Help](INSTALL-REFERENCE.md#help)**; recover that context before continuing. For B, C and D, use the same table:

| Recorded calling context | Return after successful record | Next checkpoint |
| --- | --- | --- |
| keep-stock | [Return to keep-stock completion](INSTALL-PROCEDURES.md#keep-stock-records-complete) | Confirm stock-default and Windows records, then Return to step 8. |
| everyday boot-order restoration | [Return to step 8](INSTALL.md#8-everyday-boot-and-recovery) | Confirm unattended Windows and record B, then continue everyday boot/recovery. |
| initial after-fit | [Return to step 3](INSTALL.md#3-fit-and-identify-both-drives) | Continue only the fitting comparison. |
| initial first after-bazzite | [Return to step 4](INSTALL.md#4-install-and-prepare-corrected-stock) | Complete the tools round trip. |
| initial prepared after-bazzite | [Return to step 5](INSTALL.md#5-prove-windows-and-corrected-stock) | Mandatory Windows/corrected-stock proof. |
| initial live mapping | [Return to step 4](INSTALL.md#4-install-and-prepare-corrected-stock) | Same-session installer plan. |
| initial after-aresos | [Return to step 7](INSTALL.md#7-check-the-first-aresos-session) | Initial AresOS check only. |
| undo erasure | [Return to the erasure procedure](INSTALL-PROCEDURES.md#optional-removal-or-erasure) | Complete only separately authorized erasure, then Return to step 9. |
| undo Windows confirmation | [Return to step 9](INSTALL.md#9-retire-access-and-return-to-windows) | Final independent Windows proof. |

## Sources and limits

Checked **2026-10-22** for this revision. No real disk/firmware query, installation or USB write was performed. Hardware and novice trials remain [release gates](INSTALL-STATUS.md#current-gates).

- **W1:** Microsoft [Get-Disk](https://learn.microsoft.com/en-us/powershell/module/storage/get-disk), [Get-Partition](https://learn.microsoft.com/en-us/powershell/module/storage/get-partition), [MSFT_Disk](https://learn.microsoft.com/en-us/windows-hardware/drivers/storage/msft-disk), [MSFT_Partition](https://learn.microsoft.com/en-us/windows-hardware/drivers/storage/msft-partition) and [GPT FAQ / hidden MSR](https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/windows-and-gpt-faq?view=windows-11).
- **W2:** Microsoft [WindowsPrincipal.IsInRole](https://learn.microsoft.com/en-us/dotnet/api/system.security.principal.windowsprincipal.isinrole), checked 2026-10-22: Administrator role check uses the current token; an unelevated UAC token returns false without prompting for elevation.
- **L1:** util-linux [lsblk](https://github.com/util-linux/util-linux/blob/master/lsblk-cmd/lsblk.8.adoc), [sfdisk](https://github.com/util-linux/util-linux/blob/master/disk-utils/sfdisk.8.adoc), [findmnt](https://github.com/util-linux/util-linux/blob/master/misc-utils/findmnt.8.adoc); [efibootmgr README](https://github.com/rhboot/efibootmgr/blob/main/README).
- **B1:** Bazzite's upstream [destination](https://docs.bazzite.gg/img/live-installer-drive.png) and [review](https://docs.bazzite.gg/img/live-installer-partitions.png) examples, inspected 2026-10-22: model/device-name destination and partition rows. These show `vda` in a VM; the physical NVMe/two-drive mapping remains a release trial, not a claimed screenshot from this laptop.
- **U1:** [UEFI BootCurrent/load options](https://uefi.org/specs/UEFI/2.9_A/03_Boot_Manager.html#load-options), [EDK II device paths](https://github.com/tianocore/edk2/blob/master/MdePkg/Include/Protocol/DevicePath.h); Microsoft [firmware read](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-getfirmwareenvironmentvariablew), [temporary process privilege](https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-adjusttokenprivileges). The existing native reader is unchanged and imports no firmware setter.

[W1]: https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/windows-and-gpt-faq?view=windows-11
[W2]: https://learn.microsoft.com/en-us/dotnet/api/system.security.principal.windowsprincipal.isinrole
[L1]: https://github.com/util-linux/util-linux
[B1]: https://docs.bazzite.gg/img/live-installer-drive.png
[U1]: https://uefi.org/specs/UEFI/2.9_A/03_Boot_Manager.html#load-options

**Return to step 1:** [start/checklist](INSTALL.md#1-backups-recovery-and-windows-preparation).
