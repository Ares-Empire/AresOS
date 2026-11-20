# Empire brief 317 — 20-store-oracle-reads: the notice left after a finished replay (N8), reads refused while a notice stays queued (N9)

Lead: `linux-tools`. Written on 2026-11-20 against main `897f2717`.
Follow-up to brief 302; it closes board T386.
The code was read at `4442c676`; `control/`, `reviews/` and `.github/` are the same in both.
Builder: Claude Opus, one fresh agent per step; the lead picks the model at launch.
This is a build brief, not a build. The writer changed no product code and dispatched no workflow.

Read `AGENTS.md`, `docs/design/CONTROL.md` (section 4 and "The bar") and `control/README.md:185-202`.
Then brief 302 (`briefs/20-store-oracle-followups.md`) and, in `reviews/20-store-oracle-followups/`,
`REPORT.md` and `CLASSIFICATION-CHECK.md`: its N1 is our N8; its N3, C3 and part of N4 are our N9.
Then the two "Named class" sections in `reviews/19b-owner-state/KNOWN-GAPS.md:706-757`.

**Outcome.** Two store changes, no oracle change, one re-pin.
- N8: start-up drops a queued recovery notice when its replay finished the notice's source.
- N9: a read is answered again when its request met a storage refusal before dispatch. Writes stay
  refused. The owner set the goal (board T385, 2026-11-19: "Merge, fix reads later").

Paths are repo-relative. Line numbers are at `4442c676`. Under `control/`: `storage.py`, `recovery.py`,
`engine.py`, `results.py` are in `aresos_control/`; `model.py`, `driver.py`, `compare.py` are in
`owner_state_oracle/`.

**The bar (decision 24, `docs/design/CONTROL.md:348`), for the builder and every reviewer.**
Reasonable safety for an MCP service, not every edge case. Real harm gets fixed: a repeated send or
delete, a write or app effect in a request that met a storage failure, a lost owner change, a hidden
warning or unknown outcome, unsaved state shown as saved. A low-harm edge case becomes one line under
"Known limits" in the report, not another fix round.

## 1. N8: a queued recovery notice the replay made untrue

### Verified facts

- Start-up collects unfinished work twice: before the replay (`storage.py:214-215`) and after it
  (`:276-277`). Both passes call `recover_intents`, which queues up to three recovery notices in
  memory (`recovery.py:131-140`).
- Between the passes start-up replays a staged event: `_replay` is called at `storage.py:239`, `:250`
  or `:257`. It applies the event and appends its commit marker (`:460-477`, `:597-603`). If that
  fails, start-up fails (`:281-284`).
- The second pass only adds. A notice queued before the replay stays queued when the replay finished
  its source, and `flush_notices` saves it (`recovery.py:141-143`). It can be saved even earlier:
  the first `submitting` to `unknown` write (`storage.py:270`) flushes the queue through
  `recorded_write` (`results.py:194-195`).
- Only Chrome is spared. The first pass does not queue Chrome's notices (`recovery.py:134-138`), and
  a queued Chrome proposal is dropped once its operation is `done` or `failed` (`:118-126`).
- The model expects a recovery notice exactly for a row that is unfinished now (`model.py:490-508`).
- Reproduced on the base engine: stop a testapp send after staging its last of five writes (the
  `sqlite_prepared` checkpoint, `storage.py:744`) and restart on the copied bytes. The operation is
  `done`, and a saved notice says "An approved operation or local repair is unfinished. Delivery …
  may already have happened". After the fourth write the operation is `unknown` with the same
  notice, correctly.
- **A second effect, not counted in N8.** A filing's queued notice has the filing's own id
  (`recovery.py:35`). So has the filing's exact warning (`warnings.py:25`, `:34`). When the replay
  finishes the filing's own last write, the flush overwrites the exact warning ("The special folders
  changed while Claude was moving these messages. …") with the generic text ("Filing roles and
  locations are not yet checked. …", `recovery.py:89-91`). The row is then `partial` without
  `check_open`, so no later check repairs it (`mail/filing.py:164-169`). Reproduced with the sweep's
  own `exercise('filing_move', 250, phase='crash')`; locally that write is applied at points 242-283.

### Decision

**The store changes. The model is right.**

1. The notice is untrue. The staged event is the service's own record of the outcome. Start-up
   checked it against its fence (`storage.py:244-245`, `:448-458`) and applied exactly that event.
2. A crash a moment later, once SQLite has applied the same event, shows no notice today: the first
   pass already finds the source finished. The lost reply is the same in both cases.
3. For a filing the queued notice hides the exact warning. That is real harm by the bar.
4. Start-up already does this for Chrome.

Teaching the model to expect the notice would pin an accident of start-up's order.

**When a queued notice may be dropped.** Right after a `_replay` call in `Store._initialize` returns,
and before any later start-up write, drop a queued notice only if all three hold:

1. It is in `store.deferred_notices` under the action `control_intent_recovery`.
2. Its source key (`source_key`, `recovery.py:106`) is a key of the replayed event's `set`.
3. After the replay, `recovery.unfinished(store, keys={source})` (`recovery.py:14-46`) no longer
   yields that source. Use that function. Do not write a second list of finished states.

Everything else keeps its notice:

- a source the replayed event does not set;
- a source the replay leaves unfinished: an operation that stays `submitting` (start-up turns it
  `unknown`, `storage.py:262-270`) or becomes `partial` or `unknown`, a filing still `started` or
  with `check_open`, an account not onboarded, an intent or export still present;
- a record-only tail: nothing is replayed and the store locks (`storage.py:245-248`);
- a failed replay: start-up fails, the queue dies with the process, the next start decides again;
- a `notice:` row that is already saved: this change never deletes a saved row;
- a legacy-intent source (`recovery.py:48-63`);
- a source that cannot be read: keep the notice, or let start-up fail as any start-up read does.

The rule is the same after each of the three `_replay` calls, the staged restore batch included.
`confirm_restore`'s own call (`storage.py:958-959`) is not a replay and does not change. Chrome's two
rules stay. Leave `store.startup_intents` alone: `recovery_notices` reads each source's current row
again (`recovery.py:73`), so a finished source yields nothing, on reads and on later writes
(`storage.py:650-658`).

Rejected: not queueing before the replay at all, as for Chrome. `confirm_restore` queues through the
same function, and with more than three unfinished sources start-up would save different notices.
The drop removes the untrue notice and moves nothing else.

### Tests

The names are purposes; the builder records the final ids.

Store, testapp (`tests/test_review22_storage.py` or `tests/test_restore_batches.py`):

- **a.** Dropped. Stop after staging a send's last write and restart on the copied bytes. The
  operation is `done`. No `notice:` row and no queued notice exist for it. `control_pending` and
  `control_log` show no recovery notice. A later ordinary write adds none.
- **b.** Kept; each asserts the saved notice.
  1. Stop after staging an earlier write: the operation stays `submitting` and becomes `unknown`.
  2. Two unfinished operations (write the second row directly); the replay finishes one. The other
     keeps its notice. The finished one has none, although the `unknown` write flushes the queue
     before the second pass.
  3. The replayed event sets the operation `partial`.
  4. A record-only tail: the store locks; after the confirm the operation is listed as `unknown`.
  5. The replay fails at its marker: start-up raises, the bytes hold no new notice, and a healthy
     restart then applies the same rule.
  6. A `notice:` row saved by an earlier start-up for the same source survives.
  7. An unfinished source the replayed event does not set.

Mail (`mail_tests/test_review26_recovery.py`):

- **c.** A filing's own last write is staged and not applied. After restart the saved notice is the
  filing's exact warning with its location pages, and the generic text is absent. The call's intent
  keeps its recovery notice: its completion was never staged.
- **d.** The intent-removal write is staged and not applied. After restart no recovery notice
  exists for the intent, and the filing's notice is intact.
- **e.** Chrome's recovery tests pass unchanged.

Sweep (`mail_tests/test_owner_state_sweep.py`): discover from each clean trace the points where the
call's last event is staged and not yet applied, as 302's tests discover theirs. In `send`,
`delete_permanent`, `attachment_export`, `filing_move` and `flag`, both modes, crash phase: no key
at those points has a `recovery` fact the model does not expect, and the `startup-replay` proofs
stay empty.

## 2. N9: a read is answered while its request is barred

### Verified facts

- `Engine.request` flushes the queued notices before dispatch, for every request but the two owner
  actions, and records a failed flush (`engine.py:751-758`).
- The flush is a `Store.write`. Under a surviving latch `ensure_writable` refuses it with
  `journal_incomplete` and the restart advice before any byte is written (`storage.py:620`,
  `:782-791`). On a fresh fault its first fence append fails and is undone (`:729-739`).
- `recorded_write` makes that refusal the request's first error and sets the request barrier, for
  every storage refusal in a request (`results.py:188-190`). The first-fence case sets it itself
  (`storage.py:736-737`).
- `_admitted_request` raises the barrier as its first statement, for every request
  (`engine.py:776`). The reply is the refusal with the passive all-app pending section (`:792-794`).
  `finish` adds the advice while the store is latched (`results.py:84-88`). There is no `data`.
- Without that gate a read still cannot write. `ensure_writable` raises the barrier before it looks
  at the latch (`storage.py:783-784`), and every write path calls it: `Store.write` (`:620`),
  `admit_history` (`:766`), `require_index` (`:526`), `confirm_restore` (`:920`), `Engine.submit`
  (`engine.py:333`), `reserve` (`:288`) and the blob stores (`:50`).
- Who queues a notice: a filing (`mail/filing.py:360-362`), a rename (`:111-113`), expiry
  (`engine.py:268-273`) and maintenance (`daemon.py:122-124`, `:134`, `:236`, `:267-269`) through
  `background_error` (`engine.py:237-250`), and start-up (`recovery.py:139`). Pages already list
  queued notices and their location pages (`mail/filing.py:263-271`, `:316-323`).
- A queued notice lives in memory, and while latched the background loop does not flush
  (`engine.py:260-261`, `:276-277`).
- The model needs no change. `permitted_status` allows only `journal_incomplete` when a write check
  met the latch first, and the storage codes for a fresh fault (`model.py:1477-1497`). The views read
  `data` whatever `ok` says (`compare.py:117-125`, `:255-357`).
- Before 302 such a read was answered with the error attached: `finish` sets `ok` false and keeps
  `data` (`results.py:77-81`).
- Reproduced on the base engine: fail a cancel at its commit marker and queue a notice. Every later
  request, reads included, gets `journal_incomplete` with the advice and no `data`.

### Decision

**A plain read that meets the barrier gets the refusal it gets today, plus its page.**

1. **Plain reads.** A request is a plain read when `requests.changing(request)` is false
   (`requests.py:28-32`) and its action is not an asking read (`definitions.py:66`). Today those are
   the methods `tools` and `pending` and a `call` of a `read` action other than
   `chrome_read_typed_fields`, which spends an approval through `Engine.submit`
   (`chrome/adapter.py:884-889`). Every other request meets the gate as today, with zero dispatch.
2. **`_admitted_request` changes.** It validates the envelope, classifies the request, and raises the
   barrier only for a request that is not a plain read. A plain read that arrives with the barrier
   set is dispatched through `_request`. Its reply then takes the passive all-app pending section the
   refusal has (`self.pending(resolve_checks=False)`, `engine.py:794`) in place of its app's own. The
   read itself runs as it does today on a latched store with nothing queued, live checks included:
   add no passive mode. The mutating branch, the error paths and the `finally` stay.
3. **`recorded_write` does not change.** It keeps setting the barrier for every storage refusal. The
   barrier is what refuses the read's own writes and what marks the reply. `Engine.request`,
   `Store.ensure_writable` and `Observations.finish` do not change either.
4. **The flush.** It runs once before dispatch, as today, for reads too. When it fails the notice
   stays queued and nothing retries it in that request. Without a latch the next healthy request
   saves it. Under a latch nothing can, and the restart drops the queue ("Known limits").
5. **What a read shows.** Saved state only: SQLite's applied rows (`storage.py:834-899`), today's
   audit events up to the SQLite head (`:812-829`), Chrome's committed projection. Never a staged
   event that is not applied, the failed write's intended rows, or the result of a check that could
   not be saved: the notice says "not yet checked" (`mail/adapter.py:807-813`) and
   `operation_status` adds `evidence_error` (`engine.py:646-650`). The one unsaved thing it shows is
   what a healthy page already shows: a queued owner warning and its location pages. A reply that
   shows a warning still queued is never `ok`: its request tried the flush and failed.
6. **What the reply tells Claude.** `ok` is false. The error is the request's first storage error:
   `journal_incomplete` with the restart advice when the flush met a surviving latch, or the fresh
   cause (`common.py:38-43`), with the advice only if the store is latched afterwards. `data` is the
   page; a read that fails for its own reason has none, and the storage error still comes first.
   `pending` lists what waits in every app and its newest three notices, queued ones included. The
   proxy hands Claude the whole reply (`proxy.py:250-251`); `aresos control log` prints it
   (`cli.py:75`). No new field and no new text: `COMMON_INSTRUCTIONS` already says "Storage failures
   return ok=false and the first storage error" (`definitions.py:52`), and Chrome's instructions
   have 3 characters left.
7. **The five flows and the N4 share.** One rule covers them. The gate does not ask who queued the
   notice: `filing_copy`, `filing_move`, `filing_rename`, `expiry`, `maintenance`, or start-up. The
   background-storage notice returns to the page because the page lists queued notices.

Why the refusal's pending section: the model expects the all-app section in every reply that
carries a storage error (`driver.py:492-493`), and the Stop hook reads that section from a reply
that is not `ok` (`hooks.py:132`). With its app's own section a `control_log` read lists no
operation.

Rejected: a "writes are paused" field on every read during a latch. It needs a reply-schema change,
instruction text there is no room for, and a model rule 302 decided against ("do not allow it on
every later read"). A read with nothing queued shows nothing unsaved, and the first change says it.

### Tests

Mail (`mail_tests/test_review_fixes_24.py`). Run every case in two states, each with a queued
notice: a fresh first-fence failure (store not latched: `storage_limit`, no advice) and a surviving
latch (`journal_incomplete` with the advice).

- **a.** Answered: `mail_accounts`, `control_pending`, `control_log`, `mail_filing_notices`,
  `mail_operation_status` and the methods `pending` and `tools`. `ok` is false. `error` and
  `pending` equal those of the refused change in b; assert that `pending` lists an operation of
  another app. `data` is present and shows the queued notice where the page has notices. The
  notice is still queued. Journal and SQLite bytes are unchanged. No SMTP command and no IMAP
  mutation happened.
- **b.** Still refused, with no `data` and zero adapter calls: `mail_operation_cancel` (the
  operation stays `reserved`), `mail_send` with its approval (zero DATA), `mail_move`,
  `mail_compose`, `upload`, `download`, `saved`, `mail_account_add` and the asking read. A table
  over every action in `definitions.ACTIONS` compares the plain reads with an explicit list in the
  test, so a new action forces a decision.
- **c.** Under the latch three reads in a row answer the same. After a restart reads are `ok` and
  a write works.
- **d.** Not latched, fault gone: a new request saves the notice, and reads are `ok`.
- **e.** A read's own write is still refused. With the barrier set and the store not latched, a
  live `control_pending` whose Sent-copy recheck tries to write changes no byte and shows "not yet
  checked". The existing `where='admitted'` case still passes.
- **f.** Saved state only. Stop a write after staging, keep the latch, queue a notice.
  `control_pending`, the operation's status and `control_log` show the row as SQLite has it and no
  audit entry for the staged event. After a restart they show the replayed write.

Base (`tests/test_review23_results.py`): an answered read whose page plus pending exceed the limit is
bounded like any reply and keeps error, advice and warnings.
Sweep: at discovered points of the five flows, in the `live-restored` phase, the status checks of
`control_log` and `control_pending` pass, and no `aresos log.total` or `control_pending.total` key
pins a count of 0 against the model's count. `WriteLatchSweep302` stays green.

## Existing tests that pin today's behaviour

- `mail_tests/test_review_fixes_25.py:44-61` asserts "no `data`" and fails with the change. Restore
  the page assertion it had before 302 (`data.untrusted_content.fragments[0].offset > 0` during the
  fault). Keep `ok` false, `storage_limit`, "Disk full", no advice, the queued notice, and 302's
  healthy retry.
- `mail_tests/test_review_fixes_24.py:189-208`
  (`test_failed_predispatch_flush_blocks_reads_and_cancellation_until_next_request`) passes before
  and after: it never asserts the missing page. Replace it with tests a to d and rename it.
- The strict sweep test (`test_owner_state_sweep.py:642`) needs only the new pin.
- No other test should change. With a scratch prototype of both rules, of 29 base tests, 53 Mail
  tests and the sweep module's 16 unit tests only the review 25 test failed (writer's evidence).

## Build order and gates

Small commits. Keep `reviews/20-store-oracle-reads/PROGRESS.md` current: commands, outputs, counts.

1. **Baseline.** Merge main. Run the modules of the test sections as they are. Record the local
   matrices (below) on the merge base under `.work/317/before/`.
2. **N8.** The rule, tests a to e, its mutations. Commit.
3. **N9.** The gate, tests a to f, the two changed tests, its mutations. Update
   `control/README.md:193-202`: a barred read is answered from saved state with the error attached;
   start-up drops a recovery notice its replay made untrue. Commit.
4. **Local gate.** Record the matrices again and compare key by key with step 1. Run
   `test_owner_state_capture` (3 tests), the sweep's unit tests and one alteration shard. Push.
5. **Review.** A fresh package and security review runs the mutations before any hosted oracle run:
   a later code fix voids a capture.
6. **Capture, re-pin, proof** as below, then the independent classification check.

**Local matrices**, with the sweep's own `exercise` and `Gaps(recording=True)`, one worker:
- live phases, both modes, every point: `filing_move`, `filing_copy`, `filing_rename`, `expiry`,
  `maintenance`, `restore`;
- crash phase, both modes, every point: `filing_move`, `attachment_export`, `flag`,
  `delete_permanent`, `send`, `cancel`, `restore`, `restart_index`, `restart_tail`.

About 80 seconds per 700 cases on the laptop. The gate passes when there is no new key, every
`crash-locked` key is identical, and every change is a closure, an alias-only renumbering, or one of
the shapes under "Expected direction". Compare with paths normalised: export flows carry the
checkout's path.

For local runs use the managed-settings stand-in, the `PYTHONPATH` order and the export location of
brief 302 ("Build order and gates", its last three paragraphs), with `317` in place of `302`. No
installed-channel or root tests on the laptop, no `os/tests` owner modules, no mounts, no sudo.

## Reviewer mutations

The reviewer runs them one at a time in a disposable export. Each baseline passes. Each mutant fails
its named assertion, not an import, fixture or pin error.

| Mutation | Test which must reject it |
|---|---|
| Start-up as on main: no drop | N8 a and c |
| Drop every queued recovery notice after a replay | N8 b1, b2, b7 |
| Drop before the replay, or although the replay raised | N8 b5 and b1 |
| Decide by a list of states that calls `partial` or `unknown` finished | N8 b3 and b1 |
| Drop only in the second pass | N8 b2 |
| Delete a saved `notice:` row | N8 b6 |
| Remove the gate for every request | `test_failed_predispatch_flush_blocks_effect_until_next_request` (zero SMTP DATA) |
| Keep the gate for reads, as on main | N9 a and the review 25 test |
| Treat the asking read or a transfer method as a plain read | N9 b |
| Check the barrier only at the gate, not in `ensure_writable` | N9 e |
| Let `recorded_write` set the barrier only for an undone first fence | N9 a under the latch (the pending section) |
| Keep the app's own pending section on an answered read | N9 a |
| Answer a barred read `ok`, or drop the advice | N9 a and c |
| Drop the queued notice when a read is answered | N9 a (still queued) |
| Serve a read from the staged event or the failed write's rows | N9 f |

## One re-pin, after both changes

The pin is `reviews/19b-owner-state/KNOWN-GAPS.json`: 2,420,003 keys, 1,860 groups, 860,653 bytes,
SHA-256 `1b21f564533df6cdc1c99a5c4068d87538047f54a5243b6d0ed930d378ca2295`. Proof 44395635207
reproduces it from 52 lists. Format 3 and strict exact-delta checking stay.

**Expected direction.** No exact total is promised before the capture.

- **N8.** Its 124,173 `crash-restart` keys close. A key stays only if its delta also holds another
  fact; name each one. Other keys of those cases may change by alias numbers only, because a notice
  no longer takes a number.
- **The filing overwrite** is outside N8's count. Its keys lose the generic `recovery` fact. Some
  keep a residual that is older than this brief: the model expects a second filing occurrence the
  store never saved. Classify it; do not fix it here.
- **N9, new keys (N3).** The 11,095 close.
- **N9, changed keys (C3).** The 35,585 do not vanish: 302 changed them from an older delta to an
  empty page. Each now closes or returns to the delta it had in the pin before 302 (`8b27b116…`,
  proof 43972005458). A few return to that delta as 302's applied-row model moved it: a recovery
  notice the running store shows only after a restart (the check's N4, M06). None keeps the empty
  page 302 gave it.
- **The N4 share.** The 1,056 keys close.
- **New keys: none expected.** A new key is explained before the pin is committed, or it is a stop.
- **Unchanged:** the 376 contract, `G22-*` and channel keys; every `crash-locked` key; no
  `.restore-lock`, `startup-replay` or `crash-startup` key; all 34 clean-run point counts; every
  alteration shard `slipped=0`.

**Capture and proof.** Before the capture, fetch and merge main and check what changed under
`control/`, the workflow and the pin; settle drift first. Dispatch `control-owner-oracle.yml` on the
build branch with `ledger_only=false`. A strict failure against the old pin is capture evidence;
reject any other failure. Download the lists under `.work/317/`, merge them without conflicting
shared keys, and check that proof 44395635207's lists reproduce the old pin. Regenerate with
`owner_state_oracle.gaps` as `KNOWN-GAPS.md:759-771` shows. Commit the one new pin with a new section
in `KNOWN-GAPS.md`: counts by outcome and phase, N8 and N9 marked closed with their numbers, the
commands. Then dispatch the proof on that commit: 61 of 61 jobs green, its lists equal to the pin
byte for byte.

**How a reviewer confirms it.** An independent classification check, as 302 had: a fresh agent,
read-only, with its own scripts and not the builder's. It rebuilds both pins byte for byte with its
own packer and sorts every key of the union into closed, changed, alias-only, new and identical. It
recomputes N8's set and N9's three sets from the old lists by `CLASSIFICATION-CHECK.md`'s
definitions and follows each key. It compares every C3 key with its delta before 302. It writes
`reviews/20-store-oracle-reads/CLASSIFICATION-CHECK.md` with a verdict.

## CI budget

- **Owner oracle** (61 jobs, about 2.5 hours a run): one capture and one proof. No `ledger_only`
  run is needed. A third run needs the lead's OK first. 302 lost a capture to harness errors a local
  run would have shown, so step 4's gate comes first.
- **Control CI** (six workflows on every push to the PR): at most three pushes that carry code, then
  one rerun for the second green on the final head (`docs/REVIEW.md:44`). Progress and report
  commits carry `[skip ci]`.
- After a dispatch, write the run id into `PROGRESS.md` and stop. No agent waits on a run; the
  lead's watcher does (`gh run watch <id> --exit-status --interval 60`). On HTTP 403 wait for the
  reset and try once.

## Paths, and what must not change

May change: `recovery.py`; `Store._initialize` in `storage.py`; `Engine._admitted_request` in
`engine.py`; the test files named above; `control/README.md:193-202`;
`reviews/19b-owner-state/KNOWN-GAPS.json` and `KNOWN-GAPS.md`; `reviews/20-store-oracle-reads/`.

Must not touch:
- `results.py`: `recorded_write`, `Observations`, `RESTART_ADVICE`;
- `Store.write`, `_append`, `_finish`, `_replay`, `ensure_writable`, `flush_notices`, and the journal
  and SQLite formats;
- `definitions.py`, the tool schemas and the generated artifacts (`generate.py --check` stays clean);
- `owner_state_oracle/`: no expectation changes. `FORMAT.md` only if a sentence becomes untrue;
- Chrome's committed projection and its two recovery rules; the restore-lock allow-list
  (`engine.py:575`); app approval, no-resubmission, storage reservations, the durability order;
- `.github/workflows/`, `os/`, `mod/`, the installed service.

Replies outside these two cases keep their codes, fields, paging, warnings and text.

**Overlapping work**, fetched 2026-11-20:

| Work | Overlap |
|---|---|
| PR #72, `pkg/28-chrome` `cd2ce599`; PR #116, `pkg/28a-chrome-act` `1c67199b` (held until after R29's cut) | Both put `Engine.request`'s body under Chrome's `call_time` and add `**untrusted(exc)` to the refusal's error in `_admitted_request` and `_request`. Our edit is next to it: whoever merges second resolves by hand and keeps both. The answered read stays inside `call_time`. #116 also edits `control/README.md`, away from lines 193-202. |
| PR #76 `pkg/18c-b-chrome`, #82, #123, #124 | No file in common. |

## Stop rules

Stop, write the case into `PROGRESS.md` and report to `linux-tools` when:

- an oracle expectation would have to change to get green;
- a local matrix shows a new key, a changed `crash-locked` key, or a change that is none of the
  expected shapes;
- a plain read can only answer by writing, and the fix would be to let it write;
- the change would reach beyond `recovery.py`, `Store._initialize` and `Engine._admitted_request`;
- the capture fails anywhere but the strict comparison;
- main moved under `control/`, the workflow or the pin;
- the CI budget is used up.

## Acceptance

1. Both rules are built as written; every named test passes; every mutation is rejected by its test,
   rerun by the reviewer.
2. The local gate passed and is recorded with its counts.
3. The capture failed only on the strict comparison; alterations `slipped=0`.
4. The new pin is committed with its classification; the proof is 61 of 61 green and reproduces it.
5. A fresh package and security review says SAFE; the classification check says CONFIRMED; Control
   CI is green twice on the final head.
6. `control/README.md` and `KNOWN-GAPS.md` say what the code now does.

## Report

`reviews/20-store-oracle-reads/REPORT.md` in `AGENTS.md`'s format (a Claude builder leaves the text
in `PROGRESS.md`). It also holds: capture, re-pin and proof with run ids, counts and the pin's
SHA-256; the mutation table with the catching test's id and result; the changed tests; the known
limits below with any the build adds; what is left under `.work/` over 500 MB.

Known limits to record, none of them new harm:

- A legacy-intent source keeps its start-up notice even when the replay completes it: its list is
  cached before the replay (`recovery.py:48-63`). A caution too many, on stores with old audit rows.
- A read during a latch with nothing queued says nothing about the latch; the first change does.
- A barred live read still asks the mail server read-only for open filing checks whose result it
  cannot save, and shows "not yet checked" for a send whose saved check is clean. As today on a
  latched read.
- A queued notice lives in memory. The restart the advice asks for drops it; the durable source
  brings back a recovery notice and the next live check looks again.
- A proxy started while a notice is queued and storage fails still stops at start: its `tools`
  reply is not `ok` (`proxy.py:39-40`), as before 302. The error carries the advice.

## JUDGMENT-CALL for the owner

**None is needed.** T385 set the goal for reads, and his answer to 302's question (board T352, "Yes
(recommended)") covers what he will see: the tools ask for the restart "while continuing to show
changes already saved locally". What changes for him:

- After a crash at an unlucky moment and a restart, no notice says "outcome unknown, inspect" for
  work the log shows as finished, and a filing's exact warning is not replaced by a vaguer one.
- While a storage write is unfinished, Claude can read again: mail, the log, what is waiting. Such
  an answer still says a write did not finish and asks for the restart. Changes stay refused.

The technical calls are decided above with their reasons.

## Writer's local evidence

Scratch only: nothing committed, no prototype code adopted. Two exports of `4442c676`, one with a
prototype of both rules, both with the managed-settings stand-in.

- Base engine probes reproduced both gaps. On the prototype a barred `control_log` returned the
  refusal's `error` and `pending` and its page with the queued notice, and changed no byte.
- The sweep's own `exercise`, every point, both modes, 7,190 cases a side: live phases of the five
  N9 flows; crash phase of `filing_move`, `attachment_export`, `flag`, `delete_permanent`, `send`,
  `cancel`, `expiry`, `maintenance`; both for `restore`, `restart_index`, `restart_tail`. Main
  against prototype: 16,433 keys closed, 17,764 changed in content, 1,630 changed by alias numbers
  only, **0 new**; every `crash-locked` key identical. Four `restore` cases stop on an existing
  harness assertion on both sides.
- Crash closures sit where the last event is staged and not applied, for example
  `delete_permanent` 370-411 and 413 in single mode: the hosted N8 window (374 to 415 and 417) less
  the stand-in's 4 points. The filing overwrite sits at `filing_move` 242-283.
- `filing_move`, live phases, also against the commit before 302: of 7,758 changed keys 7,722 are
  again the delta from before 302 and 36 differ by 302's applied-row model; 1,275 closed.
- Unit tests on the prototype: base `test_review22_storage`, `test_restore_batches`,
  `test_review23_results`, `test_journal_closed`, `test_review21_pending`; Mail
  `test_review_fixes_22` to `25`, `test_review26_recovery`, `_storage`, `_results`,
  `test_owner_state_capture`, `test_owner_state_regressions`; the sweep module without its full
  matrix. Only the review 25 test failed. Two regression cases could not run: the export has no
  pin file.
- Not run: `onboarding` and the other flows, cleanup pairs, alteration shards, Chrome's tests, any
  hosted workflow. Local point numbers differ from hosted ones; resolve points from traces.
