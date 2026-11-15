# 32: The flat home world

Empire board brief 280. Mod package. The first of the hub packages (`docs/design/HUB.md`, section 6, row 1).

**Builder:** a Claude agent (Fable 5.2): it is the world the owner lands in every day, and world creation has cost several rounds before (packages 04 to 04d). **Review:** a fresh reviewer that isn't the builder.

## Why

The owner (2026-11-13): "Initially the plan was a nether hub but I think we start differently. I think we start with an overworld superflat world. its easier to build and design can come later." Today the AresOS button can only create the Nether home.

**Goal:** he clicks **AresOS** on the title screen and gets a flat world: he stands on a small dark pad with a gold block under his feet, it is noon and clear and stays so, nothing lives there, and four roads with coloured centre lines lead north, east, south and west, each with its group's name floating over it. Every later start puts him on the pad, facing north. The Nether home stays as a choice.

## Read first

`docs/design/HUB.md` sections 1, 2.1, 2.5 ("His own builds", "Protected in Live mode"), 2.6 (roads and group names), 3.1, 3.2 ("Fixed things" and the coordinate rules), 3.4 (first paragraph: where a town is built) and 3.5 ("With the world"). Then the code this builds on: `mod/src/main/java/dev/aresos/world/` (all four files), `mod/src/client/java/dev/aresos/client/HomeButton.java` and `HomeCreateScreen.java`, `zone/WalkInZones.java` (how logos are protected), `mixin/LogoExplosionMixin.java`, `mode/LiveMode.java`, and the tests `NetherHome*Test*`, `HomeChoiceClientGameTest`, `ProvisioningAudit`. `mod/README.md` describes the promises the Nether home makes about existing saves.

## Build

1. **The create screen** gets a choice "Home: Flat / Nether", Flat first and chosen by default. The seed field, the seed buttons and the placeholder toggle show only for Nether. Creating a Nether home behaves exactly as today.
2. **The flat world** as HUB.md 2.1 says: the layers, plains everywhere, no structures or features, seed 0, survival, normal difficulty, cheats off, through the game's own create flow as today's `HomeButton.create` does. The save folder is `AresHub`, as today.
3. **The rules, set once at creation and never again:** the ones `NetherHome.applyRules` sets, plus the day cycle off with the time at noon and the weather cycle off with clear weather. Find the real names of the two rules in 26.2 (the design guesses `advance_time` and `advance_weather`). An owner who later changes a rule keeps his change.
4. **Home:** his feet in block (0, 64, 0), looking north, pitch -8, the world spawn on the same block. Arrival on every join, respawn, `/aresos home`, `/aresos home set` and `/aresos home info` work in the flat world as they do in the Nether home. The home data keeps its format; a flat home has the Overworld as its dimension. Do not rename `NetherHome` or its saved data in this package; if a name is now misleading, say so in the report.
5. **The fixed things** of HUB.md 3.2, built once with a new flat world and only then:
   - the home pad (5 x 5 polished blackstone bricks in the floor, a gold block under him);
   - the four avenues, each from outward 3 to outward 24 (row 0 with no logos yet), 5 wide, the centre line in the group's concrete;
   - the four group names as text displays (the name only; the count comes with package 36).
6. **`data/aresos/hub.dat`** (HUB.md 3.5, "With the world"): the look (`flat-1`), the numbers of 3.1, the home block, and for the fixed things every block placed as a list of `{pos, block}` (the block's ID as text) and the IDs of the four text displays. Put the numbers and the group table (letter, outward, right, yaw, concrete, name) in one small class, as data: packages 33 and 36 read them from there. Keep the record's shape exactly this simple: package 36 will move every block change of the hub onto one shared function.
7. **Protected in Live mode:** the blocks recorded in `hub.dat` can't be broken by hand or by explosions, and the group names can't be hit, the way logos are protected today. In Build mode he can change anything, and a block he changed is his from then on (the mod never touches it again).
8. **The promises of the Nether home hold for the flat home too:** an existing save is never rebuilt, replaced or deleted; provisioning is claimed before the first block is placed and never runs twice; a save with missing or unreadable home data opens unchanged with the message; "New AresOS world…" renames the old save and asks which home to create. Opening an existing Nether `AresHub` after this package behaves exactly as before.
9. **Only in the flat home:** worlds marked with `/aresos desktop on` and the Nether home get none of the fixed things.

## Acceptance

- Unit and server game tests: the provisioning rules of point 8 for the flat home (no second build, no build in an existing save, missing data); the rules are set once and a changed rule survives a restart; the coordinates of the pad, the avenues and the group names against HUB.md 3.2; protection in Live mode and none in Build mode; a Nether home created after this package is byte-for-byte what `ProvisioningAudit` expects today.
- **No mob appears:** a server game test that runs the flat world for at least ten minutes of game time with the player at home and finds no mob (slimes are the usual pest of flat worlds).
- Client game tests with screenshots under `reviews/32-flat-home/screenshots/`: the create screen with Flat chosen and with Nether chosen; the arrival view at home (this is HUB.md's first picture: check the horizon, the pad, the north road and its name against it); the view east, south and west; from above in Build mode. Look at every one yourself.
- `mod/dev/build.sh` passes; `mod/dev/client-test.sh` passes **twice** (AGENTS.md).
- `mod/README.md` describes the flat home next to the Nether home. `README.md`'s "Home is the Nether" line says what is true after this package.
- `reviews/32-flat-home/REPORT.md` in the AGENTS.md format, with a short "try this" note for the owner (`mod/dev/run-hub.sh`, click AresOS).

## Out of scope

Logos, the doorway, signs on logos, "My apps", `/name`, `/go`, `/home` as a root command and the H key, extending the avenues, the counts on the group names. No change under `os/`.

## Already decided

- Everything in HUB.md 2.1 and 3.2. If the game cannot do something as written (a preset, a rule), take the nearest thing that gives the same picture, and record it as a JUDGMENT-CALL with what the owner would notice.
- The text displays' sizes and colours as HUB.md 3.2 says; tune them only if the screenshot shows they are wrong, and say what you changed.

## If unsure

Never touch an existing save. Leave a thing unbuilt rather than place a block where something stands.

## Rules

- `AGENTS.md` applies. Worktree `~/AresOS-32-flat-home`, branch `pkg/32-flat-home`. Push it and open a PR against `main`. Never merge, never push to `main`, never `--no-verify`.
- Build and test with `mod/dev/build.sh` and `mod/dev/client-test.sh` only (`mod/README.md`, "On Linux"): they keep the game off the owner's screen, hold the laptop's one client-test lock and refuse while his own game runs or memory is short. Never pass `--force`. Never run `./gradlew` directly.
- Packages 33 (the gate logo) and 34 (My apps) are built at the same time in other worktrees. Stay out of `zone/LogoBuilder.java`, `zone/LogoPixels.java`, `item/`, `config/`, `shell/`, `catalogue/` and `client/AppsScreen.java`. If you must touch a file outside `world/`, the new hub class, the two home screens and the protection hooks, keep the change to a few lines and name it in the report.
- The repo is public: no personal data, no Mojang assets (colours and block IDs are fine; no texture, sound or font).
- Don't touch other worktrees, `~/AresOS` itself, `~/.minecraft` or `~/.lunarclient`. No sudo.
- Commits end with `Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>`.
