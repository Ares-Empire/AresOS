# 08: Walk-in app logos

**Owner idea (2026-10-21):** big block logos of apps and sites in the world. You walk into one and the app opens, portal style, with no door. The owner isn't a designer, so the mod can **build the logo automatically** from the app's icon as block pixel art. Owner-built logos work too.

**Read first:** `README.md` (design table: walk-in app logos), and the existing app catalogue, generated icons, launcher, focus return and desktop marker code.

**In scope:**
1. **Walk-in zones.** A zone is a box in the world bound to one app id (program or url).
   - Entering a zone from outside in **Live mode** launches the app **exactly once**, with a short portal sound and particles.
   - Standing inside never relaunches.
   - Build mode and normal worlds never trigger.
   - On returning from the app (the existing focus-return path), teleport the player to the zone's **exit point**: just outside it, facing the logo. That prevents a re-trigger.
   - Zones persist in the world save and can't overlap (refuse with a message).
2. **Commands** (host only, works without cheats, AresOS worlds only):
   - `/aresos zone pos1`, `/aresos zone pos2`, `/aresos zone set <app id>`: mark an owner-built logo.
   - `/aresos zone list`, `/aresos zone remove <app id|here>`.
3. **Auto-built logos.** `/aresos logo <app id> [wall|floor]` builds the app's icon as block pixel art at the player's position, facing them.
   - Map each icon pixel to the closest-colored solid block from a fixed palette (concrete, wool, terracotta and similar). Commit only RGB numbers, never textures.
   - Transparent pixels place nothing.
   - Use the higher-resolution source icon where available (about 32×32), so the logo is readable.
   - **wall:** a vertical logo; its zone is the space right in front of the face, so walking up to it opens the app.
   - **floor:** a floor logo; its zone is on top, so walking onto it opens the app.
   - Creates the matching zone automatically.
   - Refuse if the area isn't clear, or would overwrite non-air blocks unless confirmed (say how). **Never silently destroy blocks.**
4. **Protection.** In Live mode, blocks of auto-built logos can't be broken. In Build mode they can.

**Out of scope:** shops, sound and visual polish beyond a simple portal effect, OS helper integration (the launch goes through the existing launcher), and doors.

**Acceptance:**
- `./gradlew build runClientGameTest` passes twice (AGENTS rule), and all earlier tests still pass.
- Tests:
  - entering a zone → one fake launch
  - staying inside → no relaunch
  - Build mode and normal worlds → no trigger
  - returning from an app → player at the exit point, no re-trigger
  - zones persist across rejoin, and overlap is refused
  - the logo builder is deterministic from a fixture icon (golden block layout), refuses to overwrite, and protection holds in Live but not in Build
  - a url zone launches once
- Screenshots of a fixture wall logo and a floor logo with their zones. Add `REPORT.md` as usual, and stop your Gradle daemons.

**If unsure:** never destroy blocks, never launch twice, and keep normal worlds vanilla.

**Model:** gpt-6.1-sol, xhigh.
