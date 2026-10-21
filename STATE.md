# AresOS: state

Updated 2026-10-21. The live truth is `git log`, `gh pr list` and `git worktree list`. Update this file when a PR merges or a decision lands.

## Done (on main)

- **Mod** (PR #1):
  - Right-clicking an app item opens a real app exactly once, and you return to the game afterwards.
  - Live mode (survival, can't die) and Build mode (creative), switched with G.
  - Desktop rules apply only in worlds marked as AresOS.
- **OS design** (PR #2): Bazzite base, council-approved. See `docs/design/OS-BASE.md`.
- **Decisions:**
  - Dual boot on the existing SSD (no second drive).
  - Secure Boot is off on the laptop, so no MOK step.
  - Normal Minecraft is a separate app with normal rules.
  - App icons are generated automatically from each app's real icon. The owner doesn't draw them.

## In progress

- **PR #3** (brief 03): the AresOS image builds and boots in a CI VM.
- **PR #4** (briefs 04, 04b): Nether home. AresOS button, seed 49, starter hub, always spawn there. Fixing review findings.
- **Brief 05:** dual-boot plan and the owner install guide (`docs/INSTALL.md`).

## Waiting on the owner

- A USB stick of at least 16 GB for the installer.
- How the image reaches the laptop: public image or local build. Recommendation comes with 03/05.
- Hub build: the owner designs it in creative later. The glass box is a placeholder, and we save the build as a structure.

## Next, in order

1. **First boot:** install into the freed space and switch to the AresOS image. Plain AresOS (a terminal) boots. Check GPU, Wi-Fi and sound, and that Windows still boots.
2. **Real apps in the mod:** scan installed apps, generate item icons, all apps in the inventory.
3. **Minecraft inside AresOS** (P2): Prism and Microsoft login, the Nether world, mod ↔ OS helper (interface v1), clean save and shutdown, backups.
4. **Full trial** (P3): boot → Nether hub → open/close an app → shut down → Windows still fine.
5. **Later:** sign doors, piglin shops, owner-designed hub, shaders, controlled updates, boot splash, sleep, Brawl Stars theme.

Codex Pro runs until 2026-11-21.
