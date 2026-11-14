I found **five blocking issues and four should-fix issues** at `60b94384`. Passing named tests do not cover these counterexamples.

1. **Blocking — answering a delayed native dialog can release an unapproved form submission.**

   **Where:** [background.js:533](../../control/chrome/extension/background.js:533), [guard.js:104](../../control/chrome/extension/guard.js:104).

   The native-dialog path calls `Page.handleJavaScriptDialog` without first establishing a new private input hold. It depends on an earlier input still being marked in flight. If a dialog opens after that input finished—or independently of any tool input—the resumed handler can call `form.submit()` while `active()` is false. The submission passes immediately.

   **Probe run:** I reused the actual page/guard and background VM fixtures, finished the previous input, advanced its clock by 600 ms, then answered a dialog whose handler called `form.submit()`. Output:

   ```json
   {
     "nativeArrivals": ["native"],
     "steps": [],
     "commands": ["finish_input", "steps"],
     "reportedDispatched": true
   }
   ```

   This also affects an innocuous `confirm("Continue?")`: accepting it is free, yet its resumed handler can submit a form without any approval. The existing group-4 test starts its dialog during an already armed input, concealing this case.

   **Fix:** establish a private hold covering dialog completion before answering it, without carrying an old approval into a new form submission. If the modal prevents establishing that hold, refuse tool answering and hand it to the owner. Add delayed and independently opened dialogs, including free acceptance and dismissal, to the receiver matrix.

2. **Blocking — readable inherited-origin frames are omitted from both binding and input holds.**

   **Where:** [background.js:430](../../control/chrome/extension/background.js:430), [background.js:615](../../control/chrome/extension/background.js:615).

   `facts()` unconditionally skips `about:blank` frames. It also skips `about:srcdoc` because `safeURL()` rejects that address. These can contain ordinary, same-origin page content. Only frames returned by `facts()` are armed before input.

   Consequently, a top-page free click can synchronously call a form’s ordinary `submit()` in one of those child frames without a hold. Generic outside-form sends also omit editable content in those frames from their approval binding. These frames are not members of the fixed exclusion list.

   **Probe run:** using the actual dispatcher and guard with an available child reader, I supplied each frame address and made the top click handler submit the child form. Both cases produced:

   ```text
   framesInFacts: [0]
   armedFrames: [0]
   childNativeArrivals: ["native"]
   steps: []
   ```

   **Container reproduction:** create a pre-existing same-origin blank or `srcdoc` iframe containing a POST form. Have a top-level “Continue” button call that child form’s `submit()`. A tool click must produce zero receiver arrivals before separate approval. Also change a child editor while a generic Send approval waits.

   **Fix:** determine inherited-frame eligibility from authenticated document/origin and ancestor information, then include eligible frames in reading, binding and arming. Refuse acting when a required frame cannot be guarded; silently omitting it is unsafe.

3. **Blocking — modified Delete and Backspace bypass classification.**

   **Where:** [policy.py:89](../../control/aresos_control/chrome/policy.py:89), [background.js:165](../../control/chrome/extension/background.js:165).

   Classification checks the complete key string against `Delete` and `Backspace`. The dispatcher separately parses modifiers and dispatches the underlying deletion key. Thus a supported key such as `Shift+Delete` reaches the page without the required deletion approval.

   **Python probe run, outside an editable field:**

   ```text
   Delete 'delete'
   Shift+Delete None
   Ctrl+Delete None
   Backspace 'delete'
   Shift+Backspace None
   Ctrl+Backspace None
   ```

   A focusable selected-item fixture whose key handler deletes or posts whenever `event.key === "Delete"` reproduces the problem with `chrome_press(key="Shift+Delete")`. The guard does not independently intercept that key handler. The browser matrix currently tests only the two unmodified strings.

   **Fix:** classify the parsed base key, preserving modifiers in the bound input. Cover modified deletion keys with strict receiver 0/1/1 tests and retain their free behavior inside text editing.

4. **Blocking — adapter recognition can turn explicit payment/deletion cues into a trusted send.**

   **Where:** [policy.py:91](../../control/aresos_control/chrome/policy.py:91), [sites.py:111](../../control/aresos_control/chrome/sites.py:111), [adapter.py:542](../../control/aresos_control/chrome/adapter.py:542).

   The adapter result returns before generic classification examines all required label channels. A complete Gemini prompt with a button named “Send” is recognized as `gemini_question` even when its title explicitly says “Pay” or “Delete”. `trusted()` then checks the owner entry and adapter kind hash, without an independent prohibition on those cues.

   **Python probe run:** I used the actual recognition, classification and trusted-entry predicate, with a qualified Gemini adapter and an exact matching synthetic owner entry:

   ```text
   title=Pay:    generic_kind=pay,    adapter_kind=send, trusted=True
   title=Delete: generic_kind=delete, adapter_kind=send, trusted=True
   ```

   The recorded page state can contain the payment/deletion cue, but `chrome_submit_trusted` still permits dispatch without presenting it to the owner. This contradicts “deleting and paying always ask.”

   **Fix:** prevent adapter exemptions and trusted kinds from overriding explicit deletion/payment evidence in the required control channels. Make the trusted-send predicate independently reject forbidden operations. Add mixed-label and form-destination cases to group 11.

5. **Blocking — deletion binding misses ARIA list items and rows.**

   **Where:** [reader.js:137](../../control/chrome/extension/reader.js:137), [adapter.py:30](../../control/aresos_control/chrome/adapter.py:30).

   `itemText()` recognizes native `li`, `tr` and `article`, but omits `[role=listitem]`, `[role=row]` and `[role=article]`. It also misses an implicitly named section region. A Delete button inside such an item therefore binds only its own “Delete” text.

   **Node probe run:** I executed the actual reader’s `text()` and `itemText()` functions against DOM doubles. Changing the surrounding item from “Invoice A” to “Invoice B” produced:

   ```text
   div role=listitem: before="Delete", after="Delete"
   div role=row:      before="Delete", after="Delete"
   named section:    before="Delete", after="Delete"
   ```

   An explicit `role=region` correctly changed from “Invoice A Delete” to “Invoice B Delete”, confirming the selector gap.

   **Reproduction:** prepare Delete inside an ARIA row, replace its identifying text while retaining the button, then submit the original approval. The affected-item binding remains unchanged even though the item changed.

   **Fix:** resolve the smallest affected item using both native semantics and supported ARIA roles. Include its identifying content in approval and comparison. Add mutation tests for each supported container kind.

6. **Should-fix — Chrome page content reaches ordinary audit summaries without untrusted marking.**

   **Where:** [adapter.py:397](../../control/aresos_control/chrome/adapter.py:397), [engine.py:245](../../control/aresos_control/engine.py:245), [engine.py:496](../../control/aresos_control/engine.py:496).

   Chrome serializes page observations into a stage string. The shared engine interpolates that string into the ordinary audit `summary`; `control_log` applies the protective historical-summary treatment only to Mail.

   **Python probe run:** using the actual `Engine.stage()` and `control_log` paths with an in-memory store, a page-dialog sentinel returned as:

   ```json
   {
     "action": "chrome_submit",
     "summary": "stage page: {\"dialog\":{\"text\":\"UNTRUSTED_PAGE_SENTINEL\"}}"
   }
   ```

   There was no `untrusted_content` field. This launders page-origin text into the service’s audit-summary channel, contrary to rule 4.8.

   **Fix:** keep Chrome audit summaries service-written and put page-derived stage data inside structured `untrusted_content`. Protect historical Chrome summaries when reading them. Test marking through status, evidence and log results.

7. **Should-fix — acting results do not contain the promised page observations.**

   **Where:** [background.js:666](../../control/chrome/extension/background.js:666), [adapter.py:393](../../control/aresos_control/chrome/adapter.py:393).

   Ordinary input returns the fixed sentence:

   ```text
   Input dispatched once; inspect a fresh read for what the page shows.
   ```

   The service records that reply as its `page` stage. It does not collect the new address, success/error notice, changed elements or resulting download. Section 6 requires every acting result to describe what happened and records page observations after dispatch.

   **Reproduction:** use a fixture button that changes a status element to “Sent”, or navigates to a result page. Call `chrome_click`/`chrome_submit` and inspect the returned result and recorded `page` stage without an additional read. Neither contains that observed result.

   **Fix:** collect a bounded post-input observation and record it as page evidence. Preserve the distinction between dispatched input and site delivery, and report explicitly when observation is unavailable.

8. **Should-fix — Chrome questions lack the required bounded recipient/name presentation.**

   **Where:** [adapter.py:300](../../control/aresos_control/chrome/adapter.py:300), [common.py:229](../../control/aresos_control/common.py:229).

   The sentence builder concatenates every recipient and attachment name. It does not implement exact overflow counts or positional descriptions of long names. Safe refusal follows, but otherwise displayable operations unnecessarily become unusable.

   **Python probe run:** a synthetic Gmail approval with 60 displayed recipients produced:

   ```text
   Question characters: 4958
   Whole approval bytes: 10288
   asking_input_too_large: The question exceeds 4096 displayed characters
   ```

   The complete approval fits the 16 KiB bound. Rule 4.1 requires a bounded sentence with an exact remaining count while retaining the full recipients below it.

   **Fix:** budget the escaped sentence, count omitted recipients exactly, and describe oversized names by position and length. Keep complete values in the content fields. Add Chrome-specific boundary tests.

9. **Should-fix — the claimed complete cross-site password matrix is incomplete.**

   **Where:** [fixture.mjs:160](../../control/chrome/ci/fixture.mjs:160), [fixture.mjs:167](../../control/chrome/ci/fixture.mjs:167), [REPORT.md:60](./REPORT.md:60).

   The top document and its shadow roots contain the fuller password matrix. The cross-site `password-inner` fixture contains only password type, `current-password` and CSS masking. It lacks `new-password`, `one-time-code`, the show-password transition and the late type transition. The Show handler operates only on the top document’s roots.

   Therefore the named test can pass without testing every required kind in a cross-site frame, despite the report’s “Every password kind in open/closed/cross-site roots” claim. The password-matrix fixture also does not exercise these combinations as form bindings.

   **Check:** inspect the two fixture branches and the group-7 test: the missing frame variants cannot execute because those fields and transitions are absent.

   **Fix:** exercise the complete matrix in cross-site frames during both reading and binding, in qualified and conservative modes, retaining the browser-return/value-read traces. Correct the report until those cases have passed twice. I have not established an actual password leak.

The package-level checks otherwise support these narrower conclusions:

- All **29 first Chrome rows** have declared tools and named coverage in the report. All 13 groups are named; group 12 remains explicitly false and deferred to 18d.
- The retained-evidence auditor passes for both install modes in runs `42773242428` and `42773249076`: **61 named cases and 135 adapter 0/1/1 sequences per matrix**. That verifies the retained cases, not the counterexamples above.
- Generated artifacts match. The runtime hash is `e4030361b4d50170f3c0a11d915954519257ca4a7911862586225cdc99034c72`, matching the report. Changes after verified source `ab7aba92` are confined to review material.
- The diff stays within the allowed paths. I found no changes under the prohibited image, mod, design, plan, FEATURES or owner-document paths. The service-unit networking change matches the lead’s narrow authorization.

Locally, **136 focused Node tests and 11 policy tests passed**, alongside the in-memory probes above. A combined policy/sites invocation stopped during import because its fixture attempted to create `.work`; the sandbox denied it and no files were created. I did not run browser, container or storage-writing suites.

In passing, the installed verifier/network checks and real-site checks remain explicit handoffs, not proven laptop behavior. The Chrome/host/service crash matrix also does not establish recovery from an extension-worker restart or extension update; I did not establish that native behavior here.

I made no file edits, pushes or GitHub comments, and accessed no browser profile.

CHANGES-NEEDED