# 29 review fixes 2: four small holes in the dev scripts

Follow-up on the same branch (`pkg/29-linux-dev-rig`, PR #44). The fix check is `reviews/29-linux-dev-rig/REVIEW-2.md` (gpt-6.1-sol, high, on `5e53ca2f`): seven of the eight first findings are closed, one is open, and three new should-fix findings came with the fixes. Read it, `briefs/29-review-fixes-1.md` and `mod/dev/env.sh`, `client-test.sh`, `run-hub.sh`, `build.sh` as they are now.

**Builder:** Codex (gpt-6.1-sol, xhigh). **Review:** the same reviewer model checks only these fixes, with this bar: these are development scripts on one laptop. A finding counts if a script can leave something running that holds the client-test lock, stop something it did not start, or put a window on the owner's screen. A case that needs a broken systemd or an impossible name clash is a known limit, written into the README, not another round.

## Fixes

1. **Gradle's daemon switches in every spelling** (finding 7, still open). Gradle also accepts single-dash long options. Refuse `--daemon`, `--stop`, `--status`, `--foreground` and their single-dash forms in the shared guard, for all three scripts. One test loop over the eight spellings.
2. **A failed question to systemd is not an answer** (new finding 1). Where cleanup asks whether its scopes are gone, and where `run-hub.sh` decides that an old run's folder is stale, treat a failed `systemctl` call as "not known": retry the stop and the question until the stop timeout, and if absence still can't be confirmed, say so in one loud line that names the units and exit non-zero; never delete a run folder on a failed query.
3. **Starting a scope has a deadline** (new finding 2). If a scope has not become active (and its launcher has not ended) within a fixed time (15 seconds is plenty), the script stops waiting, stops that unit by name, handles the deferred signal, and fails with one sentence. A signal is never deferred longer than that.
4. **A name is ours only if we made it** (new finding 3). Before creating a scope, check that no unit of that name exists and pick a new random suffix if one does. If `systemd-run` fails, the name is taken off the list without stopping anything.

Keep the changes small: this round should add a few dozen lines, not a new mechanism.

## Verification

- `bash -n` on the four files; the stand-in tests of round 1 extended for each fix: the eight spellings; a `systemctl` wrapper on a private `PATH` that fails for the question (the script says the units are not confirmed gone and exits non-zero, and no folder is deleted); a launcher that never activates (the script gives up after the deadline, also with a TERM sent meanwhile); a unit name that already exists (another suffix is used, and the existing unit is still running afterwards).
- `mod/dev/build.sh` passes; `mod/dev/client-test.sh` passes once in full.
- `reviews/29-linux-dev-rig/REPORT.md` gets a section "Review fixes 2"; `mod/README.md` gets a short "Known limits" list for the dev scripts (a real Ctrl+C and a really closed terminal were tested as signals only; a hanging probe was tested with a stand-in).

## Rules

- As before: worktree `/var/home/ares/AresOS-29-linux-dev-rig`, push the branch, never merge, never `--no-verify`. No mod source and no test changes.
- Never open a window in the real session. While the owner's game runs or under 6 GiB available: wait with a blocking sleep of several minutes; never `--force`. Stop only what you started, by your own scopes or PIDs you hold.
- Commit after each fix. Commit messages end with a trailer naming the model.
