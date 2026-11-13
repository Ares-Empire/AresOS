# 32 review fixes 1: a damaged flat home never sends him to the Nether

Follow-up to `briefs/32-flat-home.md` on the same branch (`pkg/32-flat-home`, PR #50). The review is `reviews/32-flat-home/REVIEW-1.md` (gpt-6-astra, high, on `28646baa`): CHANGES-NEEDED, one blocking and four should-fix. Read the review, the first brief, `reviews/32-flat-home/REPORT.md` and the code under `mod/src/main/java/dev/aresos/world/` and `hub/` before changing anything.

**Builder:** Codex (gpt-6.1-sol, xhigh): rules and tests, nothing about looks. **Review:** the same reviewer model checks only these fixes.

## Fixes

1. **A flat home needs its exact home** (finding 1, blocking). A save identified as flat (the manifest's `home=flat`) whose home data lacks the nested home, or holds one that does not decode completely, is a save with unreadable home data: it opens unchanged, with the existing message, no arrival, no respawn change, no rebuild, and the file is not rewritten. The fallback to the old Nether arrival stays only for Nether saves from before this package. Reject partial decodes. Tests that really open a save: the nested home missing, the nested home malformed, both for a flat save; and an old Nether save without the field still arriving as today.
2. **A block he changed is his for good** (finding 2). When the host breaks or replaces a recorded block in Build mode, its entry leaves the record at once and stays out across restarts; putting the same kind of block back does not make it the mod's again. And whenever the mod looks at a recorded position and finds another block there (an explosion in Build mode, a piston, anything), that entry is dropped too. The record's shape stays `{pos, block}`. Tests: the gold block broken and replaced by a gold block of his is breakable in Live mode afterwards; a replacement changed back; the same after a restart.
3. **Explosions follow the host's mode** (finding 3). Whether the pad and roads resist an explosion depends on the singleplayer host's mode alone: Live protects, Build does not. If the host cannot be identified, they are protected. Keep the policy in one small function with a unit or server test of its own, and exercise the real host in the client test.
4. **The no-mob test proves it** (finding 5). In the server test, count mobs as they are added during the whole quiet interval (not only at its end), and restore every rule the test changes. Keep the control. If it fits the suite's time limit, also check the real flat home in the client test: let the game sprint 12000 ticks (the game's own tick sprint) with a counter on added mobs, and assert none; say in the report how long it takes, and leave it out with a reason if it makes the client suite pass eight and a half minutes.

Not code:

- **Finding 4 (the group names can't be edited by hand in Build mode):** a design exception, recorded by the orchestrator in HUB.md: in version 1 the names belong to the mod and change with the look (package 36). Correct the report's wording ("in Build mode he can change every block; the names are the mod's") and keep the test that a name survives.
- The reviewer's assessments of the JUDGMENT-CALLs: 2 and 3 are settled by fixes 3 and 2; the others stand.

## Verification

- Each fix has a test that fails without it.
- `mod/dev/build.sh` passes twice in a row; `mod/dev/client-test.sh` passes once on the final code (twice if the client test changed). After a run put back other packages' tracked screenshots (`git checkout -- reviews/`, and remove untracked pictures outside `reviews/32-flat-home/`); commit this package's pictures only if they changed.
- `reviews/32-flat-home/REPORT.md` gets a section "Review fixes 1": per finding what changed, what you ran, what it printed.

## Rules

- As in the first brief. Worktree `/var/home/ares/AresOS-32-flat-home`; push the branch; never merge; never `--no-verify`. Stay inside `world/`, `hub/`, the protection hooks, their tests and the report.
- Build and test only through `mod/dev/build.sh` and `mod/dev/client-test.sh`; never `--force`, never `./gradlew` directly, never a window in the real session, do not edit `mod/dev/`. While the scripts refuse (exit 75), wait with a blocking sleep of several minutes between tries.
- Commit after each fix. Commit messages end with a trailer naming the model.
