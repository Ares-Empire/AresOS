# 33 review fixes 2: a harmless edit never blocks a removal

Follow-up on the same branch (`pkg/33-gate-logo`, PR #49). The fix check is `reviews/33-gate-logo/REVIEW-2.md` (gpt-6-astra, high, on `7059daf4`): all ten first findings are closed or accepted as decided; one new should-fix came with the fixes (finding 11).

**Builder:** Codex (gpt-6.1-sol, xhigh). **Review:** the same reviewer model checks only this fix.

## The fix

The removal preflight uses the placement whitelist on blocks that stay. So a gate in which he replaced a pixel with a slab or a pillar in Build mode can never be removed: the slab is rightly left alone, but its neighbours' removal gets it inspected and refused, every time.

Removal must refuse only what removal would really disturb. For a block that stays (not in the removal set):

- it is a reason to refuse if it needs a block that is being removed for support or attachment (the existing torch, sign, button, vine, rail and hanging-entity cases), if it would fall, if it holds or is a fluid that would flow into the freed space, or if its state reacts to a neighbour's change;
- otherwise it is no reason, whatever its shape or class: slabs, stairs, walls and fences that only change their look, pillars, glass, full blocks.

Decide by what the game's block does (its support and neighbour-update behaviour in the 26.2 classes), not by a hand list of names. Where that cannot be decided for a kind of block, keep refusing and name it in the message, as today.

Placement keeps its stricter check unchanged.

## Verification

- The changed-block test grows: a gate with one pixel replaced by a dry stone slab, one by a quartz pillar and one by a stair is removed successfully and the three blocks stay as they were; the torch, sand and item-frame refusals still refuse and change nothing.
- `mod/dev/build.sh` passes twice; `mod/dev/client-test.sh` passes once on the final code.
- `reviews/33-gate-logo/REPORT.md`: a short section "Review fixes 2".

## Rules

- As before. Worktree `/var/home/ares/AresOS-33-gate-logo`; the branch now contains a merge of `main` (the dev scripts and the mod workflow come from there); push; never merge; never `--no-verify`. Stay inside `zone/`, its tests and the report.
- Build and test only through `mod/dev/build.sh` and `mod/dev/client-test.sh`; never `--force`. After a client run put back other packages' tracked screenshots (`git checkout -- reviews/`, and remove untracked pictures outside `reviews/33-gate-logo/`).
- Commit messages end with a trailer naming the model.
