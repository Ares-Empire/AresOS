# Windows counterparts to test_owner_entry.py. All storage facts are fixtures.
param([Parameter(Mandatory)][string]$Bundle, [Parameter(Mandatory)][string]$Work)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$repo = (Resolve-Path "$PSScriptRoot/../..").Path
# Share the fixture's script scope so its process-local PSDrive is visible
# inside the module, just as when owner-tools.Tests.ps1 is invoked directly.
$captured = @(. "$PSScriptRoot/owner-tools.Tests.ps1" -Bundle $Bundle -Work $Work)
$captured
$recordOutput = @(& {
    # Reuse the synthetic records and all 78 original refusal assertions.
    . "$repo/reviews/10b-own-ssd-fixes/test-install-record.ps1"
    Import-Module "$repo/docs/install-tools/InstallRecord.psm1" -Force
    Confirm-AresWindowsDiskUnchanged -Before $before -After (Copy-Record $before)
})
$recordOutput
$captured += $recordOutput

$record = Get-Content -LiteralPath "$repo/docs/INSTALL-RECORD.md" -Raw
$section = [regex]::Match($record, '(?ms)^## B\..*?(?=^## C\.)').Value
$block = [regex]::Match($section, '(?ms)^```powershell\r?\n(.*?)^```').Groups[1].Value
$end = $block.IndexOf('$aresRepo =')
if ($end -lt 1) { throw 'Record B pre-check boundary not found.' }
$precheck = $block.Substring(0, $end)
# Supply a synthetic administrator identity to the real documented guard.
# No elevation, Storage module, record collection or firmware query executes.
$identity = '[Security.Principal.WindowsIdentity]::GetCurrent()'
$principal = '[Security.Principal.WindowsPrincipal]::new($aresIdentity)'
foreach ($expression in $identity,$principal) {
    if ([regex]::Matches($precheck,[regex]::Escape($expression)).Count -ne 1) { throw 'Unexpected identity boundary.' }
}
$fixturePrincipal = [pscustomobject]@{}
$fixturePrincipal | Add-Member ScriptMethod IsInRole { param($Role) $true }
$precheck = $precheck.Replace($identity, '$null').Replace($principal, '$fixturePrincipal')
$adminOutput = @(& ([scriptblock]::Create($precheck)))
if ($adminOutput.Count -ne 1) { throw 'Administrator pre-check must print exactly one result.' }
$captured += $adminOutput
$adminOutput

$checked = 0
foreach ($page in 'INSTALL.md','INSTALL-PROCEDURES.md','INSTALL-REFERENCE.md','EMERGENCY.md') {
    $guide = Get-Content -LiteralPath "$repo/docs/$page" -Raw
    foreach ($match in [regex]::Matches($guide, '`(PASS(?:: | tools manifest SHA256 | ARESTOOLS )[^`]+)`')) {
        if ($captured -cnotcontains $match.Groups[1].Value) { throw "Documented Windows PASS differs from captured stdout in $page." }
        $checked++
    }
}
if ($checked -lt 4) { throw 'Missing Windows PASS expectations.' }
"PASS $checked documented Windows PASS results equal captured entry stdout; no hardware queries."
