# 37 review fixes 2: the swap's own pass touches only what it checked

Follow-up on the same branch (`pkg/37-getting-around`, PR #62). The fix check of round 1 at `60d66a0b` is `reviews/37-getting-around/REVIEW-2.md` (gpt-6-astra, high): CHANGES-NEEDED, one FIX, two SHOULD and one NIT. All four are accepted. Everything else of round 1 is confirmed: arrivals (the list of teleports is complete), the catalogue snapshot and its lock, `checkRemoval` and `takeDown` as one rule, `Gone`, and the earlier behaviour.

Read `REVIEW-2.md`, `briefs/37-review-fixes-1.md` (the principle stays), the section "Review fixes 1" of `reviews/37-getting-around/REPORT.md` with F1 to F7, and the code it names (`hub/TownMoves.java`, `hub/TownKeeper.java` `plan`, `keep` and its rounds, `world/Arrivals.java`, `world/GettingAround.java`, `mode/LiveMode.java`, `GettingAroundGameTests.java`) before changing anything.

**Builder:** one Claude agent on Opus 5.5, one step. The orchestrator has decided the designs below; a builder that finds a rule cannot be carried out stops and says why. If the budget runs out first, commit what is done and leave `reviews/37-getting-around/PROGRESS.md` with what remains. **Review:** a fresh reviewer checks only these fixes.

## 1. The swap's own pass touches only the logos it moves (FIX 1)

Why: the pass that commits a swap or move today is a whole pass of the town. It can also renew, build or take down other logos in the same tick (a renewal after a name or picture change, a newcomer, an app that left), and those effects are not in the checks. F4 is withdrawn.

- `swap` and `move` commit through a pass of the town limited to the apps the command moves. In that tick it takes down and builds only their logos, plus what follows from them by package 36's rules: the group names and counts, the roads of their groups (paved only on untouched loaded ground, as always), the doormats. Every other logo stays exactly as it is in that tick, including one that is due for renewal, and is handled by the next ordinary pass. Ask the town for that pass after the command.
- The limited pass is the same code as the ordinary pass with a scope, not a second way of building. Planning (where each app stands) still sees every app's place, as today.
- The checks model exactly the limited pass's take-downs and builds, as round 1 made them do. Say in the report why nothing outside the scope can change in that tick.
- If the limited pass still ends otherwise than checked, the existing "town did not finish" line stays. It must not save a place other than the one the command checked: the limited pass never moves an app of the command on to another place. Say how that is ensured.
- Tests:
  - the review's three-app case: C due for renewal, its sign moved into A's new place, swap A and B. The swap succeeds or refuses exactly as checked; C is untouched in that tick and renewed by the next ordinary pass; his sign stays;
  - a newcomer waiting while a swap runs: it is built by the next pass, not in the swap's tick;
  - the claims in the report (`REPORT.md` around lines 540 and 640) are corrected.

## 2. A pending `/go` is dropped when it is no longer his wish (SHOULD 2)

- A pending (deferred) `/go` belongs to the player's connection and to the dimension he was in when he typed it. It is dropped, its ticket released and nothing said, when he leaves the game, changes dimension, dies or respawns, is moved by void recovery, or is moved by any other teleport of the mod.
- Before landing it checks its target again: the app is still one of his, and its logo stands at the same place, or its hand-made zone still exists. Otherwise it drops the request and says one line.
- Tests: a dimension change, a respawn and `/home` while a `/go` waits (none lands), and the app removed from My apps while it waits (one line, no move).

## 3. The test's clean-up says what it does (SHOULD 3)

- Cover the unguarded teleport steps (`GettingAroundGameTests.java` around lines 589 and 606) with the same clean-up.
- Correct the comment: the wall-clock bound works only while the server ticks (it is checked by the test's own steps). A server that stops ticking ends the whole test run through Gradle's limits. No watchdog thread: releasing tickets from another thread is not safe.
- If a test can force the wait's timeout path cheaply, add it; otherwise say it is checked by reading.

## 4. Wording (NIT 4)

The comments in `Arrivals.java` and `GettingAround.java`, the report and HUB.md say what the code does: the ground is requested through the game's ticket system and checked in a later tick. They do not say the loading happens away from the server thread. Keep the report's distinction between the command's own time (about 1 ms) and the loading tick (about 400 ms in the test world, a new chunk; unmeasured in his own world).

## Verification

- A test for each fix that fails without it, where it can; say which claims are from reading.
- `mod/dev/build.sh` twice and `mod/dev/client-test.sh` once on the final code. Put other packages' pictures back as before (restore `.png` files only, so the report is not reverted); this package's pictures change only if what they show changes.
- The report gets a section "Review fixes 2": per finding what changed, the tests, what ran and what it printed.

## Rules

- As before. Worktree `~/AresOS-37-getting-around`, branch `pkg/37-getting-around`; push with `git push origin pkg/37-getting-around`. Never merge, never push to main, never `--no-verify`. Build and test only through `mod/dev/build.sh` and `mod/dev/client-test.sh`; never `./gradlew`, never `--force`.
- Do not use `gh`.
- Game tests build relative to their own plot and never force or release chunks they don't own.
- The repo is public: no personal data, no Mojang assets, no real app icons.
- Commit after each fix. Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
