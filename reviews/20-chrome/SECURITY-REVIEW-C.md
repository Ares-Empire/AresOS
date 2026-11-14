Reviewed `60b94384` against the specified `origin/main` documents and later decision briefs. **Six blocking findings and two should-fix findings.** No files were changed; no browser, profile, or container was accessed or started.

The vendor exclusions and protected owner-setting loader look correct. I found no hard-coded Aresus address or generic DevTools passthrough. The findings below concern reading, password isolation, and incomplete evidence.

1. **Blocking — Reading an iframe’s `srcdoc` collects raw password-containing HTML.**

   **Where:** [reader.js:149](../../control/chrome/extension/reader.js:149).

   `embedding()` evaluates `element.srcdoc` merely to choose an address. That getter returns the entire embedded document, including password values in source attributes, before any field exclusion runs.

   **Reproduction run:** I executed the production reader in a Node VM with an iframe whose `srcdoc` getter returned:

   ```html
   <input type="password" value="SENTINEL_SRCDOC_PASSWORD">
   ```

   Output:

   ```text
   password-containing srcdoc getter reads: 1
   sentinel represented in snapshot/trace: false
   ```

   The password-containing string reaches the reader, while the existing trace misses it. This violates the requirement that exclusion happen before collection, even though the final result omits the string.

   **Fix:** Test attribute presence with `hasAttribute('srcdoc')`; never retrieve its value. Read any supported embedded document through its own guarded reader. Add an instrumented regression that fails on accessing the source string.

2. **Blocking — Releasing and retaking a tab resets sticky password protection without changing the document.**

   **Where:** [reader.js:5](../../control/chrome/extension/reader.js:5), [guard.js:272](../../control/chrome/extension/guard.js:272), [background.js:399](../../control/chrome/extension/background.js:399).

   `protectedFields` belongs to one reader instance. Release disposes that reader and deletes its guard. Retaking injects another reader into the existing document, creating an empty `WeakSet`.

   **Reproduction run:** Using the production reader and the same field objects throughout:

   - Read a password field: excluded.
   - Change its type to text: still excluded.
   - Dispose and reinject the reader without replacing the document: its value is returned.

   Output:

   ```text
   first read password leaked: false
   same-reader show password leaked: false
   same-document dispose/reinject leaked: true
   ```

   **Container reproduction:** Open a password fixture, read it, use its Show password control, release the tab, retake it, and read immediately. Taking and reading deliberately do not reload, so the first-action reload rule does not protect this path.

   **Fix:** Preserve private, document-scoped password identities across control release and reader reinjection. This can remain inert isolated-world state outside control. If that state is lost while the document survives, refuse unsafe reads instead of treating the fields as newly safe.

3. **Blocking — Protection does not cover a protected editable field’s descendants, and disappears when the element stops being editable.**

   **Where:** [reader.js:33](../../control/chrome/extension/reader.js:33), [reader.js:70](../../control/chrome/extension/reader.js:70), [reader.js:162](../../control/chrome/extension/reader.js:162).

   The reader visits every descendant independently. `password()` checks only the current element’s attributes and style. It also returns `false` for an element that no longer belongs to its recognized field types **before checking `protectedFields`**.

   **Reproductions run:**

   ```html
   <div contenteditable="true" autocomplete="current-password">
     <span>SENTINEL_PRIVATE_PASSWORD_PROBE</span>
   </div>
   ```

   The production reader marked the parent `password:true` but returned the child’s text as its `value`.

   Separately, after observing a protected editable `div`, I removed its editable state and autocomplete attribute. The next read returned the sentinel:

   ```text
   seen protected field made noneditable leaked: true
   ```

   These values enter the ordinary snapshot and can consequently reach the native host, service and results.

   **Fix:** Check sticky membership before current element-type eligibility. Apply exclusion to the entire protected field’s content, including descendant text and accessible-name traversal across shadow boundaries. Check before touching text: the generic-row path currently gathers child text before its password check.

4. **Blocking — `Runtime.enable` subscribes the extension to page values unrelated to injection.**

   **Where:** [background.js:43](../../control/chrome/extension/background.js:43), [background.js:731](../../control/chrome/extension/background.js:731).

   Runtime reporting remains enabled on controlled targets. It delivers console arguments and exception details, independently of the reader’s password checks. Enabling it also reports previously collected console messages. This behavior is explicit in [V8’s Runtime implementation](https://raw.githubusercontent.com/v8/v8/main/src/inspector/v8-runtime-agent-impl.cc); console notifications contain their arguments according to the [protocol definition](https://raw.githubusercontent.com/ChromeDevTools/devtools-protocol/master/pdl/js_protocol.pdl).

   **Exact Linux-container reproduction:** Have a fixture execute this before taking the tab, then repeat after taking it:

   ```js
   console.log(document.querySelector('input[type=password]').value);
   ```

   Inspect raw `chrome.debugger.onEvent` arguments. The password arrives in `Runtime.consoleAPICalled.args`, despite never passing through `safeValue()`.

   This is a **source-backed finding, not a browser reproduction run here**. I additionally delivered such an event to the production handler in a Node VM with recording enabled. Its audit output was `[]`: the current audit does not record this ingress.

   **Fix:** Change the injection/bootstrap mechanism so it does not subscribe to arbitrary page console/exception values. Dropping them after delivery does not satisfy “never reaches the extension.” Audit all incoming protocol events in the synthetic test build. If the chosen mechanism cannot meet this guarantee, record that design conflict explicitly for the lead.

5. **Blocking — Populated `about:blank` frames are omitted from reading and generic-send binding.**

   **Where:** [background.js:117](../../control/chrome/extension/background.js:117), [background.js:433](../../control/chrome/extension/background.js:433), [background.js:449](../../control/chrome/extension/background.js:449).

   Both late reader installation and snapshot collection unconditionally skip `about:blank`. Such a frame can contain a complete editable document. It is an allowed address, not an excluded site.

   **Reproduction run:** I supplied the production background handler with a top document, an `about:blank` child, an `about:srcdoc` child and an HTTPS child. Only frame IDs `[0,3]` were queried and returned.

   **Concrete binding regression:** Put a textarea inside a populated `about:blank` iframe, a nonempty editable field in the top document, and a top-level Send button that sends both values. Prepare Send, change the iframe textarea, then submit the original approval. The binding contains only the returned frames, so that editable content is absent from both approval and comparison. The top-level field prevents the “no editable text” refusal.

   **Fix:** Support allowed inherited-origin documents using authenticated frame/document identity and the same password exclusions. If a relevant frame cannot be inspected, refuse a generic send requiring complete editable-field binding. Do not silently treat that frame as empty.

6. **Should-fix — Several page-text copies escape untrusted marking.**

   **Where:** [adapter.py:255](../../control/aresos_control/chrome/adapter.py:255), [adapter.py:478](../../control/aresos_control/chrome/adapter.py:478), [adapter.py:538](../../control/aresos_control/chrome/adapter.py:538).

   `Chrome.read()` places native-dialog text in a top-level `dialog`, beside `untrusted_content`. Stopped-activation followups put page-controlled labels into an unmarked `reason`. Free-operation `stages.page` and the stages returned by `Chrome.evidence()` also expose page observations without enclosing them in an untrusted field.

   **Reproduction run:** Calling the production `Chrome.read()` with a synthetic native dialog printed:

   ```text
   dialog text outside untrusted_content: PAGE_TEXT_SENTINEL
   untrusted_content keys: ['url', 'title', 'tree']
   ```

   Escaping text with `visible()` does not mark its provenance.

   **Fix:** Put every page-derived text copy under explicit untrusted marking, including dialogs, followups, operation status and evidence. Keep service-authored states separate. Test these public views individually with a recognizable page-text sentinel.

7. **Should-fix — Group 7 does not establish the advertised password guarantee.**

   **Where:** [fixture.mjs:160](../../control/chrome/ci/fixture.mjs:160), [matrices.mjs:288](../../control/chrome/ci/matrices.mjs:288), [reader.js:95](../../control/chrome/extension/reader.js:95).

   The cross-site fixture contains only three variants: password type, current-password autocomplete and CSS masking. It lacks the other autocomplete variants and the late-type/show-password transitions there. The main password matrix has no forms and performs reads plus Show; it does not exercise form reading and approval binding for every variant/root combination.

   More fundamentally, `trace` records `safeValue()` results, not every browser value consumed. Finding 1 demonstrates a password-containing getter access that leaves the trace clean; finding 4 demonstrates an unaudited protocol event.

   **Evidence checked:** Both install modes of runs `42773242428` and `42773249076` report this group passing on Chrome `157.0.8103.50`. Their `control/` and workflow code is unchanged at the reviewed head. Those passes are real but cover the narrower tests above.

   **Fix:** Build the complete variant × document/open-shadow/closed-shadow/cross-site matrix, exercising read, read_form, preparation and final binding checks. Instrument browser ingress and sensitive getters before filtering. Include release/retake, protected descendants and raw-source access regressions.

8. **Blocking — Cross-angle finding for classification: a tooltip hides a visible asking label.**

   **Where:** [reader.js:77](../../control/chrome/extension/reader.js:77), [policy.py:105](../../control/aresos_control/chrome/policy.py:105), [guard.js:68](../../control/chrome/extension/guard.js:68).

   The accessible-name implementation chooses `title` before button contents:

   ```html
   <button type="button" title="More information">Delete</button>
   ```

   The reader reports `name`, `label` and `title` as “More information”; its button-row `text` is empty. The visible Delete label disappears from every field classification examines.

   **Reproduction run:** The production reader produced those facts in Node. Passing the corresponding target to the production Python classifier returned:

   ```text
   classification of visible Delete button: None
   ```

   On a qualified build in ordinary mode, that means free input. The page guard uses the same reader facts, so it does not repair the omission. A fixture whose button handler posts a deletion to the receiver provides the end-to-end regression.

   **Fix:** Implement the specified accessible-name precedence, using button contents before the title fallback, and share those facts with classification and the guard. Test conflicting title/content combinations through clicks, keyboard activation and page-script activation.

Verification run locally: the selected reader, qualification-reader and background Node suites passed **70/70**; `test_policy` and `test_exclusions` passed **14 tests**. The additional probes above ran against production code with in-memory fixtures. No native-browser reproduction is claimed for them. Group 12 remains the explicitly deferred stage boundary.

CHANGES-NEEDED