# 334a review fixes, round 1

Package 334a (`briefs/334a-bench-hosted.md`, PR168) came back CHANGES-NEEDED from
`reviews/334a-bench-hosted/REVIEW-1.md`. The OS lead (`linux-aresos`) added one should-fix and chose how the guarded
refs are handled. Fix these on `pkg/334a-bench-hosted`. The original brief's Rules all still hold.

Model: Codex `gpt-6.2-sol`, effort `xhigh`.

## Must fix

1. **The launch nonce must not reach the evidence** (REVIEW-1 must fix 1). Keep the real credential out of every
   exported guest output: don't run `exec` in a way that lets its output carry the runtime file's nonce, and make the
   evidence check refuse both a bare nonce and the `ARESOS_LAUNCH_NONCE=…` form. Add regression cases for both forms
   with a synthetic value.
2. **The health probe must not displace the desktop** (REVIEW-1 must fix 2). Don't authenticate as the desktop. Use a
   bench-provisioned identity that is authenticated and non-displacing for the read-only `list_apps` request, set up
   only in the bench layer (never in `os/config`). Prove in a test that an existing desktop connection survives the
   probe. If the helper offers no such identity, say so in `PROGRESS.md` and the report and stop before changing
   `os/config/usr/libexec/aresos-shell`. The helper belongs to another lead.
3. **Bench refuses ledger-managed refs** (REVIEW-1 must fix 3; the OS lead's choice). Release ledgers must keep seeing
   every run on their refs, so don't teach any guard to skip the bench title.
   - Take the list of ledger-managed refs from the guards' own data (the branches in `os/ci/rehearsal-packages.json`,
     including `pkg/331-release-29`), not a hand-written copy, so a new release branch is covered automatically.
   - Refuse twice: in the bench client before it dispatches, and in a fail-fast job guard in the workflow. Add a test
     for each.
   - Add a Known limit: a stray manual bench run on such a ref stays in its history. On `pkg/331-release-29`, R29's
     ledger counts an unknown title as rejected and charges its minutes, so it costs budget but doesn't block.
     Deleting such a run is the lead's decision, never a routine step, because it removes evidence.

## Should fix

4. **Bench keeps every release exclusion** (`linux-aresos`). The check-build job's condition now reads
   `(inputs.check_build == 'bench' || (inputs.check_build != '' && !inputs.rehearsal && !inputs.release_13 …))`.
   With bench, that skips the `rehearsal`, `release_*` and `dry_run_*` exclusions. Apply the same exclusions to bench,
   so a bench dispatch never combines with a release, dry-run or rehearsal flag.
5. **Tests that check the real conditions** (REVIEW-1 should fix 2). `os/tests/test_bench_dispatch.py` must check the
   effective job conditions and the condition on the bench upload step itself, so a bypassing `||` or an upload gate
   on the wrong step fails the test.
6. **An environment allow-list for `qemu-img` and QEMU** (REVIEW-1 should fix 1; `os/ci/bench/driver.py` near lines
   39 and 48). Pass only what they need, never the runner's whole environment.

## Verify

- Run the touched `os/tests/test_bench_*.py` modules one at a time on the laptop.
- Hosted: one passing bench dispatch and one broken-helper dispatch, with the same acceptance as the original brief,
  plus `checks_only=true`. Use **at most 3 more bench dispatches** in this round.
- Add a "Review fixes, round 1" section to `reviews/334a-bench-hosted/REPORT.md`: each item, what changed, the new run
  IDs.
- Push, and leave the PR open. Never merge.
