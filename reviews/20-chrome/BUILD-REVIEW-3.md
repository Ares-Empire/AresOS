# Independent interim review — CHANGES NEEDED

Reviewer: fresh `gpt-6.1-sol`, high, requested by brief 20. This is an
interim review of stage **Now**, not a final qualification or a SAFE result.
The starting HEAD was `8013537646e5407423d5a459ca67dfa5b5b37cf2`.
Implementation and tests changed concurrently throughout this review. The
findings below name the source snapshot observed; repairs being written by
the builder are not cleared by the earlier test results.

Read the continuation briefs, parallel-start rules, earlier BUILD reviews,
and the specification from `origin/main` with `git show`, including section 6
and re-checks 29–34. No local browser, browser profile, browser container,
real site, account, system configuration or external service was accessed.
Only this review file was intentionally edited by the reviewer; plain Node
and Python tests created their disposable data under the worktree's `.work/`.
No implementation, branch or index changes were made by the reviewer.

## Findings at the reviewed snapshot

1. **P1 — Page-role confirmation text does not classify its OK button.**
   **Read:** in the initial `reader.js`, `targetFacts()` contains no enclosing
   dialog facts. `policy.py:classify()` classifies a click using only the
   target's label/title/value/role and form action. Thus an ordinary `OK`
   button inside `role="alertdialog"` with text `Delete everything?` is free.
   `guard.js:asks()` has the same omission for a script's activation. This
   conflicts with section 6's rule that a new confirmation asks when its
   **text or button** contains a listed word. **Run:** a browser-free call to
   the production classifier with that target, dialog and item returned
   `None`; native-dialog acceptance with the same dialog returned `delete`.
   No HTTP arrival or Chrome event-order claim follows from that probe.
   Add the enclosing page dialog's kind, full text, frame/site and button to
   classification and binding, and exercise exact-match changes plus script
   activation. The builder began adding `page_dialog` facts while this
   review was running; that repair has not been rerun by this review.

2. **P1 — The isolated guard misses the shipped German word `Papierkorb`.**
   **Read:** `guard.js:asks()` lowercases the matched words but uses
   `config.words.includes(word)` against the original generated list, which
   includes capitalized `Papierkorb`. The Python classifier casefolds both
   sides and therefore makes a different decision. **Run:** the actual
   guard/page scripts in the existing browser-free VM fixture, armed for a
   free input with `words:['Papierkorb']`, delivered a page-script `.click()`
   on a button named `Papierkorb`: `scriptClickDelivered:1, heldReports:0`.
   Normalize both sides consistently and test the complete shipped word
   list through wrappers and the capture fallback. The current browser
   word matrix tests direct tool actions; it does not establish the page
   guard's decision for every word. This is a Node handler count, not an
   independent network receiver result.

3. **P1 — An unmerged shipped-copy PR prevents the next qualification
   publication.** **Read:** `qualify.py:main(plan)` initially passes only
   the shipped record on `main` to `plan()`. It does not plan against the
   verified record already published on `chrome-qualification`. After a
   successful publication whose shipped-copy PR is still unmerged, the
   next scheduled run therefore repeats those pairs. `prepare()` appends
   them again, and record validation refuses the duplicate keys. A new
   result in that same candidate cannot be published either. The design
   explicitly allows the lead to merge the shipped-copy PR whenever
   convenient; runtime publication must continue independently.
   **Run:** with an empty shipped baseline and a data record containing a
   passing stable entry, production `plan()` scheduled that already-published
   stable twice. Production `prepare()` with its rerun entry then raised
   `qualification_invalid: Repeated qualification key.` The probe used a
   temporary directory and a stub verifier, with no remote mutation.
   Plan from the verified newest record and handle duplicate/racing pairs
   without preventing unrelated new entries from being published. The
   builder was editing this path when this report was written.

4. **P1 acceptance gap — The qualification result consumed by `pair` has
   no producer.** **Read:** initial `qualify.py:125–128` loads
   `qualification-result.json`, defaulting to empty dictionaries when it is
   absent. Searching the CI sources and tests found no writer for that
   file: `browser.mjs` emits preliminary `smoke.json` and `matrices.json`.
   Consequently even successful pair jobs produce all-false aggregate
   qualifications. The initial browser matrices also omit the complete
   groups 3, 4, 5, 6 and 9, and several subcases of the remaining groups.
   The builder confirmed those were still being built, with no green
   claim. Produce per-group results only from the complete named suite,
   retain failures truthfully, and require the full final-head runs twice.
   Source inspection is the evidence here; no qualification workflow was
   run or inspected by this reviewer.

5. **P2 — Service paging originally starts after an oversized native
   response has already failed.** **Read:** initial `reader.snapshot()`
   serializes the entire document's rows, editable fields and trace;
   `background.facts()` aggregates whole-frame snapshots; `Bridge.read()`
   refuses a message over 1 MiB. Fragmenting the tree in `Chrome.read()`
   occurs only after that response. Thus a sufficiently long page has no
   readable first page, despite the public cursor interface. **Run:** the
   actual reader in its existing Node mock fixture serialized 2,000 input
   fields to **1,332,884 bytes**, above that native-message limit. This is
   a synthetic size probe, not a representative real-page measurement.
   The builder began adding bounded native-response fragmentation during
   this review. That new transport has not been validated by this review;
   it needs multibyte UTF-8, missing/out-of-order/oversized fragments and
   a page genuinely above the former bound, including subsequent paging.

## Additional source concern passed to the security reviewer

**Read, not browser-confirmed:** password history is updated by the
MutationObserver callback. Within a single page input handler, a new or
previously ordinary field can become `password`, receive a secret, become
plain text, and immediately call `requestSubmit()`. The isolated submit
capture synchronously calls `reader.form()` through its search check;
`formFacts()` can then call `safeValue()` before queued old-type mutation
records have been delivered. The secret could enter the accumulated trace
even if the later observer callback protects the field. Exercise this
same-task path with the browser-to-extension audit, and consider consuming
pending mutation records before value reads. This concern is not reported
as a reproduced browser leak or an impossibility claim.

## Checks run and their limits

- **Run:** `node --test control/chrome_tests/*.test.mjs`: **17 passed,
  0 failed**, exit 0. This preceded the concurrent page-dialog, allowance
  and native-fragmentation repairs.
- **Run:** `PYTHONPATH=control python3 -m unittest discover -s control/chrome_tests -v`:
  **54 tests in 142.313s, FAILED (failures=5)**, exit 1. Every failure was
  in the new `test_fault_surface` activation sweep: the observed catalogue
  had an extra `recovery-*` occurrence compared with its new independent
  committed-record oracle. Cases included persistent `file.fsync` point
  56, the cleanup pair at 57, and `sqlite.index.write` point 57 in single
  and persistent modes. The source and oracle changed during this run;
  this is interim failure evidence, not a stable-head diagnosis. The
  existing sweep separately printed
  `Chrome durable-write sweep {'single': 442, 'persistent': 442, 'pairs': 829}`
  and passed.
- **Run:** focused Python classifier and local qualification-helper probes
  reproduced findings 1 and 3; Node production-script probes reproduced
  finding 2 and measured finding 5. An initial qualification helper probe
  failed its local import because `control/chrome` was missing from
  `PYTHONPATH`; it was rerun successfully with
  `PYTHONPATH=control:control/chrome`.
- **Read:** private guard state is now in ISOLATED, with no public MAIN
  `stop`/`arm`/`resume` object. The MAIN wrappers carry requests that the
  isolated listener rechecks. Identity comes from dispatched DOM nodes
  rather than the earlier page-provided identity string. These are useful
  architectural repairs; Node mocks do not prove cross-world browser
  behavior or the complete hostile-page guarantees.
- **Read:** prepared actions recheck read-only restrictions and password
  qualification before dispatch. Qualification delivery now has runtime
  callers in `mode()` and daemon maintenance. Pending preparations derive
  refusal reasons from the committed operation's process/browser session,
  live control/document identity, current owner restrictions and current
  qualification. Exact full binding is still checked at actual dispatch;
  the pending validity response itself is a narrower live check.

No browser or receiver suite, Linux socket-credential suite, real
attestation verifier fixture, base/Mail/boundary workflow, or full final
head run twice was executed by this reviewer. Fresh review of the completed
repairs and their receiver evidence is still required.

## Follow-up on concurrent repairs

HEAD remained `8013537646e5407423d5a459ca67dfa5b5b37cf2`; the following
checks used later, uncommitted working files. **Run:**
`node --test control/chrome_tests/page.test.mjs control/chrome_tests/reader.test.mjs`
passed **19 tests, 0 failed**. This includes the new `Papierkorb` wrapper and
capture test, queued password-to-text mutation test, trusted-event replay
test, and default/extra-submission arbitration test. **Run:**
`PYTHONPATH=control python3 -m unittest discover -s control/chrome_tests -p 'test_publisher.py' -v`
passed **5 tests**. Its new local test confirms an already-published pair
can remain unchanged while a new pair is appended, and a conflicting
immutable verdict refuses. **Read:** planning now fetches and verifies the
published data record before deciding which pairs are missing. Findings 2
and 3 and the queued-mutation concern have useful browser-free/source repair
evidence, but their complete Linux/browser behavior remains unverified here.

**Run:** an actual `Bridge.call()` over a socketpair reconstructed
**1,600,070 UTF-8 wire bytes** containing **600,000 multibyte characters**
from 64 KiB base64 fragments, exactly equal to the original text. This
establishes that one happy-path native reassembly works; it does not replace
out-of-order, interrupted, oversized, cross-process or full paging tests.

Two further source issues were reported immediately to the builder:

- **P1 — Oversized post-effect replies must remain `unknown`.** The new
  `background.respond()` initially returned a plain `refused` error when a
  complete response exceeded 32 MiB, even if `effectStarted` was true.
  A page input that already ran and generated a large held-step response
  could therefore be settled as a definite failure by `Chrome.execute()`
  (`refused` becomes `NothingLeft`) or `Chrome.free()`. An oversized pure
  read may refuse; an oversized response after a possible input must say
  `unknown`, through the existing effect-aware error path. **Read only:**
  no 32 MiB post-effect fixture was executed in this review.
- **P2 — Page confirmation classification must preserve its own kind.**
  The first `page_dialog` repair appends the enclosing dialog's text to the
  generic word scan. An OK button under `Submit this request?`, with no
  editable text, becomes `send`, then generic outside-form send preparation
  refuses because it finds no editable text. Native confirmations instead
  use the `confirmation` kind. Exercise a send-word page confirmation with
  OK and no editable fields, retaining actual compose Send binding when the
  target really sends compose content. **Read only:** this follow-up source
  path was not yet checked with a receiver or a new engine test.

## Focused owner-state review at `40f380d6`

Reviewed clean snapshot `40f380d639206cfb6782d8e3eac7d0ee8f621270` at the
builder's request, limited to Chrome R1–R3, warning lifecycle and the
receiver/crash harness. Ran only small Python probes using the existing
`test_engine.Operations` fixture; no full storage sweep or browser was run.
The following are new findings, separate from the earlier changing-tree run.

1. **P1 — A committed Chrome warning disappears under failed SQLite
   reads.** `Engine.pending()` falls back to `_last_pending` plus deferred
   in-memory notices. **Run:** cache an empty Chrome pending response,
   commit an activation warning through production `Chrome.steps()`, then
   replace the working DB's read interface with one raising an
   `sqlite3.OperationalError` carrying `SQLITE_FULL`. The committed store
   contains one Chrome notice, but pending returns
   `items:0, total:0, notices:0, unavailable:true`. No new deferred notice
   exists because the warning already committed successfully. This is an
   R1 loss of an owner-visible fact, despite the generic snapshot warning.

2. **P1 — Failed reads can resurrect an acknowledged occurrence.**
   **Run:** cache the healthy activation notice; invoke the real
   `chrome_notice_ack` action, allowing its `Store.write()` to commit, then
   inject `SQLITE_FULL` reads immediately after that successful commit.
   The reply's `data.notice.ack` is `true`; the stored notice's `ack` is
   also `true` after reads are restored. Its passive `pending.notices`
   nevertheless contains that same occurrence from `_last_pending`.
   Refreshing memory after successful actions cannot close this window:
   the failure occurs between the commit and the attempted refresh.

3. **P2 — Cached validity is not recomputed after a live session change.**
   **Run:** reserve an operation and cache `validity:'current'`; change the
   synthetic bridge session to represent a browser restart; fail SQLite
   reads. The pending fallback still reports `validity:'current'` with
   `Awaiting exact approval; nothing submitted.` Its generic
   `unavailable:true` notice does not make this current validity true.
   Refusals/validity must be recomputed from committed context plus current
   private session checks, or explicitly be unavailable rather than current.

4. **P1 — A new document's activation can inherit an old acknowledgement.**
   `Chrome.steps()` builds its source identity from
   `digest([bridge.session, tab, step])`. The guard's held IDs (`h1`) and
   reader's element IDs (`e1`) restart per document, while the browser session
   and tab remain the same. No source-document identity is attached when
   background polls those steps. **Run:** call `Chrome.steps()` for an
   `activation` with `h1/e1`, acknowledge its notice, change the fixture's
   document and URL, and call `steps()` with the new document's identical
   per-document IDs. Results: `notice_count:1, unacknowledged:0,
   chrome_notices.total:0`. The new activation has silently reused the old
   evidence fingerprint and acknowledgement. Include private document
   identity in the step, source ID and evidence; repeated readings of that
   same event should still retain the existing occurrence. Refuse a step
   whose document differs from the fresh frame before preparing anything.

   A related **source-only binding concern** was passed to the builder:
   rereading current facts for an old step currently constructs a reference
   in the current document from the old per-document element ID. `guard.resume`
   receives only the held ID and operation, not the expected held form or
   submitter. Document rejection plus local expected-node validation should
   prevent old IDs from binding one control while resuming a different
   colliding hold. No cross-document browser resumption was run here.

5. **P2 harness gap — Receiver counts alone do not establish truthful
   crash outcomes.** At `matrices.mjs:171–189`, the after-input cut waits for
   receiver arrival and then kills a component, with no barrier proving the
   service had not already committed completion. Its replay assertion accepts
   every non-`reserved` state, including an incorrect definite `failed`.
   Thus this test can show no duplicate send while missing a false claim
   about whether input ran. Add a private post-input/pre-outcome barrier and
   assert `unknown` when the outcome was cut off; definite pre-dispatch
   refusals may remain `failed`. **Read only:** this harness was not executed.

The first probe attempt raised a plain `OperationalError` without a SQLite
error code; production correctly did not classify that mock as `SQLITE_FULL`.
The successful probes above set the real `SQLITE_FULL` code explicitly. All
fixture stores were restored and closed after probing; no implementation
files were edited.

The builder proposed a limited Chrome read fallback in the **existing
independent journal**, retaining Chrome operation/check/notice updates and
acknowledgements and using existing paging and occurrence bookkeeping.
That scope fits Now's explicit Chrome storage requirements, provided it:

- honors commit markers and excludes appended-but-uncommitted tails;
- retains acknowledgement, resolution and tombstone transitions through
  archive/restore, and cannot revive acknowledged occurrences;
- serves global passive envelopes and every `chrome_notices` page as well
  as explicit Chrome pending reads;
- treats old records lacking sufficient owner-state context as conservatively
  unavailable rather than a complete empty set;
- recomputes available live session facts, avoids cached affirmative validity,
  and uses bounded streaming rather than a full-history memory dictionary.

This is a proposed repair scope, not an implemented or tested substitute
for 19b. The final report should explicitly describe the additional record
fields and the later migration to 19b's one shared read path and full oracle.

## Review of the committed Chrome fallback repair

Reviewed the new `chrome/committed.py`, additive `record['chrome']` journal
metadata, Engine integration and private step identities in a changing
worktree based on `40f380d6`; HEAD advanced to
`e1f1bacf048afae2d1513ddeb0a425c78421b8ec` during this follow-up. The builder
reported broader passing sweeps; those are not runs by this reviewer.

**Run:**
`PYTHONPATH=control python3 -m unittest discover -s control/chrome_tests -p 'test_committed.py' -v`
passed **6 tests in 0.072s**. These establish useful focused repairs for the
lost notice, stale session validity, acknowledgement/restart, tombstone and
clean/recurrence cases, plus an appended-but-uncommitted tail. **Read:**
the indexed values remain on disk, acknowledgement filter hits are checked
against committed records, and per-document step identity plus local held
form/submitter checks address the earlier cross-document collision. These
are limited repair findings, not full browser or final-head evidence.

The follow-up found the following further issues and sent them immediately
to the builder:

1. **P2 — Pending validity omitted failed adapter qualification.**
   **Run:** prepare Gmail through its adapter, append a qualification entry
   disabling Gmail, and move the synthetic browser to a later patch of that
   major. Both healthy pending and `pending_projection()` returned
   `validity:'current'`, while actual `Chrome.revalidate()` refused
   `stale_approval: The site adapter is no longer qualified; prepare again
   under the generic rules.` The builder subsequently added that adapter
   check to the common pending path. That latest edit was source-reviewed,
   not yet rerun by this reviewer.

2. **P2 — Legacy completed operations were retained as unknown.**
   The first projection implementation indexed an old reserved/submitting
   compact operation as unknown, but did not remove it when a later legacy
   compact record said `done` or `failed`. **Run:** create a real completed
   fixture operation, copy its journal to a separate temporary directory,
   remove the new Chrome metadata, and recompute its valid chain and commit
   markers to model the preceding format. `Projection.rows('op:')` returned
   the completed operation as unknown, despite its final compact state being
   done. The builder subsequently added removal on those legacy terminal
   states and a legacy-path key-count check. Source reviewed; no repeat of
   this probe was run against that later edit. The separate migration
   warning for missing old notice/check metadata can remain conservative.

3. **P2 — Acknowledgement can leave a phantom paged warning count.**
   The fallback removes cached Chrome notice rows, but initially retained
   cached `notices_more` when the newly computed Chrome page had no cursor.
   **Run:** cache four Chrome activation notices, then acknowledge one
   through the actual action and inject `SQLITE_FULL` immediately after the
   acknowledgement commit. The projection correctly returns three notices
   and a catalogue with `total:3, cursor:None`; passive pending still has
   `notices_more:{count:1,...}`, implying a fourth warning that no longer
   exists. Remove/recompute the old pagination metadata with the rows.

   The same probe exposed a healthy routing problem: with only Chrome
   warnings, cached `notices_more.action` was `mail_filing_notices`, whose
   implementation filters to Mail. It cannot fetch the omitted Chrome
   occurrence. Global/mixed-app envelopes need explicit usable catalogue
   routes; a healthy first page must not hide an inaccessible later page.

4. **P2 — The key bound cannot recover after archived history.**
   The scanner initially enforces `MAX_KEYS` as it encounters each historical
   record. If a record exceeds the bound, it raises before advancing its
   offset; later tombstones are never reached. The error tells the owner to
   archive finished history, but appending that archive cannot fix it, and
   a fresh projection fails at the same historical peak.

   **Run:** write a valid committed synthetic journal in a temporary
   directory and patch only the test's `MAX_KEYS` to 2: first record adds
   `chrome:a,b`; second adds `chrome:c`; third deletes `a,b`. The final
   current set has one key. Both fresh and repeated sync nevertheless
   return `owner_state_unavailable`, stopped at sequence 1 with three
   indexed keys. This establishes a history-peak refusal rather than the
   claimed current-key bound. A bounded latest-key/window scan, like the
   existing journal fallback pattern, can process subsequent tombstones
   without retaining the entire historical peak. Merely moving the check
   to the end while accumulating all keys would weaken the memory bound.

No full suite, full fault sweep or browser was run for this follow-up. The
focused probes use synthetic fixture data, fake SQLite read failures with
the actual `SQLITE_FULL` code, and isolated temporary journal copies; they
do not modify implementation or the live fixture journal.
