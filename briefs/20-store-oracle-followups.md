# Empire brief 302 — 20-store-oracle-followups: the write latch, the oracle's startup blind spot, rows left at H

Lead: `linux-tools`. Written on 2026-11-17 against main `4737bb69`.
Builder: Codex `gpt-6.1-sol` xhigh or Claude Opus. This is a build brief, not a build.
The brief writer changed no product code and dispatched no workflow.

Read `AGENTS.md`, `docs/design/DESIGN.md`, `docs/design/CONTROL.md`, and
`docs/control/TOOLS-HANDOFF.md` (the table and “Restore lock merged”). Then read
`briefs/20-restore-lock-followups.md` and its `PROGRESS`, `BRIEF-REVIEW-1`,
`REVIEW-1`, `CLASSIFICATION-CHECK` and `RECHECK-1`. The startup note is in
**BRIEF-REVIEW-1:234-239**, not the later code review's findings.

**Outcome.** Fix the store's write-latch recovery and advice. Add an independent
startup obligation to the oracle. Teach it to expect an ordinary write's applied
rows at H. Keep the restore lock and app approval rules. Re-pin once, after all
three changes and their local checks.

Paths below are repo-relative. Code line numbers are at `4737bb69`.
Under `control/`, `storage.py`, `engine.py` and `results.py` mean files in
`aresos_control/`; `records.py`, `driver.py`, `model.py` and `perturb.py` mean
files in `owner_state_oracle/`.

## 1. The write latch: retry only a fully undone first append

### Verified facts

- `storage.py:719-733` admits a write, sets `write_failed`, appends its fence,
  stages the full event in SQLite, applies it, and appends its commit marker.
  Only completion clears the latch. Admission refusals happen before it is set.
- `_append`, `storage.py:553-573`, also sets the latch on failure. It tries to
  truncate and sync the journal back to its earlier offset. Even successful
  cleanup leaves the latch set. No SQLite staging has happened if this was
  `write`'s first `_append(record)`.
- `results.py:165-174` and `storage.py:779-782` remember the first storage cause.
  `ensure_writable`, `storage.py:769-777`, raises that old cause on later calls.
  `common.py:33-43` says to free storage or check the disk before retrying. That
  advice does not name the restart which the latch requires.
- Writes reach this check before app work (`engine.py:773-790`, `573-574`).
  Confirmation also reaches it (`storage.py:905-906`). Reads can encounter it
  through deferred notices or live checks. `Observations.finish`,
  `results.py:67-75`, preserves the request's first storage error over later ones.
- In a local reproduction, a failed confirm's second attempt, with faults off,
  still returned `storage_limit` and the same “Disk full … before retrying” text.
  Restart recovered the staged confirm and unlocked. A zero-byte first append
  with successful cleanup also refused the next healthy write.
- `mail_tests/test_owner_state_regressions.py:88-106` pins that last case as
  `G22-latch/assertion`. Its intended healthy retry is sound in this narrow case.

### Decision and exact change

Keep the latch once the fence may have survived or any later transaction phase
began. Free space alone cannot settle an incomplete transaction. Starting a new
one could overwrite its sequence or lose its recovery rights. A restart already
validates and recovers these bytes. Do not add live replay or retry app work.

There is one safe exception. If **the first fence append in `Store.write` fails,
and both truncation to its original offset and that truncation's fsync succeed**,
the write has not reached SQLite. Clear the latch for the next explicit request.
Keep the failed request failed. This includes zero and short writes, and a failed
fence fsync followed by successful rollback. It does not include a failed commit
marker, an index failure after the fence, or a failed cleanup.

1. Make `_append` report successful rollback explicitly on its raised failure.
   Set that fact only after truncate **and** fsync return. Consume it only around
   `write`'s first `_append(record)`. Never clear the latch in `_append` itself:
   the same method writes commit markers, including in `confirm_restore`.
2. A later call refused by a surviving latch gets `journal_incomplete`, not a
   replay of the earlier `storage_limit` or `storage_error`. Keep `storage_cause`
   for diagnosis and existing background notices. Preserve cleanup notes.
3. Give every storage refusal whose store is still latched this advice:
   “A storage write did not finish. Fix the storage problem, then ask the owner
   to restart the AresOS tool service. Check the recorded request or operation
   after restart before trying another change.” The installed unit is
   `aresos-toold.service`. Do not restart it from a tool request.
4. The **first failed request** keeps its original error code, cause and notes.
   Append the advice once, after the first-error choice in `Observations.finish`
   and before `bound_result`. A later latch refusal uses `journal_incomplete`
   with that advice. Successful reads keep their replies. Admission-only errors
   and errors after fully successful first-append rollback keep their old text.

This changes replies the owner sees. It also lets the next explicit request run
after the first-append exception above. It never retries the failed request.
Changing every failed write to retry was rejected: an applied write and a
partially staged one need recovery, not another app action.

### Tests and oracle change

- Extend `tests/test_review22_storage.py` and `tests/test_restore_batches.py`.
  Test zero/short first append, first-fence fsync, truncation failure, rollback
  fsync failure, index failure, staging failure, application failure and commit
  marker write/sync failure. Cover ENOSPC, EDQUOT, EIO and SQLite FULL/IOERR.
  Assert first error, notes, advice, latch state, unchanged bytes on a refused
  retry, and a successful explicit write after the permitted rollback or restart.
  Existing tests which expect a latch after successful first-append rollback
  must now assert the stronger healthy retry. Keep their failed-write assertions.
- For the failed final confirm, test both successful and failed marker rollback.
  First reply: original storage error with restart advice. Second confirm with
  faults off: `journal_incomplete`, lock held, no write and no new generation.
  Restart: same staged generation, unlocked, no second owner confirmation.
  Pure admission refusal remains retryable without restart. Reads, cancellations,
  background notice flushing and a read that tries to save a check need coverage.
- Keep the G22 regression's successful-next-write assertion. Once fixed, make it
  a normal passing assertion and remove its pin in the final re-pin. Keep the
  case selected by `control/ci/mail/tests.py:59-90`.
- The oracle must distinguish a fresh storage failure from a surviving latch.
  `model.py:1467-1490` currently allows `journal_incomplete` only from prepared
  events or an unmarked fence; `request_state`, `:1728-1735`, has the same limit.
  Those bytes alone miss a marker left behind after failed sync and failed
  rollback. Record the transaction phase and cleanup outcome in the test driver's
  fault trace. Derive the latch from those inputs and validated disk records.
  Never read `Store.write_failed`, the returned error, or the number of faults
  as the expected latch. Two failures do not by themselves prove a live write.
- Share that rule between status checks and request-state checks. Clear its
  running history at `Driver.restarted()`. Capture it before the failed reply's
  envelope is compared, including snapshots whose bytes did not change. Keep
  captured records immutable. Allow a latch refusal on a read only when a write
  was attempted; do not allow it on every later read. Keep the first-error rule
  when a fresh fault and a latch refusal occur within the same request.
- Add sweep assertions for the first-append rollback and failed cleanup, staged
  writes, H, and the final confirm, in live, exhausted and restarted phases.
  Include both fault modes and cleanup pairs. Test a later successful confirm
  after safe first-append rollback; its earlier interrupted-confirm flag must end.

## 2. Startup must finish a staged final confirm

### Verified facts

`storage.py:235-240` gives a pending event with `space.restoring` priority even
when startup initially finds a restore lock. `_pending_event` checks its identity
against the fence (`:448-458`); `_replay` finishes it (`:460-477`). The final batch
sets a new generation and removes `restore_pending` (`:938-942`). An intermediate
batch sets `restore_pending=True` (`:925`, `:933`); finishing that batch must keep
the lock. It is not authority to invent the remaining batches.

On the current restore flow, points 26-73 interrupt application after the final
event is staged. The clean flow has 76 points. At local samples 26, 40 and 73,
the pre-start head was 3, the last marker 5, and staged event 6 was present.
Healthy startup finished it and unlocked. Point 25 had no staged event and stayed
locked. Points 74-75 already had head 6; also cover them as controls.

The oracle reconstructs the post-start bytes (`records.py:193-245`). It remembers
only the startup rule which **adds** a lock for an unprepared fence, plus an
interrupted live confirm (`records.py:84-92`, `driver.py:102-111`). It has no
obligation saying what startup must finish. The sweep checks `store.locked` and
can issue another confirm before its final comparison
(`mail_tests/test_owner_state_sweep.py:244-249`). A test mutation which bypassed
the special staged-restore branch at points 26, 40 and 73 left store and oracle
locked together, with zero `.restore-lock` disagreements. That is the blind spot.

### Decision and exact change

Keep the store. Add a **before-start expectation**, checked immediately after a
successful start and **before any view, flush or scripted confirm**.

1. At `Driver.restarted()`, decode the captured crash bytes. Save the matching
   staged restore event's sequence, fence hash and expected changes as a startup
   obligation. Derive it from the full validated event, its restore plan and the
   recorded confirm precondition. A compact fence alone supplies no such right.
2. After binding the new Engine, compare against that saved obligation. Require
   its matching commit marker, an applied head at or beyond that sequence with
   a valid chain, and its effects. For a final batch require its exact generation,
   cleared `restore_pending` and an unlocked service. For an intermediate batch
   require completion of that batch but a retained lock and no new generation.
3. Send a named `startup-replay` proof to the same checker as the other proofs.
   Do this before the sweep's `if store.locked` branch. The obligation must not
   disappear just because a later confirm repairs the bytes. Do not merely force
   the decoder's lock to false: that would miss an unapplied batch with a falsely
   cleared lock. Preserve failed-call envelopes captured before the restart.
4. Keep decoded state and expected startup state separate. A real storage error
   during startup must fail startup, not claim readiness. Test a subsequent
   healthy restart. End an obligation only after its post-start check; do not
   carry it into unrelated later restarts. Register new record inputs in
   `perturb.RECORD_EXCLUSIONS` with a reason and tests, if stored on `Record`.

### Tests

- In `test_restore_batches`, stop just after staging a final confirm and restart
  on the captured bytes. Assert the same generation, marker, rows and unlocked
  state without another confirm. Repeat for an intermediate batch of more than
  32 changes: its replay completes, the lock stays. Test missing/mismatched event,
  an ordinary prepared write, a record-only tail, and failure during replay.
- In `test_owner_state_oracle`, build records for those cases independently of
  Store. Test obligation creation, exact effects, final versus intermediate,
  single use, and a second restart. A marker or unlocked flag alone must fail.
- In `test_owner_state_sweep`, discover the staged-final-confirm interval from
  a clean trace and pre-crash records. Exercise the interval, including current
  endpoints 26 and 73, in both modes and its cleanup pairs. Keep 25, 74 and 75 as
  neighbouring controls. The new proof must be empty on the real store and fail
  when startup skips the staged-restore branch, before any automatic confirm.
- While touching the lock tests, take `RECHECK-1`'s two test nits: give the
  alteration recompute an initially wrong lock, and table-test every
  `decoded_lock` term (pending restore, missing head, hash mismatch, behind,
  equal and ahead). This strengthens coverage without changing those rules.

## 3. Rows left at H: correct the model, keep the applied rows visible

### Verified facts

H is the 1,386 cases defined in `reviews/19b-owner-state/KNOWN-GAPS.md:602-606`.
It is a historical set of cases outside the restore flow, not a fault-point
number. N7 (`:628-638`) identifies 6,949 row/notice/count keys at 870 of those
cases in 16 flows. `CLASSIFICATION-CHECK` independently checked those counts.
The 544 N7 keys labelled `crash-restart` describe the failed call's **pre-crash
envelope**, not rows newly read after restart. There are 63,379 total keys at H;
N7 is only one part of them.

`storage.py:184-186` uses SQLite FULL synchronous mode. `_apply`, `:579-591`,
commits the changes and head in one SQLite transaction. `_finish`, `:593-599`,
does that before appending the independent marker. A failed marker leaves those
rows applied. `get` and `iter_items` read them (`:820-844`); even `iter_audit`
uses the SQLite head (`:798-815`). Ordinary startup replays the matching staged
event and finishes its marker (`:241-250`). It does not undo the write.

The decoder validates full events against their fences but puts unmarked events
only in `prepared` (`records.py:198-212`). It builds rows only from marked events
(`:237-245`). In a fresh `cancel/single/69` sample, the head was 6 and marker 5.
The store showed `failed` (cancelled); the oracle showed `reserved`. The store
was unlocked with its write latch set. The published proof's onboarding example
is at `onboarding/persistent/1439/0/exhausted/mail catalogue.total`. The local
1439 sample did not reproduce that same key; locate this boundary from the local
trace rather than assuming hosted point numbers are portable. The local clean
onboarding trace has 2,570 points, against 2,610 in the published proof. At its
first account marker, points 61 (write) and 62 (sync), the local model counted
zero catalogue rows and the store one. This independently reproduces the cause,
not the historical key or a classification of the whole pin.

### Decision and exact change

**Yes, the owner currently sees an applied but unmarked write before restart.
Keep that behaviour.** SQLite has saved the full change, the separate fence
matches it, and restart completes that same change. Hiding a cancelled operation
as still reserved, or hiding a saved account, would move the displayed state
backwards and then forwards on restart. A failed request does not mean that
nothing happened. Item 1 makes the recovery advice explicit.

Do not roll back applied rows or add another store projection. That would change
what the owner sees, add read-path and recovery work, and still could not undo a
remote effect. This recommendation changes no row replies at H. If the owner
wants those rows hidden until restart, that is a different product decision.

1. Add one oracle helper for the **visible local history**: marked events plus
   the validated ordinary applied tail. The tail must have a full staged event,
   match the last hash-checked fence and SQLite head, and be ahead of the last
   marker. A staged event with its head still behind it is not applied. Neither
   a fence alone nor an arbitrary `kv` row is evidence. Keep restore-lock views
   and restore-batch handling separate and unchanged.
2. Keep `record.committed` and the marked history exact. Retain the unmarked
   event in `prepared`. Represent applied history separately, and reconstruct
   owner rows from it. Do not add a fake commit marker to make tests pass.
   Keep archive discovery hash-qualified and rooted in marked manifests.
3. Use the helper in row reconstruction, `consistency_errors`, lifecycle row
   validation, current pending/notices/catalogues and the alteration recompute.
   `model.py:816-1229` currently validates and rebuilds from `record.events`.
   Applied claims must pass the same script, identity, effect and state-transition
   checks. Do not paste the applied rows over the validated result afterwards.
   Cancellation and acknowledgement still need the exact scripted identity;
   a `done` row still needs evidence of every required effect.
4. Separate three sequence boundaries in the driver: staged sequence for binding
   an event to its producing call, applied sequence for current local rows, and
   marked sequence for permission to start app work. The current start/end
   ranges use `max(record.committed)` (`driver.py:149-154`, `:395`, `:418`;
   sweep `:87-99`). An unmarked applied event must belong to its original call,
   not a later status read or the restart. Keep pre-command context proof based
   on marked history. Do not globally replace every committed high-water mark
   with the head or highest staged event.
5. Update `perturb.py`'s row, event and coherent mutations for the new history.
   Keep the marker set and startup inputs independent. Document the distinction
   in `owner_state_oracle/FORMAT.md` and `control/README.md`. Chrome's committed
   projection is a separate authority; do not change it.

### Tests

- Store tests: fail cancellation, acknowledgement and a small account-like write
  at the commit marker. Assert failed reply, applied row visibility, intact latch,
  and the same rows after restart. Assert no remote command is repeated. Include
  single, persistent and rollback-failure cases, and a staged-but-unapplied control.
- Decoder/model tests: marked, staged only, applied without marker, fence only,
  hash mismatch, wrong head, restored head and removed row. Show that cancellation
  and acknowledgement at the applied tail affect the proper rows and counts,
  but do not authorize another write or remote command. Corrupt the applied
  event's identity, effect evidence and claimed outcome; each must still fail.
- Sweep: `cancel`, `onboarding`, `repair`, `status`, `archive` and a send outcome
  at their discovered applied-before-marker points. Compare every public view,
  paging count and the failed call's own envelope. Include live, exhausted and
  crash phases, both modes and cleanup pairs. Keep the pre-crash envelope tied
  to its captured record. Post-restart rows must converge without a second action.
- Add applied-tail and staged-restore recordings to the alteration corpus.
  Mutating only a row and mutating row/event/fence coherently must both be tested.
  Every alteration shard must still report `slipped=0`.

## Build order and gates

Work in small commits. Record commands, outputs and case counts in this package's
`PROGRESS.md`. Never treat the old pin's “Unexpected pass” as a failed fix, or
silence it by broadening an allowed set. Explain it in the capture classification.

1. Merge current main normally. Read this brief and establish the local baseline.
   Run `test_owner_state_oracle`, `test_review22_storage`, `test_restore_batches`,
   and the sweep module's unit tests (all except its full matrix). Save clean
   flow traces and the sample described below. Test expected row/lock values,
   not just the number of recorded gaps.
2. Build item 1's store change and focused tests. Run those modules, the G22
   regression, and affected error/observation tests (`test_review23_results` and
   Mail `test_review_fixes_23`, `test_review_fixes_24`). Then build its independent
   oracle trace/status rule and run its sweep cases. Commit and record the delta.
3. Build item 2 and its pre-confirm startup check. Run its store and model tests,
   the restore sweep cases and the skipped-startup mutation. Commit. No baseline
   startup-proof gap is expected; the new check exposes broken recovery.
4. Build item 3, including lifecycle ordering and alterations. Run its tests,
   `test_owner_state_fixes_s2`, the ordinary owner contracts, quiet/regression/S2
   effect/plant suites, and the sweep's unit tests. Run the sample again and one
   local alteration shard before spending a full workflow run. Commit.
5. Run every mutation below, one at a time in disposable exports under `.work/`.
   Each baseline must pass. Each mutant must fail its named assertion, not an
   import, fixture or pin error. Restore the export between mutants. Record the
   exact patch, command and failure. Have fresh package/security reviewers and
   an independent classification checker review the resulting build.
6. Re-pin and prove as below. A later code fix invalidates the affected capture
   and proof. Required Control CI must pass twice, as `docs/REVIEW.md` requires.

For local unit tests use the managed-settings stand-in documented in
`reviews/20-restore-lock-followups/PROGRESS.md`. Put `tests` before `mail_tests`
for base tests; both contain `support.py`. Run Mail tests separately. Set
`PYTHONPATH` in the environment too, since an oracle test starts a subprocess.
Do not run installed-channel/root tests on the laptop. CI's ledger job owns them.
Do not run the OS owner modules, boot tools, mounts or sudo. No mod build is needed.

The compact sample starts with clean `restore` and `cancel`; restore points
25, 26, 40, 73, 74, 75 and pair 75:76; cancel first append, failed-cleanup pair,
staging, application and marker points (currently 1, 2, 2:3, 10, 24, 30, 67, 68, 69).
Use both modes and live/crash phases. Add onboarding's first account marker
(locally 61/62), the historical 1439 case, and discovered marker points for the
other item-3 flows. Resolve numbers from traces on the build;
never silently skip a moved point. One worker locally. Keep fixtures synthetic.

## Reviewer mutations

The names below are required test purposes; the builder records their final IDs.
The reviewer must run them, not just inspect their source.

| Mutation | Test which must reject it |
|---|---|
| Keep the latch after a fully rolled-back first fence | G22 healthy-next-write regression and first-append sweep test |
| Clear it after any append failure, including a marker or failed rollback fsync | Store marker/cleanup tests; item-1 sweep with no second effect |
| Raise the old cause on a later latched request | Two-request store test and final-confirm sweep status test |
| Remove restart advice, or replace the first error with `journal_incomplete` | Exact first/second-error tests, including cleanup notes and bounded observations |
| Infer the latch from any fault, or keep it after restart | Oracle trace table with read-only/admission faults; healthy-restart sweep |
| Bypass the special staged-restore startup branch | New `startup-replay` sweep check at 26 and 73, before another confirm |
| Skip replay but clear the lock; or append a marker without applying the event | Startup exact-effects/generation test and startup proof |
| Treat an intermediate restore batch as final, or retain an obligation for another start | Multi-batch store test and two-start oracle test |
| Ignore the applied tail and use marked rows alone | Applied-tail decoder test and cancel/onboarding H sweep |
| Treat every prepared event as applied, or ignore its head hash | Staged-only and mismatched-head decoder tests plus sweep controls |
| Assign the applied event to a later read, or accept an unscripted applied cancellation/ack | Event-to-call ordering test and coherent alteration tests |
| Use applied context to permit a remote command before its marker | Existing R2 context-before-command tests plus an applied-tail negative case |
| Copy the lock instead of recomputing it; remove a decoded-lock term | Wrong-input recompute test and full decoded-lock table |

## One re-pin, after all three fixes

The old pin is `reviews/19b-owner-state/KNOWN-GAPS.json`: 2,576,083 keys,
1,930 groups, 892,234 bytes; SHA-256
`8b27b1161505ac19eeaa41a6f1a69c95886de5da338249801963a96a083b74b1`.
Proof 43972005458 reproduced it. The historical full lists, not the compact
samples, are needed for a key-by-key classification.

Expected shape:

- `G22-latch/assertion` disappears by a passing healthy retry, not by changing
  its expectation. Other latch-caused stale-error status gaps shrink or change
  to the correct `journal_incomplete` result. Successful first-fence rollback
  may allow a later write/check that used to be refused; classify its dependent
  row, notice and hold changes separately from changes to error text.
- The startup proof adds coverage, not a new accepted gap. There should be zero
  `startup-replay` failures and still zero keys ending in `.restore-lock`.
- N7's 6,949 keys lose the false marked-versus-applied row discrepancy. A key
  can remain if it also contains another defect. Do not promise exactly 6,949
  fewer keys or erase all 63,379 keys at H. Classify closed, changed, new and
  unchanged deltas; separate alias-only changes. Include the 544 saved envelopes.
- Format 3 and strict exact-delta checking stay. There is no honest exact new
  total until capture. The other gap classes retain their semantic deltas.
  In the 377 fixed contract/G22/channel keys, only the one G22-latch key is
  expected to disappear; the other 376 stay. M14's hidden rows under restore,
  G22-rename, G22-evidence, R2, channel and unrelated lifecycle/effect gaps are
  outside scope. No unrelated gap may be relabelled as this package.

Before capture, fetch and merge main. Inspect changes since the baseline in
production, oracle, tests and workflow. Re-run affected checks and the sample.
If unrelated changes move keys, report the cause to `linux-tools` and settle
the baseline before capture. Do not bury drift in this re-pin.

The writer dispatches nothing. During the later build, a
`control-owner-oracle.yml` dispatch with `ledger_only=true` is a quick ledger
check (about 20 minutes). It runs no sweep, onboarding or alteration shard and
cannot validate items 2 or 3 or supply a re-pin. Use it only for that narrow check.

After **all fixes and mutations**, dispatch one full capture on the build branch
with `ledger_only=false`. Download all fresh lists under `.work/302/`. A strict
failure against the old pin is capture evidence, not green verification. Reject
any other test failure. Reassemble all 53 lists without conflicting shared keys;
verify the old lists reproduce the old pin before comparing them. Record every
changed key's item/phase/cause and the flow-point counts. No clean-run fault site
should move merely from these changes; any move needs its own explanation.

Regenerate using `owner_state_oracle.gaps` as `KNOWN-GAPS.md` documents. Commit
the single new pin and its classification section. Then dispatch the full proof
on that commit: about 2.5 hours, 61 jobs (ledger 1, sweep 24, onboarding 24,
alterations 12). All must pass. Its fresh 53 lists must reproduce the pin byte
for byte, and every alteration shard must have `slipped=0`. Watch with
`gh run watch <id> --exit-status --interval 60`. A 403 means wait for reset and
try once. Budget one capture and one proof; report to the lead before extras.

## What must not change; overlapping work

Replies outside these failure cases keep their codes, fields, paging, warnings
and text. Keep app approval, no-resubmission, restore-lock allow-list, Chrome's
committed reads, storage reservations and the durability order. Keep other gap
classes and all negative checks. No journal/schema migration or live service
change belongs here.

Checked after `git fetch origin` and `git merge --ff-only origin/main`, using
`git diff origin/main...origin/<branch> --stat` for both open branches:

| Work | Diff checked | Overlap |
|---|---|---|
| PR #72, `pkg/28-chrome`, `5b051f305a0f` | 73 files, +12,931/-177 | `engine.py` request wrapper gains Chrome's `call_time` scope around observations, admission and reply finishing. Keep it around the final bounded reply if this build touches that area. No storage/oracle edit in its diff. Re-run Chrome request/deadline tests after integration. |
| PR #58, `pkg/18c-image`, `537790a22185` | 43 files, +9,251/-30 | No storage/engine/oracle edit. Shared `control/README.md` changes the installed config path near line 293, away from this brief's durability text. Its daemon/launcher config paths and integration fixtures affect hosted/installed tests; keep those paths. No reason to run image or boot work for this brief. |
| PR #98, `3a5eea14`, merged 2026-11-17 | Included in the fast-forward | Does touch `engine.py:764`: qualification now uses the held object's `switches(version)`. It also changes Chrome qualification/committed reads and their tests. Keep that call and cache behaviour. No storage or owner-oracle change. |
| PR #97, `4737bb69`, merged 2026-11-17 | Included in the fast-forward | Test/CI overlap only: base workflow, `control/ci/test.sh`, integration and service-fix tests. No storage, engine or owner-oracle change. Keep its idle-loop timing and environment checks. |

These are the fetched tips, not a promise that concurrent branches will stay
still. Re-check their diffs before integration and before the final capture.

## Question for the owner

“After an interrupted storage write, should the tools say that a service restart
is needed, while continuing to show changes already saved locally? If the first
journal append was fully undone, the next request would work without a restart.”

**Recommendation: yes.** This gives useful recovery advice, keeps incomplete
writes from starting new work, and avoids hiding saved changes. H's row behaviour
stays as it is; the changed refusal text and the narrow healthy retry are the
noticeable changes. The lead takes this judgment call to the owner before merge.

## Writer's local evidence

Evidence and commands are recorded in `reviews/20-store-oracle-followups/PROGRESS.md`.
The scratch copies and prototype in `.work/302/` were treated as unverified notes.
No prototype code was adopted. In particular, “more than one fault means latched”
is not an acceptable oracle rule. The baseline tests and samples above were run
again on the fast-forwarded worktree. The full sweep and new fixes remain the
builder's work, not evidence claimed by this brief.
