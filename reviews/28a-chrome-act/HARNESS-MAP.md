# Package 28a harness map

Step 2 of the [brief](../../briefs/28a-chrome-act.md#8-the-order-of-the-change).
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

## PLAN-GAPs kept on the legacy evidence path

Step 3a owns the following evidence paths.

- The password/field matrices, native tab and dialog observers, and exact fixture URL/document
  checks need the old structured rows, full URLs, session/frame/element IDs, field values or
  native index/focus/cleanup flags. The public outline/list intentionally omit some of this.
  Group 7 also explicitly checks the old read/form/find surfaces. Moving its action preserves
  those assertions. The feature form case still checks the hidden field's value, which the
  public outline omits.
- The review's preexisting-dialog handoff asserts the returned operation ID and its committed
  status. The public take result reports the handoff without that ID. The subsequent guarded
  click uses a short ref and `chrome_do`.
- The review's two before-first-reload cases assert the prior `reload` and `navigate` loss
  action and the original sequence of reloads. `chrome_go` first runs the guarded
  `first_input` check in a newly taken tab. The taken-POST setup also keeps its old
  same-tab move to a GET so the following public back call can test that POST history is
  refused. The scheme matrix's setup leaves the cross-frame password fixture directly because
  the guarded reload can fail on an unproven frame request method.
- **Group 8 REVIEW iframe drafts and detached or Web Audio report before reload**, dirty history
  row. Public Back reports `back` and returns to page one on the explicit repeat. In both
  installs and both qualification repeats, Forward from that restored document then reported
  `first_input`. Use direct legacy Forward for the refusal and its flagged repeat. The original
  assertions require `act: forward`, the same address until acknowledged, and arrival at page two.
- **Group 8 REVIEW script-started POST documents in tabs and popups never reload** uses direct
  legacy navigation only to leave the taken POST and load the popup opener in that same tab.
  `chrome_go` would try the guarded reload that the first part just proved is refused. Both
  POST clicks still use `chrome_do`, check the refusal reason and require exactly one arrival.
- Legacy close is used for cleanup of the owner-opened borrowed child and the forced-late popup.
  Public close keeps taken owner tabs. Their opener, control and receiver assertions remain.
- The feature catalogue checks assert unique native snapshot IDs for downloads, bookmarks and
  history. `chrome_library` gives address references, which can name the same address from
  separate native entries. Keep the old catalogue checks alongside the existing public library
  cases until removal work supplies equivalent evidence.
