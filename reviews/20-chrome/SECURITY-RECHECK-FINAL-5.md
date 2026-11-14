# Security re-check 5: the POST popup admission fix, package 20 (Chrome tools for Claude), PR #27

**Verdict: SAFE (no FIX open).** Two notes (one cheap hardening, one availability edge that fails closed).

Reviewed: `git diff 662e813a fe4f254e` (code in `0347b548` and `6066468b`, both in `control/chrome/extension/background.js`,
`lateReader`; tests in `background.test.mjs`; three probes; REPORT's "POST popup admission"), read in the detached review
copy at `fe4f254e` (`git status --porcelain` empty before and after). The failed shard's artifact and the passing
counterpart were read, not modified. No browser was started or touched; no workflow dispatched; two one-shot `gh run
view` calls (metadata only). Paths are repo-relative.

## Findings

### NOTE 1 (hardening): the `scriptParsed` match uses `params.url`, which a `sourceURL` comment can set; `embedderName` cannot be

- `background.js:126`: a context is learned when `params.url` equals the extension URL of `context.js`, `guard.js` or
  `reader.js` **and** `executionContextAuxData.isDefault===false`. The second condition is what makes it safe today: a
  page's scripts, including one with `//# sourceURL=chrome-extension://…/context.js` or an `eval`, run in the default
  world (`isDefault:true`; the artifact shows the page script with `"isDefault": true, "type": "default"`), and a page
  cannot create an isolated world. Only another extension's content script (the owner's own software, outside this
  tool's threat model) could emit a non-default context with a forged `url`, and even then the proof that matters is the
  next step: `lateReader` records a document only after `Runtime.evaluate` in that context finds this extension's own
  guard (`Symbol.for("aresos.chrome.guard.v2")`, `ready`), which exists only in this extension's isolated world. A forged
  context entry would be evaluated, return no factory, and be skipped (`:284`).
- Harm today: none. Smallest hardening: match `params.embedderName` (the URL as the embedder loaded it, not subject to
  `sourceURL`, present in every event in the artifact) instead of or in addition to `params.url`. One token in one
  line; worth taking when the file is next touched.

### NOTE 2 (availability, fails closed): a frame whose dead context sits in one target state while its live context sits in another cannot be "covered"

- `background.js:297–298`: `covered(frameId)` looks for a recorded document with a live context of that frame **in the
  same `state`** (the same debugger session). An iframe that moves out of process during the admission has its dead
  context in the parent's state and its live context in the auto-attached child target's state, so `covered` is false
  and the admission refuses ("take the tab again"). A frame removed during the swap has no live context anywhere, same
  result. Both are rare races (the swap must land inside the admission window) and both end in `release` with nothing
  left behind; a retake learns the live contexts from `Debugger.enable`'s replay, as the passing run did. Fail-closed,
  availability only; no change needed, recorded so the refusal is not read as a bug.

## The lead's items

### 1. After forgetting, can admission succeed while the live document isn't covered?

- **How the live context is learned.** Only from the renderer's own `Debugger.scriptParsed` for the extension's
  scripts in an isolated world (`preloadEvent`, :124–131): the new document's `context.js` (replayed by
  `Debugger.enable` or arriving while `setBreakpointByUrl` is in flight, as the artifact shows at context 2, scriptId 3)
  or the `guard.js`/`reader.js` that `lateReader` injects into every live frame with `chrome.scripting.executeScript`
  (:252; artifact: scriptIds 5 and 6 in context 2). The Runtime domain is not subscribed, so there is no other source;
  the injection is the second, independent route and the fourth Node test covers it with the replay hidden.
- **Fail-closed.** `forgotten` (:265) collects the CDP frame id of every context the renderer no longer knows (and only
  those: any other error still throws, :278). After the loop every forgotten frame must be covered by a recorded
  document whose isolated context is live and carries that frame id (:297–298); otherwise `lateReader` throws, so
  `initializeTab`'s race rejects, `admitTab`'s catch runs `release(tab)`, and the tab ends not controlled, not attached,
  not grouped, with no target state, no install record, the injected reader `clear`ed and the guard disposed. The third
  Node test is exactly the lead's case (`swapReplay=false`, no injection report: after forgetting context 7 the context
  set is empty), and it asserts each of those "nothing left" facts plus the `released` event, no `popup_admitted`, and
  the `unread` refusal in `reader_error`; the probe `post-popup-empty-contexts-count-as-read` (the `for` over `[]`) is
  rejected (`records/post-popup/final-local-6066468b-mutations.txt:464`). "No contexts left" never counts as read.
- **The case with nothing forgotten.** If no dead context was seen and the live context's events are late, the loop
  records nothing and the admission completes with no document record. That is the pre-existing late path and it is
  safe by design: a document with no record is `!isPreloaded` → `needs_reload`, every `input`/`resume` refuses until
  the guarded reload (`dispatch`, the `needs_reload` refusal), and a popup carries `popupNeedsReload` besides. The
  injected guard and reader are live in the frame (`set_control` answered), so reads are the late reader's withheld
  reads. The fix does not touch this.

### 2. Can a page forge the proof?

- No. The `isDefault===false` condition excludes every page-controlled script (default world), and a recorded document
  additionally needs this extension's guard found by `Runtime.evaluate` in that isolated context (:269–284), which only
  the extension's own `executeScript` or document-start install puts there. The context id is the renderer's; a page
  cannot pick it. NOTE 1 is the one cheap tightening (`embedderName`).

### 3. Is the frame-id match sound across the swap, in iframes too?

- The CDP frame id is the frame tree node's token, stable across a cross-renderer navigation of the same frame; the
  artifact shows the dead context 7 and the live context 2 both under frame `4855E56C457EF028289FDDC1DD4636B2`. Frame
  ids are not reused within a browser session. Out-of-process iframes are separate auto-attached targets with their own
  `state`; a swap into or out of process during the admission lands in NOTE 2 (fails closed). A frame detached during
  the swap has its dead context forgotten and no live cover: fails closed. A same-process iframe swap behaves like the
  top frame. Nothing here can pass an uncovered live frame.

### 4. Can forgetting drop a live guard?

- A context is forgotten only when the renderer itself answers `Cannot find context with specified id` for it
  (`nativeContextMissing`, :48, the same rule release's cleanup has applied since P27), and only if the map entry is
  still the very object the loop holds (`state.contexts.get(context.id)!==context` → rethrow, :278). A new renderer
  that reuses the numeric id overwrites the entry at `scriptParsed` time, so the stale object no longer matches and is
  not deleted. Forgetting removes only documents whose `isolated` is the dead context's `uniqueId` (:279). The error
  text is the inspector's, not the page's. A live guard cannot be dropped this way.

### 5. When admission fails, the popup is plainly uncontrolled

- `admitTab` fails only through its catch (`controlled.get(tab)===original` → `release(tab)`), unchanged. The artifact
  shows the whole release for tab `1637225932`: `released` event, cleanup evaluates (756 missing-context, 757 disposing
  the live guard `true`), `Debugger.disable` (758), network rules recomputed for the opener alone, badge back, and the
  popup `controlled:false` in every later `tabs` listing; the POST reached the receiver exactly once (REPORT's receiver
  counts; the row's own `page-receiver.jsonl` count 1 before and after). The second and third Node tests pin the same
  end state for the two failure shapes on the new code, including `admissions.size===0`, `releasing.size===0`,
  `preloadTargets` empty for the popup, `installRecord()` empty, messages `['set_control','clear']`, `Debugger.disable`
  and `detach`, never `group`. The transient window (`controlled.set` before `initializeTab`) is the admission itself:
  `take` dedups through `admissions`, and a call in that window waits on `pendingSetup` and fails with it (unchanged).

### Also checked

- **Harness and tab groups unchanged:** the diff touches no file under `control/chrome/ci/`, and `background.js`'s
  diff contains no `tabs.group` line. **Unit** byte-identical to `8b7e799c`. **No extension storage** (grep over the
  extension: zero hits); `manifest.json`, `control/settings/`, `control/generated/`, `control/aresos_control/`
  untouched. **What reaches Claude** is unchanged: the new `late_reader_context` line goes to the `audit` sink, which
  exists only in the CI wrapper.
- **The diagnosis matches the artifact.** `browser-boundary.jsonl:18576–18622`: `Page.windowOpen` → initial
  `about:blank` (GET) → `Page.enable` 750, `Page.getFrameTree` 751 → `Debugger.enable` 752 replays `context.js` in
  context 7 → `setBreakpointByUrl` 753 dispatched → `form_submit` commit, `context.js` in context 2 (scriptId 3), page
  script (context 1), load events → 753 completes naming scriptId 3 → `Target.setAutoAttach` 754 → injection
  (`guard.js`, `reader.js` in context 2), `set_control` ok → `Runtime.evaluate` 755 in context 7 **failed** → release.
  No `frameNavigated`, `executionContextsCleared` or `executionContextDestroyed` for the tab in that range. The passing
  counterpart's shard shows the POST popups admitted (`popup_admitted` lines) with the replay naming only the live
  renderer. `53ecc91b` plays no part: a `virtualGroup` popup makes no group call, and the error is a context error.

## Verified

- Read both code commits in full and the surrounding `prepareTarget`, `preloadEvent` (`scriptParsed`,
  `executionContextDestroyed`), `contextGone`, `destroyedTarget`, `linkPrivateDocuments` and the whole `lateReader`;
  the four new Node tests and the three probes.
- Local, no browser, `PYTHONDONTWRITEBYTECODE=1`: `node --test control/chrome_tests/*.test.mjs` 427 pass, 0 fail (the
  four `post-popup` tests among them); the three probes `MUTATION REJECTED` in `records/post-popup/final-local-6066468b-mutations.txt:462–464`.
- Artifacts read: `<builder worktree>/.work/finalpair/artifact/{browser-boundary.jsonl,service.txt}` at the
  cited lines and `…/pr-external-artifact/browser-boundary.jsonl` (the `popup_admitted` lines and the POST popup's
  event order); nothing modified.
- `gh run view 43631476260` (push, failure, `662e813a`) and `43631483821` (pull_request, success, same head), once
  each; metadata saved under `scratchpad/final-review/recheck-sec/`.
