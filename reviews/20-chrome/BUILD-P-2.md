# Part P — feature-preserving continuation

**In progress; not acceptance green.** The lead's 2026-11-10 13:15 direction supersedes the three fallback
choices in the review-fixes brief. No browser or profile on this Mac was started, read or touched. The state
worktree and branch remain untouched. PR 27 remains a draft; no merge was performed.

## Built

- **P1:** the extension sends `Debugger.pause` before `Page.handleJavaScriptDialog`. The modal need not execute
  a page task to arm that protocol barrier. When the continuation pauses, fixed extension-owned code arms each
  isolated guard, verifies its private document identity, then resumes. It grants no previous approval allowance.
  The in-flight hold remains through the completion barriers. An ordinary native-dialog browser matrix now
  requires successful alert/confirm/prompt answers from Claude, native owner input and independent page tasks,
  including confirm/prompt dismissal; each resumed form must ask and retain receiver 0/1/1. A refusal fails this
  matrix. The browser-free test makes Runtime evaluation fail while the modal is open, and independently requires
  the debugger pause before answering.
- **P12:** selected files are hashed with the native Blob/File `arrayBuffer` in the isolated world. Only the digest
  and metadata are serialized. The immutable File cache retains no byte buffer. SubtleCrypto is used on secure
  pages; a local SHA-256 implementation keeps HTTP pages working too. Its padding and multi-block cases, including
  one million bytes, agree with Node's SHA-256. File identities use `getRandomValues`, which is available on HTTP;
  the earlier `randomUUID` call failed there. All frames' selected-file facts enter both binding implementations;
  questions show name, size and SHA-256. The added browser case uses the real native chooser, then changes bytes
  with the same name/size/date, requires refusal before dispatch and sends the fresh approval once.
- **P2:** ordinary blank/srcdoc rich-text editor fixtures each exercise a successful 0/1/1 send and a changed-draft
  refusal followed by a fresh successful approval. The guarded inherited-frame path is retained. Empty top-level
  `about:blank` creation no longer attempts a host-permission-dependent scripting injection before its requested
  web navigation. Inline documents still receive their guarded reader. Document `designMode` now reports unsaved
  editor content even without a contenteditable attribute.
- **CI fixes from the completed container:** review pages fell through a second independent `if` to the default
  404; the route is one chain now, with an actual HTTP regression. All tab inventories use the public ten-row paging
  contract and follow its cursors. Cross-site password controls have a frame large enough for native input.
  The native donor waits for completed release before use, retaining that invariant. Send confirmations bind an
  existing outside draft and bind its absence when there is none; an absent draft no longer removes the ordinary
  confirmation feature.

## Evidence and pending work

**Run:** full Node: **193 passed, zero failed/cancelled/skipped**. Focused Python: **44 tests, OK**. The expanded
mutation audit rejects **58 mutations**, with every baseline passing. It includes the pre-answer debugger barrier,
HTTP file hash, selected-file binding, designMode and actual review HTTP route. The full Python sweep passed **184 tests, OK, 250.882 s**. Generated artifacts match and `git diff --check` is clean.

**Run:** source `cbe641a8`, Chrome runs **42803248244** and **42803256661**, failed. The external artifact completed
all **74** named cases, **48 passed / 26 failed**; this is not acceptance evidence. Exact failed names and browser
log lines are retained in [review-fixes-cbe-failures.json](records/review-fixes-cbe-failures.json). Thirteen new
review cases were served the wrong HTTP response. Other failures identified the modal Runtime wait, HTTP file
identity API, opaque blank creation, designMode omission, fixture paging and geometry, and premature donor use.
No missing or failing case was counted as green. The full Python stage correctly did not run after browser failure.

**Read/inference:** Chromium routes `Debugger.pause` through its interrupt path; Runtime evaluation does not use
that path. This explains the observed modal wait; the new native behavior still requires the next container proof.
Primary source: [browser DevTools session](https://raw.githubusercontent.com/chromium/chromium/main/content/browser/devtools/devtools_session.cc),
[renderer DevTools session](https://raw.githubusercontent.com/chromium/chromium/main/third_party/blink/renderer/core/inspector/devtools_session.cc).

**Pending decision tracking:** missing private guard coverage still fails closed before a native answer. A taken
document that already has a modal before its first guarded reload is a case to resolve explicitly: late wrapping
cannot cover native functions cached before taking the tab. The ordinary preloaded path is being preserved and
tested, rather than accepting a modal refusal. Any remaining feature-removing case must be listed for the lead and
owner in the closing report; it is not approved by this checkpoint or by a passing ordinary-dialog matrix.

**Run ownership:** only runs created by this build's pushes were cancelled. The two pending `40996d6b` runs,
**42809354155 / 42809362333**, were superseded by known fixes and the new direction; no run started by the owner or
lead was cancelled. The branch ledger is **126 Chrome IDs before the next push**, **128 after it** (the following harness-only push brings it to 130) (allowance about
155). No force push or hook bypass was used.

**Not verified:** the new native barrier, native chooser and editor browser cases; final-source complete Chrome,
base, Mail and boundary twice; live signed-in sites; panel confirmation of owner Enter. Group 12 remains false.

**CI feedback:** a failed named case now retains its original failing row, raw receiver artifacts and incomplete
verdicts, then exits red immediately. A successful run still executes every case and the full Python sweep;
`assertComplete` still rejects missing cases. A browser-free test verifies the retained failure cannot qualify.
This avoids spending another full matrix on failures already known in the same run.

**Run — first short feedback batch:** source `683f333e`, Chrome **42816887474 / 42816898103**, both modes,
failed at the actual native-chooser selection assertion. The file was not selected; no receiver effect was allowed.
The new ordinary blank/srcdoc editor matrix passed before that failure. The retained external proof is
[review-fixes-683-editors.json](records/review-fixes-683-editors.json): four independently audited 0/1/1 sequences,
including both changed-draft refusals at zero. This is partial evidence, not complete acceptance. The chooser
now activates the exact Open/Open File window, allows the native path field to settle, and captures its opened,
path-entered and chosen states. Native dialogs run earlier in the next matrix. The receiver assertions remain
unchanged. The ledger is 130 IDs before this push, 132 after it.
