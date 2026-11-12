No findings in this diff.

At [os/tests/test_owner_update.py:1199](C:/Users/pab/AresOS-fix-update-test-leak/os/tests/test_owner_update.py:1199), `try/finally` correctly restores all three injected module patches on skips, failures, and normal completion. Both refusal attempts retain their original behavior; cleanup still precedes the final recovery run. No new exception suppression or failure masking is introduced.

The unasserted persistent refusal predates this change and remains unchanged.

Static review only; no Python interpreter is installed here. `git diff --check 6978dc3c...HEAD` passed. The supplied evidence reports successful runs with and without namespaces. No files modified.

SAFE