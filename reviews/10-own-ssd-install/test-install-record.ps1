# Reuse the existing synthetic fixture and regression suite, never live storage.
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '../05b-dual-boot-fixes/test-install-record.ps1')
Import-Module (Join-Path $PSScriptRoot '../../docs/install-tools/InstallRecord.psm1') -Force

function Same($a, $b) {
    $result = @(Confirm-AresWindowsDiskUnchanged -Before $a -After $b)
    Equal $result.Count 1
    Equal $result[0] 'PASS: Windows disk identity, all partition GUIDs/types/boundaries and original Windows boot target match.'
}

Check 'own SSD: unchanged Windows record passes after JSON round trip' { Same $before (Copy-Record $before) }
Check 'own SSD: reordered/renumbered disks and partitions still match' {
    $r = Copy-Record $before
    $r.Disk.WindowsNumber = 9
    $r.Partitions = @($r.Partitions | Sort-Object StartByte -Descending)
    foreach ($p in $r.Partitions) { $p.WindowsPartition += 4 }
    $r.Boot.Entry = 'Boot0099'; $r.Boot.Description = 'Renamed'
    $r.CFreeBytes = 1GB
    Same $before $r
}
Check 'own SSD: 4096-byte sectors are accepted with consistent geometry' {
    $r = Copy-Record $before; $r.Disk.LogicalSectorBytes = 4096
    foreach ($p in $r.Partitions) { $p.StartSector = $p.StartByte / 4096; $p.EndSector = $p.EndByteExclusive / 4096 - 1 }
    $r.Boot.StartSector = 256; $r.Boot.EndSector = 25855
    Same $r (Copy-Record $r)
}
Check 'own SSD: Windows shrink is rejected (legacy allowance never applies)' { Reject { Same $before $after } }
foreach ($field in 'Model', 'Serial', 'Guid', 'SizeBytes', 'LogicalSectorBytes') {
    Check "own SSD: changed disk $field rejected" {
        $r = Copy-Record $before
        switch ($field) {
            'Guid' { $r.Disk.$field = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee' }
            'SizeBytes' { $r.Disk.$field += 1GB }
            'LogicalSectorBytes' { $r.Disk.$field = 4096 }
            default { $r.Disk.$field = 'Other disk' }
        }
        Reject { Same $before $r }
    }
}
for ($index = 0; $index -lt $before.Partitions.Count; $index++) {
    foreach ($field in 'Guid', 'GptType', 'StartByte', 'EndByteExclusive', 'SizeBytes', 'StartSector', 'EndSector') {
        Check "own SSD: partition $index changed $field rejected" {
            $r = Copy-Record $before
            if ($field -in 'Guid', 'GptType') { $r.Partitions[$index].$field = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee' }
            else { $r.Partitions[$index].$field += 512 }
            Reject { Same $before $r }
        }
    }
}
Check 'own SSD: removed MSR rejected' {
    $r = Copy-Record $before; $r.Partitions = @($r.Partitions | Where-Object GptType -ne $msrType)
    Reject { Same $before $r }
}
Check 'own SSD: extra partition in old free space rejected' {
    $r = Copy-Record $before; $r.Partitions += Partition 9 '' $linuxEsp $espType 450GB 1GB 512
    Reject { Same $before $r }
}
Check 'own SSD: C letter moved to another partition rejected' {
    $r = Copy-Record $before; $r.Partitions[2].DriveLetter = ''; $r.Partitions[3].DriveLetter = 'C'
    Reject { Same $before $r }
}
Check 'own SSD: Windows boot pointing to other disk rejected' {
    $r = Copy-Record $before; $r.Boot.PartitionGuid = $linuxEsp
    Reject { Same $before $r }
}
Check 'own SSD: misleading Windows label with GRUB loader rejected' {
    $r = Copy-Record $before; $r.Boot.LoaderPath = '\EFI\fedora\shimx64.efi'
    Reject { Same $before $r }
}
Check 'own SSD: relocated but internally consistent recovery partition rejected' {
    $r = Copy-Record $before
    $r.Partitions[3].StartByte += 1MB; $r.Partitions[3].EndByteExclusive += 1MB
    $r.Partitions[3].StartSector += 2048; $r.Partitions[3].EndSector += 2048
    Reject { Same $before $r }
}
foreach ($field in 'Disk', 'Partitions', 'Boot') {
    Check "own SSD: missing $field in both records never passes" {
        $r = Copy-Record $before; $r.PSObject.Properties.Remove($field)
        Reject { Same $r $r }
    }
}
Check 'own SSD: empty partition inventories never pass' {
    $r = Copy-Record $before; $r.Partitions = @(); Reject { Same $r $r }
}
Check 'own SSD: duplicate GUIDs never pass even in both records' {
    $r = Copy-Record $before; $r.Partitions[3].Guid = $r.Partitions[2].Guid
    Reject { Same $r $r }
}
Check 'own SSD: missing partition bounds fail closed' {
    $r = Copy-Record $before; $r.Partitions[3].PSObject.Properties.Remove('EndSector')
    Reject { Same $r $r }
}
Check 'own SSD: missing boot loader fails closed' {
    $r = Copy-Record $before; $r.Boot.PSObject.Properties.Remove('LoaderPath')
    Reject { Same $r $r }
}
Check 'own SSD: empty disk GUID fails closed' {
    $r = Copy-Record $before; $r.Disk.Guid = [guid]::Empty.ToString(); Reject { Same $r $r }
}
Remove-Module InstallRecord
Write-Output "All $script:passed synthetic checks passed (including the 26 existing regression checks). No hardware queries or writes executed."
