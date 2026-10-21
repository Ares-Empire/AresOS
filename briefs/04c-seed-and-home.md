# 04c: Choose the seed, set home yourself

Follow-up on branch `pkg/04-nether-home` (PR #4), on top of 04b.

**Owner decision (2026-10-21):** seed and home spot are **not locked**. The owner wants to explore seeds and pick a spot themselves later, then build the hub there. Seed 49 and the glass hub are only defaults.

**Goal:** the owner can try different seeds, fly around in Build mode, pick a spot, and make it home, without code changes and without ever losing a world.

**In scope:**
1. **Create screen.** When no AresOS world (`AresHub`) exists, the AresOS button opens a small create screen:
   - A **seed** field, prefilled with 49, plus quick-pick buttons for the three surveyed candidates (49, 50, 26).
   - A **placeholder hub** on/off toggle. It defaults to on for seed 49, whose site was surveyed.
   - For any other seed, find a safe arrival spot near (0, 0) with the existing site scoring: solid ground, not in lava, an air pocket. Build the placeholder there only if the toggle is on.
2. **A new AresOS world while one exists.** "New AresOS world…" (with confirmation) **renames** the existing `AresHub` save to `AresHub-<date-time>` and then opens the create screen. **Never delete a save.** Loading an existing world works as before.
3. **`/aresos home set`.** Makes the player's current position, dimension and facing the home: arrival on every join and the respawn point.
   - It places and removes **no blocks**.
   - Host only, works without cheats, AresOS worlds only.
   - Refuse with a message if there's no solid block below or the spot is unsafe (lava or fire at feet or head).
4. **`/aresos home`** teleports you home. **`/aresos home info`** prints the seed, home position and dimension.

**Out of scope:** the hub's look, structure saving (later, once the owner has built), and everything else.

**Acceptance:**
- `./gradlew build runClientGameTest` passes. All 01–04b tests still pass, including "never rebuild an existing hub".
- Tests:
  - Creating with a typed seed gives that seed.
  - Placeholder off → no blocks placed.
  - Placeholder on with a non-49 seed → a safe arrival spot.
  - `home set` then rejoin → arrival at the new spot. Respawn goes there too.
  - `home set` refuses unsafe spots.
  - "New AresOS world" keeps the old save under its new name with its data intact.
- Screenshots of the create screen. Add a "04c" section to `REPORT.md`, and stop your Gradle daemons.

**If unsure:** never destroy or overwrite a world or blocks, and keep it simple.

**Model:** gpt-6.1-sol, xhigh.
