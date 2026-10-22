# Owner-operated, read-only inventory. Importing this module performs no hardware reads.
Set-StrictMode -Version Latest

function ConvertFrom-AresBootEntry {
    param([byte[]]$Bytes, [string]$Entry)
    if ($Bytes.Length -lt 8) { throw 'STOP: truncated EFI load option.' }
    $pathLength = [BitConverter]::ToUInt16($Bytes, 4)
    $position = 6
    while ($position + 1 -lt $Bytes.Length -and [BitConverter]::ToUInt16($Bytes, $position) -ne 0) {
        $position += 2
    }
    if ($position + 1 -ge $Bytes.Length) { throw 'STOP: unterminated EFI description.' }
    $description = [Text.Encoding]::Unicode.GetString($Bytes, 6, $position - 6)
    $position += 2
    $pathEnd = $position + $pathLength
    if ($pathEnd -gt $Bytes.Length) { throw 'STOP: truncated EFI device path.' }
    $diskNode = $null
    $loader = $null
    $ended = $false
    while ($position -lt $pathEnd) {
        if ($position + 4 -gt $pathEnd) { throw 'STOP: truncated EFI node.' }
        $kind = $Bytes[$position]
        $subtype = $Bytes[$position + 1]
        $length = [BitConverter]::ToUInt16($Bytes, $position + 2)
        if ($length -lt 4 -or $position + $length -gt $pathEnd) { throw 'STOP: invalid EFI node length.' }
        if ($kind -eq 4 -and $subtype -eq 1) {
            if ($null -ne $diskNode -or $length -ne 42 -or $Bytes[$position + 40] -ne 2 -or $Bytes[$position + 41] -ne 2) {
                throw 'STOP: boot target is not one unambiguous GPT partition.'
            }
            $diskNode = [pscustomobject]@{
                PartitionGuid = [guid]::new([byte[]]$Bytes[($position + 24)..($position + 39)]).ToString()
                StartSector = [BitConverter]::ToUInt64($Bytes, $position + 8)
                SizeSectors = [BitConverter]::ToUInt64($Bytes, $position + 16)
            }
        } elseif ($kind -eq 4 -and $subtype -eq 4) {
            if ($null -ne $loader -or $length -lt 6 -or $length % 2 -ne 0 -or
                [BitConverter]::ToUInt16($Bytes, $position + $length - 2) -ne 0) {
                throw 'STOP: ambiguous or invalid EFI file path.'
            }
            $loader = [Text.Encoding]::Unicode.GetString($Bytes, $position + 4, $length - 6)
            if ($loader.Contains([char]0)) { throw 'STOP: embedded terminator in EFI file path.' }
        } elseif ($kind -eq 127) {
            if ($subtype -ne 255 -or $length -ne 4 -or $position + $length -ne $pathEnd) {
                throw 'STOP: multiple or malformed EFI device paths.'
            }
            $ended = $true
        } elseif ($kind -notin 1, 2, 3) {
            throw 'STOP: unsupported EFI device path; request a read-only review.'
        }
        $position += $length
    }
    if (-not $ended -or $null -eq $diskNode -or $null -eq $loader -or $diskNode.SizeSectors -eq 0) {
        throw 'STOP: incomplete GPT/file boot target.'
    }
    [pscustomobject]@{
        Entry = $Entry
        Description = $description
        PartitionGuid = $diskNode.PartitionGuid
        LoaderPath = $loader
        StartSector = $diskNode.StartSector
        EndSector = [decimal]$diskNode.StartSector + $diskNode.SizeSectors - 1
    }
}

function Get-AresCurrentBoot {
    # Windows requires this process privilege even for firmware-variable reads.
    # Restore its previous state immediately; no firmware setter is imported.
    if (-not ('AresFirmwareReader' -as [type])) {
        Add-Type -TypeDefinition @'
using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
public static class AresFirmwareReader {
    [StructLayout(LayoutKind.Sequential)] struct Luid { public uint Low; public int High; }
    [StructLayout(LayoutKind.Sequential)] struct Privileges { public uint Count; public Luid Id; public uint Attributes; }
    [DllImport("kernel32.dll")] static extern IntPtr GetCurrentProcess();
    [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr handle);
    [DllImport("advapi32.dll", SetLastError=true)] static extern bool OpenProcessToken(IntPtr process, uint access, out IntPtr token);
    [DllImport("advapi32.dll", CharSet=CharSet.Unicode, SetLastError=true)] static extern bool LookupPrivilegeValue(string system, string name, out Luid id);
    [DllImport("advapi32.dll", SetLastError=true)] static extern bool AdjustTokenPrivileges(IntPtr token, bool all, ref Privileges value, uint size, out Privileges previous, out uint required);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)] static extern uint GetFirmwareEnvironmentVariable(string name, string guid, byte[] bytes, uint size);
    public static byte[] Read(string name) {
        IntPtr token;
        if (!OpenProcessToken(GetCurrentProcess(), 0x28, out token)) throw new Win32Exception();
        Privileges previous = new Privileges();
        bool changed = false;
        try {
            Luid id;
            if (!LookupPrivilegeValue(null, "SeSystemEnvironmentPrivilege", out id)) throw new Win32Exception();
            Privileges requested = new Privileges { Count = 1, Id = id, Attributes = 2 };
            uint required;
            bool adjusted = AdjustTokenPrivileges(token, false, ref requested, (uint)Marshal.SizeOf(typeof(Privileges)), out previous, out required);
            int error = Marshal.GetLastWin32Error();
            changed = adjusted;
            if (!adjusted || error != 0) throw new Win32Exception(error);
            byte[] bytes = new byte[65536];
            uint length = GetFirmwareEnvironmentVariable(name, "{8be4df61-93ca-11d2-aa0d-00e098032b8c}", bytes, (uint)bytes.Length);
            if (length == 0) throw new Win32Exception();
            Array.Resize(ref bytes, (int)length);
            return bytes;
        } finally {
            try {
                if (changed) {
                    Privileges ignored; uint required;
                    if (!AdjustTokenPrivileges(token, false, ref previous, (uint)Marshal.SizeOf(typeof(Privileges)), out ignored, out required)) throw new Win32Exception();
                }
            } finally { CloseHandle(token); }
        }
    }
}
'@
    }
    $current = [AresFirmwareReader]::Read('BootCurrent')
    if ($current.Length -ne 2) { throw 'STOP: invalid BootCurrent.' }
    $entry = 'Boot{0:X4}' -f [BitConverter]::ToUInt16($current, 0)
    ConvertFrom-AresBootEntry -Bytes ([AresFirmwareReader]::Read($entry)) -Entry $entry
}

function Get-AresInstallRecord {
    $ErrorActionPreference = 'Stop'
    $c = Get-Partition -DriveLetter C
    $disk = Get-Disk -Number $c.DiskNumber
    if ($disk.PartitionStyle -ne 'GPT' -or -not $disk.Guid -or -not $disk.SerialNumber) {
        throw 'STOP: require an identifiable basic GPT disk.'
    }
    $sector = [decimal]$disk.LogicalSectorSize
    if ($sector -notin 512, 4096) { throw 'STOP: unexpected logical sector size.' }
    $partitions = @(Get-Partition -DiskNumber $disk.Number | Sort-Object Offset | ForEach-Object {
        if (-not $_.Guid -or $_.Offset % $sector -ne 0 -or $_.Size % $sector -ne 0) {
            throw 'STOP: missing partition GUID or unaligned partition.'
        }
        [pscustomobject]@{
            WindowsPartition = $_.PartitionNumber
            DriveLetter = [string]$_.DriveLetter
            Guid = ([guid]$_.Guid).ToString()
            GptType = ([guid]$_.GptType).ToString()
            StartByte = [decimal]$_.Offset
            EndByteExclusive = [decimal]$_.Offset + $_.Size
            SizeBytes = [decimal]$_.Size
            StartSector = [decimal]$_.Offset / $sector
            EndSector = ([decimal]$_.Offset + $_.Size) / $sector - 1
        }
    })
    $record = [pscustomobject]@{
        Disk = [pscustomobject]@{
            WindowsNumber = $disk.Number; Model = $disk.FriendlyName
            Serial = $disk.SerialNumber.Trim(); Guid = ([guid]$disk.Guid).ToString()
            SizeBytes = [decimal]$disk.Size; LogicalSectorBytes = $sector
        }
        CFreeBytes = [decimal](Get-Volume -DriveLetter C).SizeRemaining
        Partitions = $partitions
        Boot = Get-AresCurrentBoot
    }
    Confirm-AresWindowsBoot -Current $record -Original $record
    $record
}

function Confirm-AresWindowsBoot {
    param($Current, $Original)
    $boot = $Current.Boot
    $matches = @($Current.Partitions | Where-Object Guid -eq $boot.PartitionGuid)
    if ($Current.Disk.Guid -ne $Original.Disk.Guid -or $Current.Disk.Serial -ne $Original.Disk.Serial -or
        $boot.PartitionGuid -ne $Original.Boot.PartitionGuid -or
        $boot.LoaderPath -ine '\EFI\Microsoft\Boot\bootmgfw.efi' -or $matches.Count -ne 1) {
        throw 'STOP: tested Windows boot does not target the original Windows ESP and Microsoft loader.'
    }
    $esp = $matches[0]
    if ($esp.GptType -ne 'c12a7328-f81f-11d2-ba4b-00a0c93ec93b' -or
        $esp.StartSector -ne $boot.StartSector -or $esp.EndSector -ne $boot.EndSector -or
        $boot.StartSector -ne $Original.Boot.StartSector -or $boot.EndSector -ne $Original.Boot.EndSector) {
        throw 'STOP: boot target boundaries/type differ from the original Windows ESP.'
    }
}

function Get-AresDonation {
    param($Before, $After)
    foreach ($field in 'Model', 'Serial', 'Guid', 'SizeBytes', 'LogicalSectorBytes') {
        if ($Before.Disk.$field -ne $After.Disk.$field) { throw "STOP: disk $field changed." }
    }
    $oldC = @($Before.Partitions | Where-Object DriveLetter -eq C)
    $newC = @($After.Partitions | Where-Object DriveLetter -eq C)
    if ($oldC.Count -ne 1 -or $newC.Count -ne 1 -or $Before.Partitions.Count -ne $After.Partitions.Count) {
        throw 'STOP: unexpected partition count or C: identity.'
    }
    $oldC = $oldC[0]; $newC = $newC[0]
    foreach ($old in $Before.Partitions) {
        $match = @($After.Partitions | Where-Object Guid -eq $old.Guid)
        if ($match.Count -ne 1 -or $match[0].StartByte -ne $old.StartByte -or $match[0].GptType -ne $old.GptType -or
            ($old.Guid -ne $oldC.Guid -and $match[0].SizeBytes -ne $old.SizeBytes)) {
            throw 'STOP: an original partition changed unexpectedly.'
        }
    }
    $start = [decimal]$newC.EndByteExclusive
    $end = [decimal]$oldC.EndByteExclusive
    if ($oldC.Guid -ne $newC.Guid -or $end - $start -ne 96GB -or $start % 1MB -ne 0 -or $end % 1MB -ne 0) {
        throw 'STOP: C: did not donate exactly the aligned 96 GiB interval.'
    }
    if ($After.CFreeBytes -lt 60GB -or $After.CFreeBytes -lt $newC.SizeBytes * 0.15) {
        throw 'STOP: Windows free-space margin failed.'
    }
    Confirm-AresWindowsBoot -Current $After -Original $Before
    $sector = [decimal]$After.Disk.LogicalSectorBytes
    foreach ($row in @(
        @('Allowed interval', $start, $end),
        @('New EFI', $start, ($start + 1GB)),
        @('New boot', ($start + 1GB), ($start + 3GB)),
        @('New Btrfs', ($start + 3GB), $end)
    )) {
        [pscustomobject]@{
            Role = $row[0]; StartByte = $row[1]; EndByteExclusive = $row[2]
            StartSector = $row[1] / $sector; EndSector = $row[2] / $sector - 1
        }
    }
}

function Get-AresShrinkPlan {
    param($Before)
    $c = @($Before.Partitions | Where-Object DriveLetter -eq C)
    if ($c.Count -ne 1) { throw 'STOP: C: identity is ambiguous.' }
    $sizeAfter = [decimal]$c[0].SizeBytes - 96GB
    $freeAfter = [decimal]$Before.CFreeBytes - 96GB
    $minimum = [Math]::Max([decimal]60GB, $sizeAfter * [decimal]0.15)
    if ($sizeAfter -le 0 -or $freeAfter -lt $minimum) { throw 'STOP: the planned shrink fails the Windows free-space margin.' }
    [pscustomobject]@{
        ShrinkDialogMB = 98304
        ProjectedCSizeGiB = $sizeAfter / 1GB
        ProjectedCFreeGiB = $freeAfter / 1GB
        MinimumCFreeGiB = $minimum / 1GB
    }
}

function Confirm-AresWindowsDiskUnchanged {
    param($Before, $After)
    # Compare saved records only. Windows disk/partition numbers and free space
    # can change between normal boots; GUIDs and geometry must not.
    foreach ($record in $Before, $After) {
        if ($null -eq $record) { throw 'STOP: missing Windows disk record.' }
        foreach ($field in 'Disk', 'Partitions', 'Boot') {
            if (-not $record.PSObject.Properties[$field] -or $null -eq $record.$field) {
                throw "STOP: missing record field $field."
            }
        }
        foreach ($field in 'Model', 'Serial', 'Guid', 'SizeBytes', 'LogicalSectorBytes') {
            if (-not $record.Disk.PSObject.Properties[$field] -or
                [string]::IsNullOrWhiteSpace([string]$record.Disk.$field)) {
                throw "STOP: missing disk field $field."
            }
        }
        $diskGuid = [guid]::Empty
        if (-not [guid]::TryParse([string]$record.Disk.Guid, [ref]$diskGuid) -or $diskGuid -eq [guid]::Empty -or
            $record.Disk.LogicalSectorBytes -notin 512, 4096 -or $record.Disk.SizeBytes -le 0) {
            throw 'STOP: invalid disk identity or geometry.'
        }
        $seen = @{}
        $end = [decimal]0
        foreach ($p in @($record.Partitions | Sort-Object StartByte)) {
            foreach ($field in 'Guid', 'GptType', 'DriveLetter', 'StartByte', 'EndByteExclusive', 'SizeBytes', 'StartSector', 'EndSector') {
                if (-not $p.PSObject.Properties[$field] -or $null -eq $p.$field) {
                    throw "STOP: missing partition field $field."
                }
            }
            $id = [guid]::Empty; $type = [guid]::Empty
            if (-not [guid]::TryParse([string]$p.Guid, [ref]$id) -or $id -eq [guid]::Empty -or
                -not [guid]::TryParse([string]$p.GptType, [ref]$type) -or $type -eq [guid]::Empty -or $seen.ContainsKey($id)) {
                throw 'STOP: invalid or duplicate partition GUID/type.'
            }
            $seen[$id] = $true
            $sector = [decimal]$record.Disk.LogicalSectorBytes
            if ($p.SizeBytes -le 0 -or $p.StartByte -lt $end -or $p.StartByte % $sector -ne 0 -or
                $p.SizeBytes % $sector -ne 0 -or $p.EndByteExclusive -gt $record.Disk.SizeBytes -or
                $p.EndByteExclusive -ne ([decimal]$p.StartByte + $p.SizeBytes) -or
                $p.StartSector -ne ([decimal]$p.StartByte / $sector) -or
                $p.EndSector -ne ([decimal]$p.EndByteExclusive / $sector - 1)) {
                throw 'STOP: inconsistent partition geometry.'
            }
            $end = [decimal]$p.EndByteExclusive
        }
        if (@($record.Partitions | Where-Object DriveLetter -eq C).Count -ne 1) {
            throw 'STOP: require exactly one C: partition in the Windows record.'
        }
        foreach ($field in 'PartitionGuid', 'LoaderPath', 'StartSector', 'EndSector') {
            if (-not $record.Boot.PSObject.Properties[$field] -or
                [string]::IsNullOrWhiteSpace([string]$record.Boot.$field)) {
                throw "STOP: missing boot field $field."
            }
        }
        Confirm-AresWindowsBoot -Current $record -Original $record
    }
    foreach ($field in 'Model', 'Serial', 'Guid', 'SizeBytes', 'LogicalSectorBytes') {
        if ($Before.Disk.$field -ne $After.Disk.$field) { throw "STOP: Windows disk $field changed." }
    }
    if (@($Before.Partitions).Count -ne @($After.Partitions).Count) {
        throw 'STOP: Windows partition count changed.'
    }
    foreach ($old in $Before.Partitions) {
        $match = @($After.Partitions | Where-Object Guid -eq $old.Guid)
        if ($match.Count -ne 1) { throw 'STOP: Windows partition GUID changed.' }
        foreach ($field in 'GptType', 'StartByte', 'EndByteExclusive', 'SizeBytes', 'StartSector', 'EndSector') {
            if ($old.$field -ne $match[0].$field) { throw "STOP: Windows partition $($old.Guid) $field changed." }
        }
        if (($old.DriveLetter -eq 'C') -ne ($match[0].DriveLetter -eq 'C')) {
            throw 'STOP: C: partition identity changed.'
        }
    }
    Confirm-AresWindowsBoot -Current $After -Original $Before
    'PASS: Windows disk identity, all partition GUIDs/types/boundaries and original Windows boot target match.'
}

Export-ModuleMember -Function Get-AresInstallRecord, Get-AresDonation, Confirm-AresWindowsBoot, Get-AresShrinkPlan, Confirm-AresWindowsDiskUnchanged
