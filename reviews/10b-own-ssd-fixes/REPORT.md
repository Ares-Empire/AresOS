# 10b — Own-SSD council fixes

2026-10-22 · `pkg/10-own-ssd-install` · existing [draft PR #9](https://github.com/carlsenares/AresOS/pull/9). **Physical installation remains NOT RELEASED.** This follow-up changes the guide, supporting design text and verification/report files; no mod or OS implementation changes.

**Done:**

- [INSTALL](../../docs/INSTALL.md): battery-damage inspections before opening and immediately after lifting the cover, with stop/no-handling/no-reconnection/support instructions, repeated for optional removal. Model-specific 2280 fitting sequence and linked Lenovo close-up, angled insertion, full/partial seating checkpoints **before** tightening, and no screw-assisted seating. Live German layout/test before Konsole, separate installed-system layout, mapping-based destination/review checks. Default undo now verifies direct Windows/original Micron EFI, restores Windows default and checks an unattended restart while retaining Crucial and its data. Physical removal/erasure are optional extras.
- [INSTALL-RECORD](../../docs/INSTALL-RECORD.md): retained complete inventory with added parent-device field, compact tree and annotated fictitious example, per-session physical label/model/serial → live path → exact installer entry table, and explicit manual PASS/FAIL checkpoints/results. Rejects ambiguous identity, unexpected Crucial partitions/data and any proposed Micron/EFI action. Record B repeats administrator-terminal navigation and checks the current token before collection, with a corrective STOP message.
- [OS-BASE](../../docs/design/OS-BASE.md): §8/Appendix C agree with default leave-installed undo; repaired the renamed §9 link. The old [package 10 report](../10-own-ssd-install/REPORT.md) remains historical evidence with a link to this follow-up.
- [CHANGES](../councils/2026-10-22-own-ssd/CHANGES.md) maps all six council findings to fixes and outstanding physical checks. New facts have dated primary citations. Existing release gates remain closed, with explicit novice test cases; same-drive fallback files are unchanged.
- [Verification driver](test-install-record.ps1): runs all existing synthetic checks unchanged, then executes **only** the documented elevation pre-check in an ordinary terminal and verifies the exact STOP message/no PASS output. The [documentation checker](../10-own-ssd-install/check-docs.py) now also covers the follow-up report and council change map.

**Verified:**

1. From the worktree root, with process-local compiler temporary files inside the worktree:

   ```powershell
   $env:TEMP = (Resolve-Path .work/tmp).Path
   $env:TMP = $env:TEMP
   pwsh -NoProfile -File ./reviews/10b-own-ssd-fixes/test-install-record.ps1
   powershell.exe -NoProfile -File ./reviews/10b-own-ssd-fixes/test-install-record.ps1
   ```

   Both exited **0**, on **PowerShell 7.6.7** and **Windows PowerShell 5.1.26100.9711**. Each printed:

   ```text
   All 77 synthetic checks passed (including the 26 existing regression checks). No hardware queries or writes executed.
   PASS: record B refuses an unelevated terminal before collection
   All 78 checks passed (77 synthetic regression checks and 1 unelevated pre-check). No disk/firmware queries or configuration changes executed.
   ```

   Full outputs: [PowerShell 7](tests-pwsh.txt), [Windows PowerShell](tests-windows-powershell.txt). Actual invocation redirected each process's output with `*>` to its respective file, captured `$LASTEXITCODE` and returned it. The inherited suite also parses all active owner PowerShell blocks without running them. The native reader is compiled but never invoked; all inventory tests use fixtures. No tests were weakened/skipped. The additional check reads only this process's token and executes the pre-check prefix; it never evaluates the rest of record B.

2. Documentation verification from the worktree root:

   ```powershell
   python reviews/10-own-ssd-install/check-docs.py
   git diff --check
   ```

   Both exited **0**. The checker printed `PASS: 9 Markdown files; 96 local links/anchors; reference labels and fences; 6 Linux blocks pass bash -n (not executed).`, saved in [docs-check.txt](docs-check.txt). It checks local links/anchors, reference labels, fenced blocks and Linux command **syntax only** with `bash -n`; no Linux storage command is executed. The whitespace check printed nothing. `git diff --name-only c7d1965 -- docs/INSTALL-SAME-DRIVE.md docs/INSTALL-RECORD-SAME-DRIVE.md docs/install-tools/InstallRecord.psm1 mod os` also printed nothing: fallback files, existing helper and implementations remain unchanged.

3. Primary-source review **2026-10-22**: cached official Lenovo LOQ HMM, printed p. 3 and Figure 9 (PDF pp. 9/41), visually inspected; Lenovo immediate-action safety guidance; Kingston M.2 insertion guidance; KDE Layouts; Microsoft `WindowsPrincipal.IsInRole`; util-linux `lsblk`; cached Bazzite destination/review examples. Citations and limits are in the changed docs. No new upstream images/PDFs committed. The web reader could not retrieve the Lenovo PDF; its previously downloaded official copy was used. Crucial's PDF retrieval failed (web 502; direct download certificate date error), so the guide cites accessible Kingston guidance instead. No certificate bypass or software installation was used. Existing PyMuPDF rendered the safety page for inspection; its deprecated `fitz` import warned, but rendering succeeded.

4. No Gradle/client suite run, as **brief 10b explicitly requires**. No Gradle process/daemon was started in this follow-up, so there is none from this run to stop. The historical package 10 game-test failure is not converted into a green result by these documentation checks.

5. `git commit -m "Address own-SSD council safety and followability findings"` created **`4243fb5`**. `git push origin pkg/10-own-ssd-install` exited **0**, printing `c7d1965..4243fb5  pkg/10-own-ssd-install -> pkg/10-own-ssd-install`. This report, the historical-report cross-reference and captured evidence are committed/pushed separately. Existing PR #9 is used; no new PR or merge.

**Not verified:**

No disk/partition/encryption/firmware inventory on this laptop, administrator process, USB writing, hardware fitting/removal, installer, boot changes, Windows setting changes, real Minecraft/Lunar access or new system software. No human/novice or disposable two-disk VM rehearsal was performed. The elevation **success** branch and fresh-reboot UI navigation were not exercised in an elevated process. Syntax/fixture passes do not establish physical installation safety.

Still gated: exact ISO/writer/tool versions/hashes and live keyboard menus; all Micron write audits through install/rebase/rollback/undo; original Windows boot target/live helper qualification; actual laptop slot/thermal parts/storage screen; Lenovo/service-confirmed seating close-up and expendable-hardware fit checks; battery-photo and disk-renumbering/unexpected-partition/Micron-EFI novice cases; image/account/rollback handoff from brief 06. Upstream diagrams/screenshots are references, not trial evidence.

**JUDGMENT-CALL:**

- Default undo follows brief 10b: leave Crucial installed and retain Linux/data after verified Windows return. Removal/erasure remain optional. This replaces package 10's removal-first choice, avoids unnecessary handling and is reversible by selecting the recorded Linux entry; reuse/erasure still needs the separate checks.
- Linux/installer PASS/FAIL rows are **manual checkpoints**; Windows metadata comparison remains automated. The chair's fix and brief 10b request a clear mapping/results; a new Linux collection/installer parser would add unqualified software and live-media dependencies. None is claimed here. If the unaided walkthrough cannot reliably complete these comparisons, the gate stays closed; adding automation later costs a separately tested collector/comparator and media qualification.

**PLAN-GAP:**

- Lenovo's manual establishes the LOQ location/fixing sequence, while Kingston supplies general angled insertion. Neither establishes this unit's thermal parts or provides the requested service-confirmed seated/partial-fit close-up. That already-required physical qualification remains explicit, with no invented model-specific proof.
- The member report suggested automating detailed Linux comparisons; the chair/10b acceptance specifies clear PASS/FAIL results without prescribing a new helper. This revision retains full evidence and exposes the manual decisions rather than representing them as automatic validation. The maintainer must still validate novice followability before release.

**Open questions:**

- Can the released installer/rollback/undo route pass the complete protected-disk audit and novice checks? Which exact fitting parts, seating close-up and firmware screens are qualified for this unit? These remain the existing release work, not permission to install.
- A fresh review must assess this revision; the original council findings are addressed in the documents, not independently re-reviewed by this author. PR #9 remains unmerged.
