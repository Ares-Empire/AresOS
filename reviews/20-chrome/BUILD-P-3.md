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
include the actual owner-selected filename, byte digest question, refusal at
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
