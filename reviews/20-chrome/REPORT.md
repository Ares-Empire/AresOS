# Post-18d integration — in progress

**Order:** `20-post-18d.md` and addenda b–e govern this run. The base-URL class is
first; late-reader credential protection and the owner's board #210 asking tool
follow, then the main merge, slim generator, precedence and latency work.
No local browser, browser profile or container has been accessed. All browser
probes run through `control-chrome.yml` in GitHub Linux containers.

**Done so far:** HTML anchor/area addresses use saved native resolved getters;
SVG href/xlink destinations use the native effective base URI. Form action and
submitter overrides retain native resolution. Effective browsing targets include
the live base target and are bound in both the service and extension. Destination
and form-owner changes retire the old operation and prepare a fresh question,
also when the final extension check catches the change. A held submission keeps
its original resume kind. Questions show absolute destinations and targets.

**Tests added:** 60 receiver sequences cover each URL source, base/attribute/target
mutations and form-owner changes, in top, blank and srcdoc documents. Each requires
zero arrivals through a stale approval and exactly one after the fresh question,
including replay. The independent auditor rejects missing or altered evidence.
Local reader, service, final-dispatch and removal probes accompany these cases.
Browser acceptance on this source is pending. Local commands/results are retained
in [base-local.json](records/post18d/base-local.json): **327 Node tests**, **57 focused
Python tests**, **238 removal mutations rejected with every baseline passing**.
`python3 control/generate.py --check` prints `Generated artifacts match definitions`;
`git diff --check` prints nothing. The expanded final full suites remain pending.

**Late-reader work (local):** the production-code before probe confirms that a
credential-labelled text field was returned without history
([receipt](records/post18d/revealed-code-before.json)). Previously the reader
checked native password type, password/one-time autocomplete, computed masking
and sticky history. It now additionally excludes credential names in `name`,
`id`, `autocomplete`, `aria-label`, associated labels and `placeholder`, in English
and German, before value or filled-state access. Exclusion stays sticky.

A private document-start marker distinguishes watched from late readers. Late
text/tel/number/unknown inputs show filled/empty through native constraint state on an inert imported control; choices,
formatted inputs, textareas and editable areas remain readable. Normal reads
never inherit a previous read approval. The new preparation lists only labels
(including a stable ordinal for unlabelled fields); `chrome_read_typed_fields`
is an explicitly asking read. Exact engine approvals and extension-local list
checks allow one response only. Approved values are transient and never stored
in replayable operation stages. Changed lists re-ask. The tool declarations are
ready for the slim-generator merge; app-wide instructions move in that step.

**JUDGMENT-CALL:** checking a late single-line field against its default would
extract unapproved text. The first-input reload check conservatively reports
possible unsaved typing for those fields, without reading values. This preserves
the page until the existing explicit reload acknowledgement. Replacing that
warning with an equality check would violate the owner's ask-first decision;
a future browser-native dirty-state signal could avoid the warning. Tab-group
handling is unchanged.

**Local verification:** **340 Node tests pass**, **77 focused Python tests pass**,
and **268 removal mutations are rejected with every baseline passing**. Tests
cover every credential signal and mask, watched/late input types, preserved
choices/textareas/editors, approval, denial, replay, unlabelled descriptions and
field-list changes. Linux late-reader and one-call-read cases are added to the
required inventory; their browser evidence and the slim-generator artifacts
are still pending. `KNOWN-LIMITS.md` remains current.

**Browser correction:** combined probe `43455378594` (**236** total) passed
the 60 destination cases in both installs, then correctly failed a filled-state
assertion: Chrome does not provide the assumed input `textLength` property.
The fix imports the native control into an inert document and checks only its
required/missing constraint state; it never extracts a value, alters the live
field, runs custom-element code or collects protected credentials. Hidden fields
in a late document disclose presence only. Strict filled/empty assertions stay.
Replacement probe **43458099291** (**237** total) passes both installation modes,
including credentials, preserved input types, approval/denial/replay and list-change
re-asking. Final acceptance remains pending.

**Main/slim integration (in progress):** `origin/main` is merged into this branch.
Mail's action scopes, contexts, recovery semantics and slim policy are retained.
Chrome keeps the native daemon socket (its sole browser channel), hash-verified
committed-journal reads (current warnings when working SQLite fails), live owner
projections and the service network configuration (Mail and qualification HTTPS).
The network lines and their comment are byte-for-byte equal to `8b7e799c`.
19b on main ends at stage 2 and ships no generic replacement for Chrome's
independent committed projection, so that projection remains rather than claiming
a migration to an absent shared reader.

Chrome is discovered through `ACTIONS`; normal user-scope MCP installation and
asking rules are generated. The trusted send is explicitly marked and implements
`require_trusted_send(verb, op)` using the current owner entry. `SHARED` is lifted
unchanged into `instructions_for('chrome')`, with the clipboard sentence and the
owner's typed-field instruction there once. Descriptions keep their own purpose.
An explicit `asking_read` declaration extends the generator to cover the new read
without pretending it sends. Generated managed-MCP is removed, and all artifacts
are regenerated. Group 12 and final merged acceptance are still pending.

**Group 12 / CI measurement work (awaiting Linux evidence):** the native precedence
harness now installs Chrome at user scope and checks its complete instructions and
tools in actual CLI requests. Both permission modes deny managed submit and typed
reads despite user allows. Positive controls remove those asks; trusted submit
reaches the independent receiver only under its current matching owner entry,
using `Chrome.require_trusted_send`/`Chrome.trusted`. Missing, revoked and other-account
entries refuse. The qualification verdict derives from those receipts, not a constant.

The full workflow partitions the long browser modules, four word slices and four
Python file shards, within one workflow run. Aggregation requires every named case,
each word cell exactly once, every Python module and native group 12, then repeats
the independent receiver/password audit. Stable/beta qualification uses the same
partition per build/channel/repetition. The 350-minute stopgap is removed: browser
containers are limited to 120 minutes in 130-minute jobs; other jobs are shorter.
The original push and pull_request triggers remain unchanged.

**PLAN-GAP:** the current versioned word list has 37 words, hence **999** cells
(37 × 9 labels × 3 keys), rather than the historical 972 mentioned in the latency
brief. All current cells stay required. A separate four-job latency matrix compares
current and `ab7aba92`, plain versus privacy-instrumented, on one exact Chrome
package. It measures 20 calls of each of six types, service/bridge time and browser
stages (including the fixed 525 ms post-input wait). Historical absent stages stay
absent. No owner think time is included. Medians, p95, proposed owner targets and
the regression check await those measurements; **not ready** until that is done.

**Verified locally after the merge:** full plain-Python Chrome discovery passed
**234 tests in 672.944 s, OK**; Node plus artifact-stream tests passed **350 tests**;
**268 removal probes** rejected their mutation with each baseline passing. Shared
base CI, native CLI and all final workflow repetitions remain pending. The first
manual full Chrome dispatch brings the ledger to **238**.

**Fresh package review:** [BUILD-POST18D-REVIEW-1.md](BUILD-POST18D-REVIEW-1.md)
found two FIXes on `cdd1cbcb`: ARIA-referenced password labels were omitted from
credential exclusion, and qualification combine used an older test inventory
than its shards. Both are fixed: referenced labels use the same value-free
traversal (including multi-part labels), and combine copies the identical driver.
A production-reader removal probe and an older-runtime/current-driver merger
regression cover the fixes. The independent [security review](BUILD-POST18D-SECURITY-1.md) also found split associated labels bypassing the credential check. Both referenced and associated labels now combine their value-free text before classification. Watched, late and approved reads are covered. **347 Node tests pass**, **15 focused Python tests pass**, and **270 removal probes reject their mutation, with every baseline passing**. Scoped re-checks are pending. The first full sharded/latency run is `43462608845` (**238** total); its
result will not be final-head acceptance because of these fixes.

**Scoped reviews:** [package](BUILD-POST18D-RECHECK-1.md) and
[security](BUILD-POST18D-SECURITY-RECHECK-1.md) both return **SAFE** on
`6e79f1f5`, with independent removal probes. This closes their reported fixes,
not the still-pending full CI and latency work.

**First sharded run — failed, retained:** `43462608845` at `cdd1cbcb` passes
all four word slices in both installs, adapters and round-3 slices. The actual
native CLI [group-12 receipt](records/post18d/native-precedence-43462608845.json)
passes all ten normal/skip and owner-entry cases. Python shards exposed an
unguarded launcher re-entering tests under multiprocessing spawn; the main guard
is fixed and an actual subprocess/worker regression passes. Latency jobs failed
before browser startup because the Dockerfile path referred outside the tar
context; that path is fixed. No measurement was produced or invented.

Core, review and popup slices found the expected new conservative reload warning
on unread single-line fields. Their original clean-reload assertions remain:
clean fixtures use unchanged readable textareas. Additional unchanged single-line
fixtures require preservation, explicit acknowledgement, one reload and stale old
references. Dirty/media, receiver, window/opener and replay assertions remain.
The aggregate correctly refused incomplete shards. Replacement dispatch brings
the count to **239**; no final acceptance is claimed.

**Audit driver:** the raw native-getter recorder also covers the new late-reader
pages, before any filtering, so the final independent audit checks credential
sentinel absence at ingress as well as in results. Its existing raw-value
regression now exercises both fixture routes. The qualification archive uses
the same corrected Dockerfile path as latency; local tar inspection confirms
both paths exist within their context. The independent report no longer emits
an invented zero Python duration for file shards; it records their actual counts.

**Complete local file shards:** the corrected launcher passes **237 tests**
across all **21** test modules, each module appearing exactly once. Shard times
are 14.008 / 512.299 / 0.724 / 192.410 seconds; the fault sweeps retain all scenarios.
[Commands, inventory and results](records/post18d/local-complete.json) and the four
raw outputs are retained. No local browser or container was used. Final-source
verification will follow any measured performance change. The current installed
runtime digest is `1ed9248c7136763a545f5f9a79a9da47fd597444c57e37aaa3e21ce6f1655df0`.

**Destination follow-up probe:** SVG exposes an animated destination separately
from its underlying href attribute. Two additional Linux cases change that
native animated destination while a question waits, without changing the source
attribute. This checks whether the current resolver follows the actual action.
The probe is intentionally run before any production change; a failure will be
fixed before further latency work. It brings the ledger to **240**. Existing
60 base/attribute/owner/target sequences remain required.

**SVG animated destination FIX:** focused run `43469631725` (**240**) confirms
an unapproved destination in both installs. An SVG animation changed the native
href while leaving its underlying attribute unchanged; approval for `/first/receive`
reached `/second/receive`. The [raw before receipt](records/post18d/svg-animation-before.json)
retains the original question, done response, independent GET arrival and receiver
hash. This is a FIX, not an accepted last-instant race: the changed destination
was already present before revalidation.

The resolver now uses captured native `SVGAElement.href` / `SVGAnimatedString.animVal`
and the native effective base URI. The browsing target uses its corresponding
native animated value too. Animated links remain visible without a base attribute;
page shadow properties cannot replace the captured getters. There are **64**
destination sequences now: the original 60 plus animated href/xlink and targets.
**355 Node/artifact tests pass** and **273 removal probes** reject their mutation
with all baselines passing. The replacement safety probe brings the count to
**241**. Linux evidence and scoped re-checks are pending; latency changes wait.

**SVG replacement:** `43471454320` (**241**) passes all 64 destination cases
and the late-reader/asking-read checks in both installs, with raw getter ingress
recording active. The scoped package re-check is SAFE on `5630a8a5` (62 exact-source
reader/auditor tests; three independent removal mutations rejected). The security
re-check confirms the reader change and requests a directly related native-default
probe before class closure: removing base href attributes may leave animated
navigation authority on a non-cancellable activation. The next probe uses only
borrowed dispatch, including `_blank`, and requires zero arrivals/no new context
before fresh approval. It brings the count to **242**.

The same review noticed that SVG's empty native target follows the controlled top
tab despite an HTML base target. The resolver now reports `_self` for that native
case. Named-frame SVG fixtures carry their explicit target, and two additional
empty-target cases check actual top/frame context via receiver-page observations
and native tab identity. All original 60 sequences remain, with **66** total.
The final independent destination audit now requires that context evidence too.
No tab-group behavior changes.

**Probe launcher correction:** `43472757698` (**242**) was cancelled by this
builder before browser evidence after the local exact-inventory regression exposed
a missing new helper in its file inventory. The assertion remains unchanged;
the helper is now included. The complete suite passes **356 Node/artifact tests**,
zero failures/skips. Replacement dispatch brings the count to **243**. The
cancelled run is not acceptance evidence.

**Animated native-default FIX:** `43472898643` (**243**) passes all **66**
absolute destination/context sequences, then exposes an unasked `_blank` arrival
in both installs. The [before receipt](records/post18d/svg-native-before.json)
shows an ordinary Continue click, a claimed stopped non-cancellable SVG activation,
and the independent GET before any question. [Context evidence](records/post18d/svg-contexts-before-default-fix.json)
confirms both native SVG `_self` cases and all named-frame destinations.

`guard.js` now temporarily disables only native SVG animations targeting the
held link, including external animations. It changes their animated property
names without moving/adopting elements or invoking custom-element disconnection
callbacks, samples the same SVG time, strips the href authorities, and restores
unchanged properties on the next task. Repeated activation rechecks authority
if the page restores it in the same task; stale restoration tasks cannot undo a
new hold. The existing form/submitter paths retain their disabled/fenced defaults.

**Verified locally:** **360 Node/artifact tests pass**; **278 removal probes**
reject their mutation with every baseline passing. The replacement Linux probe
covers href, xlink, external animations, animated targets, both href authorities
and same-task reactivation through self/frame/new-tab routes (**18** cases).
The original round-3 native defaults remain, with **125** receiver sequences
in its expanded independent audit. This dispatch brings the count to **244**.
The security scoped re-check and Linux result remain pending.

**JUDGMENT-CALL:** pausing an animated link's affected properties for one task is
the reversible cost of stopping a non-cancellable programmatic activation. Normal
owner input and unrelated animations remain unchanged. Restoring a property the
page changed while held is avoided. Removing this protection would restore the
measured unasked new-tab default. No new DevTools method or tab-group change.

**Scoped SVG follow-up:** the [package re-check](BUILD-POST18D-SVG-REVIEW-2.md)
is SAFE on `aaf3d4b1`; the [security re-check](BUILD-POST18D-SVG-SECURITY-2.md)
found two further FIXes in animation cleanup. A form's named control could shadow
querySelectorAll and abort midway; a retargeted/detached animation could lose its
restoration record on reentry. Saved native Document/DocumentFragment/Element
queries now collect the whole batch before mutation. Refreshing a hold retains
the union of outstanding restoration records. Regressions exercise the real
private relay with clobbering, retargeting and detachment.

**363 Node/artifact tests pass**; **281 removal probes** reject their mutation
with passing baselines. The expanded Linux probe covers **27** animated-default
cases plus all **66** absolute destination/context cases. Round-3's unchanged
original cases remain alongside the added cases (**134** exact receiver sequences).
Replacement dispatch brings the count to **245**. These fixes still need their
scoped re-check and browser result before addendum -f begins.

**Scoped SVG fixes closed locally:** [package](BUILD-POST18D-SVG-RECHECK-3.md)
and [security](BUILD-POST18D-SVG-SECURITY-RECHECK-3.md) both return SAFE on
`c78178dd`. The earlier Linux replacement `43475723438` (**244**) passes all 66
destination/context cases, late readers and its 18 animated native defaults in
both installs. The current 27-case replacement remains pending.

**Intermediate full green:** [43466571812](https://github.com/Ares-Empire/AresOS/actions/runs/43466571812)
at `a108d517` passes all 95 named suites and all 999 word cells in both installs,
237 Python tests, 347 Node tests, native group 12 and both independent audits.
The audit matches 1,445 page and 139 adapter 0/1/1 sequences to independent raw
arrivals. [Job timings](records/post18d/full-43466571812-jobs.json) show the longest
job at **30m46s**, well below the 120-minute container target. The raw intermediate
audit's Python `seconds:0` was a placeholder, removed in the current auditor;
it is not a measured duration. These are intermediate results, superseded for
acceptance by the SVG fixes and new addendum -f.

**Base-URL class complete:** [43477146168](https://github.com/Ares-Empire/AresOS/actions/runs/43477146168)
(**245**, `c78178dd`) passes both install modes: all **66** absolute destination
and native context sequences, **27** animated native-default cases, credentials
and asking-read checks. Both scoped reviewers are SAFE. The `_self` and named
frame checks use receiver-page context observations plus native tab identities.

**Addendum -f built, Linux verification pending:** all text-capable inputs,
including search/email/url, and all textareas in unwatched documents show only
filled/empty. Credential-like fields remain excluded before status/value access.
A shared scope predicate also controls the asking manifest and reload warning;
editable areas remain readable and their accepted board-216 limit is stated in
`KNOWN-LIMITS.md`.

Preparations now collect metadata only, even from watched frames. The service
binds its native-connection identity, the tab/control, native frame documents,
private documents, reader instances, exact element IDs and shown labels. The
engine verifies the supplied question/description; one approval produces one
transient response. Replacement with the same label, duplicates/unlabelled
fields, frame/reader/connection changes, credential eligibility, alteration and
replay have regressions. A fresh connection to the same browser session receives
a new private identity.

Recognised form submissions holding unknown-history content refuse before
preparation and at both revalidation/native boundaries, with “send it yourself,
or let Claude reload the tab first”. An approved read never clears the withheld
state. The Linux fixtures cover a late closed-shadow form and a value change
while the asking read waits. A separate service regression introduces withheld
content while a submission approval waits and requires refusal before input.
Unchanged readable choices retain the clean-reload fixture; typed text/textarea
fixtures preserve content until the explicit acknowledgement. No assertion was
relaxed. Tab-group handling is unchanged.

**Local -f verification:** [exact commands/results](records/post18d/f-local.json):
**369 Node/artifact tests pass**, **79 focused Python tests pass**, and **302
removal probes** reject their mutation with every baseline passing. Generated
artifacts match. The native-value recorder covers the new parent/child/form
routes. The next Linux safety dispatch brings the count to **246**. Main's
PR #43/#47 integration, latency limits and final workflow repetitions follow.

**Main refresh for -f:** merged fetched `origin/main` at `f89d0237`, including
PR #43's native interactive driver/17 cases and tmux dependency, both flaky-test
fixes, the second service-unit pin test, PR #42's image-test brief and PR #47's
hosted namespace tests. The only conflict was comment wording in hostile.py;
main's wording is retained and its executable code was already identical.
Chrome's precedence-only entry remains, alongside the main interactive workflow.
Both unit pin tests remain and the complete service unit is still byte-identical
to `8b7e799c`. Generated artifacts match and all merged Python sources parse.
Forbidden-area changes in this commit come only from the authorised main merge.
Full integration CI follows; no local container or browser was run.

**Runs:** opening count **233** distinct `control-chrome.yml` runs (lead's count).
Destination-only dispatch `43451063290` used **234** and failed at the first
blank-frame base case. The new fixture had duplicate blank-frame addresses, so
pointer routing correctly refused; an inherited about:blank base is also a
creator snapshot. The correction gives receiver sinks distinct addresses and
changes the inline document’s effective base itself while keeping its initial
inherited base. Zero-arrival assertions remain strict. Replacement dispatch **43453115578** passed both external and policy installs;
the ledger is **235**. It is focused destination evidence, not full acceptance. Its explicit probe output
is not full acceptance. Intermediate and report-only pushes use `[skip ci]`;
a normal final code push starts **two runs** through push and pull_request.
The approximate limit is **260**; report here before passing it. Shards within a
workflow run do not create extra workflow runs. Existing round-3 runs
`43437786144` and `43437906776` on `63c81414` are watched with one blocking shell
call each; their outcome is still pending and will be handled by section 0.

**Not verified / open:** the destination browser probe, late-reader work, main
merge, generator, group 12, latency targets and the final two full workflow sets.
PR #27 remains draft. No PR/main merge or force push is authorized. The fixed
service network lines will remain byte-for-byte equal to `8b7e799c`.

---

# Recheck fixes 3 / 3b — verification in progress

**Read:** briefs `20-recheck-fixes-3.md` and `-3b.md` govern this round on `pkg/20-chrome`.
Fetched `origin/main` and read its `AGENTS.md` and `briefs/20-chrome.md` with `git show`;
also read SECURITY-RECHECK-3, the prior report/known limits and briefs 2/2b/2c.
The first code push included all three classes. Additional local whitespace/visibility probes and the Linux SVG/trailing-newline cases required further corrections. PR [#27](https://github.com/Ares-Empire/AresOS/pull/27)
stays draft and unmerged; its existing conflict with main is not resolved in this brief.
Installed runtime hash: `66cdb07105b163cecf8e82c1c6293a3459fda2da556533552305dd5e41e737c0`.
Linux acceptance on the new source is pending; historical green sections below do not establish it.

## Done (read)

- `page.js`: wrapped listener registration installs private capture on the receiver **before** its handler,
  including detached receivers. A saved native brands the receiver even if page code replaces global `Node`.
  Root/insertion/dispatch hooks remain in place. The generated unit and production-code probe cover all
  **128** combinations: 16 wrapped/native masks × open/closed × composed/non-composed × listener before/after
  insertion. All non-native rows hold; the four all-native non-composed rows alone run unheld. Linux fixtures
  add all **32** single-wrapped-step rows plus eight all-wrapped rows, and **16** iframe rows covering each single
  wrapped step in both insertion orders and root modes, plus **four** native-adoption rows. The full matrix is
  generated for same-document, foreign-wrapper and third-document adoption cases: **384** production probes. Cross-document routing uses detached private native carriers,
  authenticated with unpredictable markers and linked by background handles before page resume. Live private
  isolated guard queries retain the source hold past 500 ms during synchronous handlers; the browser cases wait 650 ms before
  dispatch. Ordinary recipient documents get no added bridge listeners. Passive controlled recipients get isolated
  capture without MAIN prototype changes. Passive disposal confirms isolated teardown directly; it does not wait
  for a MAIN-wrapper restoration acknowledgement. MAIN-installed guards still require that restoration. Marker retirement, source release, forged public traffic and conservative
  recipient policy have separate regressions. MAIN document properties carry no API and may be forged harmlessly.
  MAIN metadata contains primitive source IDs; private guard references stay in our own isolated world.
  [Chromium clones object values between worlds](https://raw.githubusercontent.com/chromium/chromium/main/third_party/blink/renderer/bindings/core/v8/world_safe_v8_reference.cc), while its
  [isolated-world registry reuses a given world ID](https://raw.githubusercontent.com/chromium/chromium/main/third_party/blink/renderer/platform/bindings/dom_wrapper_world.cc).
  Native roots are registered while startup is paused; the isolated reference exchange waits until live page
  execution because [paused DOM callbacks are suppressed](https://raw.githubusercontent.com/chromium/chromium/main/third_party/blink/renderer/bindings/core/v8/js_event_listener.cc).
  Unavailable recipient guards hold as unknown and retry; inherited configuration preserves a stricter recipient.
  DOM branding accepts adopted native objects; private node metadata preserves sticky password exclusion across
  adoption, source release and retake. No password value enters that metadata.
- `guard.js`: native `a`, `area` and SVG `a` lose hyperlink authority synchronously, including both SVG `href`
  and namespaced `xlink:href` when both exist. Ping is quarantined. Native submit/reset controls (including image
  submitters and external `form=` buttons) are disabled through activation. Repeated interceptions restore their
  original state once. Destinations restore only if still carrying the guard's change. Shadow-root lookup accepts only HTMLElements,
  as the [Chrome API requires](https://developer.chrome.com/docs/extensions/reference/api/dom); SVG capture now reaches neutralisation rather than throwing. Unknown defaults, including
  checkbox/radio preactivation, never receive a false stopped result. The existing narrow DNR rule is unchanged.
- `reader.js`: exposes area/SVG link destinations as strings, names and input targets so the approved action can
  run normally. Image-map bounds and hit checking respect preceding map regions. Compose text walks only safe
  visible composed nodes, preserving line breaks, indentation, tabs and significant spaces under `pre`, `pre-wrap`,
  `pre-line` and `break-spaces`, including pre, textarea and code. Ordinary collapsible whitespace stays collapsed;
  pre-line indentation is correctly insignificant. Structural block separators do not consume leading pre-line
  newlines, trailing preserved newlines or block-leading br blank lines; visible descendants of visibility-hidden containers remain included. Computed display takes precedence over a
  hidden attribute overridden by CSS; the Linux PRE variant exercises hidden with display:block. Password exclusion is checked before every text/value read.
- Service questions include the original compose representation as well as exact before/after text on the one
  allowed re-ask. Service and extension bindings retain the same text. A second change stops with the decided
  owner-send message; stale approvals cannot send. The original input/whole-question bounds still apply.
- The new Linux matrices independently identify **33** native-default scenarios (each listed element, self/new
  context/frame, HTML link ping/download and reset) and **14** significant-whitespace changes. Every stopped
  sequence must remain zero through stale/re-ask/stop attempts, then reach exactly **0/1/1** after fresh approval.
  `recheck3.json` retains questions, bindings and outcomes; its separate auditor checks them against raw receiver
  arrivals and snapshots. The exact named qualification inventory now requires all three new matrices.

## Verified (run)

Local-only verification so far: **317 Node tests pass**, **225 removal mutations rejected, every baseline passing**,
384 generated production-code mixes pass, generated artifacts match definitions and `git diff --check` passes.
[Exact commands, output tails/hashes and corrected local attempts](records/recheck3/local-summary.json) retain the results.
The full plain-Python suite passes **231 tests in 580.856 s, OK**; Linux CI is still pending. Five artifact-stream tests pass. No local browser,
browser profile, container, Java/Gradle process or installed system software was used.

## Not verified / open questions

Linux browser receiver and privacy evidence on this source is pending. Live accounts/sites, owner panel acceptance,
real payment sheets, installed image behavior, main integration and deferred post-18d group 12 remain outside this
round. `KNOWN-LIMITS.md` is unchanged: none of its accepted lines changes. Unsupported native defaults are described
as unknown rather than claiming that their effects were stopped.

## JUDGMENT-CALL / PLAN-GAP (read)

The password-safe representation follows computed whitespace: `pre-line` keeps newlines but collapses indentation;
code with significant whitespace is exercised with pre-wrap. No blanket source-whitespace binding was added to
ordinary HTML. Questions retain the common escaping of controls (`\u000a` for a newline), with indentation and
spaces intact. Including the full initial compose text can reach the existing 4,096-character question limit sooner;
this refuses with the existing explicit size message instead of omitting content. This size cost goes to the lead
and owner before merge; changing it requires a shared approval-format decision. No new cap or blanket send refusal
was introduced.

## Runs and storage

Opening ledger: **209 distinct control-chrome IDs / 210 executions**. The first own pair
(`43357353936`, `43357386934`, source `939f9d5b`) was cancelled after the new leading-newline probe exposed an alias;
[completed receipts](records/recheck3/superseded-runs.json) retain the history. They are not acceptance evidence.
The replacement pair (`43358222546`, `43358273763`, source `93148a91`) failed strictly at SVG href-self: one
receiver arrival before approval. Both had passed all 40 mixed-step rows and the HTML a/area default cases.
[Raw-derived failure evidence](records/recheck3/svg-browser-failure.json) and the before/after local API-brand probe
retain the cause and fix; no failure is counted as acceptance. The next pair brings this to
**215 IDs / 216 executions**. Both runs on `2dd343ac` (`43359345725`, `43359355384`) then passed all 40 mixed-step
and 33 native-default scenarios, but failed at the strict second whitespace change: a trailing preserved newline
aliased the block separator and the changed text was sent. [Raw-derived receipts](records/recheck3/trailing-browser-failure.json)
and a strict before/after local regression retain this failure and the correction. Source-preserved and structural
breaks are now distinct on both sides of a block. The next own pair on `7536ebff` (`43360915882`, `43360937420`) was cancelled when the local computed-display
probe found omitted visible PRE text; no pass from it is claimed. The replacement pair brings this to
**219 IDs / 220 executions**. This build then cancelled its own `04eeaa1f` pair (`43361636639`, `43361855352`)
after the cross-controlled-document local probe failed; its partial evidence is not acceptance. The replacement pair
brings this to **221 IDs / 222 executions**. Both `55dde837` runs (`43366455119`, `43366547759`) failed the new
cross-frame case: WindowProxy did not expose the other isolated guard, leaving one unapproved arrival.
[Raw receipts](records/recheck3/foreign-browser-failure.json) retain this failure. The document-wrapper pair (`43368079994`, `43368174114`, source `14833d50`) also failed the same strict
cross-frame case, although both MAIN-absence checks passed. That candidate is superseded by the private carrier
registry; these failures are not acceptance. The own `9433b2be` pair (`43379684072`, `43379749705`) was then cancelled after the corrected clone model
proved its MAIN-function transport invalid. Its before/after local receipts are retained; no partial CI pass is
acceptance. The `bc90cdbd` pair (`43384844084`, `43384908890`) then failed the first foreign root-wrapper row: both private
peer exports returned false while startup was paused. [Raw-derived receipts](records/recheck3/paused-browser-failure.json)
and a strict before/after paused-listener regression retain this failure. Native peer registration now precedes
resume, and private isolated reference exchange waits until live use. The `613f2c96` pair (`43388084520`, `43388151101`) passes all 107 new receiver sequences in both installation
modes, but fails the existing taken-tab cleanup test after 38 named cases. [Independent scoped receipts](records/recheck3/passive-browser-failure.json)
retain both the new-case passes and the full-workflow failure. Passive disposal now skips the nonexistent MAIN
acknowledgement; the strict before/after local assertion and removal cover that correction. Mail's main job and
three shards passed on this source, but shard 0 reached its 45-minute timeout; the cancelled workflow is not a pass.
The `8b7e799c` pair (`43395458551`, `43395775465`) then outgrew the 300-minute container deadline.
[Strict raw-artifact audits](records/recheck3/timeout-browser-failure.json) pass all **107 new receiver sequences**
in all four datasets; the repeat’s external job also passes the complete **92-case** browser/privacy/owner audit
and **231 Python + 317 Node** checks. Both workflows nevertheless fail because their policy jobs time out;
these are superseded evidence, not final acceptance. [All ten completed receipts](records/recheck3/timeout-head-runs.json)
retain eight successful shared runs on that source. Only the workflow time allowance changes: **350 minutes**
for the container, **360 minutes** for the job. No assertion, case, sweep or runtime byte changes; the installed
runtime hash above is unchanged. The next pair brings the ledger to **233 IDs / 234 executions**, within the
approximate 235-run budget and below the 245 notice threshold. Each CI run uses one blocking `gh run watch`, without
turn-by-turn status polling. Report-only pushes use `[skip ci]`. Closing run IDs, exact logs and `.work/` inventory
will replace this pending section after verification. No main/PR merge, force-push or qualification-data publishing
is authorized in this round.

---

# Recheck fixes 2 / 2b / 2c — completed

**Run:** source `5c4e4add2b867f6e439f496a12320aea67c03f4b`, installed runtime
`5a22b796fd859535227a54f27456ac4c37731f310fb4ac94bcfda88f3233f9dd`. Both final Chrome runs pass
all **89 named browser cases in both installation modes**, followed by the mandatory full Python sweep.
Base, Mail, boundary and qualification also pass twice on this source. PR
[#27](https://github.com/Ares-Empire/AresOS/pull/27) remains draft and unmerged. The closing push changes reports and
evidence only, with `[skip ci]`. No branch was merged, and no design document was changed.

## Done (read)

- `page.js` / `guard.js`: MAIN-world Clipboard `write` and `writeText` wrappers observe native fulfillment with the
  original receiver/arguments and success/error behavior. Trusted `copy` events observe `execCommand` in the controlled
  document only. The listener neither cancels nor changes propagation; cached wrappers act natively after release.
  No clipboard contents, preview or hash are collected, and no `clipboardRead` permission is added.
- `reader.js` / `background.js`: the post-input result includes only
  `page.clipboard = {written:true, message:"The page wrote to the clipboard.", routes:[…]}` inside untrusted page
  observations. An authenticated, epoch/document-scoped metadata queue preserves the fact across navigation and
  consumes it once. This observes a page write; it does not prove the click caused it. Borrowed-native API writes
  remain undetected, explicitly tested and listed in [KNOWN-LIMITS.md](KNOWN-LIMITS.md).
- Ten click/input/action descriptions say to tell the owner about a reported write and never paste or run clipboard
  contents because a page asked. [All 28 descriptions](TOOL-DESCRIPTIONS.md) match the generated tools. `SHARED` and
  `instructions_for` stay unchanged until the post-18d slim-generator move.
- The default-action guard synchronously neutralizes destinations/submitters while a narrow, tab-scoped session DNR
  rule blocks only the content-free quarantine address. Approved input and private owner-marked navigation retain
  native destinations. Expiry, answer/deny, Stop/close and restart reconciliation remove the rule. A stopped default
  reports its reason and is never automatically replayed.
- Compose binding covers the smallest composed ancestor holding Send and its draft/editor, including visible
  read-only preview text. A first change retires the original approval and re-asks with exact before/after text;
  a second change stops and asks the owner to send it himself. Outside live text stays free. Whole-body compose
  binds all visible body text, with the accepted owner-send cost below.
- Native-created/imported/cloned nodes and handler installation acquire private capture before borrowed insertion.
  The all-borrowed-native factory/root/listener/insertion/non-composed-dispatch path is the lead-accepted autonomous
  page limit. Its click result reports dispatch with delivery unproven and untrusted page observations; it does not
  falsely claim that the hidden step was stopped or that nothing happened.

## Verified (run)

Local commands and sanitized output tails/hashes are in [local-summary.json](records/recheck2c/local-summary.json):

- `PYTHONPATH=control:control/chrome_tests PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s control/chrome_tests -v`:
  **230 tests in 580.945 s, OK**.
- `node --test control/chrome_tests/*.test.mjs`: **288 passed**, zero failed/cancelled/skipped.
- `python3 -B reviews/20-chrome/mutation-audit.py reviews/20-chrome/records/recheck2c/mutations.json`:
  **187 removals rejected; every baseline passed**. [Exact mutation results](records/recheck2c/mutations.json).
- Five artifact-stream tests and four transport regressions pass. Generated artifacts match definitions;
  `git diff --check` passes. No local browser/profile, container, Java or Gradle process was started or accessed.
  All browser evidence comes from GitHub Linux containers in `control-chrome.yml`, using synthetic fixtures.

The first local Python invocation omitted `PYTHONPATH` and failed only the `test_bridge` import; the complete corrected
invocation above passes. Full local base discovery lacked `jsonschema` (23 errors); no dependency was installed.
The complete base suite passes in CI below.

| Workflow | First successful run | Second successful run |
|---|---|---|
| Control Chrome | [43319232281](https://github.com/Ares-Empire/AresOS/actions/runs/43319232281) | [43319941241](https://github.com/Ares-Empire/AresOS/actions/runs/43319941241) |
| Control base | [43319945952](https://github.com/Ares-Empire/AresOS/actions/runs/43319945952) | [43324347900](https://github.com/Ares-Empire/AresOS/actions/runs/43324347900) |
| Control Mail | [43319957579](https://github.com/Ares-Empire/AresOS/actions/runs/43319957579) | [43322952952](https://github.com/Ares-Empire/AresOS/actions/runs/43322952952) |
| Control boundary | [43319949694](https://github.com/Ares-Empire/AresOS/actions/runs/43319949694) | [43320702816](https://github.com/Ares-Empire/AresOS/actions/runs/43320702816) |
| Control Chrome qualification | [43319953689](https://github.com/Ares-Empire/AresOS/actions/runs/43319953689) | [43320706777](https://github.com/Ares-Empire/AresOS/actions/runs/43320706777) |

[Completed source/job metadata](records/recheck2c/completed.json),
[all 356 exact browser PASS locations](records/recheck2c/test-index.md),
[independent browser audit](records/recheck2c/browser-audit.json), and
[eight shared-artifact checks/hashes](records/recheck2c/shared-audit.json) retain the results.
Each Chrome job also passes **230 Python and 288 Node tests**. Each base run passes **146 tests**; each Mail run
passes **146 base + 309 Mail** and all four **4-test fault shards**. Boundary records **127 attacks** per filter mode,
**42 unchanged protected files** and **zero hostile connections**; absent-filter VSOCK transport is explicitly
unqualified, not a successful denial. Qualification passes **47 Python + 288 Node** plus real attestation/delivery
verification. Branch-only runs skip main-only publishing; nothing was written to the real qualification data branch.
All four browser datasets use **Google Chrome 157.0.8103.78**.

### Default actions, compose and clipboard

Every exact case is indexed above; the changed cases are:

| Named browser case | Independent result |
|---|---|
| GROUP 2 RECHECK2 every borrowed native insertion route captures noncomposed shadow events | Open/closed roots, six insertion routes and reused Events; fresh approval is exactly 0/1/1 |
| GROUP 2 RECHECK2 native defaults cover new tabs frames ping forms and downloads | `_blank`, frame, ping, form, form-to-new-window and download all stop before approval, then exactly 0/1/1; approved ping once |
| GROUP 2 RECHECK2 the owner navigates during the network hold | Owner navigation arrives once; exact destination remains strict |
| GROUP 3 RECHECK2 live compose text reasks once while outside text stays free | Outside live text sends 0/1/1; inside changes re-ask once with before/after, then owner-send with zero arrivals |
| GROUP 5 RECHECK2C clipboard writes are reported without reading contents | `writeText`, `write`, `execCommand('copy')` and write-then-navigation all report the content-free fact; receiver 0 before/1 accepted/1 after status |
| GROUP 8 RECHECK2 extension restart reconciles leftover session network rules | Fresh session has no stranded rule 2 |
| GROUP 13 RECHECK2B all-native limit records user activation and honest after-click reporting | Ten probes, exact autonomous/click receipts and honest dispatch/delivery-unproven result |

[Clipboard report facts and observed documents](records/recheck2c/clipboard-reports.json) include all four routes in
each dataset. The navigation variant returns its write fact on the **new compose document**. The synthetic written
marker never appears in any result. Unit/removal probes cover both API wrappers independently, trusted copy,
forged-copy rejection, native error behavior, release, private message boundaries, post-input consumption,
navigation retention and the description warning. A native node adopted into an ordinary document reproduced a
false copy warning; the fixed native composed-root check excludes it without changing copy delivery. Its focused
regression and removal probe pass. [Before/after reproduction](records/recheck2c/copy-document-scope.json).

### User activation — measured, lead decided

Every Claude click grants user activation to the page's own handlers, as an owner's click does. Withholding it would
break ordinary clicks. This is a property of **all clicks**, not only A-3. The final four datasets repeat ten probes
each: open and closed roots, secure localhost, all steps borrowed from an ordinary same-origin donor window.

| Probe | Autonomous | Inside Claude's click |
|---|---|---|
| Transient / sticky activation at the hidden handler | false / false | true / true |
| Popup | blocked | opened; child joins control |
| Clipboard write | pending native permission after bounded 2.5 s | accepted without clicking Allow |
| Download | independent receiver arrival | independent receiver arrival |
| Synthetic unsupported PaymentRequest | rejected | rejected |

[Actual measured probe rows](records/recheck2c/activation-probes.json) retain the outcomes/error names. The payment
probe is no evidence about real payment sheets. Popup control, opener badges and first-input reload rules are also
covered by the full group-8 cases. Borrowed-native Clipboard API writes remain **undetected**, as the browser and
unit tests require. The hidden event stays untrusted, but runs unasked both autonomously and under the click.
The original click is reported as dispatched with delivery unproven; no hidden stopped/unknown step is invented.
This replaces the unconditional “adds no harm” claim under the lead's 2c decision.

### Independent receiver and password boundary

The artifact-only audit reconstructs ingress and checks every approval snapshot against the separately recorded
raw receiver. Every complete sequence is exactly **0 before / 1 after / 1 after repeat**. It also verifies changed
quantity/draft/item bodies, three ordinary GET queries, all default routes, bounded compose zeroes, restart cleanup,
clipboard facts and the owner-mark overlap proof. Protocol and sensitive-getter observations must be present; no
password sentinel reaches reconstructed ingress, tool or service output, and forbidden Runtime value events are absent.

| Run / install | Page 0/1/1 | Adapter 0/1/1 | Ingress rows | Protocol events | Sensitive getters |
|---|---:|---:|---:|---:|---:|
| control-chrome-43319232281-1-external | 1277 | 139 | 165606 | 30257 | 3854 |
| control-chrome-43319232281-1-policy | 1277 | 139 | 165077 | 28419 | 3854 |
| control-chrome-43319941241-1-external | 1277 | 139 | 165877 | 30205 | 3854 |
| control-chrome-43319941241-1-policy | 1277 | 139 | 163766 | 28431 | 3856 |

The raw-derived owner proof requires his Enter's consumed private mark, immediate arrival within 200 ms, a real
Claude timer firing inside an independently bounded Enter-mark interval, zero timer arrivals until its own approval,
then one with no repeat. All four datasets pass. Owner Enter remains “passes in CI, panel to confirm”; CI does not
grant panel acceptance. [Audit program hashes](records/recheck2c/audit-sources.json).

### Measured views

The representative long article/form has 120 paragraphs and 80 fields. Each dataset reads all 14 bounded pages;
each tree page is at most 16,000 characters. Bytes equal characters for these synthetic pages. Token counts below
are `ceil(characters/4)` estimates, not tokenizer measurements.

| Run / install | Characters / UTF-8 bytes | Pages | Milliseconds | Estimated tokens |
|---|---:|---:|---:|---:|
| control-chrome-43319232281-1-external | 221477 / 221477 | 14 | 23661 | 55370 |
| control-chrome-43319232281-1-policy | 221476 / 221476 | 14 | 17998 | 55369 |
| control-chrome-43319941241-1-external | 221477 / 221477 | 14 | 21911 | 55370 |
| control-chrome-43319941241-1-policy | 221476 / 221476 | 14 | 23982 | 55369 |

[Actual measurements and exact VIEW log lines](records/recheck2c/view-measurements.json). Screenshots remain in
the linked Linux artifacts; no browser profile is exported.

## Earlier failures and corrections (run/read)

Source `5f0b5681` completed all 89 browser cases in all four jobs; three completed the mandatory subsequent Python
sweep. Push `43270186321`'s external job hit the 240-minute container limit during the final storage sweep;
it is **not green**. Repeat `43270268166` passed both installs, external in 3h56m3s.
[Retained partial audit](records/recheck2c/browser-audit-partial.json),
[timeout output and metadata](records/recheck2c/timeout-43270186321.json).
Both normal and qualification-pair batch budgets are now 300 container / 310 job minutes.

**Suite duration, measured by the package lead (run):** the final pair took 204.6 and 242.8 minutes
(`43319232281`, policy and external) and 221.9 and 243.4 minutes (`43319941241`, external and policy). In the
longest job, the Python suite took 2,151 s (230 tests; 712 s for 171 tests in `42773249076` on 11-10) and the browser
cases 206 minutes (84 minutes in `42773249076`). One case is most of it: `GROUP 1 what asks word/label/key matrix`
took 105.4 minutes for the same 972 cases that took 47.9 minutes on 11-10, at a steady pace (7.5 to 9.8 minutes per
81 cases, no stall). The next largest, the forms and catalogues case, went from 6.3 to 16.8 minutes. The raise
therefore covers more time per tool input across the matrix, not a stuck step. Where that time goes per input (the
hold window's session rule, the post-input observation, the compose-area binding, the clipboard hooks) is not
measured yet. No assertion or required
sweep was removed. Superseded own runs were cancelled after the budget/copy-scope corrections; no other owner's run
was cancelled. The final pair above completes everything on the corrected runtime.

Base `43320698770` hit its job limit in checkout's git fetch before any test started; its test step was skipped.
[Checkout failure receipt](records/recheck2c/base-checkout-timeout.json). Its unchanged-source replacement
`43324347900` passes. Earlier chooser/bootstrap, native navigation-completion and transport-envelope corrections
retain focused regressions/removal probes. Exact destinations, receiver counts and timing/ownership assertions
remain strict. Historical failing/partial runs are excluded from acceptance.

## PLAN-GAP / JUDGMENT-CALL — decided by the lead

The historical A-3 stop below remains, marked decided in 2b/2c. A hostile page can borrow all natives from an
ordinary same-origin donor and run labelled Delete unasked, just as it can autonomously fetch a deletion. Rejected
fixes: native entry breakpoints cannot see that borrowed call; DOM breakpoints expose raw attributes and violate
the password rule; attaching the donor violates “only Claude's tabs”. Every click adds activation; the measured
extra popup/clipboard capability is the accepted 2c cost, with clipboard reporting where observable and an explicit
known-limit line. This is not a blanket “adds no harm” assertion.

The lead accepted the narrow DNR plus synchronous default neutralization, proven above across all escape routes,
approved submissions and owner navigation. Whole-body compose binds **all visible body text**; live text there can
consume the one re-ask and end in “send it yourself”. The owner/live-site frequency remains to be measured after
boot. Delayed owner page work inside Claude's hold remains held when task ownership is unclear, as already decided.

## Not verified / open questions

The owner's panel/live-site acceptance, real payment sheets/accounts and bot checks, installed OS/Minecraft behavior,
integration with current main, production main-only qualification publishing, and post-18d group-12 precedence
remain outside this verification. The slim-generator `instructions_for(app)` sentence is still for post-18d;
the click descriptions carry it now. [KNOWN-LIMITS.md](KNOWN-LIMITS.md) is the surviving cost/coverage list.
The historical feature → tool → test map and 18d/19b handoffs below still apply. No new assumption is used as evidence.

**Read:** after `git fetch origin main`, specification files were read with `git show origin/main:<path>`;
latest read `d6df3ee3`. Briefs 2/2b/2c win where they differ. No spec/design file was edited.

## Runs and local storage

[Final branch ledger](records/recheck2c/run-ledger.json): **209 distinct control-chrome IDs / 210 executions**,
below the 245-run ceiling. Each run in this verification was waited on with one blocking watcher, without
turn-by-turn CI status queries. Report-only pushes
use `[skip ci]`. [Worktree inventory](records/recheck2c/work-inventory.json) lists files over 500 MB: **none**.
No ISO, image layer or extracted image was downloaded locally; exported CI evidence is logs/JSON/PNGs only, with
one local copy per retained artifact. No Gradle daemon was started.

---

# Recheck fixes 2 — historical stop — 2026-11-12

**Historical status: A-3 was open at this stop; the lead decided it in 2b/2c above.** The implementation was on `pkg/20-chrome`, source
`482eb7e728cdbdc46c5c05e75853bdb5caeed2d9`, installed runtime hash
`698a875de6b7d35bf229c4e690e788d007f3dfc98bf61087ecea923c181eff3e`. PR
[#27](https://github.com/Ares-Empire/AresOS/pull/27) remains draft and unmerged. No branch was merged into this one.
The historical green reports below do **not** satisfy `briefs/20-recheck-fixes-2.md`.

## Done

- `page.js` / `guard.js`: created, imported and cloned nodes, and click-handler installation, acquire private capture
  before borrowed native insertion. Weak listener bookkeeping avoids retaining every created node. Native attributes
  and doctypes keep their clone semantics; cached factory wrappers stop reporting after release. Capture decisions
  distinguish roots within one dispatch from a later reuse of the same page-owned Event, including slot traversal.
  **This is a partial A-3 fix:** a native factory plus native listener registration still bypasses these hooks.
- `guard.js` / `background.js`: the hold installs a tab-scoped session DNR fence for a content-free quarantine address
  and `main_frame`, `sub_frame`, `ping`, `other`. Isolated capture removes a non-cancellable link's `href` through its
  default, rewrites ping, or disables a submitter; form fallback uses the quarantined address and `_self`. A later task
  restores only attributes that retain the guard-written value. Approved input and private owner-marked navigation
  retain normal native destinations. Expiry, Stop/close and startup reconciliation remove session rules. Stopped
  activations are never replayed. This still depends on capture actually seeing the event; the A-3 bypass is not safe.
- `reader.js`, service adapter, `background.js`, shared engine: generic sends and confirmations bind the visible text
  of the smallest composed ancestor containing Send and the body editor, or additional visible draft/preview text
  when no editor exists. A change retires the first operation and prepares one question showing before/after text.
  Another change stops with “the text next to Send keeps changing” and tells Claude to ask the owner to send it
  himself. The final extension check carries the same bounded re-ask when drift happens during frame setup.
- Browser regressions now define borrowed native insertion routes, reused Events, `_blank`, named frames, ping,
  form defaults and downloads; owner navigation during the hold; live compose text inside/outside its area; and
  restart reconciliation of a stranded session rule. Existing residual cases require stopped defaults or changed-text
  re-approval with receiver 0/1/1. These definitions are not a completed acceptance run.
- `KNOWN-LIMITS.md` removes the two harmful residuals and records the bounded re-ask/owner-send cost. The remaining
  A-3 defect is a blocker, not an accepted limit. No design document or production CDP allowlist was changed.

## Verified

The requested specification was fetched and read from `origin/main`; the newer brief absent from that remote was
read locally. **No Chrome/Chromium app or browser profile was started, read or touched on this Mac.** All local tests
were plain Python/Node; every browser experiment ran through `control-chrome.yml` in GitHub Linux containers.
No local Java/Gradle process or container was started, so no Gradle daemon needs stopping.

[Commands, output tails, hashes and the failed additional probe](records/recheck2/local-summary.json):

- `PYTHONPATH=control:control/chrome_tests PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s control/chrome_tests -v`:
  **229 tests in 625.526 s; OK**.
- `node --test control/chrome_tests/*.test.mjs`: **271 passed; zero failed, cancelled or skipped**.
- `python3 -B reviews/20-chrome/mutation-audit.py reviews/20-chrome/records/recheck2/mutations.json`:
  **170 mutations rejected; every baseline passed**. Includes the new default/owner/rule, compose binding/re-ask,
  native capture/reuse and clone compatibility removals. This proves only those tested routes.
- `node --test reviews/20-chrome/audit-streams.test.mjs`: **5 passed**, zero failures.
- `python3 control/generate.py --check`: **Generated artifacts match definitions**. `git diff --check` passed.
- **Additional strict probe failed:**
  `node reviews/20-chrome/records/recheck2/native-production-gap.mjs` exits **1**. It loads the existing shadow-aware
  DOM double and unmodified production guard/page code, saves a native factory before activation, then uses native
  creation, root creation, listener registration, insertion and non-composed dispatch. Both open and closed roots
  record **one Delete handler / zero held steps**, where the assertions require **zero / one**.
  [Reproduction](records/recheck2/native-production-gap.mjs), [actual results](records/recheck2/native-production-gap.json).
  No passing suite overrides this failure.

Three Linux diagnostic runs tested an alternative native-entry interlock, in **both external and policy installs**
on Chrome **157.0.8103.78**. They are separate disposable experiments, not production acceptance or receiver proof.
[Retained raw logs, metadata and observations](records/recheck2/native-entry-diagnostics.json):

| Run | Result |
|---|---|
| [43246493921](https://github.com/Ares-Empire/AresOS/actions/runs/43246493921) | Native `dispatchEvent` entry pauses for the controlled realm; borrowed native open/closed handlers each run once. The older popup diagnostic also lacks its result. Failed. |
| [43248197704](https://github.com/Ares-Empire/AresOS/actions/runs/43248197704) | Registering the borrowed function handle is rejected as a duplicate native breakpoint location. Its shadow experiment does not run. Failed; not evidence of that experiment's outcome. |
| [43248868183](https://github.com/Ares-Empire/AresOS/actions/runs/43248868183) | Remove the original breakpoint, register the borrowed handle successfully, repeat: **one handler in each root mode in both installs**. The strict zero-handler assertion fails. |

The uncompleted acceptance runs [43237751838](https://github.com/Ares-Empire/AresOS/actions/runs/43237751838) and
[43248850718](https://github.com/Ares-Empire/AresOS/actions/runs/43248850718) were cancelled by this run after the
blocker was confirmed. They were both started by this run. No other person's run was cancelled. GitHub superseded
pending push runs `43246458316` and `43247784103`; neither ran fixtures. Earlier failed/cancelled attempts and every
shared-workflow result are retained in [the CI attempt ledger](records/recheck2/ci-attempts.json).

Base, boundary and qualification passed twice on the superseded `92892318` source; Mail passed once there.
[Shared artifact audit](records/recheck2/shared-audit.json) independently checks base **142 / OK**, boundary
**127 blocked / 42 protected files / zero hostile connections** per mode, and qualification **47 Python + 269 Node**
plus verifier evidence. These are historical results, not final-head acceptance. The full Chrome suite did not finish. Corrected in 2b: the cancelled run did reach and pass the new default/compose
matrices in both installs; its original log filter missed named PASS markers at line ends
([corrected retained rows](records/recheck2/cancelled-browser-progress.json)). There is no accepted four-artifact pair,
and no final receiver/privacy audit is claimed.

Opening ledger: **186 distinct Chrome workflow runs / 187 executions**. This run added **nine IDs**, including failed,
queued/cancelled and diagnostic runs: closing **195 IDs / 196 executions**, below the approximate 215 cap. One blocking
`gh run watch --exit-status --interval 60` process waited on each run; shell-session continuations did not create new
watchers or turn-by-turn Actions polling. The closing push contains reports/reproduction evidence only, with `[skip ci]`.
[Closing `.work/` inventory](records/recheck2/work-inventory.json): **no file over 500 MB**; no ISO/image/browser download
was made locally.

## Not verified

All three fixes are **not accepted as complete**. A-3 still violates the required no-handler/no-unreported-action
condition. The new default and preview matrices have not supplied final-head browser receiver 0/1/1 proof, and the
required complete suites twice on one accepted source are unfinished. Owner-panel acceptance, live accounts/sites,
the installed OS image and integration with current main remain unverified. Group 12 still waits for 18d.

## JUDGMENT-CALL

The network design combines a narrowly scoped quarantine-address DNR rule with synchronous native-default
neutralization. A catch-all tab block would also block approved native submissions and the owner's navigation; a
source-tab-only rule cannot itself cover a new `_blank` context. The combined design is implemented and locally
covered but **not approved as satisfying the brief**, especially while capture can be bypassed. Replacing it requires
retaining the strict default-route, owner-input and rule-lifetime matrices and removal probes. No feature-removing
refusal was introduced to obtain green.

The sibling-editor fixture's smallest common area is the whole body: the binding includes all its visible body text,
including recipients, editor and preview. A smaller compose ancestor excludes the surrounding timestamp, autosave
line and counter. When the compose area is the body, live body text is included and can reach the bounded owner-send
fallback. Changing that boundary later requires matching questions and bindings in reader, service and extension.

## PLAN-GAP — historical stop, decided by the lead in 20-recheck-fixes-2b

`briefs/20-continue-2.md` says to stop only after a real attempt when the section 6 guarantee cannot be met by a design
on the fixtures. The remaining case needs a synchronous browser hook **before native dispatch** that is scoped to
the controlled receiver document, even when the called native function belongs to an ordinary outside tab. The
available wrapper/capture design cannot provide that hook:

- A native factory, native `attachShadow`, native insertion and native listener registration bypass every MAIN hook.
  A non-composed event never reaches the pre-existing window listener. Mutation observers run after that synchronous
  stack, too late to stop its handler. The production DOM probe above demonstrates the gap in both root modes.
- A real attempt to add `Debugger.setBreakpointOnFunctionCall` reaches native API entry for the controlled realm,
  but not the borrowed call. Registering the borrowed handle itself does not change the outcome. V8 routes pauses
  through the paused context's inspector group; attaching only the controlled tab cannot receive the outside realm's
  native-entry pause. This explains the Linux observations; it is not a claim that the candidate was implemented
  in production. [V8 primary source](https://chromium.googlesource.com/v8/v8/+/refs/heads/main/src/inspector/v8-debugger.cc).
- Attaching the ordinary donor tab or every possible fresh realm would cross section 6's group boundary. The
  diagnostic confirms that the extension cannot attach to the Browser target or use browser-only auto-attachment.
  No ordinary-tab attachment was attempted.
- DOM mutation breakpoints require the DOM agent and push node paths/attributes before the extension can redact
  them. That conflicts with the password-ingress requirement. Listener breakpoints are already inside event
  delivery; their metadata has the event name and target tag, not a private original-event handle. The native
  `window.event` path deliberately does not replace the current event for shadow-tree invocations. Arbitrary page
  scope inspection or broad script stepping would expose values outside the password-safe reader. These alternatives
  were rejected from source/API analysis, not falsely reported as passing browser tests.
  [DOM debugger source](https://chromium.googlesource.com/chromium/src/+/refs/heads/main/third_party/blink/renderer/core/inspector/inspector_dom_debugger_agent.cc),
  [event invocation source](https://chromium.googlesource.com/chromium/src/+/refs/heads/main/third_party/blink/renderer/bindings/core/v8/js_based_event_listener.cc).

Meeting this case needs a browser-level dispatch hook or broader authority than the current Chrome-extension,
password-ingress and ordinary-tab constraints permit. Disabling page behavior, severing the donor relationship or
accepting the harmful bypass would remove a feature or weaken the requirement; none was done. This is recorded as a
**stop-rule blocker**, not a safe known limit or a green package. The attempted interlock remains diagnostic-only.

Earlier implementation defects were fixed rather than treated as blockers: the fixture's unreferenced timer was
replaced by explicit clock advancement, and the per-Event cache was changed to per-dispatch path/root tracking.
No assertion was weakened. The remaining architectural case is reproduced separately and kept strict.

## Open questions

The package lead needs a browser mechanism that can enforce the native-dispatch boundary while preserving the
password and tab-scope rules. Until that exists, A-3 and this brief stay open; the draft PR is not ready to merge.


---

# Recheck fixes — 2026-11-12

**Green twice on `495c0b3477e7496134028f5244b767b3f4bc7896`.** Runtime build hash:
`ad6a5daaebdb04d6d68c1ced88e7d0305136139208d73a21e9e8424a643ea70e`. PR [#27](https://github.com/Ares-Empire/AresOS/pull/27)
remains draft and unmerged on `pkg/20-chrome`. The PR currently conflicts with `main`; no branch was merged. The closing commit changes reports/evidence only and uses `[skip ci]`.
This section supersedes the historical acceptance below for `briefs/20-recheck-fixes.md`.

## Done

- `guard.js`, `policy.py`: explicit asking cues precede GET-search exemptions in activation, native form calls,
  submit capture and private/foreign-document relay. Actual submitter labels also prevent a form-level exemption.
  Editable query/message values are data: “Pay for lunch”, “Delete old notes” and “Send a letter” stay ordinary GET
  queries; compose Enter still binds every generic draft. Native/ARIA action controls retain their control semantics.
- `reader.js`: resolve the smallest affected container through composed ancestry, including shadow hosts and native
  slot assignment when a closed root hides the public `assignedSlot`. Bind identifying text from open/closed component
  content. Visible item fields, including quantity, are bound separately; protected fields retain presence without values.
- `adapter.py`, `policy.py`, `background.js`: generic send confirmations bind every eligible frame's complete draft set,
  including outside drafts when the confirmation belongs to a form. Both OK and Send submit buttons keep confirmation
  semantics. Incomplete eligible-frame coverage refuses in both service and extension bindings.
- `page.js`, `guard.js`: composed events discover unregistered native-created roots during window capture. Synchronous
  insertion, markup-setter and listener hooks register borrowed-native roots before non-composed activation can reach
  handlers. A shadow host's own activation also meets capture. Release restores saved descriptors without overwriting
  a page's later unrelated getter. No DevTools method, tool authority or ordinary-tab MAIN wrapper was added.
- Linux fixtures exercise Pay/Delete search handlers (also editable native/ARIA controls), ordinary GET query receipts,
  eight open/closed native-list/ARIA-row shadow and slot item variants, form-contained confirmations, compose Enter,
  changed quantity, and borrowed-native composed/non-composed cancellable/non-cancellable events. The receivers get
  the actual changed draft, invoice name or quantity. Stale approvals deliver zero; fresh approval delivers once;
  repeating it adds nothing. That historical non-cancellable-default acceptance is superseded by the recheck-2 fixes above; it is no longer a known limit.
- `owner-evidence.mjs`: test-package-only observations record private mark set/pass/held/end times without changing
  marks, allowances or scheduling. A real Claude-started timer fires while the private Enter mark exists; genuine
  owner Enter submits immediately and that timer's other form stays held. The four production removal probes remain.
- [KNOWN-LIMITS.md](KNOWN-LIMITS.md) lists every surviving review/section 6 limit with harm and acceptance. Fixed defects
  and closed evidence gaps are excluded. Historical tool/feature maps, dialog decisions and group 12's 18d deferral
  remain below.

## Verified

Specification: `git fetch origin main`, then the requested `git show origin/main:<path>` reads; local recheck briefs
win where they differ. No Mac browser, browser profile or container was started or accessed. Browser tests
ran only in the GitHub Linux containers; their exported failure PNG was inspected as a static artifact. No local Gradle/Java process was started, so there is no Gradle daemon to stop.

[Exact local commands, outputs and SHA-256 hashes](records/recheck/local-final-summary.json):

- `PYTHONPATH=control:control/chrome_tests PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s control/chrome_tests -v`:
  **224 tests, 658.232 s, OK**, including all 24 explicit state-removal kills and child-failure propagation.
- `node --test control/chrome_tests/*.test.mjs`: **257 passed**, zero failed/cancelled/skipped.
- `python3 -B reviews/20-chrome/mutation-audit.py reviews/20-chrome/records/recheck/page-mutations.json`:
  **147 mutations rejected; every baseline passed**. Includes P20-form, P20-submitter, P20-trust, P20-clear and the
  independent owner-overlap oracle removals, plus removals of all four fixes, closed slots, editable-data distinction
  and item fields in reader/service/extension. New field checks compare the whole field list; no existing assertion
  was weakened or skipped.
- `node --test reviews/20-chrome/audit-streams.test.mjs`: **5 passed**. Generated artifacts were regenerated and checked
  with `python3 control/generate.py --check`: **Generated artifacts match definitions**. `git diff --check` passes.

Each workflow below passed twice on the acceptance source; Chrome covers **both external and policy installs in
both runs**, for four complete artifacts. One blocking watcher per run waited to completion; no turn-by-turn Actions
status queries were used.

| Workflow | First run | Second run |
|---|---|---|
| Control Chrome | [43166895797](https://github.com/Ares-Empire/AresOS/actions/runs/43166895797) | [43167000276](https://github.com/Ares-Empire/AresOS/actions/runs/43167000276) |
| Control base | [43168120985](https://github.com/Ares-Empire/AresOS/actions/runs/43168120985) | [43168126665](https://github.com/Ares-Empire/AresOS/actions/runs/43168126665) |
| Control Mail | [43168132614](https://github.com/Ares-Empire/AresOS/actions/runs/43168132614) | [43170615949](https://github.com/Ares-Empire/AresOS/actions/runs/43170615949) |
| Control boundary | [43168138683](https://github.com/Ares-Empire/AresOS/actions/runs/43168138683) | [43168144172](https://github.com/Ares-Empire/AresOS/actions/runs/43168144172) |
| Control Chrome qualification | [43168149635](https://github.com/Ares-Empire/AresOS/actions/runs/43168149635) | [43168155392](https://github.com/Ares-Empire/AresOS/actions/runs/43168155392) |

[Completed workflow metadata](records/recheck/closing/completed.json),
[all 328 named browser PASS locations](records/recheck/closing/INDEX.md), and
[shared artifact hashes/checks](records/recheck/closing/shared-audit.json) retain the evidence.
Base prints **142 tests / OK** per run. Mail prints **142 base + 309 Mail / OK**, with **four 4-test fault shards / OK**
and fixture-isolation PASS per run. Boundary records **127 blocked attacks per filter mode**, **42 unchanged protected
files**, **zero hostile connections**, with the expected unqualified result when the filter is absent. Qualification
prints **47 Python + 257 Node** passes per run; its branch-only behavior leaves main-only publishing jobs skipped.
Manual qualification runs retain real Sigstore and altered/retained-bundle verifier output.

[Audit program sources and hashes](records/recheck/closing/audit-sources.json) accompany the outputs.
The artifact-only command `node --max-old-space-size=192 reviews/20-chrome/audit-review-evidence.mjs <artifact>` ran
separately for every Chrome artifact. [Independent receiver/privacy results](records/recheck/closing/receiver-audit.json)
require the exact **82-case inventory**, **224 Python / 257 Node**, complete raw receiver membership and final **0/1/1**
sequences. They also require all three exact ordinary GET queries, editable Pay controls, all changed-item/form/draft
variants, the fresh quantity **2**, fresh invoice **Invoice B**, and fresh draft **Different draft**. The raw private
owner observations and independently timestamped receiver rows must reproduce `owner-overlap.json` exactly.
[Additional raw fixed-case checks](records/recheck/closing/fixed-case-audit.json) verify stopped handlers, changed-content zeroes and exact receiver bodies independently.
No password sentinel appears in reconstructed ingress, tool or service output, and no forbidden Runtime console or
exception value event appears. Protocol and sensitive-getter observations must be present.

Browser version across all four artifacts: **Google Chrome 157.0.8103.78**.

| Run / install | Page 0/1/1 sequences | Adapter 0/1/1 sequences | Ingress rows | Sensitive-getter observations |
|---|---:|---:|---:|---:|
| 43166895797 / external | 1241 | 139 | 146964 | 3507 |
| 43166895797 / policy | 1241 | 139 | 146418 | 3507 |
| 43167000276 / external | 1241 | 139 | 148149 | 3505 |
| 43167000276 / policy | 1241 | 139 | 146504 | 3507 |

### Owner Enter evidence

[Raw-derived proof](records/recheck/closing/receiver-audit.json) includes the page Enter, submit and timer timestamps,
the receiver's arrival timestamp/body, the consumed private input mark, and both endpoints of the Enter-mark interval.
Chrome's implicit Enter submission produces a trusted submitter **click** with its own exact mark; the observer now
checks that actual native sequence rather than expecting a keyboard key on that click. Removing any required
observation, interval, token, consumed state or in-flight condition fails its independent probe.

| Run / install | Private mark event | Enter-mark interval (epoch ms) | Page timer fired (epoch ms) | Owner receiver delay after page submit |
|---|---|---|---|---|
| 43166895797 / external | keyup / Enter | 1794464248090.1–1794464248093.5 | 1794464248091 | 9.400 ms |
| 43166895797 / policy | keyup / Enter | 1794464247805.8–1794464247808.4 | 1794464247806.6 | 8.600 ms |
| 43167000276 / external | keyup / Enter | 1794477365110–1794477365114.4 | 1794477365111.3 | 8.600 ms |
| 43167000276 / policy | keyup / Enter | 1794477383559.5–1794477383562.2 | 1794477383560.2998 | 7.900 ms |

In all four artifacts, the owner reaches the receiver once with `draft=Saved`, without approval and within 200 ms.
The timer fires inside the observed mark interval, is held at zero arrivals, and reaches one only after its own
approval; repeat remains one. **The required overlap evidence is now present. Owner Enter remains “passes in CI,
panel to confirm”; CI does not grant panel acceptance.**

Earlier failed, cancelled or partial diagnostics are excluded from acceptance.
[Completed superseded-run metadata](records/recheck/superseded-chrome-runs.json) and the separately named superseded
local records retain that history. Only this build's superseded Chrome runs were cancelled.
[Final ledger](records/recheck/closing/run-ledger.json): **186 distinct Chrome IDs,
187 executions including the historical rerun**, against the budget of about 215;
the opening ledger had 175 IDs / 176 executions. Report-only pushes use `[skip ci]`.

### Worktree storage

During this run, no ISO, image layer, extracted image or browser package was downloaded locally. Each retained CI artifact has one
local copy. [Inventory of `.work/` files over 500 MB](records/recheck/closing/work-inventory.json):

None.

## Not verified

The owner's panel acceptance and real-machine feel; integration with current `main`; real accounts/live-site bot checks; the installed OS image and
Windows/Minecraft experience; group 12's deferred 18d permission-precedence harness; main-only qualification publishing.
Linux screenshots remain in the linked CI artifacts. No Mac browser/profile was used for verification.

## JUDGMENT-CALL

**Editable action controls:** native/ARIA click controls are treated as controls even when `contenteditable` is set.
This closes the explicit-Pay bypass and also makes tool `type` into those controls refuse. Ordinary textareas,
textboxes and query/message editors remain editable. The rejected alternative was a separate editor/action flag,
which preserves rare editable-button-label workflows but changes the private classification/binding contract.
Changing this later needs a small reader/policy/both-bindings update and regressions; pending approvals must be prepared
again. This refusal is explicitly for lead/owner review before merge.

**Whole item questions:** visible item fields now participate in the existing complete-question size cap. A large
item editor set can therefore require a smaller item or owner action; values are never silently omitted or truncated.
The rejected alternative was approving an item while omitting a quantity or other editable field. Changing the cap
requires reviewing question rendering and bounds, rather than weakening stale-approval checks.

Existing owner-policy decisions, including borrowed dialogs, first-act reload, catalogue lifetimes and honest
unknown outcomes, are unchanged. No new owner policy or system authority was introduced.

## PLAN-GAP

GitHub reports PR #27 as `CONFLICTING` / `DIRTY` ([final metadata](records/recheck/closing/pr-state.json)); no automatic PR workflows appeared for this head. The [run rules](../../briefs/20-continue.md) say “Don't merge other branches” and prohibit merging or force-pushing. No integration was attempted. Required workflows were dispatched manually on the exact branch head instead. Integration with current `main` remains unverified and requires the lead's separate resolution. The existing Chrome dispatch 43167000276 initially returned a metadata 404; its receipt was retained and adopted without redispatch.

The superseded `6c91e209` attempt exposed a fixture race: a 100 ms on-load script POST replaced the initial GET before the strict native owner-navigation probe observed it. The [Linux failure screenshot](screenshots/recheck-script-post-race.png) and [receiver diagnostic](records/recheck/superseded-6c91e209/failure-diagnostic.json) show the POST had already completed. The fixture now waits for the native GET probe before scheduling its real page timer; takeover also waits for the exact POST URL. Navigation, POST-refusal and exact-once assertions remain strict. Three removal probes independently remove those barriers. That source is excluded from double acceptance.

The simple “editable” flag also covered action controls, while editable message/query values could look like action
labels. The fixes separate those meanings conservatively, with the refusal above disclosed. Affected-item text alone
also omitted native quantity values; those fields are now explicit bound content. The actual trusted-click sequence
of native Enter needed observation-based evidence; it did not need a production mark-lifetime change.

## Open questions

Panel confirmation of owner Enter and lead/owner review of the two refusal surfaces above. The current PR/main integration status is recorded above; branch merging is outside this run's permission. No implementation blocker within this brief remains. PR #27 stays draft; nothing was merged.

---

# Historical combined acceptance (before this recheck)

# 20 — combined page/state fixes and capped catalogue snapshots

**Read — integrate-3 and the user's 2026-11-11 resume instructions govern.** The lead already merged Part P (`df9b3fc5`) and Part S
(`1418fcde`, merge `3b37bd57`). This run adds the decided catalogue cap and verifies their combined head.
[STATE-FIXES-REPORT.md](STATE-FIXES-REPORT.md) maps S1–S12 and records the accepted lifetime decision;
[BUILD-P-1.md](BUILD-P-1.md) and [BUILD-P-5.md](BUILD-P-5.md) map P1–P31. PR [#27](https://github.com/Ares-Empire/AresOS/pull/27)
remains draft and unmerged. **Owner Enter: passes in CI, panel to confirm. Group 12 remains deferred to 18d.**

**Combined integration: green twice on `0ae4ac41`.** [Attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/42989465778/attempts/1)
and [attempt 2](https://github.com/Ares-Empire/AresOS/actions/runs/42989465778/attempts/2) each run every Chrome job
in both install modes. All four artifacts pass 80 named browser cases, 220 Python tests, 243 Node tests and the
independent receiver/ingress audit. Base, Mail, boundary and qualification each pass twice on that same source.
The [closing evidence index](records/integrate3/closing/INDEX.md) records all 320 named PASS lines and ten complete
workflow executions. The lead's pause-only `65ba456b` is preserved; the subsequent audit/report commits change
no installed runtime, CI tests or workflow. PR #27 remains draft; no merge or review was started.

## Done / scope (read)

`collection()` in `control/chrome/extension/background.js` records a separate, immutable creation time.
Downloads, history and bookmarks expire at the earlier of **five minutes since the last valid page request**
and **thirty minutes since creation**, including the exact deadline. Valid cursors renew only idle time.
Expired cursors refuse with **“list snapshot changed or expired; start the list again without a cursor”**;
they never restart a query silently. New lists prune both expired kinds before the existing two-snapshot eviction.
The 10,000-item / 8 MiB bounds are unchanged. Shared `control/aresos_control/paging.py`, `results.py` and `mail/`
are untouched by this cap; Mail behaviour and merge order are unchanged. Part S's one-line renewal in this
Part P-owned file was merged into Part P's equivalent renewal; this run keeps that merged version.

`state-catalogues.test.mjs` preserves the complete 80-row immutable walk, with 40-second page intervals
(26 minutes total) to stay inside the new absolute limit. Its former four-minute intervals implied a
156-minute walk, now explicitly disallowed by the brief. No row/count/source-immutability assertion was removed.
It additionally checks all three catalogues immediately before and at idle/absolute expiry, repeated refusal,
fresh restart, pruning an actively used expired snapshot, invalid-cursor nonrenewal and two retained snapshots.
The page removal audit adds absolute-cap, idle-deadline, absolute-pruning and actionable-error mutations.
The independent receiver auditor now requires the combined **220 Python / 243 Node** inventory, with no failure,
cancellation or skip accepted, and retains the existing exact browser inventory and receiver/ingress assertions.

`python3 control/generate.py` regenerated every artifact; its check found no drift. No shared runtime,
classification, binding, approval or site-adapter behavior changes in this round. The combined CI run exposed
six reads in Part P's newer `review-matrices.mjs` that still expected top-level `dialog`; they now consume
Part S's `untrusted_content.dialog`, like the other fixture consumers. Receiver/approval assertions are unchanged.
The browser-free contract regression executes the actual 15 ordinary and six inline dialog review variants with
a read result that rejects top-level dialog access; its removal mutation fails. A later combined run exposed the
native-dialog publication race described below; its fix also stays in `background.js`. Final runtime build hash:
`74741aa57ecbd62922500cbb600426719ef5141d35efd3b7750c1b13683a6269`.
Specification was fetched with `git fetch origin main` and read using `git show origin/main:<path>`; local
integration/review briefs take precedence. Nothing outside this worktree, no browser/profile on this Mac,
and no system software or Gradle daemon was used.

## Decided rules carried by the combined head (read)

- **Catalogue lifetime:** the lead accepted Part S's idle renewal on 2026-11-10 with the thirty-minute absolute
  cap. This is a decided rule, needs no owner decision, and does not change Mail.
- **Popups:** only children of a currently controlled native opener gain private control; opener membership/epoch
  is rechecked. No extension window opens or takes focus. Existing popup windows stay in their original window/type.
  The opener's **POP** badge and its existing toolbar action list each popup with an individual **Stop**.
  Stop ends authority immediately without moving, closing, reloading or resizing the page popup; opener loss revokes
  its children. Manual popup admission requires the same controlled native opener.
- **Reload on first act:** taking/reading an owner tab or popup preserves its page. The first act makes one guarded
  GET reload and invalidates old references. Unsaved text, possible uninspectable edits or playing/audible media
  report `reload_required`; only a repeated explicit `reload_taken_tab=true` permits it. POST/non-GET/unknown-method
  documents refuse and suggest opening the address fresh; form-target popups also refuse, including GET.
- **A dialog already open:** the initial Page-enable wait is bounded at five seconds. If blocked, detach the pending
  debugger target while retaining control/session state and tell Claude **“Please answer the dialog yourself.”**
  After the owner answers, read reattaches and completes setup without a browser restart; first-act reload still
  applies. Responsive slower Page-domain setup must not produce a false handoff. Native-UI answering is out of scope.
- **Borrowed-realm native dialogs:** authenticated alert/confirm/prompt events without the private return token
  always ask. The service question binds tab/control, type/text and exact answer/prompt and states that its
  continuation is not held. Approval is consumed before one answer; changed bindings/repeats refuse. No adapter
  confirmation or owner allowance exempts it. A prior hold remains until the resumed handler finishes. Drop leaves
  the dialog to the owner.
- **Owner's own Enter:** **passes in CI, panel to confirm**. Exact form, submitter, trusted input and mark clearing
  each have a removal regression. In-flight, while-mark-set wrong-form/wrong-submitter, delayed and unconsumed-mark
  cases remain held. No panel acceptance is inferred from CI.

- **Other controlled documents:** an asking call through another controlled document goes through that
  document's private guard. Unclear ownership holds the call; page-visible state cannot relax it.
- **Owner-selected files:** the exact chosen content is bound by SHA-256 and shown in the question. Changing
  selected bytes invalidates the approval, including a same-name/same-size replacement.
- **Inline editors:** `about:blank` and `srcdoc` editors participate in complete binding through authenticated
  inherited origin and native document identity. They are covered rather than refused as a class.

**Fixed DevTools additions for controlled-only injection:** `Runtime.evaluate`, `Runtime.callFunctionOn`,
`Runtime.runIfWaitingForDebugger`, `Debugger.enable`, `Debugger.disable`, `Debugger.setBreakpointByUrl`,
`Debugger.resume`, `Target.setAutoAttach`, `Target.detachFromTarget`, `DOM.describeNode`, `DOM.resolveNode`,
and `Page.getFrameTree`. `Page.enable` and `Page.handleJavaScriptDialog` support native dialog observation/answers;
ordinary input/navigation methods remain the original fixed list. `Runtime.enable` is absent (the earlier
integration report's list below is historical). No `Page.createIsolatedWorld` or generic script tool is added.
The inert ISOLATED bootstrap pauses only controlled documents; private bundles install before page code, using
authenticated contexts and recursive iframe-only auto-attach. No MAIN script or cancelling listener is installed
in ordinary owner tabs. This cap adds no DevTools command.

## Verified (run) / exact-head CI evidence

`PYTHONPATH=control:control/chrome_tests PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s control/chrome_tests -v`
passed **220 tests, OK, 571.272 s** ([complete output](records/integrate3/local-python.txt), result lines 273/275).
This includes both parts' regressions, **24 state removal mutations** (lines 216–239), **nine actual process cuts**
(line 192), writer sweeps **1,862 single / 1,862 persistent / 7,127 cleanup pairs** (line 82), and dispatch sweeps
**448 / 448 / 2,128** (line 253). Every public view is checked under exhaustion, after space returns without restart,
and after restart. `node --test control/chrome_tests/*.test.mjs` passed **234/234**, zero failures/cancellations/skips
([complete output](records/integrate3/local-node.txt)). The page [removal audit](records/integrate3/page-mutations.json)
rejects **106 mutations**, every baseline passing ([output](records/integrate3/page-mutations.txt)); its command,
the state mutation names, output hashes and exact result lines are in [local-summary.json](records/integrate3/local-summary.json).
Regeneration/check printed `Generated tools, help, reference and ask rules` then `Generated artifacts match definitions`;
`git diff --check` passed. These commands started no browser.

Browser acceptance runs only in GitHub Linux containers through `control-chrome.yml`. The qualified source is
`0ae4ac414cb6423059e496d1fdbb90860428c101`, with the unchanged runtime build hash above. The user requested
both complete attempts on that source followed by this report push. This post-verification report/auditor-only
push uses `[skip ci]` to avoid launching unnecessary extra Chrome jobs; it is not substituted for a test run.
[Completed metadata](records/integrate3/closing/completed.json), [all named cases](records/integrate3/closing/INDEX.md),
[receiver/ingress audits and raw file hashes](records/integrate3/closing/receiver-audit.json),
[shared-suite results](records/integrate3/closing/shared-summary.json),
[view measurements](records/integrate3/closing/view-measurements.json) and
[audit commands/resources](records/integrate3/closing/audit-commands.json) retain the final evidence.
Raw Linux artifacts remain under their named GitHub run/attempts and in `.work/20-integrate3/manual-final/`.
No earlier partial pass is counted toward this acceptance.

**Initial combined CI failed, not acceptance:** [42955378005](https://github.com/Ares-Empire/AresOS/actions/runs/42955378005)
and [42955382845](https://github.com/Ares-Empire/AresOS/actions/runs/42955382845), both install modes, source
`4340939a`. Each passed its 49 focused Python and 234 Node tests and the preliminary browser checks, then failed
the first native-dialog review case at the obsolete selector. The service correctly returned the authenticated
native alert inside `untrusted_content`; [four-job diagnosis with exact failure lines](records/integrate3/first-combined-failure.json)
retains this evidence; the inspected [Linux-container screenshot](screenshots/integrate3/native-dialog-contract-failure.png)
shows the actual alert still open. Full Python/browser acceptance was not reached. This integration defect required the
follow-up fixture/contract-test batch; no assertion or feature was weakened and no browser ran locally.

**After the consumer correction (run):** full local Python again passed **220 tests, OK, 742.060 s**, including
the complete storage sweeps, nine process cuts and all **24 state removal mutations**. Node passed **235/235**,
zero failures/cancellations/skips. The complete page audit rejects **107 mutations**, every baseline passing,
including the new S12 consumer-contract removal. [Exact commands, result lines and hashes](records/integrate3/local-recovery-summary.json)
index the retained [Python](records/integrate3/local-python-recovery.txt), [Node](records/integrate3/local-node-recovery.txt),
[page audit output](records/integrate3/page-mutations-recovery.txt) and [mutated assertions](records/integrate3/page-mutations-recovery.json).
Generated artifacts still match and the runtime hash is unchanged. The next push repeats every named CI workflow
on the corrected exact head; the failed browser pair is never counted as acceptance.

**Initial shared results / deterministic base-test repair (run/read):**
[exact completed results](records/integrate3/initial-combined-workflows.json) retain base, boundary and qualification
green twice on `4340939a`. Mail [42955406042](https://github.com/Ares-Empire/AresOS/actions/runs/42955406042)
passed **142 base + 309 Mail tests and all four sweep shards**. Mail
[42955382856](https://github.com/Ares-Empire/AresOS/actions/runs/42955382856) passed its four sweep shards but its
base suite failed `test_review22_upload_lost_final_ack_is_unknown_and_import_commits` before Mail ran
([exact failure](records/integrate3/base-upload-failure.txt)). Its 50 ms deadline applied to startup/admission/chunk
replies too, so it could fail before the end frame; the missing blob proves the import was not committed, not which
earlier response timed out. `control/tests/test_review22_protocol.py` now injects a socket timeout only when the
client has sent its real final end frame. The real server still commits after the client disconnects. Every prior
unknown/hash/byte/journal assertion stays, with a new assertion that the intended boundary was reached; no timeout
or production code changes. [Ten repetitions](records/integrate3/base-upload-repeat.txt) pass in **2.556 s**;
the [three real socket timeout tests](records/integrate3/base-timeout-regressions.txt) pass in **22.385 s**.
The first local attempt omitted jsonschema's path and failed import; the corrected invocation uses
`PYTHONPATH=control:control/tests:.work/20-chrome/python-deps`, reusing the existing worktree-only dependency,
with `PYTHONDONTWRITEBYTECODE=1`. No software was installed. Full Linux base/Mail repeats remain mandatory on the
next head; the one earlier Mail pass is not substituted for them.

**Second combined head / native-dialog publication race (run/read):** source `318b0815` passes base,
Mail, boundary and qualification twice ([all eight completed results, exact lines and artifact hashes](records/integrate3/second-shared-workflows.json)).
Chrome [42959080697](https://github.com/Ares-Empire/AresOS/actions/runs/42959080697) external passed all 15
ordinary native answers at receiver 0/1/1, six inline native dialogs and three bounded handoff/recovery cases.
It then read the first prompt-default-conversion borrowed dialog while the opening handler was awaiting native
frame lookup. The returned object had its text but **no frame, browser document or `unguarded` decision**;
the strict borrowed-dialog assertion failed. [Exact partial object, failure lines and artifact hashes](records/integrate3/dialog-readiness-failure.json)
retain this race, not a qualification pass. After the failed job was complete, this build cancelled only its own
failed push run so the existing blocking watch could finish before its logs were read. Its separate
[PR run 42959087676](https://github.com/Ares-Empire/AresOS/actions/runs/42959087676) was subsequently cancelled
as superseded by the tested fix. Neither run is acceptance evidence.

`background.js` now keeps a private promise for each native opening until frame identity and native-return
provenance have been classified. Reads, dialog facts, observations and acting-result dialogs await that promise.
A dialog opening during the final frame-reader reply re-enters the modal read path instead of exposing a partial
object or page rows behind it. A stalled lookup is bounded at five seconds and says to read again; completing it
recovers normal reads. Existing unestablished/excluded-frame refusals remain, and normal supported dialogs retain
their decided asking/holding behaviour. No page can resolve the private gate. Three clock/ordering regressions
cover every read path (guarded and borrowed), the final-reader race and bounded recovery; four new removal
mutations cover waiting, final-reader routing, completion and the deadline. The standalone confirmation-handler
VM fixture adds the new private WeakMap; its original match/consumption assertions are unchanged. The existing
native-frame mutation targets the same origin-authentication expression after its new `try/finally` scope.

**Final-source local verification (run):** the complete Python command above passes **220 tests, OK,
905.895 s**, with the full writer/dispatch sweeps, all **nine process cuts** and **24 state removal mutations**.
Node passes **238/238**, zero failures/cancellations/skips. The full page removal audit rejects **111 mutations**,
every baseline passing. [Exact commands, source, runtime hash, result lines and output hashes](records/integrate3/local-dialog-ready-summary.json)
index [Python](records/integrate3/local-python-dialog-ready.txt), [Node](records/integrate3/local-node-dialog-ready.txt),
[page audit output](records/integrate3/page-mutations-dialog-ready.txt) and [mutated assertions](records/integrate3/page-mutations-dialog-ready.json).
All generated files were regenerated and checked again; syntax/diff checks pass. The report/evidence commit
changes no runtime or test after these checks. The final exact-head Chrome pair and every shared-workflow repeat
must finish before the closing response reports green, and their four full browser artifacts must pass the
independent receiver/ingress audit. Superseded partial passes are not substitutes.

**Third combined head / missing popup reader and full-suite deadlines (run/read):** base, Mail, boundary and
qualification pass twice on `f25ac736` ([eight completed results and output hashes](records/integrate3/third-shared-workflows.json)).
Chrome [42963287917](https://github.com/Ares-Empire/AresOS/actions/runs/42963287917) external passes 20 named
cases, then fails the first popup's `Continue` lookup. Admission completed against the popup's initial empty
frame tree; only its hidden child's context marker was observed after attachment, and the committed top document
had no reader reply. The repeated empty reads contain no password-history refusal; earlier refusals in the raw
artifact belong to preceding review cases. The other three install legs, including both legs of
[42963294395](https://github.com/Ares-Empire/AresOS/actions/runs/42963294395), finish all **80/80 browser cases**
but exit 124 during the full Python suite at the former 165-minute container deadline. Their missing Python `OK`
is a failure, never acceptance. [Exact matrix counts, failure lines, job times, raw hashes and diagnosis](records/integrate3/popup-and-deadline-failure.json)
retain these results.

The [partial receiver diagnostics](records/integrate3/partial-receiver-diagnostics.json) retain the unchanged
strict auditor's successful receiver/ingress checks before its full-Python assertion: each complete browser
artifact has **1,219 page + 139 adapter** independent 0/1/1 sequences, **3,481 sensitive-getter observations**,
zero forbidden Runtime value events and no password sentinel. Each invocation then exits **1** at
**“Full Python suite missing or failed”**. A diagnostic-only print before that assertion changes no check;
these three partial diagnostics are explicitly not full acceptance.

Reads now recover only Chrome's missing-receiver API rejection, by installing the passive ISOLATED reader/guard
on that exact committed native document. They neither navigate nor mark it preloaded; first-act guarded reload,
dirty/media/POST checks and password-history refusals remain. Injection and snapshot messages address native
document IDs so a navigation cannot associate a replacement's privacy identity with an old frame snapshot.
Control epochs are rechecked after an asynchronous read/recovery. Five browser-free regressions cover late
popup commit, navigation during enumeration, retained password-history refusal, a modal during blocked injection,
and Stop/re-take during injection. The full fixture and qualification-pair containers now allow **240 minutes**
inside **250-minute jobs**, keeping the exhaustive browser and Python stages sequential and every per-case
assertion/deadline intact. Three new page removal mutations cover recovery and both document-ID boundaries.
The extension APIs' document selectors are documented by Chrome's
[tabs API](https://developer.chrome.com/docs/extensions/reference/api/tabs) and
[scripting API](https://developer.chrome.com/docs/extensions/reference/api/scripting). No DevTools command,
MAIN injection, shared runtime or feature-removing refusal is added.

**Missing-reader final-source local verification (run):** the frozen runtime/test source at `8e73c52f` passes
the full local Python command above: **220 tests, OK, 1,335.928 s**. It includes writer sweeps **1,862 single /
1,862 persistent / 7,128 cleanup pairs**, dispatch sweeps **448 / 448 / 2,128**, all **nine actual process cuts**
and all **24 state removal mutations**. Node passes **243/243**, zero failures/cancellations/skips. The full page
audit rejects **114 mutations**, every baseline passing. Four of the five new focused regressions fail against
the unfixed code (the existing password refusal already passes); all five pass after the fix, including both
Stop and re-take variants. [Exact commands, exits, result lines, source/runtime and output hashes](records/integrate3/local-popup-summary.json)
index the retained [Python](records/integrate3/local-python-popup-frozen.txt), [Node](records/integrate3/local-node-popup.txt),
[page audit output](records/integrate3/page-mutations-popup.txt), [mutations](records/integrate3/page-mutations-popup.json),
[before](records/integrate3/popup-regressions-before.txt) and [after](records/integrate3/popup-regressions-after.txt).
All generated files were regenerated and checked again; `git diff --check` passes. The earlier overlapping
Python invocation also passes 220 tests in 1,398.366 s, but only the frozen-source run is used for this claim.
No browser ran locally. The two complete Linux attempts and their four independent audits are now finished, as recorded below.

## Combined closing verification (run)

Both complete attempts use `0ae4ac41`; the second is an **all-jobs rerun**, not a failed-job-only retry.
The one blocking `gh run watch 42989465778 --exit-status --interval 60` for each complete attempt ends **0**.
The first local watch was resumed after the Mac low-memory/network interruption; the Linux run itself continued
and passed. No additional Chrome runtime or CI fix was needed after `0ae4ac41`.

Browser package: **Google Chrome 157.0.8103.50** in all four artifacts. Each has zero Python/Node failures or skips.

| Attempt | Install | Named browser passes | Python tests / duration | Node passes | Protocol events | Sensitive-getter observations | Audit peak RSS MiB |
|---|---|---:|---|---:|---:|---:|---:|
| 1 | external | 80 | 220 / 2016.671 s | 243 | 26,817 | 3,481 | 166.7 |
| 1 | policy | 80 | 220 / 1604.174 s | 243 | 25,168 | 3,481 | 165.4 |
| 2 | external | 80 | 220 / 1202.306 s | 243 | 26,737 | 3,483 | 163.1 |
| 2 | policy | 80 | 220 / 1982.947 s | 243 | 25,196 | 3,481 | 165.3 |

Each artifact independently matches **1,219 page + 139 adapter** complete receiver sequences to the raw receiver:
zero arrivals before approval, one after approval, one after repeat, and exactly one final raw arrival per case.
All four scans find **zero** `Runtime.consoleAPICalled` / `Runtime.exceptionThrown` value events and **no**
password sentinel in reconstructed ingress, tool output or service output. Null protocol returns remain part
of the scan. The complete 80-name inventory and all qualification verdicts are required, with group 12's
explicit 18d deferral retained. Long-page reads cover 221,195–221,477 characters in 14 pages; measured times are
11,904–21,597 ms. These are observed fixture measurements, not estimates of real account performance.

The raw logs are 70–76 MB each. `audit-review-evidence.mjs` now reads JSONL and hashes incrementally through
`audit-streams.mjs`, preserving every prior named-case, receiver, fragment, privacy and full-suite assertion.
Four separate `node --max-old-space-size=192` processes run sequentially; `/usr/bin/time -l` records at most
**174,800,896 bytes (166.7 MiB) RSS**. The [five small reader tests](records/integrate3/closing/audit-streams-tests.txt)
pass with a 128 MiB heap, comparing the original fragment parser's output/errors, retaining nulls and UTF-8
boundaries, detecting a sentinel split across chunks, and matching the complete byte SHA-256. These tests and
artifact audits start no browser or container. The audit tool is checkpointed in `b0a32a93`; installed runtime,
CI assertions and test inventory remain those of `0ae4ac41`.

All four shared workflows also pass twice on `0ae4ac41`: base **142** tests per execution; Mail **142 base + 309
Mail** tests plus all four sweep shards; boundary **127 attacks** in each present/absent mode, with zero hostile
connections; qualification **47 Python + 243 Node** tests and genuine delivery-attestation verification. The
[shared results](records/integrate3/closing/shared-summary.json) retain exact commands' output lines and hashes.
Initial Mail dispatch `42989479000` was automatically cancelled by the following manual dispatch because its
workflow sets `cancel-in-progress: true`; it is excluded explicitly. Runs `42989483334` and `42993942180` then
complete successfully in sequence. No failed or cancelled execution is used as acceptance.

## Not verified / PLAN-GAP / JUDGMENT-CALL / open questions

Group **12** stays false until 18d's real normal/skip-permissions precedence harness. Owner Enter keeps the panel
boundary above. Synthetic fixtures do not verify real accounts, live signed-in sites, the installed image or the
owner's desktop; native-UI answering of a preexisting modal remains out of scope. The feature → tool → test and
group maps, measured views and image/18d/19b handoffs in the historical integration section below still describe
the retained implementation; historical run IDs are not acceptance for this combined head.
No new feature-removing refusal or open JUDGMENT-CALL is introduced by this cap. The snapshot decision belongs
to the lead and is settled. No new implementation question remains; the stated staged/panel boundaries remain.

## Runs / disk ledger

GitHub listed **168** Chrome run IDs on `pkg/20-chrome` before this run, including the lead's two cancelled
brief-only runs (`42953990307`, `42953996489`). The initial batched push added two failed combined runs (**170**).
The S12 fixture-consumer/base-test correction added another pair (**172**). The native-dialog readiness fix
added the third failed pair (**174**). The original user message and integrate-3 cap were about **175**.
The `0ae4ac41` report commit used `[skip ci]` to suppress duplicate automatic push/PR dispatches, then ran the
complete Chrome workflow manually once (**175**) and each shared workflow twice. No test command or assertion
was skipped in those manual executions. The marker affects automatic push/PR triggers only
([GitHub documentation](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/skip-workflow-runs)).

After a Mac low-memory interruption, the user explicitly authorized **at most ten more complete Chrome runs,
185 in all**, and restored shell network access. The first Linux run continued and passed; it was not restarted
because of the Mac event. The lead's pause-only commit `65ba456b` advanced the branch while that run was active.
The second dispatch's preflight stopped before launching on the wrong head. `gh run rerun 42989465778` then
reran **all jobs**, keeping the original `0ae4ac41` source as
[GitHub guarantees for reruns](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/re-run-workflows-and-jobs).
Attempts 1 and 2 have separate jobs and artifacts. The complete second attempt is charged as an additional run:
**176 / 185** using the user's 175-used resume baseline, even though GitHub retains one run ID for both attempts.
The lead's commit is preserved. The decision-24 threat-model/re-check work remains paused; no review was started.
The [closing API ledger](records/integrate3/closing/closing-run-ledger.json) counts IDs and executions separately:

| Branch | Workflow | Distinct IDs | Complete/attempted executions |
|---|---|---:|---:|
| `pkg/20-chrome` | `control-chrome.yml` | 175 | 176 |
| `pkg/20-chrome-state` | `control-chrome.yml` | 16 | 17 |
| `pkg/20-chrome-adapters` | `control-chrome.yml` | 6 | 6 |
| `pkg/20-chrome-qual` | `control-chrome.yml` | 5 | 5 |
| `pkg/20-chrome-qual` | `control-chrome-qualification.yml` | 10 | 11 |

The qualification branch's previously stated 15 run IDs comprise five Chrome runs plus ten qualification-workflow
runs ([qualification ledger](records/integrate3/closing/qualification-branch-ledger.json)); including its retry,
that is 16 executions. All side branches remain within their about-25 allowances. Main Chrome usage is
**176 / 185**, including the full second attempt. Each attempt was awaited by a blocking watch, not repeated
per-turn GitHub queries. No run belonging to another build was cancelled.

The [closing pre-push disk snapshot](records/integrate3/closing/work-inventory.json) lists **8,732 regular files / 5,148,720,908 bytes**
under `.work/`. **Files over 500 MB remaining: none.** Raw Linux evidence is retained once per artifact; there
is no ISO, extracted image, partial browser-package download or local browser profile from this build. No local
browser or container sweep ran during resumption. No Gradle daemon was started, and the task's local test and
blocking-watch processes have ended.

---

# Historical Part P review fixes: implementation acceptance green

**P1–P31 implemented.** Source `2488d2420f5c39f54e3503e1746992e028ebf145` passed the complete
**80-name suite twice in both install modes**, full P30 and all later cases included. Base, Mail, boundary and
qualification also passed twice on that source. [PR 27](https://github.com/Ares-Empire/AresOS/pull/27) stays draft
and unmerged; Part S is separate. **Owner Enter: passes in CI, panel to confirm.** Group 12 remains false until 18d.
The closing report/evidence commit must repeat this full acceptance set on its exact head; its final run links
are recorded on PR 27 without another commit that would change the verified head.

## Decided dialog rules — lead, 2026-11-10

**Already open before take: owner handoff, rule (a).** The initial Page-enable wait is bounded at five seconds.
If it cannot complete, the extension discards the pending target, detaches the debugger, and retains the tab's
control record and session state. Its result tells Claude exactly what to ask: **“Please answer the dialog yourself.”**
After the owner answers, a read reattaches and completes setup without restarting Chrome or resetting our state;
Claude's first act still follows the normal take-reload rule. A responsive Page domain may finish slower setup
without a false handoff. The impossible preexisting-dialog asking case and its red mandatory test are retired.
Native-UI answering is out of scope; nothing attaches to ordinary tabs outside the Claude group.

**Borrowed outside-native alert/confirm/prompt: ask, unguarded.** Authenticated native events without the private
wrapper's return token always produce a service-written question. It binds tab/control, type/text, chosen answer
and prompt text, and says its continuation is not held. Approval is mandatory and consumed before one answer call;
changed bindings and replay refuse. “Don't ask again” never covers it, including an otherwise matching adapter
confirmation. Any existing hold is preserved through the resumed handler and finished before collecting followups,
so this extension can ask more without clearing prior protection. Dropping leaves the dialog for the owner.

**Why the handoff is necessary:** [run 42840910762](https://github.com/Ares-Empire/AresOS/actions/runs/42840910762),
Chrome 157.0.8103.50, reached pending Page.enable command 1069 with an already-open modal and no opening metadata.
[Exact retained evidence](records/review-fixes-0894-preexisting-blocker.json) and the
[container screenshot](screenshots/review-fixes-preexisting-dialog-blocked.png) remain historical proof of that
failed asking attempt. In the [exact Chrome source](https://raw.githubusercontent.com/chromium/chromium/157.0.8103.50/content/browser/devtools/protocol/page_handler.cc),
`DidRunJavaScriptDialog` stores/emits only for an enabled Page domain (624); `Enable` does not replay an old modal
(680); the answer handler needs the retained callback (1792). These source observations explain the decided
handoff; they are not a current PLAN-GAP or JUDGMENT-CALL.

## Done and local verification

The [P1–P31 implementation/test map](BUILD-P-1.md), [feature-preserving iterations](BUILD-P-3.md), and
[current continuation](BUILD-P-5.md) name code, regressions, mutations and exact partial receiver evidence.
Ordinary native answers use the private return-boundary hold; blank/srcdoc reading and drafts use authenticated
inherited origins; selected native files are freshly SHA-256 hashed for each binding; shadow endpoints use the
outer native host plus a primitive path resolved in the isolated world. Runtime.enable remains absent.

Only plain Python/Node ran on this Mac. No local Chrome/Chromium or browser profile was accessed. Browser tests
run only in GitHub Linux containers through control-chrome. Current local Node: **229 passed**, zero failed,
cancelled or skipped. Focused Python: **49 OK**. The current full sweep is **189 OK, 244.571 s**
(`PYTHONPATH=control:control/chrome_tests python3 -m unittest discover -s control/chrome_tests -v`).
An initial invocation without PYTHONPATH failed to import test_bridge; the corrected complete run passed. The expanded mutation audit rejects **102 mutations**, every baseline passing.
[Exact mutation commands/assertions](records/review-fixes-mutations.json) include bounded handoff, detachment,
retained state/recovery, no false timeout after Page enabling, mandatory borrowed questions, exact answer binding,
no automatic confirmation/trusted exemption, exact-once dispatch and prior-hold completion. Generated artifacts
match; diff checks are clean. A further P23 regression observes the actual page after an outside-native answer.
Native dialogs from inherited editor frames now join CDP and webNavigation identities through the authenticated
private document, with inherited read-only checks.
The latest borrowed-native regression also covers message/default object conversion: conversion finishes before
a private dialog token exists, so a nested borrowed dialog cannot inherit the outer call’s authority. Native
string hints, defaults, ignored extra arguments, return values and thrown identities have regressions. All ten
borrowed browser variants and all six blank/srcdoc native cases passed in each of the four completed Linux jobs.

## Complete Linux acceptance on 2488d242

[Push 42915282247](https://github.com/Ares-Empire/AresOS/actions/runs/42915282247) and
[PR 42915293661](https://github.com/Ares-Empire/AresOS/actions/runs/42915293661) are green, external and policy
installation in each. Every job passed **80/80 exact names**, all core/adapter verdicts and groups 1–11/13;
group 12 is explicitly false. Every job also passed **189 Python** and **229 Node** tests, zero Node
failures/cancellations/skips. [Exact names and one-based PASS lines](records/review-fixes-2488-test-index.md),
[completed source/job metadata](records/review-fixes-2488-runs.json),
[independent artifact audit](records/review-fixes-2488-audit.json), and
[receiver arrival rows with URL, method, timestamp and body SHA-256](records/review-fixes-2488-summary.json)
retain the evidence. Raw receiver, ingress, tool and service files remain in each named workflow artifact,
with their SHA-256 digests recorded by the audit.

| Run / installation | Named cases | Python output | Node |
|---|---:|---|---:|
| 42915282247 external | 80/80 | 189 OK, 790.691 s | 229/229 |
| 42915282247 policy | 80/80 | 189 OK, 786.981 s | 229/229 |
| 42915293661 external | 80/80 | 189 OK, 1065.794 s | 229/229 |
| 42915293661 policy | 80/80 | 189 OK, 631.514 s | 229/229 |

**Receiver audit:** `node reviews/20-chrome/audit-review-evidence.mjs <downloaded-artifacts>` passes all four
artifacts. Each has **1,219 page + 139 adapter approval sequences**, all 0/1/1, with every retained arrival
matching the independent receiver and each final receiver count exactly one. It also requires the exact
inventory and verdicts, the full Python/Node outputs, and fragment-safe ingress completeness. It rejects the
retained 76-pass trial. The old helper's 77 count described that failed trial's executed prefix; the complete
inventory is 80, including the final actual Stop, crash-cutpoint and no-listening-port cases. No missing case
is counted as passing.

**P30:** all document/open-shadow/closed-shadow/cross-site password variants exercise read, read_form,
preparation and final binding, with release/retake and sticky-password transitions. Each artifact retains
3,481–3,483 sensitive-getter records and 25,173–26,782 protocol events. The independent scan reassembles all
fragmented ingress (140,591–142,200 rows), including legitimate null results: **zero Runtime console/exception
value events and no password sentinel** in browser ingress, tool replies or service output.

**Late and feature-preserving cases:** all 15 Claude/owner/task native combinations, six inline-native cases,
three bounded owner handoff/recovery cases, ten borrowed-native variants (direct, argument conversion and
changed dialogs), four ordinary/stale inline editors, actual chooser/backing-file byte replacement, both new
shadow matrices, frozen-wrapper Stop, inactive no-ops, media/dirty reloads, script POST tabs/popups, full catalogue
paging and the final three whole-suite cases passed in all four jobs. [P1–P31 map](BUILD-P-1.md) links every fix
to regressions/removal mutations; the exact browser line for each named matrix is in the index above.
The installed runtime hash is `117dc34ebc93455ce47ca79d187fc5c7e5107ad130e6e5eb1e615a0c885e91c7`.

**Partial Linux evidence; whole runs failed:**

| Source / runs | Successful evidence and stopping failure |
|---|---|
| `d5cdde7d`, 42830213180 policy | [15 ordinary native answers and four inline-editor cases, raw receiver 0/1/1](records/review-fixes-d5cd-native-editors.json); chooser driver failed. |
| `76f9b5cf`, 42831333350 policy | [Native chooser, changed selection refusal and fresh 0/1/1](records/review-fixes-76f9-chooser.json); cross-tab fixture used an invalid pending limit. |
| `651096b2`, 42832298611 external / 42832312713 policy | [Actual backing-file mutation with restored timestamp, exact digest questions, refusal at zero and fresh 0/1/1](records/review-fixes-6510-native-file.json); retake found stale cleanup contexts. |
| `ace83b8e`, 42833507627 / 42833520319 | Native missing-context proof fixed cleanup; cross-tab and pay/delete override cases passed; [shadow handoff failed](records/review-fixes-ace8-shadow.json). |
| `02f523d3`, 42839228786 / 42839244624 | [Both new shadow matrices passed, with raw receiver rows](records/review-fixes-02f5-shadow.json). Review key/word/URL, binding, exact owner mark, reload/media, script POST and focus matrices passed. Frozen cleanup owner-driver wait failed. |
| `3f1af5b2`, 42889458048 / 42889469858 | [77 of 80 names executed; 76 pass, including P30](records/review-fixes-3f1-late-catalogue.json). Full catalogue history paging reaches 732 of 877 items before its absolute five-minute snapshot expires. Active cursors now renew the immutable snapshot; five idle minutes still expire it. The strengthened case requires every item exactly once. |
| `de337c55`, 42870158864 / 42870172304 | [The retained policy job passes 60 of 61 executed names](records/review-fixes-de3-p30.json), including all native and context-sensitive adapter cases. P30 completes its browser operations, then its scanner dereferences a legitimate null audit result; the corrected offline scan finds no sentinel or forbidden Runtime events. Push-external reaches the 105-minute container cap while still progressing through P30. The scanner is fixed and the whole-suite allowance is now 155 minutes; all individual assertions/deadlines stay strict. |
| `25263559`, 42864982361 / 42865000405 | [Six inline-native cases and the complete cross-site mismatch matrix pass](records/review-fixes-252-context-reuse.json). Whole runs fail when reused numeric renderer contexts retain old private records, leaving some new documents without readers. The root-navigation retirement and startup identity checks now have overlap/reuse regressions and three removal mutations. |
| `2d2c728e`, 42849298252 / 42849536082 | [Both modes pass the 15 ordinary dialogs, bounded owner handoff/recovery, borrowed-native questions, every review matrix and frozen-wrapper cleanup](records/review-fixes-2d2-dialog-decisions.json). Whole runs fail at cross-site native confirmation guard lookup; Gemini also failed; the next trial independently diagnosed a reused context number. The lookup now uses the authenticated opener document rather than the root event target. |
| `0894243b`, 42840910762 / 42841180213 | Ordinary native matrix passed; mandatory preexisting-dialog case failed during take. [Exact pending protocol command, zero receiver and failed row](records/review-fixes-0894-preexisting-blocker.json). |

CI was awaited with one blocking `gh run watch --exit-status --interval 60` command per latest run; failed logs
were read after completion. No missing or failed named case qualified. Group 12 remains false until 18d.

## Shared workflows verified twice on 2488d242

[Exact run metadata, artifact paths and one-based output lines](records/review-fixes-2488-shared.json):
base 42915293611 / 42915922398 (**142 tests** each); Mail 42915293687 / 42916012876
(**142 base + 309 Mail tests**, all four sweep shards each); boundary 42915293786 / 42916096946
(**127 native + 127 broker attacks in each seccomp mode**, zero hostile connections);
qualification 42915293644 / 42916179264 (**47 Python + 229 Node tests** each).
All eight workflows completed successfully. These ran through one blocking watch per workflow; no failed log
was read before completion. The earlier [de337c55 repeats](records/review-fixes-de3-shared.json) remain historical.

## Not verified / review boundaries

Owner Enter **passes in CI, panel to confirm**; the lead's panel reviews its receiver/binding angles.
Group 12 remains false until 18d supplies the real normal/skip-permissions precedence harness. Real accounts,
live signed-in sites, native-UI answering of a preexisting modal and production qualification were not used.
Part S's independent state changes are not integrated here. The closing immutable-head repeat is recorded
with its exact run links on PR 27; the table above identifies the verified implementation-source artifacts.

## Ownership, runs and remaining decisions

Only Part P files and this worktree changed; Part S's branch/worktree, state implementation/tests and Mail filing
remain untouched. The previously named minimal shared adapter lines in read()/check_readonly() use the inherited
frame's authenticated effective URL and must survive integration. No branch was merged or force-pushed. The
privacy hook ran normally. Only this build's superseded runs were cancelled; no owner/lead run was cancelled.

The earlier closing runs 42843419421 / 42843914061 are both completed failures on the superseded asking path.
The implementation-source ledger is **164 Chrome workflow IDs**, including cancelled IDs; the closing report
push is expected to add two (**166**, below the approximate 175 limit). All named workflows are awaited with
one blocking `gh run watch --exit-status --interval 60` per run; completed failures alone have their logs read.
Before the closing push, `.work/` contains **3,977 regular files, 2,618,296,875 bytes; no regular file exceeds
500 MiB**. There are no downloaded ISO/image layers or local browser profiles. No Gradle daemon was started.

Both open native-dialog policy choices are now decided. Genuinely unreachable guard/frame coverage still fails
closed under the brief; ordinary editor/dialog cases must pass. No new feature-removing fallback is approved.
No JUDGMENT-CALL is introduced by these decided rules. There is no unresolved Part P implementation decision;
the review boundaries above remain explicit.

The report below is historical integration evidence, not acceptance evidence for this fix round.

---

# 20 — integrated Chrome Now

**Run — Now integration is green twice on source `ab7aba92`**, external and policy installations, with all 61 named Now cases covering groups 1–11 and 13 plus support checks. Group12 remains false until 18d supplies its real harness. **Owner Enter: passes in CI, panel to confirm.** Draft [PR #27](https://github.com/Ares-Empire/AresOS/pull/27) remains unmerged on `pkg/20-chrome`. No browser/profile on this Mac was started, read or touched. Local tests were plain Python and Node; every browser observation below comes from the control-chrome Linux containers. The closing commit contains reports, retained evidence and its read-only auditor; the runtime, CI harness and generated files match this verified source.

## Done

**Read — scope:** fetched origin/main and read integrate-2, integration, continue-3, continue-2, continue and parallel-start briefs in that precedence order, then the three branch reports. Read AGENTS, brief 20, brief 19b, CONTROL §§3/4/6/7, FEATURES, PLAN, rechecks29–34 and workflow/review guidance using `git show origin/main:<path>` (main `ead8e648`). The lead's two side-build merges were already present. No branch was merged here. The original [adapter report](ADAPTERS-REPORT.md) and [qualification report](QUALIFICATION-REPORT.md) are retained unchanged; their implementation maps are [ADAPTERS.md](ADAPTERS.md) and [QUALIFICATION.md](QUALIFICATION.md).

**Read — shared adapter sentences:** `chrome/adapter.py` carries the service-recognized semantic action into the immutable description. A page cannot choose the action by adding a kind to its reader data. Gemini says “Gemini: ask a question”, with its full text; Gmail says send a mail or delete the selected message for inbox #. Questions include the displayed attachment count, names and sizes, account, To, Cc, hidden Bcc, subject and text length. Original content remains bound in full, escaped and subject to the existing whole-input bound. The three side-build wording tests are unchanged.

**Read — qualification verdicts:** `ci/verdicts.mjs` registers every new group 4/10/11 fixture name, plus both new group 8 popup matrices. An exact inventory test rejects omitted, duplicate, nonboolean or unknown evidence. Adapter-specific failures disable that adapter; shared prerequisites disable their dependents. An adapter-only GitHub confirmation failure does not disable the generic confirmation/binding rule. The dependency audit found that combined alias and shortcut matrices incorrectly gated unrelated adapters: a new regression failed on Gmail after the alias matrix failed. The fix gates only GitHub/Gemini/Deezer for aliases, and Gmail/WhatsApp/Gemini for shortcuts; incomplete combined coverage stays disabled for those dependent sites. The all-sites fallback matrix and genuine core/owner prerequisites still gate all their dependents. [Original regression failure](records/integration-verdict-subsets-red.txt) is retained; the complete corrected Node suite passes. Group12 is explicitly false until 18d supplies its real precedence harness; pair ingestion therefore cannot turn this Now evidence into production qualification. No fabricated shipped build or passing record was added. A one-line integration change to side-owned sites/matrices.mjs attaches its completed in-memory rows to its unchanged strict AggregateError; the shared collector preserves those failures in the final full matrix. No assertion or final failing exit was waived. Crashes/incomplete evidence still refuse.

**Read — qualification side build retained:** the [53-row requirement map](QUALIFICATION.md) covers exact stable/beta package lookup, newest-three actually shipped runtimes, each runtime's pinned hasher, complete pair accounting, signature/identity verification and append-only publication/delivery. Runtime identity includes installed command wrappers. Recorded failures survive channel changes until a higher patch passes later in immutable history; a recorded major cannot fall back to conservative mode. Fetch, verifier and malformed/history failures retain the last held state safely. An unrecorded major uses conservative asking, with read-only restrictions and password exclusions still enforced. The empty build registry and qualification record are intentional: an image shipment and real group 12 evidence must precede production qualification.

**Read — H1/H2, unit fixed here, live check in brief18c:** the unit now permits only `AF_UNIX AF_INET AF_INET6` and no longer has `IPAddressDeny=any`, as the lead decided for Mail IMAP/SMTP and daily HTTPS qualification delivery. Every other service line is pinned unchanged by `test_unit.py`, including User/Group, launch environment, UMask, NoNewPrivileges, strict ProtectSystem, ProtectHome, PrivateTmp, PrivateDevices, empty capabilities and all three writable paths. Verified TLS, transport/record/bundle bounds and offline refusal behavior are unchanged. The image must install **GitHub CLI 2.102.0 or later**, pinned by its image dependency policy: this is the already-used supported verifier with genuine-signature/minimal-environment evidence, so adding Sigstore's Python dependency tree is unnecessary. No software was installed here. Keep fetched records and `qualification-verifier-cache/config` private under `/var/lib/aresos-tools`; no owner login/token is required.

**Read — popup rule, decided by the lead:** a native [onCreatedNavigationTarget notification](https://developer.chrome.com/docs/extensions/reference/api/webNavigation#event-onCreatedNavigationTarget) admits only a child of a currently controlled opener. Opener epoch and actual membership are rechecked across admission and before reads/actions. Leaving the group, releasing, closing or stopping the opener ends child authority. Ordinary openers are untouched. Popup windows stay in their original window and type; they are never moved, reparented or put in a native tab group. Membership is the extension's private record. **Decided rule (lead, 2026-11-10): nothing of ours opens a window or takes focus.** The normal opener's pinned toolbar button shows **POP**, distinct from ordinary controlled-tab **ON**, with the controlled popup count in its tooltip. The owner opens its existing action popup, which lists every controlled popup by title/address with an individual **Stop**. That Stop ends control at once without closing, reloading, moving, resizing or reparenting the page popup. The original all-tabs Stop remains available. An unrelated/manual popup can be taken only when its native opener is currently controlled; it binds that opener's epoch. Opener close, native group departure and release revoke children and clear the badge without waiting for another tool read. Serialized badge writes cannot resurrect old popup status after Stop. Owner movement to another native window ends popup control. Normal new tabs use the visible Claude tab group.

**Read — reload behavior:** taking/reading a tab or popup preserves its document, edits and media. Its first act performs one guarded GET reload and returns stale_reference: every old reference must be reread. Unsaved values/editable content or playing media report reload_required without reloading; only a repeated call with `reload_taken_tab=true` permits it. A POST/non-GET/unknown-method document refuses with “open its address fresh in a Claude tab”. Form-target popups refuse even when the form used GET. Native document/loader identity and a final recheck guard the reload; Page.reload preserves the opener relationship. Metadata records only navigation method/document/form-transition facts, never request bodies/headers or interception. Popups always cross this first-action boundary, even if their initial navigation happened to receive a startup guard. These are decided rules, not PLAN-GAPs or new JUDGMENT-CALLs. They supersede the old continue-3 popup startup stop; no pre-first-script popup injection is claimed.

**Read — controlled-only startup and fixed DevTools additions:** ordinary tabs retain only inert ISOLATED context.js, with no MAIN/prototype mutation or cancelling listener. Controlled documents pause on the exact extension bootstrap URL; fixed guard/reader/page bundles install in authenticated native contexts and resume before page scripts. OOPIF startup uses recursive iframe-only auto-attach. Private guard state, identities and allowances remain isolated/service-only. The approved additions retained from continue-3 are `Runtime.enable`, `Runtime.evaluate`, `Runtime.callFunctionOn`, `Runtime.runIfWaitingForDebugger`; `Debugger.enable`, `Debugger.disable`, `Debugger.setBreakpointByUrl`, `Debugger.resume`; `Target.setAutoAttach`, `Target.detachFromTarget`; `DOM.describeNode`, `DOM.resolveNode`; `Page.getFrameTree`. Runtime evaluation accepts fixed extension bundles/restoration code only, never caller or page source; DOM describe/resolve links only the extension's detached private carrier. The disposable Browser-target diagnostic commands were never added to production. This integration adds no DevTools method.

**Read/run — fresh delta reviews:** [sol high review](BUILD-INTEGRATE2-REVIEW.md) and [astra security review](BUILD-INTEGRATE2-SECURITY.md) found the native-window backup setup risk and orphan manual-popup admission. Both were fixed before the source push, with the new opener regression included in the complete148-case Node pass. Runtime build hash: `e4030361b4d50170f3c0a11d915954519257ca4a7911862586225cdc99034c72`. These reviews cover this delta; package review/panel acceptance still follows.

**Read — CI transport:** exact package metadata and SHA256 checks remain required. Setup now retries transient metadata/download transport failures with bounded attempts/timeouts. A connection reset in source `67d3cb46` external setup is retained as a pre-browser failure, not acceptance evidence. The integrated qualification test also exposed a missing workflow file in the Docker archive; both fixture and qualification-pair contexts now include the driver workflow. Its strict main-only/publication assertion is unchanged, and the unchanged Workflow test passed in a fresh exact archived context. A first context probe selected the Mac system Python 3.9 and failed on existing type-union syntax; the passing probe uses the active Python 3.14 executable. This environment failure is not counted as verification. The qualification-pair changes are the workflow context and complete-suite allowance; they do not change the installed runtime.

**Read — retained implementation:** replaceable native-compatible wrappers, private carrier identity/verdicts and owner-task handling; password exclusion before every value read in every root/frame; full local binding and native/event resume kinds; exact confirmations; owner-only exclusions/read-only/allow lists; immutable upload staging; paging; R1–R3 operation context, journal-derived warnings, occurrence acknowledgements and no automatic replay. The base native-host selector repair remains. Side-build sites.py and qualification implementation are retained. H6 production mutation remains main-only; branch publisher tests use a runner-local repository/stub notifications only.

## Verified

**Run — local browser-free:** `PYTHONPATH=control:control/chrome_tests PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s control/chrome_tests -v`: **171 tests, OK, 224.896s**. Writer sweep1167 single/1167 persistent/3153 cleanup pairs; operation sweep 446/446/1605, with restart/space-restored evidence and an independent committed-record oracle. The initial invocation omitted PYTHONPATH and had one import error; its loaded tests passed, but that invocation is not counted as green. The corrected complete command above is the evidence. `node --test control/chrome_tests/*.test.mjs`: **148 tests, 148 pass, 0 fail, 6047.634917 ms**. Exact browser-free outputs: [Python](records/integrate2-python-ui.txt), [Node](records/integrate2-node-final.txt). `python3 control/generate.py --check` prints `Generated artifacts match definitions`; `git diff --check` and fixture/source syntax checks pass.

**Run — Linux, twice at the final source:** [push 42773242428](https://github.com/Ares-Empire/AresOS/actions/runs/42773242428) and [PR 42773249076](https://github.com/Ares-Empire/AresOS/actions/runs/42773249076), Google Chrome **157.0.8103.50**, both external and policy installation. All four jobs pass **61/61** named cases, all core/adapter verdicts true and only staged group 12 false. [Every exact test name and one-based PASS line](records/integration-test-index.md), [matrix/measurement summary](records/integration-summary.json) and [run/source/job metadata](records/integration-runs.json) are retained. Each job also passes171 Python tests (720.207s/682.283s/560.114s/712.744s in push-external/push-policy/PR-external/PR-policy order) and148 Node tests, zero failures/cancellations. Their retained python.txt L177 and node.txt L891/L893–895 give the exact outputs.

**Run — independent receiver audit:** `python3 reviews/20-chrome/audit-evidence.py 42773242428:external 42773242428:policy 42773249076:external 42773249076:policy` passes all four retained datasets. [Exact audit output](records/integration-receiver-audit.json): each has 135 complete adapter0/1/1 sequences and 20 independent free-dialog sequences, matching the raw receiver; unchanged popup document token/draft/name/opener and exact native windows across Stop; one initial load, zero later Claude inputs; exactly one POST request. Native test assertions additionally compare the focused X11 window. Closing/releasing the opener clears authority and badges; clean/dirty reloads preserve the postMessage flow; ordinary openers stay untouched. No extension control window opens.

**Run — H3:** `QUALIFICATION conservative activations ask and core failures gate before reads` passes in all four matrices, with CONSERVATIVE RECEIVER0/1/1 log lines and the independent receiver retained alongside each browser.txt. It covers generic mail/existing owner allowance, links/ticks/lists/Enter/Space/GET search, ordinary forms, both stopped-submission resume kinds, free read/scroll/type/address navigation, read-only refusals, notices and password exclusion across roots. Missing/throwing safety-property checks additionally run the actual reader in the Node VM; those are not presented as native-browser observations.

**Run/read — earlier failures retained, not acceptance evidence:** Source95946b96 ran all 61 named cases in all four jobs (push 42762217677, PR 42762223715):59 passed in each. [Exact case/line index](records/95946b96-integration-test-index.md) retains both failures: the new Stop focus baseline preceded the owner opening the toolbar UI, and the next POST case used an undefined tab after the backup ID was read from the wrong response field. The corrected Stop baseline follows owner opening, retains exact window-list comparison and adds native focus-ID equality. The backup now requires open’s untrusted_content.tab before the opener closes; invalid replies refuse before closing. Three new browser-free helper regressions pass. The UI also reports a refused stale Stop as changed control and refreshes an enabled Stop for the current epoch. No receiver, binding, timing or replay assertion was relaxed. The first source `5b3fd1a2` qualification run 42761520495 found a browser-free test waiting on an unreferenced timer, cancelling 6 Node cases before browser acceptance. [Exact failing lines](records/integrate2-qualification-node-red.txt) are retained. The test now advances its explicit clock, verifies bounded cleanup_pending while authority is gone, then explicitly restores cleanup; all original assertions remain. The focused test and full144-case suite pass locally. Superseded push 42761513712/PR 42761520748 and queued qualification repeat42761660738 were cancelled; no missing browser case is counted as a pass. Source9ad79254 push 42737850126 external completed 56/59; its policy and both PR 42737857384 modes hit the 85-minute container allowance while still progressing. [Exact earlier results/missing-case index](records/9ad79254-integration-test-index.md) preserves every failure and absence. The completed job failed initial unmapped page geometry0×0 versus mapped620×514, a recovered opener captured by the next popup case, and an owner-navigation helper selecting the first tab after release restored its index. Native-window/X11 identity and mapped geometry now replace the invalid zero baseline; popup cases read the current recovered opener; existing tabs results expose window/index/active/focused metadata so independent owner UI keys select the exact tab and verify its address. The original receiver assertions are unchanged. The complete suite allowance is now 105 minutes (job 115), with all individual assertions/timeouts unchanged, and only the disposable container hostname is mapped locally to remove repeated sudo DNS delays. No journal/cache/acknowledgement policy changed. The browser-free cache profile was diagnostic only (80 unknowns, unchanged journal/page); a larger cache did not improve it and was not implemented.

Cancelled/superseded runs 42734373173/42734379065 did not reach a completed native matrix; no missing case is a pass. Their retained partial outputs show Python fault sweeps only. The other pre-browser failures/cancellations are retained in [the preflight ledger](records/integration-preflight-failures.json). Earlier complete ac75 and side-build runs remain historical, never substitutes for this integrated head.


**Run — shared workflows, exact source `ab7aba92`, twice:** base [42773249103](https://github.com/Ares-Empire/AresOS/actions/runs/42773249103) and [42773419743](https://github.com/Ares-Empire/AresOS/actions/runs/42773419743) are green,142 tests each (203.191s/234.544s). Boundary [42773249067](https://github.com/Ares-Empire/AresOS/actions/runs/42773249067) and [42773427454](https://github.com/Ares-Empire/AresOS/actions/runs/42773427454) are green,127 native plus127 broker attacks in each seccomp mode, zero hostile connections. Mail [42773249404](https://github.com/Ares-Empire/AresOS/actions/runs/42773249404) and [42773424001](https://github.com/Ares-Empire/AresOS/actions/runs/42773424001) are green,142 base plus309 Mail tests and all four sweep shards in each run (Mail 844.562s/782.114s; longest shards1073.167s/1327.078s). Qualification [42773249660](https://github.com/Ares-Empire/AresOS/actions/runs/42773249660) and [42773431424](https://github.com/Ares-Empire/AresOS/actions/runs/42773431424) are green,47 Python and148 Node tests each. The manual repeat verifies genuine new and retained attestations, every altered-copy/history refusal and anonymous launch-equivalent verification (both caches 61925 bytes), without production publication. [Exact completed log summaries](records/integrate2-shared-summary.json) retain one-based lines and original output. Earlier95946b96/e229d58c/9ad shared passes remain historical; they are not substituted for this same-source repeat.

**Run/read — owner Enter review boundary:** all four CI matrices pass its strict cases: **“passes in CI, panel to confirm”**. The review panel must check the receiver log from its injection and binding angles before closing it. The private MessageChannel/exact form+submitter/native-default checks retain strict owner, delayed, replay, in-flight and timer-repair assertions.

## Groups and feature → tool → test map

**Run/read:** the [final named-case index](records/integration-test-index.md) gives every exact name, run/mode and PASS log line. Group12 remains a stated gap. The inventory consists of groups 1–11 and 13 plus FEATURE, VIEW and conservative qualification support cases.

| Section6 group | Required evidence |
|---|---|
|1 What asks|Unicode agreement; full word/label/key matrix; submit/compose/deletion/free-input matrix.|
|2 Stopped page steps|Handler/resume kinds; script activation no replay; enclosing-submit loop; owner synchronous/delayed/in-flight; timer/default/invalidity; nested validation/fresh-native fallback; slow arming; source-navigation unknown; top/same/cross-frame first-script guard.|
|3 Binding|Every form fact and generic sibling draft; cross-frame/adapter/empty/oversized drafts.|
|4 Confirmations|Page full text; exact native/mismatch; native-dialog handler submission; every named GitHub mismatch.|
|5 Question matches page|Hidden/password-presence fields; upload real path/hash/exact received bytes; strict adapter semantic/attachment sentences.|
|6 Where Claude may go|Frame/popup/redirect/take/history exclusions; schemes/links/forward routes.|
|7 Isolation|Every password kind in open/closed/cross-site roots; no port; native compatibility against Chrome without extension; private forgery receiver0/1/1.|
|8 Control/cancelling|Drop/release/close/staleness; actual popup Stop; opener POP badge, individual Stop, unchanged document/windows/focus and opener close/release; deadlines/outside tabs; taken reads/reload/dirty/media/POST; modal cleanup; native popup opener/reload/no-move and POST/ordinary-opener cases.|
|9 Crashes/restarts|All nine Chrome/host/service cuts; no replay, unknown where input may have run.|
|10 Adapters|All six original and expanded matrices, variants, fallback and the three unchanged strict wording cases.|
|11 Don't ask again|Generic exact owner kind/recipients/account/revocation; complete Gmail To/Cc/Bcc/widening; exact Gemini account/revocation.|
|12 Managed ask rule|**Not run; false.** Requires 18d's actual normal/skip-permissions precedence harness.|
|13 Residual shown honestly|Autosave/after-limit; baseline ordinary-click fetch is observed, not held. Read-only previews are now bound (recheck-2 above).|

| FEATURES Chrome row | Tool/path | Named coverage / limitation |
|---|---|---|
|List titles and addresses|tabs|FEATURE browser tools; group 8 tabs outside group|
|Take and give back an owner tab|take_tab, release_tab|GROUP8 taken tabs preserve reads; guarded reload; release/stale references|
|Open and close Claude tabs|open, close_tab|GROUP8 drop release close and stale references|
|Back/forward/reload/web address|navigate|GROUP6 schemes links and forward routes; GROUP8 POST/history refusal|
|Paged structure, positions, search|read, find|VIEW long page; FEATURE browser tools|
|Form with all options|read_form|FEATURE complete select options and form paging|
|Cross-site frames, shadows, page dialogs|read|GROUP7 password roots; GROUP3 cross-frame binding; GROUP4 confirmations|
|Click/type/select/check/keys/scroll|click, fill, select, check, press, scroll|FEATURE browser tools; GROUP1 word/label/key matrix|
|Whole form|fill_form|FEATURE browser tools; GROUP1 free inputs|
|GET address search|fill, press|GROUP1 submit compose deletion and free-input matrix|
|Form/button/field/script submission|input then submit|GROUP1/2 resumes; GROUP3 binding; GROUP5 question fields|
|Listed send/buy/delete controls|input then submit|GROUP1 word/label/key 972 variants and Unicode 3 cases|
|Compose Enter/Ctrl+Enter/Cmd+Enter|press then submit|GROUP1 compose keys; GROUP10 adapter shortcuts|
|Delete/Backspace outside editing|press then submit|GROUP1 deletion/free-input matrix|
|Unlabelled local deletion|ordinary click|Residual: accepted free action; not claimed held|
|Page-script control activation|private guard|GROUP2 activation/no-replay/fallback; guarded popup reload follows the decided rule|
|Autosave/icon/typing/read receipts|ordinary input|GROUP13 autosave/after-limit and preliminary residual fetch; not held|
|Alert/confirm/prompt|dialog|GROUP4 native exact/mismatch and second-dialog matrices|
|Local file upload|upload then submit|GROUP5 exact path/hash/bytes; Python immutable staging faults|
|Download paths|downloads|FEATURE paged catalogues; native detached download comparison|
|Find bookmarks/history|bookmarks, history|FEATURE complete two-item catalogue continuations|
|Drop preparation|drop|GROUP8 drop/release; GROUP9 no replay|
|Owner kind allowance|submit_trusted|GROUP11 exact owner kind/recipients/account/revocation|
|Owner allow/revoke/read-only lists|sites, details/admin|GROUP10 bank/read-only; GROUP11 owner-channel checks|
|Page popups/new tabs join group|native creation event + private membership|GROUP8 popup opener/reload/POST/outside matrices|
|Owner sign-in|owner_signin, safe reader|GROUP7 password kinds and lazy getter/transition tests|
|Payment/order/transfer|input then submit|GROUP1 asking labels; GROUP11 never trusted pay/delete|
|Popup Stop|opener POP badge, action popup with individual Stop|GROUP8 per-popup Stop/document/focus, opener close/release, actual global Stop and modal cleanup|
|Calls/Safe Browsing/extensions/updates|normal Chrome|Native fixture comparisons only; real coexistence remains unverified|
|Six adapters and first actions|site adapters|GROUP10 six adapter matrices and shortcuts; integrated ADAPTER matrices|
|Mail compose send|adapter then submit|GROUP10 mail compose; GROUP11 exact recipient trust|
|Message send each time|adapter then submit|GROUP10 message/chat binding and shortcuts|
|Bank read-only|read/scroll/link policy|GROUP10 read-only bank|
|Question text/account|adapter then submit|GROUP10 question account/text; GROUP11 exact trust|
|Playback/library/removal|ordinary actions or submit|GROUP10 playback/library adapter and shortcut matrix|
|Never: settings/self-approval pages|safeURL/private exclusions|GROUP6 frame/popup/redirect/take/history exclusions|
|Never: cookies/password/storage|safe reader/fixed command list|GROUP7 password kinds; no generic storage/AX/DOM snapshot command|
|Never: screenshots as main read|structure-only reader|FEATURE/VIEW structure; screenshots are CI inspection artifacts only|

**Read:** [TOOL-DESCRIPTIONS.md](TOOL-DESCRIPTIONS.md) exports all 28 generated descriptions exactly, with SHARED separately liftable into 18d. The shared suffix includes first-input reload, explicit repeat and popup membership/badge behavior. It remains verbose until 18d removes repeated shared/base text; no stand-in MCP instructions were built.

## Measured views / screenshots

**Run:** the representative long article/form fixture has 120 paragraphs and 80 fields. All14 pages are read completely, each at most 16000 tree characters. Figures below are from each final view-measurements.json, not earlier builds. UTF-8 bytes equal the listed character count in these synthetic pages. Tokens are characters / 4 rounded up, an estimate rather than a tokenizer measurement.

| Run / mode | Characters / UTF-8 bytes | Pages | Read ms | Estimated tokens |
|---|---:|---:|---:|---:|
| 42773242428 external | 221477 | 14 | 8716 | 55370 |
| 42773242428 policy | 221195 | 14 | 8783 | 55299 |
| 42773249076 external | 221477 | 14 | 6915 | 55370 |
| 42773249076 policy | 221195 | 14 | 11536 | 55299 |

**Run/read — screenshots inspected:** [native popup after guarded GET reload](screenshots/integrate-42773242428-policy/popup-clean.png), [dirty popup after the explicit repeat](screenshots/integrate-42773249076-policy/popup-dirty.png), [opener POP badge and per-popup Stop list](screenshots/integrate-42773242428-policy/popup-controls.png), [Stop finished, opener ON and popup kept open](screenshots/integrate-42773249076-external/popup-stopped.png). Native X11/window metadata and receiver probes provide the identity/focus/no-reload evidence; screenshots are visual inspection, not that proof by themselves. All four datasets retain their own popup and Stop screenshots.

## Not verified

**Read:** group 12 and slim MCP generation wait for18d. Installed service-unit networking, gh installation/private cache and launcher-to-delivery checks belong to brief18c (H1/H2: unit fixed here, live check in brief18c). Genuine signatures and minimal-environment verification test the components, not the installed image. Main-only stable/beta pair planning/observer/publication (H6) cannot mutate production from this branch; its hermetic and attestation tests remain the branch evidence.

**Read/assumed:** live signed-in sites/layouts, real accounts, owner desktop extensions/calls and laptop integration remain the designed after-boot owner checks. Known GitHub confirmation templates are fixed adapter plans, not templates learned after approval. Unknown templates classify separately. No real site/account was used, and no synthetic pass is presented as live compatibility.

## PLAN-GAP

**Read — 18d:** group 12 has no real precedence harness on this branch, and stays false. Qualification remains off until that evidence is integrated. This is the staged Now boundary, not a fabricated pass.

**Read — residuals stated by section 6:** direct fetch/autosave/read receipts, unlabelled local deletion, address-carried data, sends after 500 ms remain outside the hold guarantee. Generic visible compose text is now bound, and the tested borrowed-native defaults stop before sending (recheck-2 above). Activations never resume. Borrowed native form-submit from a fresh realm remains separately disclosed in the earlier report; no universal interception/impossibility claim is made here. Same-user host substitution/direct tool calls remain decision 24's accepted user capability.

## JUDGMENT-CALL

**Read:** exact displayed Gmail recipients keep To/Cc/Bcc roles separate, using quote-aware sets rather than guessed mailbox normalization. Ambiguous/group notation is not trusted. Gmail kind version 2 suspends old entries; a future change needs a new kind hash and recipient regressions.

**Read:** confirmation plans are fixed per modeled adapter action/context; unknown labels/dialogs do not inherit approval. Broader live coverage needs the deferred owner check and specific fixtures.

**Read/run:** qualification failure recovery requires a higher patch and later immutable publication evidence across beta/stable; same-version channel changes cannot erase a failure. Runtime hashing includes installed command wrappers; shipped builds retain their own pinned hasher. A policy/hasher change requires sequence/identity migration tests. Missing group 12 or unbound/incomplete pair evidence disables qualification.

**Read:** blocked cleanup retains visible pending control until native restoration or actual context destruction; input authority ends immediately. The safe fallback for a detached live blocked target is to close its tab. Releasing visibility before cleanup would break normal-tab guarantees. Replaceable wrappers/native-string compatibility, Unicode 16 word policy, selecting the target tab before input and the minimal committed-journal fallback retain their previous rationale. New popup/reload/network decisions above are already decided, not fresh owner choices.

## Moving onto 18d/19b / image handoffs / open questions

**Read — 18d:** lift SHARED unchanged into MCP instructions; generate slim tools/user-mcp; run group 12 in its real precedence harness, in both permission modes. Asking actions remain declared and generated; Chrome.trusted(operation) is the single owner-entry check for require_trusted_send. Keep independent adapter verdicts and exact support inventory when integrating precedence evidence.

**Read — 19b:** replace Chrome's minimal committed-journal fallback and provisional projection with its shared committed read/projection. Absorb hash-verified Chrome metadata/legacy history without migrating warning acknowledgements or changing occurrence identities. The fallback reads only the committed journal and writes no side record. Preserve R2 context before every input, round 27's open-check rule, live document/control/policy checks and final dispatch rechecks.

**Read — image:** install `/etc/aresos/control/chrome-excluded-sites.json`, `{"format":1,"hosts":[]}`, through protected root-owned parents, with no symlinks/group/world writes; a missing/unsafe setting refuses. Keep the production native-host/policy/update templates and signing key system-owned. Install gh >= 2.102.0 and private `/var/lib/aresos-tools/qualification-verifier-cache/config`; verify real HTTPS delivery under the fixed unit in 18c. Register an actually shipped build only with its full commit, its own build.py digest and timezone-qualified shipped_at; newest-three history stays empty until a build ships.

**Run — budget/storage:** [per-branch workflow-ID ledger](records/integrate2-run-count.json): `pkg/20-chrome` used 110 through source verification, including cancellations; this closing report/evidence push starts the normal push and PR pair, bringing it to **112 of about 115**. `pkg/20-chrome-adapters`: 6 Chrome IDs. `pkg/20-chrome-qual`: 5 Chrome IDs; its qualification report separately accounts for 15 total workflow IDs / 16 attempts across both workflows. Shared base/Mail/boundary runs do not count against the Chrome cap. [Closing .work inventory](records/integration-work-inventory.json): **666531157 bytes**, **no file over 500 MB**; no ISO, image layer, extracted squashfs, duplicate/partial large download or browser profile. No Gradle/Java process was started. Only pkg/20-chrome was pushed; PR #27 remains draft. No merge, force-push, main/data-branch mutation, production publisher issue/PR, real app message or privacy-hook bypass occurred.

**Open questions:** no new preference question. The lead records the decided popup/taken-tab rule and exact DevTools additions in section 6; the review panel confirms owner Enter using the receiver evidence. Merge waits for the package reviews and 18d as designed.
