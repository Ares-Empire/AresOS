# 53b home publication

## Done

- `mod/src/main/java/dev/aresos/shell/` negotiates 1.2 and publishes to helpers offering `home_state`. It checks the app, palette, part and UTF-8 byte limits before sending. The writer waits for each acknowledgement, coalesces updates, and starts a fresh revision on reconnect. A refusal logs the helper's reason and leaves the connection usable.
- `mod/src/main/java/dev/aresos/hub/` captures the integrated host's town after a whole pass and the picture reads. It takes standing places and fronts from `HubData`, uses the town's picture for unbuilt apps, and notices successful replacements and recorded front edits independently of chat.
- `mod/src/main/java/dev/aresos/item/AppInventory.java` reads slot numbers. `mode/ModeInventories.java` supplies the saved Live slots while Build is active and waits through an in-progress mode switch. The publisher uses the existing `config/` My apps list, `names/NameRules` short names, and `zone/` gate pictures and palette.
- `mod/src/testShared/` validates incoming parts in the socket fake. The unit tests cover the contract examples and limits, legacy negotiation, startup and reconnect, burst coalescing, refusal, and front and slot data. The final client test drives the same paths in an integrated home. `mod/README.md` describes what the helper receives.

## Verified

- `mod/dev/build.sh --dry-run` printed `BUILD SUCCESSFUL in 8s` with all tasks listed as skipped for the dry run.
- `mod/dev/build.sh compileTestJava` initially printed `All 106 required tests passed :)` and failed on three new unit-test cases. The multipart example fixture's tie order was corrected, and the refusal test was set to report a focused launch so it could verify the same connection.
- `mod/dev/build.sh` printed `BUILD SUCCESSFUL in 3m 45s` and `All 106 required tests passed :)`. JUnit reported 300 tests, with 294 passes and the six expected Windows-specific skips.
- `mod/dev/client-test.sh build`, first run, printed `BUILD SUCCESSFUL in 15m 4s`, `All 106 required tests passed :)`, and exit code 0. The headless client used the NVIDIA RTX 4060 and printed `53b home publish checks passed: wait for host, standing places, pin, swap, saved Live slots, name, move, add, remove and front edit`.
- `mod/dev/client-test.sh build`, second run, printed `BUILD SUCCESSFUL in 15m 2s`, `All 106 required tests passed :)`, and exit code 0. The new client test passed again on the same GPU. Both combined runs reran the client and server game tests and reported the unit-test task as up to date.
- Restored only the tracked screenshots the runs rewrote, 58 for the first run and 56 for the second. Archived 25 new screenshots from each run in its own ignored `.work/` folder, including the seed screenshots. The publication test verifies the town and hotbar directly.
- `git diff --check origin/main...HEAD` passed. `find .work -type f -size +500M -print` returned no files.

## Not verified

The installed helper and laptop-home window still need the live two-screen trial with the owner's town.

## JUDGMENT-CALL

- A fresh home waits for a whole town pass and its picture reads, then gives pending builds up to 200 ticks from the first pass. After that, apps waiting on loaded chunks can use the town's saved place and unbuilt front. Waiting for every distant chunk could leave the prior home visible indefinitely. The timeout is local to the readiness check.
- The first revision on a ready connection can go out immediately, including after reconnect. Later revisions start at least one second apart on that connection. Carrying the old timer across hello could delay recovery. This timing can be adjusted in the shell client alone.

## PLAN-GAP

Section 5 allows 64 palette entries, but its key alphabet has 62 characters. The sender keeps 62 and maps excess colours by RGB distance. The single-part example shows a spare palette key. The sender emits only keys used by the published cells.

## Open questions

None.
