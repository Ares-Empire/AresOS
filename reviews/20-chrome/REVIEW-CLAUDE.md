# Brief 20 (Chrome), Claude panel review: false passes

Reviewer: Claude (Opus 5.5), angle **false passes**: places where the tests and CI evidence would still pass even though the protection they claim is missing or broken.
Head reviewed: `60b94384` on `pkg/20-chrome` (runtime, CI harness and generated files identical to the verified source `ab7aba92`; `git diff ab7aba92 60b94384 -- control .github docs` is empty).
Method: read the briefs (`20-chrome.md` from `origin/main`, then `20-parallel-start`, `20-continue-3`, `20-integrate`, `20-integrate-2`), `REPORT.md`, the runtime (`page.js`, `guard.js`, `reader.js`, `background.js`, `adapter.py`), the CI harness (`browser.mjs`, `matrices.mjs`, `popups.mjs`, `fixture.mjs`, `compatibility.mjs`, `verdicts.mjs`, `site-results.mjs`, `run.sh`, the workflow) and the unit tests. Then ran 36 single or combined mutations of production code in a detached scratch worktree, each against the complete browser-free Node suite (148 tests), plus 3 scratch probe tests. I downloaded the two artifacts of PR run 42773249076 as data (no browser) and counted the CI log.
No browser, Chromium, profile or container was started on this Mac. The scratch worktree was removed at the end. Nothing was posted to GitHub.

## Summary

| # | Severity | Protection | False pass |
|---|---|---|---|
| F1 | **blocking** (for closing owner Enter) | Owner exemption only for *exactly his* form and submitter | Deleting both the form check and the submitter check passes all 148 unit tests, and every browser owner case too. The browser "timer while his mark is set" variants fire about 100 ms after the mark has already cleared. |
| F2 | should-fix | Nothing of ours in pages outside the group | The outside-tab comparison can't see `page.js`. CI's own Claude-tab measurement, taken with the wrappers active, is byte-identical to Chrome without the extension. |
| F3 | should-fix | Report first on unsaved typing or playing media | The protection is actually missing for about:blank-frame editors, excluded frames and media outside the DOM (`new Audio()`, Web Audio). Restricting the check to the top frame passes every test. |
| F4 | should-fix | Native passthrough unless the **composed** root is this document | Switching to a non-composed root (shadow-DOM controls are then no longer held by the wrappers) passes every test. The DOM double ignores `composed`, and no browser fixture holds a shadow-DOM control. |
| F5 | should-fix | CI green means every named case ran | A named case that never runs leaves the job green. Only the manual `audit-evidence.py` enforces 61/61. |
| F6 | should-fix | Delayed submission after his input is held; his trust is required | The "delayed" assertions are masked by one-use consumption. The unit replay test uses a formless button, so dropping all trust checks passes every unit test. The browser covers trust, not the delayed rule. |
| F7 | nit | Popups always reload on first act | `popupNeedsReload:false` passes every unit test. The browser catches it only if a popup happens to be preloaded. |
| F8 | nit | Never reload a POST document | Only owner- or approval-initiated (`form_submit`) POSTs are exercised. A script-initiated POST is not, and that path rests on the transition type plus a webRequest `documentId` the code says is sometimes missing. |
| F9 | nit | Group 6 excluded popups | No assertion that the excluded popup exists (default `tabs` page is 5), so the leg can pass vacuously. In this CI run it did execute. |
| F10 | nit | Group 7 password scan | It doesn't reassemble the 64 KB audit fragments, so a split sentinel escapes the regex. I reassembled all 19 fragmented messages of the final run: no sentinel. |
| F11 | nit | First-script guard | The capturing script sits after the body markup, not first in `<head>`, so a late-but-racy injection could still win. |
| F12 | nit | Group 6 GET excluded form | `counts(id)` is vacuous for GET, because the query replaces `case`. The handler counter carries the proof. |

Counts: **1 blocking, 5 should-fix, 6 nit.**

CI check: PR run **42773249076** (head `ab7aba92`): **61/61** named cases have exactly one `<name> PASS` line in **both** jobs, with zero `FAIL` lines. Python `Ran 171 tests … OK` (560.114 s external, 712.744 s policy). Node `# tests 148 / pass 148 / fail 0 / cancelled 0 / skipped 0`. The preliminary smoke, owner input and three page-forgery PASS lines are present in both jobs. This matches the report.
Run **42786714089** (head `60b94384`): see the last section.

---

## F1 — blocking (for the owner-Enter close-out): the exact-form / exact-submitter condition has no failing test anywhere

**Protection (continue-3 part 2, the lead's condition):** while his mark is set, a submission counts as his only if it is exactly the one his own input causes: the focused field's form with no other submitter for Enter, or the clicked button as submitter for a click. The required test: "a Claude-started timer that submits a different form, or the same form with another submitter, while his mark is set: held". The report says "Owner Enter: passes in CI, panel to confirm".

**Where:** `control/chrome/extension/guard.js:49`, in `ownerSubmission`: `…||owner.form!==form||owner.submitter!==(submitter||null))return false;`

**False pass:**
- Mutation **C3** removes both `owner.form!==form` and `owner.submitter!==…`. Result: **148/148 Node tests pass.**
- G7 (form only) and G8 (submitter only) also pass 148/148.
- Why the unit tests miss it: `page.test.mjs:248` constructs the mark-set window correctly, but only in the post-dispatch (phase 0) path. There, `other.submit()` is held by `!event?.isTrusted`, and `form.requestSubmit(button)` by `requestDepth`, before the form and submitter comparison matters. The synchronous path is different. There, the owner's event is still dispatching and the phase-0 checks are skipped, so the form and submitter comparison is the **only** defence. No test submits a different form or a different submitter from inside his event's dispatch.
- Why the browser misses it: `matrices.mjs:190` (`GROUP 2 owner defaults never exempt timer forms submitters or validation repairs`, fixture `fixture.mjs:133`) presses his key at +130 ms. The Claude-started timer fires at +230 ms. The mark is cleared by the `MessageChannel` message one task after his keydown/keypress/keyup, so at +230 ms there is no mark at all. The variants are held by the ordinary hold window, not by the condition they are named for. `owner-input` (`browser.mjs`, timer at +300 ms) has the same timing.

**Reproduction:**
- C3, G7 and G8 each: `node --test control/chrome_tests/*.test.mjs` gives `tests 148, pass 148, fail 0`.
- Scratch probe, run in a copy of `page.test.mjs` with its fixture: the owner's trusted Enter keydown handler synchronously calls `other.requestSubmit()`, `other.submit()` or `form.requestSubmit(secondButton)`, then the probe asserts zero arrivals.
- Unmodified code: the probe **passes**.
- Under C3, G7 or G8: it **fails** ("other-form must stay held" or "other-submitter must stay held").
- So the code is right today; nothing pins it.

**Why it matters:** Claude's earlier work can change page state, for example by typing into a compose form. His later Enter in another field, while Claude's hold window is still active, can then make the page's own handler submit Claude's form. The lead's condition exists for exactly this mis-attribution, and it currently rests on an unpinned comparison.

**Fix:**
- Add the probe above, or an equivalent, to `page.test.mjs`. Also add a phase-0 case with a trusted native default for another form: `f.originalRequestSubmit.call(other)` after the dispatch, while the mark is set.
- Add a browser fixture variant where his own Enter keydown handler synchronously calls `otherForm.requestSubmit()` and `form.requestSubmit(otherSubmitter)`. With the receiver's log, expect 0 before approval, 1 after, and still 1 after a repeat.
- Relabel the existing timer variants as "after his mark", because that is what they prove.
- Until this exists, don't write owner Enter as confirmed.

## F2 — should-fix: "outside Claude's group" compatibility cannot detect our page script

**Protection (decided):** outside the group, nothing of ours changes a page: no MAIN-world script, no changed prototypes or globals. The report lists "native compatibility against Chrome without extension" under group 7 as part of the evidence.

**Where:** `control/chrome/ci/browser.mjs:41` (`compareCompatibility(outside, baseline.native)`), measurements in `control/chrome/ci/compatibility.mjs:7-29`.

**False pass:** every measured item is one that `page.js` deliberately reproduces:
- `Function.prototype.toString` of the four natives is faked through `nativeStrings` (`page.js:72`).
- The detached, inert, `window`, `EventTarget` and unconnected-shadow targets all take the native passthrough (`page.js:16`).

So the comparison is equal whether or not the wrappers are installed and active.

**Reproduction (from CI's own evidence, run 42773249076 external):** `native-controlled.json == native-baseline.json` is `True`, and `native-outside.json == native-baseline.json` is `True`. The controlled measurement runs in a Claude tab with `page.js` active (the same case then holds asking controls). A measurement that is identical with active wrappers cannot show their absence outside.

For runtime injection paths, as opposed to the manifest or `registerContentScripts`, the only remaining evidence is the static test at `background.test.mjs:187-205`. It inspects only the manifest and the registration list. For example, a mutation adding a MAIN-world `chrome.scripting.executeScript` for non-controlled tabs in `webNavigation.onCommitted` passed all Node tests. I don't claim that particular mutation activates the wrappers, because `page.js` returns an inactive factory when it has a private relay. The point is that nothing at runtime looks.

**Fix:**
- Add a discriminating fingerprint to the compatibility page that our wrappers can't hide. Examples:
  - `Object.hasOwn(fn,'prototype')` for the four natives and `Function.prototype.toString` (native methods have no own `prototype`; the wrappers are `function(){}` expressions);
  - the source text returned by a fresh same-origin iframe's own `Function.prototype.toString.call(HTMLElement.prototype.click)`.
- Assert outside == baseline, and assert that the Claude-tab value differs in exactly that fingerprint, so the probe is shown to discriminate.
- Keep the behavioural comparisons as they are.

## F3 — should-fix: "report first on unsaved typing or playing media" is missing in common cases, and the tests can't notice

**Protection (owner's accepted reload, continue-3 part 1):** before the first-act reload, report instead of reloading when the page shows unsaved typing or plays media. Reload only on the explicit repeat.

**Where:**
- `background.js:585`: loops over `current.frames` only. `facts()` drops `about:blank` frames (`background.js:433`) and excluded frames (`:434`). `lateReader` never injects into `about:blank` (`:117`).
- `reader.js:198-211`, `reloadState()`: `playing` is `all().some(AUDIO|VIDEO && !paused)`, i.e. only media elements attached to an inspected DOM.

**Missing protection:**
1. **Rich-text editors in `about:blank` iframes** (designMode or contenteditable bodies written by script, common in CMS editors): never inspected, and `reloadIdentity` skips them too (`:368`). His half-typed text is lost silently on Claude's first act.
2. **Excluded-host iframes** with typed text: skipped by the dirty check. When their load method is recorded as GET, the reload proceeds and the text is lost.
3. **Audio from `new Audio(...)` or Web Audio** (common for players): not in any DOM root, so `playing=false`, and the reload stops it silently.

**False pass:**
- The dirty fixture (`fixture.mjs:58-61`) is one top-frame `<input>` plus an attached `<audio loop>`.
- Mutation **B10** limits the check to the first frame (`current.frames.slice(0,1)`): **148/148 Node tests pass**, and the browser `GROUP 8 taken tabs…` case would pass too, since it has no frames.
- The popup dirty case is likewise top-frame only.

**Fix:**
- Treat every frame that can't be inspected (`about:blank`, srcdoc, excluded, a reader that fails) as "may have unsaved text", and report first.
- Use Chrome's own `tab.audible` from `chrome.tabs.get`, which the extension's `tabs` permission already provides, in addition to the DOM check. It covers detached and Web Audio.
- Add browser fixtures: an iframe draft (same-site and cross-site), an `about:blank` designMode editor, and `new Audio().play()`. Each expects `reload_required` with the load count unchanged, then the explicit repeat.
- Add a unit test that fails under B10.

## F4 — should-fix: the **composed** part of the root check is unproven for holding

**Protection (continue-3):** call the saved native directly unless the target's *composed* root is this window's document. The composed root "covers shadow roots inside the document", so script `click()`, `submit()`, `requestSubmit()` and `dispatchEvent` on shadow-DOM controls stay held by the wrappers, including roots the guard hasn't watched yet.

**Where:** `page.js:16` (`options({composed:true})`). The test double is `page.test.mjs:33`: `class Node … getRootNode(){return this.root??document;}`. It ignores the `composed` option entirely.

**False pass:**
- Mutation **P3** (`composed:false`): **148/148 Node tests pass.**
- In a real browser, every node inside a shadow root then takes the native passthrough, so `closedRoot.querySelector('form').submit()` (no event; `submit` events don't cross the shadow boundary) is no longer held unless that root already happened to be watched.
- No browser fixture has an asking control inside a shadow root. The only shadow fixtures are `password-matrix` (reading) and the compatibility page (a non-asking custom event on an *unconnected* constructor-time element, which takes the passthrough for detachment, not for composition).
- P1, P2 (`isConnected`), P4 (page-replaceable `getRootNode`) and P5 (always false) are all caught, so the detached and inert half is well proven.

**Fix:**
- Make the double honour `composed` (return the shadow root when it is false).
- Add a browser fixture: a closed shadow root created and used in the same task, holding a POST `<form>` with a submit button. Script calls `.click()`, `form.submit()` and `requestSubmit()`. Expect a hold, with the receiver at 0, then 1 after approval, then 1 after a repeat.

## F5 — should-fix: a named case that never runs leaves CI green

**Protection claimed:** "green twice" means all 61 named cases ran and passed in both install modes.

**Where:**
- `browser.mjs:167` throws only for *failed* rows (`matrices.mjs:476` returns `results.filter(!passed)`).
- `run.sh` and the workflow never compare `matrices.json` with the inventory, and never require true verdicts.
- The only completeness checks are the static source scan `verdicts.test.mjs:60`, which matches the text `await check('…'` whether or not it executes, and the manual `reviews/20-chrome/audit-evidence.py` over retained records.
- Asymmetry: adapter rows *are* inventory-checked at runtime (`site-results.mjs` throws on an incomplete inventory); core rows are not.

**Reproduction:** mutation **H1** makes `GROUP 9 Chrome host service crash cutpoints never replay` conditional (`if(process.env.NEVER_SET)await check(…)`). Result: **148/148 Node tests pass**. In CI no row would fail, so the job stays green, with `groups[9]=false` written silently. The qualification pipeline would then record a failure, which is safe for production. But acceptance "green twice" would be a false pass unless someone reruns the audit.

**Fix:** at the end of `browser.mjs`, fail unless:
- the sorted names in `matrices.json` exactly equal `REQUIRED ∪ SUPPORT`;
- every core and adapter verdict is true;
- groups 1–11 and 13 are true and group 12 is false. Once 18d lands, replace the group 12 condition with its own rule.

## F6 — should-fix: "delayed submission is held" and "his input must be trusted" lean on masked assertions

**Protections:** a submission his input starts after a delay inside the short limit is held, and a page-forged (untrusted) input never counts as his.

**Delayed rule:**
- `guard.js:46` clears the mark through `MessageChannel`. Mutation **G9** removes the clearing: 148/148 pass. Clearing only after 50 ms or 250 ms (G9b, G9c) also passes 148/148.
- The "never delayed" assertions in `page.test.mjs:236` ("the exemption ends on the private channel task") and in the browser `owner-sync` (`matrices.mjs:177`) come *after* a synchronous submission has already consumed the one-use mark. So they are held by `consumed`, not by the clearing.
- A probe where his Enter is unconsumed (the page prevents the default), followed later by a trusted native submit, stays held under G9 because of `defaultPrevented`. Under G16 it stays held because the mark was cleared. Each check masks the other.
- No test isolates the rule the brief states.

**Trust:**
- **C2** removes `!event.isTrusted` from both `ownerInput` (`guard.js:33`) and `ownerSubmission` (`:49`): **148/148 pass.**
- `page.test.mjs:298` (`group7 replay of a formerly trusted owner event…`) replays a click on a *formless* button, so `owner.form !== form` holds the submission even without any trust check.
- My scratch probe (an untrusted Enter keydown on a form field whose handler submits) **fails under C2** and passes on current code.
- The browser `owner-replay` case (receiver count must stay 1) would catch C2. So CI evidence holds; the unit level is a false pass.

**Fix:** add the untrusted-Enter probe and an "unconsumed owner mark, then a delayed submission" case, both with a submitting form field, to `page.test.mjs`. Add a browser variant whose Enter handler submits only after a delay, without a synchronous submission. Mutations G9, G16 and C2 should each fail at least one test.

## F7 — nit: "popups always cross the first-action boundary" is unpinned at unit level

`background.js:257` sets `popupNeedsReload:true`. Mutation **B8** (`false`): 148/148 pass.
- The browser popup cases catch it only if the popup's first document happened to be preloaded. Otherwise `needs_reload` comes from `isPreloaded` anyway.
- The report says popups reload "even if their initial navigation happened to receive a startup guard".
- **Fix:** a unit test that admits a popup whose document *is* preloaded, and asserts `needs_reload` and the first-act reload.

## F8 — nit: POST refusal is proven only for `form_submit`-transition POSTs

`background.js:715-729`:
- A top-level `typed` or `link` commit is recorded as GET unless a later `webRequest.onCompleted` with the matching `documentId` overwrites it.
- The code comment says Chrome sometimes omits that `documentId`.
- The fixtures load POST documents only by his key (`take-post`) or by an approved trusted click (`popup-post`), both `form_submit`.
- Chrome's own `TransitionType` docs say script-submitted forms may not be `form_submit`. I believe current Chromium does mark them `form_submit`, but couldn't verify offline.
- Unit tests catch B1 (unknown treated as GET) and B2 (`form_submit` given the GET fallback).

**Fix:** add a browser fixture where page script (a timer, no gesture) submits a POST form into the top-level document and into a named popup. Take the tab or popup, act, and expect refusal with the receiver count unchanged.

## F9 — nit: the group 6 excluded-popup leg can pass vacuously

`matrices.mjs:281` loops `for(item of tabs.items.filter(url includes 'approval.test'))`.
- `call('tabs')` returns at most 5 items (`background.js` `command.limit||5`).
- There is no assertion that the popup exists.
- In run 42773249076 the leg did execute: `tool.jsonl` shows `total 2`, the approval.test tab listed, and `take_tab` refused in both jobs.
- **Fix:** list with a cursor or limit, and `assert.equal(matches.length,1)`.

## F10 — nit: the group 7 password scan is not fragment-safe

`matrices.mjs:291` and `:400` regex-scan `browser-boundary.jsonl` line by line. `background.js:130` splits audit values over 64,000 characters into separate `json_fragment` lines, so a sentinel straddling a boundary would not match.
- The final run has 19 fragmented messages (100–177 KB). Reassembled, none contains the sentinel, so the evidence holds.
- **Fix:** reassemble fragments by `offset` and `total` before scanning, or scan with a split-tolerant search.

## F11 — nit: the first-script fixture is not the earliest possible script

`fixture.mjs:47-48` captures `HTMLFormElement.prototype.submit` in the single `<script>` at the end of the body. The real breakpoint mechanism is deterministic, but a regression to `executeScript(injectImmediately)` after commit could still beat that script on a small page.
- **Fix:** put the capture in the first `<script>` in `<head>`, before any markup. Optionally also capture `click`, `requestSubmit` and `dispatchEvent`.

## F12 — nit: the GET excluded-form receiver assertion is vacuous

In `matrices.mjs:297-300` (`excluded-form`, method `get`), a GET submission replaces the action's query, so an arrival would have no `case` and `counts(id)` stays 0 regardless. The proof really comes from `counts('handler-'+id)===0`.
- **Fix:** add a hidden `case` field, as the other GET fixtures do.

---

## Protections checked and found properly proven

- **Verdict aggregation** (`verdicts.mjs`): a missing, duplicated, non-boolean or unknown row cannot qualify. Group 12 is hard-false, and `qualify.py:240` additionally requires `groups['12'] is True`, so nothing can mark it true. A failed adapter disables only its site; shared prerequisites disable dependents. Acting needs all four core groups (`adapter.py:102`). Missing or crashed browser runs produce no `qualification-result.json` and fail every group.
- **Manifest and registration static test:** catches an all-pages MAIN registration (the original 95ed8ac1 regression).
- **Passthrough for detached, inert, `window` and non-Node targets:** P1, P2, P4 and P5 are all caught (`page.test.mjs:136` and the root-replacement test). CI's measured inside and outside comparisons match Chrome without the extension, so the *behavioural* normality the owner cares about is proven.
- **In-flight Claude input never counts as his:** C1 (both `inFlight` checks removed) is caught at unit level (`page.test.mjs:236`). By reasoning, the browser `owner-flight` case (receiver 0 while Claude's handler is busy) would catch it too. G5 and G6 alone are layered defences.
- **Phase-0 owner checks:** G10 (one-use), G12 (trusted default), G13 (repairs and mutations), G14 (`defaultSubmission`), G15 (`requestDepth`) and G17 (whole post-dispatch block) are each caught.
- **His real input passes and Claude's timer stays held:** `browser.mjs` owner-input. Receiver: `owner-input` 1, `scheduled-input` 0, with a 128 ms delay that is inside the active hold. The case would fail if the exemption were removed.
- **Page forgery:** `page-forgery`, `hostile` and `relay-hostile` each give receiver 0, then 1, then 1, in both jobs.
- **Reload on take:**
  - reads never reload (load count 1 after take plus two reads);
  - the first act reloads exactly once, and old references are stale;
  - a dirty or playing (top-frame DOM) page reports `reload_required` without reloading, and the explicit repeat reloads;
  - B3 and B3b are caught.
- **POST and unknown method never reload:** B1 and B2 are caught. `take-post` has receiver count 1 after the refusal and after a history-back attempt.
- **Popups:**
  - only a controlled opener admits a popup (B5 caught; ordinary opener untouched, receiver load 1);
  - opener departure revokes control (B11 caught; browser close and release cases);
  - form-target GET popups never reload (B6 caught);
  - POST popups are refused with exactly one POST at the receiver (audited);
  - per-popup Stop never reloads (B7 passes the unit suite, but by reasoning the browser catches it through the `loaded-popup-stop` count, which `audit-evidence.py` also checks, and the same-document probe);
  - the opener relationship survives the reload (`loads[1].opener`, plus the `postMessage` flow at the receiver);
  - native window lists and focus are unchanged across Stop.
- **Badges** are read from `chrome.action.getBadgeText`, Chrome's own state, not the extension's map.
- **Receiver independence:** apart from F12, the asking cases end in `approval()` (0, then 1, then 1 on the fixture's own log) or explicit `counts` checks. `audit-evidence.py` cross-checks 135 adapter sequences against raw `receiver.jsonl`.
- **CI run 42773249076:** both jobs carry exactly 61/61 named PASS lines, no FAIL lines, Python 171 OK, Node 148 with 0 skipped. Both install modes really used their install path (`prepare.mjs`; different extension IDs per job). This matches the report's figures.

## CI on the real head, run 42786714089

PENDING_HEAD_RUN

CHANGES-NEEDED
