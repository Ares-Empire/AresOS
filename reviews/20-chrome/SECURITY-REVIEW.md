# Independent security review — CHANGES NEEDED

Reviewer: `gpt-6-astra`, high, as brief 20 requests. Source review of
`e31e75d242511f13e68bd482c6da661c2579b0e4`. No browser/profile, real site or
real account was accessed. Evidence is source inspection and small
browser-free Node probes. This is not a final SAFE assessment. No files were
edited by the reviewer.

1. **P1 — Honest script activations bypass approval through external labels.**
   `control/chrome/extension/page.js:51–61` does not resolve
   `aria-labelledby` or associated labels. `reader.js:58–63` does, so the two
   classifiers disagree. An ordinary free handler can call `.click()` on
   `<button type="button" aria-labelledby="delete-label"></button>` beside
   `<span id="delete-label">Delete</span>`. Neither wrapper nor capture
   detects the asking name. Running actual `page.js` in the existing Node
   fixture gave `{"delivered":1,"reports":0}`. Add a real Chrome fixture
   proving zero handler executions and receiver arrivals before approval.
2. **P1 — The whole-window hold also stops the owner.** `page.js:27,92–105`
   uses a global deadline; `background.js:210–214` arms every readable frame.
   An owner click on Delete, or a free owner click whose handler submits a
   form, is held during those 500 ms. Simulated native trusted-event delivery
   through the fixture's saved dispatch function gave
   `{"delivered":0,"reports":1}`. `isTrusted` alone cannot distinguish
   debugger and physical input. Clearing the deadline lets a pending Claude
   timer submit unapproved. This is a defect in the current architecture,
   **not an impossibility theorem**. Finite timer/Promise wrapping does not
   establish complete causality: a native async/await probe gave
   `{"continued":true,"patchedThenCalls":0}` after patching
   `Promise.prototype.then`. Required fixtures include existing promises,
   native await, MessageChannel and same-origin cross-frame calls interleaved
   with owner input. Node probes do not replace the container test.
3. **P1 / R3 — Read-only changes do not invalidate prepared input.**
   `adapter.py:265–267` checks the owner list during preparation;
   `revalidate()` at `197–208` does not repeat that check. A send/upload
   prepared before owner read-only changes can still execute; dialog
   preparation has the same stale-policy problem. Recompute current owner
   restrictions before every dispatch, including trusted/resumed submissions.
4. **P1 — Qualification delivery has no runtime caller.**
   `qualification.py:95–113` implements `refresh()`, but repository search
   found no runtime call. Daily and uncovered-version refresh are absent, so
   published core failures cannot reach the installed tool through this path.
   Also `adapter.py:84–91` checks password exclusion only in read mode.
   Preparation calls `facts()` and checks that group, but revalidating an old
   operation does not. A newly recorded password-exclusion failure must
   refuse submission before the extension rereads for binding.
5. **P2 / R1 — Pending lacks Chrome live validity checks.**
   `control/aresos_control/engine.py:107–119` projects reserved records
   directly. Chrome's session/process checks in `adapter.py:197–208` are not
   reflected in pending reads. After service restart an old item can say
   Awaiting exact approval although it can never submit. Release-event
   writes do not cover restart/lost events. Derive this from committed
   context plus current live session.
6. **Required confirmations are incomplete.** `sites.py:41–43` names an
   exact GitHub confirmation and `adapter.py:193–194` includes it in the
   question. No execution path consumes it within the approved operation;
   `adapter.py:408–417` independently classifies later dialogs. It asks again
   rather than implementing exact covered confirmation. Exact-match and
   every-mismatch browser tests remain required.

Commit-before-dispatch in the free paths and shared Engine is a useful R2
foundation. It does not establish Chrome's requested full storage sweep or
warning lifecycle. Complete qualification, confirmation, crash/restart and
durable-state evidence remains outstanding; smoke CI cannot establish it.
