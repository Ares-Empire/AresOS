# Report: 02b — OS base revision

2026-10-21 · Branch `pkg/02-os-base-design` · [PR #2](https://github.com/carlsenares/AresOS/pull/2)

This report covers [brief 02b](../../briefs/02b-os-base-revision.md). The [original 02 report](../02-os-base-design/REPORT.md) remains historical; its Ubuntu recommendation is superseded by the owner's Bazzite decision.

## Done

- [OS-BASE.md](../../docs/design/OS-BASE.md): applied Bazzite NVIDIA as the custom atomic-image base, with digest/Containerfile/Actions requirements, accepted installation MOK enrollment and Ubuntu fallback. Compared session customization, trust, maintenance ownership and complete recovery.
- Resolved the seven blocking findings as design contracts: independent recovery credentials; system-level power handling and a save channel independent of the app helper; cancellable ordinary-app shutdown; complete previous OS/driver recovery and independent media; selective restore/reprovision of machine state; one update authority and upgrade convergence; interface v1 and migration preserving package-01 IDs/configuration.
- Defined normal Minecraft as a separate app/instance with normal rules. The desktop saves/stops during play on 16 GB; focus, input, game failure and return-to-hub behavior are specified. Resource limits are initial test budgets; Lunar and simultaneous games remain qualified later options.
- Addressed findings 8–13 with pressure isolation, finite persistent crash recovery, foreground-only focus return, early hardware evidence and explicit sleep/comfort gates. Appendix E now starts with minimal image/safe installer → integrated session/world/app/save/tested backup → early F12/NVIDIA/Windows-return trial, including the missing Nether mod dependency.
- [CHANGES.md](../councils/2026-10-21-os-base/CHANGES.md): one row per council finding with direct section links, resolution/deferral and acceptance gate. The verdict and member reports were not edited.
- Added a ten-line plain-language opening. The main reading path is 2,892 words; details are in appendices. The evidence index retains 55 original sources and adds 22 sources checked on 2026-10-21. New externally grounded statements link to that dated evidence.
- Documentation/change map committed as `7509f72` and pushed to the existing PR. This report is the separate follow-up commit required by AGENTS.md. No new PR or merge.

## Verified

### Inputs and scope

Read AGENTS.md, both OS briefs, README, workflow/review guidance, council QUESTION/VERDICT and all four members, the original design/report, and briefs 01/01b for the existing app fields and desktop-world boundary. `git status --short --branch` initially printed `## pkg/02-os-base-design...origin/pkg/02-os-base-design` with no changes; starting HEAD was `42dcbe3`.

`git ls-tree -r --name-only HEAD` listed guidance, briefs, design and reviews, with no `mod/` code. `rg --files mod` printed that the path did not exist; `Test-Path mod` printed `False`. Therefore `./gradlew build` was **not run**: there is no mod project/wrapper in this worktree. No Gradle daemon or client was started, so there was no started daemon to stop.

Only this worktree's documentation and temporary verification text were changed. No OS code/configuration, binaries/ISOs, installations, disks/partitions/boot configuration, Windows settings, other worktrees, real Minecraft folder or Lunar Client were touched.

### Document verification

Ran `.\.verify-02b.ps1` from the repository root, containing exactly the following code. It exited 0. The temporary script is reproduced here for rerunning and removed before delivery to keep the committed change documentation-only.

```powershell
$ErrorActionPreference = 'Stop'
$aresDesignPath = 'docs/design/OS-BASE.md'
$aresMapPath = 'reviews/councils/2026-10-21-os-base/CHANGES.md'
$aresDesign = Get-Content -Raw $aresDesignPath
$aresMap = Get-Content -Raw $aresMapPath
$aresMain = ($aresDesign -split '## Appendix A')[0]
$aresDefinitions = @([regex]::Matches($aresDesign, '(?m)^\[([A-Z]+\d+)\]: (https://\S+)$'))
$aresDefined = @($aresDefinitions | ForEach-Object { $_.Groups[1].Value })
$aresReferences = @([regex]::Matches($aresDesign, '\[([A-Z]+\d+)\](?!:)') | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique)
$aresMissing = @($aresReferences | Where-Object { $_ -notin $aresDefined })
$aresDuplicate = @($aresDefined | Group-Object | Where-Object Count -gt 1)
$aresQuestions = @([regex]::Matches($aresDesign, '(?m)^## (\d+)\. ') | ForEach-Object { $_.Groups[1].Value })
$aresFindings = @([regex]::Matches($aresMap, '(?m)^\| (\d+) — ') | ForEach-Object { $_.Groups[1].Value })
$aresBroken = [Collections.Generic.List[string]]::new()
$aresLinkCount = 0
foreach ($aresFile in @($aresDesignPath, $aresMapPath)) {
    $aresContent = Get-Content -Raw $aresFile
    $aresDirectory = Split-Path (Resolve-Path $aresFile).Path
    foreach ($aresMatch in [regex]::Matches($aresContent, '\]\((?!https?://)([^)]+)\)')) {
        $aresLinkCount++
        $aresParts = $aresMatch.Groups[1].Value -split '#', 2
        $aresTarget = if ($aresParts[0]) { [IO.Path]::GetFullPath((Join-Path $aresDirectory $aresParts[0])) } else { (Resolve-Path $aresFile).Path }
        if (-not (Test-Path -LiteralPath $aresTarget -PathType Leaf)) {
            $aresBroken.Add($aresMatch.Groups[1].Value)
            continue
        }
        if ($aresParts.Count -eq 2) {
            $aresTargetContent = Get-Content -Raw -LiteralPath $aresTarget
            $aresSlugs = @([regex]::Matches($aresTargetContent, '(?m)^#{1,6} (.+)\r?$') | ForEach-Object {
                (($_.Groups[1].Value.Trim().ToLowerInvariant() -replace '[^\p{L}\p{N}_\- ]', '') -replace ' ', '-')
            })
            if ($aresParts[1] -notin $aresSlugs) { $aresBroken.Add($aresMatch.Groups[1].Value) }
        }
    }
}
$aresMainWords = [regex]::Matches($aresMain, '\S+').Count
$aresRevisionSources = @($aresDefined | Where-Object { $_ -match '^Z\d+$' }).Count
$aresSummaryLines = @([regex]::Matches($aresDesign, '(?m)^.+\\$')).Count + 1
'Main reading words: ' + $aresMainWords
'Total design words: ' + [regex]::Matches($aresDesign, '\S+').Count
'Owner summary lines: ' + $aresSummaryLines
'Numbered sections: ' + ($aresQuestions -join ', ')
'Council finding rows: ' + ($aresFindings -join ', ')
'External source definitions: ' + $aresDefined.Count
'Revision sources dated 2026-10-21: ' + $aresRevisionSources
'Undefined source references: ' + $aresMissing.Count
'Duplicate source definitions: ' + $aresDuplicate.Count
'Local links/anchors checked: ' + $aresLinkCount
'Broken local links/anchors: ' + $aresBroken.Count
'Adjacent reference ambiguity: ' + [regex]::Matches($aresDesign, '\[[A-Z]+\d+\]\[[A-Z]+\d+\]').Count
'mod directory exists: ' + (Test-Path mod)
if ($aresBroken.Count) { $aresBroken }
if ($aresMissing.Count -or $aresDuplicate.Count -or $aresBroken.Count -or $aresMainWords -gt 3400 -or $aresSummaryLines -ne 10 -or $aresRevisionSources -ne 22 -or ($aresQuestions -join ',') -ne '1,2,3,4,5,6,7,8,9,10' -or ($aresFindings -join ',') -ne '1,2,3,4,5,6,7,8,9,10,11,12,13') { exit 1 }
git diff --check
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
'git diff --check: PASS (no output)'
```

Final output:

```text
Main reading words: 2892
Total design words: 9404
Owner summary lines: 10
Numbered sections: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
Council finding rows: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13
External source definitions: 77
Revision sources dated 2026-10-21: 22
Undefined source references: 0
Duplicate source definitions: 0
Local links/anchors checked: 33
Broken local links/anchors: 0
Adjacent reference ambiguity: 0
mod directory exists: False
git diff --check: PASS (no output)
```

The initial diff check detected nine trailing-space Markdown hard breaks in the summary (exit 1). Replaced them with backslash hard breaks; subsequent `git diff --check` and `git diff --cached --check` printed nothing and exited 0. No test was weakened or skipped to hide a failure.

Manually checked the design and change map against all 13 verdict entries and both owner decisions. Checked that old Ubuntu-first, foreground-independent focus-return, kernel-only recovery and late-P10 policies were removed. Clarified the update/power transaction boundary because staged deployment finalization must not activate an update during emergency shutdown.

The main word count suggests roughly 13 minutes at 225 words/minute; this is an estimate, not a timed owner test. Link/reference checks establish document structure, not runtime correctness or universal external URL availability.

### Research

Read primary Bazzite/Universal Blue documentation and sources, including the concrete NVIDIA image family, custom-image/template route, installation MOK method, rollback/pinning and automatic/manual uupd units. Read upstream shim, OSTree, logind/inhibitor, UPower, NetworkManager, restic and systemd resource/OOM documentation, plus Microsoft's BitLocker policy and Ubuntu's update/driver comparison. The exact URLs and 2026-10-21 date are in Appendix F, Z1–Z22; original research is explicitly labelled inherited.

Two attempted UPower configuration-source URLs failed (GitHub 404; freedesktop GitLab inaccessible). No claim treats those as verified. The readable API reports critical-action choices; the design requires the selected image's actual configuration and forced-event test before qualification. No images or software packages were downloaded.

### Publication

`git add -- docs/design/OS-BASE.md reviews/councils/2026-10-21-os-base/CHANGES.md` staged only those files. `git diff --cached --check` printed nothing, exit 0. `git diff --cached --stat` reported 2 files, 310 insertions and 167 deletions.

`git commit -m 'docs: revise OS base design after council decisions'` printed commit `7509f72`, 2 changed files and creation of CHANGES.md. `git push origin pkg/02-os-base-design` exited 0 and printed `42dcbe3..7509f72 pkg/02-os-base-design -> pkg/02-os-base-design`. The existing PR remained open against main. The final report commit/push and final PR-head check follow this report; no merge is authorized.

## Not verified

- No Gradle, automated game/client, OS-build, VM, hardware, backup restore, battery or suspend tests were run. No screenshots were generated. Appendix D is future acceptance work, not test evidence.
- No Bazzite image digest/backend, driver pairing, UPower configuration, compositor integration, interface implementation or migration was qualified. Digest selection belongs to the minimal-image package; the design contains no pretend qualified hash.
- No proof of this laptop's Secure Boot trust, F12 discoverability, BitLocker behavior, free slot, disk identities, GPU routing, memory/VRAM capacity under load or comfort thresholds.
- The chair has not yet reviewed this revision. A complete previous deployment, offline recovery media and restore rehearsals remain prerequisites before implementation enables updates.
- No server/Lunar compatibility claim, two-game capacity claim or sleep/resume support claim. Normal gameplay and those optional gates are specified, not delivered by this documentation brief.

## JUDGMENT-CALL

| Choice | Alternatives rejected / reason | Cost of changing later |
|---|---|---|
| Stop/save desktop while normal Minecraft runs; restore hub afterwards | Two resident games or pause-only would exceed the proposed 16 GB budget; no measurements justify them. | Change transition/focus policy after real headroom/VRAM tests; quicker return trades against resources. |
| Before suspend qualification, lid saves/stops desktop and blanks panel, leaving apps running | Unqualified suspend or powering off apps risks lost work; ignoring the lid entirely does not meet the clean-save intent. First-run UI must explain it remains on. | Later suspend package must define position/focus/resume semantics and replace the lid policy. |
| Separate system power coordinator and game guardian from the app helper | A single helper cannot be the only save route when helper failure is an explicit acceptance case. | A small additional supervision/lifecycle boundary; preserve one versioned protocol rather than duplicate world logic. |
| Schema-2 config migration with explicit Linux registry and stable `notepad` ID | Silent command translation/direct-launch fallback would bypass OS window/GPU ownership. Back up original commands and preserve appearance/IDs. | Reversible using saved config; later edits need an explicit downgrade merge. |
| Measured budgets, three-consecutive-failure latch, manual initial rollback and security cadence | Optimistic two-game operation, unlimited slow restarts or claimed automatic recovery lack evidence. | Parameters are cheap to change after tests; automatic boot healing needs a separate policy. |

Bazzite, installation MOK enrollment, Ubuntu fallback and normal gameplay separation are already owner decisions, not new approval requests.

## PLAN-GAP

- README's playable survival desktop and its unresolved base question lag brief 02b. This design explicitly applies the newer owner decisions without editing the frozen briefs/README.
- Package 01/01b does not provide the Nether hub, interface v1 or lifecycle save channel. P2 explicitly includes those mod dependencies; Linux integration cannot be claimed from separate helper/mod tests.
- The selected Bazzite digest must settle deployment backend, inherited updater/power entry points and supported UPower settings. Docs expose capability, not the exact future image's contents.
- “Always clean save” cannot cover hardware forced power loss, a frozen kernel or exhausted energy. The design requires helper-failure clean saving and measured emergency reserves, cancels ordinary failed saves and labels unavoidable emergency failures unclean instead of claiming success.
- OS deployment rollback does not undo persistent state or world conversion. The recovery kit and selective state/manifest contracts remain mandatory even on an atomic base.
- AGENTS.md's Gradle build cannot execute without a mod project in this documentation worktree; no placeholder code was added to manufacture a green result.

## Open questions

None block publication of this documentation revision. Later gates must settle the actual image digest/backend and laptop feasibility; encryption/auto-login and independent backup location; measured power/noise/return limits; preferred normal-game profile; and the suspend lifecycle choice before enabling it. No mid-run answers were requested.
