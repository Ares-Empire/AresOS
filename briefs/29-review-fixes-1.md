# 29 review fixes 1: the dev scripts own everything they start

Follow-up to `briefs/29-linux-dev-rig.md` on the same branch (`pkg/29-linux-dev-rig`, PR #44). The review is `reviews/29-linux-dev-rig/REVIEW.md` (gpt-6.1-sol, on `8ee4aefa`): CHANGES-NEEDED, 3 blocking and 5 should-fix. All eight are accepted. Read the review, the first brief and the four scripts under `mod/dev/` before changing anything.

**Builder:** a fresh Claude agent (Opus 5.5). **Review:** the same reviewer model checks only these fixes.

## The one idea behind the fixes

Every process a script starts (the app helper, a GPU probe, Gradle, the game, a compositor) runs in a systemd user scope that the script created and named, and the script stops things only by stopping its own scopes. No script remembers a PID to kill later, and none reuses something an earlier run left behind. That removes findings 1, 2, 3 and 4 by construction instead of patching each.

## Fixes

1. **`run-hub.sh`: its own helper, its own socket, no reuse** (findings 1 and 4).
   - Each run makes a private folder `$XDG_RUNTIME_DIR/aresos-dev/run-hub-<pid>/` (mode 0700), starts the helper with `--socket <that folder>/shell.sock`, and gives the game `ARESOS_SHELL_SOCKET` with the same path. It never uses `$XDG_RUNTIME_DIR/aresos/shell.sock`: once package 23 is on the laptop, the session's own helper lives there.
   - The helper runs in a scope of its own, like the game. Remove the record file, `own_helper`, the reuse branch and the PID-based `kill`. A helper is never reused; a leftover folder of a dead run is removed at start only if no scope of that run exists any more.
   - Before the game starts: the helper's scope is active and the socket in the private folder is listening. Only this run can have created it.
   - At exit: stop both scopes, remove the private folder.
   - Say in the header that, with the session's own helper running (after package 23), two helpers watch the same windows while this script runs; that is accepted for a development aid.
2. **GPU probes are owned too** (finding 2): each probe runs in a scope the script created, registered for cleanup like the main run, its output captured through a file, with a bounded stop (TERM, then KILL after a few seconds). A wedged probe can never keep the client-test lock.
3. **No gap between starting and owning** (finding 3): a signal that arrives while a scope is being started must not run the cleanup before that scope is registered. Defer signal-triggered exit across the start-and-register step and act on it right after, in `env.sh`, for every scope.
4. **Check again right before the heavy part** (finding 5): `client-test.sh` and `run-hub.sh` repeat the Lunar and memory check immediately before starting Gradle, after the lock and the probes; `--force` still skips it.
5. **Lunar detection means the game** (finding 6): only a Java executable under `~/.lunarclient/` counts (the brief's wording), not any program there.
6. **Gradle's own daemon switches are refused** (finding 7): `--daemon`, `--stop` and `--status` among the forwarded arguments stop the script with one sentence, in all three scripts.
7. **`--keep-screenshots` tells the truth** (finding 8): the destination is created and checked before the run; a failed copy is reported as a failure and changes the exit code of an otherwise green run to non-zero.

`env.sh` holds the scope bookkeeping once (a list of this script's scopes); the three scripts use it. Keep the scripts as short as they can be: this round should remove about as much code as it adds.

## Verification

- `bash -n` on all four files, and `shellcheck` if the laptop has it (it is not to be installed).
- `mod/dev/build.sh` passes.
- `mod/dev/client-test.sh` passes once in full, headless as before.
- Signals, each followed by `systemctl --user list-units 'aresos-dev-*' --all --no-legend` printing nothing and the lock being free: TERM during a GPU probe, TERM right at the start of the main run, TERM in the middle of the run, HUP in the middle of the run.
- `run-hub.sh` **only inside a headless compositor of your own** (no window on the owner's screen in this round): the helper accepts the game's hello on the private socket; `$XDG_RUNTIME_DIR/aresos/` is not created or touched by the script; after the game ends, and after TERM, no scope and no private folder is left.
- The refusals: `--daemon`, an unwritable `--keep-screenshots` destination, a fake "Lunar game" (a process of your own whose executable is a copy of a small program in a scratch folder does **not** count; say how you tested the positive case without touching `~/.lunarclient`).
- Update `reviews/29-linux-dev-rig/REPORT.md` with a "Review fixes 1" section: what changed per finding, what you ran and what it printed. Update `mod/README.md` where the behaviour changed.

## Rules

- As in the first brief: worktree `~/AresOS-29-linux-dev-rig`, push the branch, never merge, never `--no-verify`. No mod source and no test changes in this round.
- While the owner's game runs or under 6 GiB available: wait and check again every few minutes; don't use `--force`.
- Stop only processes you started, by your own scopes or PIDs you hold; never by name.
- Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
