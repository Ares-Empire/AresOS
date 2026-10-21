# Synthetic records only. No disk cmdlet or firmware API is invoked.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$modulePath = Join-Path $PSScriptRoot '../../docs/install-tools/InstallRecord.psm1'
Import-Module $modulePath -Force
$module = Get-Module InstallRecord
$script:passed = 0
function Check($Name, [scriptblock]$Run) {
    & $Run
    $script:passed++
    Write-Output "PASS: $Name"
}
function Equal($Actual, $Expected) {
    if ($Actual -ne $Expected) { throw "Expected [$Expected], got [$Actual]" }
}
function Reject([scriptblock]$Run) {
    $rejected = $false
    try { & $Run | Out-Null } catch { if ($_.Exception.Message -notlike '*STOP:*') { throw }; $rejected = $true }
    if (-not $rejected) { throw 'Unsafe input was accepted.' }
}
function Copy-Record($Value) { $Value | ConvertTo-Json -Depth 10 | ConvertFrom-Json }
function Partition($Number, $Letter, $Guid, $Type, $Offset, $Size, $Sector) {
    [pscustomobject]@{
        WindowsPartition = $Number; DriveLetter = $Letter; Guid = $Guid; GptType = $Type
        StartByte = [decimal]$Offset; EndByteExclusive = [decimal]$Offset + $Size
        SizeBytes = [decimal]$Size; StartSector = [decimal]$Offset / $Sector
        EndSector = ([decimal]$Offset + $Size) / $Sector - 1
    }
}
$espType = 'c12a7328-f81f-11d2-ba4b-00a0c93ec93b'
$msrType = 'e3c9e316-0b5c-4db8-817d-f92df00215ae'
$dataType = 'ebd0a0a2-b9e5-4433-87c0-68b6b72699c7'
$windowsEsp = '01234567-89ab-cdef-0123-456789abcdef'
$linuxEsp = '11234567-89ab-cdef-0123-456789abcdef'
$before = [pscustomobject]@{
    Disk = [pscustomobject]@{ WindowsNumber = 0; Model = 'Fixture NVMe'; Serial = 'fixture-only'; Guid = '21234567-89ab-cdef-0123-456789abcdef'; SizeBytes = 512110190592; LogicalSectorBytes = 512 }
    CFreeBytes = 168GB
    Partitions = @(
        (Partition 1 '' $windowsEsp $espType 1MB 100MB 512),
        (Partition 2 '' '31234567-89ab-cdef-0123-456789abcdef' $msrType 101MB 16MB 512),
        (Partition 3 C '41234567-89ab-cdef-0123-456789abcdef' $dataType 128MB 400GB 512),
        (Partition 4 '' '51234567-89ab-cdef-0123-456789abcdef' 'de94bba4-06d1-4d40-a16a-bfd50179d6ac' (128MB + 400GB) 1GB 512)
    )
    Boot = [pscustomobject]@{ Entry = 'Boot0001'; Description = 'Windows Boot Manager'; PartitionGuid = $windowsEsp; LoaderPath = '\EFI\Microsoft\Boot\bootmgfw.efi'; StartSector = 2048; EndSector = 206847 }
}
$after = Copy-Record $before
$after.CFreeBytes = 72GB
$after.Partitions[2].SizeBytes -= 96GB
$after.Partitions[2].EndByteExclusive -= 96GB
$after.Partitions[2].EndSector -= 96GB / 512

Check 'Windows headroom is calculated and checked before shrinking' { $plan = Get-AresShrinkPlan $before; Equal $plan.ProjectedCFreeGiB 72; Equal $plan.ProjectedCSizeGiB 304; Equal $plan.ShrinkDialogMB 98304 }
Check 'pre-shrink insufficient headroom fails before any disk change' { $r = Copy-Record $before; $r.CFreeBytes = 150GB; Reject { Get-AresShrinkPlan $r } }
Check '512-byte sectors: calculate donation, excluding other free gaps' {
    $rows = @(Get-AresDonation $before $after)
    Equal $rows.Count 4
    Equal $rows[0].StartSector 637796352
    Equal $rows[0].EndSector 839122943
    Equal ($rows[1].EndSector + 1) $rows[2].StartSector
    Equal ($rows[2].EndSector + 1) $rows[3].StartSector
    Equal $rows[3].EndSector $rows[0].EndSector
}
Check '4096-byte logical sectors: no hardcoded 512-byte conversion' {
    $b = Copy-Record $before; $a = Copy-Record $after
    foreach ($r in $b, $a) {
        $r.Disk.LogicalSectorBytes = 4096
        foreach ($p in $r.Partitions) { $p.StartSector = $p.StartByte / 4096; $p.EndSector = $p.EndByteExclusive / 4096 - 1 }
        $r.Boot.StartSector = 256; $r.Boot.EndSector = 25855
    }
    $rows = @(Get-AresDonation $b $a)
    Equal $rows[0].StartSector 79724544
    Equal $rows[0].EndSector 104890367
}
Check 'changed disk identity refuses donation' { $r = Copy-Record $after; $r.Disk.Serial = 'other-disk'; Reject { Get-AresDonation $before $r } }
Check 'moved recovery partition refuses donation' { $r = Copy-Record $after; $r.Partitions[3].StartByte += 1MB; Reject { Get-AresDonation $before $r } }
Check 'missing MSR refuses donation' { $r = Copy-Record $after; $r.Partitions = @($r.Partitions | Where-Object GptType -ne $msrType); Reject { Get-AresDonation $before $r } }
Check 'wrong shrink size refuses donation' { $r = Copy-Record $after; $r.Partitions[2].EndByteExclusive += 1GB; Reject { Get-AresDonation $before $r } }
Check 'insufficient Windows free space refuses donation' { $r = Copy-Record $after; $r.CFreeBytes = 59GB; Reject { Get-AresDonation $before $r } }
Check 'renumbered Windows partition is still identified by GUID' { $r = Copy-Record $after; $r.Partitions[2].WindowsPartition = 8; Equal (@(Get-AresDonation $before $r).Count) 4 }

$installed = Copy-Record $after
$installed.Partitions += Partition 5 '' $linuxEsp $espType $after.Partitions[2].EndByteExclusive 1GB 512
Check 'original Windows ESP passes with a second ESP present' { Confirm-AresWindowsBoot $installed $before }
Check 'Windows Microsoft loader on AresOS ESP refuses deletion' {
    $r = Copy-Record $installed
    $r.Boot.PartitionGuid = $linuxEsp
    $r.Boot.StartSector = $r.Partitions[4].StartSector
    $r.Boot.EndSector = $r.Partitions[4].EndSector
    Reject { Confirm-AresWindowsBoot $r $before }
}
Check 'GRUB chainload refuses deletion despite Windows-looking label' { $r = Copy-Record $installed; $r.Boot.LoaderPath = '\EFI\fedora\shimx64.efi'; Reject { Confirm-AresWindowsBoot $r $before } }
Check 'changed original ESP boundaries refuse deletion' { $r = Copy-Record $installed; $r.Boot.EndSector++; Reject { Confirm-AresWindowsBoot $r $before } }
Check 'label and Boot number do not replace GUID identity' { $r = Copy-Record $installed; $r.Boot.Entry = 'Boot00AF'; $r.Boot.Description = 'A renamed entry'; Confirm-AresWindowsBoot $r $before }

function Boot-Bytes($Guid, $Path = '\EFI\Microsoft\Boot\bootmgfw.efi') {
    $hd = [byte[]]::new(42); $hd[0] = 4; $hd[1] = 1; $hd[2] = 42
    [BitConverter]::GetBytes([uint32]1).CopyTo($hd, 4)
    [BitConverter]::GetBytes([uint64]2048).CopyTo($hd, 8)
    [BitConverter]::GetBytes([uint64]204800).CopyTo($hd, 16)
    ([guid]$Guid).ToByteArray().CopyTo($hd, 24); $hd[40] = 2; $hd[41] = 2
    $file = [Text.Encoding]::Unicode.GetBytes($Path + [char]0)
    $node = [byte[]]@(4, 4) + [BitConverter]::GetBytes([uint16]($file.Length + 4)) + $file
    $dp = $hd + $node + [byte[]]@(127, 255, 4, 0)
    $description = [Text.Encoding]::Unicode.GetBytes('Windows Boot Manager' + [char]0)
    return ,([BitConverter]::GetBytes([uint32]1) + [BitConverter]::GetBytes([uint16]$dp.Length) + $description + $dp)
}
function Parse-Boot([byte[]]$Bytes) { & $module { param($b) ConvertFrom-AresBootEntry $b 'Boot0001' } $Bytes }
Check 'EFI binary parser preserves GUID byte order, full path and inclusive endpoint' {
    $b = Parse-Boot (Boot-Bytes $windowsEsp)
    Equal $b.PartitionGuid $windowsEsp
    Equal $b.LoaderPath '\EFI\Microsoft\Boot\bootmgfw.efi'
    Equal $b.EndSector 206847
}
Check 'two identical labels decode to different ESP identities' { Equal (Parse-Boot (Boot-Bytes $linuxEsp)).PartitionGuid $linuxEsp }
Check 'truncated EFI variable fails closed' { Reject { Parse-Boot ([byte[]]@(1, 2)) } }
Check 'missing end-of-path node fails closed' { $b = Boot-Bytes $windowsEsp; Reject { Parse-Boot $b[0..($b.Length - 5)] } }
Check 'MBR target fails closed' { $b = Boot-Bytes $windowsEsp; $b[48 + 40] = 1; Reject { Parse-Boot $b } }
Check 'multiple device-path instances fail closed' { $b = Boot-Bytes $windowsEsp; $b[$b.Length - 3] = 1; Reject { Parse-Boot $b } }
Check 'unterminated loader fails closed' { $b = Boot-Bytes $windowsEsp; $b[$b.Length - 6] = 1; Reject { Parse-Boot $b } }

# Compile the native reader, but never call it. In-memory fixture tests exercise
# the full inventory function only after replacing every hardware entry point.
Check 'Windows native reader compiles without invoking a native method' {
    $source = Get-Content -Raw $modulePath
    $native = [regex]::Match($source, "(?s)Add-Type -TypeDefinition @'\r?\n(.*?)\r?\n'@").Groups[1].Value
    if (-not $native) { throw 'Native source not found.' }
    Add-Type -TypeDefinition $native
}
Check 'complete inventory uses fixture commands and emits every partition' {
    & $module {
        param($fixture)
        $script:fixture = $fixture
        function script:Get-AresCurrentBoot { $script:fixture.Boot }
        function script:Get-Disk {
            param($Number)
            $d = $script:fixture.Disk
            [pscustomobject]@{ Number = $d.WindowsNumber; FriendlyName = $d.Model; SerialNumber = $d.Serial; Guid = $d.Guid; Size = $d.SizeBytes; LogicalSectorSize = $d.LogicalSectorBytes; PartitionStyle = 'GPT' }
        }
        function script:Get-Partition {
            param($DriveLetter, $DiskNumber)
            foreach ($p in $script:fixture.Partitions) {
                if ($DriveLetter -and $p.DriveLetter -ne $DriveLetter) { continue }
                [pscustomobject]@{ DiskNumber = 0; PartitionNumber = $p.WindowsPartition; DriveLetter = $p.DriveLetter; Guid = $p.Guid; GptType = $p.GptType; Offset = $p.StartByte; Size = $p.SizeBytes }
            }
        }
        function script:Get-Volume { param($DriveLetter) [pscustomobject]@{ SizeRemaining = $script:fixture.CFreeBytes } }
    } $before
    $r = Get-AresInstallRecord
    Equal $r.Partitions.Count 4
    Equal $r.Partitions[1].GptType $msrType
    Equal $r.Partitions[2].EndSector 839122943
}
Check 'unreadable BootCurrent aborts full inventory' {
    & $module { function script:Get-AresCurrentBoot { throw 'STOP: fixture firmware variable unavailable.' } }
    Reject { Get-AresInstallRecord }
}
Check 'owner PowerShell command blocks parse without execution' {
    foreach ($document in 'INSTALL.md', 'INSTALL-RECORD.md') {
        $markdown = Get-Content -Raw (Join-Path $PSScriptRoot "../../docs/$document")
        foreach ($block in [regex]::Matches($markdown, '(?ms)^[ \t]*```powershell\r?\n(.*?)^[ \t]*```')) {
            $tokens = $null; $parseErrors = $null
            $null = [Management.Automation.Language.Parser]::ParseInput($block.Groups[1].Value, [ref]$tokens, [ref]$parseErrors)
            if ($parseErrors.Count) { throw "$document has invalid PowerShell: $parseErrors" }
        }
    }
}
Remove-Module InstallRecord
Write-Output "All $script:passed synthetic checks passed. No hardware queries or writes executed."
