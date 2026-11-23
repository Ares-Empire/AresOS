# AresOS state

## Now

- The laptop runs R28 with R27 as rollback, corrected stock Bazzite pinned and owner tools v5. The real home has had its first try-out. [Install status](docs/INSTALL-STATUS.md) · [Hub findings](docs/HUB-HANDOFF.md)
- R29 is in preparation. See [the OS lead's handoff](HANDOFF.md) for the cut and release gates. Check live Git and PR state at session start. Update this page when a decision or the queue changes. Git and `reviews/` hold completed work.
- Notify the other leads before changing shared `rc.xml` bindings, helper app listings or cut inputs. The OS lead reads every other session's `os/` diff before merge. The hub sends the merged mod SHA and reproducible jar hash from main's Mod run, and the OS lead renews the pin at the cut.
- Stay in your own worktree. Use a noreply Git identity and keep the privacy check enabled. Never force-push, push `pre-rewrite/*`, or bypass hooks with `--no-verify`. Builders never merge or push to `main`.
- On the laptop, keep heavy work to one run at a time. Use the locked headless dev scripts for Minecraft. Keep windows, input and test clients out of the owner's session and leave the real Minecraft folder and Lunar Client alone. Run only named affected `os/tests` modules, one at a time. Never run `test_owner_update.py` on the laptop, since it reaches the real updater. Use hosted checks for the full suite. [Agent rules](AGENTS.md)
- Check new test assumptions against retained real output. Wait for hosted jobs with a polling interval of at least 60 seconds and observe the shared API allowance. Keep at most one verified copy of each large download in the worktree's `.work/` and remove extracts, partial downloads and duplicates when the step ends.
- Keep the source-binding ledger current when rehearsed files change and rebind after the next qualifying rehearsal. Keep the partition-type and identity checks in step with any future layout change. [Binding procedure](reviews/27-first-update-release/REPORT.md)

## Who works where

- `linux-aresos` — OS image, install and update docs, release B331 (R29), package 43 and the 23c brief.
- `linux-desktop` — B321 Deskflow image integration, the look and window components and the desktop-side pieces of B332.
- `linux-tools` — Control, Chrome capability packages 28/28a/28b, the R29 Chrome first-use handoff and owner trial.
- `linux-laptop-home` — B334a hosted test bench and later B334 tiers, plus package 53's trial after 23c.
- `linux-hub` — Minecraft home and mod, B333 open-app marks and activation, B332 home styles, B328 prototype trial and T364 sleeping-world study.

## Owner decisions in force

- Keep the image private unless the owner explicitly makes it public. Use a keyless signature with the repo/workflow identity and digest in Sigstore's public log. The owner creates the classic read-only `read:packages` pull token and keeps credentials private (owner, 2026-10-22)
- AresOS uses its own 500 GB Crucial P310 SSD. Never partition, format, resize, mount for writes or write to the Windows SSD or alter Windows boot files. Same-drive dual boot is a documented fallback only (owner, 2026-10-22)
- Windows stays the boot default for the first trial. Use F12 → Windows Boot Manager for recovery. Keep GRUB stock-default promotion marked untested until rehearsed (owner, 2026-10-22)
- With Secure Boot off, choose Continue boot on the expected MOK screen and never enroll. Stop on other signature or enrollment screens (owner, 2026-11-09)
- Keep the stock Bazzite fallback frozen and its automatic updates off throughout the trial. Re-enable them only if the owner returns to stock for good (owner, 2026-10-24)
- The stock backup keeps its own tested keyboard layout. If the very first AresOS boot after switching fails, use F12 → Windows → get help, since there can briefly be two look-alike stock entries (owner, 2026-10-25)
- Keep fitting photos, the physical drive serial and raw install records private. The maintainer's disk inventory stands in for the firmware-screen check. For a physical install, keep the staged checkpoints and send each step's record to the maintainer before continuing. Confirm encryption status and save the matching recovery key if encrypted. Stop on unknown or encrypted status for owner review. [Install guardrails](docs/INSTALL.md) (owner, 2026-11-07)
- For real disk, partition, boot, firmware or system software changes, explain the action and risk and wait for explicit approval. Claude may carry out approved steps. The owner supplies passwords and does hands-on steps (owner, 2026-11-08)
- Read-only checks need no approval. Codex never runs disk or boot tools on the real laptop (owner, 2026-11-08)
- Ask once per Windows system tool before installing it (integrator, 2026-10-21)
- Relayed answers cover branch work only. Get approval for real laptop changes directly from the owner (integrator, 2026-11-21)
- The installer creates `ares-recovery` first as admin at UID 1000 and reserves UID 1001 for the owner's daily account. Keep both [account names and IDs](docs/design/OS-BASE.md#image-delivery-decision) (owner, 2026-10-22)
- The daily account has admin rights behind the owner's password and can install and use apps with Flatpak and Homebrew. Keep the spare recovery admin (owner, 2026-11-09)
- Sudo asks every time. Sudo and polkit approvals never cache, and there is no passwordless bypass (owner, 2026-11-09)
- Keep image and firmware tools out of the daily account's ordinary admin prompt. Use the signed release route or the owner's explicit `sudo` (owner, 2026-11-09)
- Ship Google Chrome in the image. It is the everyday browser and Control's Chrome target (owner, 2026-11-09)
- On a hung shutdown, wait ten minutes without progress, force off only under the emergency card's conditions, then use Windows and get help (owner, 2026-11-09)
- Use one normal Claude Code session as the owner, with ordinary coding, commands, GitHub, MCP, skills and plugins. Offer app features as CLI and MCP tools, Mail and Chrome first. Keep service credentials out of Claude. [Control decisions 21, 24 and 25](docs/control/PLAN.md) (owner, 2026-11-08)
- Use Claude Code's own approval prompt on the laptop or through phone Remote Control, even with skip-permissions. Put the service question first and bind the exact send, delete, payment, unsubscribe or submit for approval. Claude cannot supply or replay consent. Validate inputs, use least access and mark untrusted content. Fix risks that can cause real harm and record low-harm limits (owner, 2026-11-11)
- A matching `PermissionRequest` allow hook can approve a managed ask. Keep asking tools out of the owner's hook matches (integrator, 2026-11-12)
- Chrome uses a light tool in the normal browser with no proxy or certificate. Ask on clear sends. An ordinary click can let a page send on its own, as in Claude in Chrome (owner, 2026-11-08)
- For Chrome, use text first without screenshots, show link addresses, ask before reading typed form text, and close the owner's tabs only on request. Loosening Chrome's policy takes a fresh admin password (owner, 2026-11-13)
- Before leaving or closing a Chrome tab, report unsaved typing and playing media. Get the owner's approval in chat if their typing would be lost (owner, 2026-11-13)
- Tools use Downloads and Documents. A stopped Control service stays quiet in sessions that never used it (owner, 2026-11-13)
- Choose Codex or Claude builders per task and allowance. Use Opus by default for Claude builders and Fable for hard work or work that resists normal attempts (owner, 2026-11-09)
- Use Fable for actual design (owner, 2026-11-13)
- Codex builders get full access in their assigned worktree. Reviews run read-only (integrator, 2026-10-21)
- Every package gets a fresh reviewer independent of the builder. Use a fresh Codex context while available, Opus by default for Claude reviews, and Fable for high-stakes or final laptop reviews (owner, 2026-11-11)
- Bring hard-to-undo choices or changes to how AresOS feels to the owner before merge (owner, 2026-11-11)
- Only the integrator merges, after a fresh SAFE review of the current head, passing checks and the owner's answers to judgment calls (integrator, 2026-10-21)
- Get `mac-capacity` approval to use the active API promo for Fable design or reviews. Carry the route and expiry into the next handoff while it is active (integrator, 2026-11-21)
- For briefs, get a Claude review followed by a cross-model review (owner, 2026-11-18)
- Use real Minecraft as the first shell. Normal Minecraft stays a separate app with normal rules. Generate icons automatically from installed apps. Never commit Mojang or Supercell assets. Load vanilla textures and fonts at runtime (owner, 2026-10-21)
- The owner picks the Nether seed and home spot after exploring. Keep old saves when changing home (owner, 2026-10-21)
- Use KWrite for Notepad. Return to the hub if the first app closes within half a second of switching to a second app (owner, 2026-11-10)
- Start with a flat Overworld, 12-block walk-in logos, the hotbar as the taskbar, and short app names in chat. Chrome keeps its own bar (owner, 2026-11-13)
- The laptop home is a street by day on terraces, with night as a second look. Dim apps until used, show only clock, date and battery, and change pins in the world. Reserve Super to search over the world and launch the chosen app there (owner, 2026-11-16)
- Draw the laptop home natively in GTK and Cairo (owner, 2026-11-18)
- Use the Bar look for search (owner, 2026-11-19)
- With a monitor attached, show the world there and a picture behind laptop-screen apps. Keep the cursor crossing screens and prototype look controls that avoid holding the right button. Clicking the world leaves part-screen windows above it. Apps first open full and then remember their size (owner, 2026-11-21)
- Protect blocks from mining in Live, keep Build mode in the home menu, hide tutorial toasts, make clear that starting a new home keeps the old one, and use a black concrete Terminal item and rimless gate (owner, 2026-11-21)
- Keep the in-game hotbar and the outside bar. A left click opens or brings back an app. Use one bar per screen where applicable and reserve its height while shown. The bar stays visible on an unfilled screen and can reappear at the edge over a full-screen app. World Off uses a plain picture by default, with black or an owner's picture as alternatives (owner, 2026-11-21)
- Use the Minecraft look for the OS's own indicators, buttons, menus and password windows first, then develop a second design in the Ares apps' style. Use Windows as orientation for familiar controls while designing original, useful features (owner, 2026-11-18)
- Default to the game's runtime textures (look B), with original art A as a setting and fallback and the game's buttons C as another setting. Make the plate's position and size settings, defaulting to top centre and medium (owner, 2026-11-19)
- Window frames follow the selected look. Keep Ares-Crown available until its replacement is built (owner, 2026-11-20)
- AresOS can run as a normal OS. Make its designs and features switchable, including which design, which home and whether tools are on. A key piece can stay fixed if a switch is unnecessary or impossible. Give normal features an original technical and visual design, such as arranging icons and choosing when the taskbar stays visible or hides (owner, 2026-11-22)
- Keep the power button on clean shutdown (owner, 2026-11-19)
- On planned stops, keep screens black while saving and prevent a closed lid from suspending mid-save (owner, 2026-11-19)
- Hide the game's saving text (owner, 2026-11-17)
- Use Deskflow with a shared clipboard from the laptop to the Mac, with the normal qualification gates. Brightness, volume and mute keys go to the Mac while it has the keyboard (owner, 2026-11-21)
- Provide a normal terminal with easy tabs. Use Konsole for the hub Terminal and any login terminal, with foot for recovery (owner, 2026-11-13)
- Ctrl+V pastes in the terminal (owner, 2026-11-18)
- Release contents aren't locked: anything SAFE and green may ride the next release if it doesn't put that release at risk, otherwise it takes the next one. This replaces the earlier rule that Chrome 28, 28a and 28b reach the laptop together (owner, 2026-11-23)
- Provide routine signed updates in a terminal without Windows or a USB stick, using the verified local-folder route for tools installs. Stage while the OS runs, restart once, and keep the previous version. Keep the stick and Windows copy for emergencies (owner, 2026-11-14)
- For a verified-folder install, the owner enters the password only if the prompt's eight-character fingerprint matches `docs/OWNER-TOOLS.md` on GitHub (owner, 2026-11-14)
- `aresos update` uses a newer installed release without downloading. It fetches only if no newer release is installed. It announces its choice before changing anything (owner, 2026-11-14)
- The separate inner update may replace a newer installed version from an older boot and must tell the owner before restart (owner, 2026-11-14)
- Throwaway CI images need no approval if they are never pushed to a registry or pinned (owner, 2026-11-07)
- Private releases may be published and pinned without asking again once the required reviews, checks and rehearsal pass. The owner still controls installation on the laptop, spending and making anything public (owner, 2026-11-19)
- From R29 on, a release candidate may be uploaded privately before its VM rehearsal. The pin waits for passing rehearsal and final review. Board T480 (owner, 2026-11-21)
- Use repo-relative paths or `owner` in home paths. Commit no secrets, real usernames or personal material (owner, 2026-11-15)
- The repo is public. Write `the owner` in everything committed, including commit messages. Leads enforce this by hand because the privacy check cannot catch names. Board T433 (owner, 2026-11-20)
- Use a hidden rootless test desk with an opt-in private simulated network. Real internet requires verified egress. Board T499 (owner, 2026-11-22)
- A laptop bench VM must fit and work, with a memory watcher, 40 GB cap and automatic cleanup. Board T500 (owner, 2026-11-22)
- Read-only hardware checks after updates and about ten minutes of owner checks per release are approved. Boards T501–T502 (owner, 2026-11-22)

## Next in order

1. Deskflow and R29. Finish B321's qualification and B331's cut, rehearsal and pin. Finish B334a's hosted bench in parallel with review and merge order agreed with the OS lead. [Deskflow brief](briefs/321-deskflow-image.md) · [Bench brief](briefs/334-test-bench.md) · [OS handoff](HANDOFF.md)
2. Hub try-out follow-ups and memory (T364). Try B328's controls and time boot-to-home (T362). Study swap and SSD wear, prefetch on wake and Prism's memory. Follow B332's world-off and sleep gates. Brief 23c for monitor placement, native laptop home and Super search, then trial it on the laptop. [B332 brief](briefs/332-outside-game-design.md) · [53/23c agreements](briefs/53-laptop-home-build.md#agreements-carried-from-state)
   - Keep terminal `lunar` as the owner's launcher until the owner tries launching Lunar from the hub on a release with hub support.
3. Tools. Finish Chrome 28/28a/28b, then the owner sitting (Mail onboarding first and Chrome's excluded hosts before use), adapters, Aresium and the first Minecraft tool alongside. [Chrome sequencing](briefs/28b-chrome-his-tabs.md#agreements-carried-from-state)
4. Normal OS pieces in the Minecraft look. Build the remaining frame looks, layouts, per-output covering, app switching and overview. Use a separate review on the password window's checked path. Desktop shortcuts and the app wheel open hub and locally installed apps by full path. [Component build order](docs/design/COMPONENTS.md#6-what-each-look-costs-and-the-build-order)
   - Build frame looks B and C after the shared look B texture work. Keep the reviewed Ares-Crown pin through R29. Explain each open design choice to the owner through `board ask`.
5. Run the quick Claude-runs-the-laptop trial on R28 and the full one after tools. Recheck the boot menu and each way back with the owner, and give the owner the post-update hardware checks.
   - Keep the owner's replacement of the temporary recovery passphrase pending until the owner confirms it.
6. Companions in order, AresOS host, hub companion (package 12 awaits the owner's go), then app-logo entry into the real app. Use data-driven original placeholder art in public and keep the owner's crab in a private add-on.
7. Package 43 step 6. The OS-owned dispatcher routes the reserved maintenance words to the owner tools and hands every other word unchanged to the Control CLI at `/usr/libexec/aresos-control/cli`. It dispatches only the supported desktop maintenance commands, refuses reserved words such as `layout` and `login`, and sends those to the recovery console, where `sudo /var/lib/ares/at` stays the fallback. Take 43's reviewed handoff if it lands before the cut.
8. The later in-image updater verifies the workflow signature and signed release list, rejects older or foreign images and carries the tools for the next update. The first release arrives by the verified-folder route. Get a council and Fable review for the trust change.
9. Add backups (26). Adopt Konsole with an opaque profile, keeping foot for recovery and covering the foot-dependent checks and the no-login-terminal decision.
   - If the image takes over the login terminal, start Konsole maximized and remove the owner's interim `.bashrc` hook that starts it from the first foot shell.
10. Later, more app tools, Minecraft player stages, a Claude Code help terminal and a second AresOS design. Open follow-ups include the legacy installer picker pin and same-drive fallback media, existing-instance memory setting migration, and a full boot-to-home, app, shutdown and Windows-return trial.
