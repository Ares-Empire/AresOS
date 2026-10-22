# AresOS: state

Updated 2026-10-21. The live truth is `git log`, `gh pr list` and `git worktree list`. Update this file when a PR merges or a decision lands.

## Done (on main)

- **Mod** (PR #1):
  - Right-clicking an app item opens a real app exactly once, and you return to the game afterwards.
  - Live mode (survival, can't die) and Build mode (creative), switched with G.
  - Desktop rules apply only in worlds marked as AresOS.
- **Real apps** (PR #6): installed apps in the inventory with generated pixel icons, websites as apps, pins kept in the hotbar.
- **Nether home** (PR #4):
  - The AresOS button opens a create screen with a seed field and a placeholder-hub toggle.
  - `/aresos home set|home|home info`, and you always arrive at home.
  - Existing worlds are never rebuilt, and saves are renamed, never deleted.
- **OS design** (PR #2): Bazzite base, council-approved. See `docs/design/OS-BASE.md`.
- **Install guide** (PR #5): same-drive dual boot, `docs/INSTALL.md` and a read-only inventory helper. Council: all 7 findings closed. **Don't start yet.** It's gated on the released AresOS image and a rehearsal on real USB sticks.
- **Decisions:**
  - Dual boot on the existing SSD (no second drive).
  - Secure Boot is off on the laptop, so no MOK step.
  - Normal Minecraft is a separate app with normal rules.
  - App icons are generated automatically from each app's real icon. The owner doesn't draw them.

## In progress

- **PR #3** (briefs 03–03c): the image builds and boots into our labwc session in a CI VM. The last checks (recovery login, power key) kept failing in the console-typing test harness, so 03c re-verifies them through robust channels.
- **Brief 08:** walk-in app logos (zones plus auto-built block logos).
- **Next for the OS image:** switch to `bazzite-nvidia-open`, publish (public or private, owner decision), and a tested "switch Bazzite to AresOS" step with an admin/recovery account. That's what unlocks the install guide.

## Waiting on the owner

- **Two USB sticks:** one becomes a Windows recovery stick (kept, never overwritten; 32 GB to be safe), one is wiped for the AresOS installer (16 GB+).
- **Image public or private on GitHub?** Public recommended (no token on the laptop, the image holds no personal data, the repo stays private). Brief 06 (switch to `bazzite-nvidia-open`, publish, tested Bazzite → AresOS switch) waits on this and on PR #3.
- Hub: the owner explores seeds, picks a spot and builds it in creative later. Nothing is locked until they say so.
- Disk space for AresOS: 96 GB proposed, not decided.

## Next, in order

1. **First boot:** install into the freed space and switch to the AresOS image. Plain AresOS (a terminal) boots. Check GPU, Wi-Fi and sound, and that Windows still boots.
2. **Walk-in app logos** (in progress): walk into a block logo and the app or site opens. Optional auto-built logos from real icons. Replaces sign doors as the main way in.
3. **Minecraft inside AresOS** (P2): Prism and Microsoft login, the Nether world, mod ↔ OS helper (interface v1), clean save and shutdown, backups.
4. **Full trial** (P3): boot → Nether hub → open/close an app → shut down → Windows still fine.
5. **Later:** piglin shops, owner-designed hub, shaders, controlled updates, boot splash, sleep, Brawl Stars theme.

Codex Pro runs until 2026-11-21.
