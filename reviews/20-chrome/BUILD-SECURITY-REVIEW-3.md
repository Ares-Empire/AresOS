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

## Follow-up: approved Enter and the implicit submitter

Reviewed at HEAD `95ed8ac1baf97b0e41ed593fed4920de0883413b` with working-tree
changes. The parent reported a runner failure at `42620316119`: approved Enter
in a field was holding the browser's implicit submitter click. This reviewer
did not run a browser or independently certify that runner result. The reviewed
repair infers the default submitter by DOM tree order and form ownership,
binds its identity and effective form destination, passes those through private
extension messages, and gives its trusted click one activation pass after input.
The owner's default-task exemption remains outside this permission.

**P1 found: another submitter could consume the primary form allowance.**
Although the click exception matched the private implicit element,
`allowance()` compared only action, method, encoding and target. A handler for
the approved field's keydown could call `form.requestSubmit(otherButton)` with
the same destination and consume the primary allowance. Another submitter may
carry different successful button name/value data. The new regression tested
another button's click, but did not test its `requestSubmit` route.

A browser-free Node probe ran the actual guard using the existing page fixture:
it armed an approved field and implicit button, delivered the trusted mock
keydown, and called `requestSubmit` with the other button. It exited 0 with:

```text
{"wrongSubmitter":"e4","approvedSubmitter":"e3","arrivals":["event"],"reports":[]}
```

This is a simulated native submission, not HTTP evidence. The finding was sent
immediately to the parent. The primary and further event allowances need an
explicit submitter policy; the required native-submit loop exception should
remain separately bounded rather than silently granting another submitter.

**P1 found: empty overrides were not described as the browser uses them.**
`formFacts()` used truthiness for `formaction`, `formmethod` and `formenctype`.
Present-but-empty attributes therefore fell back to the base form values.
The browser instead resolves empty `formaction` to the document URL, and empty
or invalid method/encoding values to their defined defaults. See the
[HTML submission attributes and their IDL getters](https://html.spec.whatwg.org/multipage/form-control-infrastructure.html#form-submission-attributes).
This affects both the approval and the new allowance comparison, which use the
same reader; comparing two identically incorrect descriptions cannot catch it.

A Node probe extracted actual `formFacts()` and supplied a mock submitter with
present-empty attributes and the browser-defined native getter results. It
printed base action `https://fixture.test/bare`, method `post` and encoding
`multipart/form-data` in the binding, while the native overrides supplied
`https://fixture.test/current`, `get` and
`application/x-www-form-urlencoded`. No browser was used. Attribute presence
and native normalized getters, plus empty/invalid override fixtures, are
required to close this mismatch. This finding was sent to the parent.

**Additional gate concern:** the implicit-click condition used `mark.input`,
which capture sets for trusted `keydown`, `input` **or** `change`. It did not
establish the narrower stated condition of the approved target's keydown.
The parent was advised to retain a distinct private matching-keydown fact for
the implicit-click exception. Whether a page-triggered native editing command
can produce the relevant trusted event in the runner was not tested here;
that specific exploit must not be claimed as browser-proven.

The focused command run before repairs to these findings was:

```sh
node --test control/chrome_tests/page.test.mjs control/chrome_tests/reader.test.mjs
```

It printed 25 tests passed, 0 failed, 0 skipped. The two adverse probes above
show why that result alone did not establish the newly added permission.
Repair and final receiver evidence remain required; this follow-up does not
relax the owner's strict default-task case or issue a SAFE verdict.

### Implicit-submitter repair recheck

The parent repaired these findings in the working tree, and this reviewer
re-ran focused probes. `formFacts()` now first checks that the candidate is an
actual submit/image control belonging to this form, tests override attribute
presence, and reads the native normalized `formAction`, `formMethod`,
`formEnctype` and `formTarget` properties. The extracted-function probe now
returned the correct empty-override destination, GET method, URL-encoded
encoding and empty target.

The isolated guard now retains a separate matching-keydown fact, including the
native key and Ctrl/Cmd/Alt/Shift modifiers. Its implicit primary submission
requires that fact and the bound submitter. Node probes with modifier masks
0, 1, 2, 4, 8 and 15 each established: trusted input before keydown held;
mismatched modifiers held; another same-destination submitter held; the
matching key and submitter produced one mock arrival; a repeated submission
held. No browser input or receiver was used.

**A further P1 variant was found and repaired during recheck.** The first
repair conditioned further-event identity enforcement on the approved
submitter being non-null. Resuming `requestSubmit()` with no submitter could
therefore let its handler call `requestSubmit(otherButton)` through the further
allowance. The actual guard probe printed:

```text
{"approvedSubmitter":null,"actualSubmitter":"e2","arrivals":["event"],"reports":1}
```

After the parent removed that truthiness exemption, every non-null event
submitter must equal the bound one, including when the bound value is null.
The identical adverse probe then exited 0 with assertions for no arrival and
a new hold, printing:

```text
{"approvedSubmitter":null,"actualSubmitter":null,"arrivals":[],"reports":2}
```

The last recheck command was:

```sh
node --test control/chrome_tests/page.test.mjs control/chrome_tests/reader.test.mjs
```

It printed 27 tests passed, 0 failed, 0 skipped, including the null-submitter
regression, native normalized override getter regression and unchanged native
submission loop tests. The earlier recheck, before adding those two tests,
printed 25 passed. These are mocked DOM results. The reported implicit-path
defects are closed at the source/focused-test level; final real receiver runs
must still prove the added permission and override cases. No remaining blocker
was found within this repair recheck's scope, and no final SAFE verdict or
owner-default-task exemption is implied.

### Follow-up: form-name clobbering and capture exceptions

Reviewed the further working-tree repair at the same HEAD. The reader now
obtains `elements`, `action`, `method`, `enctype` and `target` through isolated
native `HTMLFormElement` getters and queries the form through the native
`Element` method. The guard catches inspection exceptions around capture,
cancels a cancellable event and stops propagation before attempting to report
a non-resumable activation. Label inspection in reporting has a fallback.

No relaxing bypass was found in this scoped review. Two additional
browser-free probes exercised the repair:

- A Node probe extracted the real reader helper and `formFacts()` functions.
  The mock form's page-owned `elements`, `action`, `method`, `enctype`, `target`
  and `querySelector` properties all threw on access; its native prototype
  getters returned separate values. The probe exited 0 with
  `pageOwnedPropertyReads: 0`, `nativeQueries: 1` and the expected native
  destination, method, encoding, target and fields.
- A Node guard probe modified the test fixture **in memory only** so event
  listeners swallowed exceptions, matching the browser behavior relevant to
  the original failure. With `reader.form()` and `reader.target()` throwing,
  `requestSubmit()` and a cancellable native click each produced zero mock
  arrivals and zero page-handler invocations, with a non-resumable stopped
  activation. A noncancellable native click also invoked no handler and was
  reported as `activation_unknown`, not as stopped; resume refused all three.
  The mock does not emulate a noncancellable click's navigation default, so
  the unknown classification remains necessary.

The second probe found a minor report inconsistency: the exception handler
initially omitted the `cancellable` argument, so an unknown noncancellable
step incorrectly carried `cancellable: true`. The parent passed the actual
event flag. The focused recheck then printed:

```text
{"kind":"activation_unknown","cancellable":false}
```

The reviewer also ran:

```sh
node --test control/chrome_tests/page.test.mjs control/chrome_tests/reader.test.mjs
```

It printed 28 tests passed, 0 failed, 0 skipped. Only this report was edited by
the reviewer. Native form getter behavior and the clobbered-form fixture still
need the final authorized runner evidence; these mock results do not certify
the whole Chrome stage or change the strict owner-input requirement.

### Design review: opaque MAIN-world event reconstruction

This is review of a **proposal**, not an implemented or verified repair. The
parent reported runner evidence that wrapped `dispatchEvent(MouseEvent)` and
retained-event replay reached neither handlers nor held steps, despite working
`.click()` wrappers. Native getter failure on an opaque cross-world Event is
a hypothesis to test; this reviewer did not reproduce it in Chrome. No new
executable tests were run for this design-only review.

The proposed fallback can preserve the security boundary if it discards an
opaque original completely and constructs a fresh, untrusted native event in
ISOLATED. A forged `keyup` hint must produce only an untrusted keyup; it must
never cause an opaque original click to be dispatched. The final native type
of whichever event will actually be dispatched must determine interception.
A successfully native-branded original must be classified from its native
type, not from MAIN's hint.

Required constraints sent to the parent:

- Read and validate each hint once into bounded primitive locals. Use a fixed
  constructor map and an explicit option allowlist; do not select a global
  constructor or copy arbitrary object properties from page data.
- Never copy or synthesize authority-bearing state: `isTrusted`, event phase,
  target/currentTarget, owner verdict, approval marks or allowances. Do not
  copy opaque `detail`, DOM nodes, `view`, data-transfer objects or other
  arbitrary native objects through this fallback.
- Evaluate all page-reachable lazy getters before the final target/type
  classification. Do not invoke another page getter/function between that
  classification and native dispatch: a malicious getter could otherwise
  change the target's asking semantics or the selected event. Exceptions,
  excessive values and unsupported reconstruction must add a hold/refusal.
- Check password protection before reading event data. For a protected
  target, do not invoke getters that can reveal input text, including
  `InputEvent.data` or transfer data. Filtering after extraction is too late.
- A fresh event must remain untrusted, so retained physical input replay can
  never restore the owner exemption. Test contradictory type hints, forged
  options, getter reentrancy, getters changing the target, and noncancellable
  asking clicks with real receiver logs.

Cloning has a compatibility consequence that must not be hidden: event identity,
the original object's `defaultPrevented`, and its dispatch-in-progress state
are not automatically preserved. In particular, a listener receiving a clone
can attempt to dispatch the original object again while the clone runs, where
the native original-object path would reject reentrancy. A private MAIN
per-original in-progress check may add a hold, but cannot grant a pass.
Cancellation return values and original-object state need explicit treatment;
do not claim full native Event semantics without evidence. Strict wrappers and
captured intrinsics are appropriate hardening, not authorization on their own.

The same opacity problem must not weaken `requestSubmit(submitter)`. First
attempt captured native form/type access on the actual candidate. If that
fails, a MAIN selector, id, index, `.form` claim or a missing submitter check
cannot establish identity. A native report dispatched on the actual submitter
can expose its real node through the isolated composed path, with its form
derived privately; however, that still must preserve the original receiver's
form identity and equality. Invalid
`requestSubmit.call(otherForm, submitter)` must not silently become a valid
submission on the submitter's form. If both identities cannot be established,
hold/refuse instead of guessing.

This assessment identifies conditions for a safe protocol, not approval of
an implementation. The actual patch and strict runner regressions still need
review. The parent's diagnosis of interop failure and any compatibility gains
remain unverified by this design-only follow-up; no SAFE verdict is issued.

### Opaque-event implementation recheck

The parent then implemented the fallback, and this reviewer read the actual
working-tree `page.js` and `guard.js`. The guarded original path first requires
native Event recognition and reads the native type; the opaque path creates a
fresh untrusted event from validated primitive options. The original opaque
object is not dispatched. The actual event type and current target are checked
after descriptor-data getters finish. Protected targets skip the data getter.
Neither arbitrary event detail nor DOM objects are copied as constructor
options. `requestSubmit` identity handling was not weakened; failure to unwrap
its supplied submitter remains a refusal/hold, with runner compatibility still
to be demonstrated.

Two issues in the first implementation were sent to the parent and repaired
during review:

- MAIN's reentrancy set originally looked up `WeakSet.has/add/delete` through
  mutable page prototypes. These methods are now captured and invoked using
  captured `Reflect.apply`.
- A single native getter per property let KeyboardEvent's modifier getters
  overwrite MouseEvent's. The getter table now retains native alternatives and
  tries their brand checks, without reading arbitrary Event expandos in Chrome.

A custom Node VM probe modeled opaque cross-world recognition by using a
separate isolated Event subclass while retaining the existing mock DOM
dispatch. In both baseline and page-patched-WeakSet cases, recursive use of the
original produced `handlers: 1, rejected: 1`. This is a model of the proposed
boundary behavior, not a real Chrome interoperability result.

The focused command was run twice during this implementation review:

```sh
node --test control/chrome_tests/page.test.mjs control/chrome_tests/reader.test.mjs
```

Both runs printed 34 tests passed, 0 failed, 0 skipped. Relevant passing cases
include contradictory opaque type hints, no trusted-owner forgery, descriptor
getters changing the target before classification, protected-target data getter
skipping, recursive event rejection and stale-finish nonce rejection. These
mock tests do not establish that Chrome exposes each lazy descriptor or native
Event reference in the way the implementation expects.

A final hardening concern was sent to the parent: MAIN still traversed its
captured getter arrays and field lists using page-mutable array iteration, and
added the per-original dispatch mark after descriptor extraction. Indexed
iteration plus marking before getter evaluation would close that remaining
prototype/reentrancy surface. No approved-send bypass was demonstrated through
that concern. Clone identity, cancellation and unsupported-event compatibility
remain the limitations described in the design review above.

No new confirmed unapproved-send defect was found in the implemented fallback
within this focused review. The actual runner must prove the opaque click and
retained-event cases, including their independent receiver counts. This is not
a final SAFE verdict or permission to relax the owner's strict default-task
case.

### Follow-up: durable private observations of held steps

Reviewed at HEAD `76d39fa29cb6ddf205e707a2354d7e42fcbcf992` with concurrent
working-tree changes. The new path reports held steps through isolated
extension messaging, authenticates the extension sender and private tab epoch,
queues observations across document loss, and commits an open service intent
without nested bridge I/O. The later polling/queued merge performs preparation
or warning resolution. This observation path does not grant an allowance,
resume a step or clear the in-flight mark. No new relaxing action path was
found in the source reviewed.

Four state/delivery issues were sent to the parent during this review:

1. **A valid late observation could be lost after control release.** The
   initial `observeStep()` accepted only currently controlled epochs. A
   document's unknown activation could trigger an excluded navigation and
   release before its private message was handled. A Node probe began
   `collectSteps`, removed the controlled epoch, then delivered its legitimate
   old observation; it printed
   `oldControlledObservationAccepted: false, committedNotifications: 0,
   collectedSteps: 0`. This models event ordering; it does not establish the
   frequency of that order in Chrome. Retained authenticated observation
   context must never authorize subsequent input.
2. **Modal opacity was treated as proof of document loss.** A dialog can open
   between collection and service processing. The native-modal read path then
   returns `frames: []`. `steps()` treated that as a changed document and
   committed the still-live held submission as done/dropped. A Python probe
   using `Operations` observed exactly that committed state and the reason
   `The stopped step document changed; no resumption is possible.` A modal
   instead requires an unresolved/open check until identity can be established.
3. **Polling bypassed the observation queue's bound.** `collectSteps()` added
   every polled entry to its result map, independently of the 512-step queue
   bound. The initial focused background run printed 13 passed, 1 failed: the
   newly added `combined queued and polled steps stay capped with one truthful
   overflow warning` assertion failed. The combined merge requires one bound
   and an explicit uncertainty warning for overflow.
4. **The daemon could strand complete notification lines in its decoder.**
   The selector's Chrome-peer branch initially processed one `Bridge.read()`
   result per socket-readiness event. A single recv can buffer more complete
   lines while emptying the kernel socket. A plain Python `socketpair` probe
   sent two JSON events and read the first through the actual Bridge; it
   printed `first: 1, kernelReadable: false, secondCompleteLineBuffered: true`.
   Already-buffered complete lines need processing without waiting for another
   readiness signal, so observations reach committed owner state promptly.

These findings concern missing or prematurely resolved owner-visible facts;
the probes did not demonstrate an unapproved submission. They remain relevant
to R1 and the rule that checks stay open until their result is committed.
The reviewer used only Node mocks and plain Python, including a local anonymous
socketpair. No browser, profile or real service was accessed. Repair recheck
and the final runner evidence remain required.

### Private-observation repair recheck

The four reported issues were repaired in the working tree and rechecked.
Retired tab epochs are retained for observations only, bounded to 15 minutes
and 32 records; action authorization still requires current control. Combined
polling and notification collection now returns at most 512 steps plus one
explicit unknown-overflow step. Collection retains queued entries until the
service acknowledges their committed results through the private
`ack_steps` command.

The service now leaves modal-blocked checks `started`, and later normal reads
can process retained steps after their initial bridge read has completed.
`event(held_step)` still only commits the observed intent and performs no
nested bridge request. A completed submission preparation records its
operation id so a failed acknowledgement does not reserve it again.

The daemon now drains complete decoder-buffered events in batches of 128 and
checks that buffer before serving later client reads. It no longer relies on
new kernel readiness to process already-received complete messages.

Commands run by this reviewer after these repairs:

```sh
node --test control/chrome_tests/background.test.mjs
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/chrome_tests python3 -m unittest test_bridge.ConnectionDelivery.test_daemon_drains_complete_buffered_events_without_waiting_for_socket_readiness -v
```

The background suite printed 16 passed, 0 failed, 0 skipped. Its passing cases
include retired-epoch observation without input authority, bounded expiration,
combined polling/notification overflow, and retention through a modal until
private acknowledgement. The focused Python socketpair test printed
`Ran 1 test` and `OK`; it processed 200 events as batches of 128 and 72.

An additional plain Python probe used the actual service methods with the
`Operations` fixture. It made every bridge call raise during the observation
callback, confirmed that modal opacity left the source `started`, forced a
transport error on the first acknowledgement after preparation committed, and
retried processing. It exited 0 and printed:

```text
{"eventNestedIO":false,"modalCheckStayed":"started","reservedBeforeAckRetry":1,"reservedAfterAckRetry":1}
```

The reported defects are closed at the source and focused-test level. No
additional relaxing path or confirmed owner-state defect was found in this
recheck. These checks do not establish durable delivery of an observation that
never reaches the service, or replace the existing pre-dispatch operation
record and unknown-outcome handling. Final runner evidence remains required;
there is no final SAFE verdict.

### Final data-only event protocol and lifecycle source recheck

The final MAIN dispatch descriptor contains a primitive event name, Boolean
flags, and lazy primitive data; it no longer passes an Event or submitter DOM
object. ISOLATED always constructs a fresh untrusted event and classifies its
actual native type. Password targets skip the event-data getter. Page getters
run before the final consequential-click decision; they cannot supply a trusted
event or a private allowance. Prior cancellation is copied and cancellation of
the fresh dispatch is returned to the caller. No new authority bypass was
found in this protocol source read.

For `requestSubmit(button)`, MAIN uses captured native receiver/form/type
getters to reject the wrong receiver or another form's submitter before the
report. The report is dispatched on the actual submitter and contains only
`kind` and `with_submitter`; ISOLATED derives the form and calls its captured
native `requestSubmit`, whose validation and guarded submit event remain in
force. The two new tests covering descriptor contents, wrong-form rejection,
fresh-event trust and cancellation were inspected, not rerun by this reviewer.

Control-stop wakes now produce an interrupted outcome; the post-effect
`assertControl` prevents reporting a released dispatch as successful. Stale
tab-update callbacks compare a fresh tab snapshot and the same control object;
stale detach callbacks probe the current attachment before releasing it.

One remaining source race was sent to the implementer: the awaited final arm
can finish after Stop releases control, and the following `tabs.update` still
activates the released tab before the later control assertion. Activation may
run focus/visibility handlers after its guard was cleared. Assert current
control immediately before calling `tabs.update`, not only afterward. This
finding concerns the newly added activation step; the primitive event protocol
does not grant that authority.

This was source-only review, with no browser execution or new test-pass claim.
The strict owner default-task gap and required receiver-run evidence remain;
this is not a final SAFE verdict.

### Flat payload getters, excluded form destinations and finish interruption

Reviewed the subsequent flat enumerable primitive payload getters. The bridge
still constructs a fresh untrusted event and checks the resulting native type;
raw getter fallback supplies data, not identity or permission. A source/mock
probe nevertheless found a password-exclusion race: the first payload getter
could mark the target protected, after the initial password check, and its later
`data` getter still ran. The actual page/guard source probe printed
`{"protectedAtDataRead":true,"payloadDataReads":1}`. Added the strict regression
`a descriptor getter protecting the target prevents every later payload read`.
It failed with `1 !== 0` before repair. The implementer's sticky protection
check before each payload getter closes this reproducer; the test now passes.

The known form-action exclusion gap was present in the reviewed source:
service preflight checked links but not submission actions, while GET searches
could bypass the guard without checking their destination. Existing network
rules block excluded main/subframe destinations in controlled tabs, so this
source finding alone does not prove a receiver arrival. A newly opened form
target also cannot be assumed covered by the old tab's rule. The repair checks
known form destinations in service preparation and twice in background input
preflight, and gives the isolated search predicate the private excluded-host
list. Added `GET search cannot bypass private excluded destinations or unsafe
URLs`, covering the exact excluded host, a subdomain with trailing dot, a
JavaScript URL and credentials. Both wrapped native submission paths remain
held for all four cases. The existing allowed GET-search/POST-override test
still passes. The mock now exposes URL and uses an absolute search action to
match the browser's normalized native form action.

Also found that `finishFrames` ignored an interrupted Stop wake and returned
`uncertain_finish:false`. Added `Stop during finish keeps the handler
completion uncertain`; it failed with `false !== true`. The repair returns
uncertainty on that wake while retaining observed holds. Service free and
approved execution both process returned steps and mark uncertain completion
unknown. The earlier tab-activation race is also closed in current source:
control is asserted before and after the awaited tab lookup and immediately
before any needed activation.

Final focused reviewer command:

```sh
node --test --test-name-pattern='Stop during finish|descriptor getter protecting|GET search' control/chrome_tests/page.test.mjs control/chrome_tests/background.test.mjs
```

It printed 4 passed, 0 failed, 0 skipped. These findings are closed at source
and focused mock-test level. Real sandbox-frame dispatch, excluded form target
receiver behavior, and the required final runner passes remain runner evidence;
no local browser was accessed and no final SAFE verdict is made.

### Sandbox donor realm: native form submission boundary (source assessment)

The sandbox fallback fixture obtains a native `dispatchEvent` from an iframe
with `sandbox="allow-same-origin"`. If that succeeds in the runner, the donor
realm may likewise expose native `HTMLFormElement.prototype.submit`. Calling
that function with a parent-page form would bypass MAIN's wrapper; native
submission has no submit event for ISOLATED capture to stop. The HTML algorithm
uses the form's node document for its sandbox check, not the donor function's
realm. This is a source-based hypothesis requiring a receiver fixture, not a
locally reproduced browser arrival. See the [HTML submission algorithm](https://html.spec.whatwg.org/multipage/form-control-infrastructure.html#form-submission-algorithm).

This path does not alter a private hold or use our page-reachable report
protocol to gain permission. It is deliberate wrapper bypass. The reviewed
`origin/main` section 6 explicitly limits its submission holding statement to
honest pages and separately accepts hostile page sends. That distinction must
remain explicit: it is not the earlier public arm/stop/resume defect. It also
does not justify weakening any existing zero-arrival test or claiming this
unmeasured route held.

The current registration already uses allFrames and matchOriginAsFallback.
Chromium's published [RequestExecuteScript implementation](https://chromium.googlesource.com/chromium/src/+/117d86bef4eb55198d344517b0f53d082868dba3/third_party/blink/renderer/core/frame/local_frame.cc)
selects the policy respecting disabled scripts for MAIN, and the policy allowing
execution despite disabled scripts for isolated worlds. This supports the
sandbox-injection concern; it is not proof for the pinned runner binary.
Changing frame-matching options alone is not an established repair, and an
isolated-world wrapper does not replace the page world's prototype. No
verified supported fix or impossibility result was established by this read.

Proposed strict runner fixture: a free Continue handler obtains that donor's
native submit function, records native identity, and calls it on an ordinary
parent POST form targeting an existing sink. Exercise both retained and removed
donor frames. Assert zero receiver arrivals before approval and zero submit
handler executions; a held native submission must resume exactly once. A
receiver arrival must remain a diagnostic failure and be reported as the
measured wrapper-bypass boundary, not quietly counted as stopped or passing.
No production changes or browser execution were made for this assessment.


### Parent closure of the final pre-activation race

**Read/run:** the input path now asserts control before reading selected-tab state and again immediately before the synchronous activation branch. It selects only an inactive controlled tab and marks that activation as a possible effect before calling Chrome. A later binding refusal cannot claim that no activation happened. The full browser-free Node suite passed64/64 after this closure; the reviewer’s preceding source finding is retained above. Actual container activation and interleaving evidence remains pending.
