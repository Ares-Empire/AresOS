No blocking, should-fix, or nit findings in `25854164..36a058d0`. Both REVIEW-2 findings are closed.

- **Cleanup:** `mod/dev/env.sh:198` checks the holder during final confirmation; `:280` checks again immediately before intentional release, including when no ordinary scopes exist. `holder_failed` stays latched, prints the diagnostic once, and forces failure through the finish reply and shell exit handling. The additions preserve existing deadlines, process ownership and supervisor teardown; no new PID-reuse or unrelated-scope stopping race was found.
- **Timing claim:** `reviews/47-gpu-awake/REPORT.md` correctly describes parent SIGKILL **followed by** hanging release, matching `lifecycle-test.py:251`.
- **Deterministic regression case:** The shim gates injection on KILL escalation, kills the recorded holder during the first final-confirmation query, waits for its pidfd, and forces another confirmation iteration. Its marker requires the diagnostic before that query completes. Assertions cover exit 1, exactly one diagnostic, exited clients, removed scopes and lock reacquisition.
- **Evidence:** All 15 case names and expected statuses match the committed output, which matches `.work/47/lifecycle-review-fix-2-final.log` byte-for-byte. Both full saved power traces match the committed transition CSV: each shows one observed wake-up and one suspend, with a constant suspended-time counter throughout active samples. Counter deltas match the report.
- **Preserved safeguards:** The lock, 6 GiB checks, headless isolation and NVIDIA → Intel → software fallback are unchanged. No protected-system writes, root requirement or process-name killing was added.

Read-only review only: files, git and small evidence-parsing Python. No build, Gradle, harness, client test, game or GPU operation was run; no files were changed.

SAFE