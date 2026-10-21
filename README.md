# AresOS

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

## Phases

AresOS = Linux base + the Minecraft mod as its shell. The mod is the same code on Windows and on AresOS. Only how apps get launched differs.

1. **Shell mod + OS base, in parallel.**
   - Mod: Nether hub, app items, sign doors, return-to-world on close. Developed in normal Minecraft on Windows for fast testing.
   - OS base: Linux defined as code in this repo, with NVIDIA drivers, Mojang boot logo, auto-login, and boot straight into the Nether world. Also auto-restart if Minecraft crashes, and a hidden escape key to a plain terminal.
2. **Dual boot on the existing SSD** (owner decision, 2026-10-21: free, and not very risky if done carefully).
   - The owner shrinks Windows with Windows' own tools, and AresOS goes into the freed space with its own partitions.
   - The installer touches only the new space and AresOS's own EFI partition. Windows boot files stay untouched; F12 selects the OS.
   - First test the plain AresOS terminal session on hardware, then add Minecraft. The [install guide](docs/INSTALL.md) records the checks and the image-release prerequisites before any disk changes.
   - A second SSD stays an option for later.
3. **Polish:** piglin app shops, respawn anchor = sleep, Save and Quit = shut down, more worlds via the portal (Overworld survival, BedWars).
4. **Later, optional:** a Brawl Stars theme (custom app).

## Open questions

- Minecraft version: defaulting to 26.2 (Fabric API, Sodium and Iris all available, Fabric already installed locally).
- Seed and home spot: the owner picks them later by exploring (not locked).
- Linux base: **decided, Bazzite**. Secure Boot stays off, so no MOK enrollment is needed. See [OS base design](docs/design/OS-BASE.md).
- A second SSD is optional later. Confirm the slot is empty before buying one.
- **Laptop facts (msinfo32, 2026-10-21):**
  - UEFI mode, and **Secure Boot OFF**.
  - Device encryption is very likely off, since it needs Secure Boot. A missing "Geräteverschlüsselung" page doesn't prove it, so confirm fully decrypted status before shrinking.
  - Turning Secure Boot on later is a separate owner decision.
- **Hardware:** no second SSD required. Keep **two separate labelled USB sticks**: Windows recovery (plan 32 GB, or more if its wizard requests it; never overwrite), and an expendable installer stick (at least 16 GB). Existing suitable sticks are fine. Boot-test recovery before shrinking; see the [install guide](docs/INSTALL.md).
- App icons: **decided**, generated automatically from each app's real icon on the laptop, in a Minecraft pixel-art style. The owner doesn't draw them (owner decision 2026-10-21). Test and tune later.

## Safety rules

- Mod development on Windows touches only Minecraft's mod folder and this project.
- AresOS installs only into its own new partitions in the space freed from Windows. Never delete, format or move existing Windows partitions or modify Windows boot files. The only proposed resize exceptions are the owner's C: shrink and undo-extension using Windows Disk Management, as checked in the [install guide](docs/INSTALL.md). Agents never perform them. Back up first.
- Before BIOS/boot changes, confirm encryption status and independently save the matching BitLocker recovery key if encryption exists. Unknown/encrypted status stops this install path for owner review; do not assume protection is off because Secure Boot is off.
