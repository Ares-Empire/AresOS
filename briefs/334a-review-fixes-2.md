# 334a review fixes, round 2

`reviews/334a-bench-hosted/REVIEW-2.md` (the recheck after round 1) came back CHANGES-NEEDED. Fix on
`pkg/334a-bench-hosted`. The original brief's Rules hold. Model: Codex `gpt-6.2-sol`, effort `xhigh`.

1. **Make the release isolation checks fail closed** (must fix 1). `.github/workflows/os-image.yml` near lines 385,
   506, 619 and 733 chains absence checks with `&&` inside `bash -ec`. Bash ignores a failure before the last command
   of an `&&` list, so a present file passes. On `main` these checks stood one per line, and this branch weakened them.
   Put every assertion on its own line, or give each one an explicit `|| exit 1`. Add a regression test that extracts
   each block and proves it fails when any one listed path is present (the existing CI paths and every bench path).
2. **Condition tests that would catch a removed guard** (should fix). In `os/tests/test_bench_dispatch.py`:
   - test rehearsal values that are valid on each guarded branch, so removing the rehearsal job's bench guard fails a
     test (today only `release-28` is tried, which other predicates already exclude);
   - model the Actions status functions (`success()`, `failure()`, `always()`) in the evaluator, so adding `success()`
     to the upload condition fails a test. The upload must still work after a failed VM step when the evidence check
     passed.
3. Add REVIEW-2's Known limits to REPORT.md's Known limits. Add a "Review fixes, round 2" section with each item and
   the run IDs.

Verify: the touched test modules one at a time on the laptop; hosted `checks_only=true`; **at most 1 bench dispatch**
to confirm the passing script still passes after the workflow edit. Push, leave the PR open, never merge.
