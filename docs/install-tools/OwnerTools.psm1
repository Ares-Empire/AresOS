# Importing this module never queries hardware. The copy refuses before writing.
Set-StrictMode -Version Latest

function Test-AresToolsBundle {
    param([Parameter(Mandatory)][string]$Path)
    $root = (Resolve-Path -LiteralPath $Path -ErrorAction Stop).ProviderPath
    if ((Get-Item -LiteralPath $root).Attributes -band [IO.FileAttributes]::ReparsePoint) {
        throw 'STOP: bundle root is a link.'
    }
    $manifest = Join-Path $root 'SHA256.json'
    $raw = Get-Content -LiteralPath $manifest -Raw
    $document = [System.Text.Json.JsonDocument]::Parse($raw)
    $keys = @($document.RootElement.EnumerateObject() | ForEach-Object { $_.Name })
    if (@($keys | Sort-Object -Unique).Count -ne $keys.Count) { throw 'STOP: duplicate manifest entries.' }
    $entries = $raw | ConvertFrom-Json -AsHashtable
    if ($entries.Count -lt 3) { throw 'STOP: incomplete bundle manifest.' }
    $files = @(Get-ChildItem -LiteralPath $root -Recurse -Force)
    if (@($files | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint }).Count) {
        throw 'STOP: bundle contains a link.'
    }
    $actual = @($files | Where-Object { -not $_.PSIsContainer } | ForEach-Object {
        [IO.Path]::GetRelativePath($root, $_.FullName).Replace('\', '/')
    } | Sort-Object)
    $expected = @(@($entries.Keys) + 'SHA256.json' | Sort-Object)
    if (Compare-Object $actual $expected) { throw 'STOP: partial or unexpected bundle files.' }
    foreach ($name in $entries.Keys) {
        if ($name -notmatch '^[a-zA-Z0-9._/-]+$' -or $name.Split('/') -contains '..' -or
            $name.StartsWith('/') -or $entries[$name] -cnotmatch '^[0-9a-f]{64}$') {
            throw 'STOP: invalid manifest entry.'
        }
        $file = Join-Path $root $name
        if ((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant() -cne $entries[$name]) {
            throw "STOP: bundle hash mismatch: $name"
        }
    }
    (Get-FileHash -LiteralPath $manifest -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Copy-AresToolsPayload {
    # Pure file-copy implementation, also used by CI after its file-backed USB
    # attestation. The public Windows entry below supplies actual hardware facts.
    param([Parameter(Mandatory)][string]$Source,
          [Parameter(Mandatory)][string]$Destination,
          [Parameter(Mandatory)]$Drive)
    if ($Drive.Letter -ieq 'C' -or $Drive.DriveType -ne 'Removable' -or
        $Drive.BusType -ne 'USB' -or $Drive.IsBoot -or $Drive.IsSystem -or
        -not $Drive.Serial -or $Drive.FileSystem -ne 'exFAT') {
        throw 'STOP: destination must be the restored removable exFAT USB, never C: or an internal disk.'
    }
    $parent = Split-Path -Parent $Destination
    if (-not $Drive.Root -or -not (Test-Path -LiteralPath $parent -PathType Container) -or
        (Resolve-Path -LiteralPath $parent).ProviderPath -cne (Resolve-Path -LiteralPath $Drive.Root).ProviderPath) {
        throw 'STOP: destination is not on the inspected USB root.'
    }
    $fingerprint = Test-AresToolsBundle -Path $Source
    if (Test-Path -LiteralPath $Destination) { throw 'STOP: destination exists; preserve it for review.' }
    Copy-Item -LiteralPath $Source -Destination $Destination -Recurse -ErrorAction Stop
    if ((Test-AresToolsBundle -Path $Destination) -cne $fingerprint) { throw 'STOP: copied manifest differs.' }
    "PASS tools manifest SHA256 $fingerprint"
}

function Copy-AresOwnerTools {
    param([Parameter(Mandatory)][string]$Source,
          [Parameter(Mandatory)][ValidatePattern('^[D-Zd-z]$')][string]$DriveLetter)
    $letter = $DriveLetter.ToUpperInvariant()
    $volume = Get-Volume -DriveLetter $letter -ErrorAction Stop
    $partition = Get-Partition -DriveLetter $letter -ErrorAction Stop
    $disk = Get-Disk -Number $partition.DiskNumber -ErrorAction Stop
    if (@($partition).Count -ne 1 -or @($disk).Count -ne 1 -or @($volume).Count -ne 1) {
        throw 'STOP: ambiguous destination.'
    }
    $drive = [pscustomobject]@{Letter=$letter; DriveType=[string]$volume.DriveType;
        FileSystem=[string]$volume.FileSystem; BusType=[string]$disk.BusType;
        IsBoot=$disk.IsBoot; IsSystem=$disk.IsSystem; Serial=$disk.SerialNumber; Root=($letter + ':\')}
    Copy-AresToolsPayload -Source $Source -Destination ($letter + ':\ares-tools') -Drive $drive
    Set-Volume -DriveLetter $letter -NewFileSystemLabel 'ARESTOOLS' -ErrorAction Stop
    if ((Get-Volume -DriveLetter $letter -ErrorAction Stop).FileSystemLabel -cne 'ARESTOOLS') {
        throw 'STOP: tools label did not round-trip; do not unplug until Windows reports safe eject.'
    }
    'PASS ARESTOOLS ready; safely eject and unplug before shutdown/restart or record B.'
}

Export-ModuleMember -Function Test-AresToolsBundle, Copy-AresToolsPayload, Copy-AresOwnerTools
