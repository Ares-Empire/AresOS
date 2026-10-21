# 04 — Nether home

Branch: `pkg/04-nether-home`. PR: https://github.com/carlsenares/AresOS/pull/4.

**Current owner decision:** seed and home are selectable. The historical seed
and enclosure choices below describe 04/04b defaults; see **04c** for the
creation screen, preserved old saves and `/aresos home set`.

**Default seed: 49. Nether floor center: (-64, 56, 32).**
Arrival: **(-63.5, 57, 37.5)**, south, yaw 0 / pitch 20.
Charged anchor: **(-68, 57, 35)**. Alternatives: **50** and **26**, with
[coordinates, scoring and screenshots](seeds/README.md).

## Done

- **Title screen:** `HomeButton` adds AresOS above Singleplayer. It reserves the
  exact `AresHub` folder and uses vanilla world creation/opening. Display name
  AresOS, fixed seed 49, normal generation, survival, cheats off, Normal
  difficulty. Existing unrecognized, malformed, or incomplete folders get an
  error and are kept intact. A `level.dat_old` is allowed through to vanilla's
  recovery flow; a folder alone does not count as a complete world.
- **Provisioning/persistence:** `NetherHome` writes a version-1
  `aresos-home.properties` only into the newly reserved directory. Server
  startup builds once, enables the existing desktop marker, saves the chosen
  site in `data/aresos/nether_home.dat`, and saves the world before the first
  join. Later starts use that saved site and never rebuild a readable existing
  hub. An unreadable existing home-data file stops provisioning instead of
  overwriting the hub. Merely running `/aresos desktop on` in another world
  neither builds a hub nor changes that world's gamerules.
- **Hub:** original code builds a 15x15 polished-blackstone floor, gilded
  blackstone border, four gold corners with lanterns, a fully charged anchor,
  and a 2x2 lava pool with polished-blackstone-brick edging. A one-block safety
  border makes the overall footprint 17x17. Blackstone foundation, corner
  pillars, glass walls and glass roof enclose nine clear blocks of headroom.
  This seals outside lava, including overhead sources. Initial terrain changes
  avoid neighbor notifications until supports/plants are replaced, preventing
  vegetation item drops littering the desktop. All blocks remain breakable.
- **Joining:** the common `PlayerList` mixin sets the Nether level and arrival
  position before vanilla captures its login dimension. A small game-mode
  invoker sets survival/abilities before a connection exists. Every home join
  resets motion/fall/fire, enters Live, pins apps, and sets a non-forced personal
  anchor respawn. The existing desktop marker gates this behavior, including
  after `/aresos desktop off`. Ordinary worlds retain the existing behavior.
- **Survey/tests/docs:** `searchNetherSeeds` uses Minecraft's actual 26.2
  generator and biome sampler for 3,136 seed/site pairs. Of 74 initial sites,
  21 pass the additional occlusion filter. The top three are validated in fully
  generated client worlds. Two new server tests cover rules and a hub built
  inside adversarial lava. The new client suite clicks the real button, checks
  first/repeated joins, save flags, blocks, anchor resolution, edits surviving
  reload, and save-collision errors. `mod/README.md` documents development,
  backups and the new entry point. No dependencies were repinned.

## Verified

Windows 11, Temurin **25.0.4.1+1-LTS**, existing Gradle **9.8.0** wrapper,
Minecraft **26.2**, Loader **0.19.5**, API **0.161.0+26.2**.

Final command, inside `mod/`:

```powershell
.\gradlew.bat searchNetherSeeds build runClientGameTest --console=plain
```

Exit **0**. Full stdout/stderr: [verification.txt](verification.txt).
Exact selected output:

```text
Eligible sites: 74
Eligible after visibility: 21
All 14 required tests passed :)
Full-generation seed 49: visible lava rays=34, noise score=209.84458247200067, final score=549.8445824720006
Full-generation seed 50: visible lava rays=24, noise score=217.05, final score=457.05
Full-generation seed 26: visible lava rays=22, noise score=230.21223591851523, final score=450.21223591851526
BUILD SUCCESSFUL in 2m 13s
19 actionable tasks: 10 executed, 9 up-to-date
```

- **Server:** 14 required tests means 11 existing AresOS tests, two new home
  tests, and Fabric's sanity test. The safety fixture starts with lava throughout
  and outside the intended enclosure and checks after 60 ticks: every floor,
  foundation, wall, ceiling, air cell, pool edge/source, anchor charge and corner
  light. The second fixture checks all seven requested gamerules. The actual
  created client world additionally verifies marker, rules, seed, survival,
  difficulty and cheats off against the real integrated server.
- **Unit:** all 13 existing unit tests actually ran and printed `PASSED` in the
  [first combined run](initial-verification.txt): seven config and six focus
  tests. XML results report zero failures/errors. Their final task was
  `UP-TO-DATE`; no test was weakened, skipped or removed.
- **Client regression:** the complete existing 01/01b/01c suite passed, including
  same-tick selection/input, normal-world behavior, marker persistence and
  disabling, Build/Live, host restrictions, commands without cheats, fake
  launches, and focus handling. Its five newly generated regression images are
  in ignored `mod/build/review/01-first-app/`; historical committed screenshots
  remain untouched.
- **Home client:** both real home joins observed Nether in the client JOIN
  callback, at the expected location/angle, in Live, with a pinned app. Before
  the second join the test deliberately left the player in the Overworld in
  creative with an empty inventory. The edited diamond floor block survived
  reopening, proving startup did not rebuild the hub. The actual anchor resolver
  returned a valid Nether respawn beside the charged anchor. The created hub
  contained no dropped items. Unrecognized, malformed and incomplete save
  fixtures all displayed the error screen and preserved the sentinel file.
- **Visual evidence:** all seven final PNGs were opened and inspected: the
  [title button](screenshots/0005_title-button.png),
  [arrival](screenshots/0006_arrival.png),
  [hub from above](screenshots/0007_hub-above.png),
  [rejoin](screenshots/0008_rejoin.png), and the three
  [seed views](seeds/README.md). The top-down image uses spectator mode inside
  the cleared pocket with a wider FOV; the arrival/rejoin images use the actual
  Live arrival position and normal FOV. The floor is clean and the book app,
  survival bars, anchor, pool, gold accents and glass enclosure render.
- **Packaging:** `jar tf mod/build/libs/aresos-0.1.0.jar` exited 0; complete list
  in [jar-contents.txt](jar-contents.txt). A Python zip inspection printed
  `Production jar: no test classes; only asset is assets/aresos/lang/en_us.json`.
  No textures, sounds, fonts, logos, fake launchers, survey or test classes are
  packaged. Only the requested in-game review screenshots contain game visuals.
  `git diff --check` and staged diff checks exited 0 with no output.

Earlier verification, including failures that led to fixes:

| Command inside mod/ | Result and evidence |
|---|---|
| `.\gradlew.bat genSources --console=plain` | Exit 0, `BUILD SUCCESSFUL in 14s`; used generated 26.2 sources to check current APIs. |
| `.\gradlew.bat searchNetherSeeds --console=plain` | Exit 0, `BUILD SUCCESSFUL in 20s`; [initial survey](seed-search-initial.txt) lacked ray occlusion and was superseded. |
| `.\gradlew.bat compileJava compileClientJava --console=plain` | Exit 0, `BUILD SUCCESSFUL in 2s`; [output](compile.txt). |
| `.\gradlew.bat build runClientGameTest --console=plain` (first) | Exit 0, `BUILD SUCCESSFUL in 1m 50s`; [output](initial-verification.txt). Visual inspection still found plant drops, an obstructed seed view, and a camera inside terrain. Fixed construction notifications, seed scoring and the above-camera position; added a no-drops assertion. |
| Same command (second) | Exit 1, `BUILD FAILED in 2s`; [compile failure](compile-failure.txt): 26.2's AABB constructor requires vectors, so used `AABB.encapsulatingFullBlocks`. |
| Same command (third) | Exit 1, `BUILD FAILED in 2m 10s`; [visibility failure](visibility-failure.txt): `Default site lacks a visible lava ocean`. Retained that assertion, added noise ray occlusion, moved arrival toward the view and replaced the shortlist. |
| `.\gradlew.bat searchNetherSeeds --console=plain` (refined) | Exit 0, `BUILD SUCCESSFUL in 17s`; [refined exploration](seed-search-refined.txt) printed ten distinct seeds during exploration. The final tool retains three; its final output is in verification.txt. |
| `.\gradlew.bat build runClientGameTest --console=plain` (fourth) | Exit 1, `BUILD FAILED in 2m 15s`; [incomplete-save failure](incomplete-save-failure.txt): the last error-screen check timed out. Vanilla `levelExists` checks only a directory, so changed production validation to require level.dat or level.dat_old. Kept the assertion. |

The final logs include the existing offline dev-session Realms/profile-key 401
messages and anisotropic-option error. The fake app-launch failure and three
`Cannot open AresOS home` errors are deliberate negative tests. They did not
prevent either client suite completing. No real app was launched by the tests.

## Not verified

- Physical mouse/keyboard play and the owner's preference for this view and
  glass shelter. The screenshots are from automated dev-client runs without
  shaders. Normal `runClient` was not separately launched for manual play.
- Prism/OS Quick Play as a real external process was not launched. The join
  hook uses saved world data and does not depend on entering through the button;
  the future OS can address the existing `AresHub` folder normally. No OS files,
  real Minecraft directory, Lunar installation or machine settings were touched.
- A physical death-screen/respawn-button flow was not forced; Live blocks death.
  The actual server anchor respawn resolver was checked. Independent package
  review remains the next workflow step.

## JUDGMENT-CALL

- **Seed 49 and a viewing-edge arrival.** Chose the broad ocean and 34/35 clear
  generated sightlines over seed 50's lower shoreline and seed 26's flatter
  ledge. The initial high-scoring crimson site was rejected after trees blocked
  its view. Arrival is five blocks toward the view rather than in the center.
  Changing to an alternative requires a new world; changing the default never
  modifies an existing save. All candidates and exact scoring are visible in
  [the seed record](seeds/README.md).
- **Glass lava enclosure.** Chose glass walls/roof with blackstone pillars and
  a foundation around the 15x15 floor. This gives a transparent, enclosed
  pavilion with a 17x17 outer footprint, and guarantees a sealed air pocket
  against hillside and ceiling lava. Rejected an open platform with only local
  lava removal because future fluid ticks could enter it. The enclosure's grid
  is visible in the arrival image; the owner should judge that feel before
  merge. Changing it is a small builder edit for new worlds; existing hubs need
  manual building changes because regeneration is intentionally disabled.
- **Explicit home identity, separate from the desktop marker.** A small
  provisioning manifest plus saved site avoids identifying homes by folder name
  or seed alone, and leaves legacy marked worlds alone. Rejected modifying the
  existing desktop-marker codec or adopting any existing AresHub directory.
  Backups need the whole world directory, including the manifest and both saved
  data files. A future format change needs a migration. Incomplete saves are
  refused; the owner must restore them or move them aside before a new creation.

## PLAN-GAP

The brief uses older gamerule terminology. In 26.2, no-fire-tick is implemented
with `fire_spread_radius_around_player = 0`; insomnia suppression uses
`spawn_phantoms = false`. The real saved rules are asserted. This is a naming/API
translation, not a scope change. No implementation blocker remains.

## Open questions

Owner review before merge: accept seed 49 and the glass enclosure, or choose one
of the retained seeds / a later shelter revision. No answer was needed mid-run;
the brief's reversible default was used. PR is open and has not been merged.

## Cleanup

`.\gradlew.bat --stop --console=plain`, inside `mod/`, exited **0** and printed
`Stopping Daemon(s)` / `1 Daemon stopped`; [output](daemon-stop.txt).
Only the wrapper's Gradle 9.8.0 was started; no other Gradle version was run.
A process query restricted to Java command lines containing this worktree path
printed **`Remaining worktree Java processes: 0`**;
[output](process-cleanup.txt). Local links in this report and the seed record
were checked and all resolved. No Gradle command was run after stopping it.

## 04b — Review fixes

### Done

- **Provisioning (`NetherHome`, `HomeButton`):** construction now requires a
  one-use permission from the button's fresh-directory creation path. At
  `SERVER_STARTING`, uninitialized level data must confirm this is a new world;
  permission then belongs to that exact server. Returning to the title screen
  cancels unused permission. Existing saves never acquire construction
  permission from their manifest or from missing home data.
- **Independent provisioning record:** `aresos-home.provisioned` is created
  with `started` before any hub changes, and updated to `complete` after saving
  the built world. Neither a missing record nor an interrupted creation permits
  automatic recovery. Existing version-1 manifests and saved-data codecs remain
  unchanged. `mod/README.md` documents backups and recovery behavior.
- **Missing home data:** an established home opens without rebuilding or
  changing its rules, difficulty, desktop marker or arrival mode. A persistent
  chat message explains that setup/arrival are disabled and asks the player to
  restore a complete backup. Older saves missing both home data and the new
  provisioning record are protected too.
- **Vehicles (`ServerPlayerHomeMixin`, mixin registration, `NetherHome`):**
  the original early login-dimension hook remains. For enabled home arrivals,
  saved vehicle restoration uses the original dimension from player data and
  vanilla's recursive entity loader/UUID checks, without attaching the player.
  Other worlds and disabled homes retain vanilla vehicle handling.
- **Client regressions:** actual mounted saves/rejoins from both dimensions,
  plus edited-home recovery with missing metadata. The hub's appearance and
  seed were not changed. Commits: regressions `9502514`, fixes `bf11c5e`.

### Verified

Inside `mod/`, the acceptance command was:

```powershell
.\gradlew.bat build runClientGameTest --console=plain
```

**Before the production fixes:** exit **1**, `BUILD FAILED in 2m 56s`.
The [complete output](04b-before-fix.txt) records all existing server/client
checks passing before all three new regressions failed:

```text
04b regression FAILED: mounted Nether rejoin
Saved minecraft:the_nether vehicle overrode hub arrival after 30 ticks: passenger=true, dimension=ResourceKey[minecraft:dimension / minecraft:the_nether], position=(128.5, 79.5875, 128.5)
04b regression FAILED: mounted Overworld rejoin
Saved minecraft:overworld vehicle overrode hub arrival after 30 ticks: passenger=true, dimension=ResourceKey[minecraft:dimension / minecraft:the_nether], position=(128.5, 79.5875, 128.5)
04b regression FAILED: missing home data
Missing home data changed existing save: [hub blocks, gamerules, disabled desktop marker, difficulty]
```

**After the fixes:** exit **0**; [complete output](04b-verification.txt).
Selected exact output, omitting log prefixes:

```text
All 14 required tests passed :)
04b regression PASSED: mounted Nether rejoin
04b regression PASSED: mounted Overworld rejoin
04b regression PASSED: missing home data
BUILD SUCCESSFUL in 2m 20s
18 actionable tasks: 5 executed, 13 up-to-date
```

- Both vehicle cases check the server and client at the hub after **30 ticks**,
  without a mount, with Nether in the initial client join callback, Live mode,
  pinned apps and the anchor respawn. The saved minecart's UUID is present at
  its original position in its original dimension, without the player. The
  Overworld UUID is absent from the Nether.
- The missing-data regression edits the floor, changes all seven home rules,
  selects Hard difficulty, disables the desktop marker and saves a creative
  player in the Overworld. After deleting `data/aresos/nether_home.dat`, it
  compares **all 3,468 block states** in the construction volume and checks
  every setting and player mode after 30 ticks. It also checks the separate
  completion record and the received warning. A second reopen removes the
  provisioning record too, with the marker enabled, and repeats the checks.
  Neither reopen nor shutdown recreates the missing home-data file.
- All existing 01/01b/01c and 04 client checks pass, including title-button
  creation, ordinary reloads, saved edits, flags, seed views, normal-world
  behavior, input, focus, host restrictions, marker persistence and modes.
  All **14 required server tests** pass. All **13 unit tests** actually reran
  and printed `PASSED` after the final production-code change in the
  [preceding run](04b-entity-wait-failure.txt); their final task was
  `UP-TO-DATE`. XML confirms zero failures, errors or skips.
- Opened and visually inspected all four new screenshots:
  [Nether mount rejoin](screenshots/04b/0012_04b-mounted-the_nether.png),
  [Overworld mount rejoin](screenshots/04b/0013_04b-mounted-overworld.png),
  [missing data, disabled marker](screenshots/04b/0014_04b-missing-home-data.png),
  [legacy/missing record, enabled marker](screenshots/04b/0015_04b-legacy-missing-home-data.png).
  The first two show the normal hub arrival; the latter two show the complete
  recovery message and retained creative mode in the Overworld. Historical
  04/seed screenshots were retained unchanged.
- Python standard-library ZIP/XML inspection (`python -`) exited **0**;
  [output](04b-packaging.txt): the production jar registers and contains the
  new mixin, contains no test classes, and has only the existing language
  asset. Unit XML reports `13 tests, 0 failures, 0 errors, 0 skipped`.
  `git diff --check` and staged diff checks exited **0** for the code. The final
  `git diff --check cc84b06...HEAD` checks this entire follow-up, including
  evidence files, and passes after normalizing trailing spaces in the thread
  dump. `git diff --check main...HEAD` additionally flags the pre-existing
  Markdown hard breaks in `REVIEW.md`, which this follow-up leaves unchanged.
  Git also printed its normal CRLF-to-LF notices.

Earlier attempts of the same acceptance command, recorded rather than counted
as passing evidence:

| Attempt | Result and correction |
|---|---|
| Initial test compilation | Exit 1, `BUILD FAILED in 8s`; [output](04b-test-compile.txt). Replaced the obsolete `ChunkPos(BlockPos)` test constructor with `ChunkPos.containing`. |
| Two early pre-fix runs | Stopped the dev-client attempts after test synchronization stalled; [selected actual output](04b-before-harness-fix.txt). Added cleanup after failed mounted assertions and moved rendering waits after the server assertions. The complete pre-fix run above then reproduced all three failures. |
| First fixed run | Exit 1, `BUILD FAILED in 1m 10s`; [output](04b-creation-lifecycle-failure.txt). Fabric defers `doWorldLoad` during client test tasks, so a permission scoped only to the creation method expired before startup. Moved consumption to `SERVER_STARTING`, added the new-level-data guard and title-screen cancellation. |
| Vehicle fixture wait | Stopped the stuck dev client; exit 1, `BUILD FAILED in 3m 57s`; [output](04b-entity-wait-failure.txt). `jcmd <dev-client PID> Thread.print` exited 0; [thread dump](04b-entity-wait-threads.txt) showed the server blocked in the test's `waitForEntities` for unloaded neighbors. Limited that wait to the one chunk the test loads. All arrival, vehicle and rendering assertions remain. |

The logs retain offline dev-session Realms/profile-key failures, the existing
anisotropic-option error, the deliberate fake-launch/save-collision errors,
and a compiler deprecation note for the vanilla vehicle-loading API. No real
app was launched. No dependency versions were changed.

### Not verified

- Physical play, shaders, striders or nested passenger trees were not manually
  exercised. The automated mounted cases use real saved minecarts in both
  dimensions; production retains vanilla's recursive vehicle loader.
- Actual power-loss/crash injection was not run. Missing metadata, including
  loss of both home data and the separate provisioning record, was exercised
  through real save shutdown/reopen cycles. An interrupted creation is never
  automatically retried.

### JUDGMENT-CALL

The brief requires leaving uncertain saves intact. Chose a permanent claim plus
an explicit new-world permission and level-data check; rejected relying on a
manifest/completion file alone, since old or partially restored saves can lose
either. A crash before completion requires restoring or moving the incomplete
save rather than retrying construction. Changing that behavior later needs an
explicit recovery workflow. No additional appearance decision was made.

### PLAN-GAP

None requiring a brief change. Legacy saves need no migration to gain the
no-rebuild protection.

### Open questions

None for 04b. The earlier seed/glass-enclosure owner decision remains outside
this follow-up's scope. PR #4 remains open; nothing was merged.

### Cleanup

`.\gradlew.bat --stop --console=plain`, inside `mod/`, exited **0** and printed
`Stopping Daemon(s)` / `1 Daemon stopped`; [output](04b-daemon-stop.txt).
Only wrapper Gradle **9.8.0** was run. The final process query printed
`Remaining worktree Java processes: 0`; [output](04b-process-cleanup.txt).
No Gradle command was run after that stop. All work stayed in this worktree
and the allowed build caches; the owner's Minecraft/Lunar folders and system
settings were untouched.

## 04c — Choose a seed and set home

### Done

- **Create/new-world UI (`HomeButton`, `HomeCreateScreen`, translations):**
  AresOS opens a small seed screen when AresHub is absent. It starts at 49,
  offers 49/50/26, accepts vanilla numeric/text/empty seed entry, and has a
  placeholder toggle. Seed changes default that toggle on for 49 and off
  otherwise; an explicit toggle then overrides it. Existing-world loading
  retains the previous validation and recovery behavior. **New AresOS world…**
  confirms, checks the save lock, and renames the whole directory to
  `AresHub-yyyy-MM-dd_HH-mm-ss-SSS` before opening creation. Name collisions
  receive a suffix; the move never requests replacement. Cancel, lock refusal,
  I/O errors and failed creation never delete a save.
- **Initial site/provisioning (`HomeSites`, `NetherHome`):** the default
  seed-49 placeholder uses the surveyed site. Other choices reuse the survey's
  flat-ground/air/lava/distance weights near the origin, then validate actual
  generated terrain. A bounded nearby search supplies a fallback. Placeholder
  off chooses natural ground and skips all construction, including the anchor.
  Only explicitly new worlds receive provisioning; the 04b permanent claim,
  new-level-data check and missing-data protections remain intact.
- **Saved home/commands (`NetherHome`, `HomeCommands`, `AresOs`, respawn
  mixin):** `/aresos home set` stores exact coordinates, dimension, yaw and
  pitch, sets the personal respawn metadata and saves immediately. It does not
  place or remove blocks. It requires solid support, a clear standing body,
  and no fluid/fire intersecting feet or head. `/aresos home` dismounts and
  teleports while retaining the current mode; `info` prints seed, coordinates,
  dimension and facing. All three require an enabled desktop and its
  singleplayer host, without cheats. A manually marked ordinary desktop can
  also set a home; missing metadata in a provisioned AresHub is refused.
  An optional `home` record extends the old saved-site codec. Old homes retain
  their anchor behavior until a new home is selected. Selected and natural
  homes use the exact saved location for both login and respawn, without beds,
  anchors or coordinate rounding. Every join still enters Live.
- **Tests/docs:** added a server safety fixture and a third client suite.
  Test-only mixins audit block writes during placeholder-off provisioning;
  none are packaged. Existing tests gain only the required create-screen
  click. Both READMEs explain selection, dated saves and the home commands.

### Verified

On Windows 11, existing Java **25.0.4.1**, wrapper Gradle **9.8.0**, Minecraft
**26.2**, Loader **0.19.5**, API **0.161.0+26.2**, ran inside `mod/`:

```powershell
.\gradlew.bat build runClientGameTest --console=plain
```

Exit **0**. Full stdout/stderr: [final acceptance run](04c-verification-fifth.txt).
Exact selected output:

```text
All 15 required tests passed :)
04c typed seed and placeholder OFF PASSED: seed=-812345678901234567, natural site=Site[seed=-812345678901234567, x=-16, y=48, z=-32, yaw=180.0], ZERO block writes during provisioning
04c selected home PASSED: Nether and Overworld exact position/facing persisted through rejoin; actual respawn in both dimensions
04c non-49 placeholder ON PASSED: seed=50, site=Site[seed=50, x=-32, y=38, z=0, yaw=-90.0]
BUILD SUCCESSFUL in 2m 51s
18 actionable tasks: 5 executed, 13 up-to-date
```

- **Server/unit:** all original 14 server tests plus the new safety fixture
  passed. The 13 original JUnit tests actually ran and printed `PASSED` in the
  [first run](04c-verification-first.txt); their final task was `UP-TO-DATE`.
  XML results have zero failures, errors or skips.
- **01–04b regression:** the complete original client suite passed, including
  the actual default hub, anchor resolver, edited blocks surviving reopen,
  mounted Nether and Overworld rejoins, and both missing-home-data cases with
  block/rule/difficulty/marker preservation. No old assertion was removed.
- **Create/terrain:** typed a 64-bit negative seed through Fabric's keyboard
  input into the real screen, created it, and checked the actual server seed.
  Quick picks and both toggle states were checked. Test-only injection observed
  **zero calls to Level.setBlock during placeholder-off initialization**, across
  all dimensions. Natural arrival was safe in generated terrain. Independent
  reference-world loading produced differing warped vegetation/tree decoration
  (logged), so that comparison is diagnostic rather than construction evidence.
  Seed 50 with the placeholder enabled produced a fully checked sealed hub and
  safe player arrival near the origin.
- **Commands/rejoin/respawn:** real client command packets worked with cheats
  off. Both Nether and Overworld homes preserved **(20.25, 180, 20.75)**, yaw
  **137**, pitch **-18**, through save/rejoin, with the selected dimension in
  the login callback and Live on arrival. Vanilla's actual respawn operation
  replaced the player and sent respawn/teleport packets to the exact home in
  both dimensions. `home` retained Build mode; `info` contained the seed,
  position and dimension. Snapshots around `home set` stayed identical.
  Unsupported, lava/fire at feet or head, and obstructed positions were refused
  without changing home or blocks. Guest, disabled-desktop and normal-world
  commands were refused. A manually marked desktop could set a home without
  blocks being changed.
- **Save preservation:** both confirmations were exercised through real UI
  buttons. Cancel kept AresHub intact; a held save lock displayed an error and
  kept all data intact. Successful dated renames retained SHA-256 hashes of
  **all 59 files** in the first save and **all 55 files** in the second save,
  including world, player and AresOS metadata. Both dated saves remain in the
  isolated test saves folder.
- **Screenshots:** opened and visually inspected all three final PNGs:
  [49 / default hub on](screenshots/04c/0016_04c-create-default.png),
  [typed seed / hub off](screenshots/04c/0017_04c-create-typed-no-hub.png), and
  [50 / explicit hub on](screenshots/04c/0018_04c-create-seed-50-hub.png).
  Text and buttons fit without overlap or clipping. Historical 04/04b images
  were restored after the regression run; these new 04c images are retained.
- **Packaging/review files:** the production jar contains no test or audit
  classes and its only asset remains `assets/aresos/lang/en_us.json`.
  Unit XML, jar contents and report-link checks are recorded in
  [artifact checks](04c-artifact-checks.txt). `git diff --check` and staged
  checks exited 0 with no output. No dependencies or third-party assets were
  added. Offline dev-profile/Realms errors, the existing anisotropic-option
  message, fake-launch errors and deliberate save/lock-refusal logs remain in
  the full output; they did not prevent the passing run.

Earlier commands inside `mod/`, retained as evidence rather than passing
acceptance results:

| Command | Actual result / correction |
|---|---|
| `.\gradlew.bat compileJava compileClientJava --console=plain` | Exit 0, `BUILD SUCCESSFUL in 8s`; [output](04c-compile.txt). |
| `.\gradlew.bat compileGametestJava --console=plain` | Exit 0, `BUILD SUCCESSFUL in 3s`; [output](04c-test-compile.txt). |
| `.\gradlew.bat build runClientGameTest --console=plain`, first | Exit 1, `BUILD FAILED in 2m 31s`; [output](04c-verification-first.txt). All 14 existing server tests, 13 unit tests and all 01–04b client checks passed. The new comparison of two independently ticking generated worlds differed. Replaced that new test's indirect construction check with an audit requiring **zero Level block-write calls during provisioning**, and retained the independent terrain comparison as a diagnostic. |
| Same acceptance command, second | Exit 1, `BUILD FAILED in 15s`; [output](04c-verification-second.txt). The new safety fixture tried to test unsupported head-height fire that had already removed itself. Added support and a check that the hazard really exists. |
| Same acceptance command, third | Exit 1, `BUILD FAILED in 14s`; [output](04c-verification-third.txt). That fixture's netherrack side support was not flammable; changed it to oak planks. Soul fire receives soul-soil support. Kept every safety assertion. |
| Same acceptance command, fourth | Exit 1, `BUILD FAILED in 2m 25s`; [output](04c-verification-fourth.txt). All 15 server tests and all old client checks passed. The new locked-save test correctly reached the error screen, but Windows prevented the test from reading locked `session.lock` bytes for its hash check. Moved the full hash comparison immediately after releasing the test lock; it still checks every file. |

### Not verified

- Physical keyboard/mouse exploration, shaders and the owner's eventual seed,
  home and hub preferences. Automated screenshots use the isolated dev client.
- Power-loss/crash injection and filesystem/device failures were not simulated.
  The archive test covers cancellation, an actual held save lock, and complete
  save-file hashes after a successful rename.
- The physical death-screen button was not clicked: Live prevents death.
  The tests exercise vanilla's actual player replacement and respawn packets,
  including a cross-dimension respawn, rather than only inspecting metadata.

### JUDGMENT-CALL

- **Reversible seed defaults:** seed edits reset the toggle to on for 49 and
  off otherwise. Rejected carrying an old seed's on-default silently onto an
  unsurveyed seed; the owner can explicitly turn it on. Changing this later is
  a small UI change and cannot affect existing saves.
- **Exact home respawn without a block:** selected homes override bed/anchor
  resolution while the desktop is enabled, retaining fractional coordinates
  and facing. Rejected adding/moving an anchor or relying on vanilla's rounded
  forced spawn, which would edit blocks or lose the requested location.
  Existing anchor homes retain the old behavior. Future changes need to keep
  the optional saved-home record readable; no block migration is needed.
- **Conservative safety:** a full supporting top face and a clear standing
  body are required; fluids, fire and magma support are refused. Partial
  supports or crouch-only gaps are not accepted as homes. This is a reversible
  predicate change if the owner wants more permissive building surfaces later.

### PLAN-GAP

The brief does not define text/empty seed behavior or what to do if a seed has
no safe nearby natural spot. Used vanilla seed semantics and a bounded search
within 128 blocks on each horizontal axis. If that search fails, creation
keeps the save and refuses automatic construction/recovery; it never carves a
spot. No dependency versions were changed. The root README's older statement
that every home creates an anchor was updated to match the no-block command.

### Open questions

None blocking 04c. Seed and final hub location intentionally remain the owner's
later choice. PR #4 is still open and must not be merged by this run.

### Cleanup

`.\gradlew.bat --stop --console=plain`, inside `mod/`, exited **0** and printed
`Stopping Daemon(s)` / `1 Daemon stopped`; [output](04c-daemon-stop.txt).
Only the wrapper's Gradle **9.8.0** was started. A Java-process query restricted
to this worktree printed **`Remaining worktree Java processes: 0`**;
[output](04c-process-cleanup.txt). No Gradle command was run after that stop.
Work stayed in this worktree and the permitted Java/Gradle caches. The owner's
Minecraft folder, Lunar Client, other worktrees and machine settings were not
touched. No save was deleted. The branch is pushed to existing PR #4; no merge
was performed.

## 04d — Deterministic arrival-site search

### Done / cause

- **Confirmed cause:** the noise-column ranking was stable, but the generated
  decoration used to accept or reject its first candidate depended on generation
  order. The old safety check loaded a candidate chunk to `FULL`; it did not
  establish a stable generation order for the complete search footprint. A
  `FULL` request can schedule neighboring feature work together, and 26.2's
  `FEATURES` step can write into adjacent chunks. Raw noise columns do not
  include those features.
- **Concrete reproduction:** with seed **-812345678901234567**, a cold search
  found `warped_wart_block` at head height above floor **(-16, 48, -32)** and
  rejected it for **(-80, 57, -96)**. A separate, freshly created world with the
  search area preloaded had `air` at that head cell and chose **(-16, 48, -32)**.
  The [diagnostic run](04d-old-code-trace.txt) records `blockClear=false` versus
  `true`, with `entityClear=true` in both cases, then fails the fresh-world
  equality assertion. The HashMap was only a lookup cache, never the iteration
  source; hash iteration and player/entity collisions were not the cause.
- **`HomeSites`:** synchronously completes `FEATURES` in ascending x/z order
  over a **23x23 chunk** region, including a one-chunk halo. It then requests
  `FULL` for all **21x21 chunks** containing the score samples (-160..160).
  Every score now reads generated block states, including surface, structures
  and vegetation, with the original flat/air/lava/distance weights. Explicit
  x/z/y tie breakers retain the previous loop order. The fallback and its
  safety predicate remain intact, with their complete footprint already loaded.
  No ticking delay or retry decides the winner, and no blocks are carved or
  placed by the search.
- **`HomeSitesClientGameTest` / test entry point:** three seeds, **three distinct
  fresh save directories per seed**, repeated searches, and one save/rejoin per
  seed. Cases cover first search at server startup, first search with terrain
  preloaded, and first search after login. Each world additionally loads the
  entire area, repeats the search, visits the selected Nether spot, waits
  **40 client ticks**, and requires the same safe result. A non-loading
  `getChunkNow` check requires the search itself to complete all sampled chunks.
- **Existing `HomeChoiceClientGameTest`:** retains the original equality
  assertion and adds both sites to its failure message. No old assertion or
  test was removed, skipped or loosened. The old-code trace logging was temporary
  observation only and is absent from the accepted production source.

### Verified

Windows 11, existing Temurin **25.0.4.1**, wrapper Gradle **9.8.0**, Minecraft
**26.2**, Loader **0.19.5**, API **0.161.0+26.2**. No versions were repinned.

The following **five consecutive full runs** passed, with no source edits or
other Gradle invocations between them. The loop stopped on any nonzero exit.
All commands ran inside `mod/`. Saved logs normalize line endings and trailing
whitespace only:

```powershell
# Run 1 also forces the unchanged unit tests to execute again.
.\gradlew.bat build runClientGameTest --console=plain --rerun-tasks
# Runs 2, 3, 4 and 5:
.\gradlew.bat build runClientGameTest --console=plain
```

| Run | Exit | Exact Gradle result | Complete stdout/stderr |
|---|---|---|---|
| 1 | **0** | `BUILD SUCCESSFUL in 5m 30s` | [04d-run-1.txt](04d-run-1.txt) |
| 2 | **0** | `BUILD SUCCESSFUL in 5m 27s` | [04d-run-2.txt](04d-run-2.txt) |
| 3 | **0** | `BUILD SUCCESSFUL in 5m 26s` | [04d-run-3.txt](04d-run-3.txt) |
| 4 | **0** | `BUILD SUCCESSFUL in 5m 23s` | [04d-run-4.txt](04d-run-4.txt) |
| 5 | **0** | `BUILD SUCCESSFUL in 5m 25s` | [04d-run-5.txt](04d-run-5.txt) |

Each run printed:

```text
All 15 required tests passed :)
04d deterministic site search PASSED: 3 seeds, 3 fresh worlds each, repeated searches and rejoin per seed
```

- All **45 fresh worlds and 15 rejoins across five separate client processes**
  returned exactly the same site for each seed; a post-run log parser asserted
  this across all five logs, beyond the in-process assertions. Selected floors:

  | Seed | Floor x/y/z | Yaw |
  |---|---|---|
  | -812345678901234567 | -80 / 57 / -96 | -90 |
  | 50 | -32 / 38 / 0 | -90 |
  | 26 | 32 / 44 / 16 | 0 |

- All 15 server tests ran on every full run. All four client suites completed
  each time, including the retained independent-world/actual-provisioning
  equality check, natural-arrival safety, zero construction writes with the
  placeholder off, seed-50 hub, exact homes/respawns, save hashes and prior
  01–04b regression coverage. Run 1 printed all **13 JUnit tests PASSED**; XML
  reports 13 tests, zero failures/errors/skips. Unchanged unit tasks were
  `UP-TO-DATE` in runs 2–5.
- `python .work/check-04d.py` exited **0**;
  [artifact checks](04d-artifact-checks.txt) record log counts, cross-process
  equality, matching before/after [source hashes](04d-source-hashes.txt), JUnit
  XML, and no test/audit classes in the production jar. Its only asset remains
  `assets/aresos/lang/en_us.json`. `git diff --check` and staged checks exited
  **0**. No third-party assets or dependencies were added.
- This is a terrain-selection change with numerical/safety assertions, so no
  new visual feature or 04d screenshot was added. Existing client suites still
  generated their normal review images; historical tracked PNGs were restored
  after the runs to keep this delta scoped. No new visual inspection is claimed.

Old-code proof and exploratory commands, all the same full command
`.\gradlew.bat build runClientGameTest --console=plain` inside `mod/`:

| Evidence | Exit / exact result | What it demonstrated |
|---|---|---|
| [Initial old-code run](04d-old-code.txt) | **1**, `BUILD FAILED in 4m 49s` | Reproduced the integration failure: `Site search was not deterministic`. Basic cold-only repetitions had passed, demonstrating why that test was insufficient. |
| [Old-code load-state run](04d-old-code-load-states.txt) | **1**, `BUILD FAILED in 4m 58s` | The retained integration assertion logged reference floor (-16, 48, -32) versus provisioned floor (-80, 57, -96). |
| [Old-code diagnostic run](04d-old-code-trace.txt) | **1**, `BUILD FAILED in 1m 8s` | The new multiworld test itself failed on cold versus preloaded fresh worlds. Observation-only logging identified warped wart at head height versus air; both had no entity collision. |
| [Final test on original source](04d-old-code-final-test.txt) | **1**, `BUILD FAILED in 37s` | Replaced only `HomeSites.java` with its `64879bd` version, leaving the final strengthened tests in place. It failed immediately: `Search scored an incomplete area at -10, -10`. Restored the fix before the five runs. |
| [Exploratory fix run](04d-fix-check.txt) | **0**, `BUILD SUCCESSFUL in 5m 27s` | Passed the multiworld/load/tick/rejoin cases and all old regressions before adding the final distinct-directory and non-loading completeness checks. Not counted among the five acceptance runs. |

The diagnostic cold/preloaded reproduction predates the additional completeness
assertion; that assertion further strengthens the same test rather than
replacing its equality/safety checks. To replay on the old implementation,
restore only `mod/src/main/java/dev/aresos/world/HomeSites.java` from `64879bd`
in a disposable checkout, keep the new tests, and run the full command above.
The final test fails deterministically without requiring a lucky timing window.

The full logs retain the existing offline dev-profile/Realms errors, anisotropic
option message, fake-launch errors, and deliberately refused invalid/locked
saves. They did not prevent the five passing runs. No real app was launched.

### Not verified

- Physical play, shaders or the owner's preference for the newly selected
  natural view. The tests use the isolated Gradle dev client.
- Exhaustive testing of every possible seed or terrain changed later by a
  player. Automated coverage includes the reported failing seed and seeds 50
  and 26, fully generated terrain, actual arrival ticks and rejoining.

### JUDGMENT-CALL

Within the brief's explicit **deterministic and safe beats fast** instruction,
chose complete ordered generation over the old noise-first shortlist. This
creates more terrain during first creation and can select a different initial
spot for new non-49 worlds. Rejected accepting timing-dependent decoration or
loosening equality. Existing saved homes are still read without rerunning the
search. Changing this later is local to the search; no saved-data migration is
introduced.

### PLAN-GAP

None blocking. No changes outside the deterministic-search follow-up were made.

### Open questions

None for 04d. PR #4 remains open; this run does not merge it.

### Cleanup

`.\gradlew.bat --stop --console=plain`, inside `mod/`, exited **0** and
printed `Stopping Daemon(s)` / `1 Daemon stopped`;
[output](04d-daemon-stop.txt). Only wrapper Gradle **9.8.0** was run.
The process query printed **`Remaining worktree Java processes: 0`**;
[output](04d-process-cleanup.txt). No Gradle command was run after that stop.

Implementation commit: **`2f48d7e`**. The implementation and this report/evidence
are pushed to `pkg/04-nether-home` for existing PR #4; no merge was performed.
Work stayed in this worktree and permitted build caches. Other worktrees,
the owner's Minecraft/Lunar folders and system settings were not touched.
