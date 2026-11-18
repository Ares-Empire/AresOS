# Package re-check 2: the fixes and step 2 (`801dad9a..065275ff`, Claude Opus, 2026-11-15)

**SAFE.** Both of my FIXes are closed, and the step-2 oracle changes are sound; I found nothing they hide.

## My two FIXes
- **FIX 1, the no-IMAP test (`9c2a361d`): closed.** The test no longer reads before the lock, so the older database keeps the Sent-copy check open, and it checks the session counter before `ok`. `restorelock-sent-check-runs` is now rejected by `['imap'] != []` (`test_restore_lock.py:173`) for all three reads.
- **FIX 2, the storage-failure fallback (`e2240fca`): closed.** My own two probes, rerun on `065275ff`:
  - with a stale `submitting` send and one injected EIO, `control_pending` now lists only Chrome's rows;
  - with 3 stale sends, a `background-storage` notice and no Chrome warnings, there is no `notices_more` any more (before, it named `mail_filing_notices`).
  - Both replies carry `restore_required: true` and the lock wording.
  - The two new `restorelock-fallback-` probes are rejected for their stated reasons: Mail shows up in the app set, or the lock wording is missing.

## Your three questions
- **(a) Can C2 or D hide a real gap? No.**
  - C2 only widens what the three reads may answer. Every other call under the lock still expects `restore_required` alone.
  - Where the oracle thinks the store is locked and it isn't, the disagreement is still recorded. `notice_head` checks `.restore-lock` in the reply envelope of every call (`compare.py:239`), using the same snapshot as the status check. The other read calls at those points also keep their status gaps.
  - So the up to 1,246 closed status keys only drop a duplicate symptom. That's acceptable.
- **(b) Does D spare only read-only closes? Yes.**
  - It spares only `Raw.close` of a Python file object that is not writable (`'r+'` and `'a'` still fail), and only in the sweep's exhausted phase (`OSWrites(1, mode='persistent', fail_read_only_closes=False)`).
  - A spared hit still counts as a point but never sets `failed`.
  - SQLite closes, `os.close`, writes and creates still fail.
  - The single and pair phases keep failing read-only closes with ENOSPC and EIO, so production's handling of a failing close is still exercised.
- **(c) Is the `Store.write` wrapping sound? Yes.**
  - `Store.write` is the only place a write meets the lock (`storage.py:621`), and nothing holds a captured reference to it. So an instance patch per `observe()` sees every such write.
  - `index` is taken right after `oracle.call`, which keeps it correct even if `call_index` changes later.
  - The wrapper re-raises, and `ExitStack` restores the scenarios' own `store.write` patches correctly.
  - Only code `restore_required` sets the flag, and `permitted_status` uses it only for the three locked reads.

## NOTEs (non-blocking)
- In the fallback under the lock, the `unavailable` text now says "Chrome … below are current" twice: `LOCKED_PENDING` plus the storage text. Cosmetic only.
- **Step 3:** confirm that every status key C2 closes outside the crash phase keeps its `.restore-lock` gap at the same point, and name those closures in `KNOWN-GAPS.md` next to C5. They are its mirror case: the oracle says locked, the store isn't.
- D's `sparing` flag is one per-injector flag, not per thread. That's fine for the single-threaded sweep.
- PROGRESS.md now has absolute local paths. There are earlier examples (the brief, `docs/WORKFLOW.md`, `docs/REVIEW.md`), and PROGRESS is deleted at the last step. Strip them if the privacy guard objects.

## Checked
- The diff `801dad9a..065275ff`.
- `test_restore_lock`: 5 of 5 pass.
- All 11 `restorelock-` probes, through the audit's harness: rejected, and I read each reason.
- The two new sweep tests pass, run in my own scratch venv with `jsonschema` and the repo's managed-settings stand-in.
- Three removal mutations of my own, each rejected on an assertion: the spare removed, the recorder removed, any refusal recorded.
- Scope: production code changed only in FIX 2. No personal data beyond those paths.
- Not run: the full sweep and `test_owner_state_contracts` (needs `cryptography`).

Scratch copy and scripts are in the reviewer's scratch directory (not committed) and the reviewer's scratch directory (not committed).
