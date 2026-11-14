# Independent interim security review — CHANGES NEEDED

Date: 2026-11-09. Scope: continuation brief part 1, `page.js`, `reader.js`,
`background.js`, and the existing owner-input fixture. This is a delegated,
interim source review with a browser-free Node probe, not a completed security
review or a SAFE assessment. The worktree was changing concurrently; its HEAD
when this report was written was `414c672968b921b684484d52d9727b1bde35c0cd`.
The probe used the then-current working files, not a clean checkout of that
commit. No browser, browser profile, real site, or real account was accessed.
The reviewer changed only this report.

## Confirmed in source and Node: public guard API permits unapproved submission

**P1.** `page.js` publishes `globalThis[Symbol.for('aresos.chrome.page.v1')]`.
Its `arm`, `stop`, and `resume` methods have no caller authentication.
`background.js` calls that same page-visible object through `main()`.

- `stop` accepts an invented epoch and clears the hold deadline anyway.
- `arm` accepts an invented operation and creates a submission allowance.
- `resume` accepts an invented operation and consumes a held submission.
  The held ID is exposed in the page's `aresos-page-step` event.
- The element identity bridge is also a page-forgeable DOM event, so possession
  of an identity string does not authenticate the selected element.

These are authorization bypasses, separate from the owner-input false hold.
They need no trusted physical event or disputed browser-task attribution.

The exact browser-free command run from the repository root was:

```sh
node --input-type=module <<'NODE'
import fs from 'node:fs';
import vm from 'node:vm';
const source=fs.readFileSync('control/chrome_tests/page.test.mjs','utf8');
const fixture=Function('fs','vm',source.slice(source.indexOf('function fixture()'),source.indexOf("\ntest('"))+'\nreturn fixture;')(fs,vm);
for (const attack of ['baseline','stop','arm','resume']) {
  const f=fixture(),form=new f.HTMLFormElement();
  f.arm(form,form,null);
  if(attack==='stop')f.api.stop('page-guessed-epoch');
  if(attack==='arm')f.api.arm({words:['send','delete'],holdMs:500},'target','form','page-invented-approval','page-invented-epoch',true);
  form.submit();
  if(attack==='resume')f.api.resume(f.reports[0].id,'page-invented-approval');
  console.log(JSON.stringify({attack,receiverArrivals:f.arrivals.length,heldReports:f.reports.length}));
}
NODE
```

It exited 0 and printed:

```text
{"attack":"baseline","receiverArrivals":0,"heldReports":1}
{"attack":"stop","receiverArrivals":1,"heldReports":0}
{"attack":"arm","receiverArrivals":1,"heldReports":0}
{"attack":"resume","receiverArrivals":1,"heldReports":1}
```

The fixture executes actual `page.js` in Node's VM with mock DOM classes.
`receiverArrivals` here counts the fixture's native submission array. It is
**not** an independent HTTP receiver log and establishes no Chrome event
ordering, network delivery, or browser acceptance result. The primary agent
is adding a strict receiver-backed page-forgery case in the Linux container;
that pending result must be recorded separately before deciding the brief's
stop outcome. This report does not claim that test has run or passed.

## Owner attribution: architectural limits reviewed, full solution unproven

Part 1 permits an owner exemption only within the same browser task as trusted
input received while no extension dispatch was in flight. In-flight coverage
must begin before dispatch and end only after page handling finishes. The
mark and verdict must remain private to isolated-world/extension messaging;
page-visible events, attributes, or globals cannot carry their authority.
Unclear cases must hold.

The required strict cases remain: owner Enter at 130 ms gives one arrival;
Claude's 300 ms delayed submit gives zero before approval; owner input during
dispatch holds; accessible page forgeries hold; and delayed owner work inside
the limit holds. The last case requires the brief's JUDGMENT-CALL about the
owner-exemption wording. None of these cases was browser-tested by this review.

No suitable current-browser-task identity was found in the reviewed standard
interfaces. This is **not an impossibility theorem**. A timer or MessageChannel
cleanup is not proof of task identity: another task can execute before the
cleanup. A microtask cleanup can run between native event listeners and clear
too early, producing false holds. These concerns follow from the
[HTML event loop and callback processing model](https://html.spec.whatwg.org/multipage/webappapis.html#event-loops).
The reviewed [Scheduling API](https://wicg.github.io/scheduling-apis/) does not
provide the needed task-identity primitive; priority or a shared TaskSignal
is not a unique browser task.

Retaining a trusted input event and checking its native `eventPhase` may prove
a narrower synchronous event-dispatch relationship. It does not cover every
native default action: the
[DOM dispatch algorithm](https://dom.spec.whatwg.org/#concept-event-dispatch)
resets the phase before activation behavior. It therefore cannot, without
additional evidence, be claimed to fix the existing native Enter regression.

MAIN code and isolated code have separate variables, and MAIN code cannot
directly use the isolated extension's private state. The reviewed documented
messaging interfaces supply no synchronous private request/reply primitive
that a MAIN form wrapper can use while preserving the original call stack.
[Chrome's content-script documentation](https://developer.chrome.com/docs/extensions/develop/concepts/content-scripts#work_in_isolated_worlds)
describes that isolation. An authenticated MAIN control API would address the
confirmed forgery defect; it would not by itself demonstrate compliance with
the brief's isolated-only owner-verdict requirement.

## Hardening obligations and safe next steps

1. Authenticate every state-changing guard operation, including `stop`, `arm`,
   and `resume`, before any effect. A candidate is an entry installed at
   `document_start`, nonwritable and nonconfigurable, with frozen callable
   methods and a high-entropy primitive capability kept in a lexical closure.
   This is a candidate design, not a reviewed implementation. Competing or
   failed initialization must make extension dispatch refuse, not authorize
   a page-selected capability.
2. Protect capability delivery as carefully as storage. MAIN globals and
   intrinsics may be monkeypatched by the page. The current `Symbol.for`
   lookup and argument spread are unsuitable for transmitting a secret:
   symbol lookup, replacement entry points, or an altered array iterator can
   intercept the call. Use an established nonreplaceable entry and direct
   scalar arguments, with necessary native operations captured before page
   code. Validate bootstrap and caller assumptions in adversarial tests.
3. Keep document/frame/control-generation binding and operation consumption
   enforced independently of possession of the capability. Reject forged
   element identities, stale documents, and repeated approval use. Do not
   promote data received from DOM events into authority.
4. Keep dispatch marking conservative. Require private acknowledgement before
   sending input; ambiguous completion, navigation, or lost acknowledgement
   must not clear the mark early. CDP input-command acknowledgement alone
   needs evidence that it covers the relevant page handling boundary.
5. Preserve the strict owner regression and all receiver assertions. Do not
   replace exact same-task attribution with a grace period, user-activation
   lifetime, or timeout. Where proof is absent, keep the hold and record the
   unfinished owner behavior rather than claiming the stage complete.
6. Add browser receiver cases for public `stop`/`arm`/`resume`, forged identity
   events, wrong capabilities, bootstrap takeover, entry replacement, and
   intrinsic monkeypatching. Run only through the authorized Linux-container
   workflow. Node success is not replacement evidence for those cases.

The next decisive evidence is the strict real-receiver page-forgery test.
Full Now coverage, a final security assessment, and a successful owner-task
architecture remain outside what this interim review has established.
