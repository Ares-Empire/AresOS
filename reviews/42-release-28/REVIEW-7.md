# 42 step 1: fix check round 2 (Codex gpt-6-astra high, 2026-11-17)

Checks `6948f39f` (REVIEW-5 fixes, notes in FIXES-5.md) at merged head `c39d48cc`. Read-only sandbox: test errors from temporary-file creation are environmental; the lead ran the modules locally (all OK, `c39d48cc`).

Both original findings are **fixed**.

1. **Consistently wrong record and links — fixed.** [release_diff.py:1219](os/ci/release_diff.py:1219) compares the complete group/name/public-path/target/priority mapping against the reviewed manifest. Its NEVRA and SHA-256 match both the current lock and recorded candidate lock. I independently reconstructed all four groups and twelve chains from the recorded scriptlet; they match exactly.

2. **Missing public command links — fixed.** [release_diff.py:1230](os/ci/release_diff.py:1230) checks every selected public link’s presence, type, ownership, mode, xattrs and target. Absent slave targets require both links absent. [release_diff.py:1443](os/ci/release_diff.py:1443) rejects missing or invalid groups independently of changed paths, covering an entirely missing group.

No new blocking, should-fix or nit findings in the touched code.

Compatibility: an in-memory reconstruction from the scriptlet accepted all **28 alternatives paths**, consistent with PROGRESS’s recorded dry-run shape. This includes the JVM directory links and `.1.gz` public names targeting uncompressed `.1` pages. I did **not** replay the actual image inventories; the recorded successful dry runs predate this fix.

Regression evidence: in-memory comparisons against `6948f39f^` reproduced acceptance of the consistent swap, missing public links, incorrect unchanged public ownership and missing whole group. The fixed methods rejected each. All five consistent-swap assertions and the three missing-link scenarios distinguish the old and fixed behavior.

`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s os/tests -p 'test_release28.py'` reported **85 tests, 63 errors** from read-only temporary-file setup; 22 passed. These are environmental errors, not code failures; the fixture-dependent regression tests could not execute normally. `git diff --check 6948f39f^ 6948f39f` passed. No files edited.

SAFE