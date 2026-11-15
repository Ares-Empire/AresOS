# 34 review fixes 2: `/aresos give` never loses the item it moves

Follow-up on the same branch (`pkg/34-my-apps`, PR #52). The fix check is `reviews/34-my-apps/REVIEW-2.md` (gpt-6-astra, high, on `f57e83a8`): all thirteen first findings are closed or accepted as decided; one new should-fix came with the fixes.

**Builder:** Codex (gpt-6.1-sol, xhigh). **Review:** the same reviewer model checks only this fix.

## The fix

`/aresos give <app>` now moves the app's existing item instead of making a second one (round 1). It removes the item first and then inserts it. In Build mode with slots 0 to 35 full and the app's item in the offhand, the game's creative-mode insertion swallows the stack and reports success: the item is gone and the command says it worked.

Choose the destination before touching the existing item, and move it there directly. If there is no destination, leave everything as it was and say so. The same care for any other place where this package removes an app's item before placing it again: read `item/AppInventory.java` for that pattern and fix each case you find, naming them in the report.

## Verification

- A server test: a full Build inventory with the app's item in the offhand, `give`, and both inventories exactly as before with a failure message; and the ordinary cases (a free slot; the item already in the main inventory) still move the one item.
- `mod/dev/build.sh` passes twice; `mod/dev/client-test.sh` passes once on the final code.
- `reviews/34-my-apps/REPORT.md`: a short section "Review fixes 2".

## Rules

- As before. Worktree `/var/home/ares/AresOS-34-my-apps`; push; never merge; never `--no-verify`. Stay inside `item/`, its tests and the report. The example messages under `mod/src/test/resources/shell-1.1/` stay unchanged.
- Build and test only through `mod/dev/build.sh` and `mod/dev/client-test.sh`; never `--force`. After a client run put back other packages' tracked screenshots (`git checkout -- reviews/`, and remove untracked pictures outside `reviews/34-my-apps/`).
- Commit messages end with a trailer naming the model.
