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
foreach ($kind in 'tamper','partial','duplicate') {
    $badBundle = Join-Path $full $kind
    Copy-Item -LiteralPath $Bundle -Destination $badBundle -Recurse
    if ($kind -eq 'tamper') { Add-Content -LiteralPath (Join-Path $badBundle 'at') -Value 'BAD' }
    if ($kind -eq 'partial') { Remove-Item -LiteralPath (Join-Path $badBundle 'at') }
    if ($kind -eq 'duplicate') {
        $manifest = Join-Path $badBundle 'SHA256.json'
        $raw = Get-Content -LiteralPath $manifest -Raw
        $entry = [regex]::Match($raw, '"at"\s*:\s*"[0-9a-f]+"').Value
        Set-Content -LiteralPath $manifest -Value ('{' + $entry + ',' + $raw.Trim().Substring(1))
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
        Copy-AresOwnerTools -Source $Bundle -DriveLetter Y
        if ((Test-AresToolsBundle (Join-Path $root 'ares-tools')) -cne (Test-AresToolsBundle $Bundle)) { throw 'Public entry differs.' }
    } finally { Remove-PSDrive -Name Y }
}
"PASS $count destination refusals with zero writes; copied payload equals source"
