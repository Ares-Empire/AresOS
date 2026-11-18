# 53b home publication

## Done

- `mod/src/main/java/dev/aresos/shell/` negotiates 1.2 and publishes to helpers offering `home_state`. It checks the app, palette, part and UTF-8 byte limits before sending. The writer waits for each acknowledgement, coalesces updates, and starts a fresh revision on reconnect. A refusal logs the helper's reason and leaves the connection usable.
- `mod/src/main/java/dev/aresos/hub/` captures the integrated host's town after a whole pass and the picture reads. It takes standing places and fronts from `HubData`, uses the town's picture for unbuilt apps, and notices successful replacements and recorded front edits independently of chat.
- `mod/src/main/java/dev/aresos/item/AppInventory.java` reads slot numbers. `mode/ModeInventories.java` supplies the saved Live slots while Build is active and waits through an in-progress mode switch. The publisher uses the existing `config/` My apps list, `names/NameRules` short names, and `zone/` gate pictures and palette.
- `mod/src/testShared/` validates incoming parts in the socket fake. The unit tests cover the contract examples and limits, legacy negotiation, startup and reconnect, burst coalescing, refusal, and front and slot data. The final client test drives the same paths in an integrated home. `mod/README.md` describes what the helper receives.

### Review fix 1

- `HomePublishClientGameTest` moves a pre-existing `AresHub` to a unique sibling of the save before cleaning `a53b`. It restores the original when the test ends and recovers backups left by interrupted runs, including the old `a53b/previous-home`. If `AresHub` is occupied during recovery, the test keeps that save under its own unique recovery name. If it finds several backups, setup stops and reports their paths. Regression tests cover an initial move failure, a failing test body, and both backup locations.
- `TownHome` defers publication while every My apps entry is waiting for a saved short name. The capture test checks that a saved name produces a row and an empty My apps produces `apps: []`.
- `ShellClient` logs the helper's `message` on a `publish_home` refusal. The socket fake uses that field, and the refusal tests check the warning text and a successful follow-up on the same connection.

## Verified

- `mod/dev/build.sh --dry-run` printed `BUILD SUCCESSFUL in 8s` with all tasks listed as skipped for the dry run.
- `mod/dev/build.sh compileTestJava` initially printed `All 106 required tests passed :)` and failed on three new unit-test cases. The multipart example fixture's tie order was corrected, and the refusal test was set to report a focused launch so it could verify the same connection.
- `mod/dev/build.sh` printed `BUILD SUCCESSFUL in 3m 45s` and `All 106 required tests passed :)`. JUnit reported 300 tests, with 294 passes and the six expected Windows-specific skips.
- `mod/dev/client-test.sh build`, first run, printed `BUILD SUCCESSFUL in 15m 4s`, `All 106 required tests passed :)`, and exit code 0. The headless client used the NVIDIA RTX 4060 and printed `53b home publish checks passed: wait for host, standing places, pin, swap, saved Live slots, name, move, add, remove and front edit`.
- `mod/dev/client-test.sh build`, second run, printed `BUILD SUCCESSFUL in 15m 2s`, `All 106 required tests passed :)`, and exit code 0. The new client test passed again on the same GPU. Both combined runs reran the client and server game tests and reported the unit-test task as up to date.
- Restored only the tracked screenshots the runs rewrote, 58 for the first run and 56 for the second. Archived 25 new screenshots from each run in its own ignored `.work/` folder, including the seed screenshots. The publication test verifies the town and hotbar directly.
- `git diff --check origin/main...HEAD` passed. `find .work -type f -size +500M -print` returned no files.

### Review fix 1

- `mod/dev/build.sh` printed `BUILD SUCCESSFUL in 3m 6s` and `All 106 required tests passed :)`. JUnit reported 305 tests, with 299 passes and six expected Windows-specific skips.
- The first `mod/dev/client-test.sh build` run printed `BUILD SUCCESSFUL in 14m 30s`, `All 106 required tests passed :)`, and exit code 0. The headless RTX 4060 client printed `53b home publish checks passed: wait for host, standing places, pin, swap, saved Live slots, name, move, add, remove and front edit`.
- The second `mod/dev/client-test.sh build` run printed `BUILD SUCCESSFUL in 14m 34s`, `All 106 required tests passed :)`, the same home publication checks on the RTX 4060, and exit code 0. Both combined runs reported the unit-test task as up to date.
- Restored only the tracked screenshots each run rewrote, 60 for the first and 59 for the second. Archived 25 new PNGs from each run in its own ignored `.work/` folder. `git diff --check` and `git diff --check origin/main...HEAD` passed. `find .work -type f -size +500M -print` returned no files.

## Known limits

- A reinstall with identical published fields can leave the laptop house missing until another change triggers publication.
- A standing logo's recorded place and resolved group can disagree while a category change waits for the logo to move.
- After a refusal, a burst of changes that returns to the refused snapshot can leave the helper showing its last accepted town.

## Not verified

The installed helper and laptop-home window still need the live two-screen trial with the owner's town.

## JUDGMENT-CALL

- A fresh home waits for a whole town pass and its picture reads, then gives pending builds up to 200 ticks from the first pass. After that, apps waiting on loaded chunks can use the town's saved place and unbuilt front. Waiting for every distant chunk could leave the prior home visible indefinitely. The timeout is local to the readiness check.
- The first revision on a ready connection can go out immediately, including after reconnect. Later revisions start at least one second apart on that connection. Carrying the old timer across hello could delay recovery. This timing can be adjusted in the shell client alone.

## PLAN-GAP

Section 5 allows 64 palette entries, but its key alphabet has 62 characters. The sender keeps 62 and maps excess colours by RGB distance. The single-part example shows a spare palette key. The sender emits only keys used by the published cells.

## Open questions

None.
