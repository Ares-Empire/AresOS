# Part P — native modal continuation trial

In progress; no acceptance claim. This checkpoint supersedes BUILD-P-2's
`Debugger.pause` design. Linux runs **42820293765 / 42820302232**, source
`a9ee2d76`, failed. The latter's external trace dispatched `Debugger.pause` but
never completed it or answered the modal. Receiver remained zero. Exact protocol
line references and failure are retained in
[review-fixes-a9ee-native.json](records/review-fixes-a9ee-native.json).

The alternative installs native alert/confirm/prompt wrappers at document start,
before the fixture's first cached references. Native arguments and return values
are preserved. A private begin notification authenticates the browser document.
Before answering, the extension installs its continuation barrier in background
state, without evaluating page code while the modal is open. The native wrapper's
finally block synchronously reaches a private isolated-world debugger statement
before the original caller can continue. At that pause the extension verifies
the private document and exact return token, arms every current document without
an approval allowance, then resumes. A submission begun by the caller must ask.
The test requires successful answers and preserved return values for all 15
alert/confirm/prompt combinations of Claude input, owner input and a page task,
including confirm/prompt dismissals. Refusal fails this test.

An existing in-flight hold can be reused only when each current document proves
its active nonce. An existing approval allowance is preserved only for the
already-matched exact native confirmation; other answers cannot reuse it. A
conservative-policy upgrade cannot reuse a weaker hold. Finish invalidates this
proof before sending cleanup. Stop rejects pending barriers and clears native
begin records. An authenticated boundary failure retains the debugger pause and
reports uncertainty; it cannot release an unguarded continuation.

**Run:** Node **201 passed**, zero failed/cancelled/skipped. Full Python **185
tests, OK, 232.281 s** (before the subsequent JavaScript-only reuse checks).
Mutation audit **65 rejected; every baseline passed**, including return-boundary
omission, token authentication, existing allowance and current nonce proof.
Generated artifacts match; `git diff --check` is clean. Browser validation of
this alternative is pending. Selected-file chooser validation and the complete
matrix also remain pending. Earlier blank/srcdoc editor partial evidence is in
BUILD-P-2; it is not whole-set acceptance.

**Decision still tracked for owner/lead:** a modal that predates the first guarded
reload, or a native dialog called through an unwrapped native recovered outside
guarded control, has no authenticated return boundary. If every current document
already proves a free in-flight hold, answering remains possible. Otherwise this
case still refuses before answering. Direct Runtime evaluation and pre-answer
Debugger.pause both failed in real Linux-container trials. This remaining feature
limitation has no owner/lead approval and must not be treated as complete or
silently shipped. Further ordinary-path browser evidence is needed first.

No local browser/profile was touched; no other worktree or branch was read or
changed. No workflow was cancelled in this trial. Ledger: **134 Chrome IDs before
this push**, expected **136 after it**, allowance approximately 155. PR 27 remains
draft; no merge.

**Linux feedback:** `d5cdde7d`, policy job of **42830213180**, passed all
15 native answer/return-value cases and all four inline editor cases. The raw
0/1/1 snapshots and log lines are retained in
[review-fixes-d5cd-native-editors.json](records/review-fixes-d5cd-native-editors.json).
Its native chooser did not install a file. The remote screenshots showed the
correct path but no selected file after Return. The driver now allows GTK path
validation to settle and uses one explicit Open accelerator. The subsequent
`76f9b5cf` trial, **42831333350**, passed the native dialogs, editors, chooser,
same-metadata replacement refusal and inherited/new-frame matrices, then failed
the cross-tab fixture's unsupported `control_pending(limit=20)`. The fixture now
uses the public ten-row bound; the zero-arrival assertion remains unchanged.
[Retained chooser events and receiver snapshots](records/review-fixes-76f9-chooser.json)
include the actual owner-selected filename, refusal at
zero, and fresh send/repeat 0/1/1. These are partial results, not acceptance green.

**P12 refinement:** each snapshot now hashes the native bytes again, including
when the File object and all its metadata survive. The old digest is not proof
of the current backing file. A changed selection during asynchronous hashing
refuses before snapshot extraction. Only digests/metadata leave the isolated
world; byte buffers remain transient. Staged hashes are independently checked.
Two new regressions and mutations pin the fresh hash and selection-race checks.
The native chooser case now changes the actual disk bytes, restores the exact
mtime, and requires refusal before dispatch, then installs a fresh selected File
for successful approval. This expanded browser case still needs its next run.

**Run:** full Node **203 passed**, no failures/cancellations/skips; **67 mutations
rejected, every baseline passed**. The unchanged Python checkpoint remains 185
tests OK. Only this build's superseded push/PR runs were cancelled; no owner or
lead run was cancelled. Ledger: 138 IDs before the next push, expected 140 after.

**Linux feedback, source `651096b2`:** **42832298611 / 42832312713** failed at
retaking the cross-tab fixture after release. Before that failure, both modes
passed the native disk-byte mutation with the same File object and timestamp,
as well as all ordinary native dialogs, editors and inherited/new frames.
[Retained receiver rows and exact digest questions](records/review-fixes-6510-native-file.json)
show both GOOD and EVIL SHA-256 questions, disk-change refusal at zero, fresh
approval/repeat 0/1/1, and the controlled cross-tab send/repeat 0/1/1. The outside
document also took its native path once; its immediate retake found pending
cleanup. With Runtime subscriptions disabled, dead contexts can survive in our
bookkeeping. Cleanup now retires a stale context only when the native protocol
rejects that context ID as missing. It does not treat an unavailable object,
arbitrary error or a failed restoration as realm destruction. The negative
regression initially checked too early and let the broad-error mutation survive;
it now waits until cleanup is either complete or waiting on native destruction.
The original safety assertion is unchanged. Full Node: **204 passed**. Mutation
audit: **69 rejected; every baseline passed**. The next Linux trial is pending.
Ledger: 140 before the next push, expected 142 after.

**Linux feedback, source `ace83b8e`:** **42833507627 / 42833520319** failed
at the synchronous new-shadow-root matrix. The cleanup fix, both cross-tab legs,
and explicit pay/delete adapter overrides passed. The shadow continuation was
stopped, but its target handoff threw before producing a resumable hold. Chrome
returned no InputEvent target range for the shadow endpoint. Chromium's
[native implementation](https://raw.githubusercontent.com/chromium/chromium/main/third_party/blink/renderer/core/events/input_event.cc)
filters ranges when their endpoints would be retargeted. This was absent from
our double. The new double reproduces filtering; a native TreeWalker carries
the precise endpoint privately instead. The isolated guard calls saved native
getters and creates an isolated walker before using the node. It reads no MAIN
node properties, mutates no public DOM, and exposes no private carrier. Native
brand conversion rejects forged handles. The inherited-getter/iterator probe
also exercises this path. Its removal mutation fails. Exact partial receiver,
native missing-context proof and shadow exception lines are retained in
[review-fixes-ace8-shadow.json](records/review-fixes-ace8-shadow.json).

**Run:** Node **205 passed**, zero failed/cancelled/skipped. Mutation audit **70
rejected**, every baseline passed. The full plain-Python sweep on `ace83b8e`
passed **185 tests, OK, 236.250 s**. Generated artifacts match and diff checks
are clean. The new native shadow-identity transport needs the next Linux trial.
Ledger: 142 before the next push, expected 144 after.

**Linux feedback, source `920ec23f`:** **42835200413 / 42835217594** failed
before the complete matrix, at the original native stopped-submission smoke
case. No pending submission appeared. This source is not verified and its
TreeWalker-only transport is superseded. [Exact failure](records/review-fixes-920e-world-identity.json)
is retained. The native TreeWalker root uses its node's own context; cloning
another TreeWalker did not give us an isolated node. The corrected transport
constructs an isolated StaticRange from the native endpoint, then uses that
range's saved native container getter. It never dispatches InputEvent, so no
shadow retargeting filter runs. The getter is found on the private native
prototype chain, accommodating both AbstractRange and NodeRange layouts.
Primary sources: [TreeWalker IDL](https://raw.githubusercontent.com/chromium/chromium/main/third_party/blink/renderer/core/dom/tree_walker.idl),
[AbstractRange IDL](https://raw.githubusercontent.com/chromium/chromium/main/third_party/blink/renderer/core/dom/abstract_range.idl),
[NodeRange IDL](https://raw.githubusercontent.com/chromium/chromium/main/third_party/blink/renderer/core/dom/node_range.idl).

The double now represents MAIN native handles separately from isolated nodes;
reading the MAIN handle's properties fails. A mutation bypassing the isolated
conversion is rejected. Node: **205 passed**; mutation audit: **71 rejected,
every baseline passed**. The next Linux trial remains required. Ledger: 144
before the next push, expected 146 after.

**Linux feedback, source `a64251e6`:** **42836125870 / 42836137343** failed
the same pre-matrix native stopped-submission assertion. The second identity
transport is also unverified. The next trial retains the previously proven
InputEvent path for ordinary document endpoints, and limits the replacement to
actual shadow endpoints authenticated by the saved native ShadowRoot host getter.
Test-build-only instrumentation records native type/realm booleans at that
handoff; no node properties, field values or contents are serialized. This will
distinguish missing native getter support from a wrong-world node without adding
Runtime subscriptions. The shadow test double and removal mutations remain
mandatory; no receiver assertion is relaxed. Ledger: 146 before the next push,
expected 148 after.
