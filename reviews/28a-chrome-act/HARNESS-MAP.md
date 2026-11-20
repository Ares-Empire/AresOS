# Package 28a harness map

Steps 2 and 3a of the [brief](../../briefs/28a-chrome-act.md#8-the-order-of-the-change).
The [package 28 map](../28-chrome-read/HARNESS-MAP.md) still governs its field-rule assertions.
The inventory and original receiver, approval, binding and outcome checks are the comparison for this move.

**Original migration counts.** 23 helpers changed or introduced and 23 existing cases with hand-built arguments moved.
The helper count covers the driver, routing and observation helpers, including the engine fixture's
two entry points. The case count is by named browser or engine case and includes stale/discard
replays and dialog arguments. Browser-free stand-ins, fresh assertions, and the legacy evidence
listed below are outside the case count.

## Helper calls

| Helper | Before | Step 2 |
|---|---|---|
| Browser catalogue and socket `toolName` / `rpc` | Bare replacement verbs go to `chrome_old_…`, `outline` maps to the current read. | Keep name lookup for historical runtimes and the measured old leg. Give the normal browser checks a separate routing helper. Explicit `chrome_…` calls use the wire unchanged, and the wire log records the actual tool. |
| Browser `call` / routed `rpc` | Return the brief 20 body for old aliases. | Use one-step `chrome_do` for click, fill, select, check, press, scroll and dialog. Use one list of fills for fill_form. Project the actual step, preparation, refusal and followups into the case's existing assertions. No action retry or lookup of a fresh ref on dispatch. |
| Routed evidence helper | Free input reported raw native reply, operation ID and post-input details. | Where the case asserts the old dispatch evidence, get the committed page stage for the exact step operation by `chrome_operation_status`. Use the actual outcome for success, unknown and refusal. |
| Browser `read` / row paging | Join legacy JSON rows, including raw field state, IDs and document/revision metadata. | Keep this observation for assertions that require it. Act on a short ref from a real `chrome_read` find or full outline captured at target selection. Keep the legacy row as evidence and use the same role/name/order selector. |
| Browser `target` / selected-row helper | Return an old row's reference and expected. | Return the public short ref alongside observation metadata. Map direct row choices into the same helper, matching exact labels and roles when the outline supplies them. |
| Browser `nav` and routed open/navigate | `chrome_old_open` / `chrome_old_navigate`, then an exact committed URL check. | `chrome_open` / `chrome_go` with the same URL or `to`; keep the committed URL check and fixture settle. |
| Routed take/release/close | `chrome_old_take_tab`, `chrome_old_release_tab`, `chrome_old_close_tab`. | `chrome_tabs` supplies `seen` for `chrome_take`; `chrome_release` preserves release evidence; `chrome_close` supplies each tab's closed or kept result. Preserve old calls explicitly where native/detail or ownership assertions require them. |
| Routed find/wait and read-dialog observation | Legacy find/wait and read's native dialog object. | `chrome_read` with find, a `chrome_do` wait for the text, and `chrome_read` to show the dialog at observation time. Preserve native dialog evidence and never prime a dialog by rereading at dispatch. The long view and the bank's balance check read through the full outline. |
| Browser caller / `call.py` | The synthetic MCP proxy maps old verbs via `BY_NAME`. | Keep that historical/explicit mapping. Pass `chrome_upload` explicitly with tab/ref/path through the same proxy transport, and keep the independent readonly upload and caller snapshot checks. |
| Popup `rows` / `target`, review `childTarget` | Parse legacy rows and copy the chosen target facts, also using document IDs for reload/install evidence. | Use the common target capture when the row is used for an action; keep native document and installation checks. |
| Brief 28 asking helper `approvedTypedFields` | Before 1d, use frame-shaped values; after 1d, match public rows to exact approved native document/reader/fields. | Keep both lanes. Short public references, display labels/descriptions and values still match the approved native evidence. |
| `ownerUI.open` and owner tab observers | 1d added genuine native tabs via the selected window and exact address. | Keep native creation, tab index, focus, cleanup, and the address observations. Public tabs shorten addresses and omit fields needed by those assertions. |
| Acting contextual `refOf` / `lineOf` | 1d allows a short ref before the find hit's contextual suffix. | Reuse the same short-ref grammar for migrated find selections, including fold/inlined controls and ` · in …`. Keep the existing acting cases on the raw public result. |
| Engine `Operations.call` / `prepare_do` | Group 1 uses the legacy target and prepare helper. | The public catalogue is requested explicitly. `prepare_do` reads Send's short ref and prepares the single step through `chrome_do`; the question, wrong-question refusal and exactly-once dispatch checks use the same submit path. |

The 23 helpers are `browser.mjs`'s `wire` (formerly `rpc`), `modern`, `nav` and `caller`;
`harness-tools.mjs`'s `harnessTools`, `fields`, `targetArgs`, `failure`, `lossReport`, `matchingRefs`,
`outline`, `readRows`, `selectedTarget`, `target`, `step`, `doResult`, `rpc` and `call`;
`popups.mjs`'s `targetFor` (replaces the local `rows` reader) and `target`;
`review-matrices.mjs`'s `childTarget`; and `test_engine`'s `Operations.call` and `prepare_do`.
The popup, owner-UI and POST stand-ins in `popups.test.mjs`, `owner-ui.test.mjs` and
`fixture.test.mjs` inject the moved row/target helpers and retain their timing and exact-tab checks.

`efficiency-probe.mjs` and `latency-probe.mjs` keep the measured calls and both old/new arms,
including the existing call name attribution, counts, ceilings and frozen comparison files.
The migration applies to the normal browser checks, including the smoke before measurements,
when the installed runtime offers `chrome_do`.

## Cases assembling a reference, expected or view

| Case | Old form | Step 2 form |
|---|---|---|
| Browser startup taken-tab smoke; group 8 taken tabs, repeated guarded reload and deadline/outside | Legacy read targets and spread `discard_unsaved`; compare original document and retry old reference. | Capture the short ref once, use its original tab on each attempt, and keep the separate native document and receiver observations. A real reload or release still stales the old ref. |
| Browser group 13 residual unlabeled click | Copy the first button row's legacy reference and expected. | Select the same legacy row, capture the short ref from an outline even when the name is empty. |
| Group 1 word/label/key matrix | First matching button or Continue row is handed to click or press. | Capture that row's short ref before either call, then dispatch via `chrome_do` for click, Enter and Space. Keep the exact word inventory and each 0/1/1 receiver check. |
| Other group 1 browser asking cases | Old click/press target facts on the picked control. | Original target selection through the shared helper, then `chrome_do`. The existing reference-open classification case already uses the public tools. |
| Group 4 exact native confirmation/mismatch and separately held form; review ordinary/inline/borrowed dialogs; site cleanup and confirmation/readonly dialogs; H1 native dialog | Copy `expected: dialog` after reading, with exact prompt text or accept flag. | Read the native dialog via `chrome_read` when it is observed, then send `{do:'dialog',accept,text?}` with its original tab. Existing approval mismatches and repeats are untouched. |
| Group 8 review borrowed wrappers and script POST popup | Build the other tab's reference from a JSON row. | Resolve Ready/Continue by short ref in the actual child tab. Keep document comparison, old error/outside tests and zero/one receiver checks. |
| Four group 8 popup cases | Copy the opener/child target facts, replay stale targets and compare the installed document. | Capture the short ref for the same row/tab; preserve explicit discard, document comparison, install path, native window and receiver assertions. |
| Site adapter two same-labelled Send rows | Copy the second Send row's reference and expected. | Capture the second exact button's short ref after verifying both observations, keep its original recipient, binding and receiver checks. |
| Group 7 password forms, late-reader form, unread taken field, and feature forms | Pass a field's legacy reference to read_form. | Retain directly where the case checks the old structured form surface or hidden value. Package 28's independent public outline checks remain. |
| Feature fill_form and readonly site fill_form | Send a list of legacy expected/reference fields. Old fill_form has to rebind the full-page view after the first mutation. | Pass the two original short refs as `fill` steps (or the one readonly field). Remaining fields and no dispatch on refusal follow from the real batch result. |
| Group 8 guarded handoff parser fixture, `review-reload.test.mjs` | Makes `reference.view` snapshots by hand to require two settled observations. | Keep the parser-settle assertion as fixture scheduling evidence. This is different from the item 2 action staleness check below. |
| Python old-tool contract fixtures and efficiency stand-ins | Construct legacy `reference` / `expected` / `view` explicitly. | Keep the legacy transport/baseline contract tests pending step 3. Public `chrome_do` coverage is additional. |
| Engine Group 1 exact approval and dispatch once | `Operations.target` used native `reference` with `view`, and `expected`. | `prepare_do` issues the ref through `chrome_read` and passes it to the public batch. Other old-tool Python contract calls keep their fixture. |

The 23 moved cases comprise nine direct row selectors (residual smoke, Group 1 word matrix,
review borrowed wrappers and POST popup, the four popup cases, and the adapter's second Send);
eight dialog cases (core confirmation and separately held form, review ordinary/inline/borrowed,
adapter mismatches and read-only, and H1); four stale/discard cases (initial taken smoke,
core taken tabs, review preexisting handoff and review iframe drafts); the feature fill batch;
and the engine's Group 1 approval case. Read-form and legacy parser evidence are mapped for step 3.

### Item 2 staleness rule

The former page-wide view comparison is exercised as **`ACT BRIEF28A the fingerprint refuses a changed element with its present line and keeps unchanged ones acting`**.
Keep the original saved short reference after another control changes neighboring text, position or state.
Require the input to dispatch with the same receiver evidence. After a semantic target change, require
`stale_reference`, the target's present line in `untrusted_content.now`, and zero dispatch from the refused input.
A genuine document replacement still makes the old reference stale in the smoke, review and popup cases.
Read cursor staleness keeps its independent whole-read token rule.
The browser-free `test_saved_reference_survives_an_unrelated_change_and_stales_when_the_target_changes`
in `test_doing` separately changes the neighbouring row and then the target between calls.

### Item 3b question descriptions

Keep the existing approvals, unread checks, re-asks and receiver counts. The rule established in step 0c
is distinct human descriptions in both the question and the content fields with the same native identities
and order. Keep `approvedTypedFields` and the blocked getter/identity assertions in the asking-read matrix.
Group 5's question case uses two Visible fields. The original Submit question still checks
hidden text, the password label and absence of its value. Its content describes both Visible
fields distinctly. Enter in the second field uses the second ref and checks the ordinal in the
question and in the target description, with zero receiver arrivals. Tests for repaired labels,
duplicate frames and mutations stay in `test_field_descriptions` and `outline-asking.mjs`.

### Item 5b loss envelopes

Keep the original reload/close receiver, unchanged-document and explicit-discard assertions. A bare
`chrome_go` refusal gives `error.untrusted_content.loss`; a `chrome_do` first-input refusal carries the
code/fixed prose on the step and the report at `data.untrusted_content.loss` with its step index. A
`chrome_close` refusal carries the report only in the matching kept row's `untrusted_content.loss`.
Check those envelopes before projecting them to the existing loss assertions. Keep labels out of trusted
prose and values out of the report. The step 0b transport/schema/hostile-label tests in `test_loss_errors`
and the existing stored-result checks remain.

## Step 2 reader fixes

The failed `205c7219` browser artifacts and both stable qualification repeats showed a legacy
target row followed by an empty public find. The fix keeps the same row selection and uses its
public short reference for `chrome_do`.

| Case | Reader repair | Evidence kept |
|---|---|---|
| Group 3 absolute destinations and Group 2 RECHECK3 native defaults | Show an image-map `area` as a link when its mapped image gives it usable bounds. | The original destination and browsing target, the re-ask and stale approval checks, the held native default and ping checks, and receiver counts. |
| Group 2 RECHECK payment and delete labels override GET search | Keep the native button role and visible `Pay` label on the editable submit button. | The handler stays stopped, the payment and delete controls still require approval, and the receiver counts stay zero, one, one. |

## Step 2, fix 2

- **Group 7, late shadow root.** Routed `rpc('fill_form')` keeps the public batch alongside its
  projection. A failed first fill exposes the step's actual code and message. A partial batch
  keeps the completed steps. An approval, deadline or batch error keeps its own result.
  In all four failed core artifacts the fill on Code was `unknown` with the reader's
  `owner_signin` reason and an empty `prepared` list. The failed pending IDs belonged to
  earlier operations. The green legacy fill reported the same uncertainty in its reason.
  Both the Code attempt and the successful Comment fill still use short refs and `chrome_do`.
- **Approval audit.** Compared approval counts by fixture address, kind, input verb and target
  name across all nine policy shard artifacts from `44604152322` and `44622916426`.
  The single addition was the item 3b Enter question in Group 5 above. The two preparations
  missing from the later core artifact belonged to `brief28-known` and `brief28-moved`,
  past the first failure. The late-shadow case added zero approvals.
- **Shard reporting.** The browser's `smoke` wrapper and the matrix's `check` use `recordCheck`
  to collect named results. `writePartialResults` replaces `failBrowserCase` and preserves
  failure evidence while the matrix continues. `assertChecksPassed` reports the failed names
  after the last check, before the shard can write its completion marker. Smoke checks and
  individual word routes participate. `pendingCheck` observes an in-flight rejection until the
  case awaits the original promise. The qualification inventory and its aggregate gate still
  require all nine shards.

## PLAN-GAPs kept on the legacy evidence path in step 2

Step 3a moves those paths to these channels. The step 2 tables above are the
historical mapping. The approval, receiver, binding and outcome assertions
use the existing named cases.

| Step 2 gap | Step 3a evidence |
|---|---|
| Structured password and unread-field data | Public `chrome_read` outline, full, find, until, multi-tab and form-by-ref replies. The Group 7 field counts, allowed draft, withheld values, known credential cases, getter and protocol ingress, and receiver and approval checks remain. Group 3 checks the public read refusal after a page submission is held. |
| Exact tab URLs, browser session, frame/reader element and document IDs, parser settle, native dialog ID/frame/guard, focus, index, sound and deferred cleanup | Admin socket observations from the instrumented extension copy. `CHROME_FIXTURE_OBSERVER=true` enables the two fixed observations in CI. After a restart, `chrome_tabs` establishes service readiness before the native focus and cleanup checks. Native rows use the current outline reader. A digest of its frame snapshots detects parser changes. The acting ref still comes from `chrome_read` at target selection. Public reads also show the native dialog kind and text before an answer. |
| Exact file and feature-form values, including the hidden input | The fixture receiver reports a single owner-selected file, the original hidden value, both filled texts and preservation of the hidden value. The form-by-ref and full public replies show the hidden name and options, with a negative assertion for the hidden value. |
| Preexisting dialog's operation ID | The admin fixture reads committed take audit rows bounded by the previous sequence. The commit and record name the same operation, and public `chrome_operation_status` checks that operation is done. The handoff, debugger detachment, session, stale ref and receiver counts stay checked. |
| First reload and direct address loss in a newly taken tab | Public `chrome_go` reports `first_input` before any native movement. One boundary slice checks command begins and flat CDP dispatches in order. It requires one guarded reload for a reload request, and a guarded reload followed by one navigate for an address. Chrome's tab-tagged start events confirm the exact tab and URL of both effects. The fixture receiver checks one load before acknowledgment, two after a reload, and one destination arrival for an address move. The watched dirty reload still asserts `act: reload`. The watched address rows still assert `act: navigate`. |
| Forward from the dirty restored history entry | Public Forward on the restored page reports its first-input or Forward loss, with zero native dispatches in the boundary slice. The acknowledged repeat must arrive at page two, with its tab-tagged history start event, or refuse before a native dispatch when Chrome cannot prove the restored request method. A watched dirty document with two fragment history entries independently exercises `act: forward`, keeps the exact prior address on refusal, and arrives at the second address once acknowledged. The boundary requires one history dispatch, the reply and native address identify the exact tab, and the receiver requires one document load. |
| Taken POST setup's GET, script-started POST to popup opener, leaving the cross-frame password fixture | Owner address-bar navigation with the exact tab and address verified, then the original public input and history refusals. The POST cases still count one receiver arrival for each POST. |
| Borrowed child's and forced-late popup's cleanup | Owner UI closes the exact normal tab or native popup window after the receiver and control assertions. |
| Native library IDs | The three native catalogue passes remain until 3b. The same fixture inventory now checks public library paging, stable totals, address refs and download file names for all three kinds. |

## Retired with the old tools

The legacy-only Group 7 comparisons already use their carrying cases below.
The native catalogue and browser-free alias contracts are kept until the
catalogue is removed in 3b.

| Legacy-only assertion | Carrying test on the new surface |
|---|---|
| Group 7 preliminary show-password and qualification password reads as JSON rows | The same smoke and qualification cases check public replies; **GROUP 7 BRIEF28A no password reaches the new tools results questions or records** covers action and stored results too. |
| Group 7 all password kinds across roots and frames, legacy read and six `read_form` replies with the visible draft | The same case reads all six forms by public ref and checks the draft, the absence of the password, approvals and receiver counts. |
| POST18D credentials and revealed passwords, old read/form kinds and withholding before and after take | **GROUP 7 POST18D credentials and revealed passwords stay unreadable before take reload** checks full and form-by-ref replies. **GROUP 7 POST18D typed field reads require exact one-call approval and reask on list changes** checks the unchanged asking read and the public outline after it. |
| Group 7 fields made plain, late roots and the unread taken form, old read/find/form rows and empty/filled/password flags | **GROUP 7 BRIEF28 fields made plain before the reader came stay unread in every root and frame**, **GROUP 7 BRIEF28 a shadow root met late and the name rule keep secrets unread in a watched document**, and **GROUP 7 BRIEF28 the new read holds no password in any form of read** cover public field counts, full/detail, find, until and multi-tab. **GROUP 3 BRIEF28 a form holding an unread field is refused unasked for a click Enter and a page submission** covers the later read and the zero receiver checks. |
| Feature form legacy hidden value and options | **FEATURE tools forms options find wait fill_form scroll and full catalogues** now checks the fixture's value independently, the hidden name without its value in public full and detail, options and the visible fills. |
| `chrome_old_downloads` native IDs and filename snapshot | The feature case's `chrome_library` downloads pages and `test_small_tools.test_the_library_shows_short_addresses_and_a_reference_per_entry_that_opens_the_full_address`. |
| `chrome_old_bookmarks` native IDs | The feature case's `chrome_library` bookmarks pages and the same public library entry test, including bookmark-folder shape. |
| `chrome_old_history` native IDs | The feature case's `chrome_library` history pages, plus `test_small_tools.test_library_references_live_as_long_as_their_snapshot` and the acting address case that opens a history ref. |
| CI-only catalogue registration and forwarding in `test_outline_action.Switch` | Public `chrome_read` engine/schema/size checks in the same module. Step 3b replaces the temporary-switch assertions with absence of the removed names. |
| `test_excluded_sites_28a.Sweep`'s old catalogue entries | The same sweep keeps its public entries and asserts settings-unavailable without reaching the page. |
| `ProxyUpload.test_the_new_upload_and_the_old_one_read_the_path_on_the_callers_side`'s legacy upload | The current branch of the same test checks exact caller bytes, the file snapshot and `chrome_upload`. |
| `test_outline_time.Read.test_brief_20s_read_carries_no_time_with_an_approval_outstanding` | The `chrome_read` deadline and pending validity tests in the same module. |
| `test_acting_references.test_brief_20s_reference_and_expected_keep_working_until_the_switch`'s private legacy adapter route | The same module's stale element, changed present line and single dispatch checks on the short-ref path. |
| Old bare, staged and batched loss response shapes in `test_loss_errors.LossEnvelope` | The same module's `chrome_go` untrusted loss, `chrome_do` indexed refusal and `chrome_close` per-item checks, plus the review matrix's public bare/kept/step envelopes and receiver assertions. |

### Remaining `chrome_old_` call sites

**40 source call sites** can reach old wire names. Repeated samples and
parameter rows count once per source expression. The two private `old_click`
adapter calls in `test_acting_references` are separate from that count.
The sites below are due to go with the old catalogue in 3b.

| Count | Site and aliases |
|---:|---|
| 8 | `latency-probe.mjs`: history seed read, measured navigate, committed-address read, measured read, free click, fill, asking click; `harness-tools.mjs`: the measured target's paged read. The historical runtime still uses its own unprefixed catalogue verbs. |
| 16 | `efficiency-probe.mjs`: F1 first read and every page, paged find shared by F1/F3/F4, F1 form page, F2 continuation, open and wait, F7 click and wait, F5 click and read, three-tabs read, 25-tabs list, F4 old fill batch and click, first-read setup for the old rows. The shared setup, new legs and cleanup use public calls. Frozen definitions and recorded call plans stay as committed. |
| 1 | `matrices.mjs` feature catalogue's `oldCatalogue` paging loop dispatches `chrome_old_downloads`, `chrome_old_bookmarks` and `chrome_old_history`. |
| 3 | `test_outline_action.Switch` probes `chrome_old_tabs` through the proxy, CLI and engine. |
| 1 | `test_excluded_sites_28a.Sweep.test_every_read_and_action_is_refused_and_reaches_no_page` sweeps `chrome_old_tabs`, `downloads`, `bookmarks`, `history`, `take_tab`, `release_tab`, `close_tab`, `open`, `navigate`, `read`, `find`, `read_form`, `wait`, `click`, `fill`, `select`, `check`, `press`, `scroll`, `upload`, `fill_form`, and `dialog` (all with the same prefix). |
| 1 | `test_small_tools.ProxyUpload` crosses the caller snapshot path once with `chrome_old_upload`. |
| 1 | `test_outline_time`'s brief 20 timing contract calls `chrome_old_read`. |
| 9 | `test_loss_errors.LossEnvelope`: the old bare error matrix (`navigate` and `close_tab`), first-input `fill`, stored `navigate`, partial `fill_form`, malformed and hostile-text `close_tab` (two), numbered and duplicate `close_tab` (two), and ordinary refused `navigate`. |

The alias selection in `browser.mjs` and `call.py` and frozen comparison
labels in `efficiency-summary.py` and its test data are names or routing,
rather than additional dispatched cases.

### Step 3b removal

- The 16 catalogue-contract sites retired. The feature matrix still visits all
  three public library catalogues. The never-list sweep still covers the public
  catalogue. The upload test checks the caller snapshot, and the public read
  tests keep their deadline and pending checks. The catalogue tests now check
  absence, including when the former switch is in the environment.
- The 24 comparison sites now use public calls or have no live task.
  `browser.mjs` uses `harness-tools.mjs` for the current latency leg and keeps
  the historical runtime's own unprefixed tools for the runner comparison.
  The historical and current sample counts and ceilings stay in the existing
  latency gate. Group 16 retains the frozen plans as data. It runs each public
  task with one warm-up and five measured samples, and compares every measured
  sample with 1.5 times its task's median in the run.
- `test_outline_action` also had private close and release routes outside the
  inventory. Its public close and release cases keep reference cleanup and
  prove a refused close preserves the references. The two private old-click
  cases retire with their handler. The pending deadline fixture issues a
  short reference before it prepares the operation.
- The structured loss tests use the public navigation, batch and close shapes.
  The close cases carry malformed, hostile and indistinguishable labels through
  the real bridge parser and the public reply. The refactored catalogue checks
  for absence replace the temporary proxy, CLI and engine alias probes.
