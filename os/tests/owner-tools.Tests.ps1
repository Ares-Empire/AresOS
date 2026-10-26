param([Parameter(Mandatory)][string]$Bundle, [Parameter(Mandatory)][string]$Work)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
Import-Module "$PSScriptRoot/../../docs/install-tools/OwnerTools.psm1" -Force
if (Test-Path -LiteralPath $Work) { throw 'Use a new ordinary test folder inside this worktree.' }
$repo = (Resolve-Path "$PSScriptRoot/../..").Path
$full = [IO.Path]::GetFullPath($Work)
if (-not $full.StartsWith($repo + [IO.Path]::DirectorySeparatorChar)) { throw 'Test folder must stay in worktree.' }
New-Item -ItemType Directory -Path $full | Out-Null
$usb = Join-Path $full 'usb'
New-Item -ItemType Directory -Path $usb | Out-Null
$good = @{Letter='T'; DriveType='Removable'; BusType='USB'; IsBoot=$false; IsSystem=$false;
          Serial='VIRTUAL-TOOLS'; FileSystem='exFAT'; Root=$usb}
$cases = @(@{Letter='C'}, @{DriveType='Fixed'}, @{BusType='NVMe'}, @{IsBoot=$true},
           @{IsSystem=$true}, @{Serial=''}, @{FileSystem='NTFS'}, @{Root=$full})
$count = 0
foreach ($bad in $cases) {
    $drive = $good.Clone()
    foreach ($key in $bad.Keys) { $drive[$key] = $bad[$key] }
    $refused = $false
    try { Copy-AresToolsPayload -Source $Bundle -Destination (Join-Path $usb 'ares-tools') -Drive $drive }
    catch { if (-not $_.Exception.Message.StartsWith('STOP:')) { throw }; $refused = $true }
    if (-not $refused -or @(Get-ChildItem -LiteralPath $usb -Force).Count -ne 0) { throw 'Refusal wrote files.' }
    $count++
}
foreach ($kind in 'tamper','partial','duplicate','duplicate-field','old-shape','path-first','traversal') {
    $badBundle = Join-Path $full $kind
    Copy-Item -LiteralPath $Bundle -Destination $badBundle -Recurse
    if ($kind -eq 'tamper') { Add-Content -LiteralPath (Join-Path $badBundle 'at') -Value 'BAD' }
    if ($kind -eq 'partial') { Remove-Item -LiteralPath (Join-Path $badBundle 'at') }
    if ($kind -notin 'tamper','partial') {
        $manifest = Join-Path $badBundle 'SHA256.json'
        $raw = Get-Content -LiteralPath $manifest -Raw
        $rows = @($raw | ConvertFrom-Json -AsHashtable)
        if ($kind -eq 'duplicate') { $raw = ConvertTo-Json -Depth 5 -InputObject @($rows + @($rows[0])) }
        if ($kind -eq 'duplicate-field') { $raw = $raw.Replace('"path": "at"', '"path": "at", "path": "at"') }
        if ($kind -eq 'old-shape') { $raw = '{"at":"' + ('a' * 64) + '"}' }
        if ($kind -eq 'path-first') { $raw = '[{"path":"at","sha256":"' + ('a' * 64) + '"}]' }
        if ($kind -eq 'traversal') { $rows[0].path = '../outside'; $raw = ConvertTo-Json -Depth 5 -InputObject $rows }
        Set-Content -LiteralPath $manifest -Value $raw
    }
    $refused = $false
    try { Copy-AresToolsPayload -Source $badBundle -Destination (Join-Path $usb 'ares-tools') -Drive $good }
    catch { if (-not $_.Exception.Message.StartsWith('STOP:')) { throw }; $refused = $true }
    if (-not $refused -or @(Get-ChildItem -LiteralPath $usb -Force).Count -ne 0) { throw 'Bad bundle refusal wrote files.' }
    $count++
}
Copy-AresToolsPayload -Source $Bundle -Destination (Join-Path $usb 'ares-tools') -Drive $good
if ((Test-AresToolsBundle $Bundle) -cne (Test-AresToolsBundle (Join-Path $usb 'ares-tools'))) { throw 'Copy differs.' }
if ($IsWindows) {
    # A process-local filesystem PSDrive and module-local hardware stand-ins.
    # These functions never call the actual Storage module.
    $root = Join-Path $full 'public-entry'
    New-Item -ItemType Directory -Path $root | Out-Null
    if (Get-PSDrive -Name Y -ErrorAction SilentlyContinue) { throw 'Fixture PSDrive Y already exists; preserve it.' }
    New-PSDrive -Name Y -PSProvider FileSystem -Root $root | Out-Null
    try {
        $module = Get-Module OwnerTools
        & $module {
            $script:fixtureLabel = 'RESTORED'
            function script:Get-Volume { param($DriveLetter) [pscustomobject]@{DriveType='Removable'; FileSystem='exFAT'; FileSystemLabel=$script:fixtureLabel} }
            function script:Get-Partition { param($DriveLetter) [pscustomobject]@{DiskNumber=99} }
            function script:Get-Disk { param($Number) [pscustomobject]@{BusType='USB';IsBoot=$false;IsSystem=$false;SerialNumber='SYNTHETIC'} }
            function script:Set-Volume { param($DriveLetter,$NewFileSystemLabel) $script:fixtureLabel=$NewFileSystemLabel }
        }
        $entryOutput = @(Copy-AresOwnerTools -Source $Bundle -DriveLetter Y)
        $entryOutput
        foreach ($page in 'INSTALL.md','INSTALL-PROCEDURES.md','INSTALL-REFERENCE.md','EMERGENCY.md') {
            $guide = Get-Content -LiteralPath (Join-Path $repo "docs/$page") -Raw
            foreach ($match in [regex]::Matches($guide, '`(PASS (?:tools manifest SHA256 |ARESTOOLS )[^`]+)`')) {
                if ($entryOutput -cnotcontains $match.Groups[1].Value) { throw "Documented copy PASS differs from entry stdout in $page." }
            }
        }
        if ((Test-AresToolsBundle (Join-Path $root 'ares-tools')) -cne (Test-AresToolsBundle $Bundle)) { throw 'Public entry differs.' }
    } finally { Remove-PSDrive -Name Y }
}
"PASS $count destination refusals with zero writes; copied payload equals source"
