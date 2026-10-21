# 04: Nether home

**Goal:** one click on the title screen creates the AresOS world, and you spawn in the Nether on a small starter hub of blackstone and gold. Desktop rules are on, and you're in Live mode. Every time you open the world, you start at the hub.

**Read first:** `README.md` ("Home: the Nether", "Game rules"), and `docs/design/OS-BASE.md` §5 and B1 (the OS later launches this world with Quick Play, `--world AresHub`).

**In scope:**
1. **AresOS button** on the title screen (or in the Singleplayer screen).
   - It creates a world named "AresOS" in save folder `AresHub` if missing, otherwise loads it.
   - World settings: fixed seed (see 2), survival, cheats off, AresOS desktop marker on.
   - Difficulty: not peaceful, so placed piglin shopkeepers can exist later.
   - Gamerules: no mob spawning, no fire tick, no mob griefing, keep inventory, no insomnia/patrol/trader spawns.
2. **Seed and site, found by code.** Use the real 26.2 world generator to search seeds for a good hub site in the Nether near (0, 0):
   - **Good:** crimson forest or nether wastes, fairly flat, with a lava ocean view.
   - **Bad:** not basalt deltas or soul sand valley.
   - Write down the scoring you used.
   - Keep the **top 3** candidates with seed, coordinates and a screenshot each in `reviews/04-nether-home/seeds/`. The owner may pick another later. Default to the best.
3. **Starter hub**, built by our own code once, when the world is created. No copied vanilla structures.
   - About 15×15: a polished blackstone floor with gilded blackstone and gold accents.
   - A charged **respawn anchor** as the spawn point.
   - A small blackstone-edged **lava pool** (the future trash).
   - Open space to build.
   - Clear a safe air pocket above it, and make sure no lava can flow onto the platform.
4. **Always start at the hub.** Vanilla spawns new players in the Overworld, so move the player to the hub during join, ideally before the first frame shows the Overworld.
   - On every join of the AresOS world: at the hub, facing a nice view, in Live mode, with pinned apps.
   - Respawn goes to the anchor.

**Out of scope:** sign doors, piglin shops, portals, real installed apps, shaders, protecting blocks from breaking, and anything in `os/`.

**Acceptance:**
- `./gradlew build runClientGameTest` passes.
- Game tests:
  - World-creation flags: marker, gamerules and difficulty.
  - The hub blocks exist, the air pocket is safe, and there's no lava next to the platform except the pool.
  - The player is in the Nether at the hub after the first join and after rejoining.
- Client test: click the AresOS button → the world is created → you're in the Nether at the hub. Screenshots: arrival view and a view of the hub from above, in `reviews/04-nether-home/screenshots/`.
- Existing 01/01b/01c tests still pass. Report as usual, and stop your Gradle daemons.

**Already decided:**
- The Nether as home.
- Live mode and AresOS-world-only rules (`/aresos desktop`).
- Save folder `AresHub`.

**If unsure:** keep it simple and easy to change. A different seed later means a new world, so make the seed choice very visible in the report.

**Model:** gpt-6.1-sol, xhigh.
