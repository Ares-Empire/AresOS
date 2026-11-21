# 331: Release 29 (the indicator, Chrome Control, Deskflow and the signed update)

Board brief 331. Lead `linux-aresos`. Branch `pkg/331-release-29`. Start the diff and walk on main now. The lead takes the cut after 18c-b, B330 and B321 land and Deskflow resolves from Fedora stable.
B329 rides if merged by the cut. The baseline below is fetched main `a9863055`. (`HANDOFF.md:13`, `HANDOFF.md:97`)

**Builder and reviews.** One fresh Codex builder per step, about 80 tool calls each. Model and reviewer choices are in Steps. One fresh Codex `gpt-6.2-sol` high brief review while Claude's allowance is
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
     and changes the tools. Steps 6 and 7 are still due in its handoff. Do not promise its route until that handoff is complete. (`os/manifest/releases/28.json:799`, `os/ci/release_diff.py:1693`,
     `control/packaging/aresos:3`, `HANDOFF.md:83`, `HANDOFF.md:99`, `pkg/43-aresos-command:reviews/43-aresos-command/PROGRESS.md:96`, `pkg/43-aresos-command:reviews/43-aresos-command/PROGRESS.md:460`)

2. **What the late packages hand over.** Each lead gives the merged SHA, green check and review, exact expected image additions, changes and removals with reasons, and one line for the owner's summary.
   Use the final merged code and the build evidence. The following lists are the starting points.
   - **18c-b (PR76, `linux-tools`).** The fetched branch has the 11-check checker. Get the exact Control install-map and vendor delta, per-build Chrome bundle, managed policy and native-host links,
     action, tmpfiles rule and updated manifest. Get the `gh` binary, licence and installed lock with their pins. `gh` is extracted from a signature-checked RPM. It is outside the installed RPM set.
     Summary draft, “Claude's tools can work in Chrome once the browser setup is ready.” Confirm the profile and approval gate below. (`HANDOFF.md:98`, `pkg/18c-b-chrome:briefs/18c-b-chrome-image.md:615`,
     `pkg/18c-b-chrome:os/build.sh:429`, `pkg/18c-b-chrome:os/build.sh:500`)
   - **B330 (`linux-aresos`).** At `5e0c8829` the diff list names the hidden Prism desktop entry and the MIME default, with no cache rebuild. Take those two paths with the reasons and hosted proof at
     merge. Summary draft, “Microsoft browser sign-in can now return to Prism Launcher.” (`HANDOFF.md:13`, `pkg/330-prism-handler:os/config/usr/share/applications/aresos-prismlauncher.desktop:4`,
     `pkg/330-prism-handler:os/config/usr/share/applications/aresos-mimeapps.list:9`, `pkg/330-prism-handler:reviews/330-prism-handler/PROGRESS.md:22`)
   - **B329 (`linux-desktop`, only if merged at the cut).** Take its theme folder (37 files), 36 frame sprites, `look.json` and `rc.xml` rows for theme, switcher, Shift+Alt+Tab and mouse. Keep the Crown
     file pin. Expect the guest to use `AresOS` when B329 rides. Take the brief's summary line about the pixel frame, backward Alt+Tab and disabled title-bar scrolling. (`HANDOFF.md:15`,
     `briefs/329-window-frame:briefs/329-window-frame.md:74`)
   - **B321 (`linux-desktop`, cut gate).** Get the Deskflow 1.27.0 RPM and dependency reasons, the second labwc patch and rebuilt RPM evidence, plus the backend, portal routing and allow-list, sharing
     switch, polkit, launch and recovery binding changes. The fetched branch has step 1c and the `aresos2` result lock. The rest of the installed list comes from the final package. Take its owner-summary
     line, covering sharing off at first, password to turn it on and Super+Shift+Esc to get the mouse back. Require its own Deskflow VM and lead's read-clean. Testing may use the pinned RPM from
     `updates-testing`. The release resolves the reviewed NEVRA and SHA-256 from stable `updates`. Around 28 November is an estimate. (`HANDOFF.md:97`, `briefs/321-deskflow-image.md:21`,
     `briefs/321-deskflow-image.md:50`, `briefs/321-deskflow-image.md:77`, `pkg/321-deskflow-image:os/labwc/labwc.lock.json:163`)
   - Add late packages in their own profile commits after the main merge. Tie each reason to the cut's source or lock. Add exact metadata and content checks for built files, update the expected `rc.xml`
     rows and guest probes, and add near-miss tests. Re-read the combined `rc.xml` if B329 and B321 both ride. A package landing after the cut waits for another release or a new cut with its own resolve
     and dry run. (`os/ci/release_diff.py:1230`, `os/ci/release_diff.py:1269`, `briefs/329-window-frame:briefs/329-window-frame.md:76`)

3. **The R29 diff (start on main).** Add `RELEASES['29']`, `PACKAGE_REASONS_29` and `Classifier29`. Compare the complete image inventories, RPMs and units against R28. Keep R27/R28 results and source
   lists fixed. Read old locks and historical test inputs from the recorded release via `released()` or its verified source. Use `CHMOD_0755_28` and `GENERATED_28` as references for R29's own rules. The
   new scripts in item 1 already have executable Git modes. Use the configure step for any forced mode. Hold both sides of each exception to the file type, ownership, mode and xattrs that the change
   warrants. (`os/ci/release_diff.py:381`, `os/ci/release_diff.py:429`, `os/ci/release_diff.py:1693`, `os/build.sh:501`, `os/tests/test_release27.py:33`, `os/tests/test_release28.py:124`, `HANDOFF.md:28`)
   - Verify the non-ghost inventory of every added or replacement RPM, including files absent from both images. Require clean `rpm -V`. For 311 use the exact replacement NEVRA, Fedora's 64-path list, the
     two build-ID links to the binaries and byte equality elsewhere. Accept measured build-ID differences only in the reviewed binary sections and matching link names. Run the existing normalized and
     loaded-image hash checks for labwc and labnag against the four lock pins. Carry the same proof to B321's reviewed second patch. Verify the old and new inventories independently. Add only the exact
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

4. **The R29 walk (start with local fixtures).** Add `release29_walk.py` and a `rehearsal=release-29` route from R28. Reuse the R28 and tools-local legs to create the historical baseline on disposable
   disks. Assert R28 runs with v5, only R27 and pinned stock behind it, R13 gone and no transaction. Read and verify R27/R28's immutable records and v5 bytes at their recorded source. Pin each historical
   leg to its own target and tools before moving the active pointer. (`os/ci/release28_walk.py:698`, `os/ci/release28_walk.py:708`, `os/ci/owner_vm.py:1533`, `os/ci/verify_release.py:83`,
   `reviews/42-release-28/PROGRESS.md:1441`)
   - From R28, follow the folder and routine route with the new bundle in the stand-in origin. Compare the fingerprint in the window and guide, and require install, check and title PASS with no cached
     sudo ticket. Keep the identical-bundle no-op, equal-version mismatch and downgrade cases. Only an unchanged v5 baseline may defer real-commit comparison in a local prep fixture. Qualification
     requires equality of the real candidate trees, bundle and guide before the walk. Bind the checker and settings in the host receipt. Execute the actual submitted probe scripts in local tests with
     injected failures. (`os/ci/release28_walk.py:241`, `os/ci/release28_walk.py:755`, `reviews/42-release-28/FIXES-4.md:9`, `reviews/42-release-28/FIXES-4.md:57`)
   - Follow the console `at update`, `at title`, export, `at reboot`, F12 → Bazzite, `at check` route. In the VM prove the export result for the no-stick route. Require exact staged and confirmed digests.
     Check the shape at staging and after every boot. R27 is the one release the R29 update retires. `at previous` returns to R28 and `at forward` returns to R29. Require their own confirmations and fresh
     titles. Preserve the stock pin, protected Windows disk and boot entry, Windows firmware default and all R28 audits, including on failure. (`docs/INSTALL.md:345`, `docs/INSTALL.md:375`,
     `docs/INSTALL.md:417`, `os/ci/release28_walk.py:784`, `os/ci/release28_walk.py:839`, `os/ci/owner_vm.py:1038`)
   - On the first R28 boot plant the schema-4 apps fixture and synthetic `level.dat` and region data. Use the real provisioner's instance links (`patches`, `libraries`, `minecraft/mods`,
     `minecraft/saves`). Compare content, owner, mode, type, link text and access by the daily user across update, previous and forward. Keep the narrow Prism mutable-file allowance. Require both
     releases' own image targets on their boots. Both ship the desktop payload. Save the game-scope/JVM probe for the end. It proves placement and `memory.high=2684354560`. Record actual play and
     live-save checks as manual. (`os/ci/release28_walk.py:85`, `os/ci/release28_walk.py:635`, `os/ci/release28_walk.py:689`, `reviews/42-release-28/FIXES-6.md:10`, `reviews/42-release-28/FIXES-4.md:142`)
   - Check the booted theme, fontconfig and runtime privilege, polkit and terminal PATH. Keep the no-foot STOP check where the installed tools require foot. Reopen the exact Terminal app command from the
     one supervisor's Wayland environment and the daily user's home, after tty1 is active. Check the same PID survives and retain its log. Retry only the missing-monitor case, up to the existing five
     attempts. Include negative cases for display, cwd and VT in the fake. (`os/ci/release28_walk.py:625`, `os/ci/release28_walk.py:666`, `os/ci/release28_walk.py:811`,
     `reviews/42-release-28/FIXES-4.md:37`, `reviews/42-release-28/PROGRESS.md:1867`)
   - Use the stock rewind with exact ISO and Web UI checks, runner space check, offline first boot and pinned stock identity. Keep the verified 9p copy, loop-backed store, scratch cleanup and both disk
     audits. A changed ISO requires requalification. Save `finish_shutdown` output on failure. If the live console stalls again before login, bring its transcript to the lead for a bounded fix.
     (`reviews/42-release-28/PROGRESS.md:996`, `reviews/42-release-28/PROGRESS.md:1239`, `reviews/42-release-28/PROGRESS.md:1859`, `os/ci/owner_vm.py:255`)

5. **The R29 Control list (start now with PR76's contract).** Pass these names explicitly to the bound stdin checker. Assert each check's result and the whole key set on the first and final R29 boots.
   Preserve output before the login-graph probe. Keep R28's own five-check behavior. (`HANDOFF.md:98`, `os/ci/release28_walk.py:525`, `pkg/18c-b-chrome:os/ci/control/release_checks.py:321`,
   `reviews/42-release-28/REVIEW-10.md:5`)
   - Service checks: `service_user`, `unit`, `claude_code_files`, `folders`, `state_folders`. Keep UID/GID 250 and the state ownership checks. Follow the login dependency graph. Allow a masked non-root
     unit as an ordering-only reference. Traverse it and refuse any masked requirement or dependency on Control. (`os/ci/release28_walk.py:558`, `os/ci/release28_walk.py:579`, `HANDOFF.md:100`)
   - Chrome checks: `chrome_links`, `chrome_bundle`, `chrome_other_ids`, `chrome_sites`, `gh`, `chrome_polkit`. On starting R28 use root's `tee` to write `{"format":1,"hosts":["rehearsal.invalid"]}` to
     `/var/lib/aresos-control/chrome-excluded-sites.json` and save the hash. Require the same bytes and expected metadata on R29. On rollback to R28 prove the hash independently and run the five service
     checks. R28 cannot supply R29's browser records. Require the checker hash line on R29, where the checker also verifies list ownership and mode. Check again on forward. Reject a rewritten list,
     placeholder, missing file and missing check in tests. Keep the real list and its hash private. (`os/manifest/releases/28.json:799`, `os/ci/release28_walk.py:612`,
     `pkg/18c-b-chrome:os/ci/control/release_checks.py:283`, `pkg/18c-b-chrome:os/ci/control/release_checks.py:337`, `pkg/18c-b-chrome:reviews/18c-b-chrome-image/PROGRESS.md:1046`)

6. **Cut, review and publish.** The lead merges the named main cut into the release branch. Resolve from the pushed cut. Use `MOD_JAR_REPRODUCIBLE` from two clean hosted builds to renew only the AresOS
   jar's SHA-256 here. Renew missing RPM, Chrome, gh or Prism pins on main with reasons and checks, then recut. Stop for labwc/wlroots drift. Use the full stable Deskflow candidate lock in order if a lock
   refresh is needed on main. Save the resolve evidence. Compare the pinned gh release with the resolver's informational version line. Have the lead settle any renewal before the cut.
   (`pkg/18c-b-chrome:briefs/18c-b-chrome-image.md:425`) (`briefs/42-release-28.md:64`, `briefs/323-r29-image.md:23`, `os/ci/release_diff.py:671`, `os/ci/check-resolve.sh:253`,
   `reviews/42-release-28/REVIEW-2.md:27`)
   - Give `dry_run_29`, `release_29` and `release-29` distinct guarded modes on the exact branch ref. Extend the release job, `build_tools`, `registry_auth`, `publish.sh`, verification, owner runner
     allowlists and ledger with narrow entries and tests. The dry run has read permissions only and the same build, image checks, first VM pass, release isolation and diff as publish. Check selector
     collisions and reject tag refs. Start both publish caps and the rehearsal cap at zero. Count all dispatches, including early failures and cancelled runs. Use the on-job checks and resolve guards.
     (`.github/workflows/os-image.yml:202`, `.github/workflows/os-image.yml:521`, `.github/workflows/os-image.yml:632`, `os/ci/build_tools.py:87`, `os/ci/registry_auth.py:23`, `os/ci/publish.sh:5`,
     `reviews/42-release-28/REVIEW-2.md:29`, `reviews/42-release-28/REVIEW-2.md:56`)
   - Once the cut's checks, dry-run evidence and fresh review pass, open both publish caps for one publish under #388. The lead dispatches `release_29=true` once on the reviewed head. The job repeats
     every gate before pushing to private GHCR and signing with `os-image.yml@refs/heads/pkg/331-release-29`. Use the scoped job token and keep immutable tags and historical records. The standing rule
     covers private publication and pins. The signed image must exist for the update rehearsal. Leave the owner-facing pin until the rehearsal and final review pass. (`STATE.md:160`, `HANDOFF.md:102`,
     `os/ci/publish.sh:18`, `reviews/42-release-28/REVIEW-12.md:13`, `briefs/27-first-update-release.md:20`)

7. **Record, rehearse, final review, pin, in that order after publishing.**
   - Write `os/manifest/releases/29.json` from the publish artifacts. Keep the digest, signature and issuer, run, base, image diff, source trees and `daily_wheel: true`. Bind R29's
     `control.source_revision` and `chrome_build` to the image's checked manifest. Run `record_build.py add` in the job with the published commit and expected build hash. Carry its validated ledger update
     in the pinning PR. Keep full source binding to the published commit. If the ledger moves in the candidate checkout, allow only the validated `control/chrome/builds.json` update for this shipment
     while holding every other Control path and mode to the published tree. Test both the record and rejection paths. (`reviews/42-release-28/payload.py:31`, `os/ci/verify_release.py:49`,
     `pkg/18c-b-chrome:briefs/18c-b-chrome-image.md:615`, `pkg/18c-b-chrome:control/chrome/build.py:8`, `pkg/18c-b-chrome:control/chrome/record_build.py:137`)
   - Prepare the exact candidate payload on the release branch for the rehearsal. Append history, bump to the agreed fresh tools version and generate both manifest copies, `commands.json`, bundle sums and
     `OWNER-TOOLS.md` fingerprint lines. Make one generator serve the stand-in and the real candidate. If 43 lands, use its reviewed tools bytes as the agreed transition. Require a refresh to leave
     identical bytes. Stage bound guide changes before the qualifying run. Move every digest and fingerprint reference together, including the install and emergency routes. The default pin on main remains
     R28 at this point. Keep the draft PR unannounced. Record the v5 installer refusal with an older update already staged as a baseline limit. Test that refusal leaves deployment and tools state
     unchanged. (`reviews/42-release-28/PROGRESS.md:931`, `reviews/42-release-28/payload.py:11`, `reviews/42-release-28/payload.py:57`, `reviews/42-release-28/FIXES-4.md:9`, `HANDOFF.md:102`)
   - Keep the R28 save-and-close step first for this update (T462). Focus Minecraft, press Alt+F4 or Alt+Fn+F4 and wait for “Minecraft was closed. Nothing is wrong.” The reboot into R29 runs under R28's
     supervisor. Package 25 lets the next update from R29 drop the manual step. Keep the Terminal and recovery key guidance the tools still need, and show R28's Minecraft desktop on rollback. Preserve the
     no-stick export lines, provisional title off the laptop, F12 and hands off GRUB, failed-update card, install hold and exact route outputs. (`HANDOFF.md:35`, `docs/INSTALL.md:230`, `docs/INSTALL.md:375`,
     `reviews/42-release-28/PROGRESS.md:1406`, `reviews/42-release-28/PROGRESS.md:1632`)
   - Carry pending hashes forward from main. Refresh affected rows with the lead's `rebind.py pending` notes. Keep package 42's recorded bindings and historical receipt. Generate the 331 host receipt and
     require the same head's hosted checks/full model and native preflight. Check exact private signatures and job-token reads for the qualified targets. Record the actual passing run's result, audits and
     `331-bound-sources` under package 331. Verify the qualified bytes, make 331 active and empty the pending list. Test that the binding package matches its directory. Bind safe evidence only.
     (`os/manifest/ci/16/pending-rebind.json:4`, `os/manifest/ci/42/source-bindings.json:124`, `os/ci/owner_vm.py:2309`, `os/ci/checkout_sources.py:106`, `reviews/27-first-update-release/rebind.py:85`,
     `reviews/42-release-28/PROGRESS.md:1455`, `reviews/42-release-28/PROGRESS.md:1913`)
   - After the final review, make the checked branch payload the pin. Update INSTALL-STATUS's summary and signed-update row together. Name the actual passing run and tools fingerprint, and say the laptop
     still runs R28. Require the release, tools and guides to equal the qualified bytes. Any change to rehearsed owner-facing bytes goes back through qualification. Compare the route and card outputs with
     the released CLI in `test_owner_guide_output`, `test_owner_path` and `test_owner_equality`. Give the owner the short summary, exact digest, announced commit and fingerprint after the pin lands.
     The owner runs `at update`. (`HANDOFF.md:100`, `docs/INSTALL-STATUS.md:10`,
     `docs/INSTALL-STATUS.md:29`, `os/tests/test_checkout_sources.py:108`, `reviews/42-release-28/PROGRESS.md:1645`)

## Not in this package

- A new base, fresh install, reinstall, unmasking the finalize units, or any work on the real laptop. Live Prism login, Chrome profile use and Deskflow with the Mac stay with their own trials.
  (`briefs/42-release-28.md:51`, `docs/INSTALL-STATUS.md:29`)
- 23c's supervisor wiring, live monitor placement and Super search launch, Konsole, or building the package 43 dispatcher here. If 43 qualifies and lands before the cut, take its handoff and existing
  dispatcher rehearsal requirements. Otherwise keep the console update route. (`STATE.md:202`, `HANDOFF.md:14`, `pkg/43-aresos-command:reviews/43-aresos-command/PROGRESS.md:595`)

## Steps

All builder steps end with commits, a push to `pkg/331-release-29` and a stop. Keep `reviews/331-release-29/PROGRESS.md` current with done, left in order, what the code doesn't show, source and run SHAs
and the ledger. Open a draft build PR in turn 1 after brief approval. The lead dispatches between turns and reads each review. “Sol” is `gpt-6.2-sol`, “Astra” is `gpt-6.2-astra`. Builders use xhigh.
Reviewers use high. Use a fresh turn for any remaining slice at the call limit. Steps 1–5 can start now. Steps 6–12 wait for the cut.

1. **Diff for current main** (Sol / Sol, file rules against a fixed baseline). Build item 3's profile and tests, including the main source stop. Leave the labwc payload comparison for step 2. The lead
   reviews the classifier.
2. **Labwc evidence** (Sol / Astra, executable bytes and RPM provenance). Add 311's exact comparison, source bindings and near misses. The lead checks the limits of the RPM exception.
3. **Local walk baseline and update** (Sol / Astra, deployment shape and rollback). Build the R28/v5 starting leg, candidate equality and R29 console and boot route. Prove the shape and failure paths on
   the model.
4. **Guest probes and Control** (Sol / Sol, precise probe contracts). Add the home, Terminal, game and eleven Control checks. Test the submitted scripts and retain diagnostics. Produce the local host
   receipt.
5. **Hosted wiring** (Sol / Astra, permissions and dispatch scope). Wire the rehearsal and release selectors, auth, receipts, budgets, tests and closed gates. The lead runs `checks_only=true` and reviews.
   The lead uses `check_build=build` for incoming packages on their branches and their separate `control` and Deskflow qualification modes as applicable.
6. **Cut and late rules** (Sol / Astra, exact source and package deltas). Wait for the handoffs and stable Deskflow. The lead names the cut and merges main into the release branch. Add the late reasons,
   probes and regressions. If needed, give 18c-b its own fresh turn before B321's. The lead dispatches `check_build=resolve` on the final cut head.
7. **Resolve evidence and dry run** (Sol / Sol, lock and jar pin). Verify and apply item 6's allowed pin. Run the targeted checks and refresh the receipt. The lead runs hosted checks and
   `dry_run_29=true`. Any unresolved diff stops the release. Each fix gets a fresh turn, review and new dry run. Save a spare dry-run allowance. A failed publish dispatch also counts. Verify whether
   the upload was attempted before considering any retry. (`reviews/42-release-28/REVIEW-2.md:89`, `reviews/42-release-28/REVIEW-12.md:13`)
8. **Publish gate** (Sol / Astra, final look before signing). Collect the green evidence and open the one-publish gate. After the gate review, the lead dispatches `release_29=true` on that reviewed head.
9. **Published release record** (Sol / Sol, artifact and source identity). Record the signed digest and reconcile the Chrome ledger with the artifact and published commit. Leave the active pin for the
   candidate step.
10. **Candidate tools and guides** (Sol / Astra, exact tools and owner route). Prepare the branch-only payload, bound guide edits and final host receipt. Open the reviewed rehearsal allowance. The lead
    runs `checks_only=true`, checks the full model on that head and dispatches `rehearsal=release-29`. Fix failures in fresh turns with same-head checks before each rerun.
11. **Record the passing walk** (Sol / Astra, final laptop-facing review). Verify the exact passing head, digest, receipts and audit proofs. Record the bindings and fill in the status evidence. Astra
    gives the final look across the whole candidate, checks and guides. The lead asks for targeted fixes and rechecks as needed.
12. **Pin** (Sol / Sol, approved bytes and release pointers). Finalize the pinning PR and `reviews/331-release-29/REPORT.md`, including Known limits, run links, summary and budget used. The lead reads the
    final diff and checks, merges, verifies the announcement against main and sends the summary.

Use hosted runners for the full suite, privileged tests, builds and VM. Locally use one affected safe module at a time and discovery. Keep temporary umask changes inside their test. Use reachable Git
inputs or explicitly fetch the recorded source, including old squash-merged refs. Check bound-source and guide equality tests before dispatch. Use `gh run watch <id> --exit-status --interval 60`, one
dispatch per branch at a time. Account for checks job time, the model gate and rehearsal setup, VM and upload bounds. The lead reviews any cap increase before a retry. Use free standard runners. Record
exact commands and results. Leave laptop-only checks open. (`AGENTS.md:22`, `HANDOFF.md:100`, `HANDOFF.md:102`, `reviews/42-release-28/PROGRESS.md:1317`, `reviews/42-release-28/PROGRESS.md:1430`)

## Open questions for the lead

- **Deskflow timing.** B321's brief and STATE still place (c) after R29. This draft follows the newer handoff and makes it a cut gate. Confirm that with `linux-desktop`. Recommend waiting for the stable
  resolve and full B321 image/VM handoff. (`briefs/321-deskflow-image.md:3`, `STATE.md:224`, `HANDOFF.md:97`)
- **Chrome activation.** The 18c-b release handoff asks for all new checks after `previous` and also gates use on 28b's combined proof and a live C8 check at the owner's actual terminal size. Recommend
  five service checks and an independent hash on R28, all eleven on both R29 boots, and holding owner use until the combined and live gates pass. Confirm whether those gates also hold the cut or publish.
  (`pkg/18c-b-chrome:reviews/18c-b-chrome-image/PROGRESS.md:1046`, `os/manifest/releases/28.json:799`)
- **43 and the next tools version.** The old R29 note includes the dispatcher. Its branch still calls for the R28 bridge and handoff. Recommend treating 43 as separate unless it is reviewed and merged by
  the cut, and reserving the next free version with its lead before generating any candidate. v5 is the rehearsal baseline. If 43 lands first, settle its dispatcher stages and bundle/version order before
  dispatch. (`HANDOFF.md:99`, `pkg/43-aresos-command:reviews/43-aresos-command/PROGRESS.md:96`, `pkg/43-aresos-command:reviews/43-aresos-command/PROGRESS.md:1103`)
- **ISO and budget.** R28's live ISO rotated and cost three early stops. Recommend checking the pinned ISO and installer assets before spending a rehearsal and arranging durable hosting in its own
  decision. Start with R28's 345-minute ceiling for a VM job, two dry runs plus reviewed retries, one publish and up to three rehearsal attempts. Confirm the branch and shared minute allowances against
  the longer R29 route. (`HANDOFF.md:102`, `reviews/42-release-28/PROGRESS.md:1317`, `os/ci/rehearsal-packages.json:177`)
- **Publication interpretation.** #388 records reviews, checks and rehearsal as conditions. R28 used a reviewed private upload to make the signed candidate available to the rehearsal. Recommend repeating
  that ordering, with the owner-facing pin and summary gated on the passing walk and final review. Confirm the gate note before opening the caps. (`STATE.md:160`, `HANDOFF.md:102`,
  `os/ci/owner_vm.py:2411`)

AGENTS.md applies. In anything committed, write “the owner”, never a name.
