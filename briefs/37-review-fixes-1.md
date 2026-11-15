# 37 review fixes 1: arriving never opens an app, and a checked move is the move that happens

Follow-up on the same branch (`pkg/37-getting-around`, PR #62). The review is `reviews/37-getting-around/REVIEW-1.md` (gpt-6-astra, high): CHANGES-NEEDED, three FIX and three SHOULD. All six are accepted. Its points 3 to 8 are confirmed (the town's principle, host-only commands and `OwnedNodes`, hand-set groups and the apps file, the H key, the test-only registration, `/apps` and `Place.words`).

Read the review, `reviews/37-getting-around/REPORT.md` (judgment calls 1-2, 2-2, 2-4), and the code it names (`world/HomeCommands.java`, `world/GettingAround.java`, `world/HomeSites.java`, `zone/WalkInZones.java`, `hub/TownMoves.java`, `hub/Town.java`, `hub/TownKeeper.java` `plan` and `keep`, `zone/GateBuilder.java` `checkRemoval`, `takeDown` and the sign check `made`, `AresOs.java` around the catalogue and `saveSpots`) before changing anything.

**Builder:** one Claude agent on Opus 5.5, one step. The orchestrator has decided the designs below; a builder that finds a rule cannot be carried out stops and says why. If the budget runs out first, commit what is done and leave `reviews/37-getting-around/PROGRESS.md` with what remains. **Review:** a fresh reviewer checks only these fixes.

## The principle

`swap` and `move` check first and then commit through the town's own pass. The check must see exactly what the commit will see. Every input the commit reads (the catalogue, the apps file, the town's records, the blocks, the entities, the zones, the pictures) is either the same object the check used or is shown to be unchanged at commit time; otherwise nothing changes and one line says to try again.

## 1. Arriving anywhere never counts as walking in (FIX 1)

- The shared home teleport (`HomeCommands.goHome`, behind `/aresos home`, `/home` and the H key) marks the arrival as `/go` does (`WalkInZones.arrived`), so a home set inside a doorway opens nothing.
- Check every teleport the mod makes (home, `/go`, the return in front of a doorway after an app closes, void recovery, the spawn on joining a world, anything else you find) and make each one mark its arrival the same way. List them in the report.
- Test: home set inside a doorway in Build mode, then `/home` in Live mode: no launch after several ticks; walking out and in again launches. The same for the H key's server half.

## 2. One catalogue for the whole command (FIX 2)

- `swap` and `move` take the catalogue once at the start. The checks, the saved places and the town's pass all use that one snapshot (`TownKeeper.keep` already takes the programs it works on).
- At commit time, under the same lock that guards catalogue updates, confirm the catalogue is still that snapshot (its revision or identity). If a helper refresh changed it in between, change nothing and say one line, for example "Your apps changed just now. Nothing was swapped; try again."
- Test: a test hook changes an app's icon path between the checks and the commit. The command refuses, and the apps file's bytes, the town's records, the zones and the blocks are unchanged.

## 3. The check sees which signs come down and which stay (FIX 3)

- The checks model the world after the take-down exactly as the take-down will leave it. A recorded sign the take-down removes (the town's own, as `made` accepts it) is gone. Any other text display, including the logo's own sign that he moved or edited, stays and counts against the incoming logo, as the build's entity check will count it.
- Take this from the take-down's own code (for example `checkRemoval` returning what it will remove), not from a second copy of the rule.
- Then go through the build's checks (`Town.check`, `GateBuilder`) and list in the report, for each input they read, how the check sees it after the take-down. Anything the commit would judge differently is a bug of this kind; fix it the same way.
- Test: move a recorded logo's sign (as `/data` would) into a block the incoming logo will fill, then swap. It refuses before any change to the file, the records or the world.

## 4. Arriving where nothing is loaded yet (SHOULD 4)

- Keep the check of the arrival spot (his build must not be teleported into). Load only the chunks that the arrival positions' boxes touch (at most four), and stop at the first free position.
- Measure in a server test how long a `/go` to a place in a chunk that was not loaded takes on the server thread. Report the number, and the case where every position is blocked.
- If one such `/go` takes more than 50 ms, stop checking synchronously: let the game's own teleport ticket load the area, check in a later tick, and teleport then (or say one line). Otherwise keep it synchronous and say why.
- Correct the claim in HUB.md and in the report to what the code does.

## 5. Test tickets are released however a test ends (SHOULD 5)

The tickets a test takes are released on success, on failure and on timeout. Next to `LOAD_TICKS`, a test also has a wall-clock bound (for example 60 seconds) after which it fails and releases its tickets.

## 6. Frozen and refused, at the command (SHOULD 6)

Server tests: `swap` and `move` in a frozen town and with a refused town file refuse first, and the apps file's bytes, the records, the zones and the blocks are unchanged. Also `/go` in both states, to an app whose logo stands in its recorded place and to one without a logo (the line).

## Verification

- A test for each fix that fails without it, where it can; say which claims are from reading.
- `mod/dev/build.sh` twice and `mod/dev/client-test.sh` once on the final code. Put other packages' pictures back as before; this package's pictures change only if what they show changes.
- The report gets a section "Review fixes 1": per finding what changed, the tests, what ran and what it printed, and the two lists of points 1 and 3. HUB.md and `mod/README.md` follow the change.

## Rules

- As before. Worktree `~/AresOS-37-getting-around`, branch `pkg/37-getting-around`; push with `git push origin pkg/37-getting-around`. Never merge, never push to main, never `--no-verify`. Build and test only through `mod/dev/build.sh` and `mod/dev/client-test.sh`; never `./gradlew`, never `--force`.
- Do not use `gh`.
- Game tests build relative to their own plot and never force or release chunks they don't own.
- The repo is public: no personal data, no Mojang assets, no real app icons.
- Commit after each fix. Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
