# AresOS: state

Updated 2026-10-21. The live truth is `git log`, `gh pr list` and `git worktree list`. Update this file when a PR merges or a decision lands.

## Done (on main)

- **Mod** (PR #1):
  - Right-clicking an app item opens a real app exactly once, and you return to the game afterwards.
  - Live mode (survival, can't die) and Build mode (creative), switched with G.
  - Desktop rules apply only in worlds marked as AresOS.
- **Build/Live inventories** (PR #8): each mode keeps its own inventory and hotbar, and G swaps them atomically, so the app hotbar comes back exactly as left. Safe against `/gamemode`, stale input, lost acknowledgements and pickups during a switch.
- **Walk-in app logos** (PR #7): walk into a block logo and the app or site opens once, then you return in front of it. `/aresos logo <app> wall|floor` auto-builds logos, and `/aresos zone ...` marks owner-built ones. The builder never destroys or obstructs blocks.
- **Real apps** (PR #6): installed apps in the inventory with generated pixel icons, websites as apps, pins kept in the hotbar.
- **Nether home** (PR #4):
  - The AresOS button opens a create screen with a seed field and a placeholder-hub toggle.
  - `/aresos home set|home|home info`, and you always arrive at home.
  - Existing worlds are never rebuilt, and saves are renamed, never deleted.
- **OS design** (PR #2): Bazzite base, council-approved. See `docs/design/OS-BASE.md`.
- **Install guide** (PR #5): same-drive dual boot (now the fallback; brief 10 rewrites it for the own-SSD install), `docs/INSTALL.md` and a read-only inventory helper. Council: all 7 findings closed. **Don't start yet.** It's gated on the released AresOS image and a rehearsal on real USB sticks.
- **Decisions:**
  - The AresOS image is **private** on GitHub (2026-10-22: the owner doesn't mind, so the safe default). The install needs a one-time GitHub read token. Public only on an explicit "make it public".
  - **AresOS gets its own 500 GB SSD** (owner decision 2026-10-22, replaces dual boot and the 96 GB partition). Crucial P310 in the free 2280 slot, so Windows keeps all its space and is never touched. The SSD and two USB sticks are in the owner's Amazon cart (€117.98).
  - Secure Boot is off on the laptop, so no MOK step.
  - Normal Minecraft is a separate app with normal rules.
  - App icons are generated automatically from each app's real icon. The owner doesn't draw them.

## In progress

- **PR #3** (briefs 03–03f): the image boots in a CI VM, all checks green including the logind power-key proof. 03f fixes the review findings (contingency scope, updater activation audit, pinned toolchain).
- **Brief 10:** install guide rewritten for AresOS on its own SSD, including how to fit the drive. A council review follows.
- **Next for the OS image:** switch to `bazzite-nvidia-open`, publish **privately** (brief 06), and a tested "switch Bazzite to AresOS" step with an admin/recovery account. That's what unlocks the install guide.

## Waiting on the owner

- **Checkout:** the SSD plus 2 USB sticks are in the Amazon cart (€117.98). The owner checks out, or confirms the total with Claude.
- Hub: the owner explores seeds, picks a spot and builds it in creative later. Nothing is locked until they say so.

## Next, in order

1. **First boot:** fit the SSD, install onto it and switch to the AresOS image. Plain AresOS (a terminal) boots. Check GPU, Wi-Fi and sound, and that Windows still boots.
2. **Minecraft inside AresOS** (P2): Prism and Microsoft login, the Nether world, mod ↔ OS helper (interface v1), clean save and shutdown, backups.
3. **Full trial** (P3): boot → Nether hub → open/close an app → shut down → Windows still fine.
4. **Later:** piglin shops, owner-designed hub, shaders, controlled updates, boot splash, sleep, Brawl Stars theme.

Codex Pro runs until 2026-11-21.
