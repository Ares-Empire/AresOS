# 20 — Part P review-fix round

**In progress; this round is not green.** The current work follows `briefs/20-review-fixes.md`, Part P, on
`pkg/20-chrome`; Part S remains an independent unmerged build. The [current implementation/test map](BUILD-P-1.md)
accounts for P1–P31, including the browser-free mutation evidence. All browser tests run only through the
`control-chrome.yml` Linux containers. No local browser executable or profile has been accessed.

The lead's 2026-11-10 13:15 feature-preserving direction is being applied. The [current continuation checkpoint](BUILD-P-2.md)
records the debugger barrier for native dialogs, isolated byte hashing for owner-chosen files and successful-send
fixtures for ordinary blank/srcdoc editors. Missing-coverage native-dialog cases remain explicitly tracked for the
lead and owner; no fallback refusal is approved or silently treated as feature-complete.

The latest local checkpoint is 195 passing Node tests, 44 focused Python tests, 184 full Python tests and 60
rejected mutations covering every P item. Final-head browser/base/Mail/boundary runs twice and the closing
per-item receiver/log index remain required.
The first container batch found a fake-timer fixture race; the next found a real paused-startup finish deadlock.
Both have dedicated regressions and are fixed for the next batch. Missing cases are never counted as passes.
Group 12 remains false. Owner Enter remains subject to the lead's panel-confirmation condition.

The report below is retained historical evidence for the prior integration, not acceptance evidence for these fixes.

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
|13 Residual shown honestly|Changed generic read-only preview; autosave/after-limit; baseline ordinary-click fetch is observed, not held.|

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

**Read — residuals stated by section 6:** direct fetch/autosave/read receipts, unlabelled local deletion, address-carried data, sends after 500 ms and generic read-only previews remain outside the hold/binding guarantee. Fresh-frame raw activations never resume and uncertainty is reported. Borrowed native form-submit from a fresh realm remains separately disclosed in the earlier report; no universal interception/impossibility claim is made here. Same-user host substitution/direct tool calls remain decision 24's accepted user capability.

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
