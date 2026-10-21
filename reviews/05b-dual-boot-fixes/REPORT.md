# 05b — Dual-boot council fixes

2026-10-21 · `pkg/05-dual-boot` · existing [PR #5](https://github.com/carlsenares/AresOS/pull/5), against `main`; no merge.

**Done:**

- `docs/INSTALL.md`: one owner route, two labelled USBs, concrete German recovery-drive creation and boot test after encryption checks, one ISO-file writer, one hibernation path, corrected partition-then-subvolume sequence, expected tree/pending operations, screenshot links, Lenovo default-boot steps and stricter undo. Research/qualification work is outside the action sequence. The pre-shrink gate stays closed.
- `docs/INSTALL-RECORD.md`: mandatory Windows/Linux inventory, one comparison sheet, exact read-only commands, original ESP identity and automatic endpoint/headroom calculation. Distinguishes partition GUID, filesystem UUID and disk GUID; explains the hidden MSR. Before undo, ties the **actual Windows BootCurrent** to its GPT partition GUID/bounds and Microsoft loader, then cross-checks that saved entry from live Linux.
- `docs/install-tools/InstallRecord.psm1`: small owner-operated inventory/record helper, needed to make the binary firmware target and boundary calculations usable without manual interpretation. Importing does not query hardware. It exposes no disk/firmware write action; the native reader temporarily enables and restores only its process privilege. Errors stop the procedure. Tests compile the native code but never call a native method.
- `docs/design/OS-BASE.md`: current automatic/shared-ESP route compared honestly with manual/independent-ESP install and undo; retain the latter. Updated safety/acceptance contracts and media gates. `README.md` now requires two sticks rather than claiming one suffices.
- [Council CHANGES](../councils/2026-10-21-dual-boot/CHANGES.md) maps all seven findings. Original briefs, verdict/member reports, OS image/rebase implementation and Minecraft code are unchanged.

**Verified:**

- From `mod/`, using the existing JDK and worktree-local cache:

  ```powershell
  $env:JAVA_HOME = 'C:\Program Files\Eclipse Adoptium\jdk-25.0.4.101-hotspot'
  $env:GRADLE_USER_HOME = Join-Path (Get-Location).Path '..\.work\gradle-home'
  .\gradlew.bat build --no-daemon --console=plain
  .\gradlew.bat --stop
  ```

  Build exit **0**: `BUILD SUCCESSFUL in 20s`; `16 actionable tasks: 3 executed, 13 up-to-date`; `All 12 required tests passed :)`. `:test` was **UP-TO-DATE**; unit tests were not newly executed. No test was weakened or skipped. Wrapper Gradle **9.8.0** only. Stop exit **0**, `No Gradle daemons are running.` [Build output](gradle-build.txt), with line endings/trailing whitespace normalized. Existing missing-item fallback warning remains non-fatal.
- Synthetic helper tests, from the worktree root:

  ```powershell
  .\reviews\05b-dual-boot-fixes\test-install-record.ps1
  powershell.exe -NoProfile -File .\reviews\05b-dual-boot-fixes\test-install-record.ps1
  ```

  Both exited **0**, each printing `All 26 synthetic checks passed. No hardware queries or writes executed.` Tested with PowerShell **7.6.7** and Windows PowerShell **5.1.26100.9711**; process-local TEMP/TMP pointed inside `.work/` for compilation. [PowerShell 7 output](tests-pwsh.txt), [Windows PowerShell output](tests-windows-powershell.txt).

  Coverage: byte/sector endpoints for 512/4096-byte sectors, an unrelated gap, two ESPs, moved recovery/lost MSR/wrong disk/wrong donation/headroom rejection, partition renumbering, Microsoft loader on the Linux ESP rejection, chainloading/ambiguous malformed data rejection, GUID binary decoding, native-reader compilation and full inventory with **all hardware entry points replaced by fixtures**. Owner PowerShell snippets parse without execution. These are synthetic checks, not an installation or Windows API runtime test.
- Primary-source research dated **2026-10-21**: Bazzite current/legacy/manual documentation and installer source, visually inspected upstream Btrfs parent/root dialogs, Microsoft recovery/storage/power/firmware APIs, UEFI/EDK II, util-linux, efibootmgr, Fedora Media Writer QML/readback description, GParted and Lenovo's LOQ manual. Exact new source links/dates are in the guide, record and design. Fedora's direct console-doc page was access-blocked; used the readable Red Hat Anaconda tmux documentation instead. GParted Live manual was readable through `Invoke-WebRequest` when the web reader failed. No inaccessible page is claimed as evidence.
- `python reviews/05b-dual-boot-fixes/check-docs.py`: exit **0**, printed `PASS: 6 Markdown files; 47 local links/anchors; balanced fences; 3 Linux blocks pass bash -n (not executed).` `git diff --check` and both staged-diff checks: exit **0**, no whitespace errors. These check document mechanics, not installation behavior.
- Logical implementation commits: `119c706` (record/helper/synthetic tests), `e037296` (guide/design/README/council mapping). `git push origin pkg/05-dual-boot`: exit **0**, printed `057353f..e037296  pkg/05-dual-boot -> pkg/05-dual-boot`. This report, check script and normalized evidence logs are committed/pushed as the final documentation commit on that same branch. PR #5 already existed; no replacement PR or merge was requested/performed.

**Not verified:**

No laptop disk/partition/encryption/firmware inventory was run, and no administrator process, USB writer, installer, firmware setup or recovery tool was started. No software installed, disks/boot configuration changed, image built/rebased or physical USB/Windows boot attempted. No file-backed installer VM or unaided novice walkthrough was run. No new screenshots: linked installer images belong to upstream and are not our qualification evidence. No game/client visual changes were made; mod game tests do not validate this guide.

Specifically still required before shrinking: qualified ISO/writer versions and physical UEFI media rehearsal; exact-ISO full tree/pending-action screenshots; live Windows/UEFI helper trials, including Windows on the AresOS ESP; novice identification of two ESPs/extra gap; German Windows power-state paths; owner recovery USB and actual Lenovo no-key default boot. The existing released-image/rebase/account/rollback handoff also remains required.

**JUDGMENT-CALL:**

| Choice | Alternatives / reason | Cost of changing later |
|---|---|---|
| Retain manual installation with an independent ESP | Current automatic install removes several manual steps but shares the Windows ESP and needs file-level undo. No exact qualified shared-ESP write manifest exists; the brief's safest reversible default favors separate storage. | Another documentation/installer qualification pass; migration/reinstall if changed after installation. No new layout change from brief 05. |
| Ship a read-only Windows record helper | Names/BCD screenshots do not establish the actual tested firmware target; manual EFI decoding/sector arithmetic is unsuitable for a novice. BootCurrent gives the selected entry, with GUID/path matching and failure on unknown data. | Small PowerShell/native-reader maintenance surface and mandatory Windows/UEFI qualification. Helper refusal requires reviewed read-only investigation, never relaxed deletion checks. |
| Keep physical rehearsal as a release gate | Calling a source walkthrough “rehearsed” would invent evidence; this brief expressly excludes performing media/disk operations. | Maintainer/owner must supply the real trial evidence before any shrink. |

The existing 96 GiB donation, Windows-only shrink/extension exception and disposable unencrypted trial remain proposals from brief 05, not newly exercised permissions.

**PLAN-GAP:**

1. “One rehearsed ISO-writing method” and exact qualified-ISO screenshots cannot honestly be delivered as executed evidence while this run excludes doing the media/install operations. One concrete source-checked method is now prescribed, dangerous alternatives removed, and the missing rehearsal is a named pre-shrink gate. No boot/USB success was fabricated.
2. Current automatic installation is viable upstream, but documentation does not establish its exact installed shared-ESP file manifest. Possible vendor/fallback paths are documented as source-level evidence only; a shared-ESP route cannot be approved from that alone. Any `\EFI\Microsoft` modification is forbidden. The chosen route avoids that unqualified alternative.
3. Hardware-specific values and real firmware-variable availability remain unknown because agents may not inspect the laptop's disk/boot state. The owner commands compute endpoints when run; no fabricated laptop partition numbers/GUIDs appear in the sheet.

**Open questions:**

Owner acceptance of existing layout proposals; availability of two suitable sticks and independent backup/record storage; exact qualified NVIDIA image/legacy ISO; the OS image release handoff and outstanding qualification evidence. No clarification was needed to complete this documentation follow-up within its authorised scope.
