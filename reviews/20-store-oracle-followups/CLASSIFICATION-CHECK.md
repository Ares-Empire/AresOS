# Classification check: the re-pin of 20-store-oracle-followups (`b2d50247`)

Checker: a fresh Claude agent on Fable 5.2, 2026-11-19. I worked read-only on tracked files and did not build this
package. This file is the only one I wrote in the repo, and it is not committed.

**Verdict:** every count in part 7 matches my own, key for key. No class of new or changed keys is a regression
by decision 24's bar: no key newly pins a repeated effect, a lost owner change or a wrongly shown operation
state. Two classes need plainer words in the record (SHOULD-FIX 1 and 2), because each is something the owner
can see: a recovery notice that outlives a finished start-up replay, and reads that return no page while a
storage problem lasts.

## What I read and ran

- **Read:**
  - `AGENTS.md`;
  - [the brief](../../briefs/20-store-oracle-followups.md), above all "One re-pin, after all three fixes" and
    "What must not change";
  - [PROGRESS.md](PROGRESS.md): "Fix after the proof" and build parts 7, 6 and 5;
  - the new section and N7 in [KNOWN-GAPS.md](../19b-owner-state/KNOWN-GAPS.md);
  - `control/owner_state_oracle/gaps.py`, for the list and pin format;
  - the package's diff of `control/aresos_control/` and `control/owner_state_oracle/`, to trace each class to
    its cause;
  - the earlier check, [CLASSIFICATION-CHECK.md](../20-restore-lock-followups/CLASSIFICATION-CHECK.md).
- **The pins:**
  - old: `git show b2d50247^:reviews/19b-owner-state/KNOWN-GAPS.json`; new: `git show b2d50247:` of the same file.
  - `a3b42851`'s copy and the worktree file are the same bytes as `b2d50247`'s.
- **Downloads (read-only), each into its own empty directory under `.work/classcheck/`:**
  - `gh run download` of 43972005458 (the proof that reproduces the old pin), 44375098965 (the capture),
    44395635207 (the proof) and 43722918063 (the capture behind the pin before, for H and N7);
  - the job logs of the first three, through `gh api …/actions/runs/<id>/logs`.
  - I dispatched, reran and cancelled nothing. The downloads and the merged lists are deleted again.
- **My own scripts**, kept in `.work/classcheck/scripts/` with a small `summary.json`, all run under `python3 -I`,
  peak memory 1.6 GB:
  - `merge.py` merges a run's lists and refuses conflicting shared keys;
  - `pack.py` is my own packer for the format-3 layout;
  - `outcomes.py` sorts every key of the union, with a one-to-one test for alias renamings;
  - `hn7.py` and `n7detail.py` rederive H and N7 from the two earlier lists;
  - `shape.py`, `classes.py`, `case.py` and `logs.py` check the expected shape, the classes and the job logs.
  - I did not run `gaps.py`. I opened the builder's `.work/302/repin/` only after my numbers were done, and
    then only `classification-summary.json`, the per-key receipts and the cause rule in `classify.py`.
- **Not run:**
  - nothing under `os/tests`, no `test_owner_*` module, no sweep and no Engine of my own;
  - no container, no root, no mount; no rpm-ostree, bootc or ostree command.

## The claims

| # | Claim in part 7 | My number | Result |
|---|---|---|---|
| 1 | Proof 43972005458's 53 lists merge without conflict and give the old pin byte for byte | 53 lists, 495 identical shared occurrences; 2,576,083 keys, 1,930 groups, 892,234 bytes, `8b27b116…`; my packer's bytes equal the old file | match |
| 2 | The capture's 52 lists give the new pin; the proof reproduces it | Capture and proof: 52 lists each (no G22-latch list), 495 shared; 2,420,003 keys, 1,860 groups, 860,653 bytes, `1b21f564…2295`, both byte-identical to the file. The two merged lists are equal line for line | match |
| 3 | Run 43722918063 reproduces the pin before (`ee326914…`) | 2,622,072 keys, 1,997 groups, 921,711 bytes, byte-identical to `b04c7e77`'s file | match |
| 4 | Closed 303,001; changed semantically 108,155; alias-only 8,159; new 146,921; identical 2,156,768 | The same five numbers. My outcome equals the builder's receipt for each of the 2,723,004 keys of the union | match |
| 5 | Alias-only changes are one-to-one renamings and nothing else | 8,159 keys (92 distinct pairs of deltas). Row, stage, calls, failure groups and pages are equal, and one renaming per key maps every fact. In 44 keys the renaming also reorders the facts. None fails the test | match |
| 6 | Phase table | fixed 1 / 0 / 0 / 0 / 376; exhausted 5,236 / 5,349 / 61 / 2,981 / 225,060; live-restored 113,755 / 43,757 / 6,492 / 19,175 / 955,143; crash-locked 0 / 0 / 528 / 0 / 544,273; crash-restart 184,009 / 59,049 / 1,078 / 124,765 / 431,916 | match |
| 7 | Per-cause table, nine rows | Five rows are a view family each and equal mine: statuses 92,820 / 522 / 18; lifecycle, operation, completion and holds 21,783 / 5,061 / 959; locations 16 / 2,246 / 24; qualification 0 / 0 / 16; G22 1 / 0 / 0. The other four split three families by one content rule (the live-check row). My families: pending 61,690 / 31,526 / 1,174; notices and catalogue 122,281 / 68,569 / 137,590; audit pages 4,410 / 231 / 7,140. The builder's four rows add up to the same, and the receipts give all nine rows exactly | match |
| 8 | `G22-latch/assertion` closes by a passing retry; the other 376 fixed keys are identical | 1 closed, 376 identical (372 contract, 2 channel, G22-rename, G22-evidence). The regression now asserts `reply['ok']` and `allowed` directly and is `ok` in the proof's `sweep (0, 0)` log | match |
| 9 | Statuses: 92,820 close, 522 change, 18 appear; the 18 are `stale_reference` against `allowed` | Same. Of the closed keys 92,793 observed `storage_limit` and 27 `stale_reference`. All 2,082 status keys left in the new pin are `stale_reference`; none pins `storage_limit` or `journal_incomplete` | match |
| 10 | Zero `startup-replay` failures, zero `crash-startup` keys, zero `.restore-lock` keys | 0, 0 and 0 in the new list | match |
| 11 | H: 1,386 cases; 63,379 keys become 37,328: 32,478 closed, 7,025 changed, 545 alias-only, 6,427 new, 23,331 identical | Same (322 single, 161 persistent, 903 pair, 31 flows) | match |
| 12 | N7's 6,949: 4,100 closed, 928 changed, 365 alias-only, 1,556 identical; no marked-versus-applied pair left | Rederived as 6,224 + 725 at 870 cases in 16 flows; then 4,100 / 928 / 365 / 1,556. By facts: pending rows 1,134 identical and 356 changed; counts 182 / 269 / 187; notices 240 / 303 / 178. In the old pin 1,214 N7 keys held one operation in two states; in the new pin none does | match |
| 13 | The 544 saved envelopes: 440 close, 32 change, 72 identical | Same. The 32 are 16 counts and 16 notice heads at `mail_account_add` and `mail_operation_repair`; the 72 are 36 and 36 (`control_archive` 40, the other two 16 each) | match |
| 14 | Part 4's 84 target keys are absent; 76 were pinned | The 84 keys of `sample-part4.json`, send points at the hosted 877 and 878: 76 in the old list, 0 in the new | match |
| 15 | All 544,801 `crash-locked` keys keep their deltas (528 alias-only) | 544,273 identical, 528 alias-only, none closed or new | match |
| 16 | 2,572 row-label changes in 13 transitions, none label-only, no stage change | The same 13 counts; 0 label-only; every key stage 3 and no R2 kind in either list | match |
| 17 | 16 new qualification keys; 959 new history-proof keys | 16; 959 = 62 `lifecycle-proof` + 897 operation views | match |
| 18 | All 34 hosted flow-point counts agree | 34 flows, one value each, equal in 43972005458, 44375098965 and 44395635207 | match |
| 19 | Capture: 48 jobs fail only on the pin; alterations 114 partitions, 2,096,041 candidates, none slipped | 48 jobs with one failure each, all `test_all_flows_all_storage_modes_independent_views`; 13 pass; no closed-database, corpus or timeout line. 114 partitions, 2,096,041, `slipped=0` on all 126 lines. Proof: 61 of 61 jobs green, the same 114 and 2,096,041 | match |

Where I differ from the builder: in no count. I differ in two cause descriptions (SHOULD-FIX 1 and 2).

Method, in short:

- **Pins (1 to 3).** I merged each run's lists, packed them with my own packer and compared the bytes with the
  committed file.
- **Outcomes (4 to 6).** For every key of the union I compared the two canonical deltas. A changed key is
  alias-only when one one-to-one renaming of the alias numbers turns the old delta into the new one.
- **H and N7 (11 to 13).** I rederived both sets from the lists of 43722918063 and 43972005458, with the earlier
  check's definitions, and followed them into the new list.
- **Logs (18, 19).** Every `Owner oracle flow=… points=…` and `slipped=` line of every job log.

## The new keys (146,921), by class

A key is new when the model and the store agreed before and differ now. `classes.py` puts every new key in exactly
one class.

| Class | Keys | Where | What the key says | Cause |
|---|---:|---|---|---|
| N1 | 124,173 | crash-restart; 7,941 case-phases in 24 flows | The store shows a recovery notice (state `unknown`) the model no longer expects: 64,973 notice keys and their 59,200 counts | Item 3's call ranges; the notice itself is older than this package |
| N2 | 592 | crash-restart | The failed call's own saved reply lacks a recovery notice the model now expects (and 8 qualification keys) | Item 3, applied rows |
| N3 | 11,095 | exhausted 1,628, live-restored 9,467; 2,457 case-phases in 5 flows | A read returns no page: audit 7,140, notices 2,170, operation views 893, pending 886, locations 6 | Item 1's request barrier |
| N4 | 10,941 | exhausted 1,345, live-restored 9,596 | The model expects a notice or row that the running store or the reply does not show | Item 3, applied rows; some from the barrier |
| N5 | 62 | exhausted 2, live-restored 60 | `lifecycle-proof` objects to history it can now see | Items 1 and 3 |
| N6 | 18 | exhausted 2, live-restored 16 | `mail_filing_locations` answers `stale_reference` | An existing shape (1,542 identical keys) |
| N7 | 40 | exhausted 4, live-restored 36 | 18 notice counts and 18 filing notice sets; 4 `operation-stages` | Items 1 and 3 |

**N1, traced.** `attachment_export/persistent/147/0/crash-restart/aresos log.notice-head`: the store shows a
recovery notice for `intent:#1`, the model expects none.
- In the old pin the same case held `lifecycle-proof` with `intent:#1 unjustified-removal`. The model rejected
  the event that start-up had finished, kept the intent as unfinished and therefore expected the notice.
- `driver.py:190` and `:456` now bind a call to its staged sequence, where they used the last marked one. The
  finished event belongs to its call, the removal is justified, and the model stops expecting the notice.
- The store has not changed here. Start-up collects unfinished work before it replays the staged event
  (`storage.py:215`, then `:239` and `:250`) and queues a notice for it (`recovery.py:139`). Only Chrome's
  notice is dropped when the replay finishes its source (`recovery.py:121`, `:134`); the others are saved
  at `storage.py:277`. This package's diff of `storage.py` touches `_append`, `write` and `ensure_writable` only.
- The whole class has this form. In all 7,941 case-phases the old `lifecycle-proof` key closed, and it named
  every source that now carries the unexpected notice: an intent removed (2,716), an export removed (2,155), an
  operation completed (2,474, and 241 with two operations) or failed (214), an account's setup closed (141).
- The points are one window per flow, between staging a call's last event and marking it (`delete_permanent`
  374 to 415 and 417, of 420). Single and persistent mode give the same 10,287 notice keys each.
- What the owner sees: after a crash in that window and a restart, a notice says an operation's outcome is
  unknown and asks him to inspect it, although the log records it as finished. It is a caution too many, not a
  hidden harm. See SHOULD-FIX 1.

**N3, traced.** `expiry/single/10/0/live-restored/aresos log.total`: the model counts 5 events, the reply 0.
- In the old pin the page matched and `response.control_log.status` was pinned (`storage_limit`, where the model
  allowed `allowed` or `journal_incomplete`): the read was answered with the stale error attached.
- Now `Engine.request`'s flush of a queued notice fails, `recorded_write` sets the request's barrier
  (`results.py:188-190`), and `_admitted_request` refuses before dispatch (`engine.py:776`). The reply is the
  refusal with the passive pending section and no `data`. The status key closed: the model expects this refusal.
- The 2,457 case-phases are in the five flows that leave a notice queued in memory: `filing_copy` 903,
  `filing_move` 903, `filing_rename` 341, `expiry` 300, `maintenance` 10. In live-restored all 2,122 had the
  pinned `control_log` status in the old pin.
- The passive section still carries the warnings. In the example, `envelope.control_log.pending-head` closed
  (the reserved operation is shown there now) and the envelope's notice heads are not pinned.
- This is a change in what the tools answer, not only in the model. See SHOULD-FIX 2.

**N4, traced.** `delete_permanent/single/72/0/live-restored/aresos log.notice-head`: the model expects a recovery
notice for the operation, the running store shows none.
- In the old pin this case held the marked-versus-applied gap: `control_pending.page` expected `reserved` and
  saw `submitting`, and `aresos log.page` saw one `mail_delete` event too many. Both keys closed.
- The model now reads the applied row (`records.py:238`, `:422`), sees the operation as `submitting` in a call
  that failed, and expects the notice it expects at every later point.
- Points 74 and 76 of the same flow carry exactly this delta in both pins. The running store shows such a
  notice only after a restart; that is the existing gap M06, now also pinned at the two marker points.
- The five largest shapes cover 10,241 of the 10,941 keys: notice counts (6,632), recovery notices for an applied
  intent or operation (2,553), and the background-storage notice missing from a refused read's page (1,056).

**N2.** The same expectation, in the failed call's own saved reply:
`attachment_export/persistent/54/0/crash-restart/envelope.attachment_save.notice-head`. The views read after
the restart agree.

**N5.** Three kinds:
- 21 at `archive` point 72 (`unjustified-check-reopen`) and 9 at `onboarding` points 1750 and 1751
  (`unjustified-stage`): an applied event the model can now see and does not accept. The store did the same
  before: at `onboarding` the old pin showed the row as `stages.mismatch` and an extra audit event, and those
  keys closed.
- 28 at filing points (`unjustified-check-close`, `missing-obligation-source`) and 4 at `expiry` and
  `maintenance` points 1 and 2: single-fault cases, live-restored. After a fully undone first append, the next
  request now saves the queued notice and result, which the old latch refused. The model has no source for a
  row written by a later call. This is the write the brief allows.

**N7.**
- `send_duplicate/persistent/963/0/exhausted/control_pending.notice-count`: the model now sees the operation
  as done and expects one notice; the store also shows "Sent copies not yet checked".
- `settlement/single/82/0/live-restored/operation-stages`: a later request saved a `sent_copy_warning` stage
  after a clean rollback.

## The semantic changes (108,155), by class

| Class | Keys | Where | What changed |
|---|---:|---|---|
| C1 | 58,785 | crash-restart, case-phases whose `lifecycle-proof` closed or shrank | The model's side moves with the replayed event it now accepts: pending 30,802, notices 22,105, lifecycle 5,050, locations 414, statuses 414 |
| C2 | 264 | crash-restart, other | The failed call's saved reply and filing point 110 |
| C3 | 35,585 | the 2,457 refused-read case-phases | The page shows less or nothing: notices 33,533, locations 1,800, audit 231, others 21 |
| C4 | 4,785 | exhausted 163, live-restored 4,622 | Only an `unchecked` notice left or joined the delta |
| C5 | 8,736 | exhausted 524, live-restored 8,212 | The model's side moves with the applied row: notices 7,914, pending 710, statuses 92, others 20 |

**C1, traced.** `delete_permanent/persistent/28/0/crash-restart/control_pending.complete` (17,232 keys of this
shape): the store shows `unknown` ("Service restarted during submission; inspect evidence, never resubmit").
The model expected `reserved` and now expects `submitting`.
- The staged `submitting` event that start-up finishes now belongs to its call (`driver.py:456`).
- `lifecycle-proof` in the same case lost `unsupported-resolution submission` and keeps
  `unsupported-resolution uncertainty`: the store's step to `unknown` at restart is still not what the model
  derives. The store is the cautious side.
- In crash-restart the store's start-up code is untouched and the two fault modes agree, so I read these as
  moves of the model only. 124,389 of the 124,765 new keys, 58,785 of the 59,049 changes and 183,865 of the
  184,009 closures of this phase are in case-phases whose `lifecycle-proof` closed or shrank.
- Across the pin, `lifecycle-proof` stopped raising 7,918 `changed-decoded-projection`, 6,569
  `unjustified-resolution`, 4,790 `submission`, 4,028 `completion`, 3,137 `unjustified-check-close` and 5,083
  removals of intents and exports. It raises nothing new in crash-restart.

**C3, traced.** `filing_copy/persistent/166/0/exhausted/aresos log.notice-head`: the old store listed the filing
notice in the page, the new reply has no page. `envelope.control_log.notice-head` of the same case still shows
the notice. The cause is N3's.

**C4, traced.** `send/persistent/732/0/exhausted/control_pending.notice-head`: the store showed an `unchecked`
notice the model did not expect; now the model expects it after a recheck the latch refused
(`model.py:495-497`), and only the older missing recovery notice stays. This is the builder's live-check row.

**C5, traced.** `delete_permanent/persistent/72/0/exhausted/envelope.control_log.pending-head`: the reply's
pending head omits the operation in both pins; the model expected `reserved` and now `submitting`.

**The restore flow.** 1,434 keys closed and 717 changed, all in crash-restart at points 26 to 75. The model now
accepts the confirm that start-up finishes: `lifecycle-proof` drops `unjustified-restore-transition`, and the
expected reason is `RESTORED_EVIDENCE`. The flow's other 20,764 keys are identical.

## The brief's expected shape

- **G22-latch** is gone by a passing retry; the other 376 fixed keys are byte for byte the same.
- **Start-up:** no `startup-replay` or `crash-startup` key and no `.restore-lock` key.
- **N7** lost the marked-versus-applied pairs (claim 12). The brief's two examples closed:
  `cancel/single/69/0/live-restored/control_pending.page` and
  `onboarding/persistent/1439/0/exhausted/mail catalogue.total`.
- **Outside scope:** the `crash-locked` keys, G22-rename, G22-evidence and the channel keys are unchanged, R2 is
  empty, and no row label moved without its facts.
- **Regressions I looked for.** Over all new keys and all changed keys, the kinds of fact a key gained on the
  store's side (shown, not expected) are: recovery notices, counts, `stale_reference`, the lifecycle objections
  of N5's 62 keys and 4 `stages.mismatch`. No key newly pins a `duplicate`, a second delivery, a
  `false-completion`, an R2 fact or an operation shown in a state the model does not expect.
- **Drift.** The 45 clean-run keys (point 0) are identical. No case and no fault point has keys in the new list
  that had none in the old: 1,079 cases and 104 points closed entirely, none appeared.

## Flow points

All 34 clean-run point counts are equal in the old proof, the capture and the proof (`restore` 76, `cancel` 70,
`send` 879, `onboarding` 2,610). The capture's and the proof's lists are equal line for line.

## Findings

No BLOCKER.

- **SHOULD-FIX 1. The largest new class has no name, count or owner in `KNOWN-GAPS.md`.**
  - N1 is 124,173 of the 146,921 new keys. The new section mentions it in half a sentence ("exposes retained
    recovery notices").
  - It is something the owner sees: after a crash between staging and marking a call's last event, the restart
    finishes the event and still shows "outcome unknown, inspect" for it.
  - The old pin hid it behind the model's wrong objection (12,517 `lifecycle-proof` keys).
  - Fix: name the class as N7 was named, with 124,173 keys at 7,941 case-phases in 24 flows, and put the
    decision on the board: the store drops the queued notice when the replay finishes its source (as it does
    for Chrome), or the model expects it.
- **SHOULD-FIX 2. The record does not say that item 1 makes reads return no page.**
  - Part 7 explains the audit row as "newly admitted healthy checks". All 7,140 new audit keys are the opposite:
    the read is refused and shows nothing. N3 and C3 hold 46,680 keys in the 2,457 case-phases where the audit
    page went empty; refused reads in flows with no audit events of the day (N4's 1,056) come on top.
  - The cause is the request barrier the brief asks for (item 1.2), and
    `test_failed_predispatch_flush_blocks_reads_and_cancellation_until_next_request` pins it. I do not call it
    a regression.
  - The reach is wider than the first-append case. `recorded_write` sets the barrier for every storage refusal,
    so a store whose latch survives and that has a notice queued refuses every later request, reads included,
    until the service restarts. Before, such a read was answered with the error attached. The refusal still
    carries the passive pending section and the restart advice.
  - The brief also says "Successful reads keep their replies" (item 1.5), and the owner's question spoke of
    "continuing to show changes already saved locally".
  - Fix: state the class and its count in `KNOWN-GAPS.md` and correct the audit row's cause. The lead decides
    whether this reach is wanted. The model could then stop expecting a page in a reply it expects refused.
- **NIT 1. The restore flow's 2,151 keys are not mentioned.** The item 2 bullet says the new check "adds
  coverage" only. One sentence on points 26 to 75 would do.
- **NIT 2. The new section leaves out the split earlier sections give.** It is 1,068,637 cleanup-free keys,
  1,350,990 pair keys and 376 fixed keys, at 51,987 cases and 10,143 failing points.

**Limit.** The lists hold only deltas, and I ran no sweep. For each class I checked which side differs, where,
and what else moved in the same case, and traced the cause in the code. I read the shapes that cover 146,849 of
the new keys and 101,075 of the changes, plus the largest shapes of the smaller classes, not every shape. That
N3's reads are refused, and not answered with an empty page, I take from the code and from the closed status
keys.

CONFIRMED
