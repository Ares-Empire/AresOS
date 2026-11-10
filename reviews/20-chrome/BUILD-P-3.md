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
