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
