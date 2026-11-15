# Security re-check 2: the fallback fix (`e2240fca`, Claude Fable, 2026-11-15)

**SAFE** for the re-check of `e2240fca`.

## Why

- **Every route through the fallback is closed.** I read the patched branch (`engine.py:159-197`) and reran my experiment on a copy of `e2240fca`: lock, deferred Mail recovery notice present, `committed.sync` raising ENOSPC. The direct `control_pending` reply, its envelope, the envelope of `control_notices`, and the `app='mail'` envelope of a refused `mail_filing_notices` all list only `chrome-owner-state-unavailable`, no Mail row or notice, `restore_required: true`, and `unavailable` starting with the lock wording. Under the lock `other_total` is forced to 0, so the `notices_more` route can only be `chrome_notices` (when Chrome's own total exceeds 3) or absent; `mail_filing_notices` is unreachable. When the Chrome projection itself succeeds while another storage error fired, items are Chrome's committed rows only (the `[] if locked` clears the snapshot first).
- **Nothing changed outside the lock.** With `locked` false, the deferred loop, the items filter, `unavailable` and `restore_required` are byte-for-byte the old behaviour. Confirmed by the "after confirm, storage failure" case: Mail rows and warnings return, `restore_required: false`, route `control_notices`, as before the fix.
- **Evidence is real.** `test_restore_lock` 5 tests OK on the fix; the new test fails on the pre-fix engine (`801dad9a`'s `engine.py` dropped into the fixed tree) with exactly the stale `recovery-…:stale-send` notice in both views. All 8 `restorelock-` probes rejected on assertions (run with the audit's own case list). My extra experiments (`probe_fallbacks`, `probe_owner`) also pass; no IMAP/SMTP session opened in any of them.

## NOTE (non-blocking)

- In that fallback, `result['total']` still comes from the snapshot while `items` is emptied, so under the lock a failed projection can show `total: 2, items: []` (visible in my output). It is Chrome's count, not other-app state, and the same shape exists outside the lock when the snapshot's Chrome items are filtered out. Pre-existing, cosmetic.

## Read and ran

- `git show e2240fca` (engine, test, probes), read-only; the review worktree stays at `801dad9a`.
- Copies under the reviewer's scratch directory (not committed) (fix tree: `test_restore_lock -v`, `probes.py` for the 8 probes, `probe_fallbacks` + `probe_owner`) and the reviewer's scratch directory (not committed) (fix tree with the pre-fix `engine.py`, new test → FAILED as expected). No browser, no Chrome profile, nothing edited or pushed in the repo.

Combined verdict for package 20-restore-lock step 1 at `e2240fca`: **SAFE**, with the NOTEs from my first report standing (owner-state fallback drops the restore wording but keeps the flag; a post-confirm first-read storage failure may report `restore_required: true` from the locked snapshot, conservative; two probes share one mutation).
