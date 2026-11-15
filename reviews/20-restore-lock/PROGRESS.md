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
samples in the handover below; not yet captured).

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

## Step 3 handover (capture, classification, re-pin, proof)

**Dispatches used for R2 so far: 0 of 3.** Nothing was dispatched in step 2 (the lead stopped it before the
capture). The code to capture is the branch head, which contains `e2240fca` (lead's production fix), the R2 commits
`ad331af5` and `6019410c`, and the lead's test-only `9c2a361d`. Production code is unchanged since `e2240fca`.

### What R2 changed, in one paragraph each

- **C2** (`control/owner_state_oracle/model.py`, `driver.py`): under `record.locked`, the three reads in
  `LOCKED_READS` are permitted `allowed` plus the usual fault permissions; `restore_required` only when the driver
  recorded `lock_refused_write` (a `Store.write` that raised `Refused('restore_required')` during the call). Every
  other call under the lock still expects `restore_required` alone.
- **D** (`control/mail_tests/storage_faults.py`, the sweep's exhausted phase): the exhaustion injector no longer fails
  closing a Python file opened read-only; the hit still counts. Not a `permitted_status` filter, because the injected
  close error itself makes production answer `storage_limit`; a filter would have pinned new false gaps
  (`restart_index`/`restart_tail`, 8 of 8 sampled). See "Step 2" above for the measurements.

### Where the tools are (all ignored, never commit them)

- This worktree: `/Users/pab/AresOS-20-restore-lock/.work/185/`
  - `old-43137420989-full.json`: the pin's full list (reproduces `KNOWN-GAPS.json` byte for byte).
  - `43702462699-full.json`: the previous capture (pre-R1, same code as `a350cc8b`/`b0711d20` under `control/`).
  - `r2/regen2.sh <run>`: downloads a run (`gh run download`) into `.work/185/capture/<run>/`, writes
    `.work/185/<run>-full.json`, `<run>-compact.json` (sorted, `indent=1`, trailing newline, like the pin),
    `<run>-compact.diff` and `<run>-points.txt`, prints the compact SHA-256 and size, and checks that every flow's
    clean-run point count equals capture 43702462699 (it should: R1 changes nothing outside the lock).
  - `r2/account2.py PIN-full NEW-full`: the classification. It aligns points per flow by their cleanup-free
    signature (the trace's step-2 method: IDs, caller directories and alias numbers normalised, fact lists sorted,
    lock views and exhausted read statuses left out of the signature), then labels every differing key and pair
    case, prints counts and examples, and ends with `OUTSIDE THE INTENDED CLASSES: none` (exit 0) or the list of
    offending labels (exit 1). Validated on pin → 43702462699: it reproduces the trace's counts (9,822 matched,
    425 inserted, C-pairs 995 / 43,861 keys, C4 43 + 172, C2 3,826) and flags exactly C2, C3 (stale extras), C4
    and D, which R1/R2 fix.
  - `r2/pointmap.py OLD NEW OUT.json`: the same alignment as a point map (`matched`, `inserted`, ...).
    `r2/map-pin-cap1.json` is pin → 43702462699.
  - `r2/cases.py OUT.json FLOW/MODE/POINT[/CLEANUP] ...`: runs sweep cases locally exactly as the sweep does (live,
    exhausted for persistent, crash) and dumps their gap entries. `r2/extract.py FULL.json OUT.json PREFIX...`
    pulls the same cases from a full list. `r2/sample_check.py NEW.json MAP.json PIN-full.json` classifies a
    local sample against the pin with `account2`'s rules.
  - `r2/exp_d.py VARIANT FLOW...`: the D experiment (`none`, `P` = permitted filter, `I` = injector).
  - `r2/c5.py POINT [MODE]`: the restore flow's lock state at a point (store vs decoded record) during the compare.
  - `tree-base/`: `a350cc8b`'s `control/` (the previous capture's code), for local baselines.
  - `step2/probe.py FLOW POINT MODE [CLEANUP] [PHASE]`: the trace's single-case probe (replies and failing hits
    with call sites); patched here for the new `hit(read_only=...)` signature.
- The trace's originals stay in `/Users/pab/AresOS-19b-oracle-repin/.work/185/` (read-only). **Don't import
  `step2/index2.py`**: it runs at import and overwrites `sys.argv[1]` with a pickle (it clobbered a copy here once;
  restored from the original).
- Local runs: cwd `control/mail_tests`, interpreter `.work/20-restore-lock/venv/bin/python3` (has `jsonschema`),
  `PYTHONPATH=<tree>/control:<tree>/control/mail_tests:/Users/pab/AresOS-20-restore-lock/.work/185/r2`
  (`probe_env.py` there stubs the root-owned managed settings). Export flows (`attachment_export`,
  `testapp_export`, `export_rollback`) and `onboarding` don't run locally; contracts need `cryptography`.

### How local runs were checked against CI

The 13 cases `cancel/single/3`, `cancel/persistent/10`, `settlement/persistent/83`, `archive/persistent/2`,
`expiry/persistent/2`, `maintenance/persistent/2`, `status/single/55`, `restore/single/75`,
`restore/persistent/75`, `repair/persistent/2`, `send/single/5`, `send/persistent/300` and `filing_move/single/166`
were run with `cases.py` on `tree-base` and compared with the same keys extracted from 43702462699: 832 of 832
keys identical, none missing or extra. Local runs therefore stand for CI for these flows. Then on the R2 tree:
218 locked crash cases across all non-export flows, 140 persistent cases and 80 cleanup pairs, all inside the
classes below.

### Procedure for step 3, in order

1. Wait for the runs the lead names to finish (in step 2: PR #77, head `7e69bfdc`; one background `until` loop
   with `sleep 120` on `gh run list -R Ares-Empire/AresOS --commit <sha> --json status`).
2. Dispatch 1 (capture): `gh workflow run control-owner-oracle.yml -R Ares-Empire/AresOS --ref pkg/20-restore-lock`.
   Find it with `gh run list -R Ares-Empire/AresOS --workflow control-owner-oracle.yml --branch pkg/20-restore-lock
   --limit 1 --json databaseId,headSha,status`; watch with at least 60 s between `gh` calls. Expected: the ledger
   job and all 12 alteration shards pass; the 48 sweep/onboarding shards fail strictly against the old pin after
   writing their complete lists (as in 43702462699); a contract shard may fail `test_matrix_contracts` on the
   E renumbering, as before. Anything else failing: diagnose, report, don't retry.
3. From `/Users/pab/AresOS-20-restore-lock`: `bash .work/185/r2/regen2.sh <run>`. Expect 53 lists and equal
   clean-run points.
4. `python3 .work/185/r2/account2.py .work/185/old-43137420989-full.json .work/185/<run>-full.json`. It must end
   with `OUTSIDE THE INTENDED CLASSES: none`. Also `python3 .work/185/r2/pointmap.py .work/185/43702462699-full.json
   .work/185/<run>-full.json .work/185/r2/map-cap1-new.json`: expect only matched points (same numbering).
5. **Stop rule:** any `OTHER`, `UNALIGNED`, `SHOWS MORE`, any `D ...` line, `pair cases old-only`, or E fixed keys
   changed stops the step before the re-pin; report the labels and examples to the lead and don't pin. Also check
   that every `C2r` key is in the restore flow's exhausted phase (`account2.py` already makes any C2r key that is not
   closed an `OTHER lock status` line); a C2r key elsewhere also stops the step.
6. Re-pin: `cp .work/185/<run>-compact.json reviews/19b-owner-state/KNOWN-GAPS.json`; confirm
   `shasum -a 256` and `wc -c` match regen2's output. Add a KNOWN-GAPS.md section "Re-pin after 18d, PR #27, PR #68
   and 20-restore-lock (board #185)": keys, groups, bytes, SHA-256, the run ID and head, the regenerate commands
   (regen2's three `owner_state_oracle.gaps` steps, as in the earlier sections), and the class table below with the
   measured counts and commits. Commit with `[skip ci]`, push.
7. Dispatch 2 (proof) on the same branch: it must be green (all 61 jobs). Record its run ID in KNOWN-GAPS.md and
   here. Dispatch 3 stays spare.

### Expected classes (pin → new capture), with the lead's rulings

Labels are `account2.py`'s. Predictions come from the samples and from the pin → 43702462699 counts.

| Class | What it is | Commits | Prediction |
|---|---|---|---|
| A | new fault sites (index pages) | `c5810bb0` | as the trace: +425 points, 43,624 pair-0 keys, 1,316 pair cases / 51,468 keys |
| B | pair cases equal to their point's own single result (Chrome journal close after each fault) | `3bf1b0d2`, `f3cfd5b1`, `4d80ea38` | about 15,011 new / 5,571 old pair cases, as the trace |
| C1 | `restore-lock` gaps closed (control_pending answered during the lock) | `f3cfd5b1`, `994b6e8f` | about 6,375 + 238 (restore flow), closed only |
| C2 | the three reads' status under the lock: back to no gap | R2 `ad331af5` | 0 new. Also closes pin gaps where the oracle's record is locked but the store isn't (exhausted/live-restored): up to 1,246 pin keys (666 observed `allowed` close; 580 observed `storage_limit` close or change in the expected set only, labelled "expected set only"). The `restore-lock` gap at those points stays. |
| C2r | **Allowed (lead's ruling).** Reads the lock refuses now answer with the lock's refusal first: R1 no longer reads other apps' storage during the lock, so on the full disk those reads answer `restore_required` instead of `storage_limit` and the pin's gaps close. Allowed form: keys in the restore flow's exhausted phase whose gap closes, the reply being `restore_required` for a route the lock refuses. Not allowed: a C2r key that opens a gap or changes to anything but closed. Name it in KNOWN-GAPS.md as "C2r, closed by R1" with its count. | R1 `1e770483`, `e2240fca` | small (3 in the sample); closed only |
| C3 | control_pending rows and notices during the lock | R1 | back to the pin's M14 "rows missing": about 0 differences vs the pin; any key must be missing-only |
| C3e | envelopes and passive views during the lock: Mail rows/notices now missing (lead: "C3 (envelopes)", every key missing-only) | R1 | about 10 keys per locked case (2,328 in 218 sampled cases), all missing-only; tens of thousands in all |
| C4 | continuation to a refused route | `3389d862`, fixed by R1 | back to the pin: 0 new or changed |
| C5 | restore flow last point (pin 68, now 75), persistent mode | pre-existing | about 48 keys (44 missing-only envelope/notice keys, 2 `restore-lock`, 2 closed) |
| D | exhausted reads after a background storage failure | R2 `ad331af5` | the pin's 83 gaps are back: 0 differences vs the pin |
| E | identity renumbering | `baed6679` | 0 fixed keys changed after normalisation |
| C-pairs | pair cases that equal an old pair case outside the lock views | follows C1–C5 | hundreds of cases |

**C5, what disagrees.** At the restore flow's last fault point in persistent mode, the final restore commit
marker is written, its fsync fails, and the cleanup truncate fails too (persistent fault), so the unsynced marker
stays in the journal. The decoded state the oracle reads (and a restart) says the restore is confirmed: unlocked.
The running store keeps its in-memory lock and `write_failed` until restart, so it answers
`restore_required: true`. In single mode the truncate succeeds and both sides agree the lock holds. The gap
predates this package (the pin and 43702462699 already had the `restore-lock` disagreement there). R1 only adds
the missing-only envelope and notice keys. Whether the store's lock there is right (oracle drift) or a production
question: **not decided; for `linux-tools`.** The facts: the store refuses everything until restart either way,
and cannot know whether the marker is durable.

## Records

- `reviews/20-restore-lock/records/final-local-1e770483.json`: the full local preflight (`.work/20-restore-lock/preflight.py`)
  at `1e770483`, all green: Python 339 tests in 4 shards (90, 70, 52, 127; 1 skipped), Node 428 tests, 0 failures,
  529 removal mutations rejected with every baseline passing, `generate.py --check`, `git diff --check` and the
  service-unit pin clean.
- Also run locally at `1e770483`: the Chrome modules `test_committed`, `test_engine`, `test_fault_surface`,
  `test_state_fixes`, `test_questions` (118 tests, OK), and the base suite as described above.
