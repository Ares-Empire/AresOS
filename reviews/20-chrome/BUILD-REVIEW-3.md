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

## Retest of the follow-up owner-state fixes

Working-tree retest based on `e1f1bacf048afae2d1513ddeb0a425c78421b8ec`,
limited to the pending qualification check, legacy terminal handling,
shared notice pager, pagination metadata and bounded rebuild. **Run:**

- `PYTHONPATH=control python3 -m unittest discover -s control/chrome_tests -p 'test_committed.py' -v`:
  **9 tests in 0.132s, OK**.
- Repeated the failed-Gmail-adapter probe: healthy pending and the committed
  projection both now report `refused`, matching dispatch preflight.
- A separate valid legacy journal containing a reserved operation followed
  by `done` now yields **no pending operation**. The independent migration
  flag remains true, correctly distinguishing missing old metadata from an
  unfinished operation.
- Repeated the exact acknowledgement window: inject `SQLITE_FULL` after
  the acknowledgement commit and before pending refresh. The passive
  envelope now has **3 notices, no `notices_more`**; the committed catalogue
  has **3**. This clears the previously reproduced phantom fourth count.
- Exercised `control_notices` through actual Engine requests: a healthy
  mixed set of **7 Chrome + 2 Mail** notices returned all **9 across 3
  pages**. Under failed SQLite reads it returned all **7 Chrome notices
  across 3 pages**, with the storage error and explicit other-app
  `unavailable` message retained.
- Probed `Projection.rebuild()` against independent expected final values
  for **20 deterministic random seeds**, each with **80 historical keys
  and 281 committed updates**, including acknowledgements, deletions and
  reintroductions. With the test key cap reduced to 10 and final retained
  sets within it, every final value, acknowledgement and tombstone matched.
  This exercises several 32-key scan windows and the historical-peak
  recovery path; it is not a full-size performance benchmark.
- `PYTHONPATH=control python3 control/generate.py --check` printed
  `Generated artifacts match definitions`; `git diff --check` was clean.

**Read/run:** the earlier adapter, legacy-terminal, phantom-count/routing
and historical-peak findings have focused repair evidence. No new defect
was found in the bounded-window selection or acknowledgement carry-forward
in this limited retest.

One further **P2 compact-envelope bound** was reproduced and sent to the
builder: the failed-read fallback appends up to three cached other-app
notices after up to three current Chrome notices. The shared `NOTICES`
schema permits at most three. **Run:** cache three synthetic Mail notices,
commit three Chrome activation warnings, then fail SQLite reads. Passive
pending returns **6 notices** (`chrome,chrome,chrome,mail,mail,mail`). Budget
the compact envelope to three while retaining a correct current Chrome
catalogue route/count and explicitly marking other-app state unavailable.
The shared catalogue itself paged the current Chrome set correctly in the
probe above.

These are focused browser-free checks, not the full storage sweep, base
suite, full-size resource test or final Linux receiver runs.

## Compact-envelope and qualification-producer follow-up

Reviewed working files based on
`8f361aa60a564a276a2c0349fbb729718d92be08`. **Run:** the committed-state
test command above now passes **10 tests in 0.130s**, including
`test_failed_sqlite_compact_envelope_with_cached_mail_and_current_chrome_stays_bounded`.
**Read:** the normal committed-fallback branch now caps current Chrome plus
explicitly unavailable other-app snapshot rows to three, while deriving the
Chrome count and catalogue route from its current source.

A remaining **P2 exception-path bound** was sent to the builder:
when the independent Chrome source itself is unavailable, the exception
branch initially appends its explicit Chrome-unavailable marker after three
cached other-app notices. **Run:** cache three Mail notices, fail SQLite
reads, and inject EIO from `chrome.notice_page()`: passive pending has
**4 notices**, three Mail snapshots plus the Chrome-unavailable marker.
The marker must remain visible, with the remaining snapshot rows capped
within the same three-notice budget.

The new `ci/verdicts.mjs` producer initially had three reproduced false-pass
paths, which were reported and repaired during this focused review:

- Missing or failed required group-13 rows set only an unused `groups[13]`
  flag; all recorded core and adapter switches could still be true.
- A passing duplicate could mask a failing duplicate, and a nonboolean
  `passed:'false'` value counted as success.
- A new failing check whose name had not been added to the mapping could
  leave every recorded switch true while making the runner fail.

**Read/run after repairs:** each required/support name now needs exactly
one row with `passed === true`; group 13 contributes to the recorded
page-script verdict; unknown names make support qualification fail closed.
`node --test control/chrome_tests/verdicts.test.mjs` passed **6 tests,
0 failed**, including the mandatory-row-to-recorded-switch invariant,
duplicate/nonboolean evidence and unmapped extra rows. The strict owner
gap still sets group 2 and `core.page_script` false. No further false-pass
path was found in this limited producer review.

The producer tests construct result rows; they do not establish that the
browser assertions run, that every fixture matches its intended case, or
that the complete runner passes. Full final runner sets remain pending;
this report does not issue SAFE.

## Focused review of asynchronous modal completion

Reviewed the uncommitted `finishFrames()` and per-dispatch nonce changes
on a worktree based on `95ed8ac1baf97b0e41ed593fed4920de0883413b`.
**Run:**
`node --test control/chrome_tests/background.test.mjs control/chrome_tests/page.test.mjs`
passed **29 tests, 0 failed**, including the regression that an old delayed
finish cannot clear a newly armed dispatch in the same control epoch.

**Read:** background gives each input its own private `dispatch_nonce`,
passes it in every frame's arm/finish messages, and `guard.finish()` checks
both epoch and nonce after its later task before relaxing the in-flight
mark. A release changes the epoch or clears generation; a new input changes
the nonce. This addresses the stale-finish relaxation race at source/Node
level, without putting authority in MAIN.

**Run:** browser-free probes of the actual `finishFrames()` showed:

- normal completion sends finish messages to both mocked frames and carries
  the supplied nonce;
- when a finish reply stays pending, a private dialog notification releases
  the helper, skips later frames while the dialog remains open, and removes
  its waiter;
- if a dialog is already present, the helper returns without sending finish
  to any frame; deleting that dialog afterward does not itself restart
  finishing in the helper.

Two further source concerns were sent promptly to the builder:

1. **Covered-dialog close can leave frames unfinished.** The early-return
   case also covers a dialog currently being auto-accepted by the exact
   confirmation handler. If its close notification arrives after that
   return, the remaining frames did not receive finish messages, and no
   separate `chrome_dialog` call follows the auto-accept. Their in-flight
   marks can therefore remain set until another tool input. Ensure a
   covered close finishes all armed frames under the same private nonce,
   or that finishing resumes after that close. This is a source/timing
   concern; no actual Chrome event ordering was run here.
2. **Effectful content commands still await modal-blocked replies.**
   `content('focus'/'select'/'install_file')` initially waits directly on
   `tabs.sendMessage`. Reader focus/input/change handlers run before that
   reply. A synchronous uncovered native confirm in one of those handlers
   can block the reply while background serial waits on it, leaving
   `chrome_dialog` queued behind the action that needs it. The new race
   helper covers final finish messages, not these earlier content commands.
   A generalized modal race must also stop intermediate dispatch: an early
   return from focus does not establish that the reader verified the bound
   active element, so subsequent key/text input must not proceed on that
   assumption. Select/upload may have only partly handled their events;
   preserve truthful partial/unknown/dialog observations. These paths were
   source-reviewed, not reproduced in a browser by this reviewer.

**Run:** generated **159 fixture pages** through disposable local HTTP
servers and compiled each extracted inline script with `new vm.Script`:
**159 scripts compiled, zero syntax failures**. Covered the new native
confirmation variants, all six synthetic site adapters and confirmation
modes, owner replay variants, and matrix handler routes. None of those page
scripts was executed; no browser, profile, container or real site was used.
The servers were closed after the probe. Compilation proves syntax only,
not page behavior or receiver assertions.

### Modal follow-up and an exact-confirmation race

The builder added private sets of dialog waiters with individual disposal,
captured the input epoch/nonce in a WeakMap at dialog opening, and arranged
for dialog close to finish that captured input. Effectful content commands
now race modal notification and throw `unknown` on interruption, stopping
the rest of a focus/select/upload operation. **Read/run:** these address the
two preceding source concerns; focused tests cover content-focus
interruption, overlapping waiter disposal and interrupted finishing.

Two further defects were then found and reported:

- **CDP continuation deadlock:** a `keyDown` dialog wake originally returned
  normally, so the dispatcher sent `keyUp` while the dialog was already
  open. A new waiter then missed the opening notification and could wait
  indefinitely for its modal-blocked native acknowledgement. **Run:** the
  actual background dispatch/CDP functions with mocked modal-blocked
  acknowledgements remained blocked after 25 ms, having sent
  `['keyDown','keyUp']`, with the dialog present and one waiter. The builder
  added an existing-modal guard before further CDP input.
- **P1 exact-confirmation race:** the opening handler awaited frame lookup
  without rechecking which dialog was current. **Run:** suspend the old
  approved dialog's frame lookup; close it; open a dialog saying
  `Delete DIFFERENT branch?`; then resolve the old lookup. The actual
  handler sent `Page.handleJavaScriptDialog` while that **different** dialog
  was current. The VM probe printed
  `acceptedDialogTexts:['Delete DIFFERENT branch?']`. This is a confirmed
  asynchronous source/Node counterexample, not a Chrome receiver result.

The builder repaired the latter by capturing the input/nonce and approval
plan before awaiting, then requiring the captured dialog, control object,
nonce and plan still to be current before consuming the confirmation and
accepting it.

At the builder's **explicit additional delegation**, this reviewer edited
only `control/chrome_tests/background.test.mjs` beyond this report, adding
two strict browser-free regressions. The actual-handler test proves an
unchanged exact dialog remains covered, while a stale matching opening
cannot accept the DIFFERENT current dialog or consume the approval. The
actual dispatch/CDP test proves a keydown modal rejects before sending
keyup, with its waiter removed. No production implementation was edited
by the reviewer.

**Run after those repairs:**
`node --test control/chrome_tests/background.test.mjs control/chrome_tests/page.test.mjs`
passed **34 tests, 0 failed**. `git diff --check` was clean. HEAD during
this final targeted run was
`74a9ad5fe990f2945273f70478cf80b3f165cdbc`, with concurrent uncommitted
repairs. These modal findings are closed at focused source/Node level;
actual Chrome modal ordering and receiver behavior still require the
authorized Linux runner. No SAFE or full final-run claim is made.

## Follow-up: page steps after dialogs and document replacement

Reviewed source at `76d39fa29cb6ddf205e707a2354d7e42fcbcf992` at the
builder's request. Both following reporting gaps were confirmed with plain
Node probes of the actual guard/page/background functions; no production
implementation was edited and no browser was used.

1. **P1 — Answering a native dialog does not collect its resumed handler's
   held steps.** The dialog branch answers the modal, finishes frame input
   handling and immediately returns `steps:[]`. A resumed handler can call
   `form.submit()` while the preceding input's private hold is active; the
   guard stops it, but no poll runs in that command. **Run:** connect the
   actual background dispatcher to the actual page/isolated guard in their
   existing VM fixtures. The mocked native answer invokes the resumed
   handler's `form.submit()` before returning. Output:
   `receiverArrivals:0, returnedSteps:0, heldKinds:['native_submit'],
   contentCommands:['finish_input']`. The submission stays held, so this is
   not an unapproved send. It is a missing required preparation/owner-visible
   check, potentially invisible until an unrelated later input polls it.
   A normal read does not poll held steps. The dialog command should use
   the same bounded post-input collection as ordinary input, without
   automatically resuming any newly held submission.

2. **P1 — Document replacement can erase an unknown fallback activation
   before it is reported.** The isolated capture fallback correctly stores
   `activation_unknown` for a noncancelable raw activation. Its only copy
   is initially the old document's guard Map; background later polls the
   currently loaded frames. **Run with the browser default explicitly
   simulated:** actual guard capture handles a raw noncancelable Delete-link
   click; because it cannot prevent that default, the probe replaces the
   current reader with a fresh document, then lets actual background
   dispatch finish and poll. Output:
   `simulatedDefaultNavigations:1, returnedSteps:0,
   discardedOldDocumentKinds:['activation_unknown'], newDocumentSteps:0`.
   Node does not establish Chrome's actual navigation/network delivery, but
   demonstrates the source lifetime gap. This is not the accepted residual
   of an unrecognizable send, nor a stale-document refusal: the tool
   recognized the asking activation and then lost its required unknown
   report before the service could commit it.

The suggested small repair is a private ISOLATED-to-background observation
notification before returning from capture, including the private document,
dispatch nonce and step ID, with sender tab/frame and control checks.
Deduplicate notification versus later poll by document/step identity.
Keep an unknown activation report even when its old document is gone; do
not reinterpret its element IDs in a replacement document. A MAIN event,
attribute or global must never carry relaxing authority.

Native event forwarding must also preserve bridge ordering: an event
received during an outstanding `Bridge.call()` must not immediately enter
`Chrome.steps()` and make a nested browser read while the extension's
serial command is still running. Commit its observation/check context
without browser I/O, and prepare a resumable step only after the current
command completes. Actual notification delivery across navigation needs
strict Linux receiver and owner-warning evidence.

### Private observed-step repair and regression coverage

The builder added a private isolated-world report callback, an authenticated
background queue, shared post-dialog/post-input `collectSteps()`, and
`Chrome.observe_step()` to commit an open check without browser I/O.
Reviewed this changing worktree based on `76d39fa2`. **Read:** native
observation handling performs only store reads/writes, avoiding the nested
bridge-call deadlock described above. Stale or missing frames are handled
without interpreting old element IDs in the replacement document. A reply
with a still-open dialog now remains unknown instead of claiming completion.

At the builder's explicit delegation, this reviewer added five Node
regressions to `background.test.mjs` (no production edits):

- actual background dialog answering plus actual page/guard code collects
  the resumed handler's `native_submit`, with **zero native arrivals**;
- an authenticated queued `activation_unknown` survives replacement of its
  source document and is forwarded only once, including a late repeat;
- private notification and later polling of the same document/frame/step
  produce one result;
- the runtime handler rejects a wrong extension sender, generation,
  uncontrolled tab, invalid frame and malformed kind/document, and obtains
  frame identity from the sender rather than the payload;
- queued and polled steps together must respect the 512-step plus one
  truthful overflow-warning limit.

**First run:**
`node --test control/chrome_tests/background.test.mjs`:
**14 tests, 13 passed, 1 failed**, 2266.932 ms. The strict last regression
exposed another **P2 bound bypass**: `observeStep()` capped its queue, but
`collectSteps()` inserted every polled step into an unbounded Map before
merging it. Six hundred polled steps plus the queued overflow produced
more than 513 results. The failing assertion at line 179 was retained and
sent immediately to the builder for a production fix.

These VM tests exercise source identity, dispatch and notification behavior;
they do not prove Chrome delivers the isolated message before a real
document is destroyed. That part remains a strict Linux receiver check.

### Acknowledged collection and retired-control retest

The builder subsequently changed collection to retain private observations
until an explicit `ack_steps` command after the service commits its result
or preparation. The service now leaves an observed check open if a modal
prevents its document check; it does not treat the modal's empty frame view
as proof that the old document disappeared. A committed prepared-operation
identity prevents an acknowledgement retry from reserving that same held
submission again. **Read:** acknowledgement follows the corresponding
`Store.write()`; observation receipt still performs no browser I/O.

At the builder's additional test delegation, this reviewer updated the
queue tests to require retention until acknowledgement and added regressions
for modal retention and retired controls. **Run:**
`node --test control/chrome_tests/background.test.mjs`:
**16 tests passed, 0 failed**, 3839.107875 ms, against working files based
on `76d39fa29cb6ddf205e707a2354d7e42fcbcf992`.

The strict previously failing combined poll/queue cap now passes: at most
512 individual steps plus one truthful unknown overflow warning, retained
until acknowledged. Repeated collection under a modal does not clear the
queue; after the modal closes, repeated collection returns the same source
step until acknowledgement, and a late repeat cannot resurrect it.
The retired-control test uses a fake timer: late observations are accepted
for the captured old epoch, while `assertControl` still rejects acting
under that epoch, including after a new control epoch is installed. The
tombstone expires after the configured 900,000 ms and the retired map stays
at its 32-entry bound. No long timer was started by that test.

`git diff --check` was clean. Only the authorized
`background.test.mjs` regressions and this report were edited by this
reviewer. The collection/lifetime findings now have focused source/Node
repair evidence; native notification delivery, navigation/default action
and independent receiver behavior remain Linux-runner verification work.

## Focused native-input lifecycle review before batch 46

Reviewed the next uncommitted lifecycle changes based on `76d39fa2`.
At the builder's explicit delegation, added four browser-free lifecycle
tests in `background.test.mjs`, and updated the existing keydown-modal
fixture's `tabs.update` mock so it still reaches the CDP race it tests.
No production implementation was edited by this reviewer.

**Run:** `node --test control/chrome_tests/background.test.mjs`:
**20 tests passed, 0 failed**, 4430.865625 ms. The new tests establish:

- all frame guards are armed before the headed tab is activated; the fresh
  binding read follows activation and precedes native input; a label changed
  by activation refuses before keydown;
- release removes acting authority and wakes both a pending CDP input and
  an effectful content call, detaches the debugger before page clearing, and
  completes when the fake one-second clear deadline fires even if the page
  never answers;
- a tab update awaiting fresh tab data cannot release a replacement control
  object; the handler uses the fresh tab's actual group instead of the
  stale event snapshot, while a genuine current group change still releases;
- a late detach event preserves a live replacement attachment, and a failed
  probe associated with the old control cannot release its replacement;
  failure of the actual current attachment still releases it.

**Read:** the private post-input control check, object identity checks and
attachment probe align with those tests. No new blocker was found in this
limited lifecycle source review. The fake timer test starts no long timer;
no browser, profile or container was used. Headed focus behavior and actual
Chrome event/attachment ordering remain batch-46 runner evidence, not a
result of these Node mocks. This is still an interim review.

## Flat event payload, navigated-frame finish and destination retest

Reviewed changing working files based on
`6bcbc124559740bd46a9d59e1b0dd7f78b4b6e4c`, following the builder's report
that runner batch 46 still had failing named rows. Those runner results
were not independently inspected by this reviewer in this pass.

Added authorized Node regressions (no production edits):

- flat lazy event fields preserve key/code/modifiers in a **fresh untrusted
  event**, without passing the original page-owned Event object;
- protected targets do not demand the original input event's data getter;
- a flat primitive getter that changes a harmless button's name to Delete
  completes before final classification, so activation is held;
- cleanup failure for a genuinely replaced native frame preserves queued
  holds; the same native document without completion, or an unavailable
  replacement check, sets uncertain completion;
- actual background input replies retain the queued unknown activation and
  propagate `uncertain_finish` instead of dropping the observation;
- GET and POST form destinations changed to an excluded host during arming
  refuse both input and resumption, with **no supplied binding**, proving
  the fresh destination check itself is decisive. The tests require two
  fact reads, completed arming, and no focus/input/resume/native dispatch;
- an allowed GET search destination still reaches native keydown/keyup
  without a binding.

Coordinated test ownership with the independent security reviewer, who
added separate sticky per-getter protection, blocked-search and interrupted
finish tests. Their production fixes were reviewed here only within this
focused source scope. **Read:** MAIN exposes lazy primitive payload fields;
the isolated guard constructs a fresh untrusted event, rechecks protection
while demanding payloads and classifies after page-owned getters finish.
`finishFrames()` no longer lets a missing iframe cleanup discard the private
queue, and the service maps uncertain completion to `unknown` for both
approved and free input.

**Run evidence:**

- Initial combined run: **55/56 passed**. The new propagation test lacked a
  `chrome.tabs.get` mock after the selected-tab read was introduced. Fixed
  that test model with an explicit active-state read and update; no
  production code or assertion was weakened.
- `node --test control/chrome_tests/background.test.mjs control/chrome_tests/page.test.mjs`:
  **56 tests passed**, 5390.617291 ms, after that correction.
- `node --test control/chrome_tests/*.test.mjs`: **73 tests passed**,
  5415.19275 ms. This preceded adding the two final destination tests.
- `node --test --test-name-pattern='destination' control/chrome_tests/background.test.mjs`:
  **2 tests passed**, 567.582125 ms, covering the negative and positive
  destination paths above.
- Small actual-Engine Python probes: `uncertain_finish` returned operation
  state **unknown** for an approved input and a free input.
- Generated and compiled the four current sandboxed native-fallback
  variants (cancelable/noncancelable, self/sink). All compiled; each
  requires proving a native function before calling it. No fixture script
  was executed. Whether sandboxing actually supplies the required genuine
  native function is still a browser-runner assertion.
- `git diff --check`: clean.

No new unaddressed defect was found in this limited retest. These passing
plain Node/Python checks do not turn batch 46's reported failures into
passes; final receiver sets and real Chrome event/navigation behavior are
still pending. No SAFE or final qualification claim is made.

## Modal-safe pending validity before the final runner batch

Reviewed the next uncommitted repair on a worktree based on
`50dc1b90556db66d1c0e90077442bb025f3f2566`. The builder reported that
batch-48 policy run `42664908151` reached 36/37 named rows but disconnected
the host when pending validity attempted renderer `ready` behind a native
dialog. That runner trace was supplied by the builder; this reviewer did
not independently inspect it in this pass.

Added four authorized actual-dispatch Node regressions in
`background.test.mjs`:

- an already-open modal refuses validity before any renderer message;
- a modal opened during pending `ready` wakes and returns a transient
  `refused` error promptly, with no effect and no remaining private waiter;
- no-modal validity preserves the ready document/element facts and source
  frame, without input;
- a modal opened while native frame metadata is being fetched refuses
  before `ready` starts, covering the intervening await as well.

**Run:** the targeted validity command passed **4 tests**, 40.454208 ms.
The complete `background.test.mjs` subsequently passed **30 tests,
0 failed**, 5979.071375 ms. Small actual-source VM probes also confirmed
that a modal during step polling returns no steps while retaining the
queued observation and disposing both waits, and that Stop during `ready`
returns `stale_reference` with `effectStarted:false` and no waiter leak.

**Read:** content requests now reject an existing modal and race private
modal/Stop notification, distinguishing a read-only refusal from an
effectful unknown outcome. Best-effort `clear` is exempt from that waiter:
it can remain queued through release's bounded cleanup without adding a
new waiter after the release wake. The existing release regression still
passes. High-level native dialog facts remain separately readable.

No new blocker was found in this focused source/Node retest. The modal
timeout repair still needs the final authorized Linux runner set; these
tests neither establish that run nor issue SAFE. Only the authorized test
file and this report were edited by this reviewer.

## Final focused closure and package-pin source check

Working-tree review based on
`40d6a04d670fc704cccb19102cf32be25eb6f685`. **Run:**

- The committed-state command above passed **11 tests in 0.139s, OK**.
  `test_unreadable_committed_projection_prioritizes_warning_inside_three_notice_bound`
  now verifies the exception branch: the explicit Chrome-unavailable marker
  is first and the complete compact envelope remains at three notices.
  **Read:** that branch prepends the marker and caps the combined list.
  The exception-path cap finding is closed at focused source/test level.
- `PYTHONPATH=control python3 -m unittest discover -s control/chrome_tests -p 'test_publisher.py' -v`:
  **5 tests in 0.059s, OK**.
- Direct `qualify.packages()` probes accepted an exact synthetic official
  stable/beta filename plus 64-digit lowercase hexadecimal checksum and
  rejected a foreign-host filename, path traversal, wrong architecture,
  wrong package name, nonhex checksum and short checksum.
- `git diff --check` was clean.

**Read:** package URLs are constructed under the fixed official HTTPS
repository from an exact validated filename containing the selected channel,
full package version and amd64 suffix. Both branch fixtures and qualification
pairs pass the resolved URL and SHA256 to Docker. The Dockerfile checks the
downloaded file's checksum before installation; `run.sh` compares the actual
installed full Chrome version with the requested version before tests start.
Qualification pairs use the current driver's CI/tests with the separately
checked runtime build; branch fixture jobs do not enter the main-only
qualification publisher. No new defect was found in this limited pin-path
source review.

No Google package was downloaded, Docker build run, browser started, or data
branch written by this reviewer. Actual pinned-package installation, both
installation routes, attestation and the complete final receiver sets still
need runner evidence. This remains an interim review, not SAFE.
