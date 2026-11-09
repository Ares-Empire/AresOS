# 20 — Chrome Now continuation

**In progress; not green, do not merge or ship.** The old public MAIN control API and page-forgeable identity path have been removed. The independent receiver now passes both forgery regressions. The latest completed browser jobs passed34/37 named matrices on the PR and33/37 on the push, with the strict conservative owner-Enter failure also retained. Repairs need the next Linux-runner batch; this report distinguishes source changes from completed evidence. PR #27 remains draft. No local Chrome, Chromium or browser profile was started, inspected or read.

## Done

**Read:** specification precedence is `20-continue-2`, `20-continue`, `20-parallel-start`, then the specification fetched from `origin/main` with `git show`: AGENTS, brief20, brief19b, CONTROL sections3/4/6/7, FEATURES, PLAN and re-checks29–34. No other branch was merged. Image/mod/protected design files were not changed. Group12 and the slim MCP integration remain for18d.

**Read — extension boundary:** `page.js` contains only the four MAIN wrappers, with captured intrinsics and no public control object or identities. Every relaxing decision lives in `guard.js` in ISOLATED: private generation, in-flight flag, owner-event verdict, held steps, native resume and one-use consumption. Forged reports can only request normally guarded attempts. The isolated reader supplies element identities directly. Primitive event data remains lazy and protection is rechecked before each getter, with final classification after page getter side effects. Same-kind native/event resumption consumes its allowance; a further native submit cancels the enclosing submit event's default before sending, preventing the two-send defect found in review. Stopped activations are never replayed, and fallback uncertainty remains `unknown`.

**Read — reader/binding:** names include referenced and associated labels, hidden referenced labels, input button values and image alternatives. Password protection is checked before each value/text read, remains sticky, drains pending protection mutations, and requests old mutation values only for type/autocomplete/style. No bulk HTML/attribute/AX/DOM snapshot API is used. Native dialogs are read without a content-script request while a modal blocks the renderer; excluded or ambiguous openers refuse before text is read or returned. Binding covers private document identity, the target, effective form destination/fields, generic editable drafts across readable frames, adapter facts and exact confirmations. Current read-only and password qualification checks run before re-reading prepared bindings. Known form action destinations are checked before preparation/dispatch and again after arming, including submitter overrides, resumed work and otherwise-free GET searches. Private GET-search bypasses require an allowed destination; owner exclusions added after preparation refuse before input.

**Read — service/base:** free and asking dispatches commit their context first. Newly opened tabs get their actual identity committed before address navigation. Native host replies are correlated, fragmented and drained even when an owner event cannot be committed. Malformed/duplicate/reused-descriptor handshakes no longer kill the daemon. `chrome/committed.py` derives Chrome owner facts from hash-verified committed journal metadata when SQLite reads fail; offsets/flags are bounded, values stay on disk, and historical peaks can recover after archive tombstones through bounded scan windows. Warning occurrences/acknowledgements use existing `warnings.py` and `paging.py`. `control_notices` exposes the shared mixed-app catalogue; cached Chrome rows/counts cannot resurrect acknowledged warnings. These are the base changes Chrome needs pending19b.

**Read — policy/qualification/uploads:** the fixed list contains vendor hosts only. Private owner exclusions come from `/etc/aresos/control/chrome-excluded-sites.json`, `{"format":1,"hosts":[]}`, root-owned through a protected parent walk, no symlinks or group/world writes; mode0640 with the service group is the image template. Missing/unreadable/unsafe settings refuse. Dotted/IDNA spellings normalize consistently. Dynamic registration and session DNR rules apply exclusions. Qualification reads stable+beta package metadata, plans main+newest three shipped builds twice, verifies both published history and the shipped baseline, aggregates complete named evidence, attests and publishes only on main. Runtime refresh runs daily and on an accepted uncovered-version connection; offline/unverified updates retain held history. Real publication/data-branch/issue/PR mutations never run from this branch. Upload copies are service-owned, immutable to the owner, capped at two/50MiB, released on staging or execution failure and expired after15minutes; partial extension staging also expires.

**Read — six adapters:** Gmail compose/recipients/Bcc/shortcuts, per-message WhatsApp, GitHub actions and exact branch confirmation, owner read-only bank, Gemini questions/chat changes, and Deezer playback/library versus removing/sharing/paying. Trusted kinds require the exact site/account/parameters and current kind hash; deleting/paying/WhatsApp remain ineligible. SHARED remains liftable unchanged for18d. Exact exposed descriptions are in [TOOL-DESCRIPTIONS](TOOL-DESCRIPTIONS.md). They remain verbose because the current base adds its generic suffix to each tool; SHARED is separately identified for18d to lift unchanged. Readability after that lift still needs18d’s actual MCP harness; no slim substitute was added here.

## Verified

**Run — local, plain Python/Node only:**

- Full current Chrome Python suite passed99tests in263.597s: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/chrome_tests python3 -m unittest discover -s control/chrome_tests -v`, retained in `records/continue-3-python.txt`. The prior runner passed91tests in556.964s. Writer inventory:1167 single faults,1167 persistent exhaustion cases,3153 cleanup pairs. Operation sweep:446 single,446 persistent,1605 pairs. The independent oracle decodes committed journal records, rather than trusting SQLite or implementation pending rows. An earlier invocation without PYTHONPATH failed import and exposed the then-unfixed post-preparation destination check; it is retained as a failed run, not evidence of green.
- Current focused engine suite28/28 passed in0.458s (`engine-v36.txt`), including excluded GET/POST form destinations and owner exclusions added after preparation. Registered-bridge and native-handshake draining tests passed; the unchanged Mail daemon exception/next-connection regression passed after fixing the newly introduced early bridge lookup.
- Current complete Node suite75/75 passed in5.958s (`records/continue-3-node.txt`), including primitive replay, sticky protection, interrupted/navigated cleanup and destination changes after arming. These use VM DOM models and plain HTTP, never a browser.
- `python3 control/generate.py --check`: `Generated artifacts match definitions`. `git diff --check` checked between batches. Seven current native-fallback/excluded-form fixture scripts compiled with Node VM; none executed.

**Run — latest completed browser batch, runtime491485c1:** push [42653237166](https://github.com/Ares-Empire/AresOS/actions/runs/42653237166) and PR [42653248018](https://github.com/Ares-Empire/AresOS/actions/runs/42653248018), external-install and policy-install modes in each. Google Chrome157.0.8103.38, exact package checksum verified in the container. PR modes passed34/37named matrices each; push modes33/37each. Both remained failed overall. Compact per-mode summaries with exact browser-log line numbers are retained in `records/42653237166-*-summary.json` and `records/42653248018-*-summary.json`. The three common failures were nested/resume-double followup preparation, replayed owner KeyboardEvent data, and the purported raw-native activation fixture (which was still using a wrapped function). Push modes additionally failed at Chrome/after-input's cleanup/barrier. Source repairs retain observations across failed cleanup, preserve primitive key data, and require the fixture to prove its native function. They are not yet browser passes.

**Run — strict receiver baseline:** page-forgery and hostile-page tests still show0arrivals before approval,1after,1after a repeated attempt. The independent X keyboard Enter at124ms produced0owner arrivals and0Claude300ms arrivals, with separate held preparations: the permitted conservative PLAN-GAP remains a strict failure. Source changes do not fabricate a qualification pass. Password kinds/roots/traces and no browser listening port passed; all asking matrices inspect the independent receiver rather than treating a tool reply as delivery evidence.

**Run — shared compatibility:** base [42653248124](https://github.com/Ares-Empire/AresOS/actions/runs/42653248124) and boundary [42653248092](https://github.com/Ares-Empire/AresOS/actions/runs/42653248092) passed. Mail [42653248062](https://github.com/Ares-Empire/AresOS/actions/runs/42653248062) passed all4fault-sweep shards but failed its container suite: daemon accessed Chrome through a minimal engine before registration. The cache now exists only after an authenticated host registers; the unchanged failing regression passes locally. The two prior Mail paging/disclosure failures passed in that runner. Final-head shared pairs remain required.

**Run/read — qualification and observation:** real synthetic GitHub attestation verification passed, altered bytes/wrong source refused; no real data branch, issue or PR was written. Native-dialog handler submissions now passed as separately prepared operations. Private step observations are committed as open checks without nested bridge I/O. Queues survive source-document navigation and bounded15-minute retired controls, until result/preparation commits and ACK. Cleanup failure now retains holds and reports unknown if completion is uncertain. Stop's interrupted wake also reports uncertain completion. The full65-minute browser matrix remains strict; no case or assertion was removed.

## Groups and feature coverage

**Read/run:** this table records the latest completed evidence, not final acceptance. Full current named cases live in `control/chrome/ci/matrices.mjs` and `verdicts.mjs`; any missing/failing required case stays false.

| Group | Latest completed491485c1 evidence (PR external/policy unless stated) |
|---|---|
|1 What asks|`submit compose deletion and free-input matrix`, `what asks word/label/key matrix`972cases, `Unicode word matching agrees across service and guard`3cases PASS.|
|2 Stopped page steps|`handler/resume matrix`, `script activations never replay`15variants, `loop with uncancelled enclosing submit`, `delayed submission stays held after slow frame arming` PASS. `nested validation and fresh-frame fallback`, `owner synchronous task delayed work and in-flight interleavings`, `unknown activation survives navigation of its source document` FAIL. Later subcases after an assertion are not inferred.|
|3 The binding|`binding every form fact and generic sibling draft`, `cross-frame adapter empty and oversized drafts` PASS, including private post-arm mutation.|
|4 Confirmations|`page confirmations bind their full text and ask independently`, `exact native confirmation and mismatch matrix`, `native-dialog handler submission is prepared separately` PASS.|
|5 Question matches page|`question fields, hidden values, password label, upload path and hash` PASS; exact bytes received once.|
|6 Where Claude may go|`exclusions through frame, popup, redirect, taking and history`, `schemes links and forward routes` PASS. New excluded GET/POST target=_blank form/submitter-override cases await browser evidence.|
|7 Isolation|Forgery0/1/1 PASS. `all password kinds across open closed and cross-site roots` and no Chrome port before/after suite PASS.|
|8 Control and cancelling|`drop release close and stale references`, `deadline and tabs outside the group`, `actual popup Stop button drops all prepared work` PASS. Baseline owner-native Enter remains the permitted conservative PLAN-GAP.|
|9 Crashes and restarts|`Chrome host service crash cutpoints never replay` all9cuts PASS in both PR modes, FAIL at Chrome/after-input barrier in both push modes. This is not stable passing evidence; cleanup repair needs both reruns.|
|10 Adapters|All six `adapter gmail/whatsapp/github/gemini/deezer`, `read-only bank`, and `adapter shortcuts and account-specific questions` PASS.|
|11 Don't ask again|`exact owner kind, recipients, account and revocation` PASS, including widening/revocation.|
|12 Managed ask rule|Explicitly deferred to18d's real normal/skip-permissions harness; no stand-in.|
|13 Residual shown honestly|Ordinary unlabelled fetch, `autosave and after-limit submissions`, `changed read-only preview is a stated residual` PASS.|

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

**Run —491485c1 long article/form:**120paragraphs and80fields,221196–221477characters/UTF-8bytes,14pages capped at16000characters. Full read took4573ms PR external,8102ms PR policy,8234ms push external and7769ms push policy. Approximate tokens55299–55370 means characters/4, not a tokenizer measurement. It is complete and paged but verbose compared with brief17's older DOM-snapshot measurements. `read_form` fragments/catalogue continuations have separate coverage. Final-head measurements remain pending.

## Not verified / remaining work

**Read:** no real account/site or laptop interaction is claimed. Signed-in site selectors, browser-update breakage, extension coexistence and the owner's normal desktop still need the post-boot human checks. The final complete named matrices, both install modes, twice on one final head and final shared workflow pairs remain outstanding. Interim [BUILD-REVIEW-3](BUILD-REVIEW-3.md) and [BUILD-SECURITY-REVIEW-3](BUILD-SECURITY-REVIEW-3.md) contain fresh sol-high/astra-high findings and repair probes; neither certifies final SAFE.

## PLAN-GAP

**Run/read — owner task attribution:** in e1 the physical X keyboard Enter arrived116ms after Claude's handler, produced0owner arrivals and0Claude300ms arrivals, with separate held preparations. `eventPhase` proves synchronous dispatch only; native Enter's default submission can run after the retained trusted event's phase resets. No standard task identity proves that default action belongs to that same owner task. The isolated verdict therefore holds this uncertain case. The strict expected1 test remains failing. Synchronous owner-handler, delayed second submission, replay and in-flight cases stay separate strict cases. This is the continue-2 permitted conservative PLAN-GAP, not a proposed design change. It also keeps page-script qualification false; no pass is fabricated to make the tool ship.

**Read — residuals accepted by section6:** direct fetch/autosave, unlabeled local changes, sends after500ms, and generic read-only previews remain outside the hold/binding guarantee. Fresh-frame raw activations are never resumed and uncertainty is reported honestly. Same-named user-level native host replacement remains decision24's accepted owner-user capability.

## JUDGMENT-CALL

**Read:** MAIN wrapper prototype properties are nonwritable/nonconfigurable so later page replacement cannot bypass a normally held call. This may break libraries that patch those prototypes. Allowing replacement would reintroduce a relaxing path; changing this later requires a different proven wrapper boundary and the hostile fixtures again.

**Read:** committed Chrome recovery metadata includes its full bounded operation/binding/check/ack context in the private independent journal, while unrelated Mail/base compact records stay unchanged. The alternative cached-only projection violatesR1 under failed SQLite reads. This grows private Chrome history and makes format compatibility important;19b should absorb it into its shared committed read/projection path while preserving existing journal history and acknowledgements. No second warning lifecycle was invented.

**Read — event compatibility:** MAIN carries no Event/DOM object in its reports. ISOLATED always constructs a fresh untrusted event from bounded primitive hints, then classifies it after every page getter has finished. It never dispatches an opaque original on the strength of those hints. This can lose original object identity, custom payloads and cancellation history; supported primitive keyboard/mouse/input fields and cancellation return are preserved where available. The previous cross-world original-object path silently refused affected script events in the runner. Main-world native form/type/ownership validation precedes submitter-target reporting; ISOLATED identifies the actual submitter from native dispatch. Changing this later requires proven cross-world event semantics and the receiver/forgery suite. MAIN recursion tracking only adds holds.

**Read — Unicode policy version2:** a frozen Unicode16casefold/word-range resource is shared by Python and generated JavaScript so different runtime Unicode versions cannot disagree on asking labels. Regenerate/version both together for a future Unicode update.

**Read — selected tab for input:** input selects the controlled tab after arming all frames, then rechecks the binding. This makes headed Chrome input visible and avoids background-tab no-ops. It can change Chrome’s selected tab while the owner works. The alternatives are unreliable background input or requiring him to select the tab manually; a future background-input implementation needs equivalent receiver and interleaving evidence. Stale tab/group snapshots and detach callbacks cannot tear down a newer attachment; end-of-control wakes pending input as unknown.

## Handoffs / open questions

**Read —18d:** lift SHARED unchanged, generate slim per-tool descriptions/user-mcp and run group12 in the real precedence harness. Asking actions remain declared in the current generator. `Chrome.trusted(operation)` is the single owner-entry decision method for `require_trusted_send` to call.

**Read —19b:** replace Chrome's provisional offset projection with the shared committed projection/read path, keep Chrome metadata/legacy migration and warning occurrence identities, preserve live session/document/control/policy checks and source-derived acknowledgement behavior. Pending identity checks do not promise content still matches; dispatch rechecks full binding.

**Read —image:** install the protected excluded-sites setting, verifier, native host manifest/policy/update templates and stable production signing key; compute the complete installed runtime hash and register the newest three shipped builds in builds.json. Empty shipped qualification/build registries remain deliberate until real main evidence/image handoff. Nothing under os/ was changed.

**Run — budget:**46Chrome workflow runs used of about50 after the latest push; canceled/superseded runs count. The next push/PR pair will bring this to48; one further batch fits the50-run limit. More verification is still in progress. No Gradle/Java daemon was started. Latest `.work` inventory found no file over500MiB. No question is needed mid-run; work continues.
