# Nether home seed survey

**Default: seed 49**, hub floor center **(-64, 56, 32)** in Nether wastes.
Arrival is **(-63.5, 57, 37.5)**, facing south (yaw 0, pitch 20).
The charged anchor is at **(-68, 57, 35)**. All coordinates are Nether coordinates.

| Rank | Seed | Floor center (x, y, z) | Direction | Flat / 25 | Air / 200 | Ocean / 35 | Clear rays, noise / generated | Final score | Screenshot |
|---|---:|---|---|---:|---:|---:|---:|---:|---|
| 1, default | 49 | -64, 56, 32 | South, yaw 0 | 17 | 200 | 33 | 34 / 34 | 549.845 | [Lava ocean](0009_01-seed-49.png) |
| 2 | 50 | -32, 38, 0 | East, yaw -90 | 18 | 197 | 33 | 33 / 24 | 457.050 | [Lower shoreline, crimson trees nearby](0010_02-seed-50.png) |
| 3 | 26 | 64, 43, 96 | South, yaw 0 | 24 | 199 | 32 | 24 / 22 | 450.212 | [Flatter ledge with lava falls](0011_03-seed-26.png) |

All three center biomes are Nether wastes in the fully generated 26.2 world.
Seed 49 has the broadest unobstructed ocean. Seed 26 has the flattest sampled
ledge. Seed 50 sits closer to lava level and has crimson vegetation nearby.
Screenshots show the original generated terrain before building a hub; the
actual default hub is shown in [arrival](../screenshots/0006_arrival.png) and
[above](../screenshots/0007_hub-above.png).

## Reproduce and scoring

Inside `mod/`, run:

```powershell
.\gradlew.bat searchNetherSeeds
.\gradlew.bat runClientGameTest
```

`NetherSeedSearch` bootstraps Minecraft 26.2's vanilla registries and normal
world preset. It uses the real Nether `ChunkGenerator.getBaseColumn`, seeded
`RandomState`, and biome source, rather than a third-party seed approximation.
It searches seeds **0 through 63**, with x/z **-96 through 96 at 32-block
intervals**: 3,136 seed/site pairs.

1. Require crimson forest or Nether wastes at the center; reject every other
   biome. Pick the first floor y from 34 through 65 with solid ground and air at
   y+1 and y+6.
2. Sample a 5x5 grid across offsets -6 through 6, step 3. `flat` counts solid
   floor/air-above pairs; `air` counts air at heights 1 through 8 on those 25
   columns. Require flat >= 15 and air >= 160.
3. For each cardinal direction, sample exposed lava at y=31, with air at y=32
   and at viewing height y+2, at distances 16 through 64, step 8, and across
   offsets -16 through 16, step 8. Keep the direction with most ocean samples;
   require at least 10. The base score is:

   `4 * flat + 0.25 * air + 3 * ocean - 0.1 * hypot(x, z)`.

4. Refine those sites with 35 rays from the intended arrival eye position,
   five blocks toward the view from the center, to the same ocean grid. Sample
   the actual noise columns every half block and reject a ray when it hits
   solid terrain. Require at least five clear rays, then add `10 * clearRays`.
   Sort descending and keep the best site for each of three distinct seeds.
5. The client suite creates three normal, fully generated worlds using those
   seeds, checks the actual biome, and uses Minecraft's block raycast on the
   same 35 rays. This includes generated trees/terrain/features. Replace the
   noise ray bonus with the generated ray bonus and verify the default still
   wins. Save a screenshot at each intended arrival position.

The ray grid in step 4 includes exposed lava samples even when they were not
counted by step 3's separate viewing-height filter, so its count can exceed
`ocean`. Step 5 measures the natural view before hub construction; glass and
the platform rim affect the built view, which is separately photographed.
The final run's exact survey and client outputs are in
[verification.txt](../verification.txt).
Generated-world counts are observations of an active world, whose lava and
vegetation can update: seed 50 measured 26 rays in the preceding run and 24 in
the final run. The deterministic noise ranking and winning seed stayed the same.

The first survey lacked ray occlusion and shortlisted seeds 56, 26 and 58.
Screenshots exposed tree/ledge obstruction, so that incomplete scoring was
replaced. Those rejected sites are not the retained alternatives.

## Choosing an alternative later

`NetherHome.DEFAULT_SITE` is the one production default. Change it to a row
above, update the corresponding client-test default/expectation, then create a
**new** AresHub save after backing up/moving the existing save. Changing a
constant does not move, regenerate, or overwrite an existing hub: its seed/site
are saved with the world. Never change an existing world's seed to try to
convert it into another candidate.
