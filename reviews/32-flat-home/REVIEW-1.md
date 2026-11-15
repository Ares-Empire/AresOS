Reviewed `28646baa` against `aeba9fb2`, excluding `mod/dev`. I read the requested documents, implementation, tests, and all nine screenshots. I did not run Gradle or the game.

1. **Blocking — Damaged flat-home data can silently send the player to the Nether.**  
   [NetherHome.java:92](/var/home/ares/AresOS-32-flat-home/mod/src/main/java/dev/aresos/world/NetherHome.java:92), particularly the optional `home` field, `get()`, and the fallback at line 105.

   A flat save whose site fields survive but whose nested `home` field is missing still decodes successfully. Its home then becomes the legacy Nether arrival: approximately `(0.5, 64, -4.5)`, with an anchor that was never built. A malformed nested field can produce the same result: Minecraft’s saved-data reader accepts partial codec results, and the optional-field codec supplies an empty optional on failure.

   Consequently, startup sees home data, suppresses the missing-data warning, and arrival changes the player’s dimension and respawn configuration. This violates the damaged-save promise. The new “unreadable” server test passes `hasHomeData=false` manually; it never exercises this decoding path.

   **Fix:** Require a valid exact home for a save identified as flat, while preserving the legacy fallback for old Nether saves. Reject partial home decodes and use the existing warning/no-arrival behavior without rewriting the file. Add actual save-opening regressions for missing and malformed nested home data.

2. **Should-fix — Ownership returns to the mod after the owner replaces a block with the original material.**  
   [HubData.java:85](/var/home/ares/AresOS-32-flat-home/mod/src/main/java/dev/aresos/hub/HubData.java:85).

   `holds()` checks only position and current block ID. Break the gold block in Build mode, place your own gold block there, then return to Live: your block becomes protected again. The same applies after a different replacement is changed back. The record never relinquishes ownership.

   This contradicts “a block he changed is his from then on.” It also gives package 36 an unsafe ownership record for future removal/rebuilding. The tests replace paving with diamond, so they miss this case.

   **Fix:** Persistently remove ownership when an owned block is actually changed. Keep the simple `{pos, block}` format by removing the entry. Test same-material replacement, intervening replacements, and restart persistence.

3. **Should-fix — A creative LAN guest disables the owner’s explosion protection everywhere.**  
   [HubData.java:99](/var/home/ares/AresOS-32-flat-home/mod/src/main/java/dev/aresos/hub/HubData.java:99).

   `protectsFromExplosions()` scans every player on the server, including players in other dimensions. Thus the owner can be in Live mode while a creative guest causes TNT to destroy the pad and roads. Hand protection still applies, making the behavior inconsistent.

   **Fix:** Base this decision on the singleplayer owner’s mode, with protection retained when the owner cannot be identified. Test the policy separately and exercise the real host in a client test. Server-test convenience should not determine production semantics.

4. **Should-fix — Group names remain uneditable in Build mode.**  
   [FlatHub.java:72](/var/home/ares/AresOS-32-flat-home/mod/src/main/java/dev/aresos/hub/FlatHub.java:72).

   The implementation relies on text displays being unhittable in both modes. There is no supplied Build-mode interaction for removing or editing them; normal entity-management commands require cheats, which this world disables. The protection test explicitly expects a name to survive a Build-mode explosion.

   This leaves the brief’s “he can change anything” and acceptance’s “none in Build mode” unfulfilled for group names. HUB.md’s “cannot be hit at all” needs to be reconciled with that requirement.

   **Fix:** Provide a host-only Build-mode editing/removal mechanism while retaining Live protection, and test it. If names are intended to be an exception, record that as an explicit design exception rather than claiming complete Build freedom.

5. **Should-fix — The ten-minute test does not prove that no mob appears in the flat home.**  
   [FlatHomeGameTests.java:334](/var/home/ares/AresOS-32-flat-home/mod/src/gametest/java/dev/aresos/test/FlatHomeGameTests.java:334), especially lines 388–400.

   During the quiet interval, the test makes no mob assertions until the final tick. A mob can spawn and then die, despawn, or leave the observation area without failing it.

   It also runs in vanilla’s default flat test world, at that world’s surface, without creating this package’s home, setting noon/clear weather, or building its fixed things. The positive control is useful, but it does not satisfy the requested ten-minute test of the actual flat world. Additionally, it changes `SPAWN_MONSTERS` without restoring its previous value.

   **Fix:** Run against the production flat preset and initialized home for at least 12,000 ticks. Monitor mob additions throughout, or assert continuously with suitable tracking, and restore every modified rule. Retain the positive control.

Outside those findings, the main creation and save guards look sound on inspection:

- Existing saves cannot acquire new-creation permission through the normal open flow. The exclusive provisioning claim precedes block placement; a crash does not authorize another provisioning run. Rules, difficulty, noon, and weather are set only during initialization.
- The layers, plains biome, empty structure selection, disabled features, seed, home coordinates, facing, spawn, pad, roads, and recorded coordinates match the brief.
- Normal flat arrival, respawn, and home commands use dimension-aware paths. Moving the home does not move the town.
- The create screen defaults to Flat and hides Nether controls. The archive flow retains its rename-without-replacement behavior.
- The two edited Nether client tests retain their existing assertions. Their additional clicks deliberately select Nether after the default changed; the added assertions check that no flat hub record appears. `ProvisioningAudit` still wraps the same Nether initializer.

For spawning specifically, I inspected the local 26.2 bytecode: the flat generator’s initial-mob-generation method does nothing, and Nether-portal piglin spawning checks the mob-spawning rules. I found no spontaneous spawning route in the untouched flat Overworld that defeats these defaults. This is not a universal mob ban: spawner blocks use the separate, still-enabled `SPAWNER_BLOCKS_WORK` rule, and deliberate entity placement remains possible. That distinction matters because the design expressly allows future companions.

My assessment of every report decision:

| Report item | Assessment |
|---|---|
| JUDGMENT-CALL 1: explosions follow Live/Build | Agree for the new fixed blocks; preserving existing logo behavior keeps this package scoped. |
| JUDGMENT-CALL 2: any creative player | Disagree; finding 3. |
| JUDGMENT-CALL 3: ownership by comparison | Disagree; finding 2. This weakens an explicit ownership promise. |
| JUDGMENT-CALL 4: manifest key, version 1 | Agree with the encoding choice, but flat-specific home validation is missing; finding 1. |
| JUDGMENT-CALL 5: grass with air above | Agree within the guarded, new-world-only provisioning path. It is not a general proof that arbitrary grass is untouched. |
| JUDGMENT-CALL 6: one toggle button | Agree. |
| JUDGMENT-CALL 7: darker plates/lighter text | Agree; the screenshots support the readability adjustment. |
| PLAN-GAP 1: conflicting explosion requirements | The wording merits clarification, but “Protected in Live mode” and the acceptance already support the chosen block behavior. They do not justify unrestricted guest influence. |
| PLAN-GAP 2: misleading Nether names | Agree; retaining the names was explicitly required. |
| PLAN-GAP 3: clock API | Agree with the implementation; this is an API detail, not a design shortfall. |
| PLAN-GAP 4: retained test worlds | Agree that fixtures need isolation; random placement should still be validated before use. |
| PLAN-GAP 5: deferred entity visibility | Agree with addressing the timing cause without weakening assertions. |
| PLAN-GAP 6: server tests lack a host | Agree with using client tests for host behavior; disagree with using that limitation to justify JUDGMENT-CALL 2. |

CHANGES-NEEDED