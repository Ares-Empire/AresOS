# Part P — both dialog decisions implemented, acceptance continuation

The lead's 2026-11-10 about 17:00 decisions supersede the prior stopped checkpoint.
The earlier 154 Chrome workflow IDs include the completed, failed closing runs
42843419421 / 42843914061. No workflow started by another person was cancelled.

**Preexisting modal:** Page.enable waits at most five seconds before the owner
handoff. The pending target is discarded and the debugger detached. A fixed
message tells Claude to ask “Please answer the dialog yourself.” The existing
control record remains; read/take can reconnect after the owner answers and the
normal first-act reload remains required. An intentional detach cannot revoke
the retained control record. A Page domain that responded may finish slow guard
setup without a false timeout. Native-UI answering and attachment outside the
Claude group are out of scope. The unreachable asking path/test is retired.
The REPORT records Chrome 157 source lines 624/680/1792 and run 42840910762 as
the provenance of this decided handoff, replacing its PLAN-GAP.

**Outside-native dialog:** absence of the authenticated private begin/return
token forces a question, even when an adapter's original confirmation matches.
The service binds tab/control, dialog type/text and accept/dismiss/prompt text,
warns that the continuation is unguarded, and refuses trusted exemption.
Approval is consumed before one Page.handleJavaScriptDialog; failed responses
cannot replay. Existing in-flight protection is neither cleared nor weakened:
its completion is awaited and any held followup is collected. This can ask more,
never less. The normal 15 controlled-dialog cases remain mandatory.

**Local:** 214 Node tests pass; focused Python 48 OK; 85 removal mutations all
fail, with every baseline passing. The prior recovered full Python result is
188 OK in 292.209 s; the new full sweep is ongoing. The first prior-hold removal
mutation survived because the collector's unrelated timer masked early return.
The strengthened test asserts that collection starts only after the old hold
finishes; that mutation now fails. The bounded-wait regression uses a controlled
clock and verifies detach, same-record recovery and the retained reload flag.

**Next Linux cases:** three preexisting modal kinds, timed owner handoff, an
independent native getTargets snapshot proving detach, owner response and read
recovery with the same session, and the first-act reload; three borrowed native
kinds from a genuine ordinary donor realm, mandatory question, changed answer /
trusted refusal and receiver 0/1/1. The full named inventory includes both cases.
No missing case qualifies. Full P30 and later cases, whole Chrome twice in both
modes, and base/Mail/boundary twice remain required before acceptance.

No local browser/profile was started, read or touched. Only Part P files changed.
Ledger: 154 before the next push, expected 156 after, allowance approximately 175.


### Final acceptance followup in progress

P23 now collects a real bounded post-answer observation for a borrowed native
answer; its fixed policy notice is separate from page evidence. The regression
changes the address and notice in the native answer double and fails if the
pre-answer snapshot is returned.

P2/P1 also cover native alert/confirm/prompt from inherited blank/srcdoc editor
frames. Their CDP frame IDs join webNavigation IDs through the authenticated
private document; a missing or changed identity never admits inline dialog text.
The inherited effective address remains in the bound facts and enforces the
read-only host at preparation and final dispatch. Same-URL HTTP frames are
resolved by the same native identity. Six Linux cases require answer plus held
continuation and receiver 0/1/1; those results remain pending.

Local Node: 217 pass, zero failed/cancelled/skipped; focused questions: 15 OK
(total focused policy/questions/sites/unit 49); recovered full Python result:
188 OK in 565.656 s. All 88 removal mutations failed with passing baselines.
No browser ran locally. These additions will be batched with completed CI
feedback before the next push.

The current complete Python sweep passed: **189 OK, 232.606 s**, with
`PYTHONPATH=control:control/chrome_tests`. The initial command omitted that import
path and failed loading test_bridge; no test assertion or implementation changed
to correct the invocation.


### Completed 2d2c728e trial and batched correction

Runs 42849298252 / 42849536082 completed red. The PR's external/policy jobs each
record 53 passes in 56 executed named cases. Every review matrix passed,
including all 15 ordinary dialogs, the decided bounded owner handoff/recovery,
all three borrowed-native questions and frozen-wrapper Stop. Exact raw native
receiver rows and PASS lines are retained in records/review-fixes-2d2-dialog-decisions.json.
Full P30 and later inventory still did not run; this is not acceptance evidence.

Both native mismatch failures have one cause: Chrome reports a cross-site child
modal through the root Page domain, so its transport target is not the private
guard's target. The opener was authenticated correctly, but arming additionally
required the wrong target. Arming now selects the private document already
joined to the native opener; it still requires every current frame's guard and
the exact private return token. The unused transport-target map is retired.
A regression gives parent and child different targets and verifies that the
barrier belongs to the authenticated child and covers both. Its root-only
mutation fails. Gemini remained independently red; the next trial diagnosed reused context numbers.

The Linux harness also retries native-profile directory removal briefly while
killed container Chrome children finish exiting; no profile is accessed locally.
Current local Node: 218 pass; all 89 mutations rejected with passing baselines;
Python remains 189 OK (only JavaScript changed since that complete run).
Ledger: 156 Chrome IDs before this batch; expected 158 after its push.


### Completed 25263559 trial: native matrices pass; context lifetime corrected

Runs 42864982361 / 42865000405 completed red. The retained policy result executes
43 named cases, 39 passing. All review matrices pass, including the six blank /
srcdoc native cases; the complete GitHub mismatch matrix now also passes.
The Gemini failure is independent of the retired native target lookup.
Exact PASS lines, failed rows and the native context trace are retained in
records/review-fixes-252-context-reuse.json. P30 and later cases remain pending.

Chrome reused numeric context 8 after a renderer swap. A stale record belonging
to an old descendant survived the root-only context cleanup, so bootstrap
mistook the new context for an already-installed reader and resumed immediately.
The root's native Page.frameNavigated now retires all that target's old realms,
scripts, private records and failures. It also advances a context generation,
so a reused number cannot resurrect an overlapping startup's identity. Every
bootstrap command checks that identity before and after awaiting Chrome; an old
startup cannot evaluate in or resume a replacement document. A child navigation
preserves the parent's guard. Runtime.enable remains absent.

Local Node: 220 pass, zero failures/cancellations/skips. All 92 removal mutations
fail with passing baselines, including retirement, generation and overlap checks.
Python stays 189 OK (only JavaScript changed since that complete run).
Ledger: 158 before this batch; expected 160 after the push.
