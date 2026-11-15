# 34 review fixes 1: My apps holds in the corners

Follow-up to `briefs/34-my-apps.md` on the same branch (`pkg/34-my-apps`, PR #52). The review is `reviews/34-my-apps/REVIEW-1.md` (gpt-6-astra, high, on `dad1442b`): CHANGES-NEEDED, three blocking, nine should-fix, one nit. Read the review, the first brief, `reviews/34-my-apps/REPORT.md`, `docs/design/HUB.md` 2.4, 3.5 and 3.8, and the code it names before changing anything.

**Builder:** Codex (gpt-6.1-sol, xhigh): rules, state and tests. **Review:** the same reviewer model checks only these fixes.

## Fixes

Inventories:

1. **Every login reconciles both inventories** (finding 1). A removal that was waiting when he left, or a moved apps file, must not leave an item of a program that is not his in the Live or in the saved Build inventory. Additions are marked done only when they really ran in Live.
2. **No copy from the crafting grid or from `/aresos give`** (finding 2, in part). Picking an app up in the Apps screen is refused while the crafting grid holds anything (as it is for the cursor), and `/aresos give` moves the app's existing item instead of making a second one. Chests and other containers are **not** policed: an app item he puts into a chest is his business, and the mod may put a fresh one into his inventory. Write that into the report and the README as a known limit, and correct every sentence that claims an app's item is unique.
3. **Reconciling keeps things where they are** (finding 5). Pinned apps are placed into the hotbar once, at the moments they were placed before this package; a later reconcile removes unwanted items, refreshes names and looks, and puts missing items into slots 9 to 35. It never moves an item that is already there.
4. **A full inventory is tried again** (finding 6). An app that got no item because nothing was free gets it when a slot is free: keep the work pending and try again at safe inventory changes or on a slow safe tick. The same for an item given back from the cursor. The existing test must pass without calling `MyAppsGame.changed()` by hand.

The list and the helper:

5. **The starters are his on a fresh start too** (finding 4). With a new apps file and a 1.0 helper, `browser`, `terminal` and `notepad` are in My apps when first discovered, without a baseline being written and without bringing back a starter he removed. A test with a really fresh file and a 1.0 helper.
6. **A page without a proper revision is no page** (finding 8). In 1.1 every page needs a revision that is a non-empty string; otherwise the whole listing is thrown away and the list and the apps file stay as they were. Tests for missing, null, a number and an object.
7. **Nothing is missed at startup** (finding 9). Subscribe before the helper connection starts, and carry "this list has details" with the list itself instead of asking the client afterwards, so a list that arrives between start and subscription still reaches the apps file and the inventory, and an older snapshot never overwrites a newer one. A test in production's order.
8. **One send per request and connection** (finding 11, older than this package; it made a unit test fail on GitHub in package 38). Each pending open remembers the connection it was last sent on; the normal send and the replay after a reconnect go through one function that sends once per connection. A deterministic test with a barrier, asserting one received request per ID on that connection. `reviews/38-reproducible-jar/StartupReplayProbe.java` on branch `pkg/38-reproducible-jar` shows the ordering (`git show origin/pkg/38-reproducible-jar:reviews/38-reproducible-jar/StartupReplayProbe.java`).
9. **The game never waits on an icon file** (finding 3). No helper icon is read on the thread that starts the game: at startup the items use their fallback looks, and the pictures arrive through the background path that already exists for later changes. A read that does not finish within a few seconds is given up without blocking later reads (a stuck worker is replaced, not waited for). Keep the checks and limits; open without following a symlink at the last path element where the platform allows it. The threat here is a broken file, not a hostile program of his own user: say so in the report instead of claiming more.

The screen and the commands:

10. **A double click never adds the neighbour** (finding 7). After a click that changes the list, a second click of the same double click acts on the same program or on nothing. A test with three results in a list too short to scroll.
11. **Every new program is named** (finding 12): more than five at once are told over several ticks or in several lines, none as "and N more".
12. **Completion follows the same rule as execution** (nit 13): no suggestions for anyone but the host in an AresOS world.
13. **The "Apps…" button** no longer sits over the hearts: put it centred above the inventory panel, 4 pixels above its top edge, at the same size. One screenshot of the inventory with the button, looked at.

Not code:

- **Finding 10 (moving a schema-1 file on Linux drops the Windows commands from the working file):** as designed (`docs/design/OS-BASE.md` B1: on Linux the commands stay in the backup only). Correct the report's "nothing is lost" to say exactly that.

## Verification

- Each fix has a test that fails without it; the review's list of missing cases is the checklist (fresh file with 1.0, saved-inventory reconciliation after a reconnect, crafting-grid pickup, a slot freed without help, malformed revisions, startup order, the short-list double click).
- `mod/dev/build.sh` passes twice in a row; `mod/dev/client-test.sh` passes twice on the final code. After a run put back other packages' tracked screenshots (`git checkout -- reviews/`, and remove untracked pictures outside `reviews/34-my-apps/`); commit this package's pictures if they changed.
- `reviews/34-my-apps/REPORT.md` gets a section "Review fixes 1": per finding what changed, what you ran, what it printed; the known limit about containers.

## Rules

- As in the first brief. Worktree `/var/home/ares/AresOS-34-my-apps`; push the branch; never merge; never `--no-verify`. Stay inside `shell/`, `config/`, `item/`, `icon/`, `catalogue/`, `mode/` where the fixes need it, `client/AppsScreen.java`, the inventory button's registration, their tests and the report. The example messages under `mod/src/test/resources/shell-1.1/` are a contract for the OS helper: do not change them; if a fix seems to need it, stop and report.
- Build and test only through `mod/dev/build.sh` and `mod/dev/client-test.sh`; never `--force`, never `./gradlew` directly, never a window in the real session, do not edit `mod/dev/`. While the scripts refuse (exit 75), wait with a blocking sleep of several minutes between tries.
- Commit after each fix. Commit messages end with a trailer naming the model.
