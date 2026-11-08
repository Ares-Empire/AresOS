# AresOS: design

This is the design record, moved from the README on 2026-11-08. The README is now the front page for visitors.

A personal "operating system" where the desktop is a game. You boot, you spawn, and your apps live in the world.

First theme: **Minecraft** (real Minecraft Java + our own Fabric mod). Possible later theme: **Brawl Stars** (custom-built, since it can't be modded).

## How it works

- **The world is real Minecraft.** We don't rebuild the game. We write a Fabric mod that turns the game into an app launcher.
- **The mod starts real programs.** Minecraft is a Java program, and Java can start any other program on the computer.
- **Apps open on top of the game.** Closing one drops you back into the world where you were standing.
- **Underneath (phase 2) is Linux.** It has no normal desktop and boots straight into a Minecraft world, the same way SteamOS is Linux with Steam on top. The base is **Bazzite**, a gaming-focused Fedora with NVIDIA built in (owner decision, 2026-10-21). AresOS is a custom image built from this repo, and a bad update can be rolled back at startup.
- **AresOS is just the operating system.** Only the AresOS world follows desktop rules. Playing normal Minecraft (survival, Hypixel BedWars, maybe Lunar Client) is an app you open from AresOS, and it plays completely normally.

## Minecraft design

| In the game | In the OS |
|---|---|
| Boot logo | Mojang logo, then straight into the world |
| Hotbar (1–9, right-click) | Pinned apps |
| Inventory (E) | All other apps (the normal survival inventory, with extra pages if needed); drag into the hotbar to pin |
| **Walk-in app logos** (owner idea, 2026-10-21) | Big block logos of apps or sites. Walk into one and it opens like a portal. Optional auto-build of a logo from the app's real icon as block pixel art. A sign door is an optional alternative. |
| Close the app (X) | Back in front of the logo, facing it (no re-trigger). Zones are off in Build mode. |
| Villagers | App shops; each job is a category (librarian = notes/reading, cartographer = maps), trading = installing |
| Bed | Sleep mode |
| Esc → Save and Quit | Shut down |
| World select screen | Pick your desktop: **Survival** world or **BedWars** world |

Real survival play is not part of the desktop world. It's normal Minecraft opened as an app (see "How it works").

BedWars world extras:
- Islands = app groups (uni, work, gaming)
- Item shop villager = app store
- Upgrades villager = settings
- Generators drop finished downloads as items
- Throwing a file into the void deletes it

## Home: the Nether

Ares, god of war, lives in the Nether. Phase 1 is built here.

- **Spawn:** every AresOS start puts you at your home spot, like a home screen.
  - **Seed and spot are not locked yet** (owner decision 2026-10-21). The owner explores seeds and picks a spot later, then sets it with `/aresos home set`.
  - Until then, seed 49 and a placeholder glass hub are the default.
  - The owner builds the hub and houses themselves.
- **How:** vanilla Minecraft starts players in the Overworld, so the mod moves you to the saved home when the world loads and uses it for respawn. The default placeholder has an anchor; `/aresos home set` saves a new spot without placing or removing blocks.
- **Sleep:** beds explode in the Nether, so sleep mode is the respawn anchor.
- **Shops:** there are no villagers in the Nether. Piglins are the shopkeepers (they already trade for gold in the real game).
- **Trash:** lava. Throw a file in to delete it.
- **Nether portal:** the door to other worlds (Overworld survival desktop, BedWars) later.
- **Safety:** handled by Live mode and world settings (see Game rules).

## Game rules

These rules apply **only in the AresOS world** (a marker stored in the world save). Every other world plays like normal Minecraft.

The mod decides the rules. There are two modes:
- **Build mode (creative):** for building the hub and houses. Flying, unlimited blocks.
- **Live mode (survival, the everyday mode):** the normal survival look, but you can't die. The mod blocks all damage and death, and hunger never drains.
- One key switches between them. Your app hotbar comes back when you return to Live mode.

The survival bars can show system info (idea): hearts = battery, hunger = RAM use, XP bar = disk space.

World settings:
- No random mob spawning. Shopkeeper piglins are placed on purpose.
- Fire doesn't spread, and mobs can't break blocks.
- Bonus: crimson and warped wood can't burn.
- App doors and signs are protected from accidental breaking.

## Shaders

- AresOS runs on Fabric, not Lunar Client, because our mod can't run inside Lunar.
- The user's shader pack (Complementary Reimagined r5.9.3, in `.minecraft\shaderpacks`) works on Fabric via **Iris + Sodium**. Both exist for 26.2.
- While an app is open, the mod throttles Minecraft to a low frame rate, since the game keeps running behind it.
- On battery, shaders turn off automatically (Iris has a toggle API) and come back when plugged in.

Textures come from the user's own Minecraft install (nothing copied into this repo). The old 1.8.9 look is available through the built-in "Programmer Art" resource pack.

## Desktop and companion (owner ideas, 2026-10-24)

To try and tune once AresOS runs on the laptop. Not frozen; real use decides what changes.

- **Windows are free.** Two apps side by side, a small window, or fullscreen. Not always fullscreen.
- **Behind a small window: the companion's home.** A still picture, not the live Minecraft world. When an app goes small, the companion walks into its home. When the app goes fullscreen again, it comes back out.
- **Minecraft doesn't draw behind apps.** It stays open but paused while an app is open, so the hub comes back instantly. Measure its memory cost on the laptop.
- **The wheel.** Hold a key, and open apps appear in a circle around the mouse. Flick to one to switch. A **"+"** spot is always there and opens a nice app menu, sorted by favourites.
- **Home key.** One key always goes back to the hub. Apps stay open.
- **Rooms** (saved app arrangements, e.g. a browser left and a writer right). Good idea, but the Minecraft design for them is still open.
- **Search** like macOS Spotlight is needed. Its design is open.
- **The companion.** A small, "alive" character on the desktop:
  - It perches on things (like a browser's address bar) and walks between spots with animations.
  - It has idle gimmicks (sunglasses, a chair) and a thinking animation.
  - It moves to wherever it's working.
  - A hotkey opens a small chat bar. It sees the screen when asked, and can do things, with a confirmation before anything that can't be undone.
  - In the hub it's a creature that walks around and can be chatted with. Give it a task and it walks into the app's logo, the app opens, and the desktop companion takes over inside the app.
  - It starts automatically, can be switched off, and we build it ourselves, animations included, so other companions are easy to add.
  - The owner's companion is Claude's crab. Its art and anything personal live in a separate private add-on, never in this repo.
- **AI-native extras (ideas):**
  - a help command that starts Claude Code with the system's details already loaded, which also works from the recovery login
  - AI piglin shopkeepers that find and install apps
  - "build me an app", which adds a new logo to the hub
- **Open:**
  - The window system. labwc doesn't tell other programs where windows are, but the companion, the wheel and rooms need that. KDE's KWin (already in Bazzite) is the main alternative.
  - Keeping the repo publishable: no personal data, and no Anthropic art.

## Phases

AresOS = Linux base + the Minecraft mod as its shell. The mod is the same code on Windows and on AresOS. Only how apps get launched differs.

1. **Shell mod + OS base, in parallel.**
   - Mod: Nether hub, app items, sign doors, return-to-world on close. Developed in normal Minecraft on Windows for fast testing.
   - OS base: Linux defined as code in this repo, with NVIDIA drivers, Mojang boot logo, auto-login, and boot straight into the Nether world. Also auto-restart if Minecraft crashes, and a hidden escape key to a plain terminal.
2. **AresOS on its own SSD** (owner decision, 2026-10-22; replaces same-drive dual boot).
   - A second internal NVMe SSD (Crucial P310 500 GB) goes into the free M.2 2280 slot, and AresOS takes that whole drive.
   - Windows keeps all its space and is never touched. Pick the OS at startup.
   - Same-drive dual boot stays documented as a fallback.
3. **Polish:** piglin app shops, respawn anchor = sleep, Save and Quit = shut down, more worlds via the portal (Overworld survival, BedWars).
4. **Later, optional:** a Brawl Stars theme (custom app).

## Open questions

- Minecraft version: defaulting to 26.2 (Fabric API, Sodium and Iris all available, Fabric already installed locally).
- Seed and home spot: the owner picks them later by exploring (not locked).
- Linux base: **decided, Bazzite**. Secure Boot stays off, so no MOK enrollment is needed. See [OS base design](OS-BASE.md).
- The ordered second SSD is the primary install target. Confirm the 2280 slot and fitting parts before installation; the [install guide](../INSTALL.md) remains gated.
- **Laptop facts (msinfo32, 2026-10-21):**
  - UEFI mode, and **Secure Boot OFF**.
  - Device encryption was believed off. A missing "Geräteverschlüsselung" page or Secure Boot off does not prove it; confirm fully decrypted status before hardware/firmware changes.
  - Turning Secure Boot on later is a separate owner decision.
- **Hardware (ordered 2026-10-22):** Crucial P310 500 GB NVMe SSD for the free 2280 slot, plus a Kingston Exodia M 2×64 GB USB pack (one Windows recovery stick that's kept, one installer stick).
- App icons: **decided**, generated automatically from each app's real icon on the laptop, in a Minecraft pixel-art style. The owner doesn't draw them (owner decision 2026-10-21). Test and tune later.

## Safety rules

- Mod development on Windows touches only Minecraft's mod folder and this project.
- AresOS installs only onto its own SSD. Never partition, format, resize or write to the Windows SSD, and never modify Windows boot files. Back up first anyway.
- Before BIOS/boot changes, confirm encryption status and independently save the matching BitLocker recovery key if encryption exists. Unknown/encrypted status stops this install path for owner review; do not assume protection is off because Secure Boot is off.
