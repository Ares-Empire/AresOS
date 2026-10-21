# The private installation record

Use this page at INSTALL steps 4, 5 and 9. **The inventory is mandatory.** Keep its files and this comparison sheet on another device, outside Git. These commands read disk/firmware information; none partitions, mounts, repairs or changes boot entries. The helper only enables a Windows privilege temporarily in its own process to read firmware, then restores it. Errors mean **stop**, not permission to substitute disk numbers or labels.

## A. Windows: before and after shrinking

Start Windows directly with **F12 → Windows Boot Manager**, with USBs removed. Open **Terminal (Administrator)** → **Windows PowerShell**. Paste this block; at its prompt enter the folder containing AresOS's `README.md`. Use the reviewed repository/release copy, not a downloaded replacement script. If Windows blocks the module, stop for maintainer review; do not change execution policy.

```powershell
$ErrorActionPreference = 'Stop'
$aresRepo = Read-Host 'AresOS folder containing README.md'
Import-Module (Join-Path $aresRepo 'docs\install-tools\InstallRecord.psm1') -Force
$aresRecord = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'AresOS-record'
New-Item -ItemType Directory -Path $aresRecord -Force | Out-Null
if (Test-Path (Join-Path $aresRecord 'before.json')) { throw 'STOP: preserve the existing before.json; do not overwrite it.' }
$before = Get-AresInstallRecord
$before | ConvertTo-Json -Depth 6 | Tee-Object -FilePath (Join-Path $aresRecord 'before.json')
Get-AresShrinkPlan -Before $before | Format-List
```

This prints disk model, serial, GPT disk GUID, bytes and logical sector size; **every** partition's GUID/type and byte/sector endpoints; C: free bytes; and the entry used for **this Windows boot**. The final block computes the proposed Windows size/free space in **GiB** and refuses insufficient headroom **before** shrinking. `Boot.PartitionGuid` must match an EFI partition in `Partitions`, and `LoaderPath` must be `\EFI\Microsoft\Boot\bootmgfw.efi`. The helper checks those conditions. Mark that row **original Windows ESP — KEEP**. Its GUID, not “partition 1”, is the permanent identity.

Save a full Disk Management disk-row screenshot too. **The MSR is deliberately hidden by Disk Management**, so its absence in that screenshot is normal; the command inventory must still include it. `GptType` is a partition's *role*, while `Guid` is its *unique identity*. [Microsoft GPT FAQ](https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/windows-and-gpt-faq?view=windows-11) (checked 2026-10-21).

Copy the `AresOS-record` folder to the independent record device **before shrinking**; disconnect that device before any media writer or installer. Keep this PowerShell window open. After INSTALL step 4 shrinks C:, paste:

```powershell
$after = Get-AresInstallRecord
$donation = @(Get-AresDonation -Before $before -After $after)
$after | ConvertTo-Json -Depth 6 | Tee-Object -FilePath (Join-Path $aresRecord 'after-shrink.json')
$donation | ConvertTo-Json | Tee-Object -FilePath (Join-Path $aresRecord 'allowed-interval.json')
```

The helper checks disk identity, all original partitions, exactly 96 GiB removed from C:'s **end**, Windows boot target and remaining free-space margins. It prints **already calculated inclusive start/end sectors**, both for the allowed interval and the three proposed new partitions. No sector arithmetic is needed. Copy the updated folder off the laptop before continuing.

If the terminal was closed after shrinking, restore the saved baseline with this block, then run the **after** block above. Never recreate “before” after shrinking. If necessary, first restore the `AresOS-record` folder from the independent copy into Documents.

```powershell
$ErrorActionPreference = 'Stop'
$aresRepo = Read-Host 'AresOS folder containing README.md'
Import-Module (Join-Path $aresRepo 'docs\install-tools\InstallRecord.psm1') -Force
$aresRecord = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'AresOS-record'
$before = Get-Content -Raw (Join-Path $aresRecord 'before.json') | ConvertFrom-Json
```

## B. Linux: identify the SSD, its partitions and the free interval

In the legacy installer, press **Ctrl+Alt+F1**, then **Ctrl+B**, release both keys, then **2** to reach the root shell; omit `sudo` there if it is unavailable. **Ctrl+Alt+F6** returns to the graphical installer. This uses the [Anaconda tmux console procedure](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/interactively_installing_rhel_from_installation_media/troubleshooting-at-the-start-of-the-installation_rhel-installer) (checked 2026-10-21), still requiring verification on the qualified ISO. If it does not work, stop. In installed Bazzite use **Konsole**; in GParted Live double-click **Terminal**. These commands do not mount Windows.

```bash
sudo lsblk --bytes --paths --pairs --output NAME,TYPE,SIZE,MODEL,SERIAL,LOG-SEC,PTUUID,PARTUUID,PARTTYPE,FSTYPE,UUID,MOUNTPOINTS
```

Each device is one record of `FIELD="value"` pairs, so long identifiers are not shortened into a screen-width table; lines may wrap. Find the disk whose **model + serial + size + GPT disk GUID (`PTUUID`) + logical sector size (`LOG-SEC`)** match the Windows record. Take its `NAME` (for example `/dev/nvme0n1`; never assume this example is yours). Then paste, typing that whole-disk path at the prompt:

```bash
read -r -p 'Recorded SSD whole-disk path: ' aresDisk
sudo sfdisk --list "$aresDisk"
sudo sfdisk --list-free "$aresDisk"
sudo efibootmgr -v
```

`sfdisk --list` prints each device's **Start, End and Sectors**, with the sector size in the header; `--list-free` does the same for gaps. These options are read-only; **never run bare `sfdisk`**. Match `PARTUUID` from `lsblk` to Windows `Guid` (ignore letter case and surrounding braces). Then use that same device path's `sfdisk` row for boundaries. The disk GUID is not a partition GUID. Filesystem `UUID`, including the **UUID in GParted Information**, is a third, different identifier and cannot replace `PARTUUID`.

Before installation, every Windows row must match `after-shrink.json`. The free interval must match `allowed-interval.json` exactly, even if another gap exists. After installation, record the three new PARTUUIDs and their exact boundaries; require the planned tree from INSTALL §5. In Bazzite also run:

```bash
findmnt --mountpoint /boot/efi --output SOURCE,TARGET,FSTYPE
findmnt --mountpoint /boot --output SOURCE,TARGET,FSTYPE
findmnt --mountpoint / --output SOURCE,TARGET,FSTYPE,OPTIONS
findmnt --mountpoint /var --output SOURCE,TARGET,FSTYPE,OPTIONS
findmnt --mountpoint /var/home --output SOURCE,TARGET,FSTYPE,OPTIONS
```

The EFI source must be the **new** EFI row; root/var/home must use the new Btrfs parent with their respective subvolumes. Save all output privately. On GParted Live, all SSD mountpoint fields must be empty before deleting anything; a mounted SSD partition means stop. Missing commands, blank identifiers, read errors or inconsistent units also mean stop.

## C. One comparison sheet

Copy this sheet into the private record. Add a row for **each** original OEM/recovery/other partition; do not force your machine into the illustration. Fill Linux paths only after matching GUIDs. Paths/partition numbers may change between boots; resolve them anew by GUID each time.

Disk: Windows number ___; model ___; serial ___; size bytes ___; Windows disk `Guid` = Linux `PTUUID` ___; logical sector bytes ___; Linux whole-disk path ___ .

| Role / action | Windows partition / letter | Windows `Guid` = Linux `PARTUUID` | Current Linux device path | Start sector | End sector (inclusive) | Start byte / end byte (exclusive) |
|---|---|---|---|---|---|---|
| Original Windows ESP — KEEP | | | | | | |
| MSR — KEEP | | | | | | |
| C: before shrink — KEEP record | | | | | | |
| C: after shrink — KEEP partition | | | | | | |
| Every original recovery/OEM/other — KEEP | | | | | | |
| Allowed donation (from helper) | — | — | free space before install | | | |
| New AresOS EFI — remove only at undo | | | | | | |
| New AresOS ext4 boot — remove only at undo | | | | | | |
| New AresOS Btrfs — remove only at undo | | | | | | |

Original Windows boot: `Boot####` ___; ESP GUID ___; loader `\EFI\Microsoft\Boot\bootmgfw.efi`; sector bounds ___ . Linux boot: `Boot####` ___; **new** ESP GUID ___; loader path ___ . Recovery USB label/model/size/boot-test date ___; installer USB label/model/size ___ .

## D. Undo: prove the Windows boot you just tested uses the original ESP

After **F12 → Windows Boot Manager** with USBs removed, open **Terminal (Administrator) → Windows PowerShell**. Import the same reviewed module and read the original record (adjust only the repository-folder prompt if it moved):

```powershell
$ErrorActionPreference = 'Stop'
$aresRepo = Read-Host 'AresOS folder containing README.md'
Import-Module (Join-Path $aresRepo 'docs\install-tools\InstallRecord.psm1') -Force
$aresRecord = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'AresOS-record'
$before = Get-Content -Raw (Join-Path $aresRecord 'before.json') | ConvertFrom-Json
$current = Get-AresInstallRecord
Confirm-AresWindowsBoot -Current $current -Original $before
$current | ConvertTo-Json -Depth 6 | Tee-Object -FilePath (Join-Path $aresRecord 'before-undo.json')
'PASS: current Windows firmware entry targets the original ESP and Microsoft loader.'
```

This reads **BootCurrent while Windows is running**, then that exact `Boot####`'s device/file path. A Windows reinstall using the AresOS ESP fails even if Windows starts perfectly. Chainloading from GRUB, an unreadable variable, missing original record, non-GPT/ambiguous path or a different loader also stops undo. Do not replace this check with the entry's displayed name, `BootOrder`, a screenshot of a successful login or an old installation-time record.

Copy `before-undo.json` off-device. Boot the installer USB into GParted Live and repeat B. In `efibootmgr -v`, locate the exact `Entry` saved in `before-undo.json`. Its `HD(...,GPT,<GUID>,...)` must match the **original Windows ESP's PARTUUID** and its `File(...)` must match the saved Microsoft loader path. Match the ESP's sector range using `sfdisk`. The live session's **BootCurrent now describes the USB**, not the Windows boot: use the saved Windows entry. If it disappeared, changed target, or points at **any** AresOS row, **delete nothing**. Only a matching current entry plus the saved successful Windows check permits proceeding to INSTALL §9's separate three-partition deletion review.

## Sources and limits — checked 2026-10-21

[Get-Disk](https://learn.microsoft.com/en-us/powershell/module/storage/get-disk), [Get-Partition](https://learn.microsoft.com/en-us/powershell/module/storage/get-partition), [MSFT_Disk](https://learn.microsoft.com/en-us/windows-hardware/drivers/storage/msft-disk) and [MSFT_Partition](https://learn.microsoft.com/en-us/windows-hardware/drivers/storage/msft-partition) define the Windows fields. [lsblk](https://man7.org/linux/man-pages/man8/lsblk.8.html), [sfdisk](https://man7.org/linux/man-pages/man8/sfdisk.8.html), [findmnt](https://man7.org/linux/man-pages/man8/findmnt.8.html) and [efibootmgr](https://github.com/rhboot/efibootmgr/blob/main/README) define the Linux queries. [UEFI load options / BootCurrent](https://uefi.org/specs/UEFI/2.9_A/03_Boot_Manager.html#load-options), [EDK II device-path definitions](https://github.com/tianocore/edk2/blob/master/MdePkg/Include/Protocol/DevicePath.h), Microsoft's [firmware-variable read](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-getfirmwareenvironmentvariablew) and [temporary privilege adjustment](https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-adjusttokenprivileges) underpin the helper. It imports no firmware-write API.

The helper checks records and the firmware-declared boot target; it does not certify filesystem contents or perform any disk action. Synthetic tests are not a Windows/UEFI or novice installer rehearsal. Those trials remain part of the pre-shrink release gate in [INSTALL](INSTALL.md#maintainer-release-gate).
