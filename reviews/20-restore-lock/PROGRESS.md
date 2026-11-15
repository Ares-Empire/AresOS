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

## Step 2 (R2: the oracle changes; stopped before the capture)

Rebased onto the lead's `e2240fca` (the storage-failure fallback of `pending` shows no other app under the lock)
before any capture; the capture and the preflight ran on heads that contain it.

### C2: the lock's three reads (`control/owner_state_oracle/model.py`, `driver.py`)

- `permitted_status`: under `record.locked`, `control_pending`, `control_notices` and `chrome_notices`
  (`LOCKED_READS`) start from `{'allowed'}` and then take the usual fault permissions (`storage_limit`,
  `storage_error`, `journal_incomplete`, `transport_error`). `restore_required` is added only when the call carries
  `lock_refused_write`. Every other call under the lock still expects `{'restore_required'}` alone.
- `Driver.observe` wraps the engine's `Store.write` for the call and sets `lock_refused_write` on the call's script
  entry when a write raises `Refused('restore_required')`. The reply is never consulted. Another refusal of a write
  is not recorded.
- With R1, no read in the sweep reaches that refusal: Mail's checks don't run under the lock, and Chrome's
  `reconcile_open_checks()` returns at once without a bridge session. The recorder is there so a future read that
  writes during the lock is permitted its refusal, and nothing else.

### D: a full disk never fails a read-only close (`control/mail_tests/storage_faults.py`, the sweep)

- Fixed in the exhaustion injector, not in `permitted_status`. `OSWrites` gains `fail_read_only_closes`
  (default `True`, so every other injector is unchanged). `Raw.close` sets `sweep.sparing` for a file that is not
  writable when that option is off, and `hit()` returns before failing while it is set. A spared hit still counts as
  a point (and as a cleanup point); only its failure is dropped. `hit()` keeps its signature because
  `control/chrome_tests/test_full_disk_reads.py`'s `FullDisk` overrides it: a first version passed a new
  `read_only=` keyword and broke that suite (local preflight at `6019410c`: shard 2 and the audit baseline red,
  `TypeError`). Fixed in the next commit; those modules pass again (27 tests) and the sweep's results are identical.
  The sweep's exhausted phase uses `OSWrites(1, mode='persistent', fail_read_only_closes=False)`.
- Why this is the narrower form: the injected ENOSPC at the Chrome reader's journal close is not only a permission
  input. Production turns it into a `storage_limit` reply (`journal_reader` records it through
  `observations.storage`). A `permitted_status` filter alone would therefore leave that reply in place and pin new
  false gaps. Measured locally on 124 exhausted cases (4 persistent points in each of 31 non-export flows): the
  filter restored D's gaps in `expiry` and `maintenance` but added a new `response.mail_accounts.status` gap in every
  sampled `restart_index` and `restart_tail` case (8 of 8). The injector change restored the same D gaps and changed
  nothing else.
- Only Python file objects opened read-only are spared. SQLite closes and `os.close` of descriptors keep failing as
  before; they were already failing at the pin and are unchanged.
- `control/mail_tests/test_owner_state_s2_effects.py` keeps its own exhausted phase with the default injector. It is
  not pinned (it asserts only that a duplicate effect is detected), so it was left as it is.

### C3 and C4: expectations unchanged

No oracle change. With R1, the lock's rows and notices become missing-only gaps as at the pin (predicted from local
samples; confirmed by the capture in "Step 3" below).

### Tests and probes

- `control/tests/test_owner_state_oracle.py`
  `StageOneFixMutations.test_restore_lock_answers_its_three_reads_and_refuses_only_their_writes` (base suite).
- `control/mail_tests/test_owner_state_sweep.py` (Mail suite, outside the CI sweep case):
  - `test_full_disk_spares_only_closes_of_files_that_were_read`;
  - `test_locked_read_records_only_a_write_the_lock_refused` (a real restore lock in the sweep fixture: an answered
    read; a lock-refused write; another refusal, which is not recorded).
- `reviews/20-chrome/mutation-audit.py`: three `restorelock-oracle-` probes on `permitted_status`, all rejected:
  locked reads refused, write refusal ignored, every call answered.
- The Mail-suite tests don't fit that harness: it runs `python3 -m unittest` with only `control` and
  `control/chrome_tests` on the path, and these modules import `control/mail_tests`. Their five removal probes ran
  ad hoc with the same rule (rejected only on an assertion failure), and all were rejected: the spare removed, the
  read-only mark removed, every close spared, the lock refusal unrecorded, any refusal recorded.
- Local runs (Mac, the step-1 venv with `jsonschema`, the managed-settings stand-in): `control/tests` oracle
  modules 146 OK; `test_owner_state_sweep` unit tests 7 OK; `test_owner_state_s2_effects` 13 OK;
  `test_owner_state_quiet` 2 OK; `test_owner_state_regressions` 6 OK. `test_owner_state_contracts` needs
  `cryptography` (Linux container only); the alterations ran in CI.

## Step 3 (capture, classification, re-pin, proof)

**Dispatches: 1 and 2 of 3 used** (dispatch 3 unused).

- Dispatch 1, capture: **43722918063** on `065275ff`. The ledger job and all 12 alteration shards pass. All 48 sweep
  and onboarding shards fail only `test_all_flows_all_storage_modes_independent_views` against the old pin, after
  writing their complete lists. `sweep (0, 0)` also fails `test_matrix_contracts`: two contract groups changed digest
  with the same count (E renumbering, as in 43702462699). The runners were busy; the run took 2 h 35 min.
- Dispatch 2, proof: PROOF-PENDING.

### Pin

`reviews/19b-owner-state/KNOWN-GAPS.json` = the capture's compact list: **2,622,072 keys / 1,997 groups / 921,711
bytes**, SHA-256 `ee326914fff6ccddcb78afbf3c346207148471f3e8b1dd0f96868a776291e68d`. 53 lists, no conflicting shared
keys, every flow's clean-run point count equal to 43702462699's. Section "Re-pin after 18d, PR #27, PR #68 and
20-restore-lock (board #185)" in `reviews/19b-owner-state/KNOWN-GAPS.md`, and its top paragraph names it the current
pin.

### Classification (previous pin 43137420989 → capture 43722918063)

| Class | Prediction | Measured | Verdict |
|---|---|---|---|
| A | +425 points, 43,624 pair-0 keys, 1,316 pair cases / 51,468 keys | +425, 43,609, 1,316 / 51,456 | as predicted; the 15 + 12 fewer keys are C2 status keys at those points |
| B | about 15,011 new / 5,571 old pair cases | 15,514 / 6,080 (823,611 keys) | explained below |
| C1 | about 6,375 + 238, closed only | 6,375 + 238, closed only | exact |
| C2 | 0 new; up to 1,246 pin keys closed or changed in the expected set | 0 new; 661 pair-0 keys (353 closed, 308 expected set only) + 585 pair-case keys = 1,246 | exact |
| C2r | small (3 in the sample), closed only | 51, closed only, all in the restore flow's exhausted phase | explained below |
| C3 | about 0 differences, missing-only | 0 | exact |
| C3e | about 10 keys per locked case, missing-only | 95,258 (66,519 new, 28,739 changed), all missing-only | explained below |
| C4 | 0 | 0 | exact |
| C5 | about 48 (44 missing-only, 2 `restore-lock`, 2 closed) | 44 + 2 + 2 | exact |
| C-pairs | hundreds of cases | 1,071 cases / 60,722 keys | as predicted |
| D | the pin's 83 gaps back, 0 differences | 0 differences; all 100 exhausted read-status gaps of `expiry` and `maintenance` present unchanged | see below (82, not 83) |
| E | 0 fixed keys changed | 0 of 377 | exact |

No `OTHER`, `SHOWS MORE`, `D`, old-only pair cases or E changes.

**Where a count differs from the prediction, and why.**
- **The alignment.** `account2.py`'s own alignment left one `UNALIGNED replace` block in the restore flow (pin 67–68
  against 73–75) and shifted restore points 54–64 by one. R1 changes the restore flow's live-phase envelope keys at
  74 and 75 (C3e and C5), and those keys are part of its signature. The capture keeps 43702462699's numbering (the
  point map from it to this capture matches all 10,247 failing points by number; only restore 74 and 75 change
  signature), so the classification uses the trace's validated pin → 43702462699 map instead. `account3.py` is
  `account2.py` with that fixed alignment; on pin → 43702462699 it reproduces `account2.py`'s counts exactly.
- **C2, 1,246.** The pin holds exactly 1,246 status keys of the three reads outside the crash phase that expect
  `restore_required`: 661 cleanup-free (336 observed `allowed`, now closed; 308 observed `storage_limit`, now changed
  in the expected set only; 17 in the restore flow, closed) and 585 in pair cases.
- **B.** The 585 pair cases that carry a C2 key were identical between the pin and 43702462699; now they differ
  ("pair cases same" 15,539 → 14,954) and are counted as B (they equal their point's own single result: +503 new,
  +509 old) or as C-pairs (+76). Total pair cases at matched points are unchanged (22,105 old).
- **C2r, 51.** 17 restore-flow points in the exhausted phase × three statuses (`control_log`, `mail_accounts`,
  `mail_filing_notices`); the local sample had one such point. Every key is closed, the reply being
  `restore_required`.
- **C3e, 95,258.** By flow, 4 to 20 keys per locked case. The local sample took about 8 cases per flow and no
  onboarding or export flow; weighted by real case counts, onboarding (1,483 locked cases, 17.2 each) and the send
  flows (20 each) dominate: 14.8 per locked case. Every key is missing-only (no fact shown that the pin did not show,
  except a count lower than expected).
- **D, 82 not 83.** Recounted: 43702462699 had lost 82 of the pin's exhausted read-status gaps (`expiry` 50,
  `maintenance` 32); all 82 are back unchanged. The trace's 83 was a miscount.

### Reviewer's C2 check (via the lead)

Every C2 status key that closes or changes outside the crash phase keeps a `restore-lock` gap at its point, unchanged
from the pin: **712 of 712**, none without.
- 644 outside the restore flow (exhausted and live-restored phases): the oracle's record says locked, the store isn't.
  Each point keeps `control_pending.restore-lock`, `passive.restore-lock`, `aresos log.restore-lock` and the reply
  envelopes' `restore-lock` (expected `True`, observed `False`). Named in KNOWN-GAPS.md as C2's mirror of C5.
- 68 in the restore flow's exhausted phase (17 C2, 51 C2r): the store now answers as locked (C1 closes
  `control_pending.restore-lock` there); each keeps its `aresos log.restore-lock` gap.
- The 585 pair-case keys sit at 360 point, mode and phase slots; each slot has at least as many pair cases with an
  `aresos log.restore-lock` gap in the capture as it had pair cases with a C2 key in the pin.

### Tools (ignored `.work/185/` of the worktree; never committed)

`r2/regen2.sh` (download and lists), `r2/account2.py` (labels), `r2/account3.py` (labels with a fixed point map),
`r2/c2check.py` (the reviewer's check), `r2/pointmap.py`, maps `r2/map-pin-cap1.json`, `r2/map-cap1-new.json`,
`r2/map-pin-new.json`. Commands, from the repo root:

```sh
bash .work/185/r2/regen2.sh 43722918063
python3 .work/185/r2/account3.py .work/185/old-43137420989-full.json .work/185/43722918063-full.json .work/185/r2/map-pin-cap1.json
python3 .work/185/r2/c2check.py .work/185/old-43137420989-full.json .work/185/43722918063-full.json .work/185/r2/map-pin-cap1.json
python3 .work/185/r2/pointmap.py .work/185/43702462699-full.json .work/185/43722918063-full.json .work/185/r2/map-cap1-new.json
```

## Records

- `reviews/20-restore-lock/records/final-local-2312fa10.json`: the full local preflight at `2312fa10` (step 2's last
  code head, with `e2240fca` and `9c2a361d`), all green: Python 340 tests in 4 shards (91, 70, 52, 127; 1 skipped),
  Node 428 tests, 0 failures, 534 removal mutations rejected with every baseline passing, `generate.py --check`,
  `git diff --check` and the service-unit pin clean. The run at `6019410c` before it was red (shard 2 and the audit
  baseline, `FullDisk.hit` `TypeError`); see "Step 2", D.
- `reviews/20-restore-lock/records/final-local-1e770483.json`: the full local preflight (`.work/20-restore-lock/preflight.py`)
  at `1e770483`, all green: Python 339 tests in 4 shards (90, 70, 52, 127; 1 skipped), Node 428 tests, 0 failures,
  529 removal mutations rejected with every baseline passing, `generate.py --check`, `git diff --check` and the
  service-unit pin clean.
- Also run locally at `1e770483`: the Chrome modules `test_committed`, `test_engine`, `test_fault_surface`,
  `test_state_fixes`, `test_questions` (118 tests, OK), and the base suite as described above.
