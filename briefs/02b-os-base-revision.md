# 02b: Revise the OS design after the council

Follow-up on branch `pkg/02-os-base-design` (PR #2). Read `reviews/councils/2026-10-21-os-base/VERDICT.md` and the four member files first.

**Goal:** update `docs/design/OS-BASE.md` so that:
- all 7 blocking council findings are resolved in the design
- the owner's decisions below are applied
- phase 2 becomes the council's short path to a first real boot

**Owner decisions (2026-10-21):**
1. **Base: Bazzite.** Build AresOS as a custom atomic image on a Bazzite NVIDIA image (pinned by digest), defined by a Containerfile and config in this repo and built in GitHub Actions. The one-time MOK key enrollment at install is accepted. Ubuntu becomes the documented fallback if qualification on the laptop fails.
2. **"AresOS is just the operating system."** The AresOS world is the desktop: you can't die, and it doesn't need to be playable. **Playing normal Minecraft is an app launched from AresOS**: survival worlds, servers like Hypixel BedWars, possibly Lunar Client. That game is a separate game with normal rules and without desktop rules. Design how this works:
   - a separate game instance, or pausing/stopping the desktop instance while playing
   - RAM and GPU budget on 16 GB with two Minecraft instances
   - focus and input between them
   - getting back to the desktop world afterwards

**Resolve each blocking finding.** Point to the section that resolves it:
1. Backup recovery credentials kept independently of the AresOS drive.
2. Lid, power button and critical battery always go through a clean world save, including when the helper fails.
3. Shutdown checks for unsaved work in other apps (a cancellable "close your apps first" step is enough).
4. Recovery with a complete previous OS and driver set, plus recovery media, before updates are enabled. Machine settings outside `/home` (Wi-Fi etc.) get an explicit restore or reprovision policy.
5. One maintenance authority. Disable or integrate Bazzite's own automatic updaters, so nothing changes the system outside AresOS maintenance.
6. A concrete Bazzite-vs-Ubuntu comparison: session customization (our labwc session instead of Bazzite's default desktop), trust, update ownership and recovery effort.
7. **Mod ↔ OS interface v1**, versioned. Package 01 shipped `config/aresos/apps.json` with `id`, `name`, `command`, `look` and `pinned`.
   - Define which side owns what on Windows (mod launches directly) and on AresOS Linux (the mod asks the OS helper to open app `<id>`; the helper owns launch definitions, window tracking and GPU environment).
   - Keep existing app ids, and define the migration.

**Non-blocking findings 8–13:** handle each in a sentence or two, or mark it deferred with the gate that brings it back.

**Phase 2 plan:** rewrite Appendix E as the council's short path:
1. Minimal image plus a safe installer.
2. One end-to-end milestone: session, recovery terminal, network/login, Prism, launch into the world, one app via interface v1, Nether hub (a small mod dependency), clean shutdown, tested backup.
3. Early hardware trial: F12 → Nether hub on NVIDIA → open/close one app → clean shutdown → normal Windows boot, with the USB present and absent.

After that, list the later packages in order.

**Readability:** start the document with a plain-language summary for the owner: about 10 lines, no jargon, saying what AresOS will be like and what's still uncertain. The main part should still read in about 15 minutes. Details go in appendices.

**Also:** write `reviews/councils/2026-10-21-os-base/CHANGES.md`, a table mapping each of the 13 findings to where it's resolved or why it's deferred. The council chair will check only these changes.

**Out of scope:** OS code, downloads, installs, touching disks. Web research and docs only.

**Acceptance:** the doc and CHANGES.md are committed and pushed on the branch. Every new external fact has a dated source link.

**Model:** gpt-6-astra, xhigh.
