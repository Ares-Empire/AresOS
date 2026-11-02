# 15d: Take package 14's final version into the owner path; ready for review

Follow-up on branch `pkg/15-owner-path` (PR #14, draft). Briefs 15 to 15c still apply.

Package 14 is merged into `main` as squash commit `79a67d2`. Since 15c (based on 14n), the tools changed in ways the owner path must show exactly. Read `reviews/14-owner-tools/REVIEW.md`, `REVIEW-2.md` and `REVIEW-3.md`, the briefs `14zzc` to `14zzf`, and the newest sections of `reviews/14-owner-tools/REPORT.md` (all on `main` now).

- **Trusted bootstrap:** a new 13-line first command. It copies the stick into a private directory and checks the literal `SHA256SUMS` fingerprint `3e2c78ebedf7789b0616e7a4f21ad791d76784667344e76e97a1fbd95115a6fd`, the exact file list and every hash with system tools, before running anything. The Windows helper checks both manifests.
- **Layout trials:** `layout begin` and `revert` change only the running console. Only `layout finish` persists the layout. **`layout abandon`** is new: it cleans up an unfinished trial from a fresh authenticated physical admin session on any boot, including retained stock.
- **Resume:** `install` and `prepare` can resume an exactly matching interrupted operation.
- **Diagnostics:** STOP diagnostics now persist under `/var/lib/ares/diagnostics` and go out with `export`.
- **Qualification:** qualification 21 passed on `3fd7916`, including a mid-trial reset. Physical install stays **NOT RELEASED** until the owner's physical gates.

**Do:**

1. **Merge, don't rebase:** `git merge --no-ff origin/main`, never force-push.
   - Keep package 15's structure: the numbered checklist, the symptom-first card, the safety gates and the state-dependent returns. Carry over 14's final content.
   - Afterwards, every path outside package 15's own documents and tests must equal `79a67d2` (`git diff 79a67d2 -- <those paths>` empty). Show the check.
2. **Owner path:**
   - The checklist shows the new bootstrap block **byte-equal** to the block package 14's tamper tests exercise, and adds a test for that equality. It also shows `layout abandon` where it applies, and the export's diagnostics.
   - The emergency card gets symptom-first entries for "it crashed or restarted during a keyboard layout trial" (log in with the confirmed layout, `layout abandon`, its exact PASS line, then the named return step) and for "a tools command stopped" (keep the screen, `export`, get help).
   - Status lines use qualification 21's completed VM scope. Keep **NOT RELEASED** and every open physical gate.
3. **Equality and fingerprint:** every documented expected PASS line equals the real dispatcher's stdout, `layout abandon` included, and every stated fingerprint equals the regenerated manifest. The tests fail on any stale copy.
4. **Run:**
   - the owner-path, equality and full owner suites in WSL, once with `-B` and once without (`PYTHONDONTWRITEBYTECODE` unset)
   - the Windows PASS Pester test
   - the pinned local gitleaks over the full history
5. **Then:** commit, push once through the privacy hook (fast-forward only, never `--no-verify`), and mark PR #14 ready for review. Don't merge. Add a short 15d section to the REPORT.

**Model:** gpt-6.1-sol, xhigh (resuming the package 15 Codex session).
