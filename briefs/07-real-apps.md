# 07: Your real apps in the inventory, with generated icons

**Goal:** in the AresOS world, the inventory holds the apps that are actually installed on the laptop. Each one is an item with **its own icon, generated automatically from the app's real icon** in a Minecraft pixel-art style. Pinned apps sit in the hotbar. Websites (for example TUM Moodle) can be apps too. The owner doesn't draw icons (owner decision).

**Read first:** `README.md` (design table, game rules) and `docs/design/OS-BASE.md` **B1** (interface v1 and the schema-2 migration of `apps.json`). Follow B1 exactly.

**In scope:**
1. **App catalogue behind one Java interface.**
   - **Windows implementation:** discover installed apps from the Start Menu folders (user and all users, `.lnk`) and Store/UWP apps (for example via the AppsFolder AUMIDs). Use stable ids; existing ids like `notepad` keep theirs.
   - **Linux side:** a stub implementation that will talk to the OS helper later (interface v1). It must never run commands directly.
2. **Websites as apps.** Entries of type `url` open in the default browser through the launcher, one launch per click as before. The owner adds them in `apps.json`.
3. **`apps.json` schema 2.** Migrate per B1: versioned backup first, atomic write, `schemaVersion`, idempotent, all ids/names/looks/pins kept, Windows argv unchanged. Discovered apps merge in **without** being auto-pinned. Duplicates or invalid entries stop with a diagnostic and never get dropped silently.
4. **Generated icons.**
   - Take each app's real icon (`.exe`/`.lnk` icon resources, UWP logo assets; for `url` entries a site icon if easy, otherwise a generic look).
   - Turn it into a Minecraft-style item texture: 16×16, palette-reduced, crisp pixels, readable at hotbar size.
   - Generate at runtime into a runtime resource pack in the game folder. **Never commit the owner's app icons or app list.**
   - Cache them and regenerate when the app's icon changes. Fall back to the configured vanilla `look` if no icon can be read.
   - Keep the converter one swappable component, so an AI-based style can be tried later.
5. **Inventory and hotbar** (AresOS worlds, Live mode only):
   - All apps appear as items. If there are more apps than inventory slots, add a simple paged "Apps" screen reachable from the inventory.
   - Dragging an app into or out of the hotbar updates `pinned` in `apps.json`.
   - Nothing changes in normal worlds.

**Out of scope:** walk-in logos (next package), the OS helper itself, AI icon styles, shops.

**Acceptance:**
- `./gradlew build runClientGameTest` passes, and all earlier tests still pass.
- Tests:
  - discovery from **fixture** Start Menu folders and fixture UWP data
  - deterministic icon conversion (golden images from fixture icons we create ourselves)
  - migration of a package-01 `apps.json` (backup made, idempotent, ids kept)
  - client test: the inventory shows the fixture apps with generated textures (screenshot), drag-to-hotbar pin persists across rejoin, and a `url` entry launches once via the fake launcher
- Screenshots use fixture apps only.
- `REPORT.md` as usual, plus a short note on how the icons look and any style judgment calls. Stop your Gradle daemons.

**If unsure:** never lose a config entry, never auto-pin, and keep normal worlds vanilla.

**Model:** gpt-6.1-sol, xhigh.
