# Empire brief 317 — 20-store-oracle-reads: the notice left after a finished replay (N8), reads refused while a notice stays queued (N9)

Lead: `linux-tools`. Written on 2026-11-20 against main `897f2717`. Revised on 2026-11-21 after
review 1 and again after recheck 1 (`reviews/20-store-oracle-reads/BRIEF-REVIEW-1.md`,
`BRIEF-RECHECK-1.md`), against main `f4d59cc6`.
Follow-up to brief 302; it closes board T386.
The code was read at `4442c676`; `control/`, `reviews/19b-owner-state/` and the oracle workflow are
unchanged from there to `f4d59cc6`.
Builder: Claude Opus, one fresh agent per step; the lead picks the model at launch.
This is a build brief, not a build. Its writers changed no product code and dispatched no workflow.

Read `AGENTS.md`, `docs/design/CONTROL.md` (section 4 and "The bar") and `control/README.md:185-202`.
Then brief 302 (`briefs/20-store-oracle-followups.md`) and, in `reviews/20-store-oracle-followups/`,
`REPORT.md` and `CLASSIFICATION-CHECK.md`: its N1 is our N8; its N3, C3 and part of N4 are our N9.
Then the two "Named class" sections in `reviews/19b-owner-state/KNOWN-GAPS.md:706-757`.

**Outcome.** Two store changes, no change to the owner-state oracle, one line in Chrome's state
view, one re-pin.
- N8: start-up drops a queued recovery proposal when its replay finished the proposal's source or
  saved a notice under the proposal's id.
- N9: a read on a fixed list is answered again when its request met a storage refusal before
  dispatch. Everything else stays refused, Chrome's page reads included. The owner set the goal
  (board T385, 2026-11-19: "Merge, fix reads later").
- With N9, two Chrome paths that are on main today are closed. A barred request sends the browser
  nothing, and no request asks it before its flush; a waiting Chrome approval is then listed from
  its saved row as `unchecked`. A request the owner's sites page makes while a browser command
  waits no longer takes that command's reply.

Paths are repo-relative. Line numbers are at `4442c676`. Under `control/`: `storage.py`, `recovery.py`,
`engine.py`, `results.py`, `requests.py` are in `aresos_control/`, as are `chrome/` and `mail/`;
`model.py`, `driver.py`, `compare.py` are in `owner_state_oracle/`.

**The bar (decision 24, `docs/design/CONTROL.md:348`), for the builder and every reviewer.**
Reasonable safety for an MCP service, not every edge case. Real harm gets fixed: a repeated send or
delete, a write or app effect in a request that met a storage failure, a lost owner change, a hidden
warning or unknown outcome, unsaved state shown as saved. A low-harm edge case becomes one line under
"Known limits" in the report, not another fix round.

## Review 1

| # | Finding | What changed | Where |
|---|---|---|---|
| 1 | BLOCKER. The drop rule left a queued generic notice to overwrite a replayed acknowledgement, or an exact warning whose check stays open. | A second condition: the replay saved a notice under the proposal's id. That row stays as replayed and the source is not touched. | Section 1, "When a queued proposal is dropped"; tests f, g |
| 2 | BLOCKER. A nested owner request replaced the outer request's barrier and first error. | `Engine.request` keeps the outer observations across re-entry, and a nested request starts with the outer barrier. | Section 2, decision 4; test g |
| 3 | BLOCKER. Chrome's reads have effects outside `Store.write`. | The line is a fixed list of answered reads, no longer `changing()`. Chrome's page reads stay refused. In a barred request `mode()` neither configures nor maintains, and open checks are not reconciled. | Section 2, decisions 1 and 3; tests b, i |
| 4 | BLOCKER. A barred Mail status put an unsaved warning into the recorded operation. | In a barred status the operation is the saved row. The warning and both matches stay in the evidence. | Section 2, decision 5; test h |
| 5 | SHOULD-FIX. Named mutations pass their tests. | Tests read the queue when the drop returns; b8 replays a real `unknown`; refused requests are proved by a spy on `_request`. One mutant is removed as equivalent. | Both "Tests"; "Reviewer mutations" |
| 6 | SHOULD-FIX. Four `restore` cases never complete locally. | Identified: two `.close` points, which the hosted sweep skips. The local gate uses the hosted selection and compares case inventories before keys. | "Local matrices" |
| 7 | SHOULD-FIX. The capture has no semantic stop rule before the pin. | The capture is classified over all flows and pairs before the pin is committed. The pending-section discrepancy is measured on the base first. | "Capture and proof"; build step 1 |
| 8 | NIT. The overlap table. | Corrected against `cd2ce599` and `c95c350d`. | "Overlapping work" |
| — | View: the restart wording. | A queued `background-storage` notice has no durable source. | "Known limits" |

## Recheck 1

Findings 1, 2 and 4 to 8 of review 1 are closed. Finding 3 stayed open in two places, both
reproduced on main before this revision ("Writers' local evidence").

| # | Finding | What changed | Where |
|---|---|---|---|
| 1 | BLOCKER. A barred request's all-app pending section sends `validity` or `typed_fields`. In the extension both can release a tab, clear its holds and staged uploads, or inject a reader. | A barred request sends the browser nothing. A reserved Chrome approval is listed from its committed row as `validity: unchecked`, or `refused` where saved state already says so. `mode()` refuses in a barred request. Chrome's state view accepts `unchecked` in a reply that is not `ok`. | Section 2, decision 3; tests i3, i4; "Existing tests" |
| 2 | BLOCKER. The first pending pass runs before the flush, so a request can send `configure`, prune upload copies and refresh qualification before it is refused. A nested owner request reads the outstanding command's reply. | Both are on main today. The first pending pass of every request takes Chrome's rows without asking the browser, and so does every pass of a nested request. | Section 2, decisions 3 and 4; tests i5, i6, i7 |
| 3 | NIT. The restart promise. | Every barred answer carries the first storage error; only a latched store adds the restart advice; a first fence that was undone needs no restart. | Section 2, decision 8; "JUDGMENT-CALL" |

**The lead's calls on revision 2's open points (`linux-tools`, 2026-11-21).**
- **The uniform rule stands:** once a request is barred, nothing goes to the browser, including when it becomes
  barred during its own dispatch. The one acceptance line in Chrome's state view (`unchecked` allowed in a reply
  that is not `ok`) is part of this package. Deciding at the gate only would keep a live `validity` after a
  storage failure, the effect recheck 1 called real harm.
- **Requests refused without a barrier:** replaced after recheck 2 (its finding 2, below): a reply to a request
  refused for a storage error uses passive Chrome rows too, with or without a barrier.
- **Healthy requests' first pass** no longer asks the browser, so another app's request no longer applies a
  changed excluded-sites list while a typed-read approval waits. Accepted, with recheck 2's finding 3: the
  configuration step runs before the first live projection probe of any later pass.

## Recheck 2

Recheck 2 (`reviews/20-store-oracle-reads/BRIEF-RECHECK-2.md`, Codex gpt-6.2-sol) closed recheck 1's finding 2
(the first pass and the nested reply) and finding 3 (the restart wording), agreed with the uniform rule and the
state-view line, and left four points. The lead settled them here as binding rules for the builder; none
changes the design above, each adds a guard and its test. They come before the hosted capture.

| # | Finding | Rule for the builder | Test and mutation |
|---|---|---|---|
| 1 | BLOCKER. A barrier inherited from a nested request mid-command (for example during an approved upload's first `stage_file`, the owner's `chrome_sites` write hits an undone first fence) leaves the outer handler free to send another `stage_file` and `input`, or to run housekeeping after `configure`. | Check the request's barrier before every new browser command (one shared guard, see "May change") and before any housekeeping after `configure`. The outstanding command's reply is still drained, so the bridge stays in step; nothing new is sent once the barrier is set. | (a) The nested storage fault during the first `stage_file` of one approved file larger than 512 KiB (so the upload needs a second chunk): no second `stage_file`, no `input` in the trace. Mutation: drop the shared guard; the test fails. (b) The fault during `configure`: the expired upload copy is still on disk and no qualification refresh ran, which the command trace cannot show. Mutation: drop only the post-`configure` check; the test fails. i7.2 asserts the full post-barrier trace. |
| 2 | BLOCKER. With a surviving latch and nothing queued, a request refused at `ensure_writable` before dispatch (for example `mail_operation_cancel`) still runs `configure` and upload pruning in its all-app error reply. | Once a request has observed a storage refusal (a barrier, or a storage-error refusal at admission or at `ensure_writable`), its replies use passive Chrome rows, as a barred request does. `ensure_writable` itself does not change. Healthy reads in a latched store keep their live checks. | An empty-queue latch test with i5's zero-effect assertions (no `configure`, no pruning, no `validity`, no `typed_fields`). Mutation: gate the passive rows on the barrier only; the test fails. |
| 3 | SHOULD-FIX. A healthy `control_pending` whose ordinary row comes first sends `validity` before `configure`, so `requireTab` can use the extension's old excluded-sites list. | The configuration step runs before the first live projection probe in any pass that asks the browser. | A test with the ordinary row first and a newly excluded host asserts `configure` precedes `validity`. Mutation: probe before configuring; the test fails. |
| 4 | NIT. Make the named tests' assertions explicit. | i4 gets a spy proving the patched handler called `mode()`. i6's `queued_steps` assertion uses a same-session open check whose peer reply keeps it open. i3 uses distinct saved reasons, so a replaced reason fails. | As written in recheck 2's finding 4. |

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
- **The same collision with the source still unfinished (review 1).** The first pass queues a
  proposal only for an id that has no saved `notice:` row (`recovery.py:98`, `:104`). The replay can
  then save a row under that id, and the flush writes the proposal over it:
  - *An acknowledgement.* `notice_ack` of a recovery notice that was never saved writes its
    `notice:` row with `ack: true`; for an operation or an export it writes nothing else
    (`engine.py:669-688`). Staged and not applied, it ends as a saved `ack: false`.
  - *An exact warning whose check stays open.* A filing's check result is staged with `check_open`
    and its exact warning under the filing's id. It ends as the generic text.

### Decision

**The store changes. The model is right.**

1. The notice is untrue. The staged event is the service's own record of the outcome. Start-up
   checked it against its fence (`storage.py:244-245`, `:448-458`) and applied exactly that event.
2. A crash a moment later, once SQLite has applied the same event, shows no notice today: the first
   pass already finds the source finished, or the saved row. The lost reply is the same in both cases.
3. A queued generic notice that replaces an exact warning or an acknowledgement hides a warning or
   loses an owner change. That is real harm by the bar.
4. Start-up already does this for Chrome.

Teaching the model to expect the notice would pin an accident of start-up's order.

**When a queued proposal is dropped.** Two things must not be confused:

- A *proposal* is an entry of `store.deferred_notices` under the action `control_intent_recovery`:
  generic text, in memory only, made by `recover_intents`.
- A *saved notice* is a `notice:` row. An acknowledged one has `ack: true`. An exact warning is the
  row an app wrote under that id.

The rule removes proposals only. It never writes, rewrites or deletes a row, and it never changes a
source. Right after a `_replay(event)` call in `Store._initialize` returns, and before any later
start-up write, drop a proposal with id `X` and source `S` (`source_key`, `recovery.py:106`) when one
of these holds:

- **A. The replay finished its source.** `S` is a key of `event['set']`, and
  `recovery.unfinished(store, keys={S})` (`recovery.py:14-46`) no longer yields `S`. Use that
  function. Do not write a second list of finished states.
- **B. The replay saved a notice under its id.** `event['set']` holds a non-null `notice:X`. That row
  stays exactly as the replay applied it: an acknowledgement stays acknowledged, an exact warning
  stays exact. `S` may still be unfinished. It keeps the disclosure it has without the proposal: the
  saved row, and for a filing its open check (`recovery.py:99-103`, `mail/filing.py:161-169`).

Both conditions read the replayed event, so the rule is keyed on what this replay did. After the
drop no proposal shares its id with a saved row: the rule `recovery_notices` itself applies when it
proposes (`recovery.py:104`).

Every other proposal stays queued:

- a source the replayed event does not set, unless B holds;
- a source the replay leaves unfinished, unless B holds: an operation that stays `submitting`
  (start-up turns it `unknown`, `storage.py:262-270`) or becomes `partial` or `unknown`, a filing
  still `started` or with `check_open`, an account not onboarded, an intent or export still present;
- a record-only tail: nothing is replayed and the store locks (`storage.py:245-248`);
- a failed replay: start-up fails, the queue dies with the process, the next start decides again;
- a legacy-intent source (`recovery.py:48-63`);
- a source that cannot be read: keep the proposal, or let start-up fail as any start-up read does.

The rule is one function in `recovery.py`, called after each of the three `_replay` calls, the
staged restore batch included. `confirm_restore`'s own call (`storage.py:958-959`) is not a replay
and does not change. Chrome's two rules stay. Leave `store.startup_intents` alone: `recovery_notices`
reads each source's current row again (`recovery.py:73`), so a finished source yields nothing, on
reads and on later writes (`storage.py:650-658`).

Rejected: not queueing before the replay at all (as for Chrome), or dropping every proposal after
it. `confirm_restore` queues through the same function, and with more than three unfinished sources
and a `submitting` operation start-up would save different notices than today. The drop removes
what the replay made untrue and moves nothing else.

### Tests

The names are purposes; the builder records the final ids. The second pass queues a wrongly dropped
proposal again, so the end state cannot show that a proposal was kept. Tests b1 to b3, b7 and b8
therefore wrap the drop function and find the kept proposal in `store.deferred_notices` at the
moment it returns, and then assert the saved notice.

Store, testapp (`tests/test_review22_storage.py` or `tests/test_restore_batches.py`):

- **a.** Dropped. Stop after staging a send's last write and restart on the copied bytes. The
  operation is `done`. No `notice:` row and no queued proposal exist for it. `control_pending` and
  `control_log` show no recovery notice. A later ordinary write adds none.
- **b.** Kept.
  1. Stop after staging an earlier write: the operation stays `submitting` and becomes `unknown`.
  2. Two unfinished operations (write the second row directly, as `submitting`); the replay
     finishes one. The other keeps its notice. The finished one has none, although the `unknown` write flushes the queue
     before the second pass.
  3. The replayed event sets the operation `partial`.
  4. A record-only tail: the store locks; after the confirm the operation is listed as `unknown`.
  5. The replay fails at its marker: start-up raises, the bytes hold no new notice, and a healthy
     restart then applies the same rule.
  6. A `notice:` row saved by an earlier start-up for the same source survives byte for byte.
  7. An unfinished source the replayed event does not set.
  8. The replayed event itself sets the operation `unknown`: stage a real `unknown` outcome (for
     example the fixture's `lost_answer`) and stop after staging it.
- **f.** An acknowledgement survives. Four interrupted exports; one start-up saves three notices.
  Acknowledge the fourth and stop after staging that write. After restart its saved row has
  `ack: true`, no proposal has its id, the export is unchanged and still unfinished, and the other
  three rows are unchanged. The rows equal those of a run where the same write finished.

Mail (`mail_tests/test_review26_recovery.py`):

- **c.** A filing's own last write is staged and not applied. After restart the saved notice is the
  filing's exact warning with its location pages, and the generic text is absent. The call's intent
  keeps its recovery notice: its completion was never staged.
- **d.** The intent-removal write is staged and not applied. After restart no recovery notice
  exists for the intent, and the filing's notice is intact.
- **e.** Chrome's recovery tests pass unchanged.
- **g.** An exact warning survives while its check stays open. A staged, unapplied write sets a
  filing with `check_open` and its exact warning under the filing's own id (for example the first
  check, with an unresolved role, of a filing that stopped without a restart). After restart the
  saved notice is the exact warning and not the generic text, the filing still has `check_open`,
  no proposal has its id, and a later healthy view runs the open check again.

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
- A barred request cannot write the store. `ensure_writable` raises the barrier before it looks at
  the latch (`storage.py:783-784`), and every write path calls it: `Store.write` (`:620`),
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

What review 1 showed, each checked in the code:

- **`changing()` does not tell which reads have effects** (`requests.py:28-32`). Chrome's page reads
  pass `mode()` (`chrome/adapter.py:204-217`). It sends `configure` when the excluded sites changed
  (`:209`; the extension then stops its controlled tabs, `control/chrome/extension/background.js:434`)
  and runs `maintenance()` (`:219-229`): expired upload copies are deleted
  (`chrome/uploads.py:21-22`), and a due qualification refresh fetches the record and writes a
  temporary file before its store write (`chrome/qualification.py:194-213`). `chrome_read` also
  commits page steps and acknowledges finished ones in the extension (`chrome/adapter.py:791-796`).
- **Shared sections ask the browser too.** The pending section checks every reserved Chrome
  operation (`chrome/adapter.py:297-302`): a typed-read approval through `typed_binding` and so
  `mode()` (`:252-253`, `:406-408`), any other through the `validity` query (`:259`). Main's refusal
  already does this. Live notice views reconcile open page-step checks with `queued_steps` and
  store writes (`:769-786`, called from `engine.py:86` and `chrome/adapter.py:909`).
- **`Engine.request` is re-entered.** While the bridge waits for a reply it handles events
  (`chrome/bridge.py:76-84`), and an `owner_sites` event calls `Engine.request`
  (`chrome/adapter.py:132-133`, `:142-144`, `:193-197`). The nested call replaces
  `store.observations`, and only `in_request` is restored (`engine.py:751`, `:771`): the outer
  request loses its barrier and its first error.
- **Mail status merges live evidence into the operation.** Evidence that sees two Sent copies sets
  `sent_copy_warning`; when its result write is refused it adds `warning_storage_error` and returns
  (`mail/adapter.py:835-856`). The handler copies the warning into the operation's stages, and
  `public_operation` appends it to the reason (`engine.py:642-645`, `:425-427`). Review 14's tests
  pin this for a request whose own write fails (`mail_tests/test_review_fixes_22.py:22-48`).
- **Mail's server reads start nothing.** `mail_folders`, `mail_search`, `mail_read`, `mail_thread`
  and `mail_contacts` open folders read-only (`mail/adapter.py:162-165`, `mail/transport.py:190-191`)
  and write neither the store nor a file.
- **Both oracles expect live checks.** After a recheck that met the latch the model expects the
  "not yet checked" notice (`model.py:495-499`, `:549-556`), so a passive Mail view would need an
  oracle change. Chrome's state checks expect live validity in an answered `control_pending`
  (`control/chrome_tests/chrome_oracle.py:93-98`, `state_views.py:57-62`). Their flows never queue
  a notice, so none of their requests is barred before dispatch. Thirteen cases are barred during
  dispatch: in flow `stopped` of `test_fault_surface.py`, persistent mode, `control_pending` loses
  its own write and answers from the storage fallback (`engine.py:144-200`), and main sends
  `validity` after the barrier is set. Main's other tests read `validity` through `engine.pending`
  outside a request (`test_committed.py:54-61`, `test_state_fixes.py:95-99`,
  `test_qualification_service.py:251-253`).

What recheck 1 showed, each reproduced on main ("Writers' local evidence"):

- **`validity` and `typed_fields` are not passive.** In the extension both start in `requireTab`
  (`control/chrome/extension/background.js:980`; `:964` through `:803` and `:764`). For a controlled
  tab that left the Claude group it calls `release` (`:638`), which ends control, drops the tab's
  holds and staged uploads and reports `released` (`:696-710`). `typed_fields` injects the reader
  into a frame that has none (`:786`, `:284`), and `requireTab` can do so for a popup that is still
  setting up (`:651`).
- **The first pending pass runs before the flush** (`engine.py:752`, `:755`), in every request of
  every app, and it includes Chrome's rows (`:217-218`). With a reserved typed-read approval, a
  changed excluded-sites list, an expired upload copy and a due refresh, a `mail_accounts` request
  sends `configure`, deletes the copy, reaches the refresh and sends `typed_fields`. Only then is
  its flush refused, in both fault states. The refusal's section then does the housekeeping and
  asks again. With an ordinary reserved operation it sends `validity` before and after.
- **Nobody needs the first pass's Chrome rows.** The pass only keeps a snapshot for a later storage
  failure (`engine.py:116`). Both fallbacks drop Chrome's rows from it and read Chrome's projection
  again (`:131`, `:177-182`). Only `daemon.py:279` shows it whole, when the pending read after a
  failed request raises.
- **A nested request takes the outer command's reply, with no storage fault.** An `owner_sites`
  event handled while a command waits (`chrome/bridge.py:75-84`) enters `Engine.request`, and its
  pending passes send `validity`. That call reads the reply the outer command waits for and
  refuses it by its identity (`:85-86`); the outer call then does the same with the nested reply.
  With a healthy `chrome_tabs` and one reserved operation the outer reply is `transport_error`.
  Under a latch with a queued notice the same happens inside the refusal's pending section. With
  nothing reserved it does not happen. The sites page asks for its list whenever it opens and
  after every button (`control/chrome/extension/details.js:9`, `:30`).
- `chrome_sites` itself sends no command (`chrome/adapter.py:850-874`), and the sites page reads
  only `ok`, `error.message` and `data` of its reply (`details.js:8-28`).
- **The held Chrome packages already have the row.** Their `pending_state` returns
  `UNCHECKED = {'validity': 'unchecked'}` when a check runs out of time, and the row keeps the
  operation's own reason (`chrome/deadline.py:24` on both held branches).
- `pending_state` is called only for the projection (`chrome/adapter.py:301`). Its saved-state
  checks (`:235-248`, `:256-258`) read the journal, the owner's list and the store, and ask the
  browser nothing.

### Decision

**A read on a fixed list that meets the barrier gets the refusal it gets today, plus its page. A
barred request starts nothing: no store write, no browser command, no file change, no write through
a nested request. No request asks the browser before its flush.**

1. **The answered list.** `requests.py` gets one explicit set of names next to `changing()` and one
   predicate over it. The predicate is true only for a well-formed request on the list.

   | Request | Barred | Why |
   |---|---|---|
   | methods `tools`, `pending` | answered | the catalogue; saved rows without a live check |
   | `control_pending`, `control_log`, `control_notices`, `control_observations` | answered | saved rows, today's audit up to SQLite's head, queued notices, the detail pages of the last oversized reply |
   | `mail_accounts`, `mail_filing_notices`, `mail_filing_locations`, `mail_operation_status` | answered | saved rows and queued notices |
   | `testapp_list`, `testapp_operation_status` | answered | the fixture's own rows |
   | `chrome_notices`, `chrome_operation_status` | answered | Chrome's committed projection (decision 3) |
   | `mail_folders`, `mail_search`, `mail_read`, `mail_thread`, `mail_contacts` | answered | They show the mailbox, not saved state, but start nothing. On a latched store with nothing queued they are `ok` today. |
   | `chrome_tabs`, `chrome_downloads`, `chrome_bookmarks`, `chrome_history`, `chrome_read`, `chrome_find`, `chrome_read_form`, `chrome_wait` | **refused** | They show a live page, not saved state. Each passes `mode()`, and `chrome_read` and its siblings commit and acknowledge page steps as they read. |
   | `chrome_read_typed_fields` | **refused** | It spends an approval through `Engine.submit` (`chrome/adapter.py:884-889`). |
   | every action whose effect is not `read` (the owner's `chrome_sites` list included), `upload`, `download`, `saved`, `mail_account_add` | **refused** | as today |
   | anything else: a malformed request, an action added later | **refused** | A new read is refused until someone lists it. |

2. **`_admitted_request` changes.** It reads the barrier once. A barred request that is not on the
   list raises the barrier before anything else, as today: zero dispatch, and a malformed request
   still gets the storage refusal. A barred request on the list goes on to `envelope` and `_request`.
   Its reply then takes the passive all-app pending section the refusal has
   (`self.pending(resolve_checks=False)`, `engine.py:794`) in place of its app's own. A request that
   is not barred takes today's path. The mutating branch, the error paths and the `finally` stay.
   Mail's live checks run as they do today on a latched store with nothing queued: add no passive
   mode for them. The barrier in `ensure_writable` refuses their writes. Chrome's checks are off
   (decision 3).
3. **Chrome: when a request asks the browser.** Only after its first pending pass, while it is not
   barred, and when it is not nested. Outside a request nothing changes.
   - **Barred** is one predicate (`in_request` and a set `write_barrier`); a read-only method on
     `Store` is allowed for it.
   - **The row.** `pending_state` runs its saved-state checks as today, and a row they refuse reads
     `refused` with its reason. Where it would go on to `typed_binding` or `validity`
     (`chrome/adapter.py:253`, `:259`) and the request may not ask, it returns
     `{'validity': 'unchecked'}`: no `mode()`, no browser command. The row keeps the operation's
     own `reason` and has no `refusal_code`, like the held packages' row. Nothing else in a
     pending row changes.
   - **The first pending pass** (`engine.py:752`) takes such rows in every request, healthy ones
     too: nothing can know yet whether the flush will be refused. `Engine.request` turns one
     request-scoped switch off for that call and on after it; `pending_state` reads the switch.
   - **A nested request** keeps the switch off to its end, and `Engine.request` puts the outer
     value back. It sends no command, so it cannot read the reply the outer command waits for.
   - **A barred request** gets such rows in every pending section, and in `data` of
     `control_pending` and of the method `pending`. `Chrome.reconcile_open_checks` returns at once;
     open page-step checks stay listed from committed rows (`chrome/adapter.py:271-276`).
     `Chrome.mode()` raises the barrier's error as its first statement. Nothing on the answered
     list calls `mode()`: the check keeps a handler that goes on after its own write was refused
     from configuring, pruning or fetching. The rule holds for a request barred during dispatch
     too, which is why Chrome's state view gets one acceptance ("Existing tests").
   - Page reads and the asking read are refused at the gate (decision 1).
   - Unchanged: the service loop's maintenance and event handling (`daemon.py:119-124`,
     `:211-236`), `engine.pending` called outside a request, and every pending section a healthy
     request that is not nested builds after its first pass. There `control_pending`, a Chrome
     reply's own section and the page reads ask the browser as today.

   What a healthy request loses: the first pass's answers, which nothing read, and, while a
   typed-read approval waits, that pass's `mode()` in requests of every app ("Known limits").

   What the owner's tools show while barred: the storage error first; every app's waiting work from
   saved rows; a waiting Chrome approval with `validity: unchecked`; Chrome's warnings from
   committed rows, open checks included. The Stop hook hands that section on as it is
   (`hooks.py:132`, `:57-58`). The approval cannot be used in that state, since changes are
   refused. After the restart it reads `refused`: the service session changed
   (`chrome/adapter.py:240-241`).
4. **Nested requests: nesting never clears a barrier or a first error.** Only these lines of
   `Engine.request` change, and those of decision 3's switch.
   - On entry, if a request is already in progress, keep its `Observations` object. The nested
     request gets a fresh one. If the outer request is barred, the fresh one starts with the same
     `error` and `write_barrier`.
   - On exit, put the outer object back. If the nested request ended barred and the outer one was
     not, the outer one takes that barrier, and that error if it has none. Today it ends up with
     both by accident; this keeps it.
   - A nested request under a barrier is then an ordinary barred request. Its flush is refused
     before any byte. A change such as `chrome_sites` is refused with the first error, and
     `owner_reply` shows the owner that refusal (`chrome/adapter.py:199-202`). Nothing is queued for
     him: he sees that it failed and repeats it.
   - A barred request no longer waits on the browser, so an event is handled inside one only when
     the request became barred during the wait: an earlier event's write (`held_step`, `released`)
     was refused. Later events of that wait meet the barrier.
5. **Mail status: in a barred request the operation is the saved row.** In the `operation_status`
   branch (`engine.py:634-652`), note before asking for evidence whether the request is already
   barred. If it is, do not copy the live `sent_copy_warning` into the operation (`:643-645`), so
   its stages and reason are those of the applied row. `data.evidence` keeps `sent`,
   `sent_copy_warning` and `warning_storage_error`, and `observations.evidence` keeps the same: the
   warning is shown, and labelled as not saved. A request that is not barred when it asks for
   evidence keeps today's reply ("Known limits").
6. **`recorded_write` and the flush do not change.** `recorded_write` keeps setting the barrier for
   every storage refusal. The barrier is what refuses the read's own writes and what marks the reply.
   The flush runs once before dispatch, as today, for reads too. When it fails the notice stays
   queued and nothing retries it in that request. Without a latch the next healthy request saves it.
   Under a latch nothing can, and the restart drops the queue ("Known limits").
   `Store.ensure_writable` and `Observations.finish` do not change either.
7. **What a read shows.** Saved state: SQLite's applied rows (`storage.py:834-899`), today's audit
   events up to the SQLite head (`:812-829`), Chrome's committed projection, and a waiting Chrome
   approval as its committed row with `unchecked` (decision 3). Never a staged event
   that is not applied, the failed write's intended rows, or a check result that could not be saved
   shown as saved: the notice says "not yet checked" (`mail/adapter.py:807-813`), and
   `operation_status` adds `evidence_error` (`engine.py:646-650`) or labels its live evidence
   (decision 5). Three things in a reply are not saved state, and each is told apart: a queued owner
   warning with its location pages, which a healthy page shows too; live evidence under
   `data.evidence`; the mailbox content of a Mail server read. A reply that shows a warning still
   queued is never `ok`: its request tried the flush and failed.
8. **What the reply tells Claude.** `ok` is false. Every barred answer carries the request's first
   storage error. A surviving latch makes that `journal_incomplete` and adds the restart advice. A
   fresh failure reports its own cause (`common.py:38-43`), with the advice only if it left the
   store latched. A first fence that was fully undone reports its cause without the advice: no
   restart is asked for, and a fresh request is served once storage recovers. `data` is the
   page; a read that fails for its own reason has none, and the storage error still comes first.
   `pending` lists what waits in every app and its newest three notices, queued ones included. The
   proxy hands Claude the whole reply (`proxy.py:250-251`); `aresos control log` prints it
   (`cli.py:75`). No new field and no new text: `COMMON_INSTRUCTIONS` already says "Storage failures
   return ok=false and the first storage error" (`definitions.py:52`), and Chrome's instructions
   have 3 characters left.
9. **The five flows and the N4 share.** One rule covers them. The gate does not ask who queued the
   notice: `filing_copy`, `filing_move`, `filing_rename`, `expiry`, `maintenance`, or start-up. The
   background-storage notice returns to the page because the page lists queued notices.

Why the refusal's pending section: the model expects the all-app section in every reply that
carries a storage error (`driver.py:490-493`), and the Stop hook reads that section from a reply
that is not `ok` (`hooks.py:132`). With its app's own section a `control_log` read lists no
operation.

Rejected:

- A "writes are paused" field on every read during a latch. It needs a reply-schema change,
  instruction text there is no room for, and a model rule 302 decided against ("do not allow it on
  every later read"). A read with nothing queued shows nothing unsaved, and the first change says it.
- Answering Chrome's page reads. A side-effect-free `chrome_read` would have to skip its page-step
  commits and acknowledgements and still report the stopped steps. That is Chrome work, and the
  Chrome packages rewrite those paths now.
- Keeping `validity` and `typed_fields` in a barred request (revision 1). Neither is passive in the
  extension, and `typed_fields` passes `mode()`.
- A passive query in the extension, one that skips `requireTab` and the reader. It changes the
  extension, so its build and qualification, on paths the Chrome packages rewrite now.
- The flush before the first pending pass. That pass is the snapshot for the case where the failed
  write leaves SQLite unreadable (`engine.py:144-153`); taken after the flush it would be the
  previous request's.
- Leaving Chrome's rows out while barred. The owner would not see that an approval waits.
- A guard in the bridge against a command inside a command. It would close the nested collision
  too, but both Chrome packages rewrite the bridge, and the switch does it in lines this brief
  already changes.
- Deciding at the gate only, so that a request barred during dispatch keeps its live rows and
  Chrome's state view needs no acceptance. It leaves `validity` after a storage failure in the
  very flows Chrome's own checks run.

### Tests

Mail (`mail_tests/test_review_fixes_24.py`). Run every case in two states, each with a queued
notice: a fresh first-fence failure (store not latched: `storage_limit`, no advice) and a surviving
latch (`journal_incomplete` with the advice).

- **a.** Answered: every Mail, control and testapp entry of the list and the methods `pending` and
  `tools`. `ok` is false. `error` and `pending` equal those of the refused change in b; assert that
  `pending` lists an operation of another app. `data` is present and shows the queued notice where
  the page has notices. The notice is still queued. Journal and SQLite bytes are unchanged. No SMTP
  command and no IMAP mutation happened, the server reads included.
- **b.** Still refused, with no `data`. A spy shows `_request` was never entered, and no adapter
  was called: `mail_operation_cancel` (the operation stays `reserved`), `mail_send` with its
  approval, `mail_move`, `mail_compose`, `upload`, `download`, `saved`, `mail_account_add`, the
  owner's `chrome_sites` list, a malformed request. A table over every action in
  `definitions.ACTIONS`: each is on the answered list or on an explicit refused list in the test,
  the two are disjoint, and together they are complete, so a new action forces a decision.
- **c.** Under the latch three reads in a row answer the same. After a restart reads are `ok` and
  a write works.
- **d.** Not latched, fault gone: a new request saves the notice, and reads are `ok`.
- **e.** A read's own write is still refused. With the barrier set and the store not latched, a
  live `control_pending` whose Sent-copy recheck tries to write changes no byte and shows "not yet
  checked". The existing `where='admitted'` case still passes.
- **f.** Saved state only. Stop a write after staging, keep the latch, queue a notice.
  `control_pending`, the operation's status and `control_log` show the row as SQLite has it and no
  audit entry for the staged event. After a restart they show the replayed write.
- **h.** Barred status.
  1. A saved open Sent-copy check and two live matches. `data.operation` equals the public form of
     the SQLite row in `approval`, `stages`, `state` and `reason`. `data.evidence` has both matches,
     `sent_copy_warning` and `warning_storage_error`; `observations.evidence` has the same. No
     `evidence_error`. No IMAP mutation, no byte changed.
  2. A saved clean check: `evidence_error` says "not yet checked", and `data.operation` is the row.

Base (`tests/`):

- **g.** Nesting. Make the nested call from inside the outer dispatch, from a patched adapter read:
  a barred request no longer waits on the browser. Test i7 does it on the wire.
  1. Outer request barred by a one-time first-fence failure; nested `chrome_sites` list as the
     owner. The nested reply is the refusal with the outer's first error. The notice is still
     queued and no byte changed during the nested call. The outer reply is not `ok`, has the same
     first error and its page, and a write the outer request tries afterwards is refused. Then an
     independent `chrome_sites` list is `ok` and the notice is saved.
  2. The same under a surviving latch: the independent retry is refused too, until the restart.
  3. Outer request healthy with observed evidence; the nested request meets a first-fence failure.
     The outer reply is not `ok`, carries that error and its own `observations`, and its later
     writes are refused.
- `tests/test_review23_results.py`: an answered read whose page plus pending exceed the limit is
  bounded like any reply and keeps error, advice and warnings; under the latch
  `control_observations` then pages it, barred as well.

Chrome (a new module under `control/chrome_tests/`; CI picks up `test_*.py` there). Both fault
states, a queued notice. The recording browser logs every command by name, `validity`,
`typed_fields`, `configure` and `queued_steps` included; the stand-in in `test_engine.py:26-45` logs
none of those. Read the log from request entry, never from the flush. Tests i4 to i6 use a real
`Bridge` as in `chrome_tests/test_qualification_service.py:69` (`maintenance()` returns at once for
a stand-in, `chrome/adapter.py:221`), a temporary `upload_dir` with an expired copy, a due refresh
with a recorder in place of the fetch, and a changed excluded-sites list.

- **i.**
  1. Each of the eight page reads and the asking read: the first storage error, no `data`,
     `_request` not entered, no browser command.
  2. With an open page-step check: `chrome_notices`, `chrome_operation_status`, `control_pending`,
     `control_notices` and `control_log` are answered. The open check is listed. No browser
     command. No byte changed.
  3. Rows (recheck 1, blocker 1). A reserved ordinary operation, a reserved typed-read approval
     and a third whose deadline has passed (set through a store write, as
     `test_state_fixes.py:125` does). For a barred `mail_accounts`, `control_pending`, the method
     `pending`, a refused `mail_operation_cancel` and a refused `chrome_tabs`: the browser saw no
     command from request entry to the reply. In `pending`, and in `data` of `control_pending` and
     of the method `pending`, the first two rows read `unchecked`, keep the operation's own
     `reason` and have no `refusal_code`; the third reads `refused` with the deadline reason.
     Fails today: `validity` and `typed_fields` are sent.
  4. `mode()` called inside a barred request (from a patched handler of an answered read) raises
     the first storage error: no `configure`, no fetch, no `.qualification-*` file, and the copy
     is still there.
  5. From request entry (recheck 1, blocker 2). A reserved typed-read approval; the fault state
     is armed before each request. `mail_accounts`, and a refused change: from entry to the reply
     no `configure`, no `typed_fields`, no fetch, no `.qualification-*` file, and the copy is
     still there. Fails today in both states: `configure`, the pruning, the refresh and
     `typed_fields` all happen before the flush is refused.
  6. A request that is not barred keeps its checks. No fault, nothing queued: `control_pending`
     is `ok`, both rows read `current`, the browser saw `configure`, `typed_fields` and
     `validity`, and the copy is pruned; a `mail_accounts` request sends the browser nothing. On
     a latched store with nothing queued and no refresh due, `control_pending` shows both rows
     `current`, `chrome_tabs` reaches the browser, and a live `chrome_notices` sends
     `queued_steps`.
  7. Nested, on the wire (recheck 1, blocker 2). A real `Bridge` over a socket pair, a scripted
     peer, one reserved ordinary operation. While `chrome_tabs` waits for `tabs`, the peer sends
     an `owner_sites` list event and then the `tabs` reply.
     1. Healthy. The outer reply is `ok` with the tabs. Between `tabs` and its reply the peer got
        no command. The owner's reply is `ok`, and its Chrome row reads `unchecked`. The outer
        reply's own row reads `current`: the switch is back on. Fails today: both calls end in
        `transport_error`, "Chrome response identity changed".
     2. When the event arrives the test queues a notice and arms a one-time first-fence failure.
        The owner's reply is the storage refusal, and the peer got no command for it. The outer
        call returns its own `tabs` reply; the outer reply is not `ok`, carries that first error
        (g3), and its row reads `unchecked`.

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
- `mail_tests/test_review_fixes_22.py` stays as it is: its requests are not barred when they ask
  for evidence.
- **One acceptance in Chrome's state view.** `control/chrome_tests/state_views.py:57-59` compares
  `validity` of every reserved row in an answered `control_pending` with the live state. In the
  thirteen cases named under "Verified facts" (flow `stopped`, persistent, local points 145-149,
  151, 168-173 and 175) the row now reads `unchecked`, and the comparison fails with "Cached or
  missing live validity". They were found without the cleanup pairs, which may add cases of the
  same shape. As written, the check requires the browser query recheck 1 forbids. It gets one
  line: in a reply that is not `ok`, a reserved row may read `unchecked`; every other value, and
  every row of an `ok` reply, is compared as today. What the check guards stays guarded: a
  verdict that is shown is never a cached one. `chrome_oracle.py` does not change. Chrome's other
  Python tests stay as they are.
- No other test should change. A scratch prototype of the first version's two rules failed only the
  review 25 test, of 29 base tests, 53 Mail tests and the sweep module's 16 unit tests. Decision 3
  is prototyped against Chrome's Python tests ("Writers' local evidence"). The list, the nesting
  rule and the status branch of revision 1 are not prototyped.

## Build order and gates

Small commits. Keep `reviews/20-store-oracle-reads/PROGRESS.md` current: commands, outputs, counts.

1. **Baseline.** Merge main. Run the modules of the test sections as they are, and Chrome's Python
   modules that reach the engine: the list under "Writers' local evidence" (about 6 minutes) and
   `test_fault_surface` (3 minutes without its cleanup pairs; not timed with them).
   Record the local matrices and their case inventory (below) on the merge base under
   `.work/317/before/`. Measure the pending-section discrepancy there ("Capture and proof").
2. **N8.** The rule, tests a to g, its mutations. Commit.
3. **N9, engine.** The list and the gate, the nesting rule, the status branch; tests a to h, the two
   changed tests, their mutations. Commit.
4. **N9, Chrome.** The switch in `Engine.request`, the three checks in the adapter, the one line
   in Chrome's state view, tests i1 to i7, their mutations. Update `control/README.md:193-202`: a
   barred read on the list is answered from saved state with the error attached; Chrome's page
   reads wait, and a waiting Chrome approval is listed unchecked; start-up drops a recovery notice
   its replay made untrue. Commit.
5. **Local gate.** Record the matrices again and compare inventories, then keys, with step 1. Run
   `test_owner_state_capture` (3 tests), the sweep's unit tests and one alteration shard. Run
   step 1's Chrome modules again: same tests, same results. Push.
6. **Review.** A fresh package and security review runs the mutations before any hosted oracle run:
   a later code fix voids a capture.
7. **Capture, classification, re-pin, proof** as below, then the independent classification check.

**Local matrices**, with the sweep's own `exercise` and `Gaps(recording=True)`, one worker, at the
points the hosted sweep runs: every point whose label does not end in `.close`
(`test_owner_state_sweep.py:655-656`). Record per flow how many points that leaves out.
- live phases, both modes: `filing_move`, `filing_copy`, `filing_rename`, `expiry`, `maintenance`,
  `restore`;
- crash phase, both modes: `filing_move`, `attachment_export`, `flag`, `delete_permanent`, `send`,
  `cancel`, `restore`, `restart_index`, `restart_tail`.

Every selected case must complete on both sides. Write one inventory line per case (flow, mode,
point, phase, completed or the exception's first line) and compare the two inventories before any
key. A case that raises on either side is a stop, never a shorter comparison.

The four `restore` cases the first version reported are outside this selection: points 24 and 72
(`sqlite.main.close`), single mode, live and crash phase. Each stops in `exercise` on the confirm
assertion (`test_owner_state_sweep.py:231-235`, "A confirm that met a storage fault was answered
ok") before any view is compared, on main as well. The strict sweep never faults at a `.close`
point, so the pin holds no key for such a case and nothing is left uncompared. `restore` has 76
local points, 6 of them `.close`: 1, 2, 3, 24, 72, 76.

About 80 seconds per 700 cases on the laptop. The gate passes when the inventories are equal, there
is no new key, every `crash-locked` key is identical, and every change is a closure, an alias-only
renumbering, or one of the shapes under "Expected direction". Compare with paths normalised: export
flows carry the checkout's path.

For local runs use the managed-settings stand-in, the `PYTHONPATH` order and the export location of
brief 302 ("Build order and gates", its last three paragraphs), with `317` in place of `302`. No
installed-channel or root tests on the laptop, no `os/tests` owner modules, no mounts, no sudo.

## Reviewer mutations

The reviewer runs them one at a time in a disposable export. Each baseline passes. Each mutant fails
its named assertion, not an import, fixture or pin error.

| Mutation | Test which must reject it |
|---|---|
| Start-up as on main: no drop | N8 a, c, f, g |
| Condition A only | N8 f and g |
| Condition B only | N8 a |
| Drop every proposal after a replay | N8 b1, b2, b7, b8 (the queue when the drop returns) |
| Call the drop before the replay | N8 a |
| Decide by a list of states that calls `partial` or `unknown` finished | N8 b3 and b8 (the queue when the drop returns) |
| Drop only in the second pass | N8 b2 |
| Delete or rewrite a saved `notice:` row | N8 b6 and f |
| Remove the gate for every request | N9 b (`_request` entered) |
| Keep the gate for every read, as on main | N9 a and the review 25 test |
| Answer by `not changing()` instead of the list | N9 i1 and the table in b |
| Put the asking read or a transfer method on the list | N9 b and i1 |
| Check the barrier only at the gate, not in `ensure_writable` | N9 e |
| Let `recorded_write` set the barrier only for an undone first fence | N9 a under the latch (the pending section) |
| Keep the app's own pending section on an answered read | N9 a |
| Answer a barred read `ok`, or drop the advice | N9 a and c |
| Drop the queued notice when a read is answered | N9 a (still queued) |
| Serve a read from the staged event or the failed write's rows | N9 f |
| `Engine.request` as on main | N9 g1 (the outer reply) |
| Put the outer observations back, but start the nested request unbarred | N9 g1 (the nested call saves the notice) |
| Do not hand a nested barrier to the outer request | N9 g3 |
| Copy the live warning into a barred status' operation | N9 h1 |
| `pending_state` asks the browser in a barred request | N9 i3 |
| Return `unchecked` before the saved-state checks, replace the row's `reason`, or add a `refusal_code` | N9 i3 (the third row; the first two) |
| The first pending pass asks the browser, as on main | N9 i5 |
| A nested request asks the browser | N9 i7.1 (the outer reply) |
| Leave the switch off after the first pass | N9 i6 |
| Do not put the switch back after a nested request | N9 i7.1 (the outer reply's own row) |
| `reconcile_open_checks` as on main | N9 i2 |
| `mode()` as on main | N9 i4 |
| Key Chrome's checks on the latch instead of the barrier | N9 i6 (the latched store with nothing queued); i3 in the state without a latch |

Removed: "drop although the replay raised". A failed replay ends start-up and the queue dies with
the process (`storage.py:281-284`), so no behaviour differs. Test b5 keeps its assertions on the
bytes and on the healthy restart.

## One re-pin, after both changes

The pin is `reviews/19b-owner-state/KNOWN-GAPS.json`: 2,420,003 keys, 1,860 groups, 860,653 bytes,
SHA-256 `1b21f564533df6cdc1c99a5c4068d87538047f54a5243b6d0ed930d378ca2295`. Proof 44395635207
reproduces it from 52 lists. Format 3 and strict exact-delta checking stay.

**Expected direction.** No exact total is promised before the capture.

- **N8.** Its 124,173 `crash-restart` keys close. A key stays only if its delta also holds another
  fact; name each one. Other keys of those cases may change by alias numbers only, because a notice
  no longer takes a number.
- **The filing overwrite and condition B** are outside N8's count. Their keys lose the generic
  `recovery` fact. Some keep a residual that is older than this brief: the model expects a second
  filing occurrence the store never saved. Classify it; do not fix it here.
- **N9, new keys (N3).** The 11,095 close.
- **N9, changed keys (C3).** The 35,585 do not vanish: 302 changed them from an older delta to an
  empty page. Each now closes or returns to the delta it had in the pin before 302 (`8b27b116…`,
  proof 43972005458). A few return to that delta as 302's applied-row model moved it: a recovery
  notice the running store shows only after a restart (the check's N4, M06). None keeps the empty
  page 302 gave it.
- **The N4 share.** The 1,056 keys close.
- **Barred status.** An `operation-stages` mismatch on `sent_copy_warning` at a barred status
  closes, if the pin holds one. Name each.
- **New keys: none expected.** A new key is explained before the pin is committed, or it is a stop.
- **Unchanged:** the 376 contract, `G22-*` and channel keys; every `crash-locked` key; no
  `.restore-lock`, `startup-replay` or `crash-startup` key; all 34 clean-run point counts; every
  alteration shard `slipped=0`. The sweep holds no Chrome operation.

**Capture and proof.** Before the capture, fetch and merge main and check what changed under
`control/`, the workflow and the pin; settle drift first. Dispatch `control-owner-oracle.yml` on the
build branch with `ledger_only=false`. A strict failure against the old pin is capture evidence;
reject any other failure. Download the lists under `.work/317/`, merge them without conflicting
shared keys, and check that proof 44395635207's lists reproduce the old pin.

**Before the pin is committed, classify the capture.** A green proof only shows that a pin
reproduces; it cannot say a delta belongs there. With the builder's own script, sort every key of
the old pin and the new lists into identical, closed, alias-only, changed into a shape under
"Expected direction", or anything else. All 34 flows and the cleanup pairs, not only the local
gate's 13 flows. Stop with the pin uncommitted, and report, on: a new key; a changed `crash-locked`
key; a changed key outside the expected shapes; any delta that would need an expectation decision.

One discrepancy is known and is measured in step 1, on the merge base: a Mail flow with a testapp
reservation waiting and a barred `mail_accounts`. The envelope check expects the all-app pending
section (`driver.py:490-493`); the passive view check filters its expectation to the read's app
(`compare.py:293-296`). The reviewer's probe got 1/1 and 0/1. Main's refusal already carries the
all-app section, so the base should show the same. If it does, it is older than this brief: record
it under "Known limits" for the oracle's next brief, with whether any hosted flow has another app's
item waiting at a barred read. If base and build differ, stop.

Then regenerate with `owner_state_oracle.gaps` as `KNOWN-GAPS.md:759-771` shows. Commit the one new
pin with a new section in `KNOWN-GAPS.md`: counts by outcome and phase, N8 and N9 marked closed with
their numbers, the commands. Then dispatch the proof on that commit: 61 of 61 jobs green, its lists
equal to the pin byte for byte.

**How a reviewer confirms it.** An independent classification check, as 302 had: a fresh agent,
read-only, with its own scripts and not the builder's. It rebuilds both pins byte for byte with its
own packer and sorts every key of the union into closed, changed, alias-only, new and identical. It
recomputes N8's set and N9's three sets from the old lists by `CLASSIFICATION-CHECK.md`'s
definitions and follows each key. It compares every C3 key with its delta before 302. It writes
`reviews/20-store-oracle-reads/CLASSIFICATION-CHECK.md` with a verdict.

## CI budget

Kept from the first version: both revisions add unit tests, not oracle runs. The new Chrome module
runs in the Control Chrome workflow's Python shards, which every push already starts.

- **Owner oracle** (61 jobs, about 2.5 hours a run): one capture and one proof. No `ledger_only`
  run is needed. A third run needs the lead's OK first. 302 lost a capture to harness errors a local
  run would have shown, so step 5's gate comes first.
- **Control CI** (six workflows on every push to the PR): at most three pushes that carry code, then
  one rerun for the second green on the final head (`docs/REVIEW.md:44`). Progress and report
  commits carry `[skip ci]`.
- After a dispatch, write the run id into `PROGRESS.md` and stop. No agent waits on a run; the
  lead's watcher does (`gh run watch <id> --exit-status --interval 60`). On HTTP 403 wait for the
  reset and try once.

## Paths, and what must not change

May change:
- `recovery.py`: the drop function; `Store._initialize` in `storage.py`: its three calls; one
  read-only "barred" predicate on `Store`;
- `requests.py`: the answered list and its predicate;
- `engine.py`: `_admitted_request`; in `Engine.request` only the lines that keep, seed and put back
  the observations and those that set and put back decision 3's switch; in `dispatch` only the
  status branch's copy of the warning;
- decision 3's switch: one attribute, on the store next to `in_request` or on the Chrome adapter;
- `chrome/adapter.py`: the early return in `pending_state`, the barrier check in `mode()` and in
  `reconcile_open_checks`; for "Recheck 2": one shared guard that checks the request's barrier before
  each new browser command (in the adapter's command helper, or in `Bridge.call` before it sends,
  never between a send and the drain of its reply), the barrier check after `configure` and before
  maintenance (upload pruning, qualification refresh) in `mode()`, and in `pending_state`'s live
  branch the configuration step before its first probe, behind the existing passive checks; nothing
  else;
- the test files named above, one new module under `control/chrome_tests/`, and the one line in
  `control/chrome_tests/state_views.py`;
- `control/README.md:193-202`; `reviews/19b-owner-state/KNOWN-GAPS.json` and `KNOWN-GAPS.md`;
  `reviews/20-store-oracle-reads/`.

Must not touch:
- `results.py`: `recorded_write`, `Observations`, `RESTART_ADVICE`;
- `Store.write`, `_append`, `_finish`, `_replay`, `ensure_writable`, `flush_notices`, and the journal
  and SQLite formats;
- `definitions.py`, the tool schemas and the generated artifacts (`generate.py --check` stays clean);
- `owner_state_oracle/` and Chrome's state checks: no expectation changes beyond that one line.
  `FORMAT.md` only if a sentence becomes untrue;
- Chrome's committed projection, its pending projection beyond that one return and the configuration
  step before its first probe, its two recovery rules, the bridge beyond the one pre-send guard, and
  the extension; the restore-lock allow-list (`engine.py:575`); app approval,
  no-resubmission, storage reservations, the durability order;
- `.github/workflows/`, `os/`, `mod/`, the installed service.

Replies outside a barred request keep their codes, fields, paging, warnings and text.

**Overlapping work**, fetched 2026-11-21:

| Work | Overlap |
|---|---|
| PR #72, `pkg/28-chrome` `cd2ce599` (held until after R29's cut) | In `engine.py` it only puts `Engine.request`'s body under Chrome's `call_time`. Our nesting and switch lines go inside that body: whoever merges second re-applies them by hand. It rewrites parts of `chrome/adapter.py` and the bridge and changes the Chrome catalogue. It adds `chrome/deadline.py` with `UNCHECKED = {'validity': 'unchecked'}` and returns it from a re-indented `pending_state` when a check runs out of time. Ours is the same row: whoever merges second keeps one constant and both conditions. |
| PR #116, `pkg/28a-chrome-act` `b4cb60ed` (held likewise; `engine.py` unchanged since `1c67199b`; since `c95c350d` nothing changed in the functions named here) | The same wrapper, row and bridge rewrite, plus the `untrusted` import (`engine.py:15`) and `**untrusted(exc)` in both refusal envelopes (`_admitted_request` `:794`, `_request` `:893`). Keep the import and both expansions, and keep the answered read and its pending section inside `call_time`. It also rewrites `chrome/adapter.py` (`mode()` and `reconcile_open_checks` move), edits `control/README.md` away from lines 193-202, and edits `chrome_tests/test_engine.py`, which is why test i gets its own module. |
| Either Chrome catalogue landing | Recheck the answered list and the test's refused list against the new Chrome actions. A new read is refused until listed. |
| PR #76 `pkg/18c-b-chrome`, PR #82 | No file in common. |

## Stop rules

Stop, write the case into `PROGRESS.md` and report to `linux-tools` when:

- an oracle expectation, or one of Chrome's state checks beyond the one acceptance, would have to
  change to get green: for example an `ok` reply shows an `unchecked` row;
- an existing test other than the two named would have to change;
- a local matrix shows a case that raises, a new key, a changed `crash-locked` key, or a change that
  is none of the expected shapes;
- an answered read can only answer by writing, by configuring the browser or by changing a file,
  and the fix would be to let it;
- the change would reach beyond the paths under "May change";
- the capture fails anywhere but the strict comparison, or its classification shows a stop case;
- main moved under `control/`, the workflow or the pin;
- the CI budget is used up.

## Acceptance

1. Both rules are built as written; every named test passes; every mutation is rejected by its test,
   rerun by the reviewer.
2. The local gate passed and is recorded with its inventories and counts.
3. The capture failed only on the strict comparison and was classified before the pin; alterations
   `slipped=0`.
4. The new pin is committed with its classification; the proof is 61 of 61 green and reproduces it.
5. A fresh package and security review says SAFE; the classification check says CONFIRMED; Control
   CI is green twice on the final head.
6. `control/README.md` and `KNOWN-GAPS.md` say what the code now does.

## Report

`reviews/20-store-oracle-reads/REPORT.md` in `AGENTS.md`'s format (a Claude builder leaves the text
in `PROGRESS.md`). It also holds: capture, classification, re-pin and proof with run ids, counts and
the pin's SHA-256; the mutation table with the catching test's id and result; the changed tests; the
known limits below with any the build adds; what is left under `.work/` over 500 MB.

Known limits to record, none of them new harm:

- **Chrome's page reads and the asking read stay refused in a barred request**, as since 302.
  Before 302 they were answered. They show a live page, and reading one makes the browser side
  tidy up and commit page steps. A restart, or the next request after a one-time failure, ends it.
- A legacy-intent source keeps its start-up notice even when the replay completes it: its list is
  cached before the replay (`recovery.py:48-63`). A caution too many, on stores with old audit rows.
- A read during a latch with nothing queued says nothing about the latch; the first change does.
- A barred live view still asks the mail server read-only for open filing and Sent-copy checks whose
  result it cannot save, and shows "not yet checked" for a send whose saved check is clean. As today
  on a latched read; the model expects it.
- A status read that is not barred when it asks for evidence, and whose own result write is then
  refused, still shows the live duplicate warning inside `operation` (review 14,
  `mail_tests/test_review_fixes_22.py:22-48`). Its reply is not `ok` and names the failed recording.
- **While barred, a waiting Chrome approval reads `unchecked`**, also when its tab is gone or its
  page changed. It cannot be used in that state. After the restart it reads `refused`; after a
  failure that was undone, the next request checks it live again.
- **A request the store refuses without a barrier is not barred**: a change refused at the gate by
  a surviving latch with nothing queued, a quota refusal before any write,
  `chrome_read_typed_fields` refused by the latch at its submit. No longer a limit after recheck 2:
  its replies use passive Chrome rows once it has observed the storage refusal (rule 2 of
  "Recheck 2"), without making `ensure_writable` a barrier. Healthy reads in a latched store keep
  their live checks, as on main.
- A healthy request of another app no longer applies a changed excluded-sites list, or does
  Chrome's housekeeping, while a typed-read approval waits. The next Chrome request or all-app
  pending section does both, and the service loop does the housekeeping.
- A reply to the owner's sites page made while a browser command waited lists Chrome approvals as
  `unchecked`. The page does not show them.
- When the pending read after a failed request raises, `daemon.py:279` can show the first pass's
  rows, `unchecked`.
- Chrome events that arrive during a barred request wait for the service loop, like events between
  requests.
- The owner's sites page gets a refusal for a request that arrives inside a barred request. He
  repeats it.
- A queued notice lives in memory, and the restart the advice asks for drops it. A recovery notice
  comes back from its durable source, and the next live check looks again. A queued
  `background-storage` notice has no durable source and does not come back; barred replies showed
  it until the restart, and its cause is in the service log (`engine.py:248`).
- A proxy started while a notice is queued and storage fails still stops at start: its `tools`
  reply is not `ok` (`proxy.py:39-40`), as before 302. The error carries the advice.

## JUDGMENT-CALL for the owner

**None is needed.** T385 set the goal for reads, and the owner's answer to 302's question (board
T352, "Yes (recommended)") covers what he will see: the tools ask for the restart "while continuing
to show changes already saved locally". What changes for him:

- After a crash at an unlucky moment and a restart, no notice says "outcome unknown, inspect" for
  work the log shows as finished. A filing's exact warning is not replaced by a vaguer one, and a
  notice he acknowledged stays acknowledged.
- While a storage failure blocks a request, Claude can read again: mail, the log, what is waiting,
  an operation's status. Such an answer still carries the storage error, and changes stay refused.
  It asks for the restart only when a write was left unfinished. After a failure that was fully
  undone it does not, and the next request works once storage is back.
- One thing stays as it is since 302: in that state Claude cannot read a Chrome page or the tab
  list. Before 302 it could.
- In that state a waiting Chrome approval is listed as "unchecked", no longer as current or
  refused: the tools do not ask the browser then. Nothing can be approved in that state anyway.
- Opening Chrome's sites page while Claude works in Chrome no longer makes Claude's command fail,
  as it did whenever a Chrome approval was waiting.

Does the Chrome page point need his word? The writer's advice: no. T385 asked for the reads that
show saved state, a Chrome page is not saved state, and the state ends with the restart, or with
the next request after a failure that was undone. It belongs in the lead's summary to him as one
line, with the "unchecked" line. If the lead would rather ask, it is one board question that does
not block the build: "While a storage failure blocks the tools, should Claude also be able to read
Chrome pages?", with the advice "no, not in this package", because answering them safely is Chrome
work.

The technical calls are decided above with their reasons.

## Writers' local evidence

Scratch only: nothing committed, no prototype code adopted.

First version (2026-11-20; the full list is in this file at `29f79ee5`). Two exports of `4442c676`,
one with a prototype of that version's two rules, both with the managed-settings stand-in:

- Base engine probes reproduced both gaps. On the prototype a barred `control_log` returned the
  refusal's `error` and `pending` and its page with the queued notice, and changed no byte.
- The sweep's own `exercise`, every point, both modes, 7,190 cases a side: live phases of the five
  N9 flows; crash phase of `filing_move`, `attachment_export`, `flag`, `delete_permanent`, `send`,
  `cancel`, `expiry`, `maintenance`; both for `restore`, `restart_index`, `restart_tail`. Main
  against prototype: 16,433 keys closed, 17,764 changed in content, 1,630 changed by alias numbers
  only, **0 new**; every `crash-locked` key identical.
- Crash closures sit where the last event is staged and not applied, for example
  `delete_permanent` 370-411 and 413 in single mode: the hosted N8 window (374 to 415 and 417) less
  the stand-in's 4 points. The filing overwrite sits at `filing_move` 242-283.
- `filing_move`, live phases, also against the commit before 302: of 7,758 changed keys 7,722 are
  again the delta from before 302 and 36 differ by 302's applied-row model; 1,275 closed.
- Not run: `onboarding` and the other flows, cleanup pairs, alteration shards, Chrome's tests, any
  hosted workflow. Local point numbers differ from hosted ones; resolve points from traces.

Revision 1 (2026-11-21), on `f4d59cc6`:

- Read the code each finding names; the reviewer's probes were checked against it, not rerun. The
  revised rules are not prototyped: condition B, the list, the nesting rule, the status branch and
  Chrome's two checks are designed from the code.
- `restore`, every point, both modes, live and crash phase, with the stand-in: 304 cases in 139 s.
  The only cases that raise are the four named under "Local matrices".
- Branch heads compared: `origin/pkg/28-chrome` `cd2ce599`, `origin/pkg/28a-chrome-act` `c95c350d`.

Revision 2 (2026-11-21), on `f4d59cc6`. Scratch exports of the branch head, whose `control/` is
main's; temporary directories only, no network (a recorder stands in for the qualification
refresh).

- **Entry probe, main.** A real `Bridge` object with a recording call, a queued notice, a reserved
  typed-read approval, a changed excluded-sites list, an expired upload copy. `mail_accounts` under
  a surviving latch: `configure`, then the refresh and `typed_fields`, each twice, then the flush
  refused with `journal_incomplete`, then both twice again; the copy is gone. With a
  one-time first-fence failure the order is the same and the code is `storage_limit`. With an
  ordinary reserved operation: `validity` twice before the flush and twice after, in both states.
- **Nested probe, main.** A real `Bridge` over a socket pair. A healthy `chrome_tabs`, one reserved
  operation, an `owner_sites` list event before the `tabs` reply: the outer reply is
  `transport_error`, "Chrome response identity changed", and the owner's reply is `ok` with its row
  `refused` by the same error. Under a latch with a queued notice the collision happens in the
  refusal's pending section. With nothing reserved there is none.
- **Prototype of decision 3 alone** (14 lines in `storage.py`, `chrome/adapter.py` and `engine.py`,
  and the state view's acceptance; no list, no nesting rule). The entry probe shows no command
  from request entry in both states, the copy kept and the rows `unchecked`. The nested probe
  shows the outer reply `ok`, no command between `tabs` and its reply, and the owner's row
  `unchecked`.
- **Chrome's Python tests, equal on base and prototype:** `test_engine` 32, `test_questions` 35,
  `test_sites` 17, `test_committed` 24, `test_state_fixes` 21, `test_state_exhaustion` 1,
  `test_state_crashes` 1, `test_state_mutations` 1 (24 mutants killed), `test_state_oracle` 5,
  `test_storage` 16 (its sweep: 477 single, 477 persistent, 2,406 pairs; 255 s),
  `test_qualification_service` 24, `test_full_disk_reads` 10, `test_restore_lock` 5,
  `test_exclusions` 3, `test_bridge` 14, `test_unit` 1, and `test_owner_confirm` 15 with the same 2
  errors on both, from the export's location (a socket path too long, a workflow file outside the
  export).
- **The writer fault surface** (`test_fault_surface.py`, its own `sweep_case`): all 19 flows, every
  point, single and persistent, without the cleanup pairs, 4,260 cases on the prototype in 183 s.
  Without the acceptance 13 fail, all in `stopped`, all with "Cached or missing live validity";
  with it none. On the base `stopped` passes 166 and 166, and a trace of local point 145 shows
  `validity` sent twice after the barrier is set.
- Not run: the list, the nesting rule and the status branch; Mail and base tests against this
  revision; the fault surface's cleanup pairs, the latency and qualification-shard modules and the
  node tests; any hosted workflow.
- Branch heads compared: `origin/pkg/28-chrome` `cd2ce599`, `origin/pkg/28a-chrome-act` `b4cb60ed`.
