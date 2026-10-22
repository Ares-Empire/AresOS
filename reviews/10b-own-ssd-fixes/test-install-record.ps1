# Existing synthetic suite plus the documented pre-check, never storage queries.
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '../10-own-ssd-install/test-install-record.ps1')

Check 'record B refuses an unelevated terminal before collection' {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    if ($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'This check requires an ordinary terminal. Do not run the tests as administrator.'
    }

    $markdown = Get-Content -Raw (Join-Path $PSScriptRoot '../../docs/INSTALL-RECORD.md')
    $section = [regex]::Match($markdown, '(?ms)^## B\..*?(?=^## C\.)').Value
    $block = [regex]::Match($section, '(?ms)^```powershell\r?\n(.*?)^```').Groups[1].Value
    $end = $block.IndexOf('$aresRepo =')
    if ($end -lt 1) { throw 'Record B pre-check boundary not found.' }
    # Execute only the token check. The rest of record B is never evaluated.
    $precheck = [scriptblock]::Create($block.Substring(0, $end))
    $output = @()
    $message = ''
    try { & $precheck | ForEach-Object { $output += $_ } }
    catch { $message = $_.Exception.Message }
    Equal $output.Count 0
    Equal $message 'STOP: right-click Start -> Terminal (Administrator), approve the prompt, select Windows PowerShell, then rerun record B.'
}

Write-Output "All $script:passed checks passed (77 synthetic regression checks and 1 unelevated pre-check). No disk/firmware queries or configuration changes executed."
Write-Output ('PowerShell version: ' + $PSVersionTable.PSVersion.ToString())
