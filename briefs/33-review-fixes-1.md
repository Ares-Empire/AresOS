# 33 review fixes 1: the gate never disturbs what is his

Follow-up to `briefs/33-gate-logo.md` on the same branch (`pkg/33-gate-logo`, PR #49). The review is `reviews/33-gate-logo/REVIEW-1.md` (gpt-6-astra, high, on `d8a56b77`): CHANGES-NEEDED, five blocking, four should-fix, one nit. Read the review, the first brief, `reviews/33-gate-logo/REPORT.md` and the code under `mod/src/main/java/dev/aresos/zone/` before changing anything.

**Builder:** Codex (gpt-6.1-sol, xhigh): rules and checks, nothing about looks. **Review:** the same reviewer model checks only these fixes.

## What is accepted, and how

The bar is the design's own rule: the mod never destroys or changes a block or entity it did not place, and it refuses rather than disturbs. Seven findings are fixed here, one changes the design text instead of the code, one is a known limit.

1. **Removal checks before it removes** (finding 1). Before the first block changes, look at everything that hangs on, stands on or is held by a recorded gate block that is still the mod's: attached blocks (torches, signs, buttons, vines, rails, anything that needs its neighbour), falling blocks resting on one, and hanging entities (item frames, paintings, leashes). If there is any, refuse the whole removal, change nothing, keep the complete record, and name the first such thing and its place in the message. The same check for build already exists; share the logic rather than writing a second one.
2. **A light block he changed is his** (finding 2). A recorded light block is removed only if it is still exactly as placed (level 15, not waterlogged). Otherwise it stays, like any changed block.
3. **A neighbour is only "ours" if the record says so** (finding 3). The neighbour check accepts a palette block next to a planned block by ownership, not by kind: only positions recorded as a gate's (or a hub's) blocks count as the mod's own. An external block whose state reacts to neighbours (the mushroom blocks are the known case; find any other among the 60 by checking the game's classes, not by a hand list) is a reason to refuse. Natural plain ground stays accepted.
4. **The doormat** (finding 4): it is laid only where all eight floor blocks and the complete ring around them, the rear row included, are grass block or dirt. Stone and other "natural-looking" kinds no longer count. Say in the report that grass he laid himself cannot be told from the world's grass; that is a known limit, and the removal puts the same block back.
5. **The ground under a gate comes back** (finding 5). Record, with the gate, the floor blocks under its 12 by 3 footprint that are grass block when it is built. At removal, each of them that is dirt now becomes grass block again; any other block there is his and stays. The server test that accepts grass turning to dirt then asserts the opposite. This also keeps HUB.md 3.3's "untouched grass" rule usable for package 36.
6. **Nothing is read from an unloaded chunk** (finding 6). The loaded check covers every position the build or the removal will read or update, the neighbour halo and the lights' four cells included, before the first read. A test at a chunk border.
7. **The sign's space is checked** (finding 9): the box the name occupies above the gate must be air like the rest of the space, or the build is refused. A test with an overhang.
8. **Nit 10:** derive the default-size assertions and the client test's spacing from `SIZE`; keep the explicit size-12 worked examples.

Not code:

- **Finding 7 (the plate test counts from half opacity):** the first builder's choice stands. HUB.md 2.3 names the outcome (Lunar Client's figure is enlarged), and the 12% of step 1 does not give it. The orchestrator corrects HUB.md 3.6; do not change the threshold. Keep the JUDGMENT-CALL in the report.
- **Finding 8 (an older mod that saves the zones file drops the gate records):** a known limit for gates built by hand. Write it into the report with what the owner would see (after going back to an older AresOS and forward again, `logo remove` leaves the blocks; he removes them in Build mode). The town's logos (package 36) will be recorded in a file of their own that an older mod never rewrites.
- **The wording about two zones** (the review's inherited ambiguity): correct the report to what the code does: two new entries in the same tick open nothing.

## Verification

- A test for each fix that fails without it: a torch on a gate block and sand on one (refused, nothing changed); an item frame; a waterlogged light; an external mushroom block behind a planned mushroom cell (refused, its state unchanged); a stone floor (no doormat); the missing rear row; grass decayed to dirt under the gate and back after removal; the chunk border; the overhang.
- The tests the review calls too narrow get tightened where it costs little: the restoration test compares the world before the build with the world after the removal without repairing anything in between.
- `mod/dev/build.sh` passes; `mod/dev/client-test.sh` passes once on the final code (twice if the client test changed). Put back the tracked screenshots of other packages after a run (`git checkout -- reviews/` and remove untracked pictures outside `reviews/33-gate-logo/`); commit this package's pictures only if they changed.
- `reviews/33-gate-logo/REPORT.md` gets a section "Review fixes 1": per finding what changed, what you ran, what it printed; the two known limits; the corrected wording.

## Rules

- As in the first brief. Worktree `/var/home/ares/AresOS-33-gate-logo`; push the branch; never merge; never `--no-verify`. Stay inside `zone/`, its tests and the report.
- Build and test only through `mod/dev/build.sh` and `mod/dev/client-test.sh`; never `--force`, never `./gradlew` directly, never a window in the real session. While the scripts refuse (exit 75: the owner's game runs, or under 6 GiB available), wait with a blocking sleep of several minutes between tries.
- Commit after each fix. Commit messages end with a trailer naming the model.
