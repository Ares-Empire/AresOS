**I found three blocking findings and one should-fix finding at `60b94384`. The original owner-Enter PLAN-GAP can be closed for the specified fixture behavior; these separate defects still require changes.**

I read the requested specifications and later decisions, reviewed the relevant additions, and checked the retained Linux evidence. The runtime and workflow files are unchanged between the verified source `ab7aba92` and reviewed head `60b94384`.

No files were edited, no browsers or containers were started, and nothing was pushed or posted. New reproductions below use the actual production JavaScript in the repository’s browser-free Node fixtures. Their “native calls” are fixture counters, not claims of newly observed browser requests.

1. **Blocking — a wrapper from another controlled document bypasses the target document’s hold.**

   **Where:** [page.js:16](../../control/chrome/extension/page.js:16), [page.js:73](../../control/chrome/extension/page.js:73).

   The saved native `getRootNode({composed:true})` comparison correctly handles detached nodes and inert documents. However, its false branch also includes elements belonging to **another live document**.

   With two controlled same-origin documents, page code can therefore do:

   ```js
   // Executed by the parent’s free Continue handler.
   HTMLFormElement.prototype.submit.call(
     iframe.contentDocument.querySelector('form')
   );
   ```

   This calls the parent’s installed wrapper. Because the form’s root is the child document, the wrapper calls its saved native `submit()` directly. It never enters the child’s wrapper, and native `submit()` emits no submit event for the child’s capture listener to stop.

   This needs neither an uninstrumented donor nor a raw native obtained from a fresh realm.

   **Probe run:** I instantiated two private-relay fixtures, armed both guards, and compared the child’s own wrapper with the other document’s wrapper:

   ```text
   target own wrapper:
   {"nativeCalls":0,"holds":1}

   other controlled document wrapper:
   {"nativeCalls":1,"holds":1}
   ```

   The second invocation adds a native submission without adding a hold.

   **Why it matters:** page-reachable wrapper invocation recovers native submission capability while both documents are guarded. This expands the disclosed fresh-native residual.

   **Specification implication:** this is also a **PLAN-GAP in continue-3’s mandated passthrough rule**. The implementation follows its literal document comparison, but the explanation overlooks live foreign documents when asserting that the passthrough cases cannot submit.

   **Fix:** preserve native behavior for non-Nodes, detached nodes and inert documents, but distinguish a foreign document with a browsing context. Route asking calls through that document’s private guard, or conservatively hold them when its authority cannot be established. Do not replace the check with `isConnected`, which would revive the inert-document defect. Add the two-controlled-HTTP-frame reproduction to Linux CI, requiring zero arrivals before approval.

2. **Blocking — newly created or replaced frame guards do not inherit the active hold. Existing `about:blank` frames are also omitted from arming.**

   **Where:** [background.js:95](../../control/chrome/extension/background.js:95), [background.js:433](../../control/chrome/extension/background.js:433), [background.js:615](../../control/chrome/extension/background.js:615), [guard.js:19](../../control/chrome/extension/guard.js:19).

   Startup installs the guard and wrappers, then marks the document ready, but does not transfer an ongoing dispatch or hold window. A fresh guard starts with `generation === null`; its `active()` is false, and its normal `submit()` and `requestSubmit()` paths consequently run natively.

   Input arming covers only the documents in the first snapshot. The later snapshot can contain another document without arming it before dispatch. Frames whose URL is `about:blank` are skipped by `facts()` altogether, so they never enter that arming loop.

   **Probes run:**

   - In the actual background fixture, I made a child frame appear on the final read. Dispatch succeeded with:

     ```text
     ["set_control-0","arm-0","focus-0","keyDown","keyUp",
      "finish_input-0","finish_input-2"]
     ```

     There was no `arm-2`, despite finishing frame 2 afterwards.

   - With the actual private-relay guard installed in a new child fixture, arming the parent and invoking the child’s ordinary wrapped submission methods produced:

     ```text
     {"arrivals":["native","event"],"holds":[]}
     ```

   **Concrete browser reproduction:** have Claude’s free Continue handler create or navigate an ordinary same-origin HTTP iframe. After that frame installs its scripts, but within the hold window, its handler calls its own `form.submit()` or `form.requestSubmit()`. Alternatively, populate an existing same-origin `about:blank` iframe before the action and submit its form from Continue. No borrowed native is necessary.

   **Why it matters:** installing wrappers before scripts is insufficient when those wrappers start without the active private hold. A submission caused by Claude’s handler can escape without either an approval or an uncertainty report. The current first-script tests load the frame before the later input; they do not exercise this lifecycle transition.

   **Fix:** track active dispatch/hold coverage across document lifetimes. Initialize newly controlled frame guards with the applicable private hold before releasing their scripts, without transferring an approval allowance. Compare document/frame coverage again before input and arm or refuse changed coverage. Include eligible inherited-origin blank frames, with the required exclusion checks. Keep the separately decided popup reload exception explicit.

3. **Blocking — borrowed native activation in a newly created shadow root escapes both cancellation and the required `unknown` report.**

   **Where:** [guard.js:125](../../control/chrome/extension/guard.js:125), [guard.js:201](../../control/chrome/extension/guard.js:201), [reader.js:44](../../control/chrome/extension/reader.js:44).

   The window capture listener returns when the event’s element belongs to a shadow root, relying on that root already having its own listener. Root discovery happens during reads, mutation processing, or wrapped calls.

   A page can attach a shadow root and use a borrowed native `dispatchEvent` inside the same handler, before discovery. For an open root and composed event, window capture sees the inner target but returns at line 126. For a non-composed event, window capture is absent entirely. The root has no guard listener yet.

   **Probe run:** using the actual armed guard and the fixture’s saved native dispatch, I dispatched on a Delete link in an undiscovered root:

   ```text
   cancelable=true:
   returned=true, handlers=1, prevented=false, held=[]

   cancelable=false:
   returned=true, handlers=1, prevented=false, held=[]
   ```

   **Concrete Linux regression:** extend the existing native-donor fixture. Inside Continue’s handler, attach a root to an existing host, insert a Delete link targeting the receiver, and immediately invoke the donor’s native dispatch on it. Test open/closed roots and composed/non-composed events.

   **Why it matters:** this is within the explicitly specified fresh-native fallback. Cancellable activation must stop; non-cancellable activation must report `unknown` and never resume. Here handlers run and neither outcome is reported. Existing fallback tests use a light-DOM link.

   **Fix:** establish shadow-root capture synchronously before page code can activate newly inserted controls. A private registration path around controlled-document shadow creation is one approach; discovering roots only through later mutation callbacks is insufficient. Preserve ordinary-tab behavior. Require receiver and handler assertions for every fallback variant.

4. **Should-fix — refusal after arming can leave the owner’s input classified as in-flight indefinitely.**

   **Where:** [background.js:615](../../control/chrome/extension/background.js:615), [background.js:629](../../control/chrome/extension/background.js:629), [background.js:660](../../control/chrome/extension/background.js:660), [guard.js:261](../../control/chrome/extension/guard.js:261).

   Arming sets `inFlight=true`. `finishFrames()` runs only on the successful path. A final binding mismatch, targeting failure, focus refusal or another exception after arming can exit without finishing the guards.

   Because `active()` remains true whenever `inFlight` is true, expiration of the 500 ms window does not repair this. `ownerInput()` also refuses the owner exemption while that flag remains set.

   **Probe run:** I reproduced the existing activation-induced binding change against actual background code:

   ```text
   refusal: stale_approval: page changed during frame setup; prepare again
   commands: ["facts-1","set_control-0","arm-0","facts-2"]
   ```

   No finish command followed. In the actual guard fixture, advancing its clock by 60 seconds after such an unfinished arm still yielded:

   ```text
   {"arrivals":[],"holds":["native_submit"]}
   ```

   **Why it matters:** an ordinary refusal can leave the owner’s subsequent submissions held indefinitely, despite no extension input actually remaining in flight. This fails toward asking more, but exceeds the accepted short-window behavior.

   **Fix:** give every armed dispatch a generation/nonce-bound completion path on errors as well as success. Preserve over-coverage: clear only after the private page-handling barrier establishes completion. Where completion cannot be established, retain truthful uncertainty and provide cleanup rather than silently abandoning the mark. Extend the existing binding-change regression to check cleanup and subsequent owner input.

**Owner-Enter evidence and PLAN-GAP decision**

The retained evidence supports closing the original owner-Enter PLAN-GAP. I independently parsed all four receiver datasets:

| Dataset | Owner POST after Claude’s start marker | Owner arrivals | Scheduled arrivals during that case |
|---|---:|---:|---:|
| [42773242428 external](./records/integrate-42773242428-external/receiver.jsonl:6) | 150 ms | 1 | 0 |
| [42773242428 policy](./records/integrate-42773242428-policy/receiver.jsonl:6) | 147 ms | 1 | 0 |
| [42773249076 external](./records/integrate-42773249076-external/receiver.jsonl:6) | 158 ms | 1 | 0 |
| [42773249076 policy](./records/integrate-42773249076-policy/receiver.jsonl:6) | 147 ms | 1 | 0 |

Each corresponding `owner-input.json` records a held **`native_submit` for the scheduled form**, with its separate approval. The owner’s POST contains `source=owner`. The later `scheduled-input` arrival in the complete receiver file belongs to the separate slow-arming test, which explicitly approves it; it is not an escape from the owner-Enter case.

In every dataset, the additional owner cases have these receiver totals:

- Synchronous owner submission plus held delayed work: **1**.
- Owner event replay: **2**, with the second following explicit approval.
- Owner input during Claude’s in-flight dispatch: **0**.
- Owner work after the limit: **2**.

The three forgery regressions each record one final arrival, and the retained [browser assertions](./records/integrate-42773242428-external/browser.txt:14) check **0 before approval, 1 after, 1 after replay**. Source review confirms the owner mark, request depth, in-flight state and MessageChannel remain private. I found no route to forge the owner verdict itself. Receiver totals alone cannot prove a universal absence of forgery; the conclusion uses those assertions, source inspection and the passing browser-free regressions together.

Thus **the specific owner-Enter PLAN-GAP can close**. That does not close the frame-coverage, fallback-reporting or failed-dispatch cleanup findings above.

**Other verification and observations**

I ran:

```text
node --test control/chrome_tests/page.test.mjs control/chrome_tests/background.test.mjs
105 tests; 105 pass; 0 fail; 0 cancelled; 0 skipped
```

The retained-evidence auditor passed all four datasets. Independent comparisons also found `native-baseline.json`, `native-outside.json` and `native-controlled.json` equal in each dataset.

The current all-tab registration contains only inert ISOLATED `context.js`; the actual guard/page bundles are installed through authenticated debugger contexts. The reviewed resume code preserves native-submit versus submit-event kinds and consumes the operation and nested allowance before re-entry. The retained popup evidence supports the decided reload, opener preservation, POST refusal and Stop behavior.

Outside angle A, I noticed no additional independently established defect. Group 12 remains explicitly false pending 18d, and installed-image networking/verifier checks remain assigned to 18c; neither is presented here as a new stage-Now failure.

CHANGES-NEEDED