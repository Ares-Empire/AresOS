# Part P review fixes — implementation and local mutation checkpoint

**Status: in progress; browser acceptance is not green.** This supersedes no earlier receiver evidence.
The reviewed baseline is `60b94384`; instructions are `briefs/20-review-fixes.md`, Part P.
The independent state build owns Part S. No state branch was read, changed or merged.

**Read:** fetched `origin/main` and read the requested specification with `git show`, the seven panel reviews,
the existing report, and the six continuation/integration briefs. The latest fix brief wins.

**Run:** only browser-free Python and Node on this Mac. No browser executable, browser profile, system install,
container or Gradle process was started locally. All browser jobs use `control-chrome.yml` Linux containers.

## Item map

“Unit” below means the actual production implementation exercised by the browser-free test, not a browser claim.
The receiver assertions in `review-matrices.mjs` are 0 before approval, 1 after, 1 after a repeat, except explicit
owner handoff / non-cancellable uncertainty, whose different meaning is stated in the case.

| Item | Change | Regression / mutation |
|---|---|---|
| P1 | A dialog answer must first arm every private guard, without an old allowance; missing coverage or modal-blocked arming refuses and keeps the dialog for the owner. Late/error arms have nonce-bound cleanup. | Background independent/delayed dialog units; independent accept/dismiss receiver case; mutation P1. |
| P2 | Inherited blank/srcdoc documents use their ancestor's permitted address plus the isolated document's origin and native document ID. They enter reads, bindings and holds. Incomplete generic draft coverage refuses. | Background P2; inline blank/srcdoc receiver cases; mutation P2. |
| P3 | A new document inherits the active hold before MAIN activation, without an approval; final frame coverage is checked and additions are armed or refused. Inherited guards finish with the source dispatch. | Background P3 startup/final-snapshot tests; new HTTP-frame receiver case; two P3 mutations. |
| P4 | A borrowed wrapper routes through the target document's private guard; a source hold propagates protection without allowance. Inert/detached/non-Nodes and ordinary outside documents keep native behavior. | Page P4 and cross-tab/iframe/outside receiver cases; mutation P4. |
| P5 | Controlled `attachShadow` synchronously registers private capture before returning. Composed roots stay held; detached roots retain native behavior. | Composed-aware double, immediate borrowed-dispatch unit, open/closed same-handler form receiver cases; mutation P5. |
| P6 | One canonical key tuple is used for service classification, adapter shortcuts and dispatch; the extension checks the received tuple. | Modified Delete/Backspace units and receivers; Gmail Shift/Ctrl/Alt/Cmd+# variants; mutations P6 and P6-adapter. |
| P7 | Tolerant percent-byte UTF-8 replacement decoding agrees with Python, including malformed escapes and BOM preservation. | Actual guard and policy counterexamples; malformed action receiver cases; mutation P7. |
| P8 | NFC normalization precedes the frozen fold/boundary table, in word-list version 3. | Decomposed German policy/guard/receiver cases; mutation P8. |
| P9 | Explicit payment/deletion evidence wins over adapter recognition; trusted checking independently rejects forbidden effects and WhatsApp. | Policy and trusted-predicate units; mixed-label owner-entry receiver case; two P9 mutations. |
| P10 | Affected-item resolution includes ARIA listitem/row/article and named sections. | Reader units and changed-item receiver cases; mutation P10. |
| P11 | A page send confirmation also binds all generic editable drafts outside its dialog. | Service binding unit and sibling-draft receiver mutation; mutation P11. |
| P12 | Selected files bind private native immutable-File identity, plus the staged SHA-256 when installed. Unbrandable identities refuse. | Same-metadata GOOD/EVIL replacement unit and receiver mutation; mutation P12. |
| P13 | Safe rich text preserves line breaks and whitespace; binding also retains safe structure, including adapter rich drafts. | Reader multiline unit and changed-rich-text receiver case; mutation P13. |
| P14 | Unsubscribe/Abbestellen has affected-item semantics, without an unrelated draft requirement. | Policy unit, both language receiver cases; mutation P14. |
| P15 | Button content precedes the title fallback in the shared accessible name. | Reader unit and conflicting-title receiver case; mutation P15. |
| P16 | Embedding reads only srcdoc attribute presence, never its HTML value. | Throwing srcdoc getter unit; ingress instrumentation; mutation P16. |
| P17 | A passive private password tracker and its observer survive reader disposal. A changed private identity for a surviving native document refuses reading. | Reader reinjection and lost-history units; browser Show/release/retake; mutation P17. |
| P18 | Sticky protection is checked before field eligibility; protected ancestors exclude descendants before text getters. | Throwing protected-descendant/former-editor unit and browser variants; two P18 mutations. |
| P19 | No Runtime.enable. Startup uses Debugger.scriptParsed's context ID and DOM.resolveNode's MAIN-world handle; all incoming protocol events are audited in test mode. | Bootstrap unit forbids Runtime.enable; password fixtures log and throw their password, and the browser asserts no console/exception Runtime ingress; mutation P19. |
| P20 | Exact form, submitter, trust and mark clearing are independently pinned. Browser synchronous interleavings and unconsumed delayed work added; old timers renamed “after his mark.” | Four independent P20 mutations and owner receiver cases. Status remains “passes in CI, panel to confirm” only once CI passes. |
| P21 | Effective GET search exemption precedes generic compose Enter. | Ordinary text-input search unit; mutation P21. |
| P22 | Questions name the service action/key and page title; title is bound. Recipient/name summaries are bounded, count remaining recipients exactly, and preserve full fields below. | Question/title/count/long-name units, title receiver mutation; two P22 mutations. |
| P23 | Input/dialog/navigation results carry a bounded post-input address/notice/dialog/change observation, or explicitly state unavailable. | Background notice unit and actual notice receiver fixture; mutation P23. |
| P24 | Final navigation identity precedes the last dirty/media check. Tab.audible supplements attached media; uninspectable frames count as possibly unsaved. | Late-typing/audible unit; blank-editor/detached-audio/Web-Audio receiver cases; two P24 mutations. |
| P25 | Only native input requiring a selected tab activates it; satisfied checks and isolated actions do not. Satisfied checks report unchanged, without claiming dispatch. | Inactive no-op/select units and owner-tab browser case; mutations P25 and P25-report. |
| P26 | Replacements use nonconstructible methods with native property shapes. A fresh-realm stringifier must differ in a controlled tab and equal baseline outside. | Shape unit and discriminating compatibility receiver fixture; mutation P26. |
| P27 | Revocation removes session navigation blocks before waiting for native cleanup. | Pending-cleanup rule unit; mutation P27. |
| P28 | Every armed dispatch finishes its nonce-bound guards in finally, including refusal paths. | Final-binding refusal cleanup unit; mutation P28. |
| P29 | Runtime acceptance requires exact named inventory, all rows true, all core/adapter verdicts true, groups 1–11/13 true and group 12 false. | Missing/duplicate/false/unknown runtime acceptance unit; mutation P29. |
| P30 | All password variants appear in forms across document/open/closed/cross-site roots; exercise read/read_form/preparation/final binding plus Show/retake. Sensitive getters are instrumented before filtering in test builds; every protocol event is audited; scans reassemble fragments. | Getter matrix, protocol-ingress and fragment scanner tests; mutation P30. |
| P31 | Popup first-act reload pinned even when preloaded; script POST tab/popup cases; excluded popup existence; first-head-script capture; hidden GET receiver case. | Background popup, fixture head/GET units and receiver cases; three P31 mutations. |

## Local verification checkpoint

**Run:** `node --test control/chrome_tests/*.test.mjs`: **186 tests, 186 pass, 0 fail/cancelled/skipped**, 6.230 s.
Full Python checkpoints: **176 tests, OK, 342.094 s**; **180 tests, OK, 323.556 s**;
**181 tests, OK, 281.713 s**. A final full run including the modified Gmail-key test is pending.
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/chrome_tests python3 -B -m unittest test_questions test_policy test_sites test_unit -q`:
**42 tests, OK, 0.496 s**.
`python3 control/generate.py --check`: `Generated artifacts match definitions`. `git diff --check`: clean.

**Run:** `python3 -B reviews/20-chrome/mutation-audit.py`: **49 mutations rejected; every baseline passed**.
The auditor copies only into this worktree's `.work/`, mutates the copy and removes it. Exact commands and failing
assertions are in [review-fixes-mutations.json](records/review-fixes-mutations.json). The first attempt exposed the
missing nonnegative capture assertion in the new head-script unit; that test was strengthened and the complete
complete mutation audit rerun successfully.

## CI ledger (not acceptance)

**Run:** source `8613f31f`: Chrome **42795327210** and **42795334448**, both install modes in both runs, failed
before browser startup on the new P27 unit's prematurely accessed fake timer. The assertion that Stop has already
removed its navigation rules is unchanged; the fixture now explicitly waits for the pending cleanup deadline to be
registered. The correction was committed in `719d5cd1`. No missing browser case is a pass.

Source `661b650c`: push **42798171530**, PR **42798181820**, both failed after entering browser input. External push log lines 2609–2614 show the native stopped-submission case reached its receiver assertion, followed by a disconnected host. Retained ingress ends at a new-frame startup awaiting guard.finish while the debugger is paused: a real deadlock. Startup now uses synchronous guard.inherit, with no allowance and no wait for a paused browser task; a new regression pins it. The background in-flight flag now over-covers every private completion barrier. This was fixed before the next batch. Qualification
**42798181770** and boundary **42798181847** succeeded; base **42798181856** and Mail **42798181785** must be checked in the closing ledger.

Source `6f65b16e`: Chrome **42801585223** and **42801591854** were cancelled as superseded before acceptance;
they are not passing evidence. Source `cbe641a8`: Chrome **42803248244** and **42803256661** are in progress.
On that source, base **42803257055**, Mail **42803256710**, boundary **42803256666** and qualification
**42803256636** succeeded. These are intermediate checks, not final-head acceptance.

The starting branch ledger had 114 Chrome workflow IDs, including the owner's two brief/review-only IDs. Four
implementation pushes add eight more: 122 at this checkpoint. Recount from
`gh run list --branch pkg/20-chrome --workflow control-chrome.yml --limit 200` before every closing push; remain
within about 155. Earlier superseded baseline runs 42786706317/42786714089 were cancelled. No force push or hook
bypass was used.

## Boundaries and decisions

**Read/built:** the new brief's dialog refusal, foreign-document routing, inherited-frame protection, title/name
rules and immediate Stop rule are decided requirements. No new owner permission is requested.

**Read/built:** no new DevTools method was added. `Runtime.enable` was removed from the generated fixed list.
Evaluation remains extension-owned fixed code with private context/object handles, never service-supplied script.
The ordinary-tab MAIN scope remains unchanged. Fresh-realm detection remains a disclosed compatibility residual;
matching toString text alone is not bot-check proof.

**Read/built:** the selected-file identity is native immutable Blob/File identity, private per document; it is not
name/size/date equality. Staged bytes additionally retain their verified hash. Live behavior and browser ingress
remain to be confirmed by the running Linux jobs.

**Ownership:** only Part P files changed. Minimal shared-function edits needed outside Part P's adapter sections:
`Chrome.read()` validates inherited frames using `effective_url`, and `check_readonly()` checks that same permitted
address. These lines must be preserved when the Part S adapter edits are integrated. The stored-state read in
`trusted()` was left intact; only its independent semantic prohibition was added. No engine/storage/recovery/
retention/committed/qualification stored-read or Mail filing changes were made here.

**Not verified:** final-head Chrome twice in both modes, base/Mail/boundary twice, live signed-in sites and owner
review. Group 12 stays false pending 18d. Part S is an independent unmerged build. The old report's green claims are
historical and do not establish this round.


**Read — bootstrap rationale:** Chromium's [ResolveNode implementation](https://raw.githubusercontent.com/chromium/chromium/main/third_party/blink/renderer/core/inspector/resolve_node.cc)
selects the node owner's frame's main-world context when no execution context is supplied. The private detached
node therefore gives a frame-specific MAIN handle without subscribing to Runtime. This source reading is separate
from the actual browser bootstrap and native-submission progress observed above.

The exact retained early-failure log index is [review-fixes-first-batches.json](records/review-fixes-first-batches.json).


**Built/run — precollection refinement:** origin and surviving-document expectations now travel into the reader's
private message handler and are checked before snapshot/value extraction; a post-collection refusal alone was
insufficient. Dedicated throwing-getter and background expectation tests cover both ends. Inline frames also enter
stopped-step polling and validity checks. The added mutations remove each precollection check independently.
CI ordering now runs the focused page Python and all Node checks first, then the complete browser matrix, then the
unchanged full Python sweep. A green job still requires every suite; earlier browser failures return sooner.
