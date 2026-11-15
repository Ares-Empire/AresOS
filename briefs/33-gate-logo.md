# 33: The gate logo

Empire board brief 281. Mod package. `docs/design/HUB.md`, section 6, row 2.

**Builder:** a Claude agent (Fable 5.2): the logo is what the owner looks at, and turning an icon into twelve by twelve blocks that still read as the app is the delicate part. **Review:** a fresh reviewer that isn't the builder.

## Why

The owner (2026-11-13): "the logos will be built from minecraft blocks and I guess just have an opening at the front but I wouldnt make them too tall, that would look weird." Today `/aresos logo <app>` builds a flat wall of up to 32 x 32 blocks whose whole front opens the app.

**Goal:** `/aresos logo chrome` builds, in front of him and facing him, the app's icon as a block build 12 wide, 12 tall and 3 thick with a doorway at the bottom middle and its name floating above. Stepping into the doorway opens the app; walking past does nothing. Closing the app puts him a few steps in front of the door. `/aresos logo remove chrome` takes it down again without touching anything he built.

## Read first

`docs/design/HUB.md` sections 2.3, 3.1, 3.2 (the logo's geometry: niche, trigger zone, exit point, sign, light, doormat) and 3.6 (from an icon to 12 x 12 blocks), and section 5 ("Other logo forms"). Then `mod/src/main/java/dev/aresos/zone/` (all files), `mixin/LogoExplosionMixin.java`, the tests `LogoPixelsTest`, `ZoneGameTests`, `ZoneSafetyGameTests`, `WalkInLogosClientGameTest`, `WalkInFixesClientGameTest`.

## Build

1. **The picture rules of HUB.md 3.6** as pure functions with unit tests: cut, the plate test and enlarging, scaling to 12 x 12, the colour match in Oklab with lightness counted half, tidying, the door. `SIZE` (12) and `DEPTH` (3) are numbers in one place, not spread through the code: the owner is being asked whether 12 is right (board #207), and 10, 14 and 16 must work by changing that one number (the door stays 2 x 3; test all four sizes).
2. **The palette:** today's 48 blocks plus the 12 of HUB.md 2.3. Measure each new block's average colour from the game's own textures on this machine (the development setup has the game's files in Gradle's cache; a small development-only task or test may read them) and write only the numbers into the code, as was done for the 48. Re-measure the 48 the same way and say in the report where today's numbers differ. No texture enters the repo. Check that each of the 12 is a full, plain block that does not fall, burn, tick or change by itself in 26.2; drop any that isn't and record it.
3. **A plan, then the build:** from an icon, a base block, a facing and a size, compute a plan: every block with its kind, the niche, the black back of the niche and the door posts, the trigger zone (exactly the niche), the exit point (HUB.md 3.2: 5.5 blocks in front of the front face, on the doorway's centre line, looking at the door, pitch -10), the sign, the two `light` blocks, and the doormat. The plan is plain data and is what the tests check. Package 36 will call this with places it computes itself, so nothing in the plan may depend on a player.
4. **`/aresos logo <app>`** builds the gate (the new default) 6 blocks in front of him, facing him, on the ground he stands on; `/aresos logo <app> wall` and `floor` keep building today's forms exactly as today. The existing refusals stay and apply to the whole gate with its approach and exit: the space must be clear, nothing is overwritten, nothing of his is disturbed, the exit must be safe. The neighbour check must accept the mod's own palette blocks and the things this package places (the sign, the light blocks, the doormat) and still refuse plants, circuits, fluids and blocks with special behaviour.
5. **The doormat:** the two floor blocks under the niche and the two rows in front, in concrete. The floor block it replaces must be untouched ground of the kind around it; otherwise the doormat is left out and the gate is still built. Its colour is the app's group colour when the app's categories are known (HUB.md 2.2; the table lives with package 32, so keep your own copy of the four colours in one place and say so), light grey otherwise.
6. **The sign:** one text display above the logo as HUB.md 3.2 says: the app's name in white. The second line (the short name in gold) appears when the app has one; short names come with package 35, so give the plan a field for it and leave it empty.
7. **What was placed is recorded** with the zone: every block as `{pos, block}` (the block's ID as text), the sign's entity ID, and that this zone is a gate. Old zones (walls, floors, hand-made `/aresos zone`) load and work unchanged; the saved format stays readable both ways where the game's codecs allow, and a test loads a zones file written before this package.
8. **`/aresos logo remove <app | here>`** removes a gate: each recorded block only if it is still that block, the sign, the light blocks, the doormat (put the recorded ground block back only where the doormat is still the mod's block), and the zone. A block he changed stays. For old walls and floors the command does what `/aresos zone remove` does today and says that the blocks stay.
9. **Protection:** as today for logo blocks, and the sign can't be hit in Live mode.
10. **Trigger and return:** only the niche opens the app, once per entry, with today's rules (Live mode only, joining inside is not an entry, two zones at once open nothing). After the app closes he stands on the exit point looking at the door.

## Acceptance

- Unit tests for point 1 with icons the tests draw themselves (a ring, a figure on a plain plate, a non-square picture, a fully transparent one, one with a loose pixel), for all four sizes; the palette match for a list of reference colours (pure red stays red and does not turn orange).
- Server game tests: the plan's coordinates against the worked examples of HUB.md 3.2 (use them with a fixed base block and facing); build and remove leave the world exactly as it was; a block the test changes after the build survives the removal; every refusal changes no block; an old zones file loads.
- Client game tests with screenshots under `reviews/33-gate-logo/screenshots/`: three gates from made-up icons seen from 20 blocks at eye height, one from 10 blocks, one from the side and one from behind; walking past the front opens nothing; walking into the niche opens the app once (the fake launcher) and the return lands on the exit point. Look at every screenshot yourself and compare with the design's drawing `reviews/hub-design-v1/gate.png`.
- For your own eyes only, not committed: build Chrome's, Discord's and Lunar Client's gates from their real icons on this laptop (`~/.local/share/flatpak/exports/share/icons/`, `/usr/share/icons/hicolor/`, the icon named in `~/.local/share/applications/lunarclient.desktop`; read-only) in a headless run and look at the screenshots. Say in the report, in words, how recognisable each is at 12 and whether 10, 14 or 16 change your view. Real app icons never enter the repo.
- `mod/dev/build.sh` passes; `mod/dev/client-test.sh` passes **twice**.
- `mod/README.md` describes the gate and `logo remove`.
- `reviews/33-gate-logo/REPORT.md` in the AGENTS.md format, with a "try this" note for the owner.

## Out of scope

Where logos stand (package 36), the flat world and its roads (32), which apps get a logo and where icons come from on Linux (34 and 30), short names (35). No change under `os/`.

## Already decided

- Everything in HUB.md 2.3 and 3.6. Where a rule gives a plainly bad picture for one of the three real icons, keep the rule, show the picture in words, and propose the change as a PLAN-GAP; do not tune the rules to three icons.
- Wall and floor logos stay as they are.

## If unsure

Refuse to build rather than overwrite or disturb a block.

## Rules

- `AGENTS.md` applies. Worktree `~/AresOS-33-gate-logo`, branch `pkg/33-gate-logo`. Push it and open a PR against `main`. Never merge, never push to `main`, never `--no-verify`.
- Build and test with `mod/dev/build.sh` and `mod/dev/client-test.sh` only (`mod/README.md`, "On Linux"). Never pass `--force`. Never run `./gradlew` directly, except for a development-only task of your own through the same scripts' environment (`mod/dev/env.sh`), and never with a daemon.
- Packages 32 (the flat home) and 34 (My apps) are built at the same time in other worktrees. Stay inside `zone/`, its tests, the explosion mixin and the command registration for `logo`. Stay out of `world/`, `item/`, `config/`, `shell/`, `catalogue/` and the client screens.
- The repo is public: no personal data, no Mojang assets (colour numbers and block IDs are fine), no real app icons or renders of them.
- Don't touch other worktrees, `~/AresOS` itself, `~/.minecraft` or `~/.lunarclient`. No sudo.
- Commits end with `Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>`.
