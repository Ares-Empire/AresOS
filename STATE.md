# AresOS: state

Updated 2026-11-13. The live truth is `git log`, `gh pr list` and `git worktree list`. Update this file when a PR merges or a decision lands.

## Done (on main)

- **Minecraft starts in AresOS: Prism, Java 25, the desktop supervisor** (PR #36, brief 23 to 23-review-fixes-5, empire brief 264, merged 2026-11-13 as `3bff81b6`):
  - Prism and Java 25 in the image, the managed `AresDesktop` instance, and a supervisor that boots into the hub. On the first start the owner creates the hub himself with the mod's AresOS button (board #168); his other answers are board #169 and #170.
  - The supervisor decides from Java's exit status alone: a SIGKILL by anyone latches recovery, exit 0 is his quit, no facts latch, any other status is one counted crash and a restart (the three-crash latch stays). The widened JUDGMENT-CALL 10 (a Java the wrapper had to SIGKILL latches instead of restarting) is covered by board #170. Twelve known limits are in the report.
  - Every image build builds the mod jar from the build commit. Its pinned hash binds release builds only: a throwaway check build with another jar goes on with one loud line and records its jar in `/usr/share/aresos/manifest/aresos-mod.json`. The pin is stale (`8b04c511…`); the next release sets it from the "Mod" workflow's hash for its commit (the jar builds reproducibly since PR #51, `linux-hub`).
  - Built by Claude agents (Opus; fix round 5 on Fable 5.2). Reviews 1 to 5 CHANGES-NEEDED; reviews 6 and 7 (gpt-6-astra high) SAFE. On the merged head: hosted checks 43490423057 (1095 tests) and the check build with VM 43490417132 (40 image checks; in the VM the JVM in its 5 GiB scope, a whole-scope kill latching recovery, memory pressure hitting only the hog).
  - Not proven: a real Prism and Minecraft start with his account, a systemd-oomd kill, and the focus hand-back with a real game. They wait for the laptop trial. It reaches the laptop with the next release.
  - Left for the next release: pins expire on their own (Fedora replaced the Java builds within three days, Prism's Minecraft metadata changes about weekly; `check_build=resolve` now renews a vanished Fedora pin by name, and a session whose check build stops on a pin reports it to the OS lead); the release diff does not know this package's build-time files yet; a regression test for known limit 11; one uncaptured local failure in `test_aresos_desktop` on a busy laptop (possibly timing).

- **Release 27, the first update release** (PR #35, brief 27 to 27-review-fixes-3 and 27-rehearsal-fixes-1, empire brief 266, merged 2026-11-13 as `41b06513`):
  - Image `ghcr.io/ares-empire/aresos@sha256:5fad242fceac7244563913eed96cd72dfcd300fec5e458cdb2ba81bce00d944c` (packages 21, 22 and 24; private, keyless-signed, run 42842793096). Tools fingerprint `851eb742…`.
  - Update rehearsal run 14 (43302603386) passed the owner's whole route in the VM: tools v1 to v2, `at update`, `at title`, `at reboot` into R27 with R13 as rollback and stock pinned, `sudo passwd ares`, package 21's rules, `at previous` back to R13 (forward refused), every protected-disk audit unchanged.
  - Built by a Claude agent (Opus). Reviews 1–3 CHANGES-NEEDED (the update stop routine); reviews 4 (owner tools), 5 and 6 (harness) SAFE. Runs, reviews and known limits: `reviews/27-first-update-release/REPORT.md`.
  - Owner answers: board #175 (JUDGMENT-CALL 11, unmasking the two staging finalizers) and board #188 (JUDGMENT-CALLs 1 and 2, "OK to both").
  - **The laptop runs R27 since 2026-11-13.** The owner ran the update route himself, guided by `mac-aresos-install` (board #189): tools v1 to v2, update, title, export and reboot passed, the check was confirmed after the restart, and he set `ares`'s password (`sudo -v` passes). Checked live the same day: R27 booted, R13 as rollback, stock pinned. `at previous` has not been used on the laptop. INSTALL-STATUS records it since 27b (PR #41, merged 2026-11-13 as `4d0c4dc5`; built by a Claude agent on Opus; reviews gpt-6.1-sol: one should-fix, then SAFE; hosted checks 43439396623, 933 tests OK).
  - **Bound files may change again (27b, integrator's decision 2026-11-13).** A file bound by a rehearsal that changes records its new bytes in `os/manifest/ci/16/pending-rebind.json` (`reviews/27-first-update-release/rebind.py pending "<note>"`); the next VM rehearsal rebinds it and empties the list. Three test files and the workflow wait now, no tool, guide or image file. The next rehearsal package needs its own record step (27b's PLAN-GAP).
  - The hosted checks-only job fetches full history since 27b; before that the hosted suite failed with 9 errors from package 27's merge on.
  - **The hosted checks run the owner tools' namespace tests since 27c** (PR #47, merged 2026-11-13; a Claude agent on Opus, review gpt-6.1-sol SAFE). GitHub's runner refused unprivileged user namespaces, so the 136 tests of `test_owner_update.ToolsUpdateTest` were skipped there, and since the Windows laptop with WSL was retired they ran nowhere (on the AresOS laptop that module must never run: it reaches the real `rpm-ostree`). Now 933 tests run with 0 skipped and pass (run 43470821960). The `image` and `rehearsal` jobs still run the suite without that setup and skip them silently: give them the same step when 22c touches the rehearsal job.
  - Later fixes (harness only): cache the pinned rehearsal tool .debs; PLAN-GAP for the next image: stop masking the two finalize units. INSTALL-STATUS rows that still describe the time before the update are listed in 27b's report section.

- **The update route: `at update`, `at previous`, tools updating themselves** (PR #32, brief 22 to 22-review-fixes-9, empire brief 263, merged 2026-11-10 as `002dcc09`):
  - `at update` moves a running AresOS to a newer signed release whose reference comes only through the fingerprint-pinned tools bundle. `at previous` goes back to the last AresOS. The tools update themselves through `at install`: recovery-first, with versioned toolsets and an atomic entry switch. The guide has the step 8 route, and INSTALL-STATUS records steps 4–7.
  - Built by a Claude agent; a Fable 5.2 agent rebuilt the tools self-update from round 5 on. Reviews 1–9 were CHANGES-NEEDED. Review 10 (gpt-6.1-sol) said SAFE, and review 11 checked the merge with main as SAFE. The full WSL suite at the merged head ran 853 tests, failing only in the known WSL-only set.
  - Owner answers: board #154 (judgment calls 1 and 4) and board #166 (the rest).
  - Package 27's rehearsal walked `update` and `previous` (`unwalked_commands` is empty since then). 22c (rollback, keep-stock and layout trials after an update) comes before the second update.

- **Everyday account like Windows, Google Chrome, daily-use fixes** (PR #31, brief 21 to 21-review-fixes-6, empire brief 262, merged 2026-11-10 as `25ef5cd1`):
  - `ares` is in wheel behind his own password: sudo asks every time and keeps no ticket, no polkit authorization is cached, and the upstream passwordless rules ask instead. The control layer relies on these three properties.
  - Homebrew runs as its stock owner through sudo. Chrome is in the image. His PATH is in his shells and terminals (including the hub's Terminal app), while the session keeps the system PATH. The foot font is 16, `script` and qrencode are added, and the brightness keys are bound; they do nothing until 21b adds the backlight driver.
  - Built by a Claude agent. Reviews 1–5 were CHANGES-NEEDED (privilege hardening); review 6 (gpt-6-astra) and review 7 (gpt-6.1-sol, after merging 24) said SAFE. CI build+VM 42792865417 and the 791-test suite 42798151752 passed.
  - Owner answers: board #156, #163 (desktop shortcuts will come) and #167 (the `xdg-desktop-portal-wlr` 0.8.5 pin).
  - It reaches the laptop with the next release (package 27).

- **Interface v1: apps open from the hub on AresOS** (PR #33, brief 24 to 24-review-fixes-5, empire brief 265, merged 2026-11-10 as `7cf0541b`):
  - The OS helper `aresos-shell/1.0` (`/usr/libexec/aresos-shell`) and the mod's Linux client. Windows behaviour is unchanged.
  - Built by a Claude agent. Reviews 1–5 were CHANGES-NEEDED; review 6 (gpt-6-astra, high) said SAFE.
  - On the reviewed code: the Gradle build, two full client-test runs and the full WSL suite passed, apart from the known WSL-only failures.
  - Owner answers:
    - board #155: Notepad opens KWrite; each Chrome-logo click opens a new window; the terminal looks like a command block and the browser like a compass;
    - board #157 (2026-11-10, "Yes"): if the first app closes within half a second of switching to another, you land back in the hub.
  - It reaches the laptop with the next release.

- **Owner checklist and emergency card** (PR #14, briefs 15–15e, merged 2026-11-02 as `2f4c0d9`, under the owner's standing permission to merge once SAFE):
  - One numbered install checklist (`docs/INSTALL.md`), plus procedures, reference, records and a symptom-first `docs/EMERGENCY.md`.
  - All of it is aligned byte-for-byte with package 14's final tools: the 13-line bootstrap, every PASS line, `layout abandon` with a bounded interrupted-finish login route (below faillock's documented deny=3), resume, and the export with diagnostics.
  - Reviews REVIEW to REVIEW-4: SAFE.
  - `docs/INSTALL-STATUS.md` is the single release authority. **Physical installation: NOT RELEASED**, and its physical gates are open. The mounted-protected-child runtime refusal check is OPEN (synthetic evidence only).

- **Checked owner tools** (PR #13, briefs 14–14zzf, merged 2026-11-02 as `79a67d2`): the root-only `at` tools the owner runs from the ARESTOOLS stick. They cover:
  - a trusted bootstrap: system tools check the literal `SHA256SUMS` fingerprint `3e2c78eb…` and every file before any stick code runs
  - `install` and `prepare`, with resume
  - records and `export`, including persisted STOP diagnostics
  - token `login`, `verify`, `switch`, `title`, `rollback` and `keep-stock`
  - keyboard `layout begin/proof/revert/finish/abandon`. A trial changes only the running console; only `finish` persists it.

  **VM qualification 21** (run 41374876561, on `3fd7916`) proved the whole owner path on two file disks, with every Windows-disk capture unchanged. That includes the real token login, US International and back to German, a mid-trial `system_reset`, rollback, keep-stock and the final Windows checks.

  The review found two blocking and three should-fix issues; all were fixed, and the re-checks say SAFE (`reviews/14-owner-tools/REVIEW*.md`). Since 2026-11-01 the privacy check runs as aresync's local pre-push hook, not on GitHub.

- **Keyboard layout follows the system setting** (PR #12, briefs 13–13g, merged 2026-10-25 as `775be05`):
  - A new private release `ghcr.io/ares-empire/aresos` (owner OK): the frozen, tested image with only the 2 keyboard files changed, keyless-signed by the org workflow.
  - On stock, before the pin, `os/release/system-keyboard.sh` removes the installer's `vconsole.keymap` override from the booted deployment only. Stock's first-boot hardware setup always leaves two entries of the same commit, and the whole entry list is checked before and after.
  - The AresOS session (labwc) reads the system's X11 layout from localed.
  - VM qualification 40184846815 proved repairs from both `de` and an injected `us`; physical-key typing on tty3 (login and password sudo) and in foot under `de`, then `us`, then `de` again; and rollback to the corrected, pinned stock. All disk/NVRAM audits passed.
  - The review was CHANGES-NEEDED, then fixed in the guides (13g), and the re-review said SAFE.
  - Still open, and needs the laptop: the live-desktop keyboard step during installation. By owner decision, the backup keeps the installer's layout; US-then-rollback was not run.

- **Two-disk install rehearsal** (PR #11, briefs 11–11n, merged 2026-10-25 as `0c5902a`): GitHub Actions VMs with a stand-in Windows disk run the real Bazzite installer from the pinned ISO onto a second disk, in both drive orders. The stand-in Windows disk and its boot entry were never written (every capture byte-identical, zero writes). Proven there: the installed German keyboard files, pausing and pinning the stock copy's updaters, the signed switch to AresOS, policy, tty3 recovery login, rollback, Windows-default undo, checked BootNext, and (Part B, protected-second order) choosing the backup Bazzite from the real GRUB menu, promoting it and booting it again. Installer media are pinned. The fresh fix re-review said SAFE. **Open for the physical install:** the console keymap override was fixed by PR #12; the "selected" GRUB screenshot is inconclusive; the new Windows-first timing ran in one drive order only.

- **Mod** (PR #1):
  - Right-clicking an app item opens a real app exactly once, and you return to the game afterwards.
  - Live mode (survival, can't die) and Build mode (creative), switched with G.
  - Desktop rules apply only in worlds marked as AresOS.
- **First AresOS image** (PR #3): a Bazzite derivative booting into our labwc session, with all inherited updaters masked (including Bazzite's self-updating Cockpit container) and safe power defaults. CI boots 2 fresh VMs and proves session, recovery login, power/input and the logind power-key → poweroff path from the guest journal. Activation-graph audit deferred (`briefs/03-followup-activation-audit.md`).
- **Build/Live inventories** (PR #8): each mode keeps its own inventory and hotbar, and G swaps them atomically, so the app hotbar comes back exactly as left. Safe against `/gamemode`, stale input, lost acknowledgements and pickups during a switch.
- **Walk-in app logos** (PR #7): walk into a block logo and the app or site opens once, then you return in front of it. `/aresos logo <app> wall|floor` auto-builds logos, and `/aresos zone ...` marks owner-built ones. The builder never destroys or obstructs blocks.
- **Real apps** (PR #6): installed apps in the inventory with generated pixel icons, websites as apps, pins kept in the hotbar.
- **Nether home** (PR #4):
  - The AresOS button opens a create screen with a seed field and a placeholder-hub toggle.
  - `/aresos home set|home|home info`, and you always arrive at home.
  - Existing worlds are never rebuilt, and saves are renamed, never deleted.
- **Image release + tested switch and rollback** (PR #10, briefs 06–06e, merged 2026-10-22): a private, signed AresOS image on `bazzite-nvidia-open` (`ghcr.io/carlsenares/aresos@sha256:362af9b7…c402`). CI switches stock Bazzite to it, then proves the full policy (inherited Homebrew blocked for `ares`), the tty3 recovery login, sudo and logout, unchanged partitions, a rollback to the exact stock copy with a rendered login screen, and a second stock boot (run 39851266266). Negative checks now really fail (the `! cmd`/`set -e` bug, which also affected PR #3, is fixed). The tested recipe is `docs/INSTALL.md` §6.
- **OS design** (PR #2): Bazzite base, council-approved. See `docs/design/OS-BASE.md`.
- **Emergency card** (`docs/EMERGENCY.md`, 2026-10-23): one page for the owner's phone covering F12 → Windows, the emergency terminal, the tty3 recovery login and rollback, a safe power-off, the GRUB backup entry (UNTESTED), and when to stop and get help. Reviewed by fresh Codex until SAFE (`reviews/emergency-card/`).
- **Install guide** (PR #9, rewritten from PR #5): AresOS on its own SSD, including fitting the drive (battery check, correct seating), clear drive identification, a whole-drive install, and a Windows-return check. Council says READY-TO-MERGE. The image/switch/rollback gate is now DONE (PR #10), but **physical install stays CLOSED** until the remaining gates in INSTALL.md's "Maintainer release gate" pass (see Next). The same-drive fallback is archived.
- **Decisions:**
  - The AresOS image is **private** on GitHub (2026-10-22: the owner doesn't mind, so the safe default). The install needs a one-time GitHub read token. Public only on an explicit "make it public".
  - **AresOS gets its own 500 GB SSD** (owner decision 2026-10-22, replaces dual boot and the 96 GB partition). Crucial P310 in the free 2280 slot, so Windows keeps all its space and is never touched. **Ordered 2026-10-22** (see below).
  - **Accounts** (owner OK 2026-10-22): the installer creates the admin `ares-recovery` first (UID 1000), and the locked daily `ares` is UID 1001. The name stays `ares-recovery` (a rename isn't worth a package).
  - **Image seal** (owner OK 2026-10-22): keyless signing. Sigstore's public log shows the repo/workflow identity and the image digest; the image stays private.
  - **Laptop pull token** (owner OK 2026-10-22): a classic, read-only `read:packages` GitHub token, created by the owner on install day.
  - **GRUB recovery** (owner OK 2026-10-22): the identity-checked "make the backup Bazzite the default" step stays marked UNTESTED until a rehearsal proves it.
  - **New AresOS release for the keyboard fix** (owner OK 2026-10-25): a new private image built from the org repo to `ghcr.io/ares-empire/aresos`, same pinned base, only the keyboard-layout change, keyless-signed by the org workflow. The old release stays as history.
  - **Keyboard release built from the frozen image** (owner OK 2026-10-25, package 13's JUDGMENT-CALL): the new release is the frozen, fully tested AresOS image with only the 2 keyboard files changed, not a full rebuild.
  - **First-switch caution** (owner OK 2026-10-25, package 13's JUDGMENT-CALL): if the very first AresOS start after the switch fails, the guide says F12 → Windows → get help instead of picking a Bazzite boot entry. Right after the switch there are briefly two look-alike stock entries. After the first successful AresOS start, the guide names the backup entry.
  - **Everyday account like Windows** (owner 2026-11-09, replaces OS-BASE's locked daily account): `ares` gets admin rights behind his own password, Flatpak and Homebrew work, and `ares-recovery` stays as a spare admin. OS image and firmware changes still go only through the signed release route. Package 21.
  - **Google Chrome in the image** (owner 2026-11-09): same browser as Windows, and the one the control layer's Chrome tool targets. Package 21.
  - **Backup keeps the installer's keyboard layout** (owner OK 2026-10-25, package 13 review finding): a later layout change in AresOS doesn't change the backup Bazzite, which stays frozen exactly as tested. The guide and emergency card say so.
  - **Backup Bazzite stays frozen** (owner OK 2026-10-24, package 11's JUDGMENT-CALL): the stock copy's automatic updates are switched off at the first login and stay off for the whole trial, so the fallback is exactly the tested version. One command in INSTALL.md turns them back on if the owner returns to plain Bazzite for good.
  - **Emergency path:** Windows stays the boot default for the first trial. F12 → Windows Boot Manager is the intended way back (the Micron is never written), and `docs/EMERGENCY.md` covers the rest.
  - **Windows encryption is OFF** (checked 2026-10-23 without admin). Install day still runs `manage-bde -status C:` in Terminal (Administrator).
  - Secure Boot is off on the laptop, so nothing is enrolled. Shim's blue MOK screen still showed once at first boot; the guide now expects it: **Continue boot**, never enroll (15g).
  - Normal Minecraft is a separate app with normal rules.
  - App icons are generated automatically from each app's real icon. The owner doesn't draw them.

## In progress

- **Who works where (since 2026-11-13).** The OS lead runs on the laptop itself as `linux-aresos` (`laptop-aresos` on Windows is retired). Worktrees are `~/AresOS-NN-slug`, and the tests run natively.
  - `linux-aresos`: `os/`, the install and update documents, `STATE.md`, `HANDOFF.md`, the releases; packages 23, 22c, 21b, 25 and 26.
  - `linux-hub`: all of `mod/`, the helper's app list, `/usr/libexec/aresos-shell` and labwc's theme (the home screen, later the companions).
  - `linux-tools`: the control tools, including brief 18c (the control files in the image). `mac-aresos-control` keeps the Chrome PR #27 until it merges.
  - Touch points: labwc's `rc.xml` (21b changes key bindings there; tell each other first) and the mod jar the image pins (it moves with each release). His own programs in the hub (board #163; Lunar, Discord and Chrome first): `linux-hub` builds the listing of installed programs inside `aresos-shell` as one package with the game side; the OS lead reviews its `os/` diff before the merge, and it ships with the next release (agreed 2026-11-13).
- **The home screen (`linux-hub`, since 2026-11-13).** The owner's pointers: a flat Overworld first, app logos built from blocks that he walks into, the hotbar as the taskbar, `/name` in chat. Design: `docs/design/HUB.md` (PR #45), by a Fable design agent; his decisions so far: logos 12 blocks tall (board #207), the window frame Ares-Crown with Chrome keeping its own bar (board #206).
  - **Merged:** package 29, the mod's dev scripts under AresOS (PR #44, `640e300f`).
  - **In review or a fix round (2026-11-13 evening):** 32 the flat home (PR #50), 33 the gate logo (PR #49), 34 My apps and the mod's side of `aresos-shell/1.1` (PR #52), 38 a reproducible mod jar with the mod's tests on GitHub (PR #51).
  - **Waiting for package 23 on main:** 30 the helper lists his installed programs (brief on branch `pkg/30-installed-programs`, a Codex build) and 31 the Ares-Crown frame (brief and themes on branch `design/windows-v1`).
  - **Then:** 35 slash names (brief on branch `pkg/35-slash-names`, after 34), 36 the town builds itself (after 32, 33, 34), 37 getting around. The companions come after the hub works; they are a Windows app today and need an AresOS host first.
- **Lunar Client on AresOS (2026-11-13).** The owner's normal Minecraft client runs from his home folder (`lunar`, the official AppImage), outside the image. Package 23's Prism instance is a separate thing.
  - Minecraft 26.3 crashed at launch at first (exit code 1). Cause, found by the laptop session `linux-discord`: the game's window library (SDL3) falls back to XWayland on labwc 0.9.6, which lacks the `fifo-v1` protocol; there the game's OpenGL backend fails on the NVIDIA card ("Could not retrieve OpenGL functions", its EGL-on-X11 path; plain GLX and EGL test programs work), the game drops to Vulkan, and Lunar's Iris mod then calls OpenGL without a context. Fix in `lunar`: `SDL_VIDEO_DRIVER=wayland`, beside the three NVIDIA offload variables. Seen at 23:06 with that setting: the game on the RTX 4060 (about 590 MiB, 27 to 30% load) with sound on his headset.
  - Open: his own word that it plays well, and the frame rate (not measured; without `fifo-v1` a native Wayland window may be throttled when hidden). A labwc with `fifo-v1` in the image would remove the workaround: one more reason for the labwc item on the next image's list.
  - The first launcher was started from a Claude session and carried that session's variables into Lunar and the game; `lunar` now strips them.
- **Owner OK to merge and publish this round (2026-11-09: "Once its safe and done you can merge and publish"):** packages 21–24 merge after a fresh SAFE review, passing checks and his answers to their judgment calls. The next AresOS release built from them may be published and pinned without asking again, once its rehearsal passes. Installing it on the laptop (`at update`) is still his own step. Anything outside this round still needs his OK.
- **Package 27 merged 2026-11-13** (see Done). Left over for 22c and the next release:
  - Its JUDGMENT-CALL 2: package 22's tools can't go forward again after `at previous`, so the rehearsal ends on 13 with 27 beside it; going forward after a rollback belongs in 22c.
  - Also for 22c (PR #37 REVIEW-1 should-fix, older than that fix): the refusal invariant in `test_owner_update` tries a persistent refusal twice but never asserts that it refused. Assert the refusal on both attempts wherever the check applies.
  - Packages 23 and 21b go into the next release, which needs 22c first.
- **Main's hosted test leak fixed** (PR #37, `d5d5c447`, 2026-11-10). `test_owner_update`'s refusal invariant now undoes its injected patch however a subtest ends. Before, a namespace skip on GitHub's runner leaked a patched `disk_record` into later tests (118 errors). Hosted `checks_only` on the fix: 853 tests OK (run 42819274873). The runner still skips the namespace tests; WSL runs them. REVIEW-2 (Sol) SAFE.
- **Then:**
  - 21b: backlight and power button. The read-only check ran on the laptop on 2026-11-13 (R27, board #149):
    - Brightness: a backlight device exists now (`nvidia_wmi_ec_backlight`, firmware type, 0 to 800) and brightnessctl is installed and sees it. The panel hangs on the Intel card (hybrid mode). Whether the keys change the screen is the owner's test, still open.
    - Power button: logind watches both power-button devices and `HandlePowerKey=poweroff` is set. The journal holds one "Power key pressed short" in all boots (2026-11-09 21:40), and the fixed-feature button counter is 0. Which device reports a press, and how reliably, needs a watched press (root, or an inhibitor so the press doesn't power off).
  - The next image, beyond 23 and 21b (checked live on R27, 2026-11-13: PATH, Flatpak without login noise, foot font 16, `script`, qrencode and Chrome have arrived):
    - Control's files and `gh` 2.102 or newer (brief 18c, `linux-tools`; the image has no `gh` of its own yet).
    - Konsole as the everyday terminal (owner, 2026-11-13, board #190 and #191: "a normal terminal with easy tabs"; noted, not to be built yet). Konsole for the hub's Terminal app and any login terminal, foot stays for recovery. Mind package 23's "no login terminal" call and the checks built on foot (`image-checks.sh`, `keyboard_vm.py`, `owner_vm.py`).
    - Stop masking the two finalize units (package 27's PLAN-GAP).
    - Already on main for it: the Ares-Crown window frame (package 31, PR #54, `linux-hub`, merged 2026-11-14; the OS lead read its `os/` diff): `/usr/share/themes/Ares-Crown/`, the font in `/usr/share/fonts/aresos/`, the theme block in labwc's `rc.xml`, and a gschema override that gives programs with their own bar all three buttons. For the release: the image diff needs a rule for `gschemas.compiled` (compiling rebuilds every default, so look at the others too), and a theme change moves its checksum in `os/ci/image-checks.sh`.
    - For the guides of that release and of 22c (what he notices after `previous`): since package 34 the mod writes `apps.json` in schema 3 and keeps a backup; a release with an older mod jar refuses that file with a message and starts without apps, so after going back his app list is empty until he goes forward again. Nothing is lost (`linux-hub`, 2026-11-13).
    - labwc with pointer constraints on layer-shell surfaces (reported 2026-11-13 by the laptop session `ares-e7`), so the owner can use the laptop's mouse and keyboard on his MacBook through Lan Mouse (set up in his home, its unit disabled until then; Deskflow cannot work on labwc, which has no InputCapture portal). labwc 0.9.6 in the image never applies the pointer lock to Lan Mouse's capture surface. Upstream fixed it in labwc 0.20.3 (commit `b7820667a2`, "allow constraints for wlr_layer_surface_v1"); Fedora 44 only has 0.9.6. Two routes for a package: backport that one commit onto 0.9.6 (the smaller change to the session he uses daily, if it applies), or build 0.20.3 (the image already has wlroots 0.20.2). Either means building labwc in the image build, which is new. His call with the release.
    - A short command for the owner tools (owner, 2026-11-13, board #195: "Can we just make it 'update' or like 'AresOS update' in the terminal? Instead of going /var/lib etc"): `aresos update` and the other words, a root-owned command in the image that runs the same tools and asks for his password. The guides keep the full path as the way that always works.
      - Agreed with `linux-tools` (2026-11-13): `/usr/bin/aresos` is one command, owned by the OS. A small dispatcher routes the owner tools' words (update, previous, rollback, keep-stock, check, title, records, export, login, verify, switch, install, prepare, layout, reboot, logs) to the owner tools through sudo and hands every other word, unchanged, to Control's own command, which then lives at `/usr/libexec/aresos-control/cli`. Control reserves those words (a test pins it) and drops its top-level `log` shortcut then. Brief 18c installs Control's wrapper as `/usr/bin/aresos` until that package.
    - Control in the image (brief 18c, `linux-tools`, PR #42): the `os/` side is agreed in the brief's section "Agreed with linux-aresos on 2026-11-13" (a fixed UID for its system user, its config under `/usr/share/aresos/control`, a failed service never delays login or breaks Claude Code). Its `os/` part starts after 23 and the Chrome PR #27 are on main, and it merges only after the owner's yes to the next release carrying Control. The next release's rehearsal covers the update from R27 with Control.
  - **22c: council held, brief in revision (2026-11-13).** `reviews/councils/2026-11-13-22c-ways-back/VERDICT.md`: GAPS-FOUND (11). The direction stands (any order of the checked set of installed systems, one identity-checked reorder, a journal on every change, one destination per command word, a model test). What changes: an open journal is settled from the deployment list by any command, so a restart that lands elsewhere or a cut-off reorder never leaves every command refusing; a stage 0 probes plain `set-default` in a VM first; on stock the tools check that Bazzite's updaters are still off. One package in three stages. Empire brief 278.
    - Owner (board #205, 2026-11-13: "Yes, tools on their own first"): the repaired tools go on the laptop in their own short session before the next release. This replaces his earlier "next release" (board #196, where he also asked whether Claude can install them if he approves the password prompt: yes, under hard rule 1, with `sudo -A` and the desktop's password dialog; not tried yet).
    - Integrator's decision on the council's unanimous advice: `update` goes to the newest installed AresOS from anywhere, also forward after `previous` and back from stock. The owner was asked twice (board #195, #204) and had no view; he sees it as a JUDGMENT-CALL with the "try this" note before the merge.
    - After the install: one calm laptop test with him (the boot menu, the older AresOS and back, stock and back). Bazzite stays frozen while AresOS is installed (decided 2026-10-24).
  - P2's remaining packages: 25 (guardian: clean save and shutdown) and 26 (backups).
  - Desktop shortcuts and the app wheel (owner, board #163): they open the apps from the hub and his own programs (`~/.local/bin`, Homebrew, Flatpak exports), each found by its full path.

- **Package 12 (the companion in the hub)**: brief drafted 2026-10-25, waiting for the owner's go. A generic companion system in the mod (look packs as data, an original placeholder look), with the owner's Claude crab as a private pack outside this repo. The desktop companions live in the private repo `Ares-Empire/companions` (browser preview: `python tools/serve.py`, then http://127.0.0.1:8765/preview/).

## Waiting on the owner

- **Hardware FITTED 2026-11-07** (Stage B): the Crucial P310 500 GB sits in the free 2280 slot; the Windows drive, a Micron 2450 **2242** (MTFDKCD512TFK), was left alone. Ordered 2026-10-22 (€127.05): Crucial P310 500 GB, Kingston 2×64 GB sticks, Wera 2050 PH0 + PH1 screwdrivers. The SSD is kept, so its return window no longer matters.
- Hub: the owner explores seeds, picks a spot and builds it in creative later. Nothing is locked until they say so.

## Next, in order

1. **Physical install, staged (owner decision 2026-11-02; package 16 merged as `4e69540`):**
   - **Stage A (steps 1–2) is DONE and CHECKED (2026-11-05),** recorded in INSTALL-STATUS by PR #1 of the public repo (merged `e0f737b`).
   - **Stage B (fitting) DONE and CHECKED 2026-11-07,** guided step by step (recorded in INSTALL-STATUS by PR #13, merged `f5bc2d4d`). Battery, seating and Crucial-label photos PASSED (checked by a Claude session on the Mac; the photos stay private). The F2 screen listed both drives (owner-reported: an "M…" and a long "C…" name; no photo). By owner decision, the maintainer's read of Windows' disk inventory (Micron GPT, Crucial `CT500P310SSD8` 466 GB RAW) stands in for checking that screen. The expendable fitting trial and the damaged-battery photograph trial stay OPEN; they are not Stage C conditions. Record B after-fit PASSED: Windows disk identity, all partition GUIDs/types/boundaries and the original Windows boot target match record A. A broken bottom-cover screw post (front corner, likely the old rattle) was removed, so that one screw stays out.
   - **Stage C (install) is RELEASED 2026-11-07** (PR #13; reviews gpt-6-astra: CHANGES-NEEDED fixed, then SAFE). The owner does steps 4 onward; each step's record goes to the maintainer before the next. While the laptop runs the live stick or AresOS, a Mac session checks the screens; the Windows parts (tools stick, record B after-bazzite) run with the laptop session.
   - **Step 4 DONE 2026-11-08** (Bazzite stock installed on the Crucial, tools installed, `at prepare` PASS twice, title, records and export PASS; Linux online since ~21:30). On the way:
     - The first install's passphrase was refused, so the owner chose a reinstall (board #114).
     - Live KDE ignored the German layout until `sudo localectl set-x11-keymap de` (#99/#100).
     - Record A's Micron "Serial" is Windows' EUI-64 drive ID, not the printed serial. A private card in the owner's OneDrive record folder carries the printed one (#122).
     - Lenovo's firmware recreates its own "Fedora" entry for the Crucial ESP at every start, so `at install` stopped. Fixed by PR #22 (15f): one such alias is allowed beside Bazzite; tools fingerprint `3ef85c4a…`. The owner chose to go on without rerunning the VM rehearsal; the files waiting for it are in `os/manifest/ci/16/pending-rebind.json`.
     - Since 2026-11-08 Claude runs the Windows-side steps itself (CLAUDE.md hard rule 1).
     - The ares-recovery passphrase is still the temporary one; the owner will change it.
   - **Step 5 COMPLETE 2026-11-09:** Windows started unattended and record B after-bazzite PASSED (11-08, 21:50); the Linux half PASSED at 19:16 (check, title, records, typing and password proof, mounts and EFI on Crucial only, Windows first in BootOrder).
   - **Step 6 DONE 2026-11-09:** `at login` (the first try was refused and wrote nothing; the retry passed), verify, switch, title and reboot PASS. AresOS's first start shows labwc + foot.
   - **Step 7 done with two open items 2026-11-09** (owner's call: move on, fix both in the next image package):
     - PASS: check, title, records, console and foot typing, sudo, RTX 4060, network after reboot, sound, touchpad, Super+Ctrl+Escape, a second Linux boot, `at logs`. Record B after-aresos PASS at 20:08, and Windows' network, files and sound are fine.
     - **Brightness FAIL** (#139): no `/sys/class/backlight`, no brightnessctl, F5/F6 unbound.
     - **Power-button gate OPEN** (#140): a short press never reaches logind. In Windows the button is set to sleep, so it never shut down there either.
   - **Next image package (a release he approves, with a rehearsal):**
     - `~/.local/bin` on `ares`'s PATH, set in the image's bashrc or profile.d. foot starts with `--rcfile /usr/share/aresos/bashrc`, so `~/.bashrc` is skipped there.
     - A browser route for `ares` (`build.sh` makes flatpak 0700, so no Firefox; decide the route). Also quiet the resulting noise: every login shell prints `/etc/profile.d/flatpak.sh: /usr/bin/flatpak: Permission denied`, and the user generator 60-flatpak fails.
     - Brightness and volume keys (#139) and the power button (#140).
     - A bigger foot font at 1080p (he uses 16).
     - `script` (util-linux) and qrencode.
     - His account installing software normally (#102/#106).
     - Control's `/etc/claude-code` files, once brief 18d is on main (#136/#137), and `gh` 2.102 or newer in the image for its Chrome tool (board #150, 2026-11-10).
     - Record steps 5–7 in INSTALL-STATUS.
   - **Claude Code runs on AresOS as `ares` (DONE 2026-11-09, reported by `mac-aresos-install`).** It has a full `claude auth login` (signed in on his phone through a one-time LAN page, so Remote Control works); the interim setup token is deleted, and he revokes it if claude.ai lists it. In `$HOME` only: gh and gitleaks (checksum-verified, in `~/.local/bin`; gh logged in), an interim PATH in `~/.bashrc` (Claude Code's shell reads it), aresync's new-machine checklist with systemd user units, 21 repos cloned, and foot font 16. Sessions there are named `linux-…` (aresync PR #1). The plan it followed:
   - **Right after step 7 PASS: Claude Code for the daily `ares` user** (owner wish 2026-11-09, via `mac-aresos-install`; he wants to build companions, app tools and the home screen inside AresOS). The image allows it: `ares` has a writable home (`/var/home/ares`) and a terminal (foot) at login; step 7 proves network. Steps: in foot, `curl -fsSL https://claude.ai/install.sh | bash` (no admin needed), then start `~/.local/bin/claude` by its full path, because the AresOS terminal doesn't search `~/.local/bin` yet (`/etc/profile.d/aresos.sh` fixes PATH for UID 1001, and foot reads only the image's bashrc). Sign-in: `ares` can't run flatpak (no Firefox), so the owner makes a `claude setup-token` on the Mac himself, copies it with scp into a 0600 file in `ares`'s home, and starts Claude with `CLAUDE_CODE_OAUTH_TOKEN` from that file (guided by `mac-aresos-install`; the token never passes through a Claude session). Switch to a normal sign-in once the next image has a browser route. The lasting fix (that path in `ares`'s PATH, and his account installing software normally, board #102/#106) goes into the next image package, which needs his OK as a release.
   - **Guide fixes from install night: DONE** (PR #23, briefs 15g and 15gb, merged as `a1052cf0` on 2026-11-09; built by gpt-6-astra, review 1 CHANGES-NEEDED fixed, review 2 SAFE). They cover the Micron printed serial (its own Windows checkpoint), live German via `localectl`, the bounded reinstall route, the expected MOK screen (Continue boot), who does what, the console fallbacks and Bazzite naming. Also the **ten-minute hung-shutdown rule**: wait 10 minutes without progress, then force off only under its conditions, then Windows and Help (owner OK 2026-11-09, board #125). `pending-rebind.json` now lists the 12 bound files changed since the package 16 walk.
2. **First boot: DONE 2026-11-09** (install steps 4 to 7 above): plain AresOS (labwc + foot) boots from the new SSD, GPU, network and sound work, and Windows still boots unchanged.
3. **Minecraft inside AresOS** (P2): Prism and Microsoft login, the Nether world, mod ↔ OS helper (interface v1), clean save and shutdown, backups.
4. **Full trial** (P3): boot → Nether hub → open/close an app → shut down → Windows still fine.
5. **Later:** a help button in AresOS that opens a terminal with Claude Code (owner idea 2026-10-22, after the first boot works), piglin shops, owner-designed hub, shaders, controlled updates, boot splash, sleep, Brawl Stars theme.
6. **AI-native control layer (owner idea 2026-11-05; started 2026-11-07, before the first boot):** every app, with
   all of its features, as clean tools (CLI and MCP) for a central Claude Code session; Mail and Chrome first. The
   plan, the owner's decisions and where it stands: `docs/control/PLAN.md`. The owner's picture:
   `reviews/councils/2026-11-07-control-layer/OWNER-SCOPE.md` (wins over that council's VERDICT). Led by the Claude
   session `mac-aresos-control`; it changes nothing under `os/`, `mod/` or the install docs without telling
   `laptop-aresos` first.
   - **On main (2026-11-07):** the plan and design (PR #2, design draft 9; PR #11, drafts 10 to 16 with the Chrome
     checkpoint, `c7ba7a71`), the shared base (brief 18, PR #6), the sandbox boundary (brief 18b, PR #5, merged as
     `6b2667f`) and the Chrome checks 17 to 17e (PRs #3, #4, #7, #8, #10). Check 17e showed that a local checkpoint
     outside Chrome holds every tested send; the owner chose it then (decisions 6 to 13) and replaced it on
     2026-11-08 with the light tool (decision 25). On 2026-11-08: the design for decisions 22 to 24 (PR #16, design
     draft 25, `0ae9f903`). On 2026-11-11: the owner's safety bar for the tools (safe like a normal MCP or CLI) and
     his re-scope answers (PRs #38, #39). **On 2026-11-12: Mail** (brief 19 with 19b, PR #9, `25528195`): read,
     search, sort and send; every send, delete and unsubscribe asks. CI tests it against test mail servers; not yet
     tried with a real account. **The slim base** (brief 18d, PR #25, `9b27a2fe`): the managed settings hold only
     the generated ask rules and two hooks, our servers install at his user scope, and Mail's descriptions shrank
     from 86,557 to 21,055 characters.
   - **Decided:** the approval surface (decision 21, after six phone tests): Claude Code's own prompt, at the laptop
     and through Remote Control on his phone, with every asking input starting with the tool service's `question`
     sentence. On 2026-11-08 (decision 24, replacing the containment parts of decisions 22 and 23): AresOS runs
     normal Claude Code, as on any OS, plus our tools, which must be safe in themselves and not make things worse
     than normal Claude Code. One session does coding, commands, mail and Chrome as his own user, with his own `gh`
     login and his own MCP servers, skills and plugins, possibly in skip-permissions mode; sends, deletes and submits
     through our tools ask through managed ask rules. The separate assistant and coder accounts aren't needed, and
     his account installs software normally. Chrome (decision 25, "B is good"): a light tool of our own in his normal
     Chrome, with no proxy and no certificate; it asks before anything that clearly sends, and a page that sends on
     its own after an ordinary click isn't held, as with Claude in Chrome.
   - **In progress:** the Chrome tool (brief 20, PR #27, led by `mac-aresos-control` until it merges, planned
     2026-11-16): a fix round for four findings of its re-check, then main merged in, Chrome moved onto the slim
     generator, test group 12 in 18d's harness, and reviews of the combined head. `linux-aresos` owns `os/` and the
     accounts.
   - **Since 2026-11-13 the AresOS-side session `linux-tools` leads the tools** (`docs/control/TOOLS-HANDOFF.md`):
     - **Brief 18c, the image test with the tools inside** (`briefs/18c-image-test.md`, PR #42, `25c0df62`), with
       the `os/` change agreed with `linux-aresos` (sixteen changes, in the brief). Its container part is on main
       (PR #43, `1108fc30`): the service's unit may reach the network (Mail couldn't under the real unit before), and
       17 cases prove in interactive Claude Code that the send question holds with allow rules, a `PreToolUse` allow
       hook, "don't ask again" and skip-permissions; a `PermissionRequest` allow hook approves, the accepted residual,
       now pinned for the interactive case. The image part (Part A and B2) waits for package 23 and PR #27 on main.
       Part A merges only after the owner's yes to a release carrying Control (a background service, two managed
       hooks in every Claude Code session). Owner answer: the tools use `Downloads` and `Documents` (board #203).
     - **The Chrome capability briefs** (branch `briefs/28-chrome-capability`, not merged): 28 (reading: outline,
       short references, folds, paging), 28a (acting: open, go, batched steps, the smaller tool list) and 28b (his
       own open tabs), with section 6 of `CONTROL.md` rewritten to match. Two Codex review rounds are worked in; the
       final checks are `BRIEF-REVIEW-3.md` and `BRIEF-SECURITY-3.md` in `reviews/28-chrome-capability/`. Building
       starts after PR #27 merges; none of the three reaches the laptop before all three are merged. Owner answers
       (2026-11-13): Claude may close his tabs when he asks (#201); text only first, no screenshots (#202); typed
       text in form fields is read only after asking (#210, "Ask first"); link addresses are shown (#213).
     - **Then:** brief 18c-b (Chrome's browser side in the image; where the extension is served from and where its
       key lives are open, board #194), and the live tests with the owner once a release carries the tools (Mail
       onboarding first; his own hosts go on Chrome's never-list in that sitting, board #200).

Codex Pro runs until 2026-11-21.
