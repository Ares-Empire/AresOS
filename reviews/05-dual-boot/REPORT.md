# 05 — Same-drive dual boot plan and install guide

2026-10-21 · Branch `pkg/05-dual-boot` · [PR #5](https://github.com/carlsenares/AresOS/pull/5) against `main`; not merged.

**Done:**

- `docs/design/OS-BASE.md`: replaced separate-drive/MOK assumptions with official Bazzite legacy USB → manual partitioning in the owner-created gap → reviewed AresOS rebase. Revised §3, §8, §10, safety Appendix C and package order in Appendix E, with corresponding recovery/test contracts and dated sources. Added P1a plain-session hardware boot before P2 Minecraft and P3 full trial.
- `docs/INSTALL.md`: owner guide with German Windows labels, backup/encryption/hibernation checks, ISO/writer choices, 96 GiB proposal, exact allowed interval, own EFI, pending-operation checks, rebase placeholder, hardware checklist, F12/Windows return and undo. It explicitly stops **before shrinking** until the image handoff is released.
- `README.md`, `CLAUDE.md`: small consistency corrections for no MOK, optional second SSD, encryption uncertainty and the proposed owner-only C: shrink/undo-extension exception. Agent disk/boot prohibitions remain.
- Read package 03 through Git objects at `7ae41a73c7e01f871b6426a34903cde13519d110`: README, Containerfile, workflow, base manifest, build script, guest checks and VM provisioning. No other worktree was accessed. No OS code, installer, image, package visibility or real laptop configuration was changed.

**Verified:**

- Inside `mod/`, using the existing JDK and an isolated worktree Gradle cache:

  ```powershell
  $env:JAVA_HOME = 'C:\Program Files\Eclipse Adoptium\jdk-25.0.4.101-hotspot'
  $env:GRADLE_USER_HOME = Join-Path (Get-Location).Path '..\.work\gradle-home'
  .\gradlew.bat build --no-daemon --console=plain
  ```

  Exit **0**; `BUILD SUCCESSFUL in 1m 51s`; `16 actionable tasks: 15 executed, 1 up-to-date`. Printed `All 12 required tests passed :)` and **13 unit-test PASSED** results. Full output (line endings/trailing whitespace normalized): [gradle-build.txt](gradle-build.txt). Fresh game-test startup logged missing `server.properties`/`eula.txt`; the intentional missing-item fallback warned; Gradle reported deprecations for Gradle 10. None failed the build, and no tests were changed.
- Setup corrections before that build: bare `java -version` was unavailable on PATH; the existing JDK path came from the earlier repository report. The first redirected build attempt could not open `.work/gradle-build.txt` because the directory did not exist, so Gradle did not start. Created the worktree-local directory and reran the command above. No software installation or persistent environment change.
- `git diff --check`: exit **0**, no output for the documents. Adding the raw build log later exposed one trailing space in Gradle's daemon message; normalized log whitespace and rechecked. An inline Python standard-library check of the four changed Markdown documents printed: `PASS: 4 Markdown files; 14 local links/anchors; 246 source references; balanced code fences.` This checks document mechanics, not installation correctness.
- Primary-source web research checked **2026-10-21**; dated links are in the guide and design Appendix F. Read Bazzite current/legacy/manual/dual-boot/FAQ/rebase/rollback docs, Microsoft storage/encryption/power docs, GitHub registry/billing/release docs and relevant tool documentation. Fedora's installation page was access-blocked; an initially wrong WirePlumber URL was corrected to its readable `/man/wpctl.html` page. No inference from an inaccessible page is presented as evidence.
- `git push -u origin pkg/05-dual-boot`: exit **0**, new branch and tracking set. `gh pr create --base main --head pkg/05-dual-boot --title "docs: plan same-drive dual boot and early hardware first boot" --body-file .work/pr-body.md`: exit **0**, printed the PR #5 URL above.
- `.\gradlew.bat --stop`, with the same JDK and isolated cache: exit **0**, `No Gradle daemons are running.` Only wrapper Gradle 9.8.0 was used; its single-use build daemon exited. No shared-cache daemon was stopped.

**Not verified:**

No USB writing, disk/encryption inspection, partitioning, firmware changes, image build/rebase, VM installer rehearsal, hardware boot/driver/network/audio/input test, backup restore, undo or Windows return was performed. No client game test or screenshots: this package changes documentation only. The existing mod's server/unit build tests do not validate the install guide. P1a requires the owner on hardware; P2/P3 still require playing the desktop/app/save/restore sequence, checking the actual NVIDIA game renderer and ordinary Windows return.

**JUDGMENT-CALL — owner review before merge/installation:**

| Proposed choice | Alternative rejected / reason | Cost of changing later |
|---|---|---|
| 96 GiB total; preserve at least 60 GiB and 15% free on resulting C: | A larger Linux allocation would eat Windows headroom; a smaller one constrains retained deployments, apps and temporary backups. Estimates require release-size checks. | Storage migration/reinstall may be needed; no Linux-side resizing of Windows. |
| Own 1 GiB EFI, 2 GiB boot, remaining Btrfs | Sharing Windows EFI violates the boot-file boundary and complicates removal. Bazzite's smaller EFI example gives less headroom. | Backup/reinstall if layout needs changing. |
| Btrfs root/var/home subvolumes, replacing a distinct home partition | Follow Bazzite's documented layout and share limited free space. A separate home partition offers a clearer reformat boundary but rigid quotas. | Selective recovery must be proven; formatting the Btrfs parent loses home. Later repartitioning requires backup/restore. |
| Private GHCR for first delivery, subject to current billing exception | Public images disclose content and need publication approval; local builds consume scarce disk/time; release assets need splitting/import. No publication occurred. | Change image transport, authentication and qualified rebase recipe if pricing/policy changes. |
| Windows-first, F12; permit recorded Linux NVRAM entry/order changes | Standard installation cannot promise all firmware variables unchanged. Optional Windows-in-GRUB adds coupling for no first-trial benefit. | Owner can change order/menu policy later; preserve Windows files throughout. |
| Only owner C: shrink and undo-extension in Windows Disk Management | Literal “never resize Windows” contradicts the required shrink and reclaim path. Linux never receives this exception. | Review/reword policy; no agent authority to perform either action. |
| Disposable unencrypted Linux first trial, AC/lid-open | Valuable data, unattended/battery use and suspend need later encryption/power qualification. | Encryption later may require reinstall; keep real data off this prototype. |

**PLAN-GAP:**

1. The brief's **500 MB private-storage premise is incomplete**: [GitHub currently exempts container-registry storage/bandwidth](https://docs.github.com/en/billing/concepts/product-billing/github-packages) (checked 2026-10-21). Private GHCR is therefore an additional, recommended option; recheck terms at publication. Actions quotas remain separate.
2. Bazzite's manual partitioner is on the **legacy ISO**, not the current automatic-only installer. The guide specifies that route; unavailable/mismatched media is a stop condition.
3. Current [Bazzite FAQ](https://docs.bazzite.gg/General/FAQ/) assigns RTX GPUs to `bazzite-nvidia-open`; the inspected image branch pins `bazzite-nvidia`. Hardware qualification must resolve the discrepancy without silently changing OS pins in this docs package.
4. Package 03 builds a **fresh bootc VM**, uploads evidence only, and supplies no published image or stock-Bazzite migration. The rebase needs tested backend transition/rollback, inherited configuration/update reconciliation and recovery-account provisioning (`ares` UID 1000 is locked and non-admin). These are release blockers for performing the guide, not omissions hidden behind a guessed command.
5. Same-drive use invalidates whole-disk deny/isolation/hash rules: the GPT must change, while protected Windows partition bytes/GUIDs/boundaries must not. Standard firmware entry/order changes are distinguished from forbidden Windows boot-file changes. Undo can extend C: only while the original donated interval remains immediately adjacent; never move a recovery partition to force it.

**Open questions:**

Owner acceptance of the proposals above; actual disk identity/layout and encryption status; qualified NVIDIA image/ISO pair; released image source/signature and tested rebase/account recipe; independent backup/recovery destination and later encryption policy. No answer was required to finish this documentation brief; all physical actions remain gated.
