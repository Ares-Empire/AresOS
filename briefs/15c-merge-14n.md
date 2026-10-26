# 15c: Take package 14's council fixes into the owner path

Follow-up on branch `pkg/15-owner-path` (PR #14, draft). Briefs 15 and 15b still apply. Read the council delta verdict (`reviews/councils/2026-10-25-install-gate/delta/VERDICT.md`, findings A and B), then `briefs/14n-council-delta-fixes.md` and the 14n section of `reviews/14-owner-tools/REPORT.md` on package 14's branch.

Package 14 fixed both defects in the tools (local commit `754cf7c` on `pkg/14-owner-tools`, in this same repository, not pushed):
- the disk helpers now use tree JSON
- every PASS line names the full action, for example `PASS layout begin us-intl`
- the payload and its fingerprint changed

**Do:**
1. **Merge, don't rebase:** `git merge --no-ff 754cf7c` into this branch. This branch is already pushed and we never force-push. Resolve the conflicts by keeping package 15's structure and carrying over 14n's content: the new bundle fingerprint, and the exact PASS lines.
2. **Every expected PASS line** in INSTALL, INSTALL-PROCEDURES, INSTALL-REFERENCE and EMERGENCY must equal what the real entry point prints for that command.
   - Extend 14n's stdout test (or the owner-path tests) so it compares every documented expected PASS line in package 15's documents with the captured stdout.
   - Fix `test_owner_path.py`'s expectations that encoded the old, nonexistent strings.
3. **Fingerprint:** every place that states it matches the regenerated manifest. The test fails on any stale copy.
4. **Run** the owner-path, equality and full owner suites in WSL, and the pinned local gitleaks over the full history.
5. **Commit locally. Don't push:** on 1 November package 14 pushes first, then this branch, fast-forward.
6. Add a short 15c section to the REPORT. Don't merge into main.

**Model:** gpt-6.1-sol, xhigh (resuming the package 15 Codex session).
