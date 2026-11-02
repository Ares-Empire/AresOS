# 15: one owner checklist and a symptom-first emergency card

## 15e — Card recovery and mounted-child status (2026-11-02)

**Done:** successful card-side abandon now jumps directly to `abandon-completion`, with no second invocation. Already-cleared state and the exact missing-pending-record refusal use completion only with the prior recorded PASS; every other refusal goes to Help. Begin/revert restart recovery uses the confirmed map; interrupted finish permits old once, then proven new once, with a two-failed-login total limit and no retry after sudo rejection. Completion keeps the AresOS/check/step-8 and retained-stock/keep-stock returns distinct.

**Policy source:** [eight retained files and digest bindings](15e-login-policy/README.md) were read from the public base pinned by the current release, after verifying the registry manifest and four OCI layer digests and resolving OSTree hardlinks. No image code, mount, container or VM executed. The baseline local PAM stack does not enable pam_faillock; its shipped configuration documents default deny=3, fail_interval=900 and unlock_time=600, without overrides. The two-failure budget is below that shipped default, not a claim of an active three-failure account lock. Build/package/keyboard-image source inheritance is checked. This does not audit a particular installed `/etc`; earlier failures, unknown policy or a lockout warning require Help before trying.

INSTALL-STATUS explicitly keeps the mounted-protected-child runtime negative check **OPEN — synthetic evidence only**. Maintainers must add a real mounted-child loop refusal/zero-mutation probe before release. Package 14's completed VM acceptance remains met; **NOT RELEASED** and all physical gates remain.

**Verified in WSL:** `python3 [-B] -m unittest discover -s os/tests -p <pattern> -v`, with `PYTHONDONTWRITEBYTECODE` unset and worktree TMPDIR. Patterns: `test_owner_path.py`, `test_owner_equality.py`, `test_owner*.py`. All six final runs have zero skips.

| Suite | `python3 -B` | Ordinary `python3` |
| --- | --- | --- |
| Owner path | **23 /45.080s, OK** | **23 /54.282s, OK** |
| Equality | **9 /362.958s, OK** | **9 /359.426s, OK** |
| Full owner | **323 /2090.153s, OK** | **323 /2167.655s, OK** |

Initial WSL owner-path run: **23 tests /53.594s, OK**; strengthened policy-source check: **1/0.906s, OK**. Final report/payload/fingerprint equality recheck: **2/2.430s, OK**. Windows Pester **1 passed, 0 failed/skipped**, exercising the existing four Windows PASS comparisons, 17 zero-write copy refusals and 78 record checks. Logs/runners and the public source archives stay in ignored `.work/15e/`; only the small policy-source files/index are retained.

Publisher-checksum-verified local **gitleaks 8.21.2**, `git . --log-opts="--all --full-history -m" --redact=100`: **733 commits /1m4.6s, zero leaks**, exit0 before this commit. The committed head is scanned again before the single privacy-hook push; the closing scan, hook and fresh billing receipts go in PR #14. Current-change whitespace and protected-path comparisons pass. All eight staged policy-source blobs match their recorded hashes; the initial Linux Git audit could not resolve the Windows gitdir, then passed using Git for Windows from WSL.

**Scope / not verified:** tools, payload, harness, workflows, Windows helpers, release and mod compare equal to `79a67d2`. No client/Gradle, dispatch or physical operation. No runtime mounted-child or live installed-PAM result is claimed. **JUDGMENT-CALL / PLAN-GAP / open questions:** none new.

## 15d — Final package 14 integration (2026-11-02)

**Done:** merged `origin/main` (`79a67d2`) with `--no-ff`, preserving the numbered checklist, symptom-first card, Windows proof gate and state-dependent returns. The 13-line bootstrap is byte-equal to the generator exercised by package 14's tamper tests. Regenerated SHA256SUMS fingerprint: `3e2c78ebedf7789b0616e7a4f21ad791d76784667344e76e97a1fbd95115a6fd`. Current copies, Windows manifests and all 20 captured dispatcher PASS results agree; earlier report sections retain historical bundle receipts.

The owner path now covers runtime-only begin/revert, persistent finish, fresh-login abandon with separate AresOS/stock returns, matching interrupted install/prepare resume, and exported persistent STOP diagnostics. Two new card entries cover interrupted layouts and tools STOPs. Status records qualification 21 on `3fd7916`, keeping its VM scope separate from 14zzf's local diagnostic-survival sequence.

**Verified in WSL:** `python3 [-B] -m unittest discover -s os/tests -p <pattern> -v`, with `PYTHONDONTWRITEBYTECODE` unset. Patterns: `test_owner_path.py`, `test_owner_equality.py`, `test_owner*.py`. All final runs have zero skips.

| Suite | `python3 -B` | Ordinary `python3` |
| --- | --- | --- |
| Owner path | **18 /53.898s, OK** | **18 /44.823s, OK** |
| Equality | **9 /367.299s, OK** | **9 /318.667s, OK** |
| Full owner | **318 /2042.911s, OK** | **318 /2093.991s, OK** |

Windows `pwsh -NoProfile -File os/tests/owner-pass.Tests.ps1 -Bundle os/owner-tools/payload -Work .work/15d/windows-pass`: **4 PASS comparisons, 17 zero-write copy refusals, 78 record checks passed**. Installed Pester 3.4.0 ran that test through `.work/15d/windows-pass-pester.Tests.ps1`: **1 passed, 0 failed/skipped**. Logs and runners remain in ignored `.work/15d/`.

Initial runs caught two integration defects: multiline inline invocations escaped the extra-argument mutation (**9 tests /335.702s, one failure**), and the session test searched INSTALL alone (**318 /2014.713s, one failure**). The scanner now checks complete spans; the session input includes INSTALL-PROCEDURES. Original assertions/mutations remain; focused reruns and both final full suites pass.

**Scope/privacy:** `git diff --exit-code 79a67d2 -- .` with only package 15's documents and five owner-test paths excluded is empty. Explicit comparisons of mod, tools/bundle, Windows helpers, workflows, harness and release are empty; screenshots match main. Current-change whitespace checks pass; imported reviews' existing Markdown hard breaks are preserved. Publisher-checksum-verified local **gitleaks 8.21.2**, `git . --log-opts="--all --full-history -m" --redact=100`: **731 commits, zero leaks**, before this commit. The committed head is scanned again before the single privacy-hook push; closing delivery receipt goes in PR #14.

**Not verified:** physical installation remains **NOT RELEASED**, with every laptop/media/phone/credential gate open. Qualification 21 did not test the exact STOP → export → reboot diagnostic sequence; 14zzf separately supplies local sequence evidence. No new VM/dispatch, image build, Minecraft client or Gradle run. **JUDGMENT-CALL / PLAN-GAP / open questions:** none new.

## 15c — Merge package 14n council fixes (2026-10-26)

**Done:** merged `754cf7c` with `--no-ff` from `3e07271`, preserving package 15's numbered checklist, symptom card, safety gates and state-dependent returns. Imported tools/harness/workflow/release content equals `754cf7c`; no additional runtime changes. The regenerated tools manifest fingerprint is `ef9cb33c7d08ff2be02e0b2fd62efb58dee9028963d66774422f5434b1168112`. Earlier bundle receipts below and in package 14's historical sections do not qualify this bundle.

All 19 CLI actions run through the real dispatcher with nonprivileged handler stand-ins. Every quoted/fenced expected CLI PASS across INSTALL, INSTALL-PROCEDURES, INSTALL-REFERENCE and EMERGENCY is compared with captured stdout, including repeated recovery references. Layout begin profiles have explicit matching results; path tests use captured proof/finish/reboot results. Mutations reject shortened PASS lines and an extra stale fingerprint in every owner page/current report, even alongside a correct copy. Regenerated payload, current fingerprint inventory and documented hashes agree; historical receipts remain intact.

**Verified locally:** WSL `python3 -m unittest discover -s os/tests` with `-p test_owner_path.py -v`: **16 tests /36.466s, OK**; `-p test_owner_equality.py -v`: **8 /41.578s, OK**; `-p 'test_owner*.py' -v`: **95 /142.298s, OK**, no skips. Worktree TMPDIR and the existing privilege-denial shim remain. Focused equality rerun with the final current-report fingerprint assertions: **8 /38.021s, OK**.

`pwsh -NoProfile -File os/tests/owner-pass.Tests.ps1 -Bundle os/owner-tools/payload -Work .work/15c/windows-pass-verified`: **4 documented Windows PASS results equal captured stdout**, plus all **15 zero-write copy refusals** and **78 record checks** passed. Two initial wrapper failures (PSDrive scope and a fixture's module cleanup) were corrected at those fixture boundaries; no product guard/assertion changed. `git diff --check`, syntax, scope and retired-fingerprint checks pass. Pinned publisher-checksum-verified **gitleaks 8.21.2**, `git . --log-opts=--all --redact=100`: **544 commits, zero leaks**, exit0 before the merge commit; the committed merge head is rescanned afterwards, with receipts in ignored `.work/15c/gitleaks/`.

**Not verified:** actual native partitioned-loop execution, VM qualification and physical gates remain open; installation is **NOT RELEASED**. No Minecraft client/Gradle, VM, dispatch, image build, hardware query, push, rebase or main merge. Screenshots unchanged. **JUDGMENT-CALL / PLAN-GAP / open questions:** none new.

## 15b — review fixes (2026-10-26)

**Done — all five findings:**

1. Battery action starts with stopping use/safely disconnecting the external charger, then safe separation from flammables, then the already-open/disconnected case. No battery handling/reconnection and no use/fitting before service clearance. Used the **LOQ guide’s own link to Lenovo Generic Safety and Compliance Notices**, plus LOQ HMM p.3; [source chain, pages and PDF hashes](SOURCES.md#15b-battery-source-review). The T490 page is superseded for this action.
2. Every tool restart shows the full canonical command and expected PASS/message. Equality now covers inline invocations across all six owner documents; mutations reject bare inline reboot, shorthand for every owner verb and extra arguments. Existing command/driver/bundle assertions remain.
3. Boot-order Secure Boot/recovery-prompt/missing-attached-entry STOPs appear before order restoration, each with Help and a named step-8 return.
4. B/C/D returns select the **calling procedure before the stage**. Keep-stock returns to its completion then step 8; AresOS layout recovery goes revert → fresh proof → finish → completion → step 8. State-dependent tests reject valid links to the wrong OS and a skipped finish.
5. Every status row has release/applicability labels: historical **362af9…** 06c/06e/11k/11n; current **9b19b7…** 13f with its protected-second/normal-rollback limits and no transferred manual-GRUB/promotion qualification.

Removed exactly the **27 package-15 screenshots**. All other tracked screenshots, owner tools/bundle, harness, workflows, manifests/releases and mod remain unchanged. Initial client timeout/pass evidence is retained below; no Minecraft client, Gradle, VM or dispatch was run in 15b.

**Verified in WSL Ubuntu** (existing Python 3.12.3/Bash; worktree TMPDIR):

| Command after `python3 -m unittest discover -s os/tests` | Result |
| --- | --- |
| `-p test_owner_path.py -v` | **15 tests /8.266s, OK** |
| `-p test_owner_equality.py -v` | **6 tests /13.258s, OK** |
| `-p 'test_owner*.py' -v` | **76 tests /125.450s, OK**, no skips |

REVIEW-2 follow-up (local only): added the everyday boot-order restoration caller returning to step 8 and its successful-route test; WSL owner-path **16/9.405s**, equality **6/19.800s**, full owner suite **77/128.769s**, all **OK**; pinned gitleaks 8.21.2 pre-commit full-history/all-ref scan: **533 commits, zero leaks**; no push or merge.

`git diff --check` and report/source/owner link checks pass. Pinned portable **gitleaks 8.21.2** was freshly extracted here from the retained publisher-checksum-verified archive (`f238c85e5f47e18fac779ce71ee11091cf70a0a8fb4415f165efba2800eef133`). Full-history/all-ref command `gitleaks.exe git . --log-opts=--all --redact=100 --no-banner --log-level info --report-format json --report-path .work/15b/gitleaks/implementation.json` at **7bdb74d**: **531 commits /27.4s /no leaks found**, exit0. Final report head is rescanned before the single push; exact final head/scan and fresh read-only org billing (must be ≥150 free minutes) go in the PR receipt without another push.

**Not verified:** physical gates and package 14 VM qualification remain open. Initial broader-suite host limits/client instability below remain unresolved; these owner-test passes do not close them. **JUDGMENT-CALL / PLAN-GAP / open questions:** none new; no runtime/tool change needed.

The remaining sections retain the initial package-15 evidence at `562e29c`.


**Documentation implemented; overall verification is NOT GREEN. Physical installation remains NOT RELEASED.** The new navigation/card tests and owner command/bundle checks pass. One client run timed out and the second sequential run passed; the native suite retains the eight package-14 host limitations. No VM, workflow dispatch, image build/publication, physical install or hardware query was performed.

## Done

- **INSTALL:** nine sequential steps with actions, expected screen/PASS, private evidence and STOP/return destinations. Step 5 combines unattended no-key/no-USB Windows, original Micron EFI comparison, corrected stock, physical typing and password-sudo proof. `STEP 5 COMPLETE` and its evidence are required at entry to step 6 and immediately before login/switch, including returns. Tools cannot enforce the human Windows proof.
- **EMERGENCY:** nine symptom headings before references/preparation; immediate action is the first paragraph of each. Freeze, failed first switch, stale title, password rejection, covered prompt, forgotten stick and battery warning are explicit. First-switch failure always returns through Windows/help.
- **INSTALL-REFERENCE / INSTALL-RECORD:** named returns without browser Back, private photo/help handling, console account/prompt/entry/exit, pinned media checks, full fitting/seating/battery stops and source-verified German writer controls. Record helper commands and all identity/EFI/geometry checks are preserved. A/B/C/D callers have explicit step destinations.
- **INSTALL-PROCEDURES:** later layout proof/revert with original root session retained, rollback, GRUB recovery/keep-stock and optional removal/erasure are outside the installation path. All existing guarded commands/checks remain. Frozen stock keeps installer German; recovery account remains `ares-recovery`.
- **INSTALL-STATUS / OS-BASE:** one current table with retained VM/source results, release/drive-order limits and open physical gates. Binding sequence reconciled: Linux-first offline setup, Windows-first during the tools round trip, repeated unattended Windows proof in step 5, then Windows-default/F12 thereafter. Qualification chronology/audit counts/screenshots are in the linked historical reports, not the owner checklist/card.
- **Tests:** new `test_owner_path.py` walks every owner line and inline/reference link as a graph with the explicit conditional gate, validates local targets/anchors, checks card ordering/action proximity, STOP/returns, shortcut labels and retirement/open-gate coverage. It tests deliberately introduced inline and reference-style bypass links below the gate and missing gate/marker. `test_owner_equality.py` only extends its document input to INSTALL plus the new separate procedures; every existing assertion, canonical command, physical-driver comparison and bundle comparison is retained.
- **Scope:** owner tools, payload/bundle, commands.json, release scripts/manifests, harness, workflows, image/release and mod source/build configuration are unchanged from `5156f5f`. The local brief `9836883` is preserved. No pull, dispatch, merge or push to main.

### Council finding map

| Finding | Change |
| --- | --- |
| **1 — return routes** | Explicit returns on checkpoints/detours; step 6 entry gate and repeated pre-invocation check; graph exploration with/without the step-5 marker, plus bypass mutation tests. |
| **4 — retirement** | Every permanent abandonment path (leave/remove/erase, including broken Linux) revokes the dedicated token from Windows/phone. GitHub Settings → Developer settings → Personal access tokens → Tokens (classic) → Delete verified 2026-10-26. Private note/date only; no new local deletion command. Fresh-auth/private-pull failure and offline retained boots remain a supervised disposable-credential gate. |
| **8 — emergency card** | Symptom-first actions; preparation/source history moved out; ordering/proximity test. Human 30-second phone discovery remains open. |
| **9 — keyboard** | Ctrl = Strg on every owner shortcut, Fn alternatives, login:/Password:/root prompts, complete logout and F1/F2 desktop return. Lenovo model-family FnLock/F12/F2 sources checked 2026-10-26. Linux prompt expectations are from our session recipe; both physical FnLock states remain open. |
| **10 — writer** | German 5.3.2 PO/QML labels, post-Write Löschbestätigung, target recheck, cancel/continue distinctions, verified-write result, restore → Weiter → Wiederherstellen and exact success sentence. Untranslated multiple-drive captions are disclosed. No main-branch translation used for new labels. |
| **11 — status** | One current table; stale untested/OPEN claims reconciled against reports; Linux-first/Windows-first phase boundary fixed in binding OS-BASE §8/Appendix C. Both-order earlier timing, protected-second revised timing and 13f limits retained. |

Both package-14 “For package 15” lists and stage walk are covered: record navigation; STOP/help/private photos; two-stick restore/copy/eject round trip; after-sign-in hotplug and no stick over restart; exact recovery-menu/account/session entry and exit; Enter for a covered prompt; frozen-backup layout; NVIDIA Flatpak-only deferral versus paused OS updates. The council's minimal owner checks are kept, not replaced by the word-count reduction.

## Verified

Commands ran locally from this worktree. Full raw logs/portable scanner remain in ignored `.work/15/`; 15b removes the unrelated client screenshots; no owner data is committed. No skipped/removed/weakened assertion and no elevated or system-install fallback was used.

| Command / check | Actual output/result | What it proves / does not prove |
| --- | --- | --- |
| `python -m unittest discover -s os/tests -p test_owner_path.py -v` | **8 tests, OK**, repeated after final link changes | Owner graph/local anchors, conditional Windows guard, deliberate inline/reference bypass rejection, missing gate/marker rejection; symptom order/actions and safety wording. Does not prove a human completed Windows checks or follows conditions, 30-second discovery, hardware behavior or localized rendering. |
| WSL `python3 -m unittest discover -s os/tests -p 'test_owner*.py' -v` | **67 tests /88.966s, OK**, no skips | Real owner handlers with explicit synthetic adapters, unchanged command/bundle equality, refusal/transport/export/media/console/guard/host walks, plus path tests. Not complete VM qualification. |
| WSL `python3 -m unittest discover -s os/tests -p test_grub_bls.py -v` | **6 tests /0.347s, OK** after restoring standalone switch code fence | Existing unchanged switch-block/bundle assertion and GRUB identity/selector fixtures. No physical menu proof. |
| WSL full `python3 -m unittest discover -s os/tests -v`, initial existing suite | **315 tests /328.955s**, `FAILED (failures=2, errors=9)`; **307 passed**, eight distinct host-limited tests, no skips | Same package-14 limitations: Pillow greeter (3), privileged Homebrew (3), sysusers (1), DrvFS mode (1). Nine error records include cleanup duplicates. |
| WSL full discovery after rewrite, before switch-fence fix | **323 tests /275.829s**, `FAILED (failures=3, errors=9)` | Also caught the existing test requiring `switch` alone in its code fence. Fixed the document, not that assertion; focused six-test rerun passed. |
| WSL final full discovery | **323 tests /321.395s**, `FAILED (failures=2, errors=9)`; **315 passed**, the same eight distinct host limitations, no skips | The switch-fence regression is resolved; only the unchanged host limitations remain. |
| `pwsh -NoProfile -File os/tests/owner-tools.Tests.ps1 -Bundle os/owner-tools/payload -Work .work/15/powershell-copy` | `PASS 15 destination refusals with zero writes; copied payload equals source`; manifest fingerprint unchanged | Synthetic Windows copy/bundle guards; no removable-media write or live disk query. |
| `pwsh -NoProfile -File reviews/10b-own-ssd-fixes/test-install-record.ps1` and Windows `powershell -NoProfile -File` of same script | Each: **All 78 checks passed**; PS7 **7.6.9**, Windows PS **5.1.26100.9711** | Synthetic inventory/decoder/comparison and unelevated pre-check; no disk/firmware query or configuration change. |
| `mod/gradlew.bat build runClientGameTest`, sequential run 1 | **BUILD FAILED in 10m 50s**, `Timeout has been exceeded` in client task; 38 required server game tests and 45 JUnit tests had passed | Client stopped progressing during world shutdown after fresh-world test 2/3. Does not qualify two consecutive client passes. |
| Same full command, accidental overlapping invocation | **BUILD FAILED in 13s**, `deleteGameTestRunDir` locked logs | Operator scheduling error; excluded from independent client evidence. No test assertion was changed. |
| Same full command, run 2 after run 1 ended | **BUILD SUCCESSFUL in 8m 5s** | Complete existing client tests passed once. Earlier timeout remains an unresolved instability, not green evidence. |
| `mod/gradlew.bat build` | **BUILD SUCCESSFUL in 38s**; 17 tasks, 3 executed/14 up-to-date | Full build passes; retained JUnit XML has **9 suites /45 tests /0 failures/errors/skips**. |
| `mod/gradlew.bat --stop` | `Stopping Daemon(s)` / `1 Daemon stopped` | No Gradle daemon remains from this run. No other Gradle version was invoked. |
| Pinned scanner download/version | **8.21.2**; publisher archive SHA-256 **f238c85e5f47e18fac779ce71ee11091cf70a0a8fb4415f165efba2800eef133** matched the release checksums | Own Windows portable copy downloaded/verified under ignored `.work/15/gitleaks`; no other worktree/system installation used. |
| `gitleaks.exe git . --log-opts=--all --redact=100 --no-banner --log-level info --report-format json --report-path .work/15/gitleaks/pre-report.json` | At implementation/test commit **eea9986**: **528 commits scanned /49.2s /no leaks found**, exit0 | All reachable refs/history, not only the diff. Final report commit is rescanned before the only push; final receipt goes in the draft PR without a receipt push. |
| Local link/source/scope checks and `git diff --check` | **PASS**; all changed design/source-report links resolved; runtime paths unchanged | No browser or live hardware test. The existing os/README hardware-check link was retargeted to the renamed step 7. Seven full-file tag-source hashes and dated source links are in [SOURCES](SOURCES.md). |

WSL uses the existing Ubuntu Python/Bash with TMPDIR under this worktree and a local `sudo` shim that exits126. This deliberately respects the no-admin rule; it does not skip the privileged tests. No Pillow/system packages were installed and no DrvFS mode assertions were relaxed.

### Screenshots

The original package 15 client suite ran: **one timeout, then one sequential pass** (with an accidental overlapping invocation excluded). The 27 dev-client captures were removed in 15b because they are unrelated to this docs-only package. Other tracked screenshots remain unchanged. No physical installation, Media Writer or owner-followability screenshot is claimed; no new visual behavior was implemented.

### Word counts

Whitespace-separated words from UTF-8 Markdown, including tables/code/URLs, comparing `5156f5f` to the initial package 15 files at `562e29c` (before 15b):

| File | Before | After |
| --- | ---: | ---: |
| INSTALL | 7,138 | 3,117 |
| EMERGENCY | 2,049 | 637 |
| INSTALL-RECORD | 2,568 | 2,715 |
| OS-BASE | 11,611 | 11,498 |
| INSTALL-REFERENCE (new) | 0 | 1,541 |
| INSTALL-PROCEDURES (new) | 0 | 1,353 |
| INSTALL-STATUS (new) | 0 | 1,110 |

Initial checklist/card total: **9,187 → 3,754**. Including the three new supporting documents: **7,758** words. Checks have been retained and reorganized; length is not a physical usability result.

## Not verified

All physical/novice gates stay open in the [single current table](../../docs/INSTALL-STATUS.md#current-gates): unaided phone/30-second trial, both FnLock states, expendable-media cancellation/restore/copy/eject/boot, damaged-battery refusal/seating/parts/firmware, record helper on real Windows/UEFI, tools lifecycle/forgotten stick, live KDE typing, password/layout failure/revert, NVIDIA deferred completion with unchanged deployment state, token negative authentication/pull/offline boots, P1a hardware/logind/independent Windows. Package 14's complete VM route remains pending for the brief's 1 November rerun. Direct US→stock rollback has not been runtime-verified. No document check closes any of these.

## JUDGMENT-CALL

No new hard-to-undo product decision. Existing owner decisions are preserved. The safe reversible navigation choice is to treat step 6's gate as a visible conditional that the reader must honor, rather than implying that unchanged tools can prove a physical Windows boot. Alternatives requiring runtime tracking are out of scope and would need renewed qualification. Later procedure command locations changed, not command text or behavior; revising those locations later costs documentation/link/test updates only.

## PLAN-GAP

Overall local verification cannot be reported green: the unchanged client suite timed out once and passed once, and eight existing OS tests require capabilities disallowed/unavailable on this host. No assertion was weakened and no runtime/tool/harness/image/workflow change was made to hide either result. The report preserves them for review instead of claiming all tests pass. No new council finding required an owner-tool change.

The retirement negative test cannot be demonstrated in every abandonment state by existing `login`, which requires prepared stock. As the brief permits, it remains an explicit supervised disposable-credential physical gate; GitHub list disappearance/local deletion is not reported as that proof.

## Budget, branch and delivery

No workflow was dispatched. Preliminary read-only billing `GET organizations/Ares-Empire/settings/billing/usage/summary?year=2026&month=10` reported **1,766/2,000 used; 234 free; net quantity/amount0**. A fresh same-period read must still show at least150 free before the single final push. No push is allowed if that check or the final full-history scan fails. Draft PR is against main; branch is stacked on package 14's pushed head `5156f5f` plus the preserved local brief. Final head/scan/billing receipt and PR URL are recorded in the PR/final response, avoiding a second report push. Never merge.

## Open questions

None blocking the document implementation. Physical release, complete package-14 VM acceptance, the repeated-client instability and host-only verification limits remain for the owner/maintainer gates above; this draft does not authorize installation.
