Reviewed `3615e4a4..f9bce2ad`. One FIX remains.

1. **FIX — The guard test can swallow its own positive assertions.** At [test_review23_sweep.py:711](control/mail_tests/test_review23_sweep.py:711), expected rejection probes and positive assertions share one latched guard. After a rejection, the guard’s exit replaces a later assertion failure with `AmbientRead`, which the outer `assertRaises` accepts.

   **Reproduced:** patched `time.localtime` to return an invalid empty tuple. The explicit-calendar assertion at line 738 should fail, but the test prints **OK**. These existing assertions have therefore been weakened.

   **Fix:** run positive assertions in a fresh guard scope containing no intentional rejections. Add a regression showing that broken explicit conversions fail the test.

2. **KNOWN LIMIT — Final Linux acceptance remains incomplete.** [Mail run 43175779056](https://github.com/Ares-Empire/AresOS/actions/runs/43175779056) is still on attempt 1. Completed `sweep (3)` runs all 12 required tests successfully, and its five flows retain baseline fault counts. Both complete attempts, all 23 per-flow count comparisons, and every job’s duration against 35 minutes remain unproven.

   **Resolution:** finish both attempts and record counts and whole-job durations as specified.

The original timestamp and cross-clock defects are addressed: one chronology supplies time views and registered blob ages; jumps retain forward progress; expiry keeps production writes; ordering exercises production warnings, recovery and the real notice page. The rejection ledger survives displaced cleanup exceptions.

AST comparison confirms unchanged flow/mode/cleanup enumeration and recovery/completion assertions. The lifecycle change retains all eight assertions. No production code changed.

Independently ran eight guard/CI-selection tests, generator verification and whitespace checks: passed. Full filesystem sweeps were not rerun in this read-only review.

CHANGES-NEEDED