# 46, review fix 1: a failed save answers ok:false

`reviews/46-save-now/REVIEW-1.md` (Codex `gpt-6-astra` `high`, head `f308ee60`) has one blocking finding. `WorldSaves` turns `saveEverything`'s `true` into `world_saved ok:true`. In Minecraft 26.2 that return value doesn't prove anything reached the disk, because the game catches write failures and only logs them:
- a chunk that fails to serialise or write goes to `reportChunkSaveFailure`, including the asynchronous chunk writes that the flush waits for;
- player data, `level.dat` and the saved data each catch and log their own failures.

So a full disk or an unwritable world folder can answer `ok:true`. The supervisor then treats a save that didn't happen as good for a backup, a shutdown or an update.

**Builder:** Codex `gpt-6.1-sol`, `xhigh`. **Review:** a fresh Codex `gpt-6-astra` `high` context. It checks only this fix and what it touches.

## What changes

1. **Find the swallow points.** Read 26.2's code from the Gradle cache, the same way the reviewer did. List every place a world save's write failure is caught without escaping, in the order a `save_world` save reaches them:
   - chunks, including the asynchronous writes;
   - player data;
   - `level.dat`;
   - the saved data (whatever 26.2 calls it);
   - anything else you find.

   For each, record in the report:
   - how the failure is caught;
   - how the mod observes it (a mixin on the reporting method, or on the catch's logging call, or similar).
2. **`ok:true` means everything is on disk.** A `save_world` answers `ok:true` only if:
   - everything the world holds in memory reached the disk in that save;
   - and nothing written since the last good save was lost.

   **Any failure the mod observes during the request's save** answers `ok:false, reason:"error"`, and the log names which part failed.
3. **Failures outside a request.** The reviewer's warning: the game clears a chunk's "unsaved" flag before its write finishes, so a failed write leaves a chunk that no later save rewrites. Resetting a failure flag at the next request would therefore report a recovery that didn't happen.
   - A failure at any time counts, including during the game's own autosave between requests.
   - After any failure, the next `save_world` must rewrite everything again, for example by marking every loaded chunk unsaved before saving.
   - That save answers `ok:true` only if it had no failure, **and** no chunk whose write failed has left memory since. A chunk's in-memory copy is gone once it has left memory, so no later save can repair it.
   - In that case, answer `error` until the world is opened again, and log why.
4. **Joined requests** (the follow-up save from package 46) count their own save's failures by the same rules.

**If unsure:** answer `error`. A false `ok:false` costs a log line. A false `ok:true` can cost the owner his home.

## Tests

- **Unit tests** for the failure accounting:
  - a failure during the request;
  - a failure during an autosave, followed by a request that rewrites everything and succeeds;
  - a failed chunk that has left memory;
  - a joined follow-up.
- **A client game test through the real `WorldSaves` path** with an injected failure, for example a test-only mixin that makes one chunk write throw, or a test world folder made unwritable. The answer must be `ok:false, reason:"error"`, and the next request after the fault is lifted must be `ok:true`.
- The package's existing tests stay green.
- **Runs:** one full `mod/dev/client-test.sh` and one `mod/dev/build.sh`, both green.

## Docs

- `reviews/46-save-now/REPORT.md`:
  - a "Review fix 1" section with the swallow-point list and the rules as built;
  - the run results under Verified.
- `docs/design/OS-BASE.md`, row B1 (`save_world`): one sentence that `ok:true` means everything in memory reached the disk, and that after a lost write it answers `error` until the world is opened again.

## Rules

As in `briefs/46-save-now.md`. Worktree `~/AresOS-46-save-now`, branch `pkg/46-save-now` (PR #92). Only `mod/`, `reviews/46-save-now/` and that one row of `docs/design/OS-BASE.md` change.

- Package 48 (PR #94) is a separate branch. Don't merge it in here.
- Other builders share the laptop. `client-test.sh` waits for its lock by itself. On exit 75 (low memory, or the owner's own game), wait about five minutes and try again, at most six times, then stop and say so.
- Until further notice:
  - run no `rpm-ostree`, `bootc` or `ostree` command, not even a read-only one;
  - run no `os/tests` owner modules;
  - mount no disk.
- End each commit with the trailer line `Codex-Model: gpt-6.1-sol xhigh`.
- Commit, push, and add a comment to PR #92 saying what changed. Never merge, never push to main, never `--no-verify`.
