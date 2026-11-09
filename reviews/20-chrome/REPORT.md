# 20 — Chrome continuation: stopped on a confirmed unapproved submission

**STOPPED, incomplete, do not merge or ship.** Stage **Now** is not finished.
The continuation's owner-input decision was followed: the existing owner false
hold is retained as a failing regression and is **not** this run's stop reason.
A separate adversarial fixture called the page-visible MAIN guard API to clear
the hold and submitted a form without approval. The independent HTTP receiver
recorded one POST in **all four installations across two workflow runs**.
This is a sending-unasked failure covered by `briefs/20-continue.md`'s stop rule.
No assertion was relaxed and no qualification pass was published.

## Specification and scope

**Read:** local `briefs/20-continue.md` first, then `20-parallel-start.md`;
`origin/main` at `7d54764e2f6aa38d3154d28527ed5658189ec2fe` through `git show`
for AGENTS, brief 20, brief 19b, CONTROL sections 3, 4, 6 and 7, FEATURES,
PLAN and design re-checks 29–34. The previous report and branch code supplied
the starting state. No other branch was merged; no protected specification,
image or mod file was changed. The first attempted `git show` for the local
continuation brief correctly reported that it is not on `origin/main`; the
brief was then read from this branch as its Where to read section requires.

**Read:** final runtime commit is `5e931377df94cae0a9e5dd1db1e550cfa2572b6a`.
Its build hash is
`bdf6ce44b18a50f157754d2107c7ecd896866444a5fd0684248fdc2a3f0a31ac`.
The closing commit adds reports and evidence only. PR #27 stays draft.
18d's slim generator, `user-mcp.json`, shared MCP instructions and group 12
remain explicitly deferred; no replacement for them was built.

## Done in this continuation

- **Read — socket service:** malformed native handshakes leave their descriptor
  open long enough for the daemon to return a refusal instead of terminating.
  Dead peers are unregistered by their saved fd even if a replacement hello is
  rejected. A live existing peer is checked without waiting on its 15-second
  timeout; refused replacement/setup paths clear bridge session state.
- **Read — activation names:** MAIN wrappers and fallback capture now resolve
  `aria-labelledby` and associated labels using the reader's name precedence.
  Browser-free cases cover each label source in click, dispatch and fallback.
  The full browser semantic matrix remains unqualified.
- **Read — late policy:** prepared sends, uploads, native dialogs and resumed
  submissions recheck current top/frame read-only restrictions; trusted
  submissions use the same guard. Acting revalidation now checks password
  exclusion qualification before any fresh binding read. Qualification delivery
  itself is still incomplete, so this guards records already held by the service.
- **Read — owner exclusions:** the guessed personal host was removed from all
  shipped Chrome code and manifest data. Vendor entries remain in the fixed
  list. Owner entries are loaded through the base's protected root-owned,
  no-symlink configuration walk. Missing, unreadable, malformed or unsafe
  settings refuse Chrome reads and actions; an installed empty list is valid.
  The extension registers content scripts and builds session DNR rules from
  the runtime list. Trailing-dot DNS aliases are canonicalized in both URL
  checks and included in the generated runtime exclusion patterns.
- **Read — strict evidence:** the original owner-input assertion still fails
  strictly. The Claude delayed-submit fixture now uses 300 ms. A new page-forgery
  fixture executes even after an owner-test failure, and the process returns
  nonzero for either failure. Earlier smoke output still explicitly says
  `acceptance_complete:false`.
- **Read — independent interim reviews:** [BUILD-REVIEW-2](BUILD-REVIEW-2.md)
  and [BUILD-SECURITY-REVIEW-2](BUILD-SECURITY-REVIEW-2.md) are fresh sol-high and
  astra-high reviews. The general review's DNS-alias and peer-replacement
  findings were fixed and rechecked. The security review's public MAIN API
  finding remains open and now has browser receiver evidence. Neither review
  is a final SAFE assessment.

The earlier partial extension, native relay, adapter definitions, generated
current settings, binding/resume logic, upload copies and fake-browser tests
remain. They are not a completed Now implementation.

## Verified — commands and results

**Run — locally, no browser or local container:**

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=control:control/chrome_tests python3 -m unittest discover -s control/chrome_tests -v
Ran 42 tests in 39.336s
OK
Chrome durable-write sweep {'single': 442, 'persistent': 442, 'pairs': 829}

node --test control/chrome_tests/*.test.mjs
tests 13; pass 13; fail 0; skipped 0

PYTHONDONTWRITEBYTECODE=1 python3 control/generate.py --check
Generated artifacts match definitions

git diff --check
(exit 0, no output)

PYTHONDONTWRITEBYTECODE=1 python3 control/chrome/build.py
bdf6ce44b18a50f157754d2107c7ecd896866444a5fd0684248fdc2a3f0a31ac
```

Exact local outputs are retained under [records](records/). The first local
candidate ran 41 Python tests and 12 Node tests successfully. A new socketpair
regression initially exposed a 15-second `TimeoutError` despite MSG_DONTWAIT;
`select.select` fixed the cause, and the unchanged regression now passes.
The suite uses real local storage fault injection with a fake browser; it
still does not cover all Chrome durable writes or provide the full 19b oracle.

**Run — shared base:** [42599594777](https://github.com/Ares-Empire/AresOS/actions/runs/42599594777)
passed on runtime predecessor `55cdee6a`; GitHub log line 322 says
`test_all_socket_peer_credentials_even_permissive_modes ... ok`, and lines
413–415 say `Ran 142 tests in 189.184s`, `OK` (a source-line summary is retained). Base run
[42600291601](https://github.com/Ares-Empire/AresOS/actions/runs/42600291601)
also passed on final runtime `5e931377`. Thus the reported base socket
regression is repaired, without changing its assertion.

**Run — boundary:**
[42599594926](https://github.com/Ares-Empire/AresOS/actions/runs/42599594926)
and [42600291884](https://github.com/Ares-Empire/AresOS/actions/runs/42600291884)
passed on those respective heads. **Not verified:** Mail's final-runtime run
[42600291829](https://github.com/Ares-Empire/AresOS/actions/runs/42600291829)
was still running when the safety stop was recorded. No Mail pass is inferred.
Earlier runs interrupted by later pushes are not passing evidence.

**Run — Chrome startup diagnostic:** `42599586064` and `42599594783` on
`55cdee6a` failed before the receiver tests: the test-only audit handshake was
incorrectly gated on exclusions being configured. `audit` now runs before
that page-access gate; `background.test.mjs` preserves the regression.
These startup failures are not safety or qualification evidence.

## Confirmed safety stop — independent receiver evidence

**Run:** both [42600282635](https://github.com/Ares-Empire/AresOS/actions/runs/42600282635)
and [42600291598](https://github.com/Ares-Empire/AresOS/actions/runs/42600291598)
tested runtime `5e931377`, Google Chrome **157.0.8103.38**, with external and
policy installations in disposable Linux containers. In each `browser.txt`:

- lines 3–8 pass only the existing smoke subset (one generic send, both resume
  kinds, one wrapped activation, a small password test and a residual fetch);
- line 10 records real X keyboard owner input while Claude's delayed task is
  pending; line 11 fails the strict owner assertion;
- line 15 records the page forgery, `arrivals:1`, no stopped steps or followups;
- line 16 fails `A page-forged control mark must never release a Claude-caused
  submission without approval`, `1 !== 0`.

Each independent `receiver.jsonl` is retained unchanged and has the decisive entry at **line 6**:
`POST /receive?case=page-forgery`, body `source=page-forged-mark`.
No `chrome_submit` was called for that action. The page's Continue handler
calls `globalThis[Symbol.for('aresos.chrome.page.v1')].stop('page-invented-epoch')`
and then the form's native `submit()`. The invalid epoch is accepted and
clears the hold. This is not the accepted ordinary-click fetch residual:
the tested guarantee is that a page cannot forge the extension's guard state.

| Run | Installation | Owner delay | Owner arrivals | Claude 300 ms arrivals before approval | Forged-mark arrivals |
|---|---|---:|---:|---:|---:|
| 42600282635 | external | 126 ms | 0 | 0 | **1** |
| 42600282635 | policy | 129 ms | 0 | 0 | **1** |
| 42600291598 | external | 132 ms | 0 | 0 | **1** |
| 42600291598 | policy | 109 ms | 0 | 0 | **1** |

**Run:** [records](records/) retains both runs' exact run identities, browser
logs, receiver logs, owner and forgery results, Chrome versions, launch and
no-listener checks. [screenshots](screenshots/) retains each failure screen.
Retained text logs normalize trailing whitespace only; substantive output and
line numbers are unchanged. Original full artifacts remain on the linked runs.
All four installations failed; no full group set passed even once, let alone
twice. The preserved earlier owner regression from run `42596054202` remains
historical evidence; its owner false hold is no longer a stop under the
continuation's decision.

**Read — required repair before another build:** `arm`, `stop` and `resume`
are all public and unauthenticated, and the DOM identity events are forgeable.
The security review demonstrates the arm/resume variants with Node too.
Renaming the global or passing an owner verdict over a DOM event would not
establish the required boundary. A replacement must authenticate bootstrap
and every state change, prevent capability theft through page-overridden
intrinsics, bind identities and consume approvals once. Its isolated-only
owner/in-flight channel and same-task attribution still need a demonstrated
solution. This report does not prove that every possible architecture fails.
The build is stopped rather than substituting an unverified boundary or
relaxing the hostile-page assertion.

## The 13 groups — actual status

**Read / run:** names are section 6's groups. PASS lines below identify a smoke
case only, never the whole group. Test group 12 is the explicitly deferred one.

| Group | Test names / evidence | Remaining obligation |
|---|---|---|
| 1 What asks | `test_group1_approval_first_exact_and_dispatch_once`; `test_group1_words_whole_words_all_labels_and_activation_paths`; browser line 3 | Complete real-browser word, attribute, control, key, upload and free-case matrices |
| 2 Stopped page steps | `page.test.mjs` same-kind, loop, nested, non-cancellable activation cases; browser lines 4–6 | All handler origins, direct control approval, fresh-frame fallback, nested and other-form matrices in Chrome |
| 3 The binding | `test_group3_current_draft_bound_even_without_prior_fill_and_across_frames`; reader field-state test; late-policy regressions | Every changed binding fact in real Chrome; re-check 30/32 fixtures, empty/oversize/existing drafts, preview residual |
| 4 Confirmations | Native dialog plumbing and exact confirmation declaration in source | Exact covered confirmation consumption is not built; all exact/mismatch tests missing |
| 5 The question matches the page | Exact ordered approval Python test and current description fields | Full fixture matrix for hidden fields, password labels, file path/hash, recipients and unknown destination; terminal/phone presentation later |
| 6 Where Claude may go | `test_group6_schemes_and_shipped_fixed_hosts`; `test_exclusions`; `background.test.mjs` runtime/dotted exclusions | `.test` owner-excluded host through take, redirects, popups, history and frames; full real-browser scheme routes |
| 7 Isolation | Browser no-listener/launch records; small password smoke at line 7; **page-forgery FAIL line 16, receiver line 6** | Private authenticated guard boundary; all return/read/relay/log/result password traces over every excluded kind, root and cross-site frame; raw-method/forgery matrix |
| 8 Control and cancelling | `test_group8_drop_deadline_restart_never_dispatch`; **owner input FAIL line 11** | Owner same-task/in-flight/delayed cases, actual Stop click, release/close/restart/stale-reference browser matrices |
| 9 Crashes and restarts | Fake-browser dispatch-once/fault tests; `test_bridge` invalid/replacement host tests | Chrome/host/service crash cutpoints before check, after submitting and after input with receiver evidence |
| 10 Adapters | Six semantic recognizers in `sites.py`; fake Gmail tests | All six fixture sites and all feature paths remain unbuilt |
| 11 Don't ask again | `test_group11_owner_only_exact_parameters_revocation_and_widened_kind` | Actual owner details/CLI flows, complete exact-kind/account/recipient and qualification browser cases |
| 12 Managed ask precedence | Current generator has asking submit and free trusted submit rules | Deferred to 18d's real harness; no stand-in built |
| 13 The residual shown honestly | Browser line 8 and receiver line 4: ordinary-click fetch not held | Autosave, after-limit submit and changing read-only preview receiver fixtures missing |

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
| Owner list/revoke/read-only | `chrome_sites`, details UI | Admin-only fake test; owner CLI aliases and list paging incomplete; late-policy revalidation is unit-tested; complete browser coverage is missing |
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

## Tool descriptions and view sizes

**Read:** [TOOL-DESCRIPTIONS.md](TOOL-DESCRIPTIONS.md) records every exact current
Chrome tool description as generated for Claude. The source's `SHARED` block
remains liftable unchanged into 18d's MCP instructions. These are draft
contracts, not release claims. Exact adapter confirmations and other missing
behavior below must be implemented and qualified before the descriptions can
be relied on; this stopped package is not ready to expose to the owner.

**Run — historical measurement only:** successful smoke run `42591825243`
returned small views of 1,135–2,852 characters (external) and 1,133–2,847
(policy). **Not verified:** representative long-form/article sizes, token counts
and collection latency. No prior DOM-snapshot measurement is reused as proof
for this reader. Complete long-page paging and list paging remain unfinished.

## Image handoff: private excluded sites

**Read:** install `/etc/aresos/control/chrome-excluded-sites.json`:

```json
{"format":1,"hosts":[]}
```

Use the owner's actual lowercase DNS host names only in the image's private
setting, never in this repository. A name includes subdomains; there is no
scheme, port or path. The file and every parent must be root-owned, without
symlinks or group/world write permission. File mode **0640**, group
`aresos-tools`, gives the service read access and only root write access.
An existing empty list is allowed. Missing, unreadable, malformed or unsafe
settings produce `chrome_settings_unavailable` and refuse reads/actions.
[Packaging README](../../control/chrome/packaging/README.md) documents this for
18c and `laptop-aresos`. Container setup uses only **approval.test**.
The extension receives the list through the native channel, registers content
scripts with exclusions and derives DNR session rules. A changed list ends
control before the new rules take effect. Browser route coverage is not complete.

## Not verified / unfinished Now work

**Read:** this remains implementation work, not reassignment to 18d:

- The authenticated MAIN boundary and isolated owner/in-flight attribution,
  plus all five strict owner tests in the continuation. The public guard
  API remains unsafe. Two owner behaviors (during dispatch and delayed owner
  work) have no strict receiver fixture yet; forgery fails and direct owner
  Enter is still falsely held.
- Full matrices of groups 1–11 and 13, all six adapter sites and exact covered
  confirmations; complete page/host/service crash and Stop/cancellation tests.
- Qualification workflow: stable/beta package lookup, newest three shipped
  builds, twice-per-pair full suite, append-only publisher verification,
  attestation, isolated publisher tests, issues/PR stubs and the shipped-copy
  update. The shipped record and build registry remain empty. Nothing from
  this branch wrote the real `chrome-qualification` data branch, main, issues
  or PRs. Runtime daily/on-connect refresh still has no production caller;
  real valid/altered attestation delivery tests and full gating sequences
  remain missing. No pass was invented from these tests.
- R1/R2/R3: pending still needs committed-context plus live-session validity;
  free navigation needs complete before-effect context and committed created
  tab identity. Warning-producing page checks, owner callbacks, disconnects
  and malformed frames need complete lifecycle/fault qualification. Existing
  `warnings.py`, `paging.py` and result bounds are reused, not replaced.
- Full storage-fault sweep over uploads, owner lists, qualification delivery,
  page warnings and every other Chrome durable write; persistent restart
  failures and an independent full outcome oracle. Current 442/442/829 sweep
  covers submit/free paths only with a fake browser.
- Bounded upload retention/cleanup, complete bounded list/form/view paging,
  representative long-page measurement and final tool-description accuracy.
- Complete Mail/base/boundary verification twice on a final accepted head.

**Assumed / later owner gates:** real signed-in site checks, production signing
identity, image installation, ordinary-profile compatibility and complete
phone/terminal prompt presentation remain owner/image work. No real account,
real fixture destination or local browser/profile was used.

## JUDGMENT-CALL

- **Read / proposed wording, as the continuation requests:** qualify section
  6's owner-input statement to: “A direct owner input is exempt only for the
  same browser task when no extension dispatch was in flight. An uncertain
  submission, including a delayed step started by the owner's input inside
  Claude's short hold limit, stays held.” This preserves the lead's decision
  and explicitly names the owner's delayed-step cost. The alternative of
  clearing the whole hold on owner input would allow Claude's already-scheduled
  submission through. Changing this later needs a stronger attribution proof
  and the interleaving fixture suite; it does not require rewriting owner data.
  This wording is a proposal for the lead to take to the owner; no design file
  was edited and no missing fixture is claimed run.
- **Read / chosen:** retain the strict forgery regression and stop after the
  actual unapproved POST. Treating this as an ordinary-click residual, hiding
  the failure behind the owner assertion, or declaring a private verdict on
  the public DOM bridge were rejected. A replacement control channel needs
  adversarial bootstrap/identity/capability tests before resuming the build.
- **Read / unchanged earlier choices:** byte-backed File/DataTransfer upload
  installation; refusal of unprimed documents, duplicate iframe-address
  geometry and unsupported transforms. These still need final qualification
  and owner/lead review before shipping.

## PLAN-GAP / moving on to 18d and 19b

**Read:** the unfinished Now items are builder gaps. The newly demonstrated
public control API is a security implementation gap; it is not permission
to weaken the specification. No impossibility of the design is asserted.

**Read — 18d:** lift unchanged SHARED text into MCP instructions, migrate the
current generated asks to the slim generator, create its user MCP wiring and
run group 12 in the real precedence harness. Asking actions remain declared
in definitions. The owner-entry decision is kept in the single `trusted()`
adapter method for 18d's `require_trusted_send` integration.

**Read — 19b:** use its committed read path/projection for Chrome operations,
free-action contexts, page-step open checks, warning occurrences and
acknowledgements. Derive pending invalidations from committed binding plus
live browser/session validity; preserve occurrences through restart, restore,
expiry and archive. Extend the combined storage oracle. No competing owner
projection was built on this branch.

## Run count, open questions and closing inventory

**Run:** GitHub lists **11** Chrome runs before this continuation's first push
(the continuation text's “9 used” predates two additional runs). This run added
four: `42599586064`, `42599594783`, `42600282635`, `42600291598`, so **15** had run
when the stop was recorded. **Assumed until queued:** the closing report push
triggers two more (push and PR), bringing the expected total to **17 / 50**.
Base, Mail and boundary workflows are not counted. No publisher test or
workflow wrote the real qualification data branch.

**Read:** the lead needs the confirmed public-API vulnerability and an actual
private-bridge/owner-attribution implementation before another acceptance run.
No mid-run owner answer was requested. This report is not a request to merge.
The first closing push was blocked by gitleaks on synthetic token strings in
the full boundary workflow log. That log was removed from the unpushed commit
and replaced with a status summary; no scanner exception or bypass was added.

**Run:** all work stayed in this worktree on `pkg/20-chrome`; each commit has
the required model trailer and each push used its privacy hook. No Mac browser,
Chromium, profile or local browser container was opened, read or changed. No
system installation, admin action, Gradle or image build ran locally. The closing
`.work/` inventory printed **files over 500 MB: []**. Downloaded evidence is
synthetic runner output, not a browser profile.
