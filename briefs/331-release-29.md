# 331: Release 29 (the indicator, Chrome Control, Deskflow and the signed update)

Board brief 331. Lead `linux-aresos`. Branch `pkg/331-release-29`. Start the diff and walk from main now. The cut needs 18c-b and B330 merged. B321 rides under item 6's cut conditions.
B329 rides if merged by the cut. The baseline below is fetched main `a9863055`. (`HANDOFF.md:13`, `HANDOFF.md:97`)

**Builder and reviews.** One fresh Codex builder per slice, about 80 tool calls each. Model and reviewer choices are in Steps. One fresh Codex `gpt-6.2-sol` high brief review while Claude's allowance is
tight. The lead decides what to fold in. Recheck must-fixes and the affected scope. Use a fresh reviewer for each code review and name the reviewed head. **Bar (decision 24).** “Reasonably safe”. Fix real
harm or a sure failure. Put low-harm edge cases in Known limits. (`briefs/323-r29-image.md:5`, `docs/REVIEW.md:3`, `docs/design/CONTROL.md:348`)

## What changes

1. **What rides from main.** Use R28's signed digest `aa97b2d5…`, source `7d5fbbf2` and base `ed93d215…` as the reference. Keep the same base. T475 records the laptop on R28, R27 as rollback, corrected
   stock pinned, R13 gone and tools v5 `df89ac33…`. T475 is a record change. (`os/manifest/releases/28.json:2`, `docs/INSTALL-STATUS.md:29`)
   - **B323.** The x86_64 lock adds `gtk4-layer-shell-1.3.0-1.fc44`. Explain its RPM files and the JetBrains Mono font, licence and regenerated fontconfig caches. The Mesa EGL and Intel Vulkan additions
     are image checks of existing package files and their libraries. The checks also prove the typelib loads with the preload and fontconfig selects our font. (`os/packages.lock.json:9`,
     `os/build.sh:487`, `os/ci/image-checks.sh:829`, `HANDOFF.md:21`)
   - **311 and B323.** R28 has Fedora's labwc. Main builds the pointer-lock backport and swaps Fedora's RPM for the locked rebuild in the same layer that installed it. A later layer once lost the
     replacement binary. Explain the exact RPM swap, `packages.txt` and the installed `labwc.lock.json`. Keep the loadable bytes and RPM metadata checks in item 3. Real hardware evidence comes after the
     owner's update. (`STATE.md:224`, `os/Containerfile:18`, `os/Containerfile:34`, `os/labwc/stage.py:377`, `briefs/323-r29-image.md:9`)
   - **B320.** Explain six changed `rc.xml` key rows, the executable `aresos-level`, `aresos-indicator` and `aresos-settings`, the look pack and the Jersey 10 font and licence. Summary lines, “volume up
     also unmutes” and “brightness down stops at 1% of the backlight's maximum”. (`os/config/usr/share/aresos/labwc/rc.xml:24`, `os/config/usr/libexec/aresos-level:46`, `os/ci/image-checks.sh:570`,
     `STATE.md:175`, `HANDOFF.md:97`)
   - **25 and PR136 (324).** Explain the changed supervisor, Java wrapper, cover and shell, the black-window rule, the guardian unit, session drop-in and exact enable link. The guardian asks the game to
     save and waits within a deadline on planned stops. PR136 adds half a second of slack to the host VM's lid timestamp check. Give the unit and any audit rows their own reasons. Keep the guardian VM
     save and timeout proofs on the cut. (`os/build.sh:537`, `os/ci/image-checks.sh:55`, `os/ci/guardian_host.py:23`, `STATE.md:143`)
   - **56, 53c, 53d, 53f and PR134 (322).** Explain the jar and its records, the shell and desktop view config, and the native laptop-home executable. The jar includes 56's mouse and hotbar changes. The
     laptop home and Super search await 23c's launch wiring. PR134 handles uncertain focus after restart, invalidates stale home cursors and caps view launch checks. B316's source is on main and its image
     integration belongs to B321. Inventory the full recorded R28 source to cut diff, including any further merged changes. (`STATE.md:143`, `STATE.md:150`, `STATE.md:224`, `os/ci/image-checks.sh:797`,
     `os/build.sh:449`)
   - **Chrome, gh and the command.** The regular Chrome browser already ships in R28, along with Control Part A and its `aresos` CLI. R28's record has a Control source revision only. 18c-b adds the
     browser-side bundle and the locked GitHub CLI binary. Package 43's desktop maintenance dispatcher is separate. Its branch adds OS words, moves the Control wrapper to `/usr/libexec/aresos-control/cli`
     and changes the tools. Its route follows the decision below. (`os/manifest/releases/28.json:799`, `os/ci/release_diff.py:1693`, `control/packaging/aresos:3`, `HANDOFF.md:99`)

2. **What the late packages hand over.** Each lead gives the merged SHA, green check and review, exact expected image additions, changes and removals with reasons, and one line for the owner's summary.
   Use the final merged code and the build evidence. The following lists are the starting points.
   - **18c-b (PR76, `linux-tools`, 2026-11-21).** Merge when the PR checks and Control run `44936830501` on `b2a404cd` are green. Get the exact Control install-map and vendor delta. Inventory the
     per-build bundle, policy and host manifest under `/usr/share/aresos/chrome/`, the two root links under `/etc/opt/chrome/`, `host` and `native_host.py` under `/usr/libexec/aresos-control/chrome/`,
     `org.aresos.control.chrome-loosen.policy` and the tmpfiles rule. Chrome extends the existing `control.json` `links` map and adds `chrome_build`, `chrome_extension` and `gh`. Get `/usr/bin/gh`, its
     `LICENSE` and `gh.lock.json` with their pins. Only the binary comes from the signature-checked RPM's 240-path payload. The RPM is outside the installed RPM set.
     (`7d5fbbf2:os/build.sh:213`, `b2a404cd:os/build.sh:235-240`, `b2a404cd:os/build.sh:265`, `b2a404cd:briefs/18c-b-chrome-image.md:572-586`,
     `b2a404cd:reviews/18c-b-chrome-image/PROGRESS.md:1775-1784`)
   - **Chrome ships with the reviewed gate closed (b).** There is no separate switch. At first boot tmpfiles creates `/var/lib/aresos-control/chrome-excluded-sites.json` as `root:aresos-tools` 0640 with
     `{"format":0,"hosts":[]}`. Every Chrome read and action returns `chrome_settings_unavailable` until root writes a format-1 list. The service can never write it. The owner opens the gate later with
     `sudo tee` in the T298 live sitting, starting with C8 at the owner's actual terminal size. C8 and 28b's combined profile proof are outside the R29 gate. The combined proof gates a release containing 28b.
     (`linux-tools`, 2026-11-21, `b2a404cd:reviews/18c-b-chrome-image/PROGRESS.md:714-718`)
     Summary for the owner. “Chrome: Claude's AresOS extension now comes with the system. You'll see its A button in the toolbar, and Chrome's menu says 'Managed by your organization'. Claude's Chrome tools
     stay off until you write your never-list in a short sitting with Claude.”
   - **B330 (`linux-aresos`).** At `9a0c7349`, B330 registers the hidden `org.prismlauncher.PrismLauncher.desktop` as the default for `x-scheme-handler/prismlauncher`. Take the two paths with
     reasons and hosted proof at merge. Keep the existing cache generation. The summary says the callback is registered. Live Microsoft sign-in stays open.
     (`9a0c7349:os/config/usr/share/applications/aresos-mimeapps.list:9`, `9a0c7349:reviews/330-prism-handler/PROGRESS.md:23`)
   - **B329 (`linux-desktop`, only if merged at the cut).** Take its theme folder (37 files), 36 frame sprites, `look.json` and `rc.xml` rows for theme, switcher, Shift+Alt+Tab and mouse. Keep the Crown
     file pin. Expect the guest to use `AresOS` when B329 rides. Take the brief's summary line about the pixel frame, backward Alt+Tab and disabled title-bar scrolling. (`HANDOFF.md:15`,
     `cc158e65:briefs/329-window-frame.md:74`)
   - **B321, Deskflow (c) (`linux-desktop`, 2026-11-21).** At B321's final head, `linux-desktop` signs off on the final portal and Deskflow paths, pins and VM proof in one list with the `os/` and
     `os/ci/` commits. With B321, R29 goes straight from R28's Fedora `labwc-0.9.6-1.fc44` to `labwc-0.9.6-1.fc44.aresos2` with both patches. `aresos1` stays out of that cut. Of the 64 RPM paths, only
     `/usr/bin/labwc`, `/usr/bin/labnag` and two `.build-id` links change. The labels were fixed in `b0971656` and `ec386039` on `pkg/321-deskflow-image`.
     (`ec386039:reviews/321-deskflow-image/PROGRESS.md:469-483`)
     Inventory the Rust stage's `/usr/libexec/aresos-input-portal` and service, and check `os/input-portal/` stays out of the final layer. Get Deskflow 1.27.0 with its NEVRA, SHA-256 and dependency
     reasons. Check `/usr/bin/aresos-input-sharing` and its desktop entry, `/usr/libexec/aresos-input-sharing-set`, two polkit actions, routing in `aresos-portals.conf`, the start hook and the allow-list
     at `/usr/share/aresos/input-portal/allowed-apps`. The runtime switch is `/etc/aresos/input-portal/sharing`. (`ec386039:os/input-portal/src/trust.rs:15`, `ec386039:os/input-portal/src/sharing.rs:22`)
     Check both marked `rc.xml` chords. `W-S-Escape` is new and `W-C-Escape` now releases first. If B329 also rides, whoever merges second shows `rc.xml` and the binding tests passing on the merged tree.
     (`HANDOFF.md:97`, `briefs/321-deskflow-image.md:50`, `cc158e65:briefs/329-window-frame.md:77`)
     Summary for the owner. “Mouse and keyboard sharing with your Mac: turn it on in the Input sharing window (it asks for your password), and Deskflow starts by itself. Move the pointer past the screen's edge
     to control the Mac, with a shared clipboard. Super+Shift+Escape brings the mouse and keyboard back; laptop shortcuts and media keys go to the Mac while you're there.”
   - Add late packages in their own profile commits after the main merge. Tie each reason to the cut's source or lock. Add exact metadata and content checks for built files, update the expected `rc.xml`
     rows and guest probes, and add near-miss tests. A package landing after the cut waits for another release or a new cut with its own resolve and dry run.
     (`os/ci/release_diff.py:1230`, `os/ci/release_diff.py:1269`, `cc158e65:briefs/329-window-frame.md:76`)

3. **The R29 diff (start on main).** Add `RELEASES['29']`, `PACKAGE_REASONS_29` and `Classifier29`. Compare the complete image inventories, RPMs and units against R28. Keep R27/R28 results and source
   lists fixed. Read old locks and historical test inputs from the recorded release via `released()` or its verified source. Use `CHMOD_0755_28` and `GENERATED_28` as references for R29's own rules. The
   new scripts in item 1 already have executable Git modes. Use the configure step for any forced mode. Hold both sides of each exception to the file type, ownership, mode and xattrs that the change
   warrants. (`os/ci/release_diff.py:381`, `os/ci/release_diff.py:429`, `os/ci/release_diff.py:1693`, `os/build.sh:501`, `os/tests/test_release27.py:33`, `os/tests/test_release28.py:124`, `HANDOFF.md:28`)
   - Verify the non-ghost inventory of every added or replacement RPM, including files absent from both images. Require clean `rpm -V`. For 311 use the exact replacement NEVRA, Fedora's 64-path list, the
     two build-ID links to the binaries and byte equality elsewhere. Accept measured build-ID differences only in the reviewed binary sections and matching link names. Run the existing normalized and
     loaded-image hash checks for labwc and labnag against the four lock pins. Use the final `aresos2` pins for the B321 cut. Verify the old and new inventories independently. Add only the exact
     labwc replacement to the expected lock delta. Retain the same-name and architecture removal check. (`STATE.md:224`, `os/labwc/stage.py:377`, `os/labwc/labwc.lock.json:161`,
     `reviews/42-release-28/FIXES-3.md:9`)
   - Apply R28's completeness checks to the new baseline. Check missing and removed config, exact enable links and audit rows even when absent from the diff, typed Prism inventory and its independently
     pinned list, and compiled schemas against a deterministic rebuild. Check alternatives against the locked scriptlet mapping and both public links, including missing groups and absent slave targets.
     Validate font-cache headers and image directories for both formats. Keep generated files exact and show why each was rewritten. No broad cache, policy, systemd or bytecode allowance.
     (`reviews/42-release-28/REVIEW-2.md:44`, `reviews/42-release-28/REVIEW-2.md:87`, `reviews/42-release-28/FIXES-3.md:22`, `reviews/42-release-28/FIXES-5.md:9`, `reviews/42-release-28/REVIEW-9.md:5`,
     `os/ci/release_diff.py:1639`)
   - Treat R28's Control and UID/GID 250 as existing. Compare the old recorded install with the new validated install. Require exact coverage, including changed and missing files and the shared manifest.
     For 18c-b verify the per-build bundle against the install record, its signature and matching policy, update and host IDs, and independently validate locked vendor and gh inputs. The list under `/var`
     is guest state. Expect the tmpfiles rule in the image. The record is evidence from the passing pipeline. (`os/ci/release_diff.py:606`, `os/ci/release_diff.py:1310`,
     `reviews/42-release-28/REVIEW-10.md:7`, `pkg/18c-b-chrome:os/ci/control/release_checks.py:232`, `pkg/18c-b-chrome:os/ci/control/release_checks.py:283`)
   - Keep `-B` on Control build Python, including child calls. Keep the CLI help check under `setpriv` as nobody. R28's import caching rewrote 353 base files and `runuser` then failed at PAM. Keep
     explicit locked vendor compilation. Test the child call and discover the static checks. R28's exact historical source exception stays in R28. (`HANDOFF.md:103`,
     `reviews/42-release-28/REVIEW-11.md:7`, `reviews/42-release-28/REVIEW-12.md:11`, `os/build.sh:270`)
   - Bind the image inputs to the main cut and check Git modes. Read build inputs from the actual COPY, tar and build commands. Add `os/labwc/` for R29. Add `os/gh.lock.json` and B321's actual portal
     inputs when they land. Keep the base ancestry, OCI config, source label and mask checks. Require zero unexplained paths or other problems. Negative tests cover near misses, including missing input,
     an unreviewed unmask, a wrong merge resolution and stopped result status. (`os/ci/release_diff.py:452`, `os/ci/release_diff.py:724`, `os/ci/release_diff.py:1797`, `os/ci/release_diff.py:1836`,
     `reviews/42-release-28/REVIEW-2.md:48`, `reviews/42-release-28/REVIEW-2.md:63`, `reviews/42-release-28/REVIEW-2.md:94`)

4. **The R29 walk (start with local fixtures).** Add `release29_walk.py` and a `rehearsal=release-29` route from R28. Reuse the R28 and tools-local legs through R13 and R27 on disposable disks.
   Pin each leg to its immutable release record and tools bytes at the recorded source before moving the active pointer. Confirm R28 with v5, R27 retained, corrected stock pinned, R13 gone and the
   transaction idle. (`os/ci/release28_walk.py:698`, `os/ci/owner_vm.py:1533`, `os/ci/verify_release.py:83`, `reviews/42-release-28/PROGRESS.md:1441`)
   - Run that baseline as a read-only hosted preflight before any private upload. Verify job-token reads and exact signatures against each historical image record used by the route, including R13, R27
     and R28. The current registry preflight reads one active `release.json`. Add explicit historical targets and test them as well as the branch allowlist. Verify the pinned ISO and the served Web UI
     bundle and source map against their exact hashes in the baseline preflight. Keep the passing receipt and rerun if baseline inputs change. (`os/ci/registry_auth.py:14`, `os/ci/registry_auth.py:131`,
     `reviews/42-release-28/PROGRESS.md:1002`)
   - From R28, follow the folder and routine route with the new bundle in the stand-in origin. Compare the fingerprint in the window and guide, and require install, check and title PASS with no cached
     sudo ticket. Keep the identical-bundle no-op, equal-version mismatch and downgrade cases. Only an unchanged v5 baseline may defer real-commit comparison in a local prep fixture. Qualification
     requires equality of the real candidate trees, bundle and guide before the walk. Bind the checker and settings in the host receipt. Execute the actual submitted probe scripts in local tests with
     injected failures. (`os/ci/release28_walk.py:241`, `os/ci/release28_walk.py:755`, `reviews/42-release-28/FIXES-4.md:9`, `reviews/42-release-28/FIXES-4.md:57`)
   - Follow the console `at update`, `at title`, export, `at reboot`, F12 → Bazzite, `at check` route. In the VM prove the export result for the no-stick route. Require exact staged and confirmed digests.
     Check the shape at staging and after every boot. R27 is the one release the R29 update retires. `at previous` returns to R28 and `at forward` returns to R29. Require their own confirmations and fresh
     titles. Preserve the stock pin, protected Windows disk and boot entry, Windows firmware default and all R28 audits, including on failure. (`docs/INSTALL.md:345`, `docs/INSTALL.md:375`,
     `docs/INSTALL.md:417`, `os/ci/release28_walk.py:784`, `os/ci/release28_walk.py:839`, `os/ci/owner_vm.py:1038`)
   - Before every restart or shutdown out of R28, including the first update, forward after `previous` and failed-update recovery, check whether its world is open. If so, focus it, press Alt+F4
     (or Alt+Fn+F4) and wait for “Minecraft was closed. Nothing is wrong.” If it is missing, go to Help before restarting. Test that ordering in the walk. The VM in SETUP can check the route order,
     Terminal prerequisites and preservation of planted files. The actual Alt+F4 close, normal-close message and live world save on R28 need a manual check. (`docs/INSTALL.md:230`, `docs/INSTALL.md:406`,
     `docs/EMERGENCY.md:20`, `reviews/42-release-28/PROGRESS.md:1447`)
   - On the first R28 boot plant the schema-4 apps fixture and synthetic `level.dat` and region data. Use the real provisioner's instance links (`patches`, `libraries`, `minecraft/mods`,
     `minecraft/saves`). Compare content, owner, mode, type, link text and access by the daily user across update, previous and forward. Keep the narrow Prism mutable-file allowance. Require both
     releases' own image targets on their boots. Both ship the desktop payload. Save the game-scope/JVM probe for the end. It proves placement and `memory.high=2684354560`. Actual play stays manual.
     (`os/ci/release28_walk.py:85`, `os/ci/release28_walk.py:635`, `os/ci/release28_walk.py:689`, `reviews/42-release-28/FIXES-6.md:10`, `reviews/42-release-28/FIXES-4.md:142`)
   - While the shipped tools require a `foot` process, open the Terminal app before `at check` on starting R28, on the first R29 boot, on R28 after `previous` and on R29 after `forward`. Keep it open
     through PASS. SETUP already opens a `foot` window in the VM, so a PASS there cannot prove the owner's case with the world open. Keep the no-foot STOP check where required.
     (`os/owner-tools/owner.py:2007-2017`, `os/config/usr/libexec/aresos-desktop:33-37`)
     Check theme, fontconfig, runtime privilege, polkit and terminal PATH. After tty1 is active, reopen the exact Terminal app command from the supervisor's Wayland
     environment and the daily user's home. Check the same PID survives and retain its log. Retry only the missing-monitor case, up to the existing five
     attempts. Include negative cases for display, cwd and VT in the fake. (`os/ci/release28_walk.py:625`, `os/ci/release28_walk.py:666`, `os/ci/release28_walk.py:811`,
     `reviews/42-release-28/FIXES-4.md:37`, `reviews/42-release-28/PROGRESS.md:1867`)
   - Use the stock rewind with the preflight's exact ISO and Web UI checks, runner space check, offline first boot and pinned stock identity. Keep the verified 9p copy, loop-backed store, scratch
     cleanup and both disk audits. A changed ISO requires requalification. Save `finish_shutdown` output on failure. If the live console stalls before login, bring its transcript to the lead.
     (`reviews/42-release-28/PROGRESS.md:996`, `reviews/42-release-28/PROGRESS.md:1239`, `reviews/42-release-28/PROGRESS.md:1859`, `os/ci/owner_vm.py:255`)

5. **The R29 Control list (start with PR76's checker).** Pass these names explicitly to the bound stdin checker. Assert each result and the whole key set. Preserve output before the login-graph probe.
   (`HANDOFF.md:98`, `os/ci/release28_walk.py:525`, `pkg/18c-b-chrome:os/ci/control/release_checks.py:321`,
   `reviews/42-release-28/REVIEW-10.md:5`)
   - Service checks: `service_user`, `unit`, `claude_code_files`, `folders`, `state_folders`. Keep UID/GID 250 and the state ownership checks. Follow the login dependency graph. Allow a masked non-root
     unit as an ordering-only reference. Traverse it and refuse any masked requirement or dependency on Control. (`os/ci/release28_walk.py:558`, `os/ci/release28_walk.py:579`, `HANDOFF.md:100`)
   - Chrome checks are `chrome_links`, `chrome_bundle`, `chrome_other_ids`, `chrome_sites`, `gh` and `chrome_polkit`. C1 `CONTROL_CHROME_FILES_PASS` checks the placeholder's owner and mode. C6
     `CONTROL_CHROME_SITES_FIRST_USE_PASS` proves `tabs`, `read`, `open` and `take_tab` all return `chrome_settings_unavailable` and the page server gets no requests. A format-1 write opens the gate,
     and `CONTROL_CHROME_SITES_REBOOT_PASS` proves the list survives reboot unchanged. Keep the unit proofs in `control/chrome_tests/test_excluded_sites_placeholder.py` and `control/chrome_tests/test_exclusions.py`.
     Control runs `44912649303` and `44927047698` passed. (`b2a404cd:reviews/18c-b-chrome-image/PROGRESS.md:1547-1550`, `b2a404cd:reviews/18c-b-chrome-image/REPORT.md:72`)
   - On starting R28, stage `{"format":1,"hosts":["rehearsal.invalid"]}` at a separate path in the guest's `/var`. Run the five service checks and save an independent root-read SHA-256 before the update.
     Leave the live path absent so tmpfiles creates the placeholder on the first R29 boot. Check its bytes, owner and mode and run C6's refusal and zero-request checks. Then use root's `tee` to put the
     staged bytes into the live list. On both R29 boots require all eleven checks, the list's ownership and mode, and `CONTROL_CHROME_SITES_SHA256` equal to the pre-update hash. After `previous`, run the
     five service checks on R28 and independently hash the live list as root against that same hash. `/var` preserves the list and R28 needs only the root read. Reject a rewritten list, a placeholder
     after setup, a missing file and a missing check in tests.
     Keep the real list and its hash private. (`linux-tools`, 2026-11-21, `b2a404cd:os/ci/control/release_checks.py:283`, `b2a404cd:os/ci/control/release_checks.py:345`)

6. **Cut, review and publish.** The lead merges the named main cut into the release branch. Resolve from the pushed cut. Use `MOD_JAR_REPRODUCIBLE` from two clean hosted builds to renew only the AresOS
   jar's SHA-256 here. Renew missing RPM, Chrome, gh or Prism pins on main with reasons and checks, then recut. Stop for labwc/wlroots drift. Use the full stable Deskflow candidate lock in order if a lock
   refresh is needed on main. Save the resolve evidence. Compare the pinned gh release with the resolver's informational version line. Have the lead settle any renewal before the cut.
   (`pkg/18c-b-chrome:briefs/18c-b-chrome-image.md:425`) (`briefs/42-release-28.md:64`, `briefs/323-r29-image.md:23`, `os/ci/release_diff.py:671`, `os/ci/check-resolve.sh:253`,
   `reviews/42-release-28/REVIEW-2.md:27`)
   - B321 merges to main only after all four cut conditions pass. Get the final reviewed handoff with the OS lead's read-clean, a green Deskflow VM on B321's final head, a resolve of the reviewed NEVRA
     and SHA-256 from Fedora stable `updates`, and observed VM evidence of monitor unplug and replug or B321's separately owner-approved laptop proof. Test builds may use the pinned RPM from
     `updates-testing`. Package 331 builders stay off the laptop. Recheck all four conditions before uploading a cut with B321. (`linux-desktop`, 2026-11-21, `HANDOFF.md:97`,
     `ec386039:briefs/321-deskflow-image.md:43-48`, `ec386039:briefs/321-deskflow-image.md:54-55`)
   - If B321 is still off main and a condition is missing when the rest of R29 is ready, defer B321 to R30. The R29 fallback ships main as it stands, with 311's reviewed
     `labwc-0.9.6-1.fc44.aresos1.x86_64` pin. Confirm the pin at the cut. If B321 has already merged and a condition later fails, the lead decides whether to revert B321 and requalify a cut from main or wait.
     (`f91aad16:os/labwc/labwc.lock.json:161-163`, `f91aad16:os/Containerfile:34-41`)
   - Give `dry_run_29`, `release_29` and `release-29` distinct guarded modes on the exact branch ref. Extend the release job, `build_tools`, `registry_auth`, `publish.sh`, verification, owner runner
     allowlists and ledger with narrow entries and tests. The read-only dry run and the publish job use the same build, image checks, both guardian boot receipts, release isolation and diff on the final cut.
     Check selector collisions and reject tag refs. Use the on-job checks and resolve guards. Start `dispatch_caps.publish-29`, `publish_cap` and the qualifying rehearsal cap at zero. Count all dispatches,
     including early failures and cancellations. Test that closing both publish caps keeps the spent dispatch and upload in the ledger, permits checks and rehearsals, and refuses another release dispatch.
     (`.github/workflows/os-image.yml:202`, `.github/workflows/os-image.yml:521`, `.github/workflows/os-image.yml:632`, `os/ci/build_tools.py:87`, `os/ci/registry_auth.py:23`, `os/ci/publish.sh:5`,
     `os/ci/check-build.sh:63`, `os/ci/rehearsal_guard.py:402`)
   - Dry-run the release record checks. Before any upload, validate the source trees and extracted Control manifest, and test the prospective Chrome shipment on a temporary ledger copy. Require the row
     for that job's source SHA and checked build hash. Treat a refusal or a returned row for another commit as a failed gate. (`os/ci/publish.sh:45`, `b2a404cd:control/chrome/record_build.py:137`)
   - From R29 on, a candidate may be uploaded privately before rehearsal so the VM can install the signed image from the registry. Only the lead opens the publish caps for one private upload, after fresh review
     of passing baseline preflight, cut checks and dry run on the cut. The lead dispatches `release_29=true` once on the reviewed gate head. The job repeats the gates before pushing to private GHCR and
     signing with `os-image.yml@refs/heads/pkg/331-release-29`. Use the scoped job token, immutable tags and historical records. Rehearse the exact signed digest. (The owner, board T480, 2026-11-21)

7. **Record, rehearse, final review, pin, in that order after publishing.**
   - Write `os/manifest/releases/29.json` from the publish artifacts. Keep the digest, signature and issuer, run, base, image diff, source trees and `daily_wheel: true`. Bind R29's
     `control.source_revision` and `chrome_build` to the image's checked manifest. Record the actual shipment with `record_build.py add` in the job, bound to the published SHA and checked build hash.
     Carry that validated row in the pinning PR. Keep full source binding to the published commit. Allow the validated `control/chrome/builds.json` update for this shipment and hold every other Control
     path and mode to the published tree. Test both the record and rejection paths. (`reviews/42-release-28/payload.py:31`, `os/ci/verify_release.py:49`,
     `pkg/18c-b-chrome:briefs/18c-b-chrome-image.md:615`, `pkg/18c-b-chrome:control/chrome/build.py:8`, `pkg/18c-b-chrome:control/chrome/record_build.py:137`)
   - Prepare the exact candidate payload on the release branch for the rehearsal. Append history, use the next free tools version at generation and generate both manifest copies, `commands.json`, bundle sums and
     `OWNER-TOOLS.md` fingerprint lines. Make one generator serve the stand-in and the real candidate. If 43 lands, use its reviewed tools bytes as the agreed transition. Require a refresh to leave
     identical bytes. Stage bound guide changes before the qualifying run. Move every digest and fingerprint reference together, including the install and emergency routes. The default pin on main remains
     R28 at this point. Keep the draft PR unannounced. Record the v5 installer refusal with an older update already staged as a baseline limit. Test that refusal leaves deployment and tools state
     unchanged. (`reviews/42-release-28/PROGRESS.md:931`, `reviews/42-release-28/payload.py:11`, `reviews/42-release-28/payload.py:57`, `reviews/42-release-28/FIXES-4.md:9`, `HANDOFF.md:102`)
   - Guide acceptance requires the same save gate on every way out of R28, including first update, forward and failed-update recovery. Whenever the R28 world is open, focus Minecraft, press Alt+F4 or
     Alt+Fn+F4 and wait for “Minecraft was closed. Nothing is wrong.” If it is missing, go to Help before restarting. While the shipped tools require `foot`, the guide tells the owner to open the Terminal app
     before `at check` on starting R28, before the first confirmation on R29, and before the confirmations after `previous` and `forward`. Keep Terminal open through PASS. Keep the recovery terminal shortcut
     and show R28's Minecraft desktop on rollback. Preserve no-stick export, provisional title off the laptop, F12 and hands off GRUB, the failed-update card, install hold and exact route outputs.
     (`docs/INSTALL.md:230`, `docs/INSTALL.md:242`, `docs/INSTALL.md:406`, `docs/EMERGENCY.md:20`)
   - Carry pending hashes forward from main. Refresh affected rows with the lead's `rebind.py pending` notes. Keep package 42's recorded bindings and historical receipt. Generate the 331 host receipt and
     require the same head's hosted checks/full model and native preflight. Check exact private signatures and job-token reads for the qualified targets. Record the actual passing run's result, audits and
     `331-bound-sources` under package 331. Verify the qualified bytes, make 331 active and empty the pending list. Test that the binding package matches its directory. Bind safe evidence only.
     (`os/manifest/ci/16/pending-rebind.json:4`, `os/manifest/ci/42/source-bindings.json:124`, `os/ci/owner_vm.py:2309`, `os/ci/checkout_sources.py:106`, `reviews/27-first-update-release/rebind.py:85`,
     `reviews/42-release-28/PROGRESS.md:1455`, `reviews/42-release-28/PROGRESS.md:1913`)
   - Update INSTALL-STATUS's summary and signed-update row together. Name the passing run and tools fingerprint, and say the laptop still runs R28. Compare the route and card outputs with the released CLI
     in `test_owner_guide_output`, `test_owner_path` and `test_owner_equality`. After rehearsal and final review, the lead checks the prospective merge's release, tools, guides and bound files against
     the qualified head before merging the live pin. Recheck any later status or gate edit and requalify changes to rehearsed bytes. After merge, compare the announcement to main and send the owner the
     short summary, exact digest, announced commit and fingerprint. The owner runs `at update`. (`docs/REVIEW.md:7`, `HANDOFF.md:100`, `docs/INSTALL-STATUS.md:10`, `docs/INSTALL-STATUS.md:29`)

## Not in this package

- A new base, fresh install, reinstall, unmasking the finalize units, or any work on the real laptop. Live Prism login, Chrome profile use and Deskflow with the Mac stay with their own trials.
  (`briefs/42-release-28.md:51`, `docs/INSTALL-STATUS.md:29`)
- 23c's supervisor wiring, live monitor placement and Super search launch, Konsole, or building the package 43 dispatcher here. If 43 qualifies and lands before the cut, take its handoff and existing
  dispatcher rehearsal requirements. Otherwise keep the console update route. (`STATE.md:202`, `HANDOFF.md:14`, `pkg/43-aresos-command:reviews/43-aresos-command/PROGRESS.md:595`)

## Steps

Plan the slices below before launching builders. Each slice ends with focused checks and commits, including an update to `reviews/331-release-29/PROGRESS.md` with done, left in order, limits, source
and run SHAs and ledger. Builders push to `pkg/331-release-29` with both publish caps at zero, then stop. Builders may prepare candidate files on that branch. Only the lead opens a cap after review of its
cut evidence. The lead owns dispatches, hosted waits and retries, the live pin, merge and announcement, and closes the publish caps before handing the branch back. Open a draft build PR in turn 1 after brief approval.
“Sol” is `gpt-6.2-sol`, “Astra” is `gpt-6.2-astra`. Builders use xhigh and reviewers high. Use a fresh turn for any slice left at the call limit. Steps 1–5 can start now.

Run `sudo`, `rpm-ostree`, `bootc` and real owner-tool entry points only on disposable hosted runners or inside their guests. This includes item 5's root `tee` in the guest. `test_owner_update`
is hosted-only. Local checks use fixtures and one affected safe test module at a time. (`AGENTS.md:26`, `os/ci/rehearsal_guard.py:530`)

1. **Diff for current main** (Sol / Sol, file rules against a fixed baseline). Build item 3's profile and tests, including the main source stop. Leave the labwc payload comparison for step 2. The lead
   reviews the classifier.
2. **Labwc evidence** (Sol / Astra, executable bytes and RPM provenance). Add 311's exact comparison, source bindings and near misses. The lead checks the limits of the RPM exception.
3. **Walk** (Sol / Astra, deployment shape and rollback). First build the historical VM baseline leg through confirmed R28/v5 and check its fixtures. In a fresh slice build candidate equality and the
   new local R29 update, recovery and boot walk. Check shape, route ordering and failures on the model.
4. **Guest probes and Control** (Sol / Sol, precise probe contracts). Add the home, Terminal, game and eleven Control checks, with the Chrome first-use and rollback checks from item 5. Test the submitted
   scripts and retain diagnostics. Produce the local host receipt.
5. **Hosted wiring** (Sol / Astra, permissions and dispatch scope). First wire and test selectors, permissions and closed caps. In a fresh slice wire and test registry targets, runner allowlists, receipts
   and budgets. The lead runs `checks_only=true` and the read-only historical baseline preflight. The lead uses `check_build=build` and separate Control and Deskflow modes as applicable on incoming branches.
6. **Cut and late rules** (Sol / Astra, exact source and package deltas). The lead settles Deskflow under item 6, names the cut and merges main into the release branch. Give each late package its own
   slice for reasons, probes and regressions, with focused checks on the combined rules. The lead dispatches `check_build=resolve` on the final cut head.
7. **Resolve evidence and dry run** (Sol / Sol, lock and jar pin). Verify and apply item 6's allowed pin. Run the targeted checks and refresh the receipt. The lead runs hosted checks and
   `dry_run_29=true`. Any unresolved diff stops the release. Each fix gets a fresh turn, review and new dry run. Save a spare dry-run allowance. A failed publish dispatch also counts. Verify whether
   the upload was attempted before considering any retry. (`reviews/42-release-28/REVIEW-2.md:89`, `reviews/42-release-28/REVIEW-12.md:13`)
8. **Publish gate** (lead / Astra, final look before signing). Builders hand over green cut evidence with both publish caps at zero. The lead opens both caps after review of that evidence and dispatches
   `release_29=true` once on the reviewed gate head. The upload is private under T480. The VM installs this signed candidate for rehearsal.
9. **Published release record** (Sol / Sol, artifact and source identity). Record the signed digest and reconcile the Chrome ledger with the artifact and published commit. Leave the active pin for the
   candidate step.
10. **Candidate tools and guides** (Sol / Astra, exact tools and owner route). First generate and check the branch-only payload. In a fresh slice bind the guide edits and final host receipt and check
    equality. The lead opens the reviewed rehearsal allowance, runs `checks_only=true`, checks the full model on that head and dispatches `rehearsal=release-29`. Fix failures in fresh turns with
    same-head checks before each rerun.
11. **Record the passing walk** (Sol / Astra, final laptop-facing review). Verify the exact passing head, digest, receipts and audit proofs. Record the bindings and fill in the status evidence. Astra
    gives the final look across the whole candidate, checks and guides. The lead asks for targeted fixes and rechecks as needed.
12. **Pin** (Sol / Sol, approved bytes and release pointers). Prepare the pinning PR and `reviews/331-release-29/REPORT.md`, including Known limits, run links, summary and budget used. After the passing rehearsal,
    final review and pre-merge equality check, the lead merges the live pin, verifies the announcement against main and sends the summary. The owner installs the update.

Use hosted runners for the full suite, privileged tests, builds and VM. Use discovery for local modules. Keep temporary umask changes inside their test. Use reachable Git
inputs or explicitly fetch the recorded source, including old squash-merged refs. Check bound-source and guide equality tests before dispatch. Use `gh run watch <id> --exit-status --interval 60`, one
dispatch per branch at a time. Account for checks job time, the model gate and rehearsal setup, VM and upload bounds. The lead reviews any cap increase before a retry. Use free standard runners. Record
exact commands and results. Leave laptop-only checks open. (`AGENTS.md:22`, `HANDOFF.md:100`, `HANDOFF.md:102`, `reviews/42-release-28/PROGRESS.md:1317`, `reviews/42-release-28/PROGRESS.md:1430`)

## Decided

- **43 and tools.** R29 proceeds on its own schedule. Package 43 rides only if reviewed and merged before the cut. Coordinate with its lead and take the next free version when generating R29's candidate.
  Rehearse from installed v5 either way. If 43 ships after R29, it renumbers and refreshes its proofs. (`HANDOFF.md:99`, `f86fdd2b:docs/OWNER-TOOLS.md:1`)
- **ISO and budget.** Start with two dry runs, one publish and up to three qualifying rehearsals, with separately reviewed allowance for the baseline preflight, same-head checks and retries. Keep
  345 minutes as the initial job ceiling and measure the longer route before fixing the VM-step limit. Verify the pinned ISO and installer assets in the baseline preflight. R28's first three stops were
  the rotated ISO, missing real candidate bytes and changed embedded stock. Two were ISO-related. R28 used seven dry runs and eight rehearsal dispatches. Durable hosting is a separate decision. (`HANDOFF.md:101`,
  `reviews/42-release-28/PROGRESS.md:1317`, `os/ci/rehearsal-packages.json:177`)

AGENTS.md applies. In anything committed, write “the owner”, never a name.
