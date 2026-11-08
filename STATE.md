# AresOS: state

Updated 2026-11-07. The live truth is `git log`, `gh pr list` and `git worktree list`. Update this file when a PR merges or a decision lands.

## Done (on main)

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
  - **Backup keeps the installer's keyboard layout** (owner OK 2026-10-25, package 13 review finding): a later layout change in AresOS doesn't change the backup Bazzite, which stays frozen exactly as tested. The guide and emergency card say so.
  - **Backup Bazzite stays frozen** (owner OK 2026-10-24, package 11's JUDGMENT-CALL): the stock copy's automatic updates are switched off at the first login and stay off for the whole trial, so the fallback is exactly the tested version. One command in INSTALL.md turns them back on if the owner returns to plain Bazzite for good.
  - **Emergency path:** Windows stays the boot default for the first trial. F12 → Windows Boot Manager is the intended way back (the Micron is never written), and `docs/EMERGENCY.md` covers the rest.
  - **Windows encryption is OFF** (checked 2026-10-23 without admin). Install day still runs `manage-bde -status C:` in Terminal (Administrator).
  - Secure Boot is off on the laptop, so no MOK step.
  - Normal Minecraft is a separate app with normal rules.
  - App icons are generated automatically from each app's real icon. The owner doesn't draw them.

## In progress

- **Package 12 (the companion in the hub)**: brief drafted 2026-10-25, waiting for the owner's go. A generic companion system in the mod (look packs as data, an original placeholder look), with the owner's Claude crab as a private pack outside this repo. The desktop companions live in the private repo `Ares-Empire/companions` (browser preview: `python tools/serve.py`, then http://127.0.0.1:8765/preview/).

## Waiting on the owner

- **Hardware FITTED 2026-11-07** (Stage B): the Crucial P310 500 GB sits in the free 2280 slot; the Windows drive, a Micron 2450 **2242** (MTFDKCD512TFK), was left alone. Ordered 2026-10-22 (€127.05): Crucial P310 500 GB, Kingston 2×64 GB sticks, Wera 2050 PH0 + PH1 screwdrivers. The SSD is kept, so its return window no longer matters.
- Hub: the owner explores seeds, picks a spot and builds it in creative later. Nothing is locked until they say so.

## Next, in order

1. **Physical install, staged (owner decision 2026-11-02; package 16 merged as `4e69540`):**
   - **Stage A (steps 1–2) is DONE and CHECKED (2026-11-05),** recorded in INSTALL-STATUS by PR #1 of the public repo (merged `e0f737b`).
   - **Stage B (fitting) DONE and CHECKED 2026-11-07,** guided step by step (recorded in INSTALL-STATUS by PR #13, merged `f5bc2d4d`). Battery, seating and Crucial-label photos PASSED (checked by a Claude session on the Mac; the photos stay private). The F2 screen listed both drives (owner-reported: an "M…" and a long "C…" name; no photo). By owner decision, the maintainer's read of Windows' disk inventory (Micron GPT, Crucial `CT500P310SSD8` 466 GB RAW) stands in for checking that screen. The expendable fitting trial and the damaged-battery photograph trial stay OPEN; they are not Stage C conditions. Record B after-fit PASSED: Windows disk identity, all partition GUIDs/types/boundaries and the original Windows boot target match record A. A broken bottom-cover screw post (front corner, likely the old rattle) was removed, so that one screw stays out.
   - **Stage C (install) is RELEASED 2026-11-07** (PR #13; reviews gpt-6-astra: CHANGES-NEEDED fixed, then SAFE). The owner does steps 4 onward; each step's record goes to the maintainer before the next. While the laptop runs the live stick or AresOS, a Mac session checks the screens; the Windows parts (tools stick, record B after-bazzite) run with the laptop session.
2. **First boot:** install onto the new SSD and switch to the AresOS image. Plain AresOS (a terminal) boots. Check GPU, Wi-Fi and sound, and that Windows still boots.
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
     outside Chrome holds every tested send; the owner chose it (with hard security requirements, `PLAN.md` decisions
     6 to 13).
   - **Decided:** the approval surface (decision 21, after six phone tests): Claude Code's own prompt, at the laptop
     and through Remote Control on his phone, with every asking input starting with the tool service's `question`
     sentence. On 2026-11-08 (decisions 22 and 23): the central session can gain tools, those that run outside its
     sandbox only through the tool layer, asking; and one session does coding, commands, mail and Chrome together,
     possibly in skip-permissions mode, replacing the assistant/coding split, with the risk of data leaving through
     allowed developer sites accepted by him.
   - **In progress:** Mail (brief 19, PR #9: package review SAFE, frontier security review in its third round);
     design draft 23 for decisions 22 and 23 (branch `control/one-session-tools`; re-check 24 next; five owner
     choices open, each with its exact bound: `docs/design/CONTROL.md` section 10).
     `laptop-aresos` owns `os/` and the accounts and has board item #102 about installing software.
   - **Next:** brief 18c (first end-to-end test on a throwaway CI image; no owner OK needed under the 2026-11-07
     rule), then brief 20 (Chrome) on the final design draft, once a re-check finds no blocking point, both as changed
     by decisions 22 and 23 (`PLAN.md`, "Order of work"); and a new brief for the add-tool path.

Codex Pro runs until 2026-11-21.
