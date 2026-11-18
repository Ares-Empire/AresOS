# 47, review fix 1: an aborted run leaves nothing behind

`reviews/47-gpu-awake/REVIEW-1.md` (Codex `gpt-6-astra` `high`, head `5d19dd82`) confirmed several things:
- the measured result: one wake-up and one suspend per complete run;
- the lock, the 6 GiB check, the headless compositor and the fallback order are preserved;
- the change has no privileged operation and kills nothing by name.

It found three gaps in what happens when a run is aborted. Fix all three.

**Builder:** Codex `gpt-6.1-sol`, `xhigh`. **Review:** a fresh Codex `gpt-6-astra` `high` context, checking only these fixes and what they touch.

**The report's JUDGMENT-CALL is accepted as built (lead, 2026-11-17).** The card stays in D0 only for the lock-held test interval, through an idle CUDA context. If the context can't be made, the run falls back to Intel or software. This is a development tool's battery use during test runs, not something the owner sees.

## What changes

1. **Parent death during a hanging CUDA call (blocking, `env.sh:224`).**
   - **The gap:** the holder checks the script's pidfd only after initialisation. If the script dies while `cuInit` or context creation hangs, nothing ends the holder. Releasing the context has no time limit either.
   - **The fix:** supervise the CUDA work independently of both the script and the CUDA calls, so that parent death is noticed at every point, including during initialisation. For example, a small supervisor process could watch the script's pidfd and own a CUDA worker child.
   - **Every exit path is bounded in time:** a normal release, parent death and a hanging release each end with termination by the owned PID or pidfd within a fixed number of seconds.
2. **Killing the script leaves the game running (blocking, `env.sh:244`, `client-test.sh:175`).**
   - **The gap:** SIGKILL skips the EXIT trap, so the game's scope and the compositor's scope keep running. They keep using the card and the inherited lock.
   - **The fix:** make parent death clean up everything the invocation started: first the game and compositor scopes (stopped by their own unit names or PIDs, which the run recorded when it created them), then the CUDA holder.
   - **Afterwards** the lock must be free for the next run.
   - **Scope:** this applies only to scopes this invocation created, never to anything else.
3. **The holder dying mid-run goes unnoticed (should-fix, `env.sh:253`).** Watch the holder for the whole run, not only until `READY`. If it exits unexpectedly, abort the run with the same cleanup and a non-zero exit, and print a line that says why.
4. **The report's claim** that killing the script can't orphan the context: correct it to what the new tests prove.

## Tests

The stand-in harness, with no real game and no real CUDA where a stand-in is enough:
- parent SIGKILL while CUDA initialisation hangs;
- a release that hangs;
- SIGKILL of the script while a persistent stand-in client runs. Check that the client's scope is gone and that the lock can be taken again within the bound;
- the holder killed after `READY` while the client runs. Check that the run aborts with cleanup and a non-zero exit.

Then **one real `mod/dev/client-test.sh` run**, sampling the card as before: it still shows one wake-up and one suspend.

## Docs

`reviews/47-gpu-awake/REPORT.md`:
- a "Review fix 1" section saying what changed for each finding;
- the corrected claim;
- the test and run results.

## Rules

As in `briefs/47-gpu-awake.md`. Only `mod/dev/client-test.sh`, `mod/dev/env.sh`, the harness and `reviews/47-gpu-awake/` change.
- Read-only on the system: no sudo, no writes under `/sys`, `/proc` or `/etc`.
- Stop only what this run started, by PID, pidfd or the unit name it created.
- Other builders share the lock. Package 49's measurement runs may be using it, so let them through between your runs. On exit 75, wait about five minutes and try again, at most six times.
- End each commit with the trailer line `Codex-Model: gpt-6.1-sol xhigh`.
- Commit, push, and comment on PR #103. Never merge, never push to main, never `--no-verify`.
