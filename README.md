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
| House with a sign on the door | Walk in = open that app |
| Close the app (X) | Back in front of the house |
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

- **Spawn:** a fixed world seed (not random), picked for a good Nether spot, with a starter hub built there in blackstone and gold, bastion style. Every AresOS start puts you at the hub, like a home screen. You build the rest of the houses yourself.
- **How:** vanilla Minecraft always spawns players in the Overworld, so the mod moves you to the hub when the world loads and sets a respawn anchor there.
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
2. **Install on its own SSD.** The laptop (Lenovo LOQ 15IRH8) has a second M.2 2280 slot (PCIe 4.0). AresOS gets its own SSD there (or an external USB SSD until then). The Windows SSD is never touched. Pick the OS at startup with F12.
3. **Polish:** piglin app shops, respawn anchor = sleep, Save and Quit = shut down, more worlds via the portal (Overworld survival, BedWars).
4. **Later, optional:** a Brawl Stars theme (custom app).

## Open questions

- Minecraft version: defaulting to 26.2 (Fabric API, Sodium and Iris all available, Fabric already installed locally).
- Exact seed and hub spot in the Nether.
- Linux base: **decided, Bazzite** (needs a one-time key enrollment at install). Details in `docs/design/OS-BASE.md` once PR #2 merges.
- Buy a 2280 NVMe SSD for the second slot (confirm the slot is empty first).
- **Laptop facts (msinfo32, 2026-10-21):** UEFI mode, **Secure Boot is OFF**, and Windows device encryption is almost certainly off (it needs Secure Boot, and the Settings page "Geräteverschlüsselung" doesn't show). With Secure Boot off, AresOS needs no MOK enrollment and BitLocker prompts are unlikely. Turning Secure Boot on would be a separate owner decision.
- **Hardware to buy (owner):** Crucial P310 500 GB M.2 2280 NVMe (CT500P310SSD801) plus a UGREEN 10 Gbps NVMe USB enclosure. External test drive first, moved into the free internal slot later.
- How app items get their icons.

## Safety rules

- Mod development on Windows touches only Minecraft's mod folder and this project.
- AresOS only ever installs to its own drive (second SSD or USB SSD). Never write to the Windows SSD (Micron 512 GB).
- Before changing any BIOS/boot settings: confirm the BitLocker recovery key is saved in the Microsoft account.
