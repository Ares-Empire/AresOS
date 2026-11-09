# 20 — Chrome Now continuation

**In progress; not green, do not merge or ship.** The old public MAIN control API and page-forgeable identity path have been removed. The independent receiver now passes both forgery regressions. The complete final-head container matrices are still running; this report distinguishes source changes from completed evidence. PR #27 remains draft. No local Chrome, Chromium or browser profile was started, inspected or read.

## Done

**Read:** specification precedence is `20-continue-2`, `20-continue`, `20-parallel-start`, then the specification fetched from `origin/main` with `git show`: AGENTS, brief20, brief19b, CONTROL sections3/4/6/7, FEATURES, PLAN and re-checks29–34. No other branch was merged. Image/mod/protected design files were not changed. Group12 and the slim MCP integration remain for18d.

**Read — extension boundary:** `page.js` contains only the four MAIN wrappers, with captured intrinsics and no public control object or identities. Every relaxing decision lives in `guard.js` in ISOLATED: private generation, in-flight flag, owner-event verdict, held steps, native resume and one-use consumption. Forged reports can only request normally guarded attempts. The isolated reader supplies element identities directly. Same-kind native/event resumption consumes its allowance; a further native submit cancels the enclosing submit event's default before sending, preventing the two-send defect found in review. Stopped activations are never replayed, and fallback uncertainty remains `unknown`.

**Read — reader/binding:** names include referenced and associated labels, hidden referenced labels, input button values and image alternatives. Password protection is checked before each value/text read, remains sticky, drains pending protection mutations, and requests old mutation values only for type/autocomplete/style. No bulk HTML/attribute/AX/DOM snapshot API is used. Native dialogs are read without a content-script request while a modal blocks the renderer; excluded or ambiguous openers refuse before text is read or returned. Binding covers private document identity, the target, effective form destination/fields, generic editable drafts across readable frames, adapter facts and exact confirmations. Current read-only and password qualification checks run before re-reading prepared bindings.

**Read — service/base:** free and asking dispatches commit their context first. Newly opened tabs get their actual identity committed before address navigation. Native host replies are correlated, fragmented and drained even when an owner event cannot be committed. Malformed/duplicate/reused-descriptor handshakes no longer kill the daemon. `chrome/committed.py` derives Chrome owner facts from hash-verified committed journal metadata when SQLite reads fail; offsets/flags are bounded, values stay on disk, and historical peaks can recover after archive tombstones through bounded scan windows. Warning occurrences/acknowledgements use existing `warnings.py` and `paging.py`. `control_notices` exposes the shared mixed-app catalogue; cached Chrome rows/counts cannot resurrect acknowledged warnings. These are the base changes Chrome needs pending19b.

**Read — policy/qualification/uploads:** the fixed list contains vendor hosts only. Private owner exclusions come from `/etc/aresos/control/chrome-excluded-sites.json`, `{"format":1,"hosts":[]}`, root-owned through a protected parent walk, no symlinks or group/world writes; mode0640 with the service group is the image template. Missing/unreadable/unsafe settings refuse. Dotted/IDNA spellings normalize consistently. Dynamic registration and session DNR rules apply exclusions. Qualification reads stable+beta package metadata, plans main+newest three shipped builds twice, verifies both published history and the shipped baseline, aggregates complete named evidence, attests and publishes only on main. Runtime refresh runs daily and on an accepted uncovered-version connection; offline/unverified updates retain held history. Real publication/data-branch/issue/PR mutations never run from this branch. Upload copies are service-owned, immutable to the owner, capped at two/50MiB, released on staging or execution failure and expired after15minutes; partial extension staging also expires.

**Read — six adapters:** Gmail compose/recipients/Bcc/shortcuts, per-message WhatsApp, GitHub actions and exact branch confirmation, owner read-only bank, Gemini questions/chat changes, and Deezer playback/library versus removing/sharing/paying. Trusted kinds require the exact site/account/parameters and current kind hash; deleting/paying/WhatsApp remain ineligible. SHARED remains liftable unchanged for18d. Exact exposed descriptions are in [TOOL-DESCRIPTIONS](TOOL-DESCRIPTIONS.md).

## Verified

**Run — local, plain Python/Node only:**

- Full Chrome Python suite: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/chrome_tests python3 -m unittest discover -s control/chrome_tests -v`; latest completed run86tests in212.575s, OK (`.work/20-chrome/local-all-v20.txt`). Writer surface:1115 single faults,1115 persistent exhaustion cases,3061 cleanup pairs. Operation sweep:446 single,446 persistent,1605 pairs. Independent oracle decodes committed journal records; it does not trust working SQLite or the implementation's pending rows.
- Latest focused Python46tests in0.503s and native bridge7tests passed, including connection refresh, post-commit/SQL_FULL acknowledgement, mixed notice caps/routes, bounded historical recovery and interrupted upload cleanup. Some fixes postdate that full run and will receive final full-suite evidence.
- Latest Node suite49/49 passed, including opaque-event forgery, getter mutation/password exclusion, old completion/new nonce, and modal waiters. No browser process is used by these tests.
- Shared record/paging tests10/10 passed locally with the installed-boundary object stubbed only for this platform: original record assertions unchanged, tiny/max25MiB sends both4078journalbytes. An earlier direct local invocation refused because the managed Linux boundary is not installed; that was not counted as passing evidence.
- `python3 control/generate.py --check`: `Generated artifacts match definitions`. `git diff --check` checked between batches. The reviewer compiled159 generated fixture HTML scripts with Node VM; no browser started.

**Run — receiver evidence on runtime e1f1bacf:** [42616318628](https://github.com/Ares-Empire/AresOS/actions/runs/42616318628) external and [42616326326](https://github.com/Ares-Empire/AresOS/actions/runs/42616326326) policy, Google Chrome157.0.8103.38. Browser log lines15–16 show `page-forgery` and `hostile`: receiver0 before approval,1 after,1 after a repeated attempt. The former API regression is repaired, not waived. Full password roots/traces, upload path/hash/bytes, page confirmations, popup Stop and all nine Chrome/host/service crash cutpoints passed. For each component the receiver count was0 before check,0 after submitting,1 after input, with no replay and unknown outcomes where required. Browser line116 records the complete crash matrix PASS.

**Run — incomplete matrices were useful failures, never passes:** the same e1 runs failed words/Space, later resume/activation cases, binding/navigation and some adapter actions. Unneeded fixture EventSources exhausted six per-origin HTTP connections; the fixture now closes old channels, creates them only for mutation cases and waits for the requested document to commit. The redirect helper also wrongly waited for a readable excluded destination. Those repairs and the extended matrices are under runner verification; none is called green from source alone.

**Run — base:** [42620316136](https://github.com/Ares-Empire/AresOS/actions/runs/42620316136) passed on7f595da6. Earlier base failures caught an empty Chrome metadata field on unrelated compact records; the writer now omits it and the unchanged size/privacy test passes. The former peer-credential regression also passed in earlier repaired base runs. Final-head base/Mail/boundary pairs are still required. Synthetic real GitHub attestation verification passed in the e1 push workflow; altered bytes/wrong source branch refused. No real qualification record was published.

**Run — latest completed container head95ed8ac1:** [42625962015](https://github.com/Ares-Empire/AresOS/actions/runs/42625962015) and [42625971758](https://github.com/Ares-Empire/AresOS/actions/runs/42625971758) failed overall. The inspected external artifact passed972strict word/label/key receiver cases; all six adapters and shortcuts; upload bytes; exclusions; password roots/traces; drop/release/close/deadline/outside-group/actualStop; every3×3crash cut; feature/catalogue and long-view paging; and no listening port before/after tools. Failures remain real failures: implicit field Enter, scripted dispatchEvent/replay, native recursive fixture behavior, mutation-channel closure, child-frame native confirmation, and GET fixture query tags. Current code addresses those causes; until container reruns they remain unverified fixes. The latter two fixture corrections preserve exact receiver assertions and add a mutation acknowledgement barrier.

## Groups and feature coverage

**Read/run:** this table records the latest completed evidence, not final acceptance. Full current named cases live in `control/chrome/ci/matrices.mjs` and `verdicts.mjs`; any missing/failing required case stays false.

| Group | Named tests / latest completed evidence |
|---|---|
|1 What asks|`what asks word/label/key matrix` (all words×9label sources×click/Enter/Space); new `submit compose deletion and free-input matrix`. e1 incomplete, rerun required.|
|2 Stopped page steps|`handler/resume matrix`, `script activations never replay`, `loop with uncancelled enclosing submit`, `nested validation and fresh-frame fallback`, `owner synchronous task delayed work and in-flight interleavings`. e1 loop/native/event smoke pass; extended set not yet green.|
|3 The binding|`binding every form fact and generic sibling draft`, `cross-frame adapter empty and oversized drafts`; upload-before-send text change. Source/focused tests pass, final container evidence pending.|
|4 Confirmations|`page confirmations bind their full text and ask independently` passed e1. `exact native confirmation and mismatch matrix` covers text/kind/frame/site/second-dialog changes; pending.|
|5 The question matches the page|`question fields, hidden values, password label, upload path and hash` passed e1; exact copied bytes reached receiver once.|
|6 Where Claude may go|`exclusions through frame, popup, redirect, taking and history`, `schemes links and forward routes`; e1 incomplete. Custom owner-excluded link refuses before input in focused tests.|
|7 Isolation|Forgery regressions0/1/1 and `all password kinds across open closed and cross-site roots` passed e1; traces checked browser boundary/tool/service logs. No port before tools passed; after-suite check added. Raw command/prototype/identity refusal tests also run in Node.|
|8 Control and cancelling|`drop release close and stale references` and actual popup Stop passed e1. `deadline and tabs outside the group` added. Native owner Enter retains strict failure described below.|
|9 Crashes and restarts|`Chrome host service crash cutpoints never replay`: all3×3 passed e1 with private post-input/pre-reply barrier, independent receiver and committed status.|
|10 Adapters|All six fixture sites exist. e1 Gmail/WhatsApp/Gemini/bank passed; GitHub/Deezer stopped at fixture connection starvation. Added shortcuts/account-specific questions.|
|11 Don't ask again|e1 exact-owner/revocation scenario passed; source/focused tests cover account/recipient/kind changes. Container cases now include current mismatches, widening suspension and conservative suspension.|
|12 Managed ask rule|Explicitly deferred to18d's precedence harness, normal and skip-permissions. No stand-in built.|
|13 Residual shown honestly|Ordinary unlabelled click fetch, autosave, after-limit submission and changed read-only preview all observed as not held in e1.|

**Read — first feature→tool→test mapping:**

| FEATURES first rows | Tool / path | Tests |
|---|---|---|
|Tabs, take/release, open/close, visible group/popups|tabs, take_tab, release_tab, open, close_tab|groups6/8/9; owner-tab startup, release/close, popup|
|Address/back/forward/reload, searches|navigate, fill, press|groups1/6; complete scheme/history routes|
|Paged structure/find, frames/shadows/page dialogs, form options|read, find, read_form|group7 password roots; VIEW long-page; FEATURE forms/options/find|
|Click/type/select/check/keys/scroll, whole forms/wait|click, fill, select, check, press, scroll, fill_form, wait|groups1/2/8; FEATURE tool matrix|
|Form/list-word/compose/delete/pay actions|input→submit|groups1/2/3/5, all English/German words and key/control routes|
|Script activations stopped, never replayed|private guard + fresh asking input|group2 wrapped/cancelable/noncancelable/fallback/nested cases|
|Native/page confirmations|dialog, adapter confirmation plan|group4 exact/mismatch/second-dialog cases|
|Caller upload|upload→submit, shared file transfer|group5 path/hash/receiver bytes; Python staging cleanup/fault surface|
|Download paths, bookmarks/history read|downloads, bookmarks, history|FEATURE12-item catalogues, two-item continuations|
|Drop, Stop, never replay after interruption|drop, popup Stop, operation_status|groups8/9, storage fault sweeps|
|Owner-only allow/revoke/read-only|sites, details page, admin aliases|groups10/11, owner-channel denial tests|
|All six adapters and their first actions|site recognition, submit/submit_trusted|group10 six sites/shortcuts; group11 exact trust/conservative suspension|
|Owner sign-in/password values excluded|owner_signin refusal, safe reader|group7; Node guarded-getter/transition cases|

## Measured views

**Run — e1 long article/form:**120paragraphs and80fields,221477characters/UTF-8bytes,14pages capped at16000characters. Full read took1881ms external and1133ms policy in the retained representative runs. Approximate tokens55370 means characters/4, not a tokenizer measurement. It is complete and paged, but verbose compared with brief17's older DOM-snapshot numbers. New `read_form` JSON fragments and catalogue continuations have separate coverage; final-head measurements are pending.

## Not verified / remaining work

**Read:** no real account/site or laptop interaction is claimed. Signed-in site selectors, browser-update breakage, extension coexistence and the owner's normal desktop still need the post-boot human checks. The final complete named matrices, both install modes, twice on one final head and final shared workflow pairs remain outstanding. Interim [BUILD-REVIEW-3](BUILD-REVIEW-3.md) and [BUILD-SECURITY-REVIEW-3](BUILD-SECURITY-REVIEW-3.md) contain fresh sol-high/astra-high findings and repair probes; neither certifies final SAFE.

## PLAN-GAP

**Run/read — owner task attribution:** in e1 the physical X keyboard Enter arrived116ms after Claude's handler, produced0owner arrivals and0Claude300ms arrivals, with separate held preparations. `eventPhase` proves synchronous dispatch only; native Enter's default submission can run after the retained trusted event's phase resets. No standard task identity proves that default action belongs to that same owner task. The isolated verdict therefore holds this uncertain case. The strict expected1 test remains failing. Synchronous owner-handler, delayed second submission, replay and in-flight cases stay separate strict cases. This is the continue-2 permitted conservative PLAN-GAP, not a proposed design change. It also keeps page-script qualification false; no pass is fabricated to make the tool ship.

**Read — residuals accepted by section6:** direct fetch/autosave, unlabeled local changes, sends after500ms, and generic read-only previews remain outside the hold/binding guarantee. Fresh-frame raw activations are never resumed and uncertainty is reported honestly. Same-named user-level native host replacement remains decision24's accepted owner-user capability.

## JUDGMENT-CALL

**Read:** MAIN wrapper prototype properties are nonwritable/nonconfigurable so later page replacement cannot bypass a normally held call. This may break libraries that patch those prototypes. Allowing replacement would reintroduce a relaxing path; changing this later requires a different proven wrapper boundary and the hostile fixtures again.

**Read:** committed Chrome recovery metadata includes its full bounded operation/binding/check/ack context in the private independent journal, while unrelated Mail/base compact records stay unchanged. The alternative cached-only projection violatesR1 under failed SQLite reads. This grows private Chrome history and makes format compatibility important;19b should absorb it into its shared committed read/projection path while preserving existing journal history and acknowledgements. No second warning lifecycle was invented.

**Read — event compatibility:** if Chrome cannot unwrap a MAIN event, ISOLATED constructs a fresh untrusted event from bounded primitive hints, then classifies it after every page getter has finished. It never dispatches an opaque original on the strength of those hints. This can lose original object identity, custom payloads and cancellation history; supported primitive keyboard/mouse/input fields and cancellation return are preserved where available. The alternative was silent refusal of affected script events. Changing this later requires proven cross-world event semantics and the receiver/forgery suite. MAIN recursion tracking only adds holds.

**Read — Unicode policy version2:** a frozen Unicode16casefold/word-range resource is shared by Python and generated JavaScript so different runtime Unicode versions cannot disagree on asking labels. Regenerate/version both together for a future Unicode update.

## Handoffs / open questions

**Read —18d:** lift SHARED unchanged, generate slim per-tool descriptions/user-mcp and run group12 in the real precedence harness. Asking actions remain declared in the current generator. `Chrome.trusted(operation)` is the single owner-entry decision method for `require_trusted_send` to call.

**Read —19b:** replace Chrome's provisional offset projection with the shared committed projection/read path, keep Chrome metadata/legacy migration and warning occurrence identities, preserve live session/document/control/policy checks and source-derived acknowledgement behavior. Pending identity checks do not promise content still matches; dispatch rechecks full binding.

**Read —image:** install the protected excluded-sites setting, verifier, native host manifest/policy/update templates and stable production signing key; compute the complete installed runtime hash and register the newest three shipped builds in builds.json. Empty shipped qualification/build registries remain deliberate until real main evidence/image handoff. Nothing under os/ was changed.

**Run — budget:**42Chrome workflow runs used of about50 after the latest push; canceled/superseded runs count. More verification is still in progress. No Gradle/Java daemon was started. Latest `.work` inventory found no file over500MiB. No question is needed mid-run; work continues.
