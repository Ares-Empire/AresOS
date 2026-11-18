# 47, review fix 2: the holder is watched until it is released on purpose

`reviews/47-gpu-awake/REVIEW-2.md` (Codex `gpt-6-astra` `high`, head `97a0f045`) checked review fix 1. **Confirmed:**
- REVIEW-1's findings 1 and 2 are closed:
  - the supervision is independent of CUDA and the shell;
  - only recorded scopes and owned children are stopped;
  - the escalation is bounded.
- The harness covers all four cases.
- The power traces show one wake-up and one suspend per complete run.
- The lock, the 6 GiB check, headless isolation and the fallback order are preserved.

Two things are left.

**Builder:** Codex `gpt-6.1-sol`, `xhigh`. **Review:** a fresh Codex `gpt-6-astra` `high` context, checking only this fix.

## What changes

1. **Holder death during cleanup (should-fix, `mod/dev/env.sh:178`, `:197`, `:276`).**
   - **The gap:** `holder_lost()` is not checked during the final three-second confirmation of ordinary-scope cleanup, or just before the intentional holder release. A holder that dies in that interval lets cleanup return 0 without the diagnostic.
   - **The fix:** watch the holder through the whole ordinary-scope cleanup, including the final confirmation, and check again right before the intentional release. Once lost, the failure status and the diagnostic line are kept whatever happens after.
2. **The report's timing claim (nit, `reviews/47-gpu-awake/REPORT.md:138`, `lifecycle-test.py:195`).** `parent-kill-release-hang` kills the script first, and the release hangs afterwards. Choose one of two fixes:
   - say exactly that ("parent SIGKILL followed by a hanging release");
   - or add a case that waits for the release to start hanging before it kills the script, and keep the claim.

## Tests

- **A new deterministic harness case:** the holder dies during the ordinary-scope cleanup's final confirmation. Expect a non-zero exit, the diagnostic line, scopes gone and the lock free.
- **The existing 14 cases** still pass.
- **One real `mod/dev/client-test.sh` run,** sampling the card as before. It must still show one wake-up and one suspend.

## Docs

In `reviews/47-gpu-awake/REPORT.md`:
- a "Review fix 2" section;
- the corrected claim;
- the new case's result and the real run's trace.

## Rules

As in `briefs/47-review-fix-1.md`:
- **What may change:** only `mod/dev/client-test.sh`, `mod/dev/env.sh`, the harness and `reviews/47-gpu-awake/`.
- **No privileged access:** no sudo, and no writes under `/sys`, `/proc` or `/etc`.
- **Stopping processes:** stop only what this run started.
- **The lock:** on exit 75, wait about five minutes and retry, at most six times.
- **Commits:** end each commit with the trailer line `Codex-Model: gpt-6.1-sol xhigh`.
- **Where it goes:** merge origin/main first if it has moved. Commit, push and comment on PR #103. Never merge, never push to main, never `--no-verify`.
