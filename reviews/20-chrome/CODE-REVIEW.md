# Independent code review — CHANGES NEEDED

Reviewer: fresh `gpt-6.1-sol`, high, as brief 20 requests. Read-only review of
head `e31e75d242511f13e68bd482c6da661c2579b0e4`, including changes since the
interim review at `5901ca09`. No local browser/profile was accessed. These
findings are open; this is not a SAFE assessment.

1. **P1 — Owner input is intercepted during Claude's hold window.**
   `control/chrome/extension/page.js:92` treats every click/submission within
   the active 500 ms as Claude-caused. An owner pressing Enter on a submit
   button is stopped and turned into asking work. Browser-free probe:
   `prevented:true`, `reports:["submit_event"]`. Clearing the guard on owner
   input would wrongly release Claude's pending timer. The genuine X-input
   container test was pending when this review finished.
2. **P1 — External accessible labels bypass script-activation asking.**
   `page.js:59` omits `aria-labelledby` and associated `<label>` text, while
   the isolated reader recognizes them. A free handler calling `.click()` on
   a button named Delete only through `aria-labelledby` delivers the
   activation without asking. Browser-free probe: `delivered:1`, `reports:[]`.
   Match reader name semantics and test both wrappers and fallback.
3. **P1 — Prepared operations ignore newly imposed read-only restrictions.**
   `control/aresos_control/chrome/adapter.py:197` does not reread the owner
   list. Prepare a send, mark its site read-only, then submit: the unchanged
   binding still permits dispatch. A Python probe configured `store.get` to
   raise; `revalidate()` accepted without consulting it. Recheck top/frame
   restrictions before dispatch, including dialogs/trusted submissions.

Since the interim review, source changes address free-input approval marks,
checkbox/disabled binding, compose scoping, frame arming and pointer
translation, upload cancellation/HTTP hashing, preparation-time read-only
inheritance and definite-refusal settlement. Comprehensive browser
verification of these fixes is outstanding.

Checks run by the reviewer: page/reader Node suite, **10 passed**; Python
policy suite, **11 passed**; three focused browser-free probes reproducing
the findings; `git diff --check`, clean. No files were edited.

The CI suite remains a smoke subset. `smoke.json` at the reviewed head was
written with `passed:true` before the owner assertions; it alone cannot
establish success. No complete Now suite run twice or qualification
certification is warranted.
