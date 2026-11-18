# PR #97: REVIEW-1 follow-up

## Done

- `control/tests/test_service_fixes.py`: retained the stopped wall clock and exact formula assertions. Added an independent first-select upper bound of **0.41 s** for the **0.4 s** pending reservation. The near-deadline floor test had the same dependency on `DEADLINE_MARGIN`; its **0.002 s** future deadline now also has an independent **0.012 s** upper bound. Product code is unchanged.
- PR description section 1: added one paragraph distinguishing requested deadlines from real elapsed-time responsiveness, documenting both independent bounds and the unchanged known limit from finding 2. All other description text, including its final attribution and session link, is preserved.

## Verified

From `control/`:

- `PYTHONPATH=.:tests python3 -m unittest test_service_fixes.IdleLoop`, twice: `Ran 9 tests in 1.043s`, `OK`; then `Ran 9 tests in 1.003s`, `OK`. Both printed the existing `Background maintenance failed; inspect service state.` diagnostic.
- `PYTHONPATH=.:tests python3 -m unittest test_service_fixes`, once: `Ran 56 tests in 5.451s`, `FAILED (errors=1)`. The sole error was the expected `StartWithoutService.test_an_mcp_session_started_without_the_service_gets_its_tools`: `ModuleNotFoundError: No module named 'mcp_types'`. The laptop lacks the vendored MCP SDK. ResourceWarnings reported the startup child and unclosed pipes; the named child had already exited when checked by PID.

From the repository root:

- `python3 .work/fix-97/run-mutations.py`: ran all nine new `IdleLoop` tests separately for each of REVIEW-1's ten mutations. All changes to product code were confined to `.work/fix-97/mutant/control/`; each mutation was restored before the next. The runner uses the actual Unix listeners, selector, SQLite and journal, with no listener substitution. All kills were assertion failures, with no setup errors.
- The 250 ms `DEADLINE_MARGIN` mutation produced `0.6500000953674316 not less than or equal to 0.41` in the pending-expiry test and `0.252000093460083 not less than or equal to 0.012` in the near-deadline test.
- `git diff --check`: passed. No screenshots apply to this test-only change.

| Mutation from REVIEW-1 | New class |
|---|---|
| Ignore the pending deadline in `Daemon.timeout` | Killed |
| Remove the idle loop's `engine.expire()` call | Killed |
| Add 250 ms to the calculated future-deadline timeout | Killed |
| Select the latest reservation instead of the earliest | Killed |
| Leave expired operations reserved | Killed |
| Let deferred notices replace an earlier reservation deadline | Killed |
| Include finished operations in `next_deadline` | Killed |
| Change `DEADLINE_MARGIN` from 5 ms to 250 ms | Killed by both independent bounds |
| Sleep 250 ms before expiry whenever a deadline exists | Survived, expected |
| Sleep 250 ms before expiry on every loop iteration | Killed by confirmation test; pending-expiry test passed |

Scratch scripts, per-mutation logs and `results.json` remain under `.work/fix-97/`. No files over 500 MB remain in `.work/`.

CI results for the pushed commit will be delivered in the final run report; they are not claimed by these pre-push local results. Only PR-triggered runs will be watched, with `gh run watch <id> --exit-status --interval 60`.

## Not verified

Real elapsed-time responsiveness is intentionally not measured by the stopped-clock reservation test. The conditional sleep survivor reflects this scope; no real-time waiting was reintroduced. No product or game behavior changed, so no game build or human play check applies.

## JUDGMENT-CALL

None beyond the requested independent bounds: each future-deadline fixture allows at most 10 ms beyond its reservation deadline, independently of the product's constant.

## PLAN-GAP

Known limit, REVIEW-1 finding 2, intentionally unchanged: idle checks retain a 1 s real monotonic budget and can fail at 0.5 s per fsync. The requested deadline tests do not measure actual responsiveness or maintenance cadence.

## Open questions

None.
