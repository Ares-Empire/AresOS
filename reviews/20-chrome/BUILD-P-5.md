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


### Shared workflow repeats on de337c55

All eight completed green: base 42870172481 / 42874609495 (142 tests each), Mail
42870172385 / 42874707566 (142 base + 309 Mail plus all four sweep shards each),
boundary 42870172295 / 42874802464 (127 native and 127 broker attacks in each
seccomp mode, zero hostile connections), qualification 42870172545 / 42874901253
(47 Python + 220 Node each). records/review-fixes-de3-shared.json retains exact
artifact paths, one-based output lines, source and job conclusions.

The closing ordinary-dialog assertions now explicitly require a guarded opener,
an answer that already happened and a separate held submission approval. That
strengthening and the report will be included in closing-head revalidation.
The Chrome pair is still pending; no partial case list counts as acceptance.


### Completed de337c55 trial: 60 named passes, P30 scanner corrected

Runs 42870158864 / 42870172304 completed red. Three modes finish P30's real
browser operations and then the test scanner dereferences a valid null CDP
result; the push-external mode is still progressing through P30 when the
105-minute container cap ends it (exit 124). The retained policy matrix has
60 passes in 61 executed names, including the complete adapter mismatch and
Gemini cases that previously exposed stale contexts. Later cases did not run.
records/review-fixes-de3-p30.json retains exact lines, failure and cutoff times.

The protocol selector now handles null independently; full raw audit rows remain
in the fragment-safe password scan. Its regression retains both nulls and
forbidden Runtime events after them. Removing null safety fails the regression.
The corrected offline scan of the completed policy evidence covers 121,236 rows,
3 nulls, 21,752 incoming protocol events, zero forbidden Runtime value events,
and no password sentinel in reassembled browser ingress, tools or service data.
That is useful privacy evidence, not a passing full CI result.

The 77-case whole-suite container allowance becomes 155 minutes (job 165), also
in qualification's identical full-suite container step. The prior cap stopped a
progressing run one minute after its last passed exclusion case. Per-case
assertions, owner timing and operation deadlines are unchanged; nothing is
skipped. Runtime input hash remains
bfd84256f4e36c1a61f66e815b87e48b39fa4d4b4f6bebd3e446a7c7078705f3.

Local Node: 221 pass; 93 mutations rejected, all baselines passing. Local Python
remains 189 OK. Shared workflows already passed twice on de337c55. The closing
head will repeat the full set. Ledger: 160 before this batch, expected 162 after.


### Borrowed dialog inside native argument conversion: feature-preserving fix

A message/default object's string conversion can open a borrowed native dialog.
The old wrapper issued its private token before invoking the native method,
whose WebIDL conversion then ran this page callback. That inner dialog could
inherit the outer same-kind token. The new regression was first run against the
old code and failed: it observed one private begin at conversion, expected zero
(.work/p-borrowed-conversion-before.txt).

Only the message and prompt-default arguments are now converted before issuing
the private token, with the native string hint. Undefined defaults and unused
extra arguments retain native behavior; primitive Symbols reach native validation
before any token, and page conversion exceptions retain identity. Return values
and wrapper shapes remain covered. No argument value enters the private relay.
A removal mutation restores the early-authority bug and fails the regression.

The borrowed matrix expands from three to seven variants: all three direct
natives, all three message conversions, and prompt-default conversion. Each inner
borrowed dialog must ask unguarded; approving/repeating it leaves receiver zero
while the outer guarded dialog waits. Answering the outer dialog must then hold
the distinct submission for its own 0/1/1 approval. This exercises the approved
rule's requirement to ask more without losing the ordinary hold.

Local Node: 223 pass; all 94 mutations rejected with passing baselines; generated
and diff checks pass. Runtime hash becomes
289b0d3304f3347506730b319be295ad196d93af11c4c4d1d94f31111ca44203.
The new variants need Linux proof. The already-running 3f1af5b2 pair is being
allowed to complete so its late-case feedback can be batched before this push.
No extra workflow was started and no local browser/profile was accessed.


### Completed 3f1af5b2 trial and closing native/catalogue batch

Runs 42889458048 / 42889469858 completed red at the sole remaining named failure:
full catalogue history paging. The retained policy matrix executes all 77 names,
76 passing, including P30, native/core/adapter matrices, Stop/recovery, wrapper
compatibility and qualification/residual cases. Full Python after the browser
was not run. records/review-fixes-3f1-late-catalogue.json retains every PASS line,
failed row, raw-artifact hashes and the independent privacy scan: 135,669 audit
rows, eight nulls, 24,181 protocol events, 3,483 sensitive getter records, zero
forbidden Runtime value events and no sentinel ingress.

History reaches 732 of 877 items in 367 consecutive two-row snapshot requests;
no other catalogue request intervenes. The absolute five-minute lifetime expires
while the list is actively read. Valid cursor reads now refresh inactivity time
and LRU position; five idle minutes still expire the cursor. The two-record,
10,000-item and 8 MiB bounds remain. A virtual-clock regression demonstrates
active reading beyond five minutes without a second native query, then refusal
after idle expiry. Removing the refresh fails it. The browser case now also
requires the exact total and unique item IDs, with its two-row pages unchanged.

Native authority is now single-opening authority: claiming a private token for
one dialog prevents a later borrowed opening from reusing it while an end message
is delayed. Arming binds that claim to the exact dialog and rechecks the dialog
after the final native frame query. A private end pause retires even an unclaimed
(suppressed) call before resume; late asynchronous begin messages cannot revive
it. Private script IDs are mapped only in authenticated extension contexts, and
the fixed boundary query carries no page argument value. Old end/return queries
cannot resume a replacement startup or poison its control. These lifetime and
query-race regressions have individual removal mutations.

The borrowed browser matrix now has ten variants: three direct, four message /
prompt-default conversions and three changed-dialog variants. Owner dismissal
leaves the initial receiver at zero; a replacement makes the old approval fail,
then fresh approval sends once. Conversion variants still require a separate
held form after the outer guarded answer. These additions need their Linux run.

Local Node: **229 pass**, zero failed/cancelled/skipped; **102 removal mutations**
rejected, every baseline passing. Generated and diff checks pass. Runtime hash:
117dc34ebc93455ce47ca79d187fc5c7e5107ad130e6e5eb1e615a0c885e91c7.
Python remains the recovered 189 OK; no Python implementation changed. The old
shared twice-green source is retained explicitly as de337c55, not this new head.
The next push is expected to bring the Chrome ledger from 162 to 164.
