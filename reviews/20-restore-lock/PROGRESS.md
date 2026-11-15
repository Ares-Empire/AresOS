# 20-restore-lock: progress

Brief: `briefs/20-restore-lock.md`. Trace: `reviews/19b-owner-state/REPIN-185-PROGRESS.md`, "Trace (step 2)".

## Done (step 1, R1)

While `store.locked`, `control_pending` and `control_notices` list only Chrome's committed rows and warnings and say
that other apps are unavailable until the owner confirms the restore. No continuation names a route the lock refuses,
and Mail's live server checks (`resolve_checks`, `resolve_sent_checks`) do not run. `chrome_notices`, Chrome's
committed-journal rows and everything outside the lock are unchanged.

- `control/aresos_control/engine.py`
  - `LOCKED_PENDING`, `LOCKED_NOTICES`: the two `unavailable` texts.
  - `Engine.notice_page`: under the lock, after Chrome's `reconcile_open_checks()` as before, returns
    `chrome.notice_page(args)` (the committed-journal pager) for the shared and Chrome views, and an empty page for any
    other app view. Mail's `notice:` rows, deferred notices, recovery notices and sent checks are never read or run.
  - `Engine._pending`: under the lock the SQLite operation scan is skipped (Chrome's `pending_rows()` still run), and
    the reply carries `unavailable: LOCKED_PENDING` beside `restore_required: true`.
  - `Engine.dispatch`, `control_notices`: the page carries `unavailable: LOCKED_NOTICES` under the lock. The
    storage-failure branch is unchanged.
- `control/aresos_control/definitions.py`: one sentence each on `control_pending` and `control_notices` saying what the
  lock shows. Regenerated `control/generated/control-tools.json` and `docs/control/TOOLS.md` with
  `python3 control/generate.py`; `--check` passes. Server instruction lengths are unchanged (control 1,652, mail
  2,426, chrome 4,052, all within 4,096).
- Tests: `control/chrome_tests/test_restore_lock.py` (4 tests). Each fails on HEAD's `engine.py` with an assertion.
  They build on the `test_engine.Operations` fixture plus the `ReadOnlyIMAP` fake from `test_full_disk_reads.py`,
  patched onto `Mail.transport.imap`/`smtp` with a session counter, so a test proves that no IMAP or SMTP session is
  opened. The lock is produced the way `test_operations` does: back up SQLite, write once more, restart on the older
  database.
- Removal probes: six `restorelock-` cases in `reviews/20-chrome/mutation-audit.py`, all rejected on assertions.
  Every one of the 529 probes still applies to the current source.

### The form chosen for R1, and why

"Unavailable until the restore is confirmed", in the existing reply shapes: the `unavailable` string the storage
paths already use, `restore_required: true`, and for `control_notices` the same `chrome.notice_page(args) |
{'unavailable': ...}` shape as its storage-failure branch. This is the state before PR #27 plus Chrome's current
warnings, which is what the brief prefers.

Deriving Mail's rows from the committed journal was not chosen. Chrome's projection (`chrome/committed.py`, about
230 lines) exists because PR #27 made `Store.write` record every Chrome key in a `chrome` map on each journal record.
Mail's keys are not in the journal that way: records carry Mail operations only as compacted summaries
(`operations`, used by restore), and Mail notices, filing intents and sent checks not at all. A Mail derivation would
need a new journal field or a second projection over the summaries, neither small nor as proven as Chrome's.

### What the code doesn't show

- Under the lock, `control_notices` pages Chrome's rows with the committed pager's own cursor scope
  (`['chrome','committed_notices']`), not the shared pager's. A cursor taken under the lock is stale after
  `control_restore_confirm` (`stale_reference`, "read again without the cursor"), which is right: the set changes
  when Mail's rows come back. The storage-failure branch of `control_notices` already behaves this way.
- Before this change `control_pending` under the lock with an open Sent-copy check could answer `ok: false,
  restore_required` with the stale data attached (the check's result write hit the lock; trace class C2's "read
  tries a write"). Now it answers `ok: true` with Chrome only. Chrome's `reconcile_open_checks()` can still hit the
  lock's write refusal exactly as before; that path is unchanged.
- `Engine.pending`'s `owner_state_unavailable` fallback computes a route with `all([])` when there are no other-app
  notices, which reads as `mail_filing_notices`; it never emits `notices_more` in that case (`other_total + 1 >
  len(notices)` is false), so no refused route is advertised. Left as is.
- The pending envelope of every reply (`Engine._request`, `pending: self.pending(app, ...)`) goes through
  `_pending`, so refused calls under the lock also show Chrome only (trace C3's `envelope.control_pending.*` keys).
- Local runs: the Chrome suite and the mutation audit run on this Mac with the system Python. `control/ci/base.py`
  needs `jsonschema` and the container's `/etc/claude-code/managed-settings.json`; locally it was run from a venv in
  the ignored `.work/20-restore-lock/venv` with the managed-settings stand-in from
  `reviews/20-chrome/records/post18d/mail-sweep/hostenv.py`, on this tree and on a copy with HEAD's `engine.py`,
  to compare the failing sets. Result: 311 tests; no test fails only with the fix (the five that fail only on the
  HEAD-engine copy are its client-timeout timing cases). The restore tests pass locally
  (`test_restore_older_log_rejects_earlier_ids_missing_ops_unknown`, `test_review21_pending_never_reads_...`,
  `test_restore_batches`, `test_review20_crash_after_first_restore_batch_keeps_lock_until_confirmation_finishes`).
  The local failures are the Linux-only parts: crash and archive workers started without the venv's path,
  `os.O_PATH`, `mcp_types`, root-owned boundary files. The container run on the PR is the real base result.

## Left (step 2, R2: the oracle)

- C2: `permitted_status` must allow `allowed` for `control_pending`, `control_notices` and `chrome_notices` under the
  lock, and `restore_required` when such a read tries a write.
- D: a failed read-only close must not permit `storage_limit`.
- C3 and C4 expectations stay; with R1 in they should now match or close.
- Capture, classification (only classes A, B, C1, E and the re-expected C2, C3, C4, D), re-pin, prove-green run. At
  most 3 dispatches.

## Records

- `reviews/20-restore-lock/records/final-local-1e770483.json`: the full local preflight (`.work/20-restore-lock/preflight.py`)
  at `1e770483`, all green: Python 339 tests in 4 shards (90, 70, 52, 127; 1 skipped), Node 428 tests, 0 failures,
  529 removal mutations rejected with every baseline passing, `generate.py --check`, `git diff --check` and the
  service-unit pin clean.
- Also run locally at `1e770483`: the Chrome modules `test_committed`, `test_engine`, `test_fault_surface`,
  `test_state_fixes`, `test_questions` (118 tests, OK), and the base suite as described above.
