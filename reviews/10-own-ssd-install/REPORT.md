# 10 — Own-SSD installation guide

2026-10-22 · `pkg/10-own-ssd-install` · [draft PR #9](https://github.com/carlsenares/AresOS/pull/9), against `main`. **Not merged. Physical installation remains unreleased. The full two-run game-test gate is not green.**

Historical report for package 10. The later [10b report](../10b-own-ssd-fixes/REPORT.md) and [council change map](../councils/2026-10-22-own-ssd/CHANGES.md) supersede its pending-council status and removal-first undo choice; the original test results below are preserved. Brief 10b explicitly excludes another Gradle run.

**Done:**

- [INSTALL](../../docs/INSTALL.md): dedicated Crucial identification, Lenovo HMM fitting sequence (rear trim, lower case, battery cable, 2280 fixing, reassembly), thermal-parts uncertainty and stop conditions, firmware detection of both drives. Two distinct USB sticks, German Windows recovery/encryption/power checks, current Bazzite live automatic whole-Crucial installation with a new Crucial EFI, explicit final-write review, F12/default order, and Crucial removal or partition-table clearing for undo. No Windows shrink/extension. The owner sequence is shorter than the old guide despite adding physical fitting; no manual Btrfs/sector arithmetic.
- [Record](../../docs/INSTALL-RECORD.md) and [helper](../../docs/install-tools/InstallRecord.psm1): retain the existing Windows inventory/native reader; add `Confirm-AresWindowsDiskUnchanged`, which compares saved records only. Check disk identity, every partition GUID/type/boundary, C: identity and the original Windows EFI boot target. Allow renumbering and normal free-space changes. Explain that layout equality is not filesystem-content equality, and ordinary JSON/compiler temporary files are writes even though the helper does not mutate storage/boot configuration.
- [Same-drive guide](../../docs/INSTALL-SAME-DRIVE.md) and [same-drive record](../../docs/INSTALL-RECORD-SAME-DRIVE.md): preserved historical procedures/source dates, adjusted links and explicit separate-authorisation gate. The record's prior “no disk action” wording is corrected as requested by the earlier council delta.
- [OS-BASE](../../docs/design/OS-BASE.md): §8 and Appendix C now require Crucial-only storage/EFI and whole protected-disk audits. Reconcile dependent introduction/owner-decision, §3, risk and acceptance/package-table assumptions. Keep inherited image-delivery research dated 2026-10-21 and the image/account/rebase work with brief 06. README fixes two contradictory leftover “second SSD later” / “before shrinking” statements.
- Dated primary sources and upstream screenshot links are in the guide/record. No upstream manual/images were committed. The safety/followability council is the next review, not a review performed by the author.

**Verified:**

1. Synthetic helper regression tests, from the worktree root, with process-local TEMP/TMP inside `.work/tmp`:

   ```powershell
   $env:TEMP = (Resolve-Path .work/tmp).Path
   $env:TMP = $env:TEMP
   & ./reviews/10-own-ssd-install/test-install-record.ps1
   powershell.exe -NoProfile -File ./reviews/10-own-ssd-install/test-install-record.ps1
   ```

   Both exited **0** on PowerShell **7.6.7** and Windows PowerShell **5.1.26100.9711**. Each printed `All 77 synthetic checks passed (including the 26 existing regression checks). No hardware queries or writes executed.` Outputs: [PowerShell 7](tests-pwsh.txt), [Windows PowerShell](tests-windows-powershell.txt). The existing suite compiles the native reader without invoking it and replaces hardware query functions with fixtures. New tests cover unchanged JSON records, renumbering/reordering, 512/4096-byte sectors, each protected field, changed C:/recovery/MSR, added partitions, missing/duplicate/malformed identity and Windows pointing at the other disk/loader. No test was weakened or skipped.

2. Mandatory full build/client test command, **twice**, from `mod/`, using existing Java and Gradle caches:

   ```powershell
   $env:JAVA_HOME = 'C:\Program Files\Eclipse Adoptium\jdk-25.0.4.101-hotspot'
   # TEMP/TMP were already set to the worktree's .work/tmp above.
   .\gradlew.bat build runClientGameTest --no-daemon --console=plain
   .\gradlew.bat build runClientGameTest --no-daemon --console=plain
   .\gradlew.bat --stop
   ```

   | Run | Exit / exact result | Interpretation |
   |---|---|---|
   | [First](gradle-first.txt) | **1**, `BUILD FAILED in 1m 40s`; `19 actionable tasks: 18 executed, 1 up-to-date` | Build/server/unit work completed; client test failed: `07b chest pin: apps.json stayed unpinned; 07b chest unpin: apps.json stayed pinned`. |
   | [Second](gradle-second.txt) | **0**, `BUILD SUCCESSFUL in 7m 6s`; `19 actionable tasks: 4 executed, 15 up-to-date` | Same unchanged game code/tests; 07b and remaining client checks passed. Unit `:test` was UP-TO-DATE this time. |
   | [Stop](gradle-stop.txt) | **0**, `No Gradle daemons are running.` | Wrapper Gradle **9.8.0** was the only Gradle version used. |

   Both server runs printed `All 22 required tests passed :)`. First-run JUnit XML totals: **45 tests, 0 failures, 0 errors, 0 skipped**, 9 classes. The first client assertion originates in existing [RealAppsFixesClientGameTest](../../mod/src/gametest/java/dev/aresos/test/RealAppsFixesClientGameTest.java). **One pass after one failure remains a failure under AGENTS.md.** Its cause is not diagnosed/fixed here: brief 10 excludes game/OS changes. This needs a game-package follow-up; do not report this branch universally green or mask the assertion. No game source or tests changed from baseline `05715f0c65ac26bde9eab7c43408fa0283417fca`.

   [Second-run chest screenshot](screenshots/second-run-chest-unpinned.png) was generated by the existing client test and visually inspected; it is game-regression evidence, not installer/EFI proof. Other generated game screenshots were kept in ignored `.work/game-screenshots/`, and the one rewritten tracked historical screenshot was restored. No installation screenshots were captured; linked upstream screenshots are clearly identified as examples.

3. `python reviews/10-own-ssd-install/check-docs.py`: exit **0**, validates current/archived guide links and anchors, reference labels, balanced fences and **6 Linux blocks using `bash -n` only**. Before the report was added it printed `PASS: 6 Markdown files; 53 local links/anchors; reference labels and fences; 6 Linux blocks pass bash -n (not executed).` The final report-inclusive result is in [docs-check.txt](docs-check.txt). PowerShell command blocks in the active guide/record parse in both synthetic test runs. `git diff --check` and staged-diff checks passed with no whitespace errors. The checker initially treated `[MSR]` inside an ASCII diagram as a citation; it now excludes fenced code from citation parsing.

4. Primary-source research checked **2026-10-22**: Lenovo HMM/PSREF and firmware keys, current Bazzite documentation and visually inspected destination/review screenshots, Microsoft recovery/status/power/hash/storage/firmware APIs, UEFI/EDK II, util-linux/efibootmgr, Fedora Media Writer and GParted. Lenovo's PDF failed through the web reader but downloaded successfully from its official URL using `Invoke-WebRequest`; extracted with `pdftotext`, rendered/inspected with the existing PyMuPDF after `pdftoppm` proved unavailable. No dependencies installed. Broken guessed manual/lsblk source paths were replaced with verified official paths; inaccessible pages were not used as evidence. Citations distinguish dates and external capability from unperformed qualification.

5. Logical commits before the report: `26c52eb` (pure comparison + fixture tests), `a63002e` (owner guide, fallback, design and checks). `git push -u origin pkg/10-own-ssd-install` exited **0** and created the remote branch. `gh pr create --base main --head pkg/10-own-ssd-install --draft --title "Document AresOS installation on its own SSD" --body-file .work/pr-body.md` exited **0**, returning PR #9. This report and the evidence are committed/pushed separately on the same branch.

**Not verified:**

No physical disk/partition/encryption/firmware inventory was queried; no administrator process, USB writer, installer or firmware UI was run. No Windows settings, disks, boot configuration, real Minecraft folder or Lunar Client were touched; no system software installed. The Gradle dev clients used this worktree. No physical fitting/media boot, two-disk installer VM, rebase/rollback or unaided novice rehearsal was performed. The helper's actual Windows/UEFI API path remains unqualified.

Specifically open before release: brief 06 image/digest/account/UID/rebase/rollback; exact current live ISO/writer/GParted hashes and rehearsal; independent EFI and complete Micron write audit (including fallback files); real helper/USB tests; model-specific thermal/fixing guidance and firmware storage-screen evidence; council review. After the guide is released, the owner must still confirm this unit's slot vacancy/parts/both-drive detection before any OS install. A metadata comparison is not proof that no filesystem bytes changed.

**JUDGMENT-CALL:**

- **Use current automatic whole-Crucial installation, with ISO-provided sizes.** Reject the old mandatory legacy/manual layout and all shared-ESP routes. This follows the new brief and removes the hardest novice steps; exact exclusive targeting still needs rehearsal. Changing later before installation costs docs/qualification work; changing an installed layout may require backing up/reinstalling Crucial. The Micron is left installed, not physically disturbed; selected-device UI is not a hardware write barrier.
- **Keep Windows default for the initial trial; remove Crucial as the simplest undo.** Persistent AresOS-first selection remains documented. The alternative to removal is an explicitly identified Crucial GPT reset in live GParted, not a Windows `diskpart clean` command or Windows EFI surgery. Its Apply acts immediately; reset is not secure sanitisation. These are reversible choices until valuable Linux data exists, and both undo paths require the original Windows boot-target check.
- **Retain the same-drive fallback as inactive history.** Its shrink cannot silently override the owner's newer hard rule. Reactivation needs an explicit new decision/exception and fresh qualification, not an automatic response to a failed install check.

**PLAN-GAP:**

- Brief 06 still asks for a **legacy** ISO and old guide section numbers; this brief prefers **current live** whole-drive installation. Its image/account/rebase handoff must be tested against the same qualified ISO/layout. The frozen brief was not edited and no guessed migration command was supplied.
- One Windows-visible disk is not proof of an empty/usable slot. Lenovo's HMM supplies the removal sequence/screws but no unit-specific SSD pad thickness or separate shield requirement. Exact parts and this unit's firmware storage-information screen remain explicit gates, not invented details.
- “Windows unchanged” needs two different checks: metadata/current-boot comparisons on the owner laptop, and offline whole-disk content comparison during disposable installer qualification. Normal Windows boots cannot have a byte-identical filesystem, and metadata alone cannot prove an installer left EFI files untouched.
- The repository's two-run green requirement conflicts with the observed 07b intermittent failure while this brief forbids game-code work. Evidence is preserved and the PR is draft; no false green claim or assertion change.

**Open questions:**

- Can the selected current live ISO demonstrably keep **all** installer/rebase/rollback/undo writes off a connected Micron-like disk? If not, qualify a revised route before release.
- Which fixing/thermal parts and storage-information screen apply to this exact laptop? Confirm with Lenovo/service support; owner confirms physical vacancy during fitting.
- What causes the existing 07b chest pin/unpin first-run failure? Assign separately before relying on a repeatable green game baseline.
- Safety/followability council verdict is pending. No further own-SSD purchase or Windows-resize decision is assumed.
