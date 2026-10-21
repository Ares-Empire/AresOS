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
- **PR #4** (briefs 04, 04b, then 04c): Nether home. AresOS button, always spawn at home, placeholder hub. Fixing review findings. Next comes 04c: choose the seed at creation and `/aresos home set`, because seed and spot aren't locked.
- **PR #5** (briefs 05, 05b): dual-boot plan and `docs/INSTALL.md`. The council found 7 gaps (4 blocking), being fixed now.

## Waiting on the owner

- **Two USB sticks:** one becomes a Windows recovery stick (kept, never overwritten; 32 GB to be safe), one is wiped for the AresOS installer (16 GB+).
- How the image reaches the laptop: public image or local build. Recommendation comes with 03/05.
- Hub: the owner explores seeds, picks a spot and builds it in creative later. Nothing is locked until they say so.
- Disk space for AresOS: 96 GB proposed, not decided.

## Next, in order

1. **First boot:** install into the freed space and switch to the AresOS image. Plain AresOS (a terminal) boots. Check GPU, Wi-Fi and sound, and that Windows still boots.
2. **Real apps in the mod:** scan installed apps, generate item icons, all apps in the inventory.
3. **Minecraft inside AresOS** (P2): Prism and Microsoft login, the Nether world, mod ↔ OS helper (interface v1), clean save and shutdown, backups.
4. **Full trial** (P3): boot → Nether hub → open/close an app → shut down → Windows still fine.
5. **Later:** sign doors, piglin shops, owner-designed hub, shaders, controlled updates, boot splash, sleep, Brawl Stars theme.

Codex Pro runs until 2026-11-21.
