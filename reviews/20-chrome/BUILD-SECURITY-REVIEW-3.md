# Independent interim security review — final browser evidence still required

Date: 2026-11-09. Reviewer: `gpt-6-astra`, as brief 20 requests. This is an
interim review of the continuation implementation, not a SAFE assessment.
HEAD during review was `8013537646e5407423d5a459ca67dfa5b5b37cf2`; the working
tree was changing concurrently. Findings below describe the working files at
the time of each probe, followed by repairs observed during this review.
The reviewer changed only this report. No Chrome, Chromium, browser profile,
container, real account, or real service mutation was used. The DOM Standard
was read through the web retrieval tool; all executable probes were Node.

Read: continuation briefs, section 6 from `origin/main`, the earlier interim
security reviews, isolated guard and reader, MAIN wrappers, background/native
confirmation path, service policy/adapter, qualification publisher, workflow,
and their focused tests. This is not an exhaustive review of the shared base
or a substitute for the required final-head receiver runs.

## Confirmed defects found, and repairs observed

1. **P1: a retained owner event could be replayed to obtain an owner verdict.**
   `guard.js` retained the native event object and checked only its current
   `eventPhase`. Page code could save a physical event, then dispatch that same
   object during the hold after extension input finished. Its phase became
   nonzero again, so a handler's `form.submit()` was exempt. The
   [DOM dispatchEvent algorithm](https://dom.spec.whatwg.org/#dom-eventtarget-dispatchevent)
   resets `isTrusted` to false before dispatch; the guard did not recheck it.
   The browser-free guard probe printed:

   ```text
   {"replayedTrustedEventNowFalse":false,"arrivals":["native"],"reports":[]}
   ```

   The fixture explicitly modeled the browser's reset to false. It did not
   establish Chrome delivery. The repaired `ownerDispatch()` now also checks
   `owner.isTrusted`. The added formerly-trusted-event regression passed in
   the focused Node run. A real physical-input/receiver replay case remains
   required.

2. **P1: the further-submission allowance could send twice.** A stopped
   `requestSubmit()` resumed with two passes. If its submit handler called
   `form.submit()` without cancelling the event, the further pass sent once
   and the uncancelled default sent again. Running the actual guard with the
   repository's mock DOM fixture printed:

   ```text
   {"before":0,"after":["native","event"],"handlers":1,"held":[{"id":"h1","kind":"submit_event","element":"e1","submitter":null,"cancellable":true}]}
   ```

   The repair retains the enclosing submission event, cancels its default
   before granting the single further same-form pass, and limits that pass
   to the enclosing dispatch or an approved consequential change. The new
   no-page-cancellation regression passed in Node. Receiver proof is still
   needed for this case, nested `requestSubmit`, another form, and a second
   attempt.

3. **P1: HTML confirmation text was absent from the actual reader.** The
   policy and service binding expected `target.page_dialog`, but the reader
   never produced it. An `OK` button inside a dialog saying `Delete messages?`
   therefore classified as free; the guard likewise omitted that text.
   This was confirmed by tracing the reader output and classifier, not by
   running a browser. The current reader supplies dialog identity, kind,
   text and button; both binding implementations include it, and the guard
   includes dialog text. Exact text/identity changes and fresh-dialog
   classification need receiver tests. Native confirmations are a separate
   path and do not establish HTML dialog coverage.

4. **P1: queued password history could arrive after a synchronous value
   read.** The parallel source reviewer identified the ordering: within one
   handler, a field changes text to password to text, then calls
   `requestSubmit()`. The guard immediately reads form facts, before the
   MutationObserver callback marks the historical password field. The value
   could also remain in `traces` after subsequent protection. Source review
   confirmed that ordering and the absence of a pending-record drain.
   The primary agent added `observer.takeRecords()` processing before each
   password check. Its lowercase transition regression passed in Node.
   A follow-up review found that historical `PASSWORD` and
   `CURRENT-PASSWORD` values still needed case-insensitive handling; that was
   sent to the primary agent and is now normalized in both historical paths.
   Final coverage must include those spellings and real same-task reads,
   with the complete extension/service audit.

5. **Qualification repeats could block publication.** The planner used only
   the shipped baseline, while preparation appended to the verified data
   branch. Before a baseline PR merged, the next run repeated already-held
   keys and failed record validation, potentially withholding a new beta
   result too. Preparation now skips previously recorded pairs only when
   their core and adapter results agree, and refuses conflicting repeats.
   The publisher also now treats an unchanged staged record as a successful
   no-op, avoiding false daily publication-failure issues. These repairs were
   read; this reviewer did not execute the publisher or real attestation
   verifier.

6. **The unused CDP whitelist still contained `DOM.getDocument`.** Section 6
   explicitly excludes whole DOM methods because they may return field
   attributes. No reachable arbitrary-CDP service command was found, so this
   review did not prove a password leak through it. The primary agent removed
   that method and the other unused DOM upload methods from policy. The
   fixed-command and generated-policy refusal tests still belong in the
   final evidence.

## Evidence run

Both exploit probes loaded the `fixture()` function from
`control/chrome_tests/page.test.mjs` using Node `fs` and `vm` and ran the real
working-tree `guard.js` and `page.js`. The first attached a submit handler
calling `form.submit()` without `preventDefault()`, stopped `requestSubmit`,
then resumed once. The second armed and finished a hold, dispatched one
trusted mock click to establish owner state, attached a submit handler,
changed the retained mock event's `isTrusted` to false to model native
redispatch, and dispatched it again. Both exited 0 and printed the JSON above.
Their arrival arrays are mock native-effect counters, **not HTTP receiver
logs**.

After the corresponding repairs, the reviewer ran:

```sh
node --test control/chrome_tests/page.test.mjs control/chrome_tests/reader.test.mjs
```

The first run printed 18 tests, 18 passed, 0 failed. After the pending-password
drain and its regression were added, the same command printed 19 tests,
19 passed, 0 failed, 0 skipped. That second run preceded the historical
uppercase follow-up. After the historical case normalization, a final focused
`node --test control/chrome_tests/reader.test.mjs` run printed 6 tests,
6 passed, 0 failed, including the uppercase historical regression. These
results cover only the mocked DOM conditions in
those files.

## Remaining acceptance evidence and review limits

- The authority move is materially better: MAIN has no control object or
  approval identity; isolated state controls marks, consumption, clearing,
  owner verdict and native resume. Page reports are still adversarial input.
  The final receiver tests must exercise forged report objects and getters,
  event replay, prototype replacement, and both wrapper and native fallback
  paths; the existing mock realms share classes and cannot prove Chrome's
  real world separation.
- Native confirmation matching now compares kind, text, button, frame URL,
  frame and browser document, and consumes the expected confirmation before
  accepting. This was read, not browser-verified by this reviewer. Every
  mismatch, second dialog, control release and independently asking dialog
  still needs final-head evidence.
- Password qualification and owner read-only restrictions are now checked
  again before prepared execution in the service. No global password-safety
  claim follows from the 19 Node tests: all excluded field kinds, frames,
  open/closed roots, transient mutations and all output/audit channels need
  the specified receiver-container tests.
- The qualification verifier pins repository, workflow, source branch and
  hosted-runner policy and checks an append-only record before accepting it.
  However, at the last search in this review there was no writer for the
  `qualification-result.json` consumed by `qualify.py pair`; missing output
  fails every group closed. Complete named-suite result production and
  delivery/publisher tests are still required. Do not turn smoke success into
  qualification success.
- The native Enter owner case is not proved by `eventPhase`: activation can
  occur after the phase resets. Holding an uncertain case is the permitted
  PLAN-GAP in continue-2, not grounds to weaken its strict expected test or
  claim that it passed.
- This review has not run or certified the required two full final-head
  browser suites, the complete named groups, the base/Mail/boundary workflows,
  or the full durable-state fault sweep. The parent run must continue and
  record their actual outcomes. No partial-green or final SAFE verdict is
  issued here.

## Follow-up: reader observation, native modals and owner exclusions

Reviewed at HEAD `ea2625ba4f57f7eec33c99fc2629491e936fa8e2` with concurrent
working-tree changes, on 2026-11-09. This follow-up again used only source,
Node mocks and plain Python. The parent reported receiver evidence from run
`42616318628` at `e1f1bacf` for page forgery, password roots/traces, upload,
Stop and nine crash cutpoints; this reviewer did **not** independently inspect
that runner artifact in this follow-up. Those results do not certify the
subsequent changes reviewed here.

**Reader observation: no new blocker found in the change reviewed.** The
general observer now tracks revisions without requesting old attribute or
character-data values. A separate historical-protection observer requests old
values only for `type`, `autocomplete` and `style`. The same registration
helper is used for document and discovered shadow roots. Pending historical
records are still drained before password checks, and the sticky protection
remains. This removes the previous API request for old source `value`
attributes. The source and mock registration test establish the requested
options, not actual Chrome mutation payloads; final all-root audit evidence
must cover this changed observer setup.

**P1 found and repaired during this follow-up: excluded native-dialog text
was returned by the new modal read path.** `facts()` checked the top tab but
returned its cached dialog without checking the opener. An excluded iframe
already loaded before control could therefore supply modal text in an allowed
top tab. A Node VM probe against the actual background implementation returned:

```text
{"readReturnedDialog":{"id":"dialog","kind":"confirm","frame":2,"frame_url":"https://approval.test/","text":"EXCLUDED_DIALOG_SENTINEL","button":"OK"}}
```

This was mock evidence, not proof that the receiver fixture exercised the
specific pre-existing iframe/native-dialog sequence. The finding was sent to
the parent immediately. The repaired `facts()` validates the opener address
and requires an established frame before returning a modal. The native event
listener now checks the address before accessing `params.message`; an excluded
opener retains only `{frame_url, blocked:true}` and wakes pending input without
automatically answering the dialog. Thus later input results cannot expose a
cached excluded message through this event path either.

A second Node probe loaded the actual native event-listener registration into
the background test VM. Its excluded `params.message` getter threw if touched.
The corrected run exited 0 and printed:

```text
{"excludedMessageGetterReads":0,"heldInputWakes":1,"retained":{"frame_url":"https://approval.test/","blocked":true},"readRefused":true}
{"allowedNativeDialogReadable":true,"contentFramesRead":0}
```

The first attempt at that second probe passed its excluded assertions, then
failed in the probe's allowed-case setup with `TypeError: Cannot set properties
of undefined (setting 'getAllFrames')`. Initializing the mock `webNavigation`
object fixed the probe; no production change was needed for that error.

**Owner-excluded links: no new blocker found in the pre-dispatch change.**
The service now checks activated link destinations with its current owner
exclusion list before classification/preparation. The check covers click and
Enter/Space key suffixes; the existing extension click path also checks its
configured list. A plain Python probe using the `Operations` test fixture,
owner entry `approval.test` and destination `http://sub.approval.test./`, ran
click, Enter, Ctrl+Enter and Space. All four returned refusal with zero recorded
browser dispatches. This proves the service branch in the mock, not native key
delivery or the browser's network exclusion rules.

Commands run in this follow-up:

```sh
node --test control/chrome_tests/reader.test.mjs control/chrome_tests/background.test.mjs
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/chrome_tests python3 -m unittest test_engine.Operations.test_owner_excluded_link_is_refused_before_any_input -v
```

The combined Node command first printed 9 tests passed, 0 failed before the
modal regression was added. After its repair it printed 10 tests passed,
0 failed, 0 skipped. The focused Python command printed `Ran 1 test` and `OK`.
The additional heredoc probes used the existing `fixture()` via Node `fs`/`vm`
and Python `Operations.setUp()`/`tearDown()`; their outputs and limits are
recorded above. No implementation or test files were edited by this reviewer.

No remaining blocking defect was found in these three repaired paths within
this follow-up's scope. That is **not** a final SAFE verdict: the required
twice-passing final-head runner evidence and the broader acceptance obligations
still govern completion.
