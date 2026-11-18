Reviewed `97a0f045`, limited to `deac29bc..HEAD`. Two findings remain:

1. **Should-fix — holder failure can escape detection during shutdown.**  
   **Where:** `mod/dev/env.sh:178`, `mod/dev/env.sh:197`, `mod/dev/env.sh:276`.  
   **Why:** `holder_lost()` runs before ordinary-scope checks, but not during the final three-second confirmation loop or immediately before intentional holder shutdown. If the holder dies in that interval, cleanup can return success without the required diagnostic. A read-only, in-memory reproduction using the parsed cleanup functions returned status **0** with an unexpectedly dead holder. REVIEW-1 finding 3 is therefore not fully closed.  
   **Fix:** monitor the holder throughout ordinary-scope cleanup, including final confirmation, and check again before transitioning to intentional holder release. Preserve the failure status and diagnostic. Add a deterministic test covering holder death during that interval.

2. **Nit — the corrected report still overstates one test’s timing.**  
   **Where:** `reviews/47-gpu-awake/REPORT.md:138`; `reviews/47-gpu-awake/lifecycle-test.py:195`.  
   **Why:** `parent-kill-release-hang` kills the script while the client runs; hanging release begins afterward. It does not kill the script *during* an already-hanging release, as the corrected claim says.  
   **Fix:** describe this as “parent SIGKILL followed by hanging release,” or add a case that waits for the release event before killing the script.

REVIEW-1 findings **1 and 2 are otherwise addressed**: supervision is independent of CUDA and the shell; cleanup targets recorded scopes and owned child processes, stops clients before the holder, and uses bounded escalation. The harness exercises all four requested scenarios, including persistent client descendants, scope removal, lock reacquisition, and non-zero failure with a diagnostic after holder death during gameplay. Its saved 14-case output matches the local recorded log.

Both full saved power traces support **one observed wake-up and one suspend per complete run**, with a constant suspended-time counter throughout the active interval. Their counter deltas match the report.

Static inspection found the lock, 6 GiB/exit-75 checks, headless isolation, and automatic NVIDIA → Intel → software fallback preserved. Missing or failed NVIDIA initialization retains the fallback path. No privileged operation, protected-system write, or process-name-based killing was added.

No build, Gradle, lifecycle harness, client test, game, or GPU operation was run during this review.

CHANGES-NEEDED