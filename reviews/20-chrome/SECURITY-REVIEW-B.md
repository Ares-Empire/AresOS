At `60b94384`, I found **10 blocking findings and 3 should-fix findings** in angle B.

I made no edits and ran no browser or container. The new counterexamples below are browser-free probes of production Python functions and JavaScript executed with the existing Node DOM doubles. They are not new browser receiver experiments.

1. **Blocking — equivalent key spellings bypass deletion classification.**

   Where: [sites.py:99](../../control/aresos_control/chrome/sites.py:99), [policy.py:89](../../control/aresos_control/chrome/policy.py:89), [background.js:165](../../control/chrome/extension/background.js:165).

   Classification examines the original key string, while dispatch separately interprets it. My Python and Node probes produced:

   ```text
   "#"       → gmail_delete / delete
   "Shift+#" → no adapter / free

   Both dispatch:
   {key:"#", code:"Digit3", modifiers:8, windowsVirtualKeyCode:51, text:"#"}
   ```

   Consequently, the existing Gmail inbox fixture’s deletion shortcut can be invoked through `chrome_press(key="Shift+#")` without preparation. `Shift+Delete` and `Shift+Backspace` also bypass the generic outside-text deletion rule, although dispatch still sends those deletion keys.

   **Reproduction:** on the Gmail inbox fixture, target “Selected message” and compare `#` with `Shift+#`. Require both to prepare before the fixture’s key handler receives input.

   **Fix:** parse and canonicalize keys once, before classification, adapter recognition, and dispatch. Classify the resulting key/modifier tuple consistently; apply outside-text Delete/Backspace protection to modified variants too.

2. **Blocking — malformed URL escapes make the service and page guard disagree about asking controls.**

   Where: [policy.py:105](../../control/aresos_control/chrome/policy.py:105), [guard.js:56](../../control/chrome/extension/guard.js:56).

   Python uses tolerant `unquote()`. JavaScript uses `decodeURIComponent()` and returns the entire undecoded address when any escape is malformed.

   I tested a non-submit “Continue” button inside a form with these action addresses:

   ```text
   https://fixture.test/%73end
       service: send; page-script click: held

   https://fixture.test/%73end?bad=%ZZ
       service: send; page-script click: delivered; no hold
   ```

   Thus a free input’s handler can call that asking control’s `.click()`, and its handler runs without approval. This is one of the script activations §6 explicitly requires stopping.

   **Fix:** use identical decoding semantics in both implementations, including malformed escapes and invalid UTF-8. Add receiver cases for wrapped `.click()`, dispatched clicks, and the capture fallback.

3. **Blocking — canonically equivalent German list words do not ask.**

   Where: [policy.py:35](../../control/aresos_control/chrome/policy.py:35), [guard.js:57](../../control/chrome/extension/guard.js:57).

   The matching pipeline case-folds but does not normalize Unicode. My production-classifier probe returned:

   ```text
   "löschen"                 → delete
   "lo\u0308schen"            → free
   "veröffentlichen"         → send
   "vero\u0308ffentlichen"    → free
   ```

   The decomposed spellings display the same German words. A button bearing either decomposed label can therefore execute its deletion or publishing handler before approval.

   **Reproduction:** use those decomposed labels in the existing word/label fixture, then test click, Enter, Space, and page-script activation.

   **Fix:** apply a shared, specified Unicode normalization before folding and whole-word matching. Test canonical equivalents independently of the current matcher’s expected output.

4. **Blocking — answering a native dialog can resume page code without arming any submission guard.**

   Where: [background.js:533](../../control/chrome/extension/background.js:533).

   The dialog path calls `Page.handleJavaScriptDialog` directly. It never performs the private arming used by ordinary input. Existing protection therefore depends on a previous Claude input still being in flight.

   My combined production-background/guard VM probe started with no active input, answered a dialog, and let its continuation call `form.submit()`. Output:

   ```text
   commands: ["Page.handleJavaScriptDialog"]
   formArrivals: ["native"]
   holds: []
   ```

   The result claimed successful dispatch with no follow-up.

   **Reproduction:** in a controlled fixture, have an owner action or an independent page task open `confirm("Continue?")`; after acceptance, call a POST form’s `submit()`. Answer through `chrome_dialog` with no earlier Claude input in flight. Acceptance is free, but the resulting form submission must be held and separately prepared.

   **Fix:** treat answering as a new guarded input. Establish private in-flight protection before releasing the dialog. If Chrome cannot establish it while the modal is open, refuse tool acceptance when no suitable guard remains active and leave that dialog to the owner.

5. **Blocking — editable drafts in inline frames disappear from generic send bindings.**

   Where: [background.js:430](../../control/chrome/extension/background.js:430), [background.js:449](../../control/chrome/extension/background.js:449).

   `facts()` unconditionally skips `about:blank` frames and also skips `about:srcdoc` through `safeURL()`. Generic send binding then treats the remaining frames as the complete editable-field set.

   My production-background probe supplied a top document, an `about:blank` child, and an `about:srcdoc` child. The native frame inventory contained all three; only frame 0 was read or bound.

   **Reproduction:** put a draft editor in a same-origin blank or `srcdoc` iframe, plus a nonempty editor and Send button in the top document. Have Send read both editors. Prepare, change the iframe draft, then approve. The omitted draft cannot make the binding comparison fail.

   **Fix:** cover eligible inline frames using their effective origin and document identity, including their password exclusions and guards. If complete binding cannot be established, refuse the generic send instead of silently omitting editable content.

6. **Blocking — a send confirmation does not bind an editable draft outside its dialog.**

   Where: [policy.py:107](../../control/aresos_control/chrome/policy.py:107), [adapter.py:37](../../control/aresos_control/chrome/adapter.py:37), [background.js:449](../../control/chrome/extension/background.js:449).

   An OK button inside “Send this message?” becomes kind `confirmation`. Only kind `send` receives the complete generic editable-field binding. The dialog binding includes fields inside the dialog, leaving a sibling draft outside it unbound.

   My Python probe changed that draft from “Approved text” to “Different text”:

   ```text
   kind: confirmation
   bound_editable: None
   binding_equal_after_draft_change: True
   ```

   **Reproduction:** place a textarea outside a page dialog; its OK handler sends the textarea’s current value. Prepare OK, change the textarea, approve. This is editable draft content covered by §6.

   **Fix:** retain the confirmation’s underlying send semantics and bind the complete generic draft set as well as the dialog. A preceding approval must not substitute for a fresh binding of this separate operation.

7. **Blocking — selected-file binding compares metadata, not file identity or content.**

   Where: [reader.js:90](../../control/chrome/extension/reader.js:90), [reader.js:118](../../control/chrome/extension/reader.js:118).

   A file field records only `name`, `size`, and `lastModified`. Replacing its File with different bytes and identical metadata leaves the form binding unchanged.

   My actual-reader VM probe replaced four bytes `GOOD` with `EVIL`, keeping `proof.txt`, size 4, and modification time 0. The complete before/after form facts were equal.

   **Reproduction:** prepare a multipart form submission, replace `input.files` using a `DataTransfer` containing a same-metadata File with different bytes, then approve. The receiver must remain at zero.

   **Fix:** bind immutable selected-file identity/content, retaining the staged hash where available. Reject changed or unverifiable files. Cover both previously uploaded files and existing selected files.

8. **Blocking — rich-text serialization loses distinctions that must invalidate approval.**

   Where: [reader.js:70](../../control/chrome/extension/reader.js:70), [reader.js:93](../../control/chrome/extension/reader.js:93).

   Editable content is serialized by recursively joining child text with spaces. Paragraph boundaries and line breaks can therefore collapse into the same recorded value.

   My actual-reader probe compared:

   ```html
   <div contenteditable>
     <div>Line one</div><div>Line two</div>
   </div>
   ```

   with the same editor containing `Line one Line two`. Both produced the identical field value `"Line one Line two"`.

   **Reproduction:** have a generic Send handler send the editor’s rendered text. Prepare with two lines, replace them with one line during approval, then submit. The current binding does not distinguish the two messages.

   **Fix:** preserve rendered line breaks and meaningful whitespace in safe editable extraction, while maintaining password exclusion. Add rich-text cases to generic and adapter binding tests.

9. **Blocking — ARIA list items and rows are omitted from affected-item binding.**

   Where: [reader.js:137](../../control/chrome/extension/reader.js:137).

   `itemText()` recognizes native `li` and `tr`, but not `[role=listitem]` or `[role=row]`. It consequently falls back to the button on common ARIA-based lists.

   My actual-reader probe used a Delete button inside a `div role="listitem"`. Changing its sibling label from “Draft A” to “Draft B” produced:

   ```text
   before item: "Delete"
   after item:  "Delete"
   ```

   The approval neither identifies nor compares the affected draft.

   **Reproduction:** prepare deletion in an ARIA list item, change the item’s displayed identity while retaining the button, and approve. Require refusal before its handler runs.

   **Fix:** find the nearest qualifying semantic item, including supported ARIA roles and named regions, rather than relying principally on tag names. Test native and ARIA containers.

10. **Blocking — Unsubscribe/Abbestellen uses message binding and omits the affected item.**

    Where: [policy.py:109](../../control/aresos_control/chrome/policy.py:109), [adapter.py:37](../../control/aresos_control/chrome/adapter.py:37), [adapter.py:437](../../control/aresos_control/chrome/adapter.py:437).

    Every listed word outside DELETE/PAY becomes kind `send`. That includes `unsubscribe` and `abbestellen`, although these actions should bind the affected subscription/item.

    My production-payload probe demonstrated both consequences:

    - Without an editor, Unsubscribe is refused as “Can’t tell what this sends: no editable text.”
    - With an unrelated editor, it prepares, but `binding.item` is `None`. Changing “Newsletter A” to “Newsletter B” leaves the binding equal.

    **Fix:** distinguish message-content sends from other asking actions. Bind unsubscribe actions to their affected item, without requiring an unrelated draft. Add both language variants and changed-item receiver tests.

11. **Should-fix — Enter in an ordinary input of a GET search form asks unnecessarily.**

    Where: [policy.py:93](../../control/aresos_control/chrome/policy.py:93).

    Compose-Enter classification runs before the GET-search-form exemption. `target.search` recognizes the field itself, so a normal text input inside `<form role="search" method="get">` becomes a send.

    My production-classifier probe returned `send` for:

    ```text
    target: editable=true, search=false
    form:   search=true, method=get
    input:  Enter
    ```

    **Fix:** evaluate the effective GET-search submission before generic compose Enter. Retain asking behavior for POST submitter overrides and conservative mode.

12. **Should-fix — generic questions conceal the key’s action and omit the page title.**

    Where: [adapter.py:34](../../control/aresos_control/chrome/adapter.py:34), [adapter.py:285](../../control/aresos_control/chrome/adapter.py:285).

    The target’s name takes precedence over the pressed key. Both Delete and Backspace on “Quarterly report” generated this question in my probe:

    > On https://fixture.test/, as the page shows it, activate 'Quarterly report'; where the page sends this isn't visible to the tool?

    The sentence does not say deletion or name the key. The full fields retain the key, but the required plain-language question is misleadingly vague. Page titles also never enter the approval binding/description, despite §4.1 requiring the page’s own title.

    **Fix:** carry the service-classified action into generic sentence generation, explicitly name the key and affected item, and include/bind the page title. Keep the existing escaping and whole-input limits.

13. **Should-fix — the recorded “page” stage contains stock text instead of an observed outcome.**

    Where: [background.js:666](../../control/chrome/extension/background.js:666), [adapter.py:393](../../control/aresos_control/chrome/adapter.py:393).

    Ordinary input returns the constant:

    > Input dispatched once; inspect a fresh read for what the page shows.

    The service records that reply as its `page` stage. It does not collect the required subsequent page result.

    My production-dispatch VM probe changed the page to `ERROR: the change failed` during input. There were two snapshot reads, both before dispatch; the response contained only the stock sentence.

    **Fix:** collect a bounded post-input observation—current page, relevant notice/error, dialog, or observable change—and record it distinctly from dispatch evidence. If observation is unavailable, say so explicitly. Preserve `done`’s limited meaning of input dispatched once.

**Owner Enter:** yes, angle B supports closing the original owner-Enter PLAN-GAP for the tested behavior.

I independently checked all four retained raw receiver datasets, scoped to the initial owner-input experiment:

| Run / installation | Owner arrivals | Delayed Claude arrivals before approval | Receiver delay from Claude-start marker |
|---|---:|---:|---:|
| [42773242428 external](./records/integrate-42773242428-external/receiver.jsonl:5) | 1 | 0 | 150 ms |
| [42773242428 policy](./records/integrate-42773242428-policy/receiver.jsonl:5) | 1 | 0 | 147 ms |
| [42773249076 external](./records/integrate-42773249076-external/receiver.jsonl:5) | 1 | 0 | 158 ms |
| [42773249076 policy](./records/integrate-42773249076-policy/receiver.jsonl:5) | 1 | 0 | 147 ms |

Each saved response has only the scheduled submission as an approval follow-up. The separate owner-task matrices show one synchronous arrival, zero in-flight arrivals, held delayed/replayed work, and ordinary behavior after the limit. The later `scheduled-input` arrival in each complete receiver file belongs to the separately approved slow-arming test.

The evidence establishes owner Enter functioning during the active hold window. It does not timestamp the physical Enter at exactly 130 ms; the report should retain the actual measurements.

Verification I ran:

```text
node --test control/chrome_tests/page.test.mjs \
  control/chrome_tests/reader.test.mjs \
  control/chrome_tests/background.test.mjs \
  control/chrome_tests/sites.test.mjs
116 passed, 0 failed

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/chrome_tests \
  python3 -B -m unittest test_policy -v
11 passed
```

I found no additional defect in the reviewed operation-ID replay protections or owner-only allow/revoke checks. Generic actions, deleting, paying, and WhatsApp messages remain ineligible for trusted allowances in those paths. Outside angle B, I established no additional finding. Group 12/18d and the documented image handoffs remain the stated stage boundaries.

CHANGES-NEEDED