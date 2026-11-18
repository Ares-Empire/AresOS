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
`hub/` (`Town`, `TownKeeper`, `Place`, `HubData`), `config/MyApps.java`, `names/`, `zone/LogoBuilder.java` and
`zone/LogoPixels.java`, how hotbar pins are kept (`item/`), and `src/testShared/java/dev/aresos/shell/FakeHelper.java`
with `src/test/java/dev/aresos/shell/ShellClientTest.java`.

## Build

1. **1.2 in `ShellClient`.** Ask for minor 2. When the helper offers `home_state`, the mod publishes. With a 1.0
   or 1.1 helper, or on Windows, everything behaves as today and nothing is sent.
2. **What is published** (section 5): for each of My apps, `id`, `short`, `group`, `place` (missing while it has
   none), `slot` (0–8 when pinned, missing otherwise) and `cells`, the logo as built (12 × 12, row by row from the
   top, `.` for no block). The `palette` gives each block's colour from the colours the mod already holds for its
   logos. An app without a readable picture sends its plain front, as the town builds it. Take every value from the
   same code that builds the town and the hotbar, so the laptop can never disagree with the world. Do not write a
   second logo converter.
3. **When.** After every successful hello, and after any change to My apps, a short name, a place, a hotbar slot or
   a logo. Coalesce bursts: at most one publish a second, and the latest state is always sent at the end of a
   burst. Nothing is sent while nothing changed. A publish never blocks the game thread: build the snapshot on the
   thread that owns the data, then send it as `ShellClient` sends today.
4. **Revision and parts.** `revision` is a string that rises within one game run, at most 128 characters. Split a
   town into parts of under 64 KiB each, as the contract says: `part` from 0, `last` on the final one, `palette` in
   part 0 only. A reconnect starts over at part 0 with a new revision.
5. **Bounds the mod enforces before sending**, so the helper never has to refuse a publish:
   - at most 200 apps: apps with a place first, then pinned ones, then the rest by name; log once when some are
     left out;
   - at most 64 palette keys: keep the 64 most-used colours and map each other colour to its nearest one by RGB
     distance; log once;
   - at most 16 parts;
   - `short`, `group` and `place` in the contract's shapes. A value that would not fit is left out or shortened by
     the contract's rule, never sent as an error.
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
  - 201 apps, 70 colours, a town that needs several parts, a reconnect in the middle of a multi-part publish;
  - a refused publish keeps the connection and the next change publishes again;
  - each kind of change publishes: an app added to and removed from My apps, a short name, a place moved, a pin
    moved, a logo changed.
- One client game test (`FakeHelper`, added at the **end** of the client suite per AGENTS.md): after the world
  opens, `FakeHelper` holds a complete home whose apps, places and slots match the hotbar and the town the test sees.
  Pinning an app then publishes a new revision. No screenshot is needed.
- `mod/dev/build.sh` passes. `mod/dev/client-test.sh` passes **twice**; it takes the machine's client-test lock and
  exits 75 under 6 GiB free (wait about five minutes and try again; never `--force`). **Known hang:** until PR #108
  is on main, `NetherHomeClientGameTest.testMountedRejoin` can deadlock while closing. A full suite hung in that test
  is that bug, not yours: note it and rerun. Afterwards `git checkout -- reviews/` for the screenshots the suite
  rewrites.
- `mod/README.md` says in one paragraph that the mod publishes its home to the helper and why.
- `reviews/53b-home-publish/REPORT.md` in the AGENTS.md format, with the files you changed under `shell/`, `hub/`,
  `config/`, `names/`, `zone/` and `item/`.

## Out of scope

The helper and anything under `os/` (53a is done; a contract gap is a PLAN-GAP in the report, not a helper change).
The window program (53c). Super's search (53d). Any change to how the town, the hotbar or the logos behave in the
game.
