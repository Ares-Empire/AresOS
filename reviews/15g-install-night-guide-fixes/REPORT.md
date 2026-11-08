# 15g REPORT: Install-night guide fixes

Built in the restricted Windows worktree on 2026-11-08. The user's delivery override applies: **no commit, push, PR, merge or WSL invocation**. All edits and scratch files are inside this worktree. No real disk/firmware queries, settings changes or system software installation were performed.

## Done

- `docs/INSTALL.md`: Claude/owner responsibilities; Windows Micron printed-serial reading linked to A before leaving Windows; live localectl command and exact US-on-German positions; typing STOP; bounded pre-tools reinstall; every-install a–x/top-row-digit passphrase; expected MOK menu; bootstrap history inspection; Bazzite naming; guarded shutdown and first-switch failure routes. The trusted 13-line bootstrap and installer target-keyboard settings are unchanged.
- `docs/INSTALL-RECORD.md`: distinguishes Windows EUI-64 `Disk.Serial` from Linux printed SERIAL. Read-only Windows snippet reads `AdapterSerialNumber` before `_`, trimmed; manual PASS requires the `SerialNumber`/A match and the matching disk GUID. Crucial retains the photographed printed label serial. Reinstall gets its own bounded checkpoint; no other data may be erased under it.
- `docs/INSTALL-REFERENCE.md`: tty4 fallback, temporary black-screen wait, keyboard/MOK sources, and the 10-minute shutdown policy with finalization limits and explicit returns.
- `docs/EMERGENCY.md`: consistent password/reinstall, MOK, console, hung-shutdown and failed-switch routes. Removes the old one-minute force-off shortcut.
- `docs/INSTALL-STATUS.md`: records step 4 passing on 2026-11-08, based on the supplied brief, and the owner's decision to continue with reviewed PR #22 tools without a new rehearsal. Keeps step 5 onward, remaining phone/negative/lifecycle/recovery/hardware gates open; publishes no new release.
- `os/tests/test_owner_path.py`: nine additional regression tests pin the requested fixes, allowed passphrase key positions against retained maps, recovery constraints and status limits. Existing assertions remain intact.
- `os/manifest/ci/16/pending-rebind.json`: updated INSTALL/test hashes and added EMERGENCY's hash. These are the changed files in the 244-source active union; INSTALL-RECORD, INSTALL-REFERENCE and INSTALL-STATUS are not in that union. All 11 previously pending sources remain, making **12 pending**. Historical walk/source-binding tables are untouched.

## Verified

**This is not a green Python/WSL or Gradle result.** Native checks below passed; the required Python suites and pinned gitleaks still need Claude's runs.

Commands were run from the worktree root unless stated otherwise:

| Command/check | Result |
| --- | --- |
| `node .work/15g/check.cjs --rebind`, then `node .work/15g/check.cjs` | Both exit 0. Output: `PASS 277 local owner-page links and anchors`; `PASS owner navigation graph: 1777 states; login/switch require step 5`; `PASS exact 13-line bootstrap, line 8 fingerprint, canonical bash blocks, restart receipts and Ctrl labels`; `PASS ISO map hashes, US-on-German minus/y/space positions and a-x/top-row digit equivalence`; `PASS install-night route guards, serial join, roles and Bazzite naming`; `PASS isolated Git checkout replay: 244 active sources; 12 pending; historical tables unchanged`. |
| PowerShell parser: extract the new serial block, run `[Management.Automation.Language.Parser]::ParseInput`, inspect all `CommandAst` names against `Get-PhysicalDisk`, `Get-Disk`, `Where-Object`, `Format-List` | `PASS serial snippet syntax and read-only command allowlist; no execution/hardware query`. The snippet was **not** executed on hardware. |
| `git diff --check` | Exit 0; no output. |
| `git diff --exit-code main -- os/owner-tools os/release os/manifest/release.json docs/install-tools .github` | Exit 0; empty. |
| `py --version` | `No installed Python found!`; no usable `python`/`python3` on PATH either. |
| Worktree-only embedded Python download with `Invoke-WebRequest -Uri https://www.python.org/ftp/python/3.13.9/python-3.13.9-embed-amd64.zip -OutFile .work/15g/python.zip -UseBasicParsing -TimeoutSec 20` | Failed: `Die Verbindung mit dem Remoteserver kann nicht hergestellt werden.` No archive retained or runtime installed. |
| `Get-Command gitleaks -ErrorAction SilentlyContinue` | No command found; no gitleaks scan claimed. |
| In `mod/`: `.\gradlew.bat --no-daemon --gradle-user-home ..\.work\15g\gradle build runClientGameTest` | Exit 1 before Gradle started: `Attempt 1/1 failed. Reason: Permission denied: getsockopt` fetching Gradle 9.8.0. No build/client tests or daemons started, so no daemon remains to stop. No second run represented as evidence. |
| `& ./.work/15g/check-record.ps1` (invented-fixture check helper) | Blocked by PowerShell script execution policy, `PSSecurityException`. Did not change/bypass that policy. Only the separate parser/command-allowlist check above ran; no fixture-execution pass claimed. |

`rg` was unavailable; searches used Git/PowerShell. An initial `node -e` scratch check lost quotes through Windows PowerShell native argument handling and failed with `SyntaxError`; the file-based native check above replaced it. Read/search errors are not test results. The ignored `.work/15g/check.cjs` retains the native checks for inspection/rerun in this worktree; it is **not** a substitute for Python unittest.

The manifest was generated with a native implementation of the same isolated `git init` / attribute-aware `git add` / `git checkout-index` replay as `checkout_sources.records`: scratch Git state and config are inside `.work/15g`, never the real index. It verifies all nonpending sources against their historical hashes and every pending source differs from the walk. **The mandated Python function could not run here; Claude must regenerate with it below and require `test_checkout_sources` to pass.**

Sources checked:

- Retained `os/manifest/ci/14/keyboard-sources/{de,us}.map` and index hashes: physical keys 12 (ß/minus), 21 (z/y), 57 (space), and the allowed account alphabet agree. [systemd v259 localectl](https://github.com/systemd/systemd/blob/v259/man/localectl.xml) confirms the command's system-map operation. Live Wayland behavior remains the brief's owner observation.
- [shim 16.1 MokManager](https://github.com/rhboot/shim/blob/16.1/MokManager.c), matching shim 16.1-7 in retained `os/manifest/ci/packages.txt`: menu labels and the continue branch checked. Blue appearance and successful continuation come from brief 15g's observation; no screenshot invented.
- Retained `os/manifest/ci/13/zero-cost/ostree-src_libostree_ostree-sysroot-deploy.c` (2026.4), [matching shutdown service](https://github.com/ostreedev/ostree/blob/v2026.4/src/boot/ostree-finalize-staged.service), [upstream staged-deployment explanation](https://ostreedev.github.io/ostree/deployment/#staged-deployments), and `qualified_state` / `Tools.check` in unchanged `os/owner-tools/owner.py`. These support the reference's interruption possibilities and limits, not a tested power-cut recovery guarantee.

Cleanup: removed the failed Gradle download's `.part` and `.lck` files after checking their absolute paths stay inside this worktree's `.work/15g/gradle`. No ISO/layer downloads or extracted images. Final inventory of **`.work/` files over 500 MB: none**.

## Not verified

- No Python test execution, WSL, pinned gitleaks, successful Gradle/client run, VM rehearsal, image build or dispatch. No new screenshots. All laptop observations are attributed to the supplied brief, not repeated here.
- No new live keyboard/MOK/reinstall/media/phone/power-cut trial. The ten-minute policy needs owner review. The edited phone instructions still need the reader trial.
- No assertion that `PASS check` proves AresOS booted after an interrupted switch: it can pass for valid stock. The guide now insists on the actual AresOS session and final pair.

### Claude: regenerate pending hashes with the required helper

Open WSL **after this sandbox run** and use this worktree. This only updates the pending list, never the historical tables. Run it again after any further edit to a bound file.

```bash
test "$(basename "$PWD")" = AresOS-15g-install-night-guide-fixes || { echo 'STOP: open this worktree root in WSL first'; exit 1; }
mkdir -p .work/15g/tmp .work/15g/verification
export TMPDIR="$PWD/.work/15g/tmp"
unset PYTHONDONTWRITEBYTECODE
python3 -B - <<'PY'
import json
import pathlib
import sys
root = pathlib.Path.cwd()
sys.path.insert(0, str(root / 'os/ci'))
import checkout_sources
path = root / 'os/manifest/ci/16/pending-rebind.json'
pending = json.loads(path.read_text())
bound = {row['path'] for row in checkout_sources.merge(checkout_sources.active_tables(root))}
changed = {
    'docs/INSTALL.md', 'docs/INSTALL-RECORD.md', 'docs/INSTALL-REFERENCE.md',
    'docs/INSTALL-STATUS.md', 'docs/EMERGENCY.md', 'os/tests/test_owner_path.py',
}
names = {row['path'] for row in pending['files']} | (changed & bound)
assert names <= bound
pending['files'] = checkout_sources.records(root, sorted(names))
with path.open('w', encoding='utf-8', newline='\n') as stream:
    stream.write(json.dumps(pending, indent=2) + '\n')
print('Regenerated', len(pending['files']), 'pending checkout sources')
PY
```

Expected: 12 sources and no hash difference from this delivery if files are unchanged. Investigate differences; do not rewrite walk tables or loosen tests.

### Claude: exact WSL test list, with and without -B

Continue in that WSL shell. The loop runs **all four focused suites and the complete suite in each mode**, retains output and continues to record later results if one fails.

```bash
set -o pipefail
for mode in bytecode no-bytecode; do
  flags=()
  if [ "$mode" = no-bytecode ]; then flags=(-B); fi
  for suite in test_owner_path test_owner_equality test_checkout_sources test_owner_step_limits; do
    python3 "${flags[@]}" -m unittest discover -s os/tests -p "$suite.py" -v \
      2>&1 | tee ".work/15g/verification/$mode-$suite.log"
    result=${PIPESTATUS[0]}
    printf '%s %s exit=%s\n' "$mode" "$suite" "$result"
  done
  python3 "${flags[@]}" -m unittest discover -s os/tests -v \
    2>&1 | tee ".work/15g/verification/$mode-all.log"
  result=${PIPESTATUS[0]}
  printf '%s full-suite exit=%s\n' "$mode" "$result"
done
```

There are **four named focused suites**, plus the whole suite, as listed in the brief. Require every focused run to pass. Only the brief's existing WSL baseline failures may remain in the whole suite: `test_greeter` (3), `test_inherited_homebrew` (6: 1 failure/5 errors), `test_sysusers` (1). Anything else must be fixed, not waived; do not skip/weaken tests. Update this report with actual commands/results.

### Claude: pinned gitleaks, including the uncommitted files

Use PowerShell from this worktree. This uses the retained **8.21.2** archive and binary pins from `os/manifest/ci/14/privacy-stop/scanner.json`, also used in package 15/16 reports. It is separate from the privacy hook's own scanner. Reuse a verified worktree-local copy if present; no system installation is needed.

```powershell
$ErrorActionPreference = 'Stop'
$aresPin = Get-Content -Raw os/manifest/ci/14/privacy-stop/scanner.json | ConvertFrom-Json
$aresScan = Join-Path (Get-Location) '.work/15g/gitleaks'
New-Item -ItemType Directory -Force $aresScan | Out-Null
$aresArchive = Join-Path $aresScan 'gitleaks.zip'
if (-not (Test-Path -LiteralPath $aresArchive)) {
    Invoke-WebRequest -Uri $aresPin.url -OutFile $aresArchive
}
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $aresArchive).Hash.ToLowerInvariant() -ne $aresPin.archive_sha256) { throw 'STOP: scanner archive hash mismatch' }
Expand-Archive -LiteralPath $aresArchive -DestinationPath $aresScan -Force
$aresLeaks = Join-Path $aresScan 'gitleaks.exe'
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $aresLeaks).Hash.ToLowerInvariant() -ne $aresPin.binary_sha256) { throw 'STOP: scanner binary hash mismatch' }
& $aresLeaks version
if ($LASTEXITCODE) { throw 'STOP: scanner did not run' }
& $aresLeaks git . '--log-opts=--all --full-history -m' --redact=100 --no-banner --report-format json --report-path .work/15g/gitleaks/history.json
if ($LASTEXITCODE) { throw 'STOP: history scan failed; review findings' }
$aresInput = Join-Path $aresScan 'current-edits'
New-Item -ItemType Directory -Force $aresInput | Out-Null
$aresFiles = @(
    'docs/INSTALL.md', 'docs/INSTALL-RECORD.md', 'docs/INSTALL-REFERENCE.md',
    'docs/INSTALL-STATUS.md', 'docs/EMERGENCY.md', 'os/tests/test_owner_path.py',
    'os/manifest/ci/16/pending-rebind.json', 'reviews/15g-install-night-guide-fixes/REPORT.md'
)
foreach ($aresFile in $aresFiles) {
    $aresDest = Join-Path $aresInput $aresFile
    New-Item -ItemType Directory -Force (Split-Path $aresDest) | Out-Null
    Copy-Item -LiteralPath $aresFile -Destination $aresDest -Force
}
& $aresLeaks dir $aresInput --config .gitleaks.toml --redact=100 --no-banner --report-format json --report-path .work/15g/gitleaks/current-edits.json
if ($LASTEXITCODE) { throw 'STOP: current-edit scan failed; review findings' }
git diff --check
git diff --exit-code main -- os/owner-tools os/release os/manifest/release.json docs/install-tools .github
```

The second scan covers the uncommitted report and working-file bytes; a Git-history scan alone cannot cover them. Do not use `--no-verify`, change privacy rules or treat redaction as approval of findings.

For the repository-wide Gradle requirement, in a usable Windows environment run `./gradlew.bat build runClientGameTest` **twice inside `mod/`**, then `./gradlew.bat --stop`. Keep any new screenshots under this package's review directory; do not overwrite historical evidence in the final diff. No mod change is part of this brief.

## JUDGMENT-CALL

**Recommendation: use the documented ten-minute minimum and narrow force-off conditions.** Reject the former one-minute hold-power advice: the pinned OSTree service alone allows five minutes for finalization. Also reject saying a staged switch is guaranteed safe to interrupt or always produces a STOP afterwards. Under a genuine shutdown hang, after completed command/PASS evidence and ten minutes without progress, the owner can force off once, then go to Windows and Help. Unknown completion, ongoing progress, firmware updates, media activity or layout trials do not qualify. Elapsed time cannot prove write completion; the tradeoff is possible lost work/incomplete deployment versus an indefinitely stuck laptop. This is a reversible documentation policy; changing it later requires updating the reference, emergency card and tests. Owner review is still required before merge, not requested during this run.

The restricted passphrase alphabet, first-install retry scope and MOK continuation are explicit brief requirements, not additional design decisions.

## PLAN-GAP

- `qualified_state` accepts the saved stock state and a valid staged state; `check` is not a switch-completion receipt and does not inspect the finalization failure marker. The guide addresses this with explicit OS/final-pair checks and Help, without changing tools. A future tool change, if desired, needs its own brief.
- Required Python helper/tests and gitleaks were unavailable here; the user explicitly permits a sandbox handoff. Native replay produced and checked the pending hashes, but the official helper and WSL results above remain required.
- The archived same-drive guide retains historical agent-role wording; it is not an active owner route and was left outside this own-SSD brief.

## Open questions

- Owner/maintainer review of the ten-minute power-off recommendation.
- Claude's official hash regeneration, WSL suites, gitleaks and remaining build/physical evidence are still outstanding. No new release or merge is authorized by these local checks.
