- **Should-fix — [os/tests/test_owner_update.py:1201](C:/Users/pab/AresOS-fix-update-test-leak/os/tests/test_owner_update.py:1201): persistent refusal is attempted twice, but never asserted.** If `run()` returns successfully, execution still reaches `works()`, which accepts either toolset. For example, at cut 1, removing the layout-trial check could let both attempts complete the update and this subtest pass. This gap predates the diff; the fix preserves it. **Fix:** explicitly require the expected exception on both attempts where the injected refusal applies. Distinguish cases where the check is legitimately bypassed or the injection changes nothing; a blanket `assertRaises` across every cut would be incorrect.

The claimed leak cause is correct: `works()` reaches `entry_run()`’s `skipTest()`, bypassing the former sequential `undo()`. `subTest` records the skip and continues, leaving `owner.disk_record` patched. Failures could likewise leak the `observations` and `installed_commands` patches. The new `finally` covers all three. I found no additional unprotected module-state mutation: other patches use context managers, `ExitStack`, or registered cleanup; remaining refusal state belongs to each installation fixture.

With namespaces available, both attempts remain inside the active refusal, and `undo()` executes exactly once before the final `run()`. On an exceptional exit, cleanup runs and the final run is skipped.

An exception from `undo()` can become the primary exception, but Python retains the original exception through chaining. None of these undo callbacks suppresses exceptions or raises `SkipTest`, so this cannot turn a real failure into a pass or skip.

Static review only: no Python interpreter was available, and WSL returned access denied. No files modified.

CHANGES-NEEDED