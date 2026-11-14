# 20, continue 2: no page-reachable control, the owner's input as decided, finish "Now"

The continuation run stopped on a confirmed unapproved submission: page code called the page script's public API
(`globalThis[Symbol.for('aresos.chrome.page.v1')]`: `stop`, `arm`, `resume`) and a form went to the receiver
without approval (`reviews/20-chrome/REPORT.md`, `BUILD-SECURITY-REVIEW-2.md`). That is a defect of this
implementation, and it is fixed, not a stop. `briefs/20-continue.md` stands, with the changes below; where they
differ, this brief wins.

**Never start, read or touch Chrome, Chromium or any browser profile on this Mac: every browser test runs only in
containers on GitHub's Linux runners through the control-chrome workflow; locally run only plain-Python and Node
tests that start no browser.**

## The stop rule, stated precisely

Stop only when a guarantee of section 6 **can't be met by any design on the fixtures**, after a real attempt and
with the reason it can't. A test that finds a bug, including one that sends unasked, twice or differently from the
approval, is a bug to fix: keep the test strict, fix the cause, continue. Never weaken a test to get green.

## 1. Nothing the page can reach may relax a hold

The rule: **anything page code can call, read, write, forge or intercept may only make the tool hold more, never
less.** Every step that relaxes (clearing or ending a hold window, granting a submission allowance, resuming a
stopped submission, the owner verdict, clearing the in-flight mark, confirming an element's identity) is decided and
carried out in the extension's isolated world or the service, from private state, never through a MAIN-world API,
global, symbol, DOM event, attribute or message that page code can reach.

- Remove the public MAIN-world control object. The MAIN script keeps only what must live in the page's world (the
  wrappers of `submit()`, `requestSubmit()`, `click()` and `dispatchEvent()`); with no private information, its
  default is to hold.
- Facts that may help (not prescriptions; choose and prove your design): the isolated world's own capture
  listeners, registered at `document_start` before any page script, see the page's events first and can cancel
  them for every world; the isolated world has the browser's own, unwrapped prototypes, so it can resume a stopped
  submission with the native `submit()` or `requestSubmit()` without any MAIN API; a signal from the isolated world
  to a MAIN wrapper is safe only in the direction where anything the page does to it adds a hold (for example the
  isolated world cancelling a synchronous report event means "hold").
- The element-identity bridge is a page-forgeable DOM event today (`BUILD-SECURITY-REVIEW-2.md`): an identity must
  not be accepted on the strength of anything the page can send.
- **Tests, strict, with the independent receiver's log:** keep the page-forgery regression of this run; add a
  hostile page that calls every function and reads every property reachable from the page script's world, forges
  every event, message and attribute the extension listens to or writes, and replaces prototypes before and after
  the page script runs. In each: zero arrivals before approval, exactly one after, none after a second attempt.

## 2. The owner's own input, as the owner decided

The owner answered (board #138, "Yes, ask in that rare case"), and section 6 on `origin/main` (now `7d54764e`) has
the paragraph **"His own input in a Claude tab"** and new cases in test group 2. Re-read both with `git show
origin/main:docs/design/CONTROL.md` and build exactly that, with the conditions of `briefs/20-continue.md` part 1.
The tests are section 6's, strict, with the receiver's log:
- his Enter 130 ms after Claude's click, in a task with no input of the extension's in flight: submits at once,
  without a question;
- his input during Claude's in-flight input: held, asks;
- Claude's own dispatched input never counts as his, also when the page forges any message, attribute or global it
  can reach;
- a submission his input starts after a delay inside the short limit: held, asks, **also when his same input first
  submitted at once without a question** (the exemption ends with that task);
- one he starts after the limit has passed: not held;
- Claude's click starting a delayed submit at 300 ms: held.

This case is now the design: **drop the JUDGMENT-CALL and the proposed section 6 wording** from the report.

If you can't establish with certainty that a submission belongs to his input's task without a page-reachable
relaxing path (the review notes there is no standard task identity), the submission is held: holding only asks
more. In that case record a **PLAN-GAP** with the evidence and the cases that hold, keep the strict test, and
continue with everything else; don't stop the build for it.

## 3. The rest

Everything else in `briefs/20-continue.md` stands: the interim reviews' open findings (`BUILD-REVIEW-2.md`,
`BUILD-SECURITY-REVIEW-2.md` and the remaining ones of `-1`), and all of part 4, "The rest of Now". Interim
reviews stay named `BUILD-*.md`.

**Runs:** 17 runs of `control-chrome.yml` are used of about 50. Push in batches. If it would pass 50, say so in the
report and stop.

## Rules for this run

As `briefs/20-continue.md`, "Rules for this run". Read the specification from `origin/main` with `git show`, as
before (run `git fetch origin main` first; section 6 is at `7d54764e` or later).
