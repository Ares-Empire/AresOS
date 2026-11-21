# 53b: the mod publishes its home (`publish_home`)

Board #335, brief 306, step 2 of `docs/design/LAPTOP-HOME.md` section 9. Mod package. The lead's handoff for the whole
build is `briefs/53-laptop-home-build.md`.

**Builder:** Codex `gpt-6.2-sol` `xhigh`: a data feed against a fixed contract and example files, which Sol builds well.
**Review:** a fresh Codex `gpt-6.2-astra` `high`, read-only.

## Why

The laptop home draws the owner's town from what the mod tells the helper, so both screens show the same town and
the laptop never parses `apps.json` or converts a logo itself (section 5, "Why the mod publishes"). 53a (PR #112,
on main) gave the helper `publish_home`. This step makes the mod send it: once after each hello, and again whenever
the town changes. Nothing in the game looks different.

## Read first

`docs/design/LAPTOP-HOME.md` section 5 (`publish_home` and its bounds, written by 53a; this is the contract) and the
example messages under `mod/src/test/resources/shell-1.2/` with their `README.md`. `docs/design/HUB.md` 3.8 (1.1)
and the parts on places, short names and logos. Then `mod/src/main/java/dev/aresos/shell/ShellClient.java`,
`hub/` (`Town`, `TownKeeper`, `Place`, `HubData`), `config/MyApps.java`, `names/` (`NameRules`), `zone/GatePicture`
and `zone/GatePalette`, `item/AppInventory.java` and `mode/ModeInventories.java`, `AresOs.java` (when the helper
starts), and `src/testShared/java/dev/aresos/shell/FakeHelper.java`
with `src/test/java/dev/aresos/shell/ShellClientTest.java`.

## Build

1. **1.2 in `ShellClient`.** Ask for minor 2. When the helper offers `home_state`, the mod publishes. With a 1.0
   or 1.1 helper, or on Windows, everything behaves as today and nothing is sent.
2. **What is published** (section 5): for each of My apps, `id`, `short`, `group`, `place` (missing while it has
   none), `slot` (0–8 when pinned, missing otherwise) and `cells`. Take every value from the same code that builds
   the town and the hotbar, so the laptop can never disagree with the world. Do not write a second logo converter.
   - **`cells`** is the front as the town builds it: for a standing logo, the front and place `HubData` recorded;
     for one not built yet, the town's `GatePicture` or its plain-front fallback. Doorway holes are `.`.
     `GatePicture` counts rows from the ground, so row `r` from the top is `at(x, 11 - r)`. (`zone/LogoBuilder` and
     `LogoPixels` draw walls and floors; they are not the source.)
   - **`palette`**: one key per block colour the cells use, with the RGB from `GatePalette.BLOCKS`.
   - **`slot`**: the host's ordered **Live** hotbar, slots 0–8 (`AppInventory.hotbar()` is a set and cannot give
     it). While Build mode is active, keep publishing the Live order as it was saved (`ModeInventories`). Two pinned
     apps swapping slots is a change.
   - **`group`**: the town's resolved group for the app.
   - **Rows that cannot be sent:** an app without a short name yet (`NameRules.mainName()` can be empty) waits and
     is published once it has one; an app whose ID does not fit the contract is skipped and logged once, never
     altered; a place that does not fit the contract's shape is left out (the app is sent without `place`). One
     bad row never invalidates the publish.
3. **When.** After every successful hello **once the host's home is ready**, and after any change to My apps, a
   short name, a place, a hotbar slot or a logo. The mod starts the helper before a world or host exists
   (`AresOs.java`), and the town reads its pictures after the host arrives: a hello before that queues the publish
   until the home is ready. **Never publish an empty or partial town** in its place, because it would replace the
   helper's last complete home. Hook the town's real outcomes in `TownKeeper` (a logo built, moved or taken down; a
   pending replacement finished), not its chat lines: since package 54 a pending replacement is one record that ends
   as one line, and a fresh home's first build waits up to 200 ticks. Coalesce bursts: at most one publish a second, and the latest state is always sent at the end of a
   burst. Nothing is sent while nothing changed. A publish never blocks the game thread: build the snapshot on the
   thread that owns the data, then send it as `ShellClient` sends today.
4. **Revision and parts.** `revision` is a string that rises within one game run, at most 128 characters. Split a
   town into parts of under 64 KiB each, as the contract says: `part` from 0, `last` on the final one, `palette` in
   part 0 only. A reconnect starts over at part 0 with a new revision.
5. **Bounds the mod enforces before sending**, so the helper never has to refuse a publish:
   - at most 200 apps: apps with a place first, then pinned ones, then the rest by name; log once when some are
     left out;
   - at most 62 palette keys (`[A-Za-z0-9]`; `.` is no block): keep the 62 most-used colours and map each other
     colour to its nearest one by RGB distance; log once (today's palette has 60 colours);
   - at most 16 parts;
   - every row in the contract's shapes, by the row rules in point 2; each serialized message, newline included,
     under 64 KiB.
6. **A refused publish** (`invalid_state`, `malformed`) is logged with its reason. It never disconnects the mod
   from the helper or changes the game. The next change publishes again.
7. **The test helper.** `FakeHelper` speaks 1.2: it offers `home_state`, accepts and records `publish_home` with the
   same validation as the real helper (the contract's bounds), and can be set to refuse.

## Acceptance

- Unit tests (`ShellClientTest` or a new `HomePublishTest`):
  - the mod's publish for a fixed town equals the example files `publish-home-request.json` and the two-part pair
    in shape; every message the mod sends passes `FakeHelper`'s validation;
  - a 1.1 helper gets no publish; minor 2 is asked for;
  - a burst of ten changes gives at most two publishes and ends with the latest state;
  - 201 apps, 70 synthetic colours, a town that needs several parts, a reconnect in the middle of a multi-part
    publish, a town change after part 0 (the helper gets consecutive parts of one revision, then the latest);
  - an asymmetric front with doorway holes and a colour only gates use, compared cell by cell with the town;
  - hello before the world opens publishes nothing until the home is ready; a reconnect after that publishes at once;
  - two pinned apps swapped in the inventory publish their new slots; Build mode keeps the Live order;
  - an app without a short name yet, an over-long ID and a malformed place, each beside good rows;
  - a refused publish keeps the connection and the next change publishes again;
  - each kind of change publishes: an app added to and removed from My apps, a short name, a place moved, a pin
    moved, a logo changed.
- One client game test (`FakeHelper`, added at the **end** of the client suite per AGENTS.md): after the world
  opens, `FakeHelper` holds a complete home whose apps, places and slots match the hotbar and the town the test sees.
  Pinning an app then publishes a new revision. No screenshot is needed.
- `mod/dev/build.sh` passes. `mod/dev/client-test.sh` passes **twice**; it takes the machine's client-test lock and
  exits 75 under 6 GiB free (wait about five minutes and try again; never `--force`). Package 54's test mixin (on
  main) fixes the old `testMountedRejoin` hang. **Screenshots:** commit your own work before a suite run; afterwards
  restore only the tracked screenshot files the suite rewrote (`git status --porcelain -- 'reviews/*/screenshots/*'`),
  never a blanket `git checkout -- reviews/`.
- `mod/README.md` says in one paragraph that the mod publishes its home to the helper and why.
- `reviews/53b-home-publish/REPORT.md` in the AGENTS.md format, with the files you changed under `shell/`, `hub/`,
  `config/`, `names/`, `zone/` and `item/`.

## Out of scope

The helper and anything under `os/` (53a is done; a contract gap is a PLAN-GAP in the report, not a helper change).
The window program (53c). Super's search (53d). Any change to how the town, the hotbar or the logos behave in the
game.
