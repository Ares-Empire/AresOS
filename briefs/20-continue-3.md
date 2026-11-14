# 20, continue 3: the page script in Claude's tabs only, his own Enter, finish "Now"

The **core** build of stage "Now": two required changes from the lead (2026-11-09), the owner's decision on taking
his tabs, and the rest of "Now" outside the adapters and qualification. Two side builds run at the same time in
their own worktrees (owner's direction, 2026-11-09): `briefs/20-adapters.md` and `briefs/20-qualification.md`.
`briefs/20-continue-2.md` and `briefs/20-continue.md` stand; where they differ, this brief wins. The stop rule is
`20-continue-2.md`'s: stop only when a guarantee of section 6 can't be met by any design on the fixtures; a bug a
test finds is fixed.

**Shared files are yours alone:** `definitions.py`, `unicode_words.json`, the generated artifacts
(`control/generated/`, `docs/control/TOOLS.md`), `control/settings/`, the base, the extension, the service and the
core harness. Leave the side builds' files alone: `sites.py` and adapter fixtures (adapters), and `qualify.py`,
`qualification.json`, `builds.json`, `build.py`, `qualification.py`, `ci/attestation.py` and the qualification jobs
of the workflow (qualification). If the core change needs a change there, make the smallest one and name it in the
report, so the package lead can merge the branches.

**Never start, read or touch Chrome, Chromium or any browser profile on this Mac: every browser test runs only in
containers on GitHub's Linux runners through the control-chrome workflow; locally run only plain-Python and Node
tests that start no browser.**

## 1. Blocking: the page script runs only in Claude's tabs

At `95ed8ac1`, `background.js` `configure()` registers `page.js` (MAIN world) and `guard.js` for every http(s) page,
in all frames and all tabs. `page.js` replaces `submit`, `requestSubmit`, `click` and `dispatchEvent`, locked so
they can't be changed, and the real call happens only if `guard.js` sees `aresos-page-call-v2` on `window` or
`document`. Anything outside that path is lost while the wrapper returns `true`: a detached `<a download>`'s
`click()` or `dispatchEvent` (a "save file" library: no download); a detached file input's `click()` (no file
picker); `new EventTarget()` event buses and any non-Node target (events silently lost); nodes in a shadow root the
guard hasn't watched yet; and a site that redefines those properties throws. That breaks his normal browsing in
every tab. Decision 25 says Chrome stays completely normal, and section 6 says the script goes into each **Claude**
tab. Patched natives can also trip sites' bot checks.

- **Outside Claude's group, nothing of ours changes a page:** no MAIN-world script, no changed prototypes or
  globals, no listener that cancels, stops or writes anything.
- **Injection before the page's scripts, in Claude tabs only.** The likely way: the debugger stays attached while a
  tab is controlled, so use `Page.addScriptToEvaluateOnNewDocument`, plus `Target.setAutoAttach` with
  `waitForDebuggerOnStart` for out-of-process frames and popups. Adding the DevTools commands this needs to the
  fixed list is approved by the lead: name each one in the report (he updates section 6). The private state and
  every relaxing decision stay out of the page's reach, as `20-continue-2.md` part 1 says. **If no mechanism can put
  the script in before the page's scripts in Claude tabs only, stop and report. Never fall back to all tabs.**
- **Taking an already-open tab of his** (the owner accepted a reload: "yea it's ok"; the lead's refinements):
  - **Reload only when Claude first acts in a taken tab** (click, key, fill, choose, tick, file, any asking input),
    not on taking it and not for reading. Reading and the reader (isolated world or DevTools) may attach late
    without a reload; only `page.js` must predate the page's scripts. A playing tab or half-typed text stays intact
    while Claude only looks. If reading turns out to need `page.js` too, drop this refinement and say why.
  - **Before that reload, the tool reports instead of reloading** when the page shows typed text that isn't saved (a
    field's value differs from its default, or editable content was changed) or is playing media. Claude tells him,
    and the reload runs only on a repeated call that says so through an explicit parameter, never silently.
  - **Never reload a document that a form submission loaded** (POST or any non-GET): a reload resubmits it, a send
    without its question. Refuse to act in that tab and suggest opening its address fresh in a Claude tab.
  - After the reload, every old reference is stale ("read again"), as after any page change.
  - Tests: reading without a reload; the first act reloads and refuses old references; unsaved text and playing
    media report instead of reloading, and the explicit repeat reloads; a POST-loaded page is refused with no second
    request reaching the receiver.
  - This is decided, not a JUDGMENT-CALL. The report names the exact behaviour and every DevTools command it uses;
    the lead writes both into section 6.
- **In Claude tabs, keep native behaviour except for holding asking actions.** Call the saved native function
  directly **unless the target's composed root is this window's own document**, checked with a native
  `getRootNode({composed: true})` and the document reference, both saved at `document_start` (that root covers
  shadow roots inside the document). So non-Node targets, detached nodes, and nodes in documents with no browsing
  context (`DOMParser` output, `document.implementation.createHTMLDocument`, `template` content, which report
  `isConnected` true but whose events never reach the guard) all get native behaviour. None of them can submit or
  navigate in a way that asks: a detached form can't submit, a detached anchor can only navigate, which is free,
  and inert documents have no browsing context. Drop the prototype lock if a page replacing a wrapper can't reach
  native delivery except through the fresh-frame route already reported as `unknown`; otherwise keep it and say why.
- **Tests, each comparing against Chrome without the extension**, in a tab outside Claude's group: a detached-anchor
  download; a detached file input's `click()` (the picker opens); an `EventTarget` bus with its return value; the
  return value of `preventDefault`; a fresh shadow root dispatching in its constructor; `window.dispatchEvent`; a
  site redefining `HTMLElement.prototype.click`; and `Function.prototype.toString` of the four functions. Run the
  same list in a Claude tab, where the only allowed difference is a held asking control. In a Claude tab also:
  `dispatchEvent` and `click()` on an element in a `DOMParser` document, in `createHTMLDocument` output and in
  `template` content each reach their listener with the native return value. Add a static test that no
  manifest or registered content script puts a MAIN-world script or a cancelling listener into every page.

## 2. His own Enter: try this before accepting the PLAN-GAP

The owner was told "your direct presses are never held". Try this (from mac-capacity, with the lead's condition):
- On every trusted input event (`keydown`, `keypress`, `keyup`, pointer events, `click`) that arrives while the
  extension has nothing in flight, the isolated world sets an "owner task" mark. It clears the mark with a message
  on its own `MessageChannel`: that message arrives as a new task, after the native default action that ends the
  input task (a microtask would clear it too early).
- Because tasks from other sources (a Claude-started timer) could run before that message, while the mark is set a
  submission counts as his **only if it is exactly the submission his own input causes**: for Enter, the form of the
  focused field his Enter targeted, with no other submitter; for a click, that form's submit, with the button he
  clicked as submitter. So a mis-attribution can only let through the submission his own key or click makes anyway.
- Everything else is held, as now. The mark and the verdict never pass through anything the page can reach.
- Section 6's test-2 cases for his input, strict, with the receiver's log, plus: a Claude-started timer that submits
  a different form, or the same form with another submitter, while his mark is set: held.
- If this can't be proven strictly on the fixtures, the PLAN-GAP stands; say so plainly in the report's first
  section, with the evidence, so the lead can correct what the owner was told.

## 3. The rest of "Now"

Everything the report lists as open for **Now** outside the adapters and qualification (among them the group 8
failure of the final policy-install job, where opening a tab after the release/close checks hit "invalid address";
the group 4 `exact native confirmation and mismatch matrix` until it passes everywhere; and every remaining blocking
or should-fix finding of
`BUILD-REVIEW-3.md` and `BUILD-SECURITY-REVIEW-3.md` that isn't repaired yet), until test groups 1 to 9, 11 and 13
pass by name, twice on the final head, with the base, Mail and boundary workflows green. Group 10 stays green: if
the injection change breaks an adapter test, fix the core cause, not `sites.py`. The package lead merges the side
builds afterwards and reruns everything twice on the integrated head.

**The fallback read of the committed journal** (for failed SQLite reads) stays minimal, and (lead's conditions):
- it reads only the committed journal, so R1 holds, and writes nothing new beside the record;
- its format stays one that 19b's projection can absorb without migrating acknowledgements.
List it under "moving onto 19b", with what replaces it there.

**Runs:** the stage may use about **85** runs of `control-chrome.yml` in all; the report gives the final count. Batch
commits into fewer pushes where that doesn't hide a failing step, and cancel superseded runs. If it would pass 85,
say so in the report and stop.

## Rules for this run

As `briefs/20-continue.md`, "Rules for this run". Read the specification from `origin/main` with `git show` after
`git fetch origin main`.
