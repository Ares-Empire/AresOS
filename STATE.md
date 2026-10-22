# AresOS: state

Updated 2026-10-22. The live truth is `git log`, `gh pr list` and `git worktree list`. Update this file when a PR merges or a decision lands.

## Done (on main)

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
- **Install guide** (PR #9, rewritten from PR #5): AresOS on its own SSD, including fitting the drive (battery check, correct seating), clear drive identification, a whole-drive install, and a Windows-return check. Council says READY-TO-MERGE. The image/switch/rollback gate is now DONE (PR #10), but **physical install stays CLOSED** until the remaining gates in INSTALL.md's "Maintainer release gate" pass (see Next). The same-drive fallback is archived.
- **Decisions:**
  - The AresOS image is **private** on GitHub (2026-10-22: the owner doesn't mind, so the safe default). The install needs a one-time GitHub read token. Public only on an explicit "make it public".
  - **AresOS gets its own 500 GB SSD** (owner decision 2026-10-22, replaces dual boot and the 96 GB partition). Crucial P310 in the free 2280 slot, so Windows keeps all its space and is never touched. **Ordered 2026-10-22** (see below).
  - **Accounts** (owner OK 2026-10-22): the installer creates the admin `ares-recovery` first (UID 1000), and the locked daily `ares` is UID 1001. The name stays `ares-recovery` (a rename isn't worth a package).
  - **Image seal** (owner OK 2026-10-22): keyless signing. Sigstore's public log shows the repo/workflow identity and the image digest; the image stays private.
  - **Laptop pull token** (owner OK 2026-10-22): a classic, read-only `read:packages` GitHub token, created by the owner on install day.
  - **GRUB recovery** (owner OK 2026-10-22): the identity-checked "make the backup Bazzite the default" step stays marked UNTESTED until a rehearsal proves it.
  - **Emergency path:** Windows stays the boot default for the first trial, and F12 → Windows Boot Manager always works because the Micron is never written.
  - Secure Boot is off on the laptop, so no MOK step.
  - Normal Minecraft is a separate app with normal rules.
  - App icons are generated automatically from each app's real icon. The owner doesn't draw them.

## In progress

- Nothing running. Next is the "If something goes wrong" emergency card (docs only), then the remaining install gates.

## Waiting on the owner

- **Hardware ORDERED 2026-10-22** (€127.05, delivery Mon 2026-10-26): Crucial P310 500 GB, Kingston 2×64 GB sticks, Wera 2050 PH0 + PH1 screwdrivers. The owner bought the SSD before the slot check because one opening beats two. Evidence the 2280 slot is free: the Windows drive is a Micron 2450 **2242** (MTFDKCD512TFK), and a LaptopMedia teardown of this model shows the factory 2242 in the 2242-only slot with the 2280 slot (by the Wi-Fi card) empty.
  - **Return window: request within 14 days of delivery (about 2026-11-09).** Before that: make the Windows recovery stick, open the laptop once following INSTALL.md §3, and fit the SSD if the slot is free; if not, return it sealed. (Opening before the guide is released is the owner's call for the slot check.)
  - Pry the cover clips with plastic (card or pick), never metal.
- Hub: the owner explores seeds, picks a spot and builds it in creative later. Nothing is locked until they say so.

## Next, in order

1. **Close the remaining install gates** (INSTALL.md "Maintainer release gate"). In CI: the two-disk VM rehearsal (prove the Windows-like disk is never written), GRUB recovery promotion, and pinned installer media. Then the safety and followability council. Hardware items (fitting/firmware screens, helper trials) happen on the laptop with the owner.
2. **First boot:** fit the SSD, install onto it and switch to the AresOS image. Plain AresOS (a terminal) boots. Check GPU, Wi-Fi and sound, and that Windows still boots.
3. **Minecraft inside AresOS** (P2): Prism and Microsoft login, the Nether world, mod ↔ OS helper (interface v1), clean save and shutdown, backups.
4. **Full trial** (P3): boot → Nether hub → open/close an app → shut down → Windows still fine.
5. **Later:** a help button in AresOS that opens a terminal with Claude Code (owner idea 2026-10-22, after the first boot works), piglin shops, owner-designed hub, shaders, controlled updates, boot splash, sleep, Brawl Stars theme.

Codex Pro runs until 2026-11-21.
