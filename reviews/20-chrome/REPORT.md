# 20 — Chrome: stopped at a mandatory control guarantee

**STOPPED, incomplete, do not merge or ship.** The note's **Now** part is not
built fully or green. Both requested independent reviewers return **CHANGES
NEEDED**. This report preserves the partial implementation and the failing
regression; it is not a qualification record.

**Run — stop evidence:** [Control Chrome 42596054202](https://github.com/Ares-Empire/AresOS/actions/runs/42596054202),
head `e31e75d242511f13e68bd482c6da661c2579b0e4`, both installations failed,
Google Chrome `157.0.8103.38`. In `browser.txt:10`, genuine X keyboard input
(`Tab`, then `Return`, outside the tool) arrives 130 ms after Claude's free
click. The independent receiver sees **zero owner submissions**. The result
incorrectly says the page's activation was stopped. Claude's separately
scheduled form submission also stays held (zero arrivals). `browser.txt:15`
fails with `Owner submission must run normally while a Claude task is pending`,
`0 !== 1`. External installation reproduces it at **122 ms**, also with zero
owner and scheduled arrivals. The strict assertion remains in the workflow.
Retained [records](records/) include both receiver logs, tool evidence,
browser log lines, version/launch/listener records and run identity. The
[policy screenshot](screenshots/42596054202-owner-input-policy.png) shows the
owner's Submit button focused in the synthetic page after the failed input.

**Read / judgment — why stop:** section 6 says the owner's own clicks are
never held. The current MAIN script instead arms every readable frame for a
500 ms wall-clock window. It cannot tell those owner actions from Claude's
causal work. Disarming the window on owner input would release the already
scheduled Claude task. A replacement based on a few timer/Promise wrappers
would not establish coverage of native `await`, existing promises,
MessageChannel or same-origin cross-frame callbacks. The reviewers reproduced
the first defect without a browser and identified that coverage obligation.
This is a failure of this implementation, not a proof that every possible
implementation is impossible. I cannot honestly establish the specified
guarantee with this architecture, so I apply brief 20's rule to stop rather
than weaken it. No rule was narrowed and no assertion was removed.

## Specification and scope

**Read:** the specification is `origin/main` at
`29807fa6e6e14bfc405b3fe9b031f7c071b21eef`, read using `git show`:
`AGENTS.md`, `briefs/20-chrome.md`, `briefs/19b-owner-state.md`, CONTROL sections
3, 4, 6 and 7, FEATURES' Chrome rows, PLAN and design re-checks 29–34. The local
`briefs/20-parallel-start.md` wins. Branch code and the shared base are from
the Mail start specified by that note (`d3babf1f`; initial branch head
`b187e487`). The branch's control README, package 18/Mail reports, 17–17c
reports and 17 harness README are historical context, not decision-25 product
code to port. No main-only specification file was copied or edited, and no
other branch was merged.

**Read:** 18d's slim generator, `user-mcp.json`, MCP `instructions` and group
12 remain deferred as the note explicitly requires. The unfinished items
below, including qualification and six-site browser fixtures, belong to
**Now**; they are not being reassigned to 18d.

## Done — partial implementation

- **Read — service:** `control/aresos_control/chrome/` adds the Adapter/Engine
  implementation, definitions, classification word list, page-state binding,
  exact approval submission, owner rules, upload copies, a fixed-command
  bridge and qualification-record parsing. Asking inputs reserve shared
  operations. Free page changes also commit context before dispatch. Shared
  `warnings.py`, `paging.py` and response bounds are reused.
- **Read — extension:** `control/chrome/extension/` contains MV3 normal-Chrome
  transport, Claude group management, debugger input/navigation allow-list,
  isolated reader, MAIN hold/resume script, Stop popup and owner details UI.
  The reader builds safe structural facts and password-presence records;
  this is a handwritten semantic reader, not a qualified Playwright-equivalent
  implementation. Closed-root/frame, geometry and semantic completeness
  still need their browser regressions.
- **Read — packaging:** `control/chrome/native_host.py` relays length-framed
  native messaging to the service's `chrome.sock`. Packaging templates supply
  CRX3, the owner-supplied signing identity, Forcelist/pinning, native-host
  manifest and update manifest. CI uses an ephemeral key, not a production
  key. No image changes were made.
- **Read — shared changes:** the catalogue imports Chrome definitions;
  `Action.asks` excludes the trusted submit route from managed asks; daemon
  accepts the owner-UID native connection; proxy imports uploads on the
  caller side; storage retains Chrome approval context; warnings take their
  source app; setup installs the runtime and its build marker. Generated
  tools, help, current managed settings and managed MCP configuration match
  the definitions. These changes require the base/Mail regression workflows;
  their prior Mail results are not evidence for Chrome's combined head.
- **Read — tests:** `control/chrome_tests/` adds browser-free Python and Node
  tests. `control/chrome/ci/` and `control-chrome.yml` run branded headed Chrome
  inside disposable Linux containers through external and policy installs.
  A receiver logs arrivals independently of tool outcomes. Profiles remain
  inside those containers, and no real site or account is loaded.

## Verified

**Run — locally, no browser started:**

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/chrome_tests python3 -m unittest discover -s control/chrome_tests -v
Ran 30 tests in 39.380s
OK
Chrome durable-write sweep {'single': 442, 'persistent': 442, 'pairs': 829}

node --test control/chrome_tests/*.test.mjs
tests 11; pass 11; fail 0

PYTHONDONTWRITEBYTECODE=1 python3 control/generate.py --check
Generated artifacts match definitions

git diff --check
(exit 0, no output)
```

These were run on the working tree subsequently committed as `43d88a24` /
`e31e75d2`. Exact output is in `.work/20-chrome/plain-final-candidate.txt`
and `node-final-candidate.txt`. Inherited test methods account for some of
the 30 executions. The storage sweep injects real SQLite/file write faults
around submit/free operation paths but uses a **fake browser** as its dispatch
oracle. It does not cover every Chrome durable write or prove the complete
19b/R1–R3 acceptance matrix.

**Run — preliminary container capabilities, not full acceptance:**
[42591825243](https://github.com/Ares-Empire/AresOS/actions/runs/42591825243),
head `39bc55cdb3657558b13ba324b5dc32c62c23e6b5`, both external and policy
installations passed their smoke subset. Both artifacts' `browser.txt` have:

| Lines | Printed result | What it actually proves |
|---|---|---|
| 3 | `GROUP 1 what asks PASS: zero before approval, one after, no replay` | One generic Send click, approved once, repeated submit not replayed |
| 4–5 | `GROUP 2 stopped page steps PASS native` / `event` | One click-handler `submit()` and one `requestSubmit()` hold/resume |
| 6 | `GROUP 2 wrapped non-cancellable activation PASS: no delivery and never resumed` | One scripted Delete activation stopped before delivery |
| 7 | `GROUP 7 password presence and show-password PASS` | A small top-document value/show-password test, not full boundary audit |
| 8 | `GROUP 13 residual ordinary-click fetch OBSERVED, NOT HELD` | One ordinary-click fetch arrives without a hold, as the residual says |

The artifacts also record no Chrome TCP listener, no debugging launch switch,
and no `--no-sandbox`. Chrome was `157.0.8103.38`. The synthetic CI service
injects passing version switches **only to exercise qualified paths**; this
is test setup, never a published qualification entry.

**Run — negative acceptance evidence:** run `42596054202` adds the owner-input
regression above. Earlier `smoke.json` files saying `passed:true` name only
the core smoke subset and precede that regression; they are not aggregate
success. The final reporting change makes that explicit with
`core_smoke_passed:true, acceptance_complete:false`.

**Run — earlier diagnostic runs:** `42583280726`, `42584162033`,
`42586318488`, `42587229057` and `42589055268` failed during development.
They exposed connection/preload, insecure-origin `crypto.randomUUID`, and
cross-world element-identity failures; they are not passing evidence. The
current negative regression remains unfixed. All browser runs used only
`control-chrome.yml` on GitHub Linux containers.

## The 13 groups — acceptance status

| Group | Test/evidence available | Remaining acceptance obligation |
|---|---|---|
| 1 what asks | `test_policy` whole-word/label/input matrix (Python); Send smoke | Real-browser whole matrix of words, attribute sources, controls, keys, uploads and free cases; MAIN accessible-label bypass is open |
| 2 stopped page steps | `page.test.mjs` resume/loop/nested/free-mark tests; native/event/activation smoke | Browser matrix for click/key/input/change/select/check; direct control approval, fresh-frame fallback, other-form and nested paths |
| 3 binding | `test_engine` draft/frame facts; reader Node state test | Real browser changes for every binding item, re-check 30/32 uploads/plain sibling editor, existing/empty/oversize drafts and preview residual |
| 4 confirmations | Native dialog plumbing and adapter declaration in source | Exact named adapter confirmation consumption is not implemented; HTML dialog classification and all mismatch tests absent |
| 5 question matches page | Exact approval/order/hash Python tests | Full question/content fixtures, complete recipient summaries, hidden/password/file disclosure and both prompt surfaces |
| 6 permitted places | Static scheme/fixed-host Python tests | Browser take/redirect/popup/history/frames and all scheme paths; fixed Aresus host still needs authoritative image setting |
| 7 isolation/passwords | No-listener smoke; top-document password/show test; protected-getter Node test | Every browser-return/content-read/host/service/log/result trace over all excluded kinds, open/closed roots and cross-site frames; forgery/raw-method tests |
| 8 control/cancelling | Fake drop/deadline/restart tests; **owner-input container regression fails** | Owner input guarantee, actual popup Stop, out-of-group, release/close/restart and stale-reference browser matrix |
| 9 crashes/restarts | Fake durable-dispatch/fault tests | Browser/host/service crash cutpoints before check, after submitting and after input; independent receiver no replay |
| 10 six adapters | Semantic recognizers and fake Gmail owner-rule tests | All six site fixtures and feature paths; no six-site browser suite exists |
| 11 don't ask again | Exact-kind/revoke/widening/admin-only fake tests | Owner details and sudo alias flows; complete real-container exact account/recipient/kind and qualification suspension tests |
| 12 managed ask precedence | CURRENT generator adds ask rules and excludes trusted submit | Explicitly deferred to 18d's real precedence harness; no substitute built |
| 13 residual | Ordinary-click fetch observed | Autosave and after-limit submission still need receiver evidence; preview change residual needs its browser fixture |

No full set has passed twice on any head. A pair of smoke installation jobs
does not satisfy that requirement.

## Feature → tool → test mapping

**Read:** all public action names in the actions table have definitions and
generated tools. The following maps every Chrome *first* feature to its
current implementation and evidence/gap, without treating catalogue presence
as behavior verification. Tests named here are browser-free unless stated.

| FEATURES row | Tool/implementation | Test or explicit gap |
|---|---|---|
| List tab titles/addresses | `chrome_tabs` | Container smoke selects a listed tab |
| Take/give back owner tab | `chrome_take_tab`, `chrome_release_tab` | Take smoke; release browser coverage missing |
| Open/close Claude tab | `chrome_open`, `chrome_close_tab` | Defined/implemented; browser coverage missing |
| Back/forward/reload/address | `chrome_navigate` | Smoke uses address navigation; other directions unverified |
| Structure/positions/paging/find | `chrome_read`, `chrome_find` | Read smoke; long-page, cursor and find browser tests missing |
| One form/options | `chrome_read_form` | Defined; safe field-state Node test; full options browser test missing |
| Cross-site frames/shadows/dialogs | `chrome_read` | Implemented traversal; required browser matrix missing |
| Click/type/select/check/key/scroll | Respective six actions | Click smoke; browser-free policy/reader tests; remaining browser input matrix missing |
| Fill whole form | `chrome_fill_form` | Sequential definition/implementation; meaningful browser regression missing |
| GET search | `chrome_fill`, `chrome_press` | MAIN effective formmethod Node test; browser test missing |
| Submit form, same-kind stopped submit | Input actions then `chrome_submit` | Native/event smoke plus `page.test.mjs`; matrix incomplete |
| Labelled send/buy/delete | Input actions then `chrome_submit` | Policy matrix and Send smoke; MAIN external-label bypass open |
| Enter/Ctrl+Enter/Cmd+Enter compose | `chrome_press`, `chrome_submit` | Policy tests; browser key/default behavior unverified |
| Delete/Backspace outside editing | `chrome_press`, `chrome_submit` | Policy tests; browser coverage missing |
| Script activation while handling input | MAIN hold plus returned warnings | One activation smoke; semantic and causal coverage incomplete |
| Native alert/confirm/prompt | `chrome_dialog` | Plumbing only; exact covered-confirmation behavior incomplete |
| Local upload | `chrome_upload`, `chrome_submit`, caller import | Immutable-copy implementation; real upload/Stop/fault matrix missing |
| List normal Chrome downloads | `chrome_downloads` | Implemented; browser test missing; current search cap needs complete paging |
| Bookmarks/history addresses | `chrome_bookmarks`, `chrome_history` | Implemented; browser tests missing; history cap needs complete paging |
| Drop prepared operation | `chrome_drop` | Fake drop/deadline no-dispatch test |
| Don't ask again exact kind | `chrome_submit_trusted` | Fake exact Gmail/revoke/widening tests; six-site browser tests missing |
| Owner list/revoke/read-only | `chrome_sites`, details UI | Admin-only fake test; owner CLI aliases and list paging incomplete; late read-only recheck missing |
| Popups join Claude group | Navigation target listener | Implemented; browser test missing |
| Pay/order/transfer always asks | Policy and `chrome_submit` | Policy tests only; bank owner list and browser refusal matrix missing |
| Stop immediately | Actual extension popup | Implemented; actual popup browser test missing |
| Normal calls/Safe Browsing/extensions/updates | Existing normal Chrome | No altered browser network stack; real-profile compatibility unverified |
| Six site adapters | `sites.py`, isolated scoped readings | Partial recognizers; all six fixtures absent |
| Gmail compose/recipient trust | Gmail recognizer | Fake account/recipient/revoke/widening tests; Bcc/shortcut/two-compose browser tests missing |
| WhatsApp per-message/chat | WhatsApp recognizer | Implemented semantics; fixture missing |
| Bank read-only | Owner read-only host list | Preparation policy tests; late-policy change defect open |
| Gemini question/trust/share/delete | Gemini recognizer | Implemented partial semantics; fixture missing |
| Deezer playback/library/delete/share/pay | Deezer recognizer | Implemented partial semantics; fixture missing |

Owner sign-in is deliberately not automated. The no-password promise is not
qualified by the small smoke test. Never/later rows remain outside this run.

## Tool descriptions and measurements

**Read:** [generated Chrome tools](../../control/generated/chrome-tools.json)
and the Chrome section of [TOOLS.md](../../docs/control/TOOLS.md) contain the
exact descriptions and schemas passed through the current generator. The
shared description suffix in `chrome/definitions.py:SHARED` can be lifted
unchanged after 18d; it has not been moved to a stand-in instructions layer.

**Read / concern:** several descriptions currently promise incomplete
behavior (notably exact adapter confirmations). Returning generic object
schemas also does not finish the base's explicit result contracts. These
descriptions are draft text and must be corrected alongside implementation
before release; they are not owner-approved policy.

**Run:** parsing successful run `42591825243` tool artifacts gives 14 read
calls per install. Small smoke views range from **1,135–2,852 characters**
(external) and **1,133–2,847** (policy). This is not the requested
representative long-form/article measurement. Tokens and collection latency
were not measured; brief 17's DOM-snapshot measurements are not reused as
evidence for this reader.

## Not verified / unfinished Now work

**Read:** see [CODE-REVIEW.md](CODE-REVIEW.md) and
[SECURITY-REVIEW.md](SECURITY-REVIEW.md). In addition to the owner-input failure,
MAIN asking detection misses accessible labels supplied through
`aria-labelledby` or associated labels, prepared operations do not recheck a
new read-only restriction, and revalidation must apply a newly recorded
password-exclusion failure before binding reads. These remain open.

**Read — qualification is incomplete:** the shipped record and shipped-build
registry are empty. Runtime hash inputs include the extension, native host,
whole service/approval code and definitions. Unit tests cover build changes,
version gating and append-only records. However daily/on-connect refresh is
not called, temporary delivery storage needs admission/fault coverage, and
the workflow has no stable/beta repository resolution, three-shipped-build
matrix, full twice-per-pair runs, publisher, attestation or append-only
publisher verification. It does not create failure issues or a shipped-copy
PR. No actual workflow attestation has been verified or tested with altered
copies. These required Now parts were not completed before the stop.

**Read — R1/R2/R3 work remains:** pending needs live Chrome validity checks,
including lost release events/service restart. Free navigation needs bound
current/destination context and a committed new tab ID before navigation.
Owner details callbacks must avoid reentrant response-observation state.
Bridge disconnect state and malformed-frame handling need hardening. Fault
sweeps need Chrome's upload, owner-rule, qualification and page-warning
writes, persistent restart failures and the complete independent outcome
oracle. Upload copies need bounded retention/cleanup. Lists need complete
bounded paging. Existing base/Mail workflow results are not combined-head
regression evidence.

**Assumed / owner gates:** real sites/accounts, production signing identity,
actual image installation, full phone/terminal approval presentation and
ordinary profile compatibility require later owner/image work. No such test
was attempted. No human can substitute for the missing automated synthetic
acceptance suite.

## JUDGMENT-CALL

- **Read / chosen:** stop at the failed owner-input guarantee, keep the PR
  draft and retain the strict test. Clearing the timer, excluding owner
  behavior from the report or accepting extra owner holds were rejected
  because they weaken section 6. A future solution needs qualified causal
  scoping and the full interleaving tests, or an explicit design decision;
  no owner decision is inferred here.
- **Read / chosen:** byte-backed `File`/`DataTransfer` installation, from a
  verified service-owned copy, follows brief 17's direct local-file debugger
  refusal. Broad file-URL access was rejected. Exact bytes and cancellation
  still need container qualification; changing transport affects the upload
  path and tests, not saved owner data.
- **Read / chosen:** refuse unprimed pre-extension documents until an owner
  reload, ambiguous duplicate iframe addresses, and unsupported transformed
  frame geometry. Guessing could act without the preload or hit the wrong
  control. These are usability limits, not acceptance of reduced safety.
  They need owner/lead review before release.
- **Read / provisional:** fixed Aresus host is `aresus.app`; the source spec
  names Aresus without a complete image-owned address list. This must be
  settled against the image's real settings/approval origin before shipping.

## PLAN-GAP and 19b integration

**Read / builder gap:** the incomplete Now functionality and tests above are
implementation gaps, not changes to the plan or a claim that the plan has
been satisfied. No production qualification entry or merged feature should
be based on these smoke results.

**Read — after 19b:** move Chrome operation/free-input sources, page-step
check sources, occurrences and per-occurrence acknowledgement onto the shared
committed read path/projection. Derive pending invalidations from the live
browser/session and committed binding. Preserve open checks independently
of warning acknowledgement through restart/restore/expiry and fault-test
the combined lifecycle. Owner lists and qualification delivery outcomes also
need that shared projection where owner-visible. This branch intentionally
does not build a competing owner-state projection. 18d's generator changes
and group 12 are separate deferred integration work.

## Open questions and closing inventory

No mid-run owner answer was requested. The lead needs to decide the causal
scoping approach before resuming this incomplete implementation, then obtain
fresh final-head reviews and run every required workflow twice after the
combined Mail/18d/19b integration. This report is not a request to merge.

**Run:** all work stayed in this worktree; no Mac browser/profile was opened
or read, no local browser/container was run, no system installation or admin
command was used, and no Gradle daemon was started. The `.work/` inventory
printed `files over 500 MB: []`; downloaded evidence was under 1 MB before
the final negative-run screenshot/artifact download. No large image or
browser download remains locally.
