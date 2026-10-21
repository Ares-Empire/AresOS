# Report: 02 — OS base design

2026-10-21 · Branch `pkg/02-os-base-design` · [PR #2](https://github.com/carlsenares/AresOS/pull/2)

## Done

- [docs/design/OS-BASE.md](../../docs/design/OS-BASE.md) answers all ten brief questions, compares alternatives and recommends minimal Ubuntu 26.04 LTS, Canonical-signed NVIDIA modules, labwc, Prism and an external SSD first.
- The main reading path contains the stack table, five owner decisions, ten topic sections and top risks. Appendices specify build/state boundaries, app/game lifecycle behavior, installer safeguards, future acceptance trials, twelve Phase 2 packages and 55 primary sources checked on 2026-10-21.
- Facts read in sources are labelled **Verified**; unmeasured or inferred claims are **Assumed**. **Proposal** explicitly means future behavior whose integration is untested. Sources do not count as hardware evidence.
- Only this design and report were added. No OS code/configs, assets, ISO downloads, installations, system changes or disk/boot operations. No access to the owner's Minecraft folder or Lunar Client.
- Design committed as `7ea4ebf` (`docs: design the AresOS Linux base`), pushed, and PR #2 opened against `main`. This report is the follow-up commit required by AGENTS.md. No merge or council review was performed; the brief says the design council comes next.

## Verified

### Repository and scope

Read `AGENTS.md`, the brief, `README.md`, `docs/WORKFLOW.md` and `docs/REVIEW.md`. `rg --files` showed repository guidance and briefs only at the starting commit `3498ebc`; there was no existing OS or mod code to modify.

`git status --short --branch` initially printed `## pkg/02-os-base-design` with no changed files. `Test-Path mod` printed `False`. Consequently `./gradlew build` was **not run**: neither `mod/` nor its wrapper exists in this worktree. This is not a passing build or an omitted failing test.

### Document checks

Ran this PowerShell command after the final design edit, with exit code 0:

```powershell
$aresDoc = Get-Content -Raw docs/design/OS-BASE.md
$aresMain = ($aresDoc -split '## Appendix A')[0]
$aresDefinitions = @([regex]::Matches($aresDoc, '(?m)^\[([A-Z]+\d+)\]: (https://\S+)$'))
$aresDefined = @($aresDefinitions | ForEach-Object { $_.Groups[1].Value })
$aresReferences = @([regex]::Matches($aresDoc, '\[([A-Z]+\d+)\](?!:)') | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique)
$aresMissing = @($aresReferences | Where-Object { $_ -notin $aresDefined })
$aresQuestions = @([regex]::Matches($aresDoc, '(?m)^## (\d+)\. ') | ForEach-Object { $_.Groups[1].Value })
$aresBrokenLocal = @([regex]::Matches($aresDoc, '\]\((?!https?://|#)([^)]+)\)') | Where-Object { -not (Test-Path -LiteralPath (Join-Path (Resolve-Path docs/design).Path $_.Groups[1].Value)) })
'Main reading words: ' + [regex]::Matches($aresMain, '\S+').Count
'Total words: ' + [regex]::Matches($aresDoc, '\S+').Count
'Numbered questions: ' + ($aresQuestions -join ', ')
'External source definitions: ' + $aresDefined.Count
'Undefined source references: ' + $aresMissing.Count
'Broken local links: ' + $aresBrokenLocal.Count
'Adjacent reference ambiguity: ' + [regex]::Matches($aresDoc, '\[[A-Z]+\d+\]\[[A-Z]+\d+\]').Count
'mod directory exists: ' + (Test-Path mod)
if ($aresMissing.Count -or $aresBrokenLocal.Count -or ($aresQuestions -join ',') -ne '1,2,3,4,5,6,7,8,9,10') { exit 1 }
git diff --cached --check
```

Output:

```text
Main reading words: 3382
Total words: 6457
Numbered questions: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
External source definitions: 55
Undefined source references: 0
Broken local links: 0
Adjacent reference ambiguity: 0
mod directory exists: False
```

The final `git diff --cached --check` printed nothing. The reading count includes tables/Markdown notation; approximately 15 minutes assumes roughly 225 words/minute and is not a timed owner test. The reference checks establish Markdown references and local paths, not universal external URL availability or technical correctness. During inspection, adjacent shortcut references were separated to avoid Markdown treating two citations as one labelled link.

### Research evidence

Web research read upstream/distro documentation and versioned source; links and the check date are in Appendix F. Material checks included Ubuntu's prebuilt signed NVIDIA path, Curtin's default NVRAM writes, Microsoft's BitLocker trigger guidance, labwc's window interfaces, Prism 11.0.3's actual CLI/auth source, GitHub's private-repository quotas and Minecraft 26.2's rendering changes.

The Fedora bootc documentation and RPM Fusion Secure Boot pages returned access-denied pages. They are not cited as verified evidence. The upstream bootc manual supports the transactional-update comparison; the exact Fedora/NVIDIA trust combination remains explicitly assumed. Some guessed documentation URLs failed and were replaced with accessible primary documentation. No OS/software binary was downloaded.

For Java requirements, ran this metadata-only request:

```powershell
$aresManifest = Invoke-RestMethod -Uri 'https://piston-meta.mojang.com/mc/game/version_manifest_v2.json' -TimeoutSec 20
$aresVersion = $aresManifest.versions | Where-Object id -eq '26.2'
if ($aresVersion) {
    $aresMeta = Invoke-RestMethod -Uri $aresVersion.url -TimeoutSec 20
    [pscustomobject]@{id=$aresMeta.id; javaVersion=$aresMeta.javaVersion; metadataUrl=$aresVersion.url} | ConvertTo-Json -Depth 4
} else {
    '26.2 absent from returned manifest'
}
```

It exited 0 and printed:

```json
{
  "id": "26.2",
  "javaVersion": {
    "component": "java-runtime-epsilon",
    "majorVersion": 25
  },
  "metadataUrl": "https://piston-meta.mojang.com/v1/packages/bdfd9856166b7171857c491f15479762f3abda99/26.2.json"
}
```

### Publication

`git commit -m 'docs: design the AresOS Linux base'` printed commit `7ea4ebf`, one new file and 354 insertions. `git push -u origin pkg/02-os-base-design` exited 0, created the remote branch and set its upstream.

`gh pr create --base main --head pkg/02-os-base-design --title 'Design the AresOS Linux base and Phase 2 rollout' --body-file .pr-body-02.txt` exited 0 and printed `https://github.com/carlsenares/AresOS/pull/2`. The temporary body file was removed from this worktree afterward.

## Not verified

- No Gradle build, automated game/client tests, VM tests, OS builds, screenshots or real-hardware trials. There is no runtime implementation in this brief to exercise. The document's acceptance matrix is future work, not results.
- No confirmation of this unit's disk serials, spare slot, BitLocker status, recovery-key availability, firmware CA/revocation state, GPU wiring, wireless hardware or installed virtualization tools.
- No exact Ubuntu kernel/NVIDIA package pairing, shader/mod compatibility lockfile, Prism offline identity continuity, labwc helper implementation or signed update pipeline was qualified.
- No measured boot-to-world time, battery life, shader performance, suspend reliability or artifact build cost. These require the implementing packages and owner-controlled hardware trials.
- No independent review. The planned design council must challenge the recommendation and assumptions before implementation/merge.

## JUDGMENT-CALL

| Choice | Alternatives rejected / why | Cost of changing later |
|---|---|---|
| Ubuntu LTS installation recipe and package updates | NixOS has stronger declarative generations, bootc has transactional updates; Ubuntu's documented signed NVIDIA path better fits unchanged firmware trust. | Replace the OS build/update/recovery layer; preserve the session/mod interface and separate data. Decide before installer work. |
| labwc with borderless game and explicit close/switch/return policy | cage's single-app model, gamescope as the entire desktop, sway's interaction model, a custom compositor. The required experience uses independent overlapping apps. | Mostly compositor/helper policy and session tests; game fullscreen/input behavior may also need changes. |
| Super+Home, Alt+Tab, terminal escape, bounded restart | Pure game-only control and endless restart would make auth/crash failures hard to recover. Closing a final app window returns to Minecraft even with another app open. | User-visible interaction change; bindings are cheap, window/lifecycle semantics need regression tests. |
| Prepared boot, with setup and occasional login UI | A completely unattended fresh boot cannot supply the owner's account and network state. | Additional provisioning/security work; cannot remove entitlement and reauthentication requirements by configuration. |
| AC/battery/background FPS hypotheses, shaders off on battery, suspend gated | Intel-only Minecraft violates the required renderer; unqualified suspend risks losing the desktop. | Tune policy cheaply after measurements; GPU switching or persistent sleep changes need broader hardware tests. |
| Disposable unencrypted trial data; encryption decision before personal use | Silent TPM unlock or pretending auto-login protects tokens. | Encryption may require reinstall/data migration and changes the boot experience; settle before storing personal files. |
| External SSD isolation, F12, no persistent boot entry by default | Shared Windows ESP, modifying BootOrder or opportunistic target selection. Reversibility and Windows protection take priority. | Persistent entry/second NVMe requires a new owner-reviewed installation brief and firmware/BitLocker checks. |

## PLAN-GAP

- The absolute no-BitLocker-recovery requirement cannot be guaranteed from a design or a separate drive. Section 3 makes the boundary explicit: retain the acceptance goal, require the owner's recovery preparation, and stay in VMs if zero risk is mandatory.
- “OS as code” does not determine atomic updates. The recommended signed-driver route accepts package-based recovery; the owner should choose bootc instead if that burden is unacceptable.
- Minecraft 26.2 has an experimental Vulkan path. The first qualification must select and record OpenGL and test the chosen Iris/Sodium combination, rather than rely on a mutable default.
- The Prism CLI wiki omits flags present in released source. Implementation must test the chosen binary, not assume the wiki's option list is complete.
- Vanilla Save and Quit does not uniquely mean OS shutdown: it also participates in world selection. A distinct intentional shutdown/save-complete protocol is required to avoid powering off on a crash or ordinary world change.
- First-run network/authentication and out-of-game recovery tools are necessary before the polished Minecraft-only interface. They are explicit packages rather than hidden future dependencies.
- The general AGENTS.md build requirement cannot run in this documentation-only worktree because `mod/` is absent. No placeholder project or test was added merely to claim green.

## Open questions

For the owner/council, not blockers to publishing this research:

1. Accept Ubuntu's recovery tradeoff, or prefer bootc and permit a separately reviewed signing/enrollment path?
2. What are the actual firmware/encryption state, protected Windows disk identity and spare-slot occupancy?
3. Is a disk-unlock prompt acceptable for personal use, and where should the independent backup live?
4. Are the proposed multitasking keys, close-to-world behavior and occasional setup/login screens acceptable?
5. What battery life and boot time are acceptable, and which essential apps/peripherals define the first hardware acceptance set?
