# 01: First app item and Live mode

**Goal:**
- In the development copy of Minecraft, you spawn with an app item in your hotbar.
- Right-click it and a real Windows app (Notepad, for now) opens. Close Notepad and you're straight back in the game, with no pause menu in the way.
- In Live mode you can't die and never get hungry. One key switches to Build mode (creative) and back.

**In scope:**
1. **Mod project** in `mod/`. Start from the official Fabric example mod template.
   - Fabric mod for Minecraft 26.2, mod id `aresos`, Java package `dev.aresos`.
   - Java 25, Gradle wrapper, Loom 1.19.x.
   - Fabric Loader 0.19.5 (the latest stable for 26.2) and Fabric API 0.161.0+26.2 (or newer for 26.2).
2. **Apps config:** `config/aresos/apps.json` in the game folder, created with defaults on first start.
   - Each app has `id`, `name`, `command` (a list of strings, run as a new process), `look` (a vanilla item id whose look the app item borrows) and `pinned` (bool).
   - Default, one app: `{"id": "notepad", "name": "Notepad", "command": ["notepad.exe"], "look": "minecraft:writable_book", "pinned": true}`.
3. **App item:** one item type, `aresos:app`.
   - Each stack stores its app id in a custom data component.
   - It's named after the app and looks like the configured vanilla item, using the vanilla `minecraft:item_model` component. No textures of our own are needed yet.
   - Stack size 1.
4. **Launching:** using an app item launches its app **exactly once per click**.
   - It runs on the client side (the machine the player sits at), through a small `AppLauncher` interface. In singleplayer the integrated server runs in the same process, so launching from both sides would open the app twice.
   - Implement `WindowsAppLauncher` (ProcessBuilder, detached, never blocks the game) and a simple `LinuxAppLauncher` (also ProcessBuilder), picked by OS.
   - An unknown app id or a failed launch shows a short action-bar message, never a crash.
5. **Back to the game:** when the game window regains focus after AresOS launched an app, close the pause menu that vanilla opened on focus loss, so you're directly back in the world. Only do this for a pause menu opened by that focus loss, never for one the player opened with Esc.
6. **Pinned apps in the hotbar:** on joining a world, pinned apps that aren't already in the player's inventory go into the first free hotbar slots. Never overwrite an occupied slot, never duplicate.
7. **Live mode (survival, can't die):**
   - In survival the player takes no damage from any source and can't die.
   - Hunger and saturation stay full.
   - Falling below the world's bottom teleports the player to their spawn point instead.
8. **Mode key:** a key binding "Switch Build/Live mode", default `G`, in its own "AresOS" category in Controls.
   - It toggles creative ↔ survival through a client-to-server packet.
   - It works in singleplayer without cheats enabled. The server only accepts it from the singleplayer host, never from other players.
9. **Test command:** `/aresos give <app id>` gives an app item. Singleplayer only is fine.

**Out of scope (later packages):**
- Sign doors, and the Nether hub and spawn.
- Listing real installed apps, and app icons of our own.
- Separate hotbars per mode.
- Shaders/Iris, and limiting the frame rate in the background.
- Linux beyond the simple launcher.

**Acceptance:**
- `./gradlew build` passes in `mod/`.
- Game tests (`fabric-gametest-api-v1`):
  - A survival player in lava, falling or attacked takes no damage and doesn't die.
  - Hunger stays full after sprinting and jumping for a while.
  - A player below the bottom gets teleported to spawn.
  - Pinned-app placement never overwrites a slot or duplicates an item.
- Client game tests (`fabric-client-gametest-api-v1`):
  - Create a singleplayer world and check the Notepad app item is in the hotbar.
  - Use it with a **fake launcher** injected for the test, and assert it was called exactly once with Notepad's command.
  - Toggle the mode with the key and check the game mode changed both ways.
  - Save screenshots of the hotbar with the app item, and of Build and Live mode, to `reviews/01-first-app/screenshots/`.
- Tests never start real apps.
- Unit tests for reading and writing `apps.json`, including a broken file: fall back to defaults, and keep a backup of the broken file. Never silently delete the owner's config.

**Already decided:**
- The design in `README.md`.
- Notepad is the test app.
- App items borrow vanilla item looks through `item_model`.
- Launching happens on the client.

**If unsure:** pick the simplest option that's easy to change later and record it in the report. If it changes how the game feels, record it as a `JUDGMENT-CALL`.

**Note:** client game tests open a real Minecraft window on the owner's laptop. That's fine, but make sure it closes when the tests end, and never leave a game client running.

**Model:** gpt-6.1-sol, xhigh.
